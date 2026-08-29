import json
import os
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from openai import AsyncOpenAI
from tools import TOOLS_SCHEMA, AVAILABLE_TOOLS

SYSTEM_PROMPT = """You are an autonomous software engineering assistant.
Your goal is to solve the user's programming request completely.
You have local tools to read/write/edit files, list directory contents, execute shell commands, and manage a Todo list.

File Storage & Workspace Rules:
- Unless the user explicitly specifies a different directory or file path, ALWAYS place newly created code and test files under the 'test_code/' directory (e.g., 'test_code/solution.py', 'test_code/snake.html').
- If the user asks for interactive apps, games, UI tools, or visual programs, prefer creating a standalone, self-contained HTML file (including CSS & JavaScript) under 'test_code/' so it can be previewed directly.

Workflow:
1. [MANDATORY INITIALIZATION] ALWAYS call the 'update_todo' tool FIRST to break down complex tasks into a structured checklist.
2. Explore existing files or run tests to understand the current state if needed.
3. Edit or create files in the appropriate directory.
4. [MANDATORY TRACKING] Call 'update_todo' again to mark tasks as 'in_progress' or 'completed' as you work.
5. Always verify your changes by executing commands if applicable.
6. [MANDATORY TERMINATION] When all tasks are completed and verified, you MUST output a comprehensive final summary and STOP calling any more tools. Do not endlessly inspect files.

Language Requirement:
- Always reply and summarize in Chinese (Simplified Chinese) by default.
"""

# 定义需要用户显式批准的敏感工具（写操作）
SENSITIVE_TOOLS = {"write_file", "edit_file"}

class CodingAgentSession:
    def __init__(self, api_key: str = None, base_url: str = None, model_name: str = None, max_steps: int = 15, permission_mode: str = "full", history_messages: list = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model_name = model_name or os.getenv("MODEL_NAME", "deepseek-chat")
        self.max_steps = max_steps
        self.permission_mode = permission_mode
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 核心修改：如果有历史记忆则继承，否则使用初始 System Prompt
        self.messages = history_messages if history_messages else [{"role": "system", "content": SYSTEM_PROMPT}]
        
        self.pending_approvals = {}  # 保持上一轮方案B的字典逻辑不变

    def resolve_approval(self, tool_call_id: str, approved: bool):
        """用户在前端点击允许或拒绝时调用，精准唤醒对应的工具调用"""
        future = self.pending_approvals.get(tool_call_id)
        if future and not future.done():
            future.set_result(approved)

    def _compress_context(self):
        """
        四层廉价优先上下文压缩管线 (滑动窗口 + 0 Token 损耗占位符)
        保护头部 (System Prompt) 和尾部 (最新 6 条记录)，对中间过期的冗长记录进行无损状态裁切。
        """
        # 只有当历史消息列表超过一定长度时才触发，避免过早压缩
        if len(self.messages) <= 12:
            return
            
        # 尾部保护窗口：始终保留最近的 6 条消息完整无缺，保证当前步骤的推理连贯性
        safe_tail_length = 6
        
        # 遍历从第 1 条（跳过索引 0 的 system prompt）到尾部保护窗口之前的所有历史消息
        for i in range(1, len(self.messages) - safe_tail_length):
            msg = self.messages[i]
            
            # L2 压缩：针对历史工具调用的超长输出
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > 300:
                    # 保留前 150 字符（通常包含状态码或首行报错），和后 50 字符（通常包含总结或异常尾部）
                    # 中间替换为明确的占位符，告知大模型该内容它之前已经看过了
                    head = content[:150]
                    tail = content[-50:]
                    msg["content"] = (
                        f"{head}\n\n"
                        f"... [L2 Compression: Large output truncated to save context window. "
                        f"Content previously inspected successfully.] ...\n\n"
                        f"{tail}"
                    )
            
            # L1 压缩：针对大模型过去轮次中产生的冗长思维链/解释文本
            elif msg.get("role") == "assistant" and msg.get("content"):
                content = msg["content"]
                if len(content) > 400:
                    # 历史思考过程不再重要，保留前 100 字作为上下文锚点即可
                    msg["content"] = content[:100] + "\n... [L1 Compression: Previous reasoning truncated] ..."

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
            self.messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                yield {"type": "finish", "content": message.content}
                break

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                
                # 1. 防御参数 JSON 反序列化崩溃
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except Exception as json_err:
                    output = (
                        f"Error: Failed to parse tool arguments as valid JSON: {str(json_err)}.\n"
                        f"Raw Arguments: '{tool_call.function.arguments}'\n"
                        f"💡 [Self-Healing Suggestion]: Retry the tool call with strictly valid JSON format."
                    )
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": output
                    })
                    yield {
                        "type": "tool_output",
                        "name": func_name,
                        "output": output,
                        "tool_call_id": tool_call.id
                    }
                    continue

                # 2. 权限校验（ask 模式且敏感操作）
                if self.permission_mode == "ask" and func_name in SENSITIVE_TOOLS:
                    yield {
                        "type": "approval_required",
                        "name": func_name,
                        "args": func_args,
                        "tool_call_id": tool_call.id
                    }
                    
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    self.pending_approvals[tool_call.id] = future
                    
                    is_approved = await future
                    self.pending_approvals.pop(tool_call.id, None)

                    if not is_approved:
                        output = (
                            f"Permission Denied: The user explicitly rejected the execution of {func_name}.\n"
                            f"💡 [Self-Healing Suggestion]: Explain to the user why this action was needed, "
                            f"or propose an alternative approach without modifying this specific file."
                        )
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

                # 3. 正常执行工具并启动 Never-Throw 外层保护网
                yield {
                    "type": "tool_call",
                    "name": func_name,
                    "args": func_args,
                    "tool_call_id": tool_call.id
                }

                # 【新增拦截】：如果是待办更新工具，直接向前端下发结构化数据
                if func_name == "update_todo":
                    yield {
                        "type": "todo_update",
                        "tasks": func_args.get("tasks", [])
                    }

                tool_func = AVAILABLE_TOOLS.get(func_name)
                if tool_func:
                    try:
                        output = tool_func(**func_args)
                    except TypeError as e:
                        output = (
                            f"Tool Argument Mismatch: {str(e)}.\n"
                            f"💡 [Self-Healing Suggestion]: Inspect the parameter schema for '{func_name}' and provide the correct argument names."
                        )
                    except Exception as e:
                        # 极端防御：即使底层有任何未处理的运行时错误，绝不上抛打崩循环
                        output = (
                            f"Tool Internal Unexpected Error: {str(e)}.\n"
                            f"💡 [Self-Healing Suggestion]: Do not repeat the exact same call. Try an alternative strategy."
                        )
                else:
                    output = (
                        f"Error: Tool '{func_name}' does not exist.\n"
                        f"💡 [Self-Healing Suggestion]: Choose from available tools: {list(AVAILABLE_TOOLS.keys())}."
                    )

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