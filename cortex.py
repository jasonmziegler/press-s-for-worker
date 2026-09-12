"""
Cortex — the execution loop for press-s-for-worker.

Enables the LLM to call tools mid-task and receive results back,
turning a single-shot text generator into an agent that can act.
"""

import importlib.util
import inspect
import json
import re
import requests
import sqlite3
from pathlib import Path

API_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen/qwen3-14b"
TOOLS_DIR = Path(__file__).parent / "tools"
DB_PATH = Path(__file__).parent / "tasks.db"
MAX_TOOL_ROUNDS = 10  # safety limit to prevent infinite loops

def _registered_tool_files() -> set[str]:
    """Return the set of filenames registered in the toolbox DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT filename FROM tools").fetchall()
        conn.close()
        return {r[0] for r in rows}
    except Exception:
        return set()

def load_tools() -> dict:
    """Load only DB-registered tools from the tools/ directory.
    Returns a dict mapping function_name -> {function, schema}."""
    registered = _registered_tool_files()
    tools = {}
    for py_file in TOOLS_DIR.glob("*.py"):
        if py_file.name not in registered:
            continue  # skip unregistered files — they are not tools
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            continue

        # find all public functions in the module
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            # build OpenAI-style function schema from signature + docstring
            sig = inspect.signature(func)
            doc = func.__doc__ or ""
            # parse "Args:" section from docstring for param descriptions
            param_docs = {}
            if "Args:" in doc:
                args_section = doc.split("Args:")[1].split("Returns:")[0]
                for line in args_section.strip().splitlines():
                    line = line.strip()
                    if ":" in line:
                        pname, pdesc = line.split(":", 1)
                        pname = pname.strip().split("(")[0].strip()
                        param_docs[pname] = pdesc.strip()

            properties = {}
            required = []
            for param_name, param in sig.parameters.items():
                desc = param_docs.get(param_name, param_name)
                prop = {"type": "string", "description": desc}
                if param.default is not inspect.Parameter.empty:
                    prop["default"] = str(param.default)
                else:
                    required.append(param_name)
                properties[param_name] = prop

            tools[name] = {
                "function": func,
                "schema": {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": (func.__doc__ or "").strip().split("\n")[0],
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required
                        }
                    }
                }
            }
    return tools

def execute_tool(tools: dict, name: str, arguments: dict) -> str:
    """Execute a tool by name with the given arguments."""
    if name not in tools:
        return f"ERROR: Unknown tool '{name}'"
    try:
        result = tools[name]["function"](**arguments)
        if result is None:
            return "Done (no output)."
        return str(result)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

def plan_reads(task_prompt: str) -> tuple[list[str], str]:
    """Ask the LLM what files it needs to read before starting a task.
    Returns (list of file paths read, formatted file contents string)."""
    plan_prompt = (
        "Before starting this task, what files do you need to read to do it correctly? "
        "Return ONLY a JSON array of file paths relative to the project root. "
        'Example: ["tools/run_script.py", "worker.py"]\n'
        "Return [] if no files need to be read.\n\n"
        f"Task:\n{task_prompt}"
    )

    try:
        response = requests.post(
            API_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": plan_prompt + " /no_think"}],
                "temperature": 0.3
            },
            timeout=60
        )
        content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        return [], ""

    # strip thinking tags if present
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # extract JSON array from response
    match = re.search(r'\[.*?\]', content, flags=re.DOTALL)
    if not match:
        return [], ""

    try:
        file_paths = json.loads(match.group())
    except json.JSONDecodeError:
        return [], ""

    if not file_paths or not isinstance(file_paths, list):
        return [], ""

    # read up to 5 files, respect truncation limit
    PROJECT_ROOT = Path(__file__).parent
    MAX_FILES = 5
    sections = []
    read_paths = []

    for path_str in file_paths[:MAX_FILES]:
        if not isinstance(path_str, str):
            continue
        full_path = PROJECT_ROOT / path_str
        if not full_path.exists() or not full_path.is_file():
            continue
        try:
            text = full_path.read_text(encoding="utf-8")
            if len(text) > 8000:
                text = text[:8000] + "\n... (truncated)"
            sections.append(f"--- {path_str} ---\n{text}")
            read_paths.append(path_str)
        except Exception:
            continue

    if not sections:
        return [], ""

    header = "Pre-read source files:\n"
    return read_paths, header + "\n\n".join(sections)


def run_cortex(task: str, think: bool = True, context: str = "", exclude_tools: list = None) -> str:
    """Run the Cortex execution loop for a single task.

    Returns the final text response from the LLM after all tool calls
    have been resolved.
    """
    tools = load_tools()
    if exclude_tools:
        for name in exclude_tools:
            tools.pop(name, None)
    tool_schemas = [t["schema"] for t in tools.values()]

    # build initial prompt
    if context:
        full_prompt = f"{context}\n\n{task}"
    else:
        full_prompt = task

    # planning step: ask model what files to read, then read them
    read_paths, pre_read_content = plan_reads(full_prompt)
    if pre_read_content:
        full_prompt = f"{full_prompt}\n\n{pre_read_content}"
        print(f"    [plan] Pre-read {len(read_paths)} file(s): {', '.join(read_paths)}")

    if not think:
        full_prompt += " /no_think"

    messages = [
        {"role": "system", "content": (
            "You are an agent that completes tasks by using tools. "
            "If the task has multiple independent parts, use queue_task to queue each part separately, then stop. "
            "Otherwise, use tools directly to complete the work. "
            "After each tool result, decide if more steps are needed. "
            "Do not simulate or imagine results — use your tools to get real data."
        )},
        {"role": "user", "content": full_prompt}
    ]

    tool_log = []

    for round_num in range(MAX_TOOL_ROUNDS):
        # build request
        request_body = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7
        }
        if tool_schemas:
            request_body["tools"] = tool_schemas
            request_body["tool_choice"] = "auto"

        response = requests.post(API_URL, json=request_body, timeout=300)
        result = response.json()
        choice = result["choices"][0]
        message = choice["message"]

        # check if LLM wants to call tools
        tool_calls = message.get("tool_calls")
        if not tool_calls or choice.get("finish_reason") != "tool_calls":
            # no tool calls — this is the final response
            content = message.get("content", "")
            # append tool usage log to the response if tools were used
            if tool_log:
                content = f"[Cortex: used {len(tool_log)} tool call(s): {', '.join(tool_log)}]\n\n{content}"
            return content

        # process each tool call
        messages.append(message)  # add assistant's tool_calls message

        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                arguments = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}

            print(f"    -> tool: {func_name}({arguments})")
            tool_result = execute_tool(tools, func_name, arguments)
            tool_log.append(func_name)

            # truncate very long results to avoid blowing context
            # 8K context per LM Studio slot, must leave room for prompt + response
            if len(tool_result) > 8000:
                tool_result = tool_result[:8000] + "\n... (truncated)"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result
            })

    # hit max rounds — preserve tool log for debugging
    log_str = f"used {len(tool_log)} tool call(s): {', '.join(tool_log)}" if tool_log else "no tools called"
    return f"[Cortex: hit max tool rounds ({MAX_TOOL_ROUNDS}). {log_str}. Last response may be incomplete.]"
