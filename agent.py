import json
import os
from openai import OpenAI
from tools import TOOLS_SCHEMA, AVAILABLE_TOOLS

# 提示词：引导模型像资深工程师一样思考，并遵循 ReAct 范式
SYSTEM_PROMPT = """You are an autonomous software engineering assistant.
Your goal is to solve the user's programming request completely.
You have local tools to read/write files and execute shell commands.

Workflow:
1. Explore existing files or run tests to understand current state if needed.
2. Edit or create files.
3. Always verify your changes by executing commands (e.g. run tests or scripts).
4. Only reply to the user with a final summary when you have confirmed everything works.
"""

class CodingAgent:
    def __init__(self, model_name: str = None, max_steps: int = 15):
        # 读取 .env 中配置的凭据与网关
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.model_name = model_name or os.getenv("MODEL_NAME", "deepseek-chat")
        self.max_steps = max_steps
        # 初始化会话历史
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def step(self, user_prompt: str):
        # 记录用户任务
        self.messages.append({"role": "user", "content": user_prompt})
        step_count = 0

        while step_count < self.max_steps:
            step_count += 1
            print(f"\n==================== [Iteration {step_count}/{self.max_steps}] ====================")

            # 1. 携带历史记录和工具列表请求 LLM
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto"
            )

            message = response.choices[0].message
            # 将模型的回复（可能包含 tool_calls）追加进上下文
            self.messages.append(message)

            # 2. 如果模型没有发起工具调用，说明任务已经完成或无需调工具，输出总结后退出
            if not message.tool_calls:
                print(f"\n[Agent Finished]\n{message.content}")
                break

            # 3. 如果模型要求调用工具，在本地逐一执行并回传
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                print(f"\n[Tool Call] {func_name}")
                print(f"Args: {json.dumps(func_args, ensure_ascii=False, indent=2)}")

                tool_func = AVAILABLE_TOOLS.get(func_name)
                if tool_func:
                    output = tool_func(**func_args)
                else:
                    output = f"Error: Tool {func_name} not found."

                print(f"[Tool Output]\n{output}")

                # 将执行结果以 tool 角色追加到 messages 中，供下一轮思考使用
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(output)
                })
        else:
            print("\n[Agent Stopped] Reached maximum iteration limit.")