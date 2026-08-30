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
import os
import shutil
from fastapi import File, UploadFile

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

class UpdatePermissionRequest(BaseModel):
    permission_mode: str

class ApprovalRequest(BaseModel):
    session_id: str
    tool_call_id: str  # 新增此字段
    approved: bool

class SteerRequest(BaseModel):
    session_id: str
    message: str

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

# 确保文件存放目录存在
os.makedirs("uploads", exist_ok=True)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join("uploads", file.filename)
    # 将文件写入本地磁盘
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # 将相对路径返回给前端
    return {"file_path": file_path}

# 【新增】删除指定会话，释放内存
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    database.delete_session_db(session_id)  # 同步删除数据库记录
    return {"status": "ok"}

@app.put("/api/sessions/{session_id}/permission")
def update_permission(session_id: str, req: UpdatePermissionRequest):
    # 1. 更新内存中的状态
    if session_id in sessions:
        sessions[session_id].permission_mode = req.permission_mode
        database.save_session(session_id, req.permission_mode, sessions[session_id].messages)
    # 2. 如果内存中没有（已被回收），直接更新数据库
    else:
        db_record = database.load_session(session_id)
        if db_record:
            _, history = db_record
            database.save_session(session_id, req.permission_mode, history)
    return {"status": "ok"}

@app.post("/api/chat/approve")
def approve_action(req: ApprovalRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 修改：将 tool_call_id 一并传入
    session.resolve_approval(req.tool_call_id, req.approved)
    return {"status": "ok"}

@app.post("/api/chat/steer")
def steer_agent(req: SteerRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 将消息打入该会话的干预队列
    session.inject_steer(req.message)
    return {"status": "ok"}

@app.get("/api/chat/stream")
async def chat_stream(session_id: str, prompt: str, exec_mode: str = "auto", file_path: Optional[str] = None, is_media: bool = False, current_todos: Optional[str] = None):
    if session_id not in sessions:
        db_record = database.load_session(session_id)
        if db_record:
            permission_mode, history_messages = db_record
            sessions[session_id] = CodingAgentSession(
                permission_mode=permission_mode,
                history_messages=history_messages
            )
        else:
            async def error_generator():
                yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在或已失效，请新建会话。'}, ensure_ascii=False)}\n\n"
            return StreamingResponse(error_generator(), media_type="text/event-stream")

    session = sessions[session_id]

    headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
    }

    # ================= 【核心新增：0 Token 本地命令路由拦截】 =================
    if prompt.strip().startswith("/"):
        command = prompt.strip().split()[0].lower()
        
        async def local_command_generator():
            yield f": {' ' * 1024}\n\n"
            # 伪造一个步骤开始事件，让前端展现动画
            yield f"data: {json.dumps({'type': 'step_start', 'step': 1, 'max_steps': 1}, ensure_ascii=False)}\n\n"
            
            # 分发本地命令逻辑
            if command == "/help":
                output = "**本地可用命令 (0 Token API 消耗)**:\n- `/status` : 查看当前 Agent 环境状态\n- `/clear_todo` : 清空右上角任务看板\n- `/remember <内容>` : 写入跨会话全局设定\n- `/clear_memory` : 清空全局设定"
            
            elif command == "/remember":
                # 提取 /remember 后的具体内容
                content = prompt[len("/remember"):].strip()
                if content:
                    # 追加写入到全局记忆文件中
                    with open("MEMORY.md", "a", encoding="utf-8") as f:
                        f.write(f"- {content}\n")
                    output = f"✅ 已将以下设定永久存入全局记忆：\n`{content}`\n\n*(注：基于 Frozen Snapshot 保护机制，新记忆将在下一次新建会话时生效。)*"
                else:
                    output = "⚠️ 请在命令后加上要记住的内容，例如：`/remember 以后写代码都用 TypeScript 并且必须加注释`"
            
            elif command == "/clear_memory":
                if os.path.exists("MEMORY.md"):
                    os.remove("MEMORY.md")
                output = "🗑️ 全局记忆文件已清空。新建会话后彻底生效。"
            elif command == "/status":
                output = (
                    f"**Agent 运行状态探测**:\n"
                    f"- 🪪 **会话 ID**: `{session_id}`\n"
                    f"- 🛡️ **权限模式**: `{session.permission_mode}`\n"
                    f"- 🧠 **记忆深度**: `{len(session.messages)}` 条历史记录"
                )
            elif command == "/clear_todo":
                # 发送结构化事件，直接驱动前端清空看板
                yield f"data: {json.dumps({'type': 'todo_update', 'tasks': []}, ensure_ascii=False)}\n\n"
                output = "✅ 任务看板已在本地重置完毕。"
            else:
                output = f"⚠️ 未知本地命令: `{command}`。输入 `/help` 查看所有可用命令。"

            # 伪造一个后台执行痕迹，维持前端 UI 统一体验
            yield f"data: {json.dumps({'type': 'tool_call', 'name': 'local_command', 'args': {'cmd': command}, 'tool_call_id': 'local'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'tool_output', 'name': 'local_command', 'output': 'Bypassed LLM successfully.', 'tool_call_id': 'local'}, ensure_ascii=False)}\n\n"
            
            # 输出总结并立刻关闭流
            yield f"data: {json.dumps({'type': 'finish', 'content': output}, ensure_ascii=False)}\n\n"

        # 拦截成功，直接返回本地流，绝不调用 OpenAI/DeepSeek 接口！
        return StreamingResponse(local_command_generator(), media_type="text/event-stream", headers=headers)
    # =========================================================================

    # 根据上传文件的性质构造临时提示内容
    file_context = None
    if file_path:
        if is_media:
            file_context = f"用户上传了多媒体素材，物理路径为 `{file_path}`。若生成 Web/游戏，请在 <img> 或 Canvas 中通过 URL `/preview/{file_path}` 加载。"
        else:
            file_context = f"用户向工作区上传了文件，存放路径为 `{file_path}`。若任务涉及该文件，请优先使用工具读取。"

    async def event_generator():
        yield f": {' ' * 1024}\n\n"
        # 将 exec_mode 和 file_context 传入 Agent
        async for event in session.step_stream(prompt, execution_mode=exec_mode, file_context=file_context, current_todos=current_todos):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # 落库保存时，此时 session.messages 里只有纯粹干净的用户对话，零污染！
        database.save_session(session_id, session.permission_mode, session.messages)

    
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