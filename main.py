import os
import asyncio
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.mcp_client import MCPClient

load_dotenv()

mcp_client = MCPClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mcp_client.connect()
    yield
    await mcp_client.disconnect()


app = FastAPI(
    title="Docker MCP Client API",
    description="HTTP API that wraps the Docker MCP server via LangChain + Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str                        

class ChatResponse(BaseModel):
    response: str                       
    status: str = "success"

class ToolInfo(BaseModel):
    name: str
    description: str

class ToolsResponse(BaseModel):
    tools: list[ToolInfo]
    count: int


@app.get("/")
async def root():
    return {"status": "running", "message": "Docker MCP Client API is live"}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    return StreamingResponse(
        mcp_client.chat_stream(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   
        }
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        response = await mcp_client.chat(request.message)
        return ChatResponse(response=response, status="success")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.get("/tools", response_model=ToolsResponse)
async def list_tools():
    tools = mcp_client.get_tools_info()
    return ToolsResponse(
        tools=[ToolInfo(**t) for t in tools],
        count=len(tools),
    )


@app.post("/clear")
async def clear_history():
    mcp_client.clear_history()
    return {"status": "success", "message": "Conversation history cleared."}


@app.post("/abort")
async def abort_agent():
    mcp_client.abort()         
    return {"status": "aborted"}