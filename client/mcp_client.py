import asyncio
import json
import os
import re
from contextlib import AsyncExitStack
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_agent

load_dotenv()

DESTRUCTIVE_TOOLS = {
    "remove_container",
    "remove_image",
    "remove_network",
    "stop_container",
    "build_image",
}

AGENT_TIMEOUT_SECONDS = 80


class ChatMessage(BaseModel):
    role:    str
    content: str


class ChatHistory(BaseModel):
    messages: list[ChatMessage] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append(ChatMessage(role=role, content=content))

    def last_n(self, n: int = 10) -> list[ChatMessage]:
        return self.messages[-n:]

    def clear(self) -> None:
        self.messages = []

    def to_langchain_messages(self) -> list:
        result = []
        for msg in self.last_n(10):
            if msg.role == "user":
                result.append(HumanMessage(content=msg.content))
            else:
                result.append(AIMessage(content=msg.content))
        return result


def sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _clean_docker_error(raw_error: str) -> str:
    match = re.search(r'\("(.+?)"\)', raw_error, re.DOTALL)
    if match:
        inner = match.group(1)
        inner = inner.replace('\\"', '"').strip().rstrip(".")
        return inner

    parts = raw_error.split(":")
    return parts[-1].strip() if len(parts) > 1 else raw_error


def _format_tool_result(tool_name: str, parsed: dict | None, raw_text: str) -> dict:

    if parsed is None:
        return {"title": raw_text}

    if tool_name == "list_containers":
        containers = parsed.get("containers", [])
        total      = parsed.get("total", len(containers))
        filt       = parsed.get("filter", "all")
        rows = [
            {
                "Name":   c.get("name", "—"),
                "Image":  c.get("image", "—"),
                "Status": c.get("status", "—"),
                "ID":     c.get("id", "—")[:12],
            }
            for c in containers
        ]
        return {
            "title": f"{total} container(s) found ({filt})",
            "table": rows,
        }

    if tool_name == "run_container":
        c = parsed.get("container", {})
        return {
            "title":  parsed.get("message", "Container started."),
            "detail": f"Name: **{c.get('name', '—')}** · Image: `{c.get('image', '—')}` · Status: `{c.get('status', '—')}`",
        }

    if tool_name == "stop_container":
        return {"title": parsed.get("message", "Container stopped.")}

    if tool_name == "restart_containers":
        results = parsed.get("results", [])
        rows = [
            {"Container": r.get("container", "—"), "Result": r.get("status", "—")}
            for r in results
        ]
        return {
            "title": parsed.get("message", "Restart complete."),
            "table": rows,
        }

    if tool_name == "remove_container":
        return {"title": parsed.get("message", "Container removed.")}

    if tool_name == "list_images":
        images = parsed.get("images", [])
        total  = parsed.get("total", len(images))
        rows = [
            {
                "Tag":     ", ".join(img.get("tags", ["<untagged>"])),
                "Size":    f"{img.get('size_mb', 0)} MB",
                "Created": img.get("created", "—"),
                "ID":      img.get("id", "—")[7:19],   # strip "sha256:" prefix, show 12 chars
            }
            for img in images
        ]
        return {
            "title": f"{total} image(s) found locally",
            "table": rows,
        }

    if tool_name == "pull_image":
        img  = parsed.get("image", {})
        tags = ", ".join(img.get("tags", []))
        return {
            "title":  parsed.get("message", "Image pulled."),
            "detail": f"Tags: `{tags}` · Size: **{img.get('size_mb', '—')} MB**",
        }

    if tool_name == "remove_image":
        return {"title": parsed.get("message", "Image removed.")}

    if tool_name == "build_image":
        return {
            "title":  parsed.get("message", "Image built."),
            "detail": f"Tag: `{parsed.get('tag', '—')}` · ID: `{parsed.get('id', '—')}`",
        }

    if tool_name == "list_networks":
        networks = parsed.get("networks", [])
        total    = parsed.get("total", len(networks))
        rows = [
            {
                "Name":   n.get("name", "—"),
                "Driver": n.get("driver", "—"),
                "Scope":  n.get("scope", "—"),
                "ID":     n.get("id", "—")[:12],
            }
            for n in networks
        ]
        return {
            "title": f"{total} network(s) found",
            "table": rows,
        }

    if tool_name == "create_network":
        net = parsed.get("network", {})
        return {
            "title":  parsed.get("message", "Network created."),
            "detail": f"Driver: `{net.get('driver', '—')}` · Scope: `{net.get('scope', '—')}`",
        }

    if tool_name == "remove_network":
        return {"title": parsed.get("message", "Network removed.")}

    if tool_name == "connect_container_to_network":
        return {"title": parsed.get("message", "Container connected to network.")}

    if tool_name == "get_docker_info":
        return {
            "title":  "Docker daemon info",
            "detail": (
                f"Version: **{parsed.get('docker_version', '—')}** · "
                f"OS: `{parsed.get('os', '—')}` · "
                f"Arch: `{parsed.get('architecture', '—')}` · "
                f"Containers: {parsed.get('total_containers', 0)} "
                f"({parsed.get('running', 0)} running) · "
                f"Images: {parsed.get('total_images', 0)}"
            ),
        }

    msg = parsed.get("message")
    if msg:
        return {"title": msg}
    return {"title": f"{tool_name} completed."}


class MCPClient:

    SYSTEM_PROMPT = SYSTEM_PROMPT = """You are a Docker assistant. Use the available tools to automate Docker tasks.
 
STRICT RULES:
1. Call ONLY ONE tool at a time — never call multiple tools in a single response.
2. Wait for each tool result before deciding what to do next.
3. After receiving a tool result, re-evaluate and THEN call the next tool if needed.
4. After receiving a tool result, return the final answer IMMEDIATELY if no more tools are needed.
5. Do NOT call extra tools unless the user explicitly asked.
6. Do NOT guess project paths — ask the user if a path is not provided.
7. If a tool returns status "error", STOP and report the error to the user clearly.
 
MULTI-STEP TASK RULES — VERY IMPORTANT:
- For tasks like "pull image then run container":
  * Step 1: Call pull_image ONLY. Wait for result.
  * Step 2: Only after pull_image succeeds, call run_container.
  * Never call run_container in the same turn as pull_image.
- Think of each tool call as a separate reasoning step.
 
DOCKERFILE + DOCKERIGNORE FLOW — VERY IMPORTANT:
- After create_dockerfile succeeds, ALWAYS ask:
  "Would you like me to also create a .dockerignore file? It will reduce your image size by excluding unnecessary files like node_modules, __pycache__, .git, logs, etc. (yes/no)"
- Wait for the user's reply before doing anything else.
- If the user says yes → call create_dockerignore with the same project_path (and language if known).
- If the user says no → say "All done!" and stop.
- Never call create_dockerignore automatically without asking first.

BUILD IMAGE RULES — VERY IMPORTANT:
- NEVER call build_image unless the user has explicitly provided BOTH:
  * project_path — the absolute path to the folder containing the Dockerfile
  * tag — the image tag to use
- If either is missing, ask for them BEFORE doing anything else. Example:
  "To build the image I need two things:
   1. The absolute path to your project folder (the one containing the Dockerfile)
   2. A tag for the image — I'll default to `<folder-name>:latest` if you leave it blank"
- If the dockerfile does not exists, terminate tool call and say no dockerfile to build image.
- For the tag, derive it from the last segment of the project_path the user provided.
  Examples: path=/home/user/my-api  → tag=my-api:latest
            path=C:\Projects\shop-service → tag=shop-service:latest
- Never invent a path. Never use placeholder tags like "my-app:latest" or "project:latest".
- If the user gives a path but no tag, use <folder-name>:latest and tell them.
 
CONFIRMATION RULES — VERY IMPORTANT:
- For destructive actions (remove_container, remove_image, stop_container, remove_network, build_image):
  * First tell the user EXACTLY what you are about to do.
  * Then ask: "Are you sure you want to proceed? (yes/no)"
  * Wait for the user to reply before calling the tool.
  * If the user says yes → call the tool.
  * If the user says no → say "Operation cancelled." and stop.
- Never perform a destructive action without explicit confirmation.
 
ERROR HANDLING — VERY IMPORTANT:
- When a tool returns an error, always explain it in plain English.
- For "container name already in use" errors: tell the user the name is taken and suggest they remove the old container first or use a different name.
- For "image not found" errors: tell the user to pull the image first.
- Always suggest a clear next step after an error.
 
OUTPUT FORMAT:
- Be concise. One short paragraph is enough for simple answers.
- Do NOT repeat or summarize tool results — the UI already shows them as tables.
- Only add context or next steps if genuinely useful.
"""

    def __init__(self):
        self.session:              Optional[ClientSession] = None
        self.exit_stack:           AsyncExitStack          = AsyncExitStack()
        self.tools:                list                    = []
        self.agent                                         = None
        self.history:              ChatHistory             = ChatHistory()
        self._abort:               bool                    = False
        self._active_tool_parent:  Optional[str]           = None

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
            max_retries=2,
        )

    async def connect(self) -> None:
        server_path = os.getenv("MCP_SERVER_PATH")
        if not server_path:
            raise ValueError("MCP_SERVER_PATH not set in .env")

        command = "python" if server_path.endswith(".py") else "node"
        server_params = StdioServerParameters(command=command, args=[server_path])

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        await self.session.initialize()

        self.tools = await load_mcp_tools(self.session)

        llm_sequential = self.llm.bind(
            tool_choice="auto",
            parallel_tool_calls=False,
        )

        self.agent = create_agent(
            model=llm_sequential,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT,
        )

        print(f"MCP connected. Tools: {[t.name for t in self.tools]}")

    async def disconnect(self) -> None:
        await self.exit_stack.aclose()
        self.session = None
        print("MCP disconnected.")

    def abort(self) -> None:
        self._abort = True

    @staticmethod
    def _extract_tool_output(raw) -> tuple[str, dict | None]:
        if hasattr(raw, "content"):
            raw = raw.content
        if isinstance(raw, list):
            parts = []
            for block in raw:
                if isinstance(block, dict):
                    parts.append(block.get("text", "") or str(block))
                else:
                    parts.append(str(block))
            raw = "\n".join(parts)
        text = raw if isinstance(raw, str) else str(raw)
        try:
            return text, json.loads(text)
        except Exception:
            return text, None

    @staticmethod
    def _ensure_str(content) -> str:
        """Coerce AIMessage.content (str OR list of content blocks) to plain string."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text", "") or block.get("content", "") or "")
                else:
                    parts.append(str(block))
            return "".join(parts).strip()
        return str(content)

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        if not self.agent:
            yield sse_event("error", {"message": "Agent not ready."})
            return

        self._abort              = False
        self._active_tool_parent = None

        print(f"\n{'='*50}\n👤 USER: {user_message}\n{'='*50}")

        messages = self.history.to_langchain_messages()
        messages.append(HumanMessage(content=user_message))

        full_response            = ""
        tool_error_detected      = False
        tools_called             : set[str] = set()
        successful_tool_ran      = False 
        _suppress_tokens         = False   

        try:
            async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
                async for event in self.agent.astream_events(
                    {"messages": messages},
                    version="v2",
                    config={"recursion_limit": 25},
                ):
                    if self._abort:
                        full_response = "⛔ Stopped by user."
                        yield sse_event("error", {"message": full_response})
                        break

                    kind = event["event"]

                    if kind == "on_chat_model_start":
                        if not successful_tool_ran:
                            _suppress_tokens = False
                        yield sse_event("thinking", {"message": "🧠 Agent is thinking..."})

                  
                    elif kind == "on_chat_model_stream":
                        if _suppress_tokens:
                            continue
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            text = chunk.content
                            if isinstance(text, str) and not text.lstrip().startswith("{"):
                                print(text, end="", flush=True)
                                full_response += text
                                yield sse_event("token", {"text": text})

                    elif kind == "on_tool_start":
                        tool_name  = event["name"]
                        tool_input = event.get("data", {}).get("input", {})
                        parent_id  = (event.get("parent_ids") or [""])[0]

                        print(f"\n🔧 TOOL: {tool_name} | Input: {tool_input}")

                        if self._active_tool_parent and self._active_tool_parent == parent_id:
                            print(f"⚠️  Parallel tool call detected: {tool_name}")
                            yield sse_event("warning", {
                                "message": f"⚠️ Parallel call to **{tool_name}** detected — waiting.",
                            })
                        self._active_tool_parent = parent_id

                        call_key = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
                        if call_key in tools_called:
                            print(f"⚠️  Duplicate tool call skipped: {tool_name}")
                            continue
                        tools_called.add(call_key)

                        if tool_name in DESTRUCTIVE_TOOLS:
                            yield sse_event("confirm", {
                                "tool":    tool_name,
                                "input":   tool_input,
                                "message": f"⚠️ About to run **{tool_name}** with `{json.dumps(tool_input)}`",
                            })
                        else:
                            yield sse_event("tool_call", {
                                "tool":    tool_name,
                                "input":   tool_input,
                                "message": f"🔧 Running **{tool_name}**...",
                            })

                    elif kind == "on_tool_end":
                        self._active_tool_parent = None
                        tool_name  = event["name"]
                        raw_output = event.get("data", {}).get("output", "")
                        text, parsed = self._extract_tool_output(raw_output)

                        print(f"\nRESULT: {text[:400]}")

                        if isinstance(parsed, dict) and parsed.get("status") == "error":
                            tool_error_detected = True
                            raw_err   = parsed.get("error", parsed.get("message", "Unknown error"))
                            clean_err = _clean_docker_error(raw_err)
                            yield sse_event("tool_result", {
                                "status":  "error",
                                "message": f"❌ {clean_err}",
                            })
                            
                            _suppress_tokens    = False
                            successful_tool_ran = False
                            full_response       = ""   
                        else:
                            formatted = _format_tool_result(tool_name, parsed, text)
                            yield sse_event("tool_result", {
                                "status": "success",
                                **formatted,
                            })
                           
                            successful_tool_ran = True
                            _suppress_tokens    = True
                            full_response       = ""   # will stay empty → done sends ""

                    elif kind == "on_chain_end":
                        output = event.get("data", {}).get("output", {})
                        if isinstance(output, dict):
                            msgs = output.get("messages", [])
                            if msgs and hasattr(msgs[-1], "content"):
                                last = self._ensure_str(msgs[-1].content)
                                if last and not full_response:
                                    full_response = last

        except asyncio.TimeoutError:
            full_response = f"❌ Request timed out after {AGENT_TIMEOUT_SECONDS} seconds."
            yield sse_event("error", {"message": full_response})

        except asyncio.CancelledError:
            full_response = "⛔ Stopped by user."
            yield sse_event("error", {"message": full_response})

        except Exception as e:
            full_response = f"❌ Agent error: {str(e)}"
            yield sse_event("error", {"message": full_response})

        self.history.add("user",      user_message)
        self.history.add("assistant", self._ensure_str(full_response))

        print()
        yield sse_event("done", {"message": self._ensure_str(full_response)})

    def clear_history(self) -> None:
        self.history.clear()

    def get_tools_info(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description or "No description"}
            for t in self.tools
        ]

