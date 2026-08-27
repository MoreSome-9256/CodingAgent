import json
import os
from typing import Generator, Dict, Any
from openai import OpenAI
from tools import TOOLS_SCHEMA, AVAILABLE_TOOLS

SYSTEM_PROMPT = """You are an autonomous software engineering assistant.
Your goal is to solve the user's programming request completely.
You have local tools to read/write/edit files, list directory contents, and execute shell commands.

Workflow:
1. Explore existing files or run tests to understand current state if needed.
2. Edit or create files.
3. Always verify your changes by executing commands (e.g. run tests or scripts).
4. When everything is verified and working, provide a comprehensive final response to the user containing:
   - Summary of actions taken and files created/modified (with exact paths).
   - The actual code blocks written/edited so the user can review directly.
   - Verification and test results.

Language Requirement:
- Always reply and summarize in Chinese (Simplified Chinese) by default, unless the user explicitly requests another language. Code comments, variable names, and technical identifiers should follow standard engineering conventions.
"""

class CodingAgentSession:
    def __init__(self, api_key: str = None, base_url: str = None, model_name: str = None, max_steps: int = 15):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model_name = model_name or os.getenv("MODEL_NAME", "deepseek-chat")
        self.max_steps = max_steps
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _compress_context(self):
        if len(self.messages) <= 20:
            return
        for i in range(2, len(self.messages) - 6):
            msg = self.messages[i]
            if isinstance(msg, dict) and msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > 200:
                    msg["content"] = content[:100] + "\n... [Earlier tool output pruned] ..."

    def step_stream(self, user_prompt: str) -> Generator[Dict[str, Any], None, None]:
        self.messages.append({"role": "user", "content": user_prompt})
        step_count = 0

        while step_count < self.max_steps:
            step_count += 1
            yield {"type": "step_start", "step": step_count, "max_steps": self.max_steps}

            self._compress_context()

            try:
                response = self.client.chat.completions.create(
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

            # 1. 任务完成，无工具调用
            if not message.tool_calls:
                yield {"type": "finish", "content": message.content}
                break

            # 2. 执行工具调用
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

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