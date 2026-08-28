import json
import os
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from openai import AsyncOpenAI
from tools import TOOLS_SCHEMA, AVAILABLE_TOOLS

SYSTEM_PROMPT = """You are an autonomous software engineering assistant.
Your goal is to solve the user's programming request completely.
You have local tools to read/write/edit files, list directory contents, and execute shell commands.

File Storage & Workspace Rules:
- Unless the user explicitly specifies a different directory or file path, ALWAYS place newly created code and test files under the 'test_code/' directory (e.g., 'test_code/solution.py', 'test_code/test_solution.py').
- If the user explicitly provides a custom path (e.g., 'src/utils.py' or 'output/app.py'), strictly follow the user's specified path.

Workflow:
1. Explore existing files or run tests to understand current state if needed.
2. Edit or create files in the appropriate directory.
3. Always verify your changes by executing commands (e.g. run 'pytest test_code/test_xxx.py' or scripts).
4. When everything is verified and working, provide a comprehensive final response to the user containing:
   - Summary of actions taken and files created/modified (with exact paths).
   - The actual code blocks written/edited so the user can review directly.
   - Verification and test results.

Language Requirement:
- Always reply and summarize in Chinese (Simplified Chinese) by default, unless the user explicitly requests another language. Code comments, variable names, and technical identifiers should follow standard engineering conventions.
"""

# 定义需要用户显式批准的敏感工具（写操作）
SENSITIVE_TOOLS = {"write_file", "edit_file"}

class CodingAgentSession:
    def __init__(self, api_key: str = None, base_url: str = None, model_name: str = None, max_steps: int = 15, permission_mode: str = "full"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model_name = model_name or os.getenv("MODEL_NAME", "deepseek-chat")
        self.max_steps = max_steps
        self.permission_mode = permission_mode
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # 新增：用于精准匹配 tool_call_id 的等待机制
        self.pending_approvals: Dict[str, asyncio.Future] = {}

    def resolve_approval(self, tool_call_id: str, approved: bool):
        """用户在前端点击允许或拒绝时调用，精准唤醒对应的工具调用"""
        future = self.pending_approvals.get(tool_call_id)
        if future and not future.done():
            future.set_result(approved)

    def _compress_context(self):
        if len(self.messages) <= 20:
            return
        for i in range(2, len(self.messages) - 6):
            msg = self.messages[i]
            if isinstance(msg, dict) and msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > 200:
                    msg["content"] = content[:100] + "\n... [Earlier tool output pruned] ..."

    async def step_stream(self, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        self.messages.append({"role": "user", "content": user_prompt})
        step_count = 0

        while step_count < self.max_steps:
            step_count += 1
            yield {"type": "step_start", "step": step_count, "max_steps": self.max_steps}

            self._compress_context()

            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto"
                )
            except Exception as e:
                yield {"type": "error", "message": f"API Request Failed: {str(e)}"}
                break

            message = response.choices[0].message
            self.messages.append(message)

            if not message.tool_calls:
                yield {"type": "finish", "content": message.content}
                break

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                # 权限校验：如果处于 "ask" 模式且调用了敏感写工具
                if self.permission_mode == "ask" and func_name in SENSITIVE_TOOLS:
                    yield {
                        "type": "approval_required",
                        "name": func_name,
                        "args": func_args,
                        "tool_call_id": tool_call.id
                    }
                    
                    # 使用 Future 挂起等待特定 tool_call_id 的用户确认
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    self.pending_approvals[tool_call.id] = future
                    
                    is_approved = await future
                    
                    # 确认完毕后从字典中清理
                    self.pending_approvals.pop(tool_call.id, None)

                    if not is_approved:
                        # 用户拒绝
                        output = f"Permission Denied: User rejected the execution of {func_name}."
                        yield {
                            "type": "tool_output",
                            "name": func_name,
                            "output": output,
                            "tool_call_id": tool_call.id
                        }
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": output
                        })
                        continue

                # 正常执行工具
                yield {
                    "type": "tool_call",
                    "name": func_name,
                    "args": func_args,
                    "tool_call_id": tool_call.id
                }

                tool_func = AVAILABLE_TOOLS.get(func_name)
                if tool_func:
                    output = tool_func(**func_args)
                else:
                    output = f"Error: Tool {func_name} not found."

                yield {
                    "type": "tool_output",
                    "name": func_name,
                    "output": str(output),
                    "tool_call_id": tool_call.id
                }

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(output)
                })
        else:
            yield {"type": "finish", "content": "Reached maximum iteration limit."}