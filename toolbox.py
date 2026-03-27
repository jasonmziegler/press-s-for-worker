import json
import re
import requests
import sqlite3
from pathlib import Path
from datetime import datetime

TOOLS_DIR = Path(__file__).parent / "tools"
TOOLS_DIR.mkdir(exist_ok=True)
DB_PATH = Path(__file__).parent / "tasks.db"
API_URL = "http://localhost:1234/v1/chat/completions"
LLM_MODEL = "qwen/qwen3-14b"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            filename TEXT NOT NULL,
            source_task_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def extract_code_blocks(text: str) -> list[str]:
    """Pull all Python code blocks from LLM output."""
    pattern = r'```python\s*\n(.*?)```'
    return re.findall(pattern, text, flags=re.DOTALL)

def save_tool(name: str, description: str, code: str, source_task_id: int = None) -> Path:
    """Save a Python script to the tools directory and register it."""
    # clean name for filename
    safe_name = re.sub(r'[^a-z0-9_]', '_', name.lower()).strip('_')
    filename = f"{safe_name}.py"
    filepath = TOOLS_DIR / filename

    filepath.write_text(code, encoding="utf-8")

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO tools (name, description, filename, source_task_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, description, filename, source_task_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return filepath

def list_tools() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM tools ORDER BY id").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

def delete_tool(tool_id: int) -> bool:
    """Delete a tool from the registry and disk."""
    conn = get_db()
    row = conn.execute("SELECT filename FROM tools WHERE id = ?", (tool_id,)).fetchone()
    if not row:
        conn.close()
        return False
    filepath = TOOLS_DIR / row["filename"]
    if filepath.exists():
        filepath.unlink()
    conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
    return True

def get_tools_summary() -> str:
    """Return a summary of available tools for injection into prompts."""
    tools = list_tools()
    if not tools:
        return ""
    lines = ["Available tools in the system:"]
    for t in tools:
        lines.append(f"- {t['name']}: {t['description']} (file: tools/{t['filename']})")
    return "\n".join(lines)

def extract_and_save_tool(task_text: str, result: str, task_id: int) -> dict | None:
    """Ask the LLM if the result contains a saveable tool, and if so, extract and save it."""
    code_blocks = extract_code_blocks(result)
    if not code_blocks:
        return None

    # ask the LLM to identify the tool
    prompt = f"""A task was completed that produced Python code. Determine if this code is a reusable tool/script.

Task: {task_text}

Code blocks found:
{chr(10).join(f'--- Block {i+1} ---{chr(10)}{block}' for i, block in enumerate(code_blocks))}

If this IS a reusable tool, respond with ONLY a JSON object:
{{"is_tool": true, "name": "short_tool_name", "description": "one line description", "best_block": 1}}

If this is NOT a reusable tool (just example code, explanation, etc.), respond with:
{{"is_tool": false}}

Respond with ONLY the JSON. /no_think"""

    response = requests.post(
        API_URL,
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        },
        timeout=60
    )
    content = response.json()["choices"][0]["message"]["content"]
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    match = re.search(r'\{.*\}', content, flags=re.DOTALL)
    if not match:
        return None

    try:
        info = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    if not info.get("is_tool"):
        return None

    block_idx = info.get("best_block", 1) - 1
    if block_idx < 0 or block_idx >= len(code_blocks):
        block_idx = 0

    code = code_blocks[block_idx]
    filepath = save_tool(
        name=info["name"],
        description=info["description"],
        code=code,
        source_task_id=task_id
    )

    return {
        "name": info["name"],
        "description": info["description"],
        "filepath": str(filepath)
    }
