import os
import subprocess

def run_command(command: str) -> str:
    """在本地系统执行终端命令并返回输出结果"""
    try:
        # 设置 30 秒超时，防止类似无限循环的脚本卡死 Agent
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output.strip() if output.strip() else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def read_file(path: str) -> str:
    """读取文件内容并附带行号，方便模型定位代码"""
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """创建或覆盖写入文件"""
    try:
        # 如果文件所在的文件夹不存在，则自动创建
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{path}' written successfully."
    except Exception as e:
        return f"Error writing file: {str(e)}"

# 提供给大模型的工具描述书（Tool Schema）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the local environment (e.g., compile code, run tests).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Text content to write"}
                },
                "required": ["path", "content"]
            }
        }
    }
]

# 用于代码内部调用的函数映射字典
AVAILABLE_TOOLS = {
    "run_command": run_command,
    "read_file": read_file,
    "write_file": write_file
}