import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from taskqueue import claim_next, complete_task, fail_task, reset_running
from memory import build_context, extract_memories, store_memory
from toolbox import extract_and_save_tool, get_tools_summary
from cortex import run_cortex

OUTPUT_DIR = Path.home() / "agent_output"
OUTPUT_DIR.mkdir(exist_ok=True)

POLL_INTERVAL = 2  # seconds between queue checks

shutting_down = False
current_task_id = None

def shutdown(sig, frame):
    global shutting_down
    if shutting_down:
        print("\nForce quit.")
        sys.exit(1)
    shutting_down = True
    if current_task_id:
        print(f"\nShutting down after task #{current_task_id} finishes...")
    else:
        print("\nShutting down...")
        sys.exit(0)

signal.signal(signal.SIGINT, shutdown)

def save_output(task_id: int, task: str, result: str, context: str = "") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"task_{task_id}_{timestamp}.md"
    parts = [f"# Task #{task_id}", task]
    if context:
        parts.append(f"\n# Context Injected\n{context}")
    parts.append(f"\n# Output\n{result}")
    out_file.write_text("\n".join(parts), encoding="utf-8")
    return out_file

def run_loop():
    global current_task_id

    # recover any tasks stuck as 'running' from a previous crash
    recovered = reset_running()
    if recovered:
        print(f"Recovered {recovered} stuck task(s) back to pending.")

    print(f"Worker online. Cortex enabled.")
    print(f"Output: {OUTPUT_DIR}")
    print("Press Ctrl+C to shut down gracefully.")
    print()

    while not shutting_down:
        task = claim_next()
        if task is None:
            time.sleep(POLL_INTERVAL)
            continue

        current_task_id = task["id"]
        task_text = task["task"]
        think = bool(task.get("think", 1))
        mode = "think" if think else "fast"

        # core behavioral rules — always injected, not subject to retrieval
        preamble = (
            "Core rules (always apply):\n"
            "- You are a worker, not an advisor. If you find a problem you can fix, fix it. Deliver solutions, not just diagnoses.\n"
            "- Before reviewing, evaluating, or modifying any code, read the actual source file first using your tools. The source file is the only truth.\n"
            "- When building or fixing a tool, write the complete Python code in a ```python code block in your response. The Forge extracts it automatically.\n"
            "- Never rewrite a file from memory. Read it first, then modify. Skipping this causes regressions."
        )

        # search memory and tools for relevant context
        context_parts = [preamble]
        mem_context = build_context(task_text)
        if mem_context:
            context_parts.append(mem_context)
            print(f"[#{current_task_id}] [{mode}] Memory hit - injecting context")
        tools_context = get_tools_summary()
        if tools_context:
            context_parts.append(tools_context)
            print(f"[#{current_task_id}] [{mode}] Tools available - injecting inventory")
        context = "\n\n".join(context_parts)
        print(f"[#{current_task_id}] [{mode}] Processing: {task_text[:80]}...")

        try:
            result = run_cortex(task_text, think=think, context=context)
            out_file = save_output(current_task_id, task_text, result, context)
            complete_task(current_task_id, result)
            print(f"[#{current_task_id}] Done -> {out_file}")

            # only extract memories from grounded tasks (used tools or produced code)
            used_tools = "[Cortex: used" in result
            produced_code = "```python" in result
            if used_tools or produced_code:
                memories = extract_memories(task_text, result)
                for mem in memories:
                    mid = store_memory(
                        summary=mem["summary"],
                        tags=mem.get("tags", ""),
                        source_task_id=current_task_id
                    )
                    print(f"[#{current_task_id}] Memory stored: #{mid} {mem['summary'][:60]}")
            else:
                print(f"[#{current_task_id}] Skipping memory extraction (no tools used, no code produced)")

            # check if the output contains a saveable tool
            tool = extract_and_save_tool(task_text, result, current_task_id)
            if tool:
                print(f"[#{current_task_id}] Tool saved: {tool['name']} -> {tool['filepath']}")

        except Exception as e:
            fail_task(current_task_id, str(e))
            print(f"[#{current_task_id}] FAILED: {e}")

        current_task_id = None
        print()

    print("Worker shut down cleanly.")

if __name__ == "__main__":
    run_loop()
