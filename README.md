# press-s-for-worker

A local-first AI agent built from scratch to learn how coding agents actually work —
the task loop, tool calling, memory, and the harness around the model — running
entirely on local hardware with no cloud API credits.

The name comes from StarCraft: you press **S** to build a worker, and a good economy
never stops producing them. The project was planned as an RTS build order, one
structure at a time (see [`build_order.md`](build_order.md)).

## How it works

```
 add_task.py / dashboard ──► Queue (SQLite) ──► Worker loop
                                                   │
                        ┌──────────────────────────┤
                        ▼                          ▼
                 Vault (memory)             Forge (tool registry)
                 embeddings search          tools/*.py + schemas
                        │                          │
                        └──────► Cortex ◄──────────┘
                                   │  tool-calling loop against
                                   ▼  a local LLM (LM Studio)
                         result → output file + new memories
```

| Component | File | What it does |
|---|---|---|
| **Queue** | `taskqueue.py` | SQLite task queue with pending/running/done states, crash recovery, and parent/child tasks |
| **Worker** | `worker.py` | Polls the queue, builds context, runs the Cortex, saves output, and extracts memories |
| **Cortex** | `cortex.py` | The agent loop: lets the model call tools mid-task and feeds results back, with a round limit |
| **Vault** | `memory.py` | Long-term memory: stores summaries with embeddings (`nomic-embed-text`) and retrieves relevant ones by cosine similarity |
| **Forge** | `toolbox.py` | Tool factory: extracts Python code the model writes and registers it as a new tool |
| **Tools** | `tools/` | `read_file`, `write_file`, `edit_file`, `list_files`, `run_script`, `queue_task` |
| **Dashboard** | `dashboard.py` | Flask web UI to add tasks and inspect the queue, memories, and tools |

### Design decisions worth noting

- **Grounded memory only.** Memories are extracted only from tasks that used tools,
  read source files, or produced code — so the agent doesn't memorize its own guesses.
- **No fork bombs.** A task with several independent parts can split itself into
  subtasks with `queue_task`, but subtasks can't split further.
- **Read before write.** Core rules injected into every task require the agent to read
  a file before modifying it. That rule exists because the agent truncated
  `dashboard.py` twice by rewriting it from memory.
- **Context budget.** Tool results are truncated at 8,000 characters, so source files
  the agent maintains are kept under that limit.
- **Think / Fast modes.** Tasks can use full reasoning or `/no_think` for quick jobs.

## Running it

Requirements: Python 3.10+, [LM Studio](https://lmstudio.ai) serving on `localhost:1234`
with a chat model (built with `qwen/qwen3-14b`) and `text-embedding-nomic-embed-text-v1.5`.

```bash
pip install flask requests

python worker.py                              # start the worker loop
python dashboard.py                           # web UI at http://127.0.0.1:5000
python add_task.py "List the files in tools/" # queue a task (add --fast to skip reasoning)
```

Outputs are written to `~/agent_output/`.

## Status

Queue, worker loop, memory, and tool-calling Cortex are working. Next up
(per the build order): multi-step planning, a Slack input channel, web access, and
self-evaluation. RTS-to-platform vocabulary lives in [`terminology.md`](terminology.md).
