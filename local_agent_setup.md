# Local AI Agent Setup — Conversation Summary
*Handoff document for Claude Code*

---

## Context & Goal

The goal is to build a local AI agent system ("workers") that runs entirely on local hardware — no OpenAI/Claude API credits. The analogy used throughout: **StarCraft worker production**. You need to spawn workers immediately and keep them producing to grow your economy (productivity).

---

## Current Setup

| Component | Detail |
|---|---|
| Local LLM runner | **LM Studio** |
| Available models | `qwen2.5-coder-7b-instruct`, `qwen2.5-coder-3b-instruct`, `google/gemma-3-4b`, `text-embedding-nomic-embed-text-v1.5` |
| LM Studio API | OpenAI-compatible, running on `localhost:1234` |
| OS | Windows 11 |
| Python | 3.14, native Windows install (`C:\Python314\python.exe`) |
| Slack → LLM | Already connected (details TBD) |
| Server status | Confirmed live — `/v1/models` returns 200 |

---

## What Was Accomplished

- Confirmed LM Studio server is running and accessible
- Identified the correct API endpoint: `http://localhost:1234/v1/chat/completions`
- Confirmed four models are loaded and available
- Decided to run everything natively on Windows (no WSL) — simpler networking, `localhost` just works, no file system indirection

---

## The First Worker Script

Saved as `worker.py` in the project directory:

```python
import requests
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path.home() / "agent_output"
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "qwen2.5-coder-7b-instruct"

def run_worker(task: str):
    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": task}],
            "temperature": 0.7
        },
        timeout=120
    )
    result = response.json()["choices"][0]["message"]["content"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"task_{timestamp}.md"
    out_file.write_text(f"# Task\n{task}\n\n# Output\n{result}", encoding="utf-8")
    print(f"Done -> {out_file}")
    return result

if __name__ == "__main__":
    run_worker("List all the things I would need to build a personal AI agent system that runs locally")
```

**To run:**
```bash
python worker.py
```

Output will be saved to `C:\Users\jason\agent_output\task_TIMESTAMP.md`

---

## Recommended Build Order (Next Steps)

### Step 1 — Verify the worker runs (do this first)
Confirm `agent_output/` gets a file written after running `worker.py`.

### Step 2 — Task Queue
Create a simple `tasks.txt` or SQLite DB where tasks are queued. Worker reads next task, processes it, marks it done.

### Step 3 — Project Index
A script that scans `agent_output/` and generates a master `index.md` summarizing all completed tasks and outputs.

### Step 4 — Slack Trigger
Wire the existing Slack → LLM connection so typing a message in Slack feeds directly into the task queue.

### Step 5 — Continuous Loop
A long-running process that polls the task queue and spawns workers automatically — the full mineral-mining loop.

---

## Key Technical Notes

- **No WSL needed**: Everything runs natively on Windows. `localhost:1234` reaches LM Studio directly — no networking hacks required.
- **LM Studio model field**: The `model` field in API calls is ignored by LM Studio; it uses whatever model is currently loaded in the UI
- **Recommended model**: `qwen2.5-coder-7b-instruct` — strong instruction-following, good for structured agent output
- **Output format**: Writing to `.md` files makes outputs human-readable and easy to index later
- **Cost**: Zero API credits — only electricity

---

## Open Questions to Resolve

- What does the current Slack → LLM connection look like exactly? (Is it hitting LM Studio or a separate model?)
- What are the specific projects/domains you want workers to produce output for?
- Should the task queue be file-based (simple) or database-backed (scalable)?
