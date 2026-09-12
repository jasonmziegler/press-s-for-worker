import os
import sqlite3
from pathlib import Path
from datetime import datetime

def queue_task(task_description, think="true"):
    """Break work into subtasks by queuing each one for independent execution.

    Use this to decompose complex tasks. Each queued subtask will be picked up
    and executed by a fresh worker with its own tool access. Make subtasks
    self-contained â€” include enough context that a worker can execute without
    knowing about sibling subtasks.

    Args:
        task_description (str): A clear, self-contained action for the worker to execute.
        think (str): Use deep reasoning - "true" or "false". Default "true".
    """
    db_path = Path(__file__).parent.parent / "tasks.db"
    conn = sqlite3.connect(db_path)
    think_val = 1 if think.lower() == "true" else 0
    parent_id = os.environ.get("WORKER_TASK_ID")
    parent_id = int(parent_id) if parent_id else None
    cursor = conn.execute(
        "INSERT INTO tasks (task, think, status, created_at, parent_task_id) VALUES (?, ?, 'pending', ?, ?)",
        (task_description, think_val, datetime.now().isoformat(), parent_id)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return f"Task #{task_id} queued (subtask of #{parent_id}): {task_description[:80]}"