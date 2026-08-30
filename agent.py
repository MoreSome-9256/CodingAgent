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
1. [TASK PLANNING] For new complex tasks, call 'update_todo' to create a checklist. If a checklist already exists in the context, DO NOT create a new one from scratch; instead, continue updating the existing tasks' statuses.
2. Explore existing files or run tests to understand the current state if needed.
3. Edit or create files in the appropriate directory.
4. [MANDATORY TRACKING] Call 'update_todo' again to mark tasks as 'in_progress' or 'completed' as you work.
5. Always verify your changes by executing commands if applicable.
6. [MANDATORY TERMINATION] When all tasks are completed and verified, you MUST output a comprehensive final summary and STOP calling any more tools. Do not endlessly inspect files.

- For HTML/Web UI projects, once the file is written, DO NOT attempt to extract scripts or verify DOM elements using Node.js or shell commands. Just output the final summary and let the user test it via the browser.

Language Requirement:
- Always reply and summarize in Chinese (Simplified Chinese) by default.
"""

# 定义并发安全工具集（只读操作，支持多任务无锁并发）
PARALLEL_SAFE_TOOLS = {"list_dir", "read_file"}

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
        
        # ================= 【核心新增：读取全局记忆冻结快照】 =================
        global_memory = ""
        if os.path.exists("MEMORY.md"):
            with open("MEMORY.md", "r", encoding="utf-8") as f:
                global_memory = f.read().strip()
                
        # 将全局记忆拼接到 SYSTEM_PROMPT 尾部
        final_system_prompt = SYSTEM_PROMPT
        if global_memory:
            final_system_prompt += f"\n\n【全局用户个性化设定】:\n{global_memory}"
            
        # 初始化 messages：如果有历史则继承，否则使用注入了快照的 System Prompt
        self.messages = history_messages if history_messages else [{"role": "system", "content": final_system_prompt}]
        # ===================================================================
        
        self.pending_approvals = {}  # 保持上一轮方案B的字典逻辑不变
        self.steer_queue = []

    def inject_steer(self, message: str):
        """外部接口：向当前正在运行的会话注入纠偏指令"""
        self.steer_queue.append(message)

    def resolve_approval(self, tool_call_id: str, approved: bool):
        """用户在前端点击允许或拒绝时调用，精准唤醒对应的工具调用"""
        future = self.pending_approvals.get(tool_call_id)
        if future and not future.done():
            future.set_result(approved)

    # def _compress_context(self):
    #     """
    #     四层廉价优先上下文压缩管线 (滑动窗口 + 0 Token 损耗占位符)
    #     保护头部 (System Prompt) 和尾部 (最新 6 条记录)，对中间过期的冗长记录进行无损状态裁切。
    #     """
    #     # 只有当历史消息列表超过一定长度时才触发，避免过早压缩
    #     if len(self.messages) <= 12:
    #         return
            
    #     # 尾部保护窗口：始终保留最近的 6 条消息完整无缺，保证当前步骤的推理连贯性
    #     safe_tail_length = 6
        
    #     # 遍历从第 1 条（跳过索引 0 的 system prompt）到尾部保护窗口之前的所有历史消息
    #     for i in range(1, len(self.messages) - safe_tail_length):
    #         msg = self.messages[i]
            
    #         # L2 压缩：针对历史工具调用的超长输出
    #         if msg.get("role") == "tool":
    #             content = msg.get("content", "")
    #             if len(content) > 300:
    #                 # 保留前 150 字符（通常包含状态码或首行报错），和后 50 字符（通常包含总结或异常尾部）
    #                 # 中间替换为明确的占位符，告知大模型该内容它之前已经看过了
    #                 head = content[:150]
    #                 tail = content[-50:]
    #                 msg["content"] = (
    #                     f"{head}\n\n"
    #                     f"... [L2 Compression: Large output truncated to save context window. "
    #                     f"Content previously inspected successfully.] ...\n\n"
    #                     f"{tail}"
    #                 )
            
    #         # L1 压缩：针对大模型过去轮次中产生的冗长思维链/解释文本
    #         elif msg.get("role") == "assistant" and msg.get("content"):
    #             content = msg["content"]
    #             if len(content) > 400:
    #                 # 历史思考过程不再重要，保留前 100 字作为上下文锚点即可
    #                 msg["content"] = content[:100] + "\n... [L1 Compression: Previous reasoning truncated] ..."

    # -------------------- 插入新的类方法 --------------------
    async def _run_tool_async(self, func_name: str, func_args: dict) -> str:
        """利用线程池安全地异步执行工具，避免 IO 阻塞主事件循环"""
        tool_func = AVAILABLE_TOOLS.get(func_name)
        if not tool_func:
            return f"Error: Tool '{func_name}' does not exist."
        try:
            # 将同步的物理文件读写操作丢入 asyncio 底层线程池执行，实现真并发
            return await asyncio.to_thread(tool_func, **func_args)
        except TypeError as e:
            return f"Tool Argument Mismatch: {str(e)}.\n💡 [Self-Healing Suggestion]: Inspect parameter schema."
        except Exception as e:
            return f"Tool Internal Unexpected Error: {str(e)}.\n💡 [Self-Healing Suggestion]: Try an alternative strategy."

    async def step_stream(self, user_prompt: str, execution_mode: str = "auto", file_context: str = None, current_todos: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        # 底层真实的持久化上下文：只保存用户原始输入与真实工具返回，100%零污染
        self.messages.append({"role": "user", "content": user_prompt})
        step_count = 0

        while step_count < self.max_steps:
            step_count += 1
            yield {"type": "step_start", "step": step_count, "max_steps": self.max_steps}

            # ================= 【核心：安全点 Steer 拦截】 =================
            if self.steer_queue:
                # 提取并清空当前队列
                steer_msgs = list(self.steer_queue)
                self.steer_queue.clear()
                
                for sm in steer_msgs:
                    # 组装为高优先级的用户指令，原子落盘写入真实上下文
                    steer_content = f"【用户即时干预 (Steering)】: {sm}\n请立即根据上述指示调整你的后续行动计划。"
                    self.messages.append({"role": "user", "content": steer_content})
                    # 向前端广播干预已生效的信号
                    yield {"type": "steer_applied", "content": sm}
            # ===============================================================

            # ----------------- 【核心：非破坏性压缩与临时视图构建】 -----------------
            messages_view = []
            safe_tail_length = 6
            total_msgs = len(self.messages)
            
            # 1. 动态生成带 L1/L2 压缩的浅拷贝视图
            for i, msg_raw in enumerate(self.messages):
                # 浅拷贝字典，修改 msg["content"] 绝不会影响 self.messages 里的原对象
                msg = dict(msg_raw)
                
                # 仅当历史总长度超过12，且当前条目属于“中间过期轮次”时，实施压缩
                if total_msgs > 12 and 0 < i < total_msgs - safe_tail_length:
                    if msg.get("role") == "tool":
                        content = msg.get("content", "")
                        if len(content) > 300:
                            # L2 压缩：旧工具结果占位
                            msg["content"] = f"{content[:150]}\n\n... [L2 Compression: Content previously inspected successfully.] ...\n\n{content[-50:]}"
                    elif msg.get("role") == "assistant" and msg.get("content"):
                        content = msg["content"]
                        if len(content) > 400:
                            # L1 压缩：旧思维链裁切
                            msg["content"] = content[:100] + "\n... [L1 Compression: Previous reasoning truncated] ..."
                
                messages_view.append(msg)
            
            # 2. 构造临时系统约束（注入视图末尾，绝不落盘）
            ephemeral_instructions = []
            if file_context:
                ephemeral_instructions.append(file_context)
            
            is_empty_todo = not current_todos or current_todos.strip() in ["", "[]", "{}"]
            
            if execution_mode == "plan":
                if is_empty_todo:
                    ephemeral_instructions.append(
                        "【🚨 强制指令 - 计划制定阶段】：你当前处于引导计划模式！\n"
                        "你的唯一任务是：调用 `update_todo` 工具列出拆解步骤，然后**必须立刻停止调用任何其他工具**，直接输出一段文本询问用户是否同意该计划。\n"
                        "严禁在本轮对话中调用 `write_file`, `edit_file`, `run_command`！"
                    )
                else:
                    ephemeral_instructions.append(
                        "【引导计划模式 - 执行阶段】：任务看板已就绪。请根据用户的最新反馈，严格按照计划步骤开始执行。\n"
                        "执行过程中，请务必持续调用 `update_todo` 推进对应任务的状态（pending -> in_progress -> completed）。"
                    )
            
            # 【修复冗余】：仅保留此一处记忆注入，防止重复下发
            if not is_empty_todo:
                ephemeral_instructions.append(
                    f"【当前任务看板状态】：\n{current_todos}\n"
                    "请注意：你之前已经制定了上述任务计划，请依据此计划继续往下执行（例如完成下一个 pending 的任务）。"
                    "调用 update_todo 时，请保留已有任务的 id 和 title，仅更新 status，切勿直接清空原计划。"
                )
            
            # 临时拼接指令到最后一条 user 消息
            if ephemeral_instructions:
                combined_ephemeral = "\n\n".join(ephemeral_instructions)
                last_msg = messages_view[-1]
                if last_msg.get("role") == "user":
                    last_msg["content"] = f"{last_msg['content']}\n\n(临时环境提示:\n{combined_ephemeral})"
            # -------------------------------------------------------------

            # 2. 发起 API 请求时，传入的是 messages_view 而不是 self.messages
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages_view,  # 使用隔离视图
                        tools=TOOLS_SCHEMA,
                        tool_choice="auto",
                        timeout=45.0
                    )
                    break  # 成功则跳出重试循环
                except Exception as e:
                    if attempt < max_retries - 1:
                        # 向前端抛出系统级的重试警告，不记入上下文
                        yield {"type": "tool_output", "name": "system", "output": f"Network warning: {str(e)}. Retrying {attempt+1}/{max_retries}...", "tool_call_id": "sys"}
                        await asyncio.sleep(2)
                    else:
                        yield {"type": "error", "message": f"API Request Failed after {max_retries} attempts: {str(e)}"}
                        return  # 【核心修改】：直接 return 退出生成器，不再往下执行赋值

            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                yield {"type": "finish", "content": message.content}
                break

            # ----------------- 【核心：并发分流与严格保序回填】 -----------------
            # 预分配占位数组，确保无论执行先后顺序如何，最终落盘严格保序
            tool_outputs = [None] * len(message.tool_calls)
            parallel_tasks = []

            for i, tool_call in enumerate(message.tool_calls):
                func_name = tool_call.function.name
                
                # 1. 解析参数
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except Exception as json_err:
                    output = f"Error: Failed to parse arguments as valid JSON: {str(json_err)}"
                    tool_outputs[i] = (tool_call.id, func_name, output)
                    yield {"type": "tool_output", "name": func_name, "output": output, "tool_call_id": tool_call.id}
                    continue

                # 2. 权限拦截 (若需审批，则挂起等待用户操作)
                if self.permission_mode == "ask" and func_name in SENSITIVE_TOOLS:
                    yield {"type": "approval_required", "name": func_name, "args": func_args, "tool_call_id": tool_call.id}
                    
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    self.pending_approvals[tool_call.id] = future
                    is_approved = await future
                    self.pending_approvals.pop(tool_call.id, None)

                    if not is_approved:
                        output = f"Permission Denied: User explicitly rejected {func_name}."
                        tool_outputs[i] = (tool_call.id, func_name, output)
                        yield {"type": "tool_output", "name": func_name, "output": output, "tool_call_id": tool_call.id}
                        continue

                # 3. 拦截特定工具向前端单独发信号 (如 Todo 看板)
                yield {"type": "tool_call", "name": func_name, "args": func_args, "tool_call_id": tool_call.id}
                if func_name == "update_todo":
                    yield {"type": "todo_update", "tasks": func_args.get("tasks", [])}

                # 4. 智能调度：并发入池 vs 屏障串行
                if func_name in PARALLEL_SAFE_TOOLS:
                    # 并发安全：创建后台异步任务并加入缓冲池
                    task = asyncio.create_task(self._run_tool_async(func_name, func_args))
                    parallel_tasks.append((i, tool_call.id, func_name, task))
                else:
                    # 遇到非并发工具（写操作）：触发内存屏障！必须先等之前的并发任务全部完成
                    if parallel_tasks:
                        results = await asyncio.gather(*(t[3] for t in parallel_tasks))
                        for (p_idx, p_id, p_name, _), res in zip(parallel_tasks, results):
                            tool_outputs[p_idx] = (p_id, p_name, res)
                            yield {"type": "tool_output", "name": p_name, "output": res, "tool_call_id": p_id}
                        parallel_tasks.clear()
                    
                    # 随后，独立且安全地串行执行当前敏感写操作
                    output = await self._run_tool_async(func_name, func_args)
                    tool_outputs[i] = (tool_call.id, func_name, output)
                    yield {"type": "tool_output", "name": func_name, "output": output, "tool_call_id": tool_call.id}

            # 5. 清理收尾：处理最后剩余的并发任务
            if parallel_tasks:
                results = await asyncio.gather(*(t[3] for t in parallel_tasks))
                for (p_idx, p_id, p_name, _), res in zip(parallel_tasks, results):
                    tool_outputs[p_idx] = (p_id, p_name, res)
                    yield {"type": "tool_output", "name": p_name, "output": res, "tool_call_id": p_id}

            # 6. 一次性严格保序回填至上下文 (Zero-Pollution)
            for item in tool_outputs:
                if item:
                    t_id, f_name, out_text = item
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": t_id,
                        "content": str(out_text)
                    })
            
            # ====== 新增：硬性物理阻断 ======
            # 如果是引导计划模式的第一轮，且刚刚调用了 update_todo 生成计划，必须强行刹车！
            if execution_mode == "plan" and is_empty_todo:
                if any(t.function.name == "update_todo" for t in message.tool_calls):
                    # 把大模型附带生成的大纲文本（message.content）推给前端，然后直接打断循环
                    yield_content = message.content if message.content else "任务计划清单已生成，请在右上角看板查看。若无异议，请回复“同意”以开始执行代码编写。"
                    yield {"type": "finish", "content": yield_content}
                    break
        else:
            yield {"type": "finish", "content": "Reached maximum iteration limit."}