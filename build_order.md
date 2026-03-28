# Build Order — Local AI Agent System
*StarCraft II Terran analogy. Every step builds on the last. No skipping.*

---

## The Map

| SC2 Concept | System Equivalent |
|---|---|
| Command Center | The kernel — core loop that receives, routes, executes, stores |
| SCVs | Workers — LLM calls that produce output |
| Minerals / Gas | Compute — VRAM, CPU, tokens/sec |
| Supply Depots | Memory system — without it you get supply blocked (every task starts from zero) |
| Barracks | Tool factory — produces new capabilities (scripts, functions) |
| Orbital Command | Kernel upgrade — adds scanning (memory retrieval) and MULEs (burst tasks) |
| Expand (2nd CC) | New input channels — Slack, file watchers, web |
| Engineering Bay | Self-improvement — agent evaluates its own output quality |

---

## Current State — 0:00 Game Loaded

- Command Center placed = LM Studio running
- First SCV produced = `worker.py` confirmed working
- Map scouted = hardware benchmarked, model selected (Qwen3 14B running, 118-148 tok/s)
- LM Studio config: 4 parallel slots, 32K total context (8K per slot), unified KV cache

---

## Phase 1 — Economy (get income flowing) [**Complete**]

The mineral line. Boring but load-bearing. Everything else is funded by this.

| # | SC2 | System | Why first |
|---|---|---|---|
| 1 | SCV → mineral line | **Task queue** — `tasks.db` with SQLite | Workers need something to mine. No queue = idle workers. |
| 2 | SCV → SCV → SCV | **Worker loop** — auto-pull, execute, store, repeat | One-shot workers are useless. The loop is the mineral line. |
| 3 | Supply Depot | **Memory system** — store + retrieve past outputs | Without this, every task starts from zero. You'll supply-block yourself fast. |

**Phase 1 complete when:** Tasks go in, workers pull them automatically, results are stored, and the system remembers what it's done.

---

## Phase 2 — Military (create power) [**In Progress**]

The system stops being a script and starts being an agent.

| # | SC2 | System | Why now |
|---|---|---|---|
| 4 | Barracks | **Tool factory** — agent writes and saves new Python scripts as reusable tools | First offensive capability. The system can now extend itself. |
| 5 | Orbital Command | **Orchestrator upgrade** — kernel reads a task, checks memory, picks (or creates) the right tool, plans multi-step tasks | The moment the system becomes an agent. |

**Phase 2 complete when:** The system can receive a complex task, remember context, break it down, pick or build the right tool, and execute.

---

## Phase 3 — Expand (scale income)

More bases = more income. Open new input channels.

| # | SC2 | System | Why now |
|---|---|---|---|
| 6 | 2nd CC (Natural) | **Slack trigger** — new input channel, tasks flow in from outside | More income = more bases. First expansion. |
| 7 | Refineries | **File system + web tools** — agent can read local files, fetch URLs | Gas income. Unlocks higher-tier capabilities. |

**Phase 3 complete when:** Tasks arrive from multiple sources and the agent can reach outside itself for information.

---

## Phase 4 — Late Game (compound advantage)

Upgrades, specialization, and fortification.

| # | SC2 | System | Why now |
|---|---|---|---|
| 8 | Engineering Bay | **Self-evaluation** — agent scores its own output, refines prompts | Upgrades make every unit more efficient. |
| 9 | Starport | **Specialized workers** — different worker types for different task categories | Air units = capabilities manual work can't match. |
| 10 | Planetary Fortress | **Persistence + reliability** — auto-restart, error recovery, logging, **single launcher** (dashboard + worker bundled into one start command) | Fortify what you've built so it runs unattended. |

**Phase 4 complete when:** The system runs autonomously, improves itself, and recovers from errors without intervention.

---

## The Rule

> You don't build Barracks before you have workers mining. You don't expand before your main base economy is saturated. Every build order mistake in SC2 comes from building something cool before building what's needed.

Phase 1 is the mineral-saturated main base that funds everything else. No skipping.

---

## Design Constraints

- **8K character file limit** — The Cortex truncates tool results at 8,000 characters. Any source file the system needs to read and modify must stay under this limit. If a file grows past 8K, split it into smaller modules. This is not optional — the system literally cannot see past the cutoff, and `write_file` on a file it can't fully read causes data loss (proven by dashboard.py being truncated twice).

---

## Backlog (add when the time is right)

- **Task priority** — urgent tasks jump the queue. Add a `priority` column to tasks table, sort by priority then id. Needed once task volume grows.
- **Parallel workers** — LM Studio supports 4 parallel slots (8K context each). Could run up to 4 workers simultaneously. Tradeoff: speed vs. context length per task.
- **Start/restart from browser** — launch and manage worker + dashboard processes from the web UI. Belongs in Phase 4 (Planetary Fortress) with the single launcher.
- **Dashboard smart refresh** — instead of replacing the entire task list every 3s (which resets scroll position), diff the data and only patch changed elements. Finishing detail for the dashboard.