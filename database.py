import sqlite3
import json
import os

DB_PATH = "agent_sessions.db"

def init_db():
    """初始化数据库表结构"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                permission_mode TEXT,
                context_messages TEXT
            )
        """)

def save_session(session_id: str, permission_mode: str, messages: list):
    """保存或更新会话状态（利用 REPLACE INTO 实现有则更新，无则插入）"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO sessions (id, permission_mode, context_messages) VALUES (?, ?, ?)",
            (session_id, permission_mode, json.dumps(messages, ensure_ascii=False))
        )

def load_session(session_id: str):
    """从数据库加载会话上下文"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT permission_mode, context_messages FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return row[0], json.loads(row[1])
        return None

def delete_session_db(session_id: str):
    """删除指定的会话"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))