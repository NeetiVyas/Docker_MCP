import streamlit as st
import httpx
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

if "messages" not in st.session_state:
    st.session_state.messages = []
if "tools" not in st.session_state:
    st.session_state.tools = []
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False


def fetch_tools() -> list[dict]:
    try:
        response = httpx.get(f"{API_BASE}/tools", timeout=5.0)
        if response.status_code == 200:
            return response.json().get("tools", [])
    except Exception:
        pass
    return []


def send_message(message: str) -> str:
    try:
        response = httpx.post(
            f"{API_BASE}/chat",
            json={"message": message},
            timeout=120.0,
        )
        if response.status_code == 200:
            return response.json().get("response", "No response.")
        else:
            return f"API error {response.status_code}: {response.text}"
    except httpx.ConnectError:
        return "❌ Could not connect to the API. Make sure FastAPI is running on port 8000."
    except httpx.TimeoutException:
        return "⏱️ Request timed out. The operation may still be running."
    except Exception as e:
        return f"❌ Error: {str(e)}"


def stop_agent() -> None:
    try:
        httpx.post(f"{API_BASE}/abort", timeout=3.0)
    except Exception:
        pass
    st.session_state.is_loading = False


def clear_chat():
    st.session_state.messages = []
    st.session_state.is_loading = False
    try:
        httpx.post(f"{API_BASE}/clear", timeout=5.0)
    except Exception:
        pass


def check_api_health() -> bool:
    try:
        response = httpx.get(f"{API_BASE}/", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False


st.title("🐳 Docker MCP Client")
st.caption("Powered by LangChain + Groq + MCP")

with st.sidebar:
    st.header("⚙️ Status")

    api_ok = check_api_health()
    if api_ok:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Offline")
        st.info("Start the API with:\n```\nuvicorn api.server:app --port 8000\n```")

    st.divider()

    if st.button("🔄 Refresh Tools", use_container_width=True):
        st.session_state.tools = fetch_tools()

    if not st.session_state.tools and api_ok:
        st.session_state.tools = fetch_tools()

    st.header("🛠️ Available Tools")
    if st.session_state.tools:
        for tool in st.session_state.tools:
            with st.expander(f"🔧 {tool['name']}"):
                st.write(tool["description"])
    else:
        st.info("No tools loaded yet.")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True, type="secondary"):
        clear_chat()
        st.rerun()

    st.divider()

    if st.session_state.is_loading:
        if st.button("⏹️ Stop Agent", type="primary", use_container_width=True):
            stop_agent()
            st.session_state.messages.append({
                "role": "assistant",
                "content": "⛔ Stopped by user.",
            })
            st.rerun()

    st.header("💡 Try These")
    examples = [
        "List all running containers",
        "Show all containers including stopped",
        "Run an nginx container named test-server",
        "Stop the container named test-server",
        "Create a Dockerfile for D:/my-project",
    ]
    for example in examples:
        if st.button(example, use_container_width=True, key=example):
            st.session_state.messages.append({"role": "user", "content": example})
            st.session_state.is_loading = True
            st.rerun()


# ── Chat messages ────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "👋 Hi! I'm your Docker assistant. I can help you:\n"
            "- 📋 **List** running containers\n"
            "- ▶️ **Run** containers from images\n"
            "- ⏹️ **Stop / Remove** containers by name or ID\n"
            "- 🔄 **Restart** containers by name or ID\n"
            "- 🌐 **Manage networks**\n"
            "- 📄 **Create** Dockerfiles for your projects\n\n"
            "Make sure Docker Desktop is running, then ask me anything!"
        )

# ── Handle loading state (e.g. triggered by sidebar example buttons) ─────────
if st.session_state.is_loading and st.session_state.messages:
    last = st.session_state.messages[-1]
    if last["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                response = send_message(last["content"])
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
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

    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            response = send_message(prompt)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.is_loading = False
