import json
import uuid
from typing import Dict, Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import CodingAgentSession

load_dotenv()

app = FastAPI(title="Autonomous Coding Agent UI")

# 内存会话存储
sessions: Dict[str, CodingAgentSession] = {}

class CreateSessionRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None

@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = CodingAgentSession(
        api_key=req.api_key,
        base_url=req.base_url,
        model_name=req.model_name
    )
    return {"session_id": session_id}

@app.get("/api/chat/stream")
def chat_stream(session_id: str, prompt: str):
    if session_id not in sessions:
        sessions[session_id] = CodingAgentSession()
    session = sessions[session_id]

    def event_generator():
        # [核心修复] 发送一个 1KB 的不可见注释包，瞬间填满浏览器的初始缓冲区，强制它立刻开始处理后续事件
        yield f": {' ' * 1024}\n\n"
        
        for event in session.step_stream(prompt):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    # [核心修复] 添加强制去缓存、关闭代理缓冲的 Headers
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # 告诉所有中间网关不要缓冲
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    # 增加 log_level="warning" 来屏蔽普通的 INFO 级别请求日志
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")