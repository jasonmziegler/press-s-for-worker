# Terminology — press-s-for-worker

Our internal planning uses RTS strategy concepts. This file maps those to
the platform's own vocabulary for public-facing use (code, UI, docs, README).

---

## Core Terms

| RTS Concept | Platform Term | Description |
|---|---|---|
| Command Center / Base | **Kernel** | The core system — receives, routes, executes, stores |
| Workers / SCVs | **Workers** | LLM task runners that produce output |
| Minerals / Gas | **Compute** | Hardware resources — VRAM, CPU, tokens/sec |
| Build Order | **Playbook** | The sequenced plan for what to build and when |

## Phases & Structures

| RTS Concept | Platform Term | Description |
|---|---|---|
| Mineral Line | **Queue** | Task queue — the income pipeline |
| Supply Depot | **Vault** | Memory system — stores and retrieves knowledge |
| Barracks | **Forge** | Tool factory — where new capabilities are built |
| Orbital Command | **Cortex** | Orchestrator upgrade — agent loop with tool execution |
| Expansion / 2nd Base | **Channel** | New input source — Slack, file watchers, web hooks |
| Refineries | **Reach** | External access tools — file system, web, APIs |
| Engineering Bay | **Optimizer** | Self-evaluation — agent scores and refines its own output |
| Starport | **Fleet** | Specialized worker types for different task categories |
| Planetary Fortress | **Watchtower** | Persistence layer — auto-restart, error recovery, single launcher |

## Task Modes

| RTS Concept | Platform Term | Description |
|---|---|---|
| Full army micro | **Think** | Deep reasoning mode — LLM uses chain of thought |
| A-move | **Fast** | Quick mode — `/no_think`, skip reasoning for simple tasks |

## Misc

| RTS Concept | Platform Term | Description |
|---|---|---|
| Scouting | **Probe** | Exploring the system, benchmarking, discovery |
| Tech tree | **Capability map** | The full set of tools and skills the system has |
| Supply blocked | **Memory blocked** | System can't grow because it has no context from past work |
| GG | **Ship it** | Done. Push to prod. |

---

## Usage

- **Internal docs** (`build_order.md`, planning conversations): RTS terms are fine
- **Code** (variable names, function names, module names): Use platform terms
- **UI** (dashboard labels, status messages): Use platform terms
- **Public docs** (README, GitHub description): Use platform terms
