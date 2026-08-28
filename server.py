import json
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import CodingAgentSession
import database
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse

load_dotenv()

# 初始化数据库表
database.init_db()

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
    agent_session = CodingAgentSession(
        api_key=req.api_key,
        base_url=req.base_url,
        model_name=req.model_name,
        permission_mode=req.permission_mode
    )
    sessions[session_id] = agent_session
    
    # 新建时立刻存入数据库，保留初始上下文
    database.save_session(session_id, agent_session.permission_mode, agent_session.messages)
    return {"session_id": session_id}

# 【新增】删除指定会话，释放内存
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    database.delete_session_db(session_id)  # 同步删除数据库记录
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
    # 核心拦截逻辑：如果内存中没有，尝试从数据库唤醒
    if session_id not in sessions:
        db_record = database.load_session(session_id)
        if db_record:
            permission_mode, history_messages = db_record
            sessions[session_id] = CodingAgentSession(
                permission_mode=permission_mode,
                history_messages=history_messages
            )
        else:
            # 数据库里也没有，说明是彻底丢失或非法的 ID
            async def error_generator():
                yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在或已失效，请新建会话。'}, ensure_ascii=False)}\n\n"
            return StreamingResponse(error_generator(), media_type="text/event-stream")

    session = sessions[session_id]

    async def event_generator():
        yield f": {' ' * 1024}\n\n"
        async for event in session.step_stream(prompt):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # 流式输出完全结束（包含压缩上下文逻辑执行完毕）后，将最新的记忆落库更新
        database.save_session(session_id, session.permission_mode, session.messages)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

# 【新增】供前端 iframe 直接运行本地生成的 HTML/Web 项目
@app.get("/preview/{file_path:path}")
def preview_file(file_path: str):
    import os
    # 拼接本地真实路径
    target_path = os.path.abspath(file_path)
    if not os.path.exists(target_path):
        # 兼容只传文件名的情况，自动去 test_code/ 下找
        fallback_path = os.path.abspath(os.path.join("test_code", file_path))
        if os.path.exists(fallback_path):
            target_path = fallback_path
        else:
            raise HTTPException(status_code=404, detail="Preview file not found")
    
    return FileResponse(target_path)

@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)