import os
import subprocess
import zipfile
import xml.etree.ElementTree as ET
import uuid
import tempfile

MAX_OUTPUT_LENGTH = 3000  # 单次工具输出最大字符数，防止撑爆上下文 Token

def _save_large_output(content: str, prefix: str = "log") -> str:
    """内部辅助函数：将超长结果落盘到临时目录"""
    os.makedirs("test_code/.logs", exist_ok=True)
    log_name = f"{prefix}_{uuid.uuid4().hex[:8]}.txt"
    log_path = os.path.join("test_code/.logs", log_name)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(content)
    return log_path

def run_command(command: str, **kwargs) -> str:
    """在本地系统执行终端命令，包含超时控制、UTF-8强制容错与长输出截断"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        
        # 退出码非 0 时的自愈引导
        if result.returncode != 0:
            err_output = result.stderr if result.stderr else result.stdout
            err_output = err_output.strip() if err_output else "Process exited with code != 0 without explicit error."
            return (
                f"[COMMAND FAILED - Exit Code: {result.returncode}]\n"
                f"ERROR OUTPUT:\n{err_output}\n\n"
                f"💡 [Self-Healing Suggestion]: Inspect the error trace above. If it's a syntax/import error, "
                f"use 'read_file' to locate the issue, modify via 'edit_file' or 'write_file', and rerun the command to verify."
            )

        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR (Non-fatal warnings):\n{result.stderr}\n"
        
        output = output.strip() if output.strip() else "Command executed successfully with no output."
        
        # 核心改造：L3 大结果落盘机制
        if len(output) > MAX_OUTPUT_LENGTH:
            # 完整输出落盘本地
            log_path = _save_large_output(output, "cmd")
            
            # 返回给模型的截断视图带上本地路径指引
            head = output[:1500]
            tail = output[-1500:]
            output = (
                f"{head}\n\n"
                f"... [Output truncated due to length (Total {len(output)} chars)]. \n"
                f"💡 [L3 Spilling]: The full log has been written to '{log_path}'. \n"
                f"If you need to inspect the hidden middle parts (like deep stack traces), use 'read_file' on this log path. ...\n\n"
                f"{tail}"
            )
            
        return output
    except subprocess.TimeoutExpired:
        return (
            "Error: Command timed out after 30 seconds.\n"
            "💡 [Self-Healing Suggestion]: The command likely hung waiting for interactive input (e.g. input(), scanf()) "
            "or an infinite loop. Avoid interactive commands or pass arguments directly (e.g., echo '...' | python)."
        )
    except Exception as e:
        return f"Error executing command: {str(e)}\n💡 [Self-Healing Suggestion]: Check command syntax and binary path."

def list_dir(path: str = ".", **kwargs) -> str:
    """列出指定目录下的文件和文件夹结构，帮助定位项目文件"""
    try:
        if not os.path.exists(path):
            return (
                f"Error: Path '{path}' does not exist.\n"
                f"💡 [Self-Healing Suggestion]: Call 'list_dir(path=\".\")' to check available project folders from root."
            )
        items = []
        for root, dirs, files in os.walk(path):
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
    """读取文件内容，原生支持纯文本与 Word (.docx) 文档的解析"""
    try:
        if os.path.basename(path) == ".env":
            return "Error: Access to .env file is restricted for security. Please do not attempt to inspect credentials."
        
        if not os.path.exists(path):
            return (
                f"Error: File '{path}' does not exist.\n"
                f"💡 [Self-Healing Suggestion]: Use 'list_dir' to verify the exact file path and directory structure."
            )
            
        ext = os.path.splitext(path)[1].lower()
        
        # 针对 Word (.docx) 文档解析
        if ext == ".docx":
            try:
                with zipfile.ZipFile(path) as docx:
                    xml_content = docx.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                paragraphs = []
                for p in tree.findall('.//w:p', namespaces=ns):
                    texts = [t.text for t in p.findall('.//w:t', namespaces=ns) if t.text]
                    if texts:
                        paragraphs.append("".join(texts))
                content = "\n".join(paragraphs)
                lines = content.split('\n')
                return "".join([f"{i+1:4d} | {line}\n" for i, line in enumerate(lines)])
            except zipfile.BadZipFile:
                return (
                    f"Error: '{path}' is not a valid or readable .docx file.\n"
                    f"💡 [Self-Healing Suggestion]: If this is an older binary Word file (.doc), it is not supported. "
                    f"Ask the user or convert it to a plain text format."
                )

        # 针对纯文本读取
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
        
    except UnicodeDecodeError:
        return (
            f"Error: '{path}' appears to be a binary file or uses an unsupported non-UTF-8 encoding.\n"
            f"💡 [Self-Healing Suggestion]: Inspect the file type. Only source code and text documents should be read."
        )
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def write_file(path: str, content: str, **kwargs) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        # 临时文件 + 原子替换，防止中途断电损坏原文件
        dir_name = os.path.dirname(os.path.abspath(path))
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            tf.write(content)
            tf.flush()
            os.fsync(tf.fileno()) # 确保刷入磁盘
            temp_path = tf.name
        os.replace(temp_path, path) # 操作系统级原子覆盖
        return f"File '{path}' written successfully."
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"

def edit_file(path: str, old_snippet: str, new_snippet: str, **kwargs) -> str:
    """通过精准替换旧代码片段来修改文件，无需全量重写"""
    try:
        if not os.path.exists(path):
            return (
                f"Error: File '{path}' does not exist.\n"
                f"💡 [Self-Healing Suggestion]: Use 'write_file' if you want to create a new file, or check path with 'list_dir'."
            )
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_snippet not in content:
            return (
                f"Error: Target 'old_snippet' not found in '{path}'.\n"
                f"💡 [Self-Healing Suggestion]: Call 'read_file' with exact line numbers on '{path}' first! "
                f"Make sure indentation, blank lines, and whitespace in 'old_snippet' match the existing file verbatim."
            )

        count = content.count(old_snippet)
        if count > 1:
            return (
                f"Error: Target 'old_snippet' appears {count} times in '{path}'. Ambiguous replacement.\n"
                f"💡 [Self-Healing Suggestion]: Expand your 'old_snippet' to include more preceding or following context lines "
                f"so that it matches exactly ONE unique occurrence in the file."
            )

        new_content = content.replace(old_snippet, new_snippet, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"File '{path}' edited successfully."
    except Exception as e:
        return f"Error editing file '{path}': {str(e)}"

def update_todo(tasks: list, **kwargs) -> str:
    """更新任务看板（工具本身只返回成功确认，实际渲染由 SSE 拦截处理）"""
    return "Task list updated successfully. User can now see the progress."

# 元数据保持不变
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
            "description": "Read file content with line numbers. Supports plain text files (.txt, .py, .md) and Word documents (.docx).",
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
    },
    {
        "type": "function",
        "function": {
            "name": "update_todo",
            "description": "Create or update a global Task/Todo checklist. Call this BEFORE starting complex tasks to plan, and call it again to update status as you finish steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "e.g., '1', '2'"},
                                "title": {"type": "string", "description": "Task description"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                            },
                            "required": ["id", "title", "status"]
                        }
                    }
                },
                "required": ["tasks"]
            }
        }
    }
]

AVAILABLE_TOOLS = {
    "run_command": run_command,
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "update_todo": update_todo
}