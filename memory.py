import json
import math
import re
import requests
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "tasks.db"
API_URL = "http://localhost:1234/v1"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
LLM_MODEL = "qwen/qwen3-14b"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            source_task_id INTEGER,
            embedding TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def embed(text: str) -> list[float]:
    """Get embedding vector from nomic model."""
    response = requests.post(
        f"{API_URL}/embeddings",
        json={"model": EMBED_MODEL, "input": text},
        timeout=30
    )
    return response.json()["data"][0]["embedding"]

def cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

def store_memory(summary: str, tags: str = "", source_task_id: int = None) -> int:
    """Store a memory with its embedding."""
    embedding = embed(summary)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO memories (summary, tags, source_task_id, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
        (summary, tags, source_task_id, json.dumps(embedding), datetime.now().isoformat())
    )
    conn.commit()
    memory_id = cursor.lastrowid
    conn.close()
    return memory_id

def search_memories(query: str, top_k: int = 5, min_score: float = 0.3) -> list[dict]:
    """Search memories by semantic similarity."""
    query_embedding = embed(query)
    conn = get_db()
    rows = conn.execute("SELECT * FROM memories WHERE embedding IS NOT NULL").fetchall()
    conn.close()

    scored = []
    for row in rows:
        row_dict = dict(row)
        mem_embedding = json.loads(row_dict["embedding"])
        score = cosine_sim(query_embedding, mem_embedding)
        if score >= min_score:
            row_dict["score"] = round(score, 4)
            del row_dict["embedding"]  # don't return the raw vector
            scored.append(row_dict)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

def extract_memories(task: str, result: str) -> list[dict]:
    """Ask the LLM to extract key facts from a completed task."""
    prompt = f"""Extract memories worth keeping from this completed task.

A GOOD memory is:
- A lesson learned from failure (what went wrong and why)
- A design rule or principle discovered (guides future decisions)
- A reasoning breakthrough (WHY something was chosen, not WHAT was built)
- A milestone or major capability gained (not implementation details)

A BAD memory is:
- Implementation details (how open() works, what parameters a function takes)
- Restating what a tool does (the tool already exists in the toolbox)
- Vague generic wisdom ("good design is important")
- Obvious facts ("a file reader reads files")

Return ONLY a JSON array of objects, each with "summary" (one sentence) and "tags" (comma-separated keywords).
Extract 0-2 memories. If nothing is worth remembering, return an empty array [].
No explanation, just the JSON array.

Task: {task}

Result: {result[:2000]}"""

    response = requests.post(
        f"{API_URL}/chat/completions",
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt + " /no_think"}],
            "temperature": 0.3
        },
        timeout=120
    )
    content = response.json()["choices"][0]["message"]["content"]

    # strip thinking tags if present
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # extract JSON array from response
    match = re.search(r'\[.*\]', content, flags=re.DOTALL)
    if not match:
        return []

    try:
        memories = json.loads(match.group())
        return [m for m in memories if isinstance(m, dict) and "summary" in m]
    except json.JSONDecodeError:
        return []

def build_context(task: str, top_k: int = 3) -> str:
    """Search memories and format them as context for a prompt."""
    memories = search_memories(task, top_k=top_k)
    if not memories:
        return ""

    lines = ["Relevant context from previous tasks:"]
    for m in memories:
        lines.append(f"- {m['summary']} (relevance: {m['score']})")
    return "\n".join(lines)

def delete_memory(memory_id: int) -> bool:
    """Delete a memory by ID."""
    conn = get_db()
    row = conn.execute("SELECT id FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()
    return True

def list_memories() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, summary, tags, source_task_id, created_at FROM memories ORDER BY id DESC").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result
