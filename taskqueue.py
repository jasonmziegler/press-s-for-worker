import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "tasks.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            think INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            result TEXT
        )
    """)
    # migrate: add think column if missing (existing DBs)
    columns = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "think" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN think INTEGER NOT NULL DEFAULT 1")
    conn.commit()
    return conn

def add_task(task: str, think: bool = True) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (task, think, created_at) VALUES (?, ?, ?)",
        (task, 1 if think else 0, datetime.now().isoformat())
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def claim_next() -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM tasks WHERE status = 'pending' ORDER BY id LIMIT 1"
    ).fetchone()
    if row is None:
        conn.close()
        return None
    conn.execute(
        "UPDATE tasks SET status = 'running', started_at = ? WHERE id = ?",
        (datetime.now().isoformat(), row["id"])
    )
    conn.commit()
    result = dict(row)
    conn.close()
    return result

def complete_task(task_id: int, result: str):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET status = 'done', completed_at = ?, result = ? WHERE id = ?",
        (datetime.now().isoformat(), result, task_id)
    )
    conn.commit()
    conn.close()

def fail_task(task_id: int, error: str):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET status = 'failed', completed_at = ?, result = ? WHERE id = ?",
        (datetime.now().isoformat(), f"ERROR: {error}", task_id)
    )
    conn.commit()
    conn.close()

def reset_running():
    """Reset any tasks stuck as 'running' back to 'pending' (crash recovery)."""
    conn = get_db()
    count = conn.execute(
        "UPDATE tasks SET status = 'pending', started_at = NULL WHERE status = 'running'"
    ).rowcount
    conn.commit()
    conn.close()
    return count

def list_tasks(status: str = None) -> list[dict]:
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result
