import streamlit as st
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE = f"http://{API_HOST}:{API_PORT}"


st.set_page_config(
    page_title="Docker MCP Client",
    page_icon="🐳",
    layout="wide",
)

if "messages"   not in st.session_state: st.session_state.messages   = []
if "tools"      not in st.session_state: st.session_state.tools      = []
if "is_loading" not in st.session_state: st.session_state.is_loading = False


def check_api_health() -> bool:
    try:
        return httpx.get(f"{API_BASE}/", timeout=3.0).status_code == 200
    except Exception:
        return False


def fetch_tools() -> list[dict]:
    try:
        r = httpx.get(f"{API_BASE}/tools", timeout=5.0)
        return r.json().get("tools", []) if r.status_code == 200 else []
    except Exception:
        return []


def clear_chat():
    st.session_state.messages   = []
    st.session_state.is_loading = False
    try:
        httpx.post(f"{API_BASE}/clear", timeout=5.0)
    except Exception:
        pass


def stop_agent():
    try:
        httpx.post(f"{API_BASE}/abort", timeout=3.0)
    except Exception:
        pass
    st.session_state.is_loading = False


def send_message_stream(message: str):
    try:
        with httpx.stream(
            "POST",
            f"{API_BASE}/chat/stream",
            json={"message": message},
            timeout=120.0,
        ) as response:
            event_type = None
            for line in response.iter_lines():
                line = line.strip()
                if not line:
                    event_type = None
                    continue
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:") and event_type:
                    try:
                        data = json.loads(line[5:].strip())
                        yield {"type": event_type, "data": data}
                    except json.JSONDecodeError:
                        pass
    except httpx.ConnectError:
        yield {"type": "error", "data": {"message": "❌ Cannot connect to API. Is FastAPI running?"}}
    except httpx.TimeoutException:
        yield {"type": "error", "data": {"message": "⏱️ Request timed out."}}
    except Exception as e:
        yield {"type": "error", "data": {"message": f"❌ Error: {str(e)}"}}


def render_tool_result(data: dict, container):
    status = data.get("status", "success")
    title  = data.get("title", "")
    detail = data.get("detail", "")
    table  = data.get("table")   

    if status == "error":
        msg = data.get("message", title or "Unknown error")
        if "Client Error" in msg and '("' in msg:
            try:
                inner = msg.split('("')[1].rstrip('")')
                inner = inner.split('\\\"')[0].strip().rstrip('.')
                msg = f"❌ {inner}"
            except Exception:
                pass
        container.error(msg)
        return

    with container:
        # if title:
        #     st.success(f"✅ {title}")
        # if detail:
        #     st.markdown(detail)
        if table:
            st.dataframe(
                table,
                use_container_width=True,
                hide_index=True,
            )


st.title("🐳 Docker MCP Client")
st.caption("Powered by LangChain + Groq (llama-3.3-70b) + MCP")

with st.sidebar:
    st.header("⚙️ Status")
    api_ok = check_api_health()
    if api_ok:
        st.success("API Connected")
    else:
        st.error("API Offline")
        st.code("uvicorn api.server:app --port 8000", language="bash")

    st.divider()

    if st.button("Refresh Tools", use_container_width=True):
        st.session_state.tools = fetch_tools()

    if not st.session_state.tools and api_ok:
        st.session_state.tools = fetch_tools()

    st.header(" Available Tools")
    if st.session_state.tools:
        container_tools = [t for t in st.session_state.tools if "container" in t["name"]]
        image_tools     = [t for t in st.session_state.tools if "image"     in t["name"]]
        network_tools   = [t for t in st.session_state.tools if "network"   in t["name"]]
        other_tools     = [t for t in st.session_state.tools
                           if t not in container_tools + image_tools + network_tools]

        for group_name, group in [
            ("📦 Containers", container_tools),
            ("🖼️ Images",     image_tools),
            ("🌐 Networks",   network_tools),
            ("🔧 Other",      other_tools),
        ]:
            if group:
                st.caption(group_name)
                for tool in group:
                    with st.expander(f"`{tool['name']}`"):
                        st.write(tool["description"])
    else:
        st.info("No tools loaded yet.")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", use_container_width=True, type="secondary"):
            clear_chat()
            st.rerun()
    with col2:
        if st.session_state.is_loading:
            if st.button("⏹️ Stop", use_container_width=True, type="primary"):
                stop_agent()
                st.session_state.messages.append({
                    "role": "assistant", "content": "⛔ Stopped by user."
                })
                st.rerun()

    st.divider()
    st.header("💡 Try These")
    examples = [
        "Docker version on my machine",
        "List all running containers",
        "Show all containers including stopped",
        "List all local images",
        "Run a hello-world container named test",
        "Stop the container named test",
        "Remove the container named test",
        "List all networks",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.session_state.is_loading = True
            st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content = msg["content"]
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    render_tool_result(block["data"], st.container())
                elif block.get("type") == "text":
                    st.markdown(block["text"])
        else:
            st.markdown(content)

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "👋 Hi! I'm your Docker assistant powered by **Groq + LangChain + MCP**.\n\n"
            "I can help you:\n"
            "- 📋 List / run / stop / remove **containers**\n"
            "- 🖼️ Pull / build / remove **images**\n"
            "- 🌐 Create / remove / connect **networks**\n"
            "- 📄 Generate **Dockerfiles** for your projects\n\n"
            "⚠️ I'll always ask for confirmation before performing destructive actions.\n\n"
            "Make sure **Docker Desktop** is running, then ask me anything!"
        )


def process_stream(user_message: str):
    """
    Stream events from the backend and render them live.
    Returns a list of content blocks for history storage.
    """
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        steps_container      = st.container()
        response_placeholder = st.empty()

        history_blocks = []   # what we'll store in session_state
        final_text     = ""

        for event in send_message_stream(user_message):
            etype = event["type"]
            data  = event["data"]

            # ── Agent is thinking ─────────────────────────────────────────
            if etype == "thinking":
                thinking_placeholder.info("🧠 Agent is thinking...")

            # ── Streaming LLM tokens ──────────────────────────────────────
            elif etype == "token":
                final_text += data.get("text", "")
                response_placeholder.markdown(final_text + "▌")

            # ── Non-destructive tool being called ─────────────────────────
            elif etype == "tool_call":
                thinking_placeholder.info("🧠 Agent is thinking...")
                with steps_container:
                    st.info(f"🔧 **{data['tool']}** — `{json.dumps(data.get('input', {}))}`")

            # ── Destructive tool confirmation prompt ──────────────────────
            elif etype == "confirm":
                thinking_placeholder.empty()
                with steps_container:
                    st.warning(
                        f"⚠️ About to run **{data['tool']}** with "
                        f"`{json.dumps(data.get('input', {}))}`\n\n"
                        "Reply **yes** to confirm or **no** to cancel."
                    )

            # ── Tool result (structured) ──────────────────────────────────
            elif etype == "tool_result":
                thinking_placeholder.empty()
                render_tool_result(data, steps_container)
                # Save for history so it re-renders on rerun
                history_blocks.append({"type": "tool_result", "data": data})

            # ── Final answer ──────────────────────────────────────────────
            elif etype == "done":
                thinking_placeholder.empty()
                final_text = data.get("message", "").strip()
                # Empty = a tool result already told the whole story, nothing to add.
                # Non-empty = either an error explanation or a pure-text LLM reply.
                if final_text:
                    response_placeholder.markdown(final_text)
                    history_blocks.append({"type": "text", "text": final_text})
                else:
                    response_placeholder.empty()

            # ── Hard error ────────────────────────────────────────────────
            elif etype == "error":
                thinking_placeholder.empty()
                msg = data.get("message", "❌ Unknown error")
                response_placeholder.error(msg)
                final_text = msg
                history_blocks.append({"type": "text", "text": msg})

        # If only tokens came through (no tool calls), persist them
        if final_text and not history_blocks:
            history_blocks.append({"type": "text", "text": final_text.strip()})

        return history_blocks


if st.session_state.is_loading and st.session_state.messages:
    last = st.session_state.messages[-1]
    if last["role"] == "user":
        with st.chat_message("user"):
            st.markdown(last["content"])
        blocks = process_stream(last["content"])
        st.session_state.messages.append({"role": "assistant", "content": blocks})
        st.session_state.is_loading = False
        st.rerun()

prompt = st.chat_input(
    "Ask me anything about Docker...",
    disabled=st.session_state.is_loading,
)

if prompt and not st.session_state.is_loading:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.is_loading = True
    blocks = process_stream(prompt)
    st.session_state.messages.append({"role": "assistant", "content": blocks})
    st.session_state.is_loading = False