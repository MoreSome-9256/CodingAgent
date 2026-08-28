import os
import subprocess

MAX_OUTPUT_LENGTH = 3000  # 单次工具输出最大字符数，防止撑爆上下文 Token

def run_command(command: str, **kwargs) -> str:
    """在本地系统执行终端命令，包含超时控制与长输出自动截断"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",    # 强制以 UTF-8 解码命令行输出
            errors="replace",    # 核心防御：遇到无法解码的乱码字符直接替换为问号，绝不抛出异常让程序崩溃
            timeout=30
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        
        output = output.strip() if output.strip() else "Command executed with no output."
        
        # 保护机制：如果输出过长，保留首尾关键信息，中间截断
        if len(output) > MAX_OUTPUT_LENGTH:
            head = output[:1500]
            tail = output[-1500:]
            output = f"{head}\n\n... [Output truncated due to length, showing first and last 1500 chars] ...\n\n{tail}"
            
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def list_dir(path: str = ".", **kwargs) -> str:
    """列出指定目录下的文件和文件夹结构，帮助定位项目文件"""
    try:
        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."
        items = []
        for root, dirs, files in os.walk(path):
            # 过滤掉不需要让大模型看的隐藏目录和虚拟环境
            dirs[:] = [d for d in dirs if d not in [".venv", "__pycache__", ".git", ".pytest_cache"]]
            level = root.replace(path, "").count(os.sep)
            indent = " " * 4 * level
            items.append(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 4 * (level + 1)
            for f in files:
                items.append(f"{subindent}{f}")
        return "\n".join(items) if items else "Directory is empty."
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def read_file(path: str, **kwargs) -> str:
    """读取文件内容并附带行号"""
    try:
        # 安全防护：禁止模型直接读取 .env 避免泄露 Key
        if os.path.basename(path) == ".env":
            return "Error: Access to .env file is restricted for security."
        
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str, **kwargs) -> str:
    """新建或全量覆写文件"""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{path}' written successfully."
    except Exception as e:
        return f"Error writing file: {str(e)}"

def edit_file(path: str, old_snippet: str, new_snippet: str, **kwargs) -> str:
    """通过精准替换旧代码片段来修改文件，无需全量重写"""
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_snippet not in content:
            return f"Error: Target snippet not found in '{path}'. Please read the file first to ensure exact match."

        count = content.count(old_snippet)
        if count > 1:
            return f"Error: Target snippet appears {count} times in '{path}'. Provide a more specific/longer code block to ensure unique replacement."

        new_content = content.replace(old_snippet, new_snippet, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"File '{path}' edited successfully."
    except Exception as e:
        return f"Error editing file: {str(e)}"

# 工具元数据定义
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command locally (e.g. running tests, scripts, compilers).",
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
            "name": "list_dir",
            "description": "List all files and directories in a directory tree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to list, default is '.'"}
                }
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
            "description": "Create a new file or completely overwrite an existing file with content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Text content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Precisely replace an exact code block with a new code block in an existing file. Read the file before editing to ensure exact match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "old_snippet": {"type": "string", "description": "The exact existing code block to replace"},
                    "new_snippet": {"type": "string", "description": "The new replacement code block"}
                },
                "required": ["path", "old_snippet", "new_snippet"]
            }
        }
    }
]

AVAILABLE_TOOLS = {
    "run_command": run_command,
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file
}