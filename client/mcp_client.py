import asyncio
import json
import os
from contextlib import AsyncExitStack
from pydantic import BaseModel
from typing import Any, Optional
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks.base import BaseCallbackHandler

load_dotenv()

DESTRUCTIVE_TOOLS = {
    "remove_container",
    "remove_image",
    "remove_network",
    "stop_container",
    "build_image",      
}


class AgentThinkingLogger(BaseCallbackHandler):
    def on_llm_start(self, serialized: dict, prompts: list, **kwargs) -> None:
        print("\n" + "="*50)
        print("🧠 LLM THINKING...")
        print("="*50)

    def on_llm_end(self, response, **kwargs) -> None:
        for gen in response.generations:
            for g in gen:
                text = getattr(g, "text", "") or getattr(g.message, "content", "")
                if text:
                    print(f"LLM Output:\n{text}")

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        print(f"\n CALLING TOOL: {tool_name}")
        print(f"   Input: {input_str}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        print(f"TOOL RESULT:\n{output}")

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        print(f"TOOL ERROR: {error}")

    def on_agent_action(self, action, **kwargs) -> None:
        print(f"\n ACTION: {action.tool}")
        print(f"   Input:  {action.tool_input}")

    def on_agent_finish(self, finish, **kwargs) -> None:
        print(f"\nFINAL ANSWER:\n{finish.return_values.get('output', '')}")
        print("="*50 + "\n")


class ChatMessage(BaseModel):
    role: str       
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
    

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()     
        self.tools: list = []
        self.agent = None
        self.history = ChatHistory()
        self._abort: bool = False          
 
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
            max_retries=2,
        )

    SYSTEM_PROMPT = """You are a Docker assistant. Use the available tools to automate Docker tasks.
 
STRICT RULES:
1. Call ONLY the ONE tool that directly answers the user request.
2. Call each tool ONLY ONCE per user message — never retry the same tool.
3. After receiving a tool result, return the final answer IMMEDIATELY.
4. Do NOT call extra tools unless the user explicitly asked.
5. Do NOT guess project paths — ask the user if a path is not provided.
6. If a tool returns status "error", STOP and report the error to the user directly.
 
CONFIRMATION RULES — VERY IMPORTANT:
- For destructive actions (remove_container, remove_image, stop_container, remove_network, build_image):
  * First tell the user EXACTLY what you are about to do.
  * Then ask: "Are you sure you want to proceed? (yes/no)"
  * Wait for the user to reply before calling the tool.
  * If the user says yes → call the tool.
  * If the user says no → say "Operation cancelled." and stop.
- Never perform a destructive action without explicit confirmation.
 
OUTPUT FORMAT:
- Present containers/images/networks as a clean markdown table.
- Be concise. One short paragraph is enough for simple answers.
"""

    async def connect(self) -> None:
        server_path = os.getenv("MCP_SERVER_PATH")
        if not server_path:
            raise ValueError("MCP_SERVER_PATH not set in .env")

        command = "python" if server_path.endswith(".py") else "node"
 
        server_params = StdioServerParameters(
            command=command,
            args=[server_path],
        )
 
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
 
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
 
        await self.session.initialize()
 
        self.tools = await load_mcp_tools(self.session)
 
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT,
        )
 
        print(f"MCP connected. Tools loaded: {[t.name for t in self.tools]}")

    async def disconnect(self) -> None:
        await self.exit_stack.aclose()
        self.session = None
        print("MCP disconnected.")

    def abort(self) -> None:
        """Signal the current chat() call to stop after the next chunk."""
        self._abort = True

    async def chat(self, user_message: str) -> str:
        if not self.agent:
            raise RuntimeError("Agent not ready. Server may still be starting.")

        self._abort = False                  # reset for new request
 
        print(f"\n{'='*50}")
        print(f"👤 USER: {user_message}")
        print(f"{'='*50}")
 
        messages = self.history.to_langchain_messages()
        messages.append(HumanMessage(content=user_message))
 
        response = ""
        tool_error_detected = False
 
        try:
            async for event in self.agent.astream_events(
                {"messages": messages},
                version="v2",
            ):

                if self._abort:
                    print("\n[ABORTED by user]")
                    response = response or "⛔ Stopped by user."
                    break

                kind = event["event"]
 
                if kind == "on_tool_start":
                    print(f"\n TOOL: {event['name']}")
                    print(f"   Input: {event.get('data', {}).get('input', '')}")
 
                elif kind == "on_tool_end":
                    output = event.get("data", {}).get("output", "")
                    print(f"RESULT: {output}")
                    # ── detect error in tool result and set flag ───────────
                    try:
                        parsed = json.loads(output) if isinstance(output, str) else output
                        if isinstance(parsed, dict) and parsed.get("status") == "error":
                            tool_error_detected = True
                            error_msg = parsed.get("message", "Unknown error")
                            response = f"❌ Tool error: {error_msg}\n\nPlease check your input and try again."
                    except (json.JSONDecodeError, AttributeError):
                        pass
 
                elif kind == "on_chat_model_stream":
                    if tool_error_detected:
                        break
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        print(chunk.content, end="", flush=True)
 
                elif kind == "on_chain_end":
                    if tool_error_detected:
                        break
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        msgs = output.get("messages", [])
                        if msgs:
                            response = msgs[-1].content

        except asyncio.CancelledError:
            response = response or "⛔ Stopped by user."

        if not response and not tool_error_detected and not self._abort:
            try:
                result = await self.agent.ainvoke(
                    {"messages": messages},
                    config={"recursion_limit": 3},   # tighter limit to prevent loops
                )
                response = result["messages"][-1].content
            except Exception as e:
                response = f"❌ Agent error: {str(e)}"
 
        self.history.add("user", user_message)
        self.history.add("assistant", response)
 
        return response


    def clear_history(self) -> None:
        self.history.clear()


    def get_tools_info(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description or "No description"}
            for t in self.tools
        ]