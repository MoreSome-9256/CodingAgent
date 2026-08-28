import json
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import CodingAgentSession

load_dotenv()

app = FastAPI(title="Autonomous Coding Agent UI")

sessions: Dict[str, CodingAgentSession] = {}

class CreateSessionRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    permission_mode: Optional[str] = "full"  # "full" 或 "ask"

class ApprovalRequest(BaseModel):
    session_id: str
    tool_call_id: str  # 新增此字段
    approved: bool

@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = CodingAgentSession(
        api_key=req.api_key,
        base_url=req.base_url,
        model_name=req.model_name,
        permission_mode=req.permission_mode
    )
    return {"session_id": session_id}

# 【新增】删除指定会话，释放内存
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "ok"}

@app.post("/api/chat/approve")
def approve_action(req: ApprovalRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 修改：将 tool_call_id 一并传入
    session.resolve_approval(req.tool_call_id, req.approved)
    return {"status": "ok"}

@app.get("/api/chat/stream")
async def chat_stream(session_id: str, prompt: str):
    if session_id not in sessions:
        sessions[session_id] = CodingAgentSession()
    session = sessions[session_id]

    async def event_generator():
        yield f": {' ' * 1024}\n\n"
        async for event in session.step_stream(prompt):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)