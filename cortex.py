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
from pathlib import Path

API_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen/qwen3-14b"
TOOLS_DIR = Path(__file__).parent / "tools"
MAX_TOOL_ROUNDS = 10  # safety limit to prevent infinite loops

def load_tools() -> dict:
    """Discover and load all tools from the tools/ directory.
    Returns a dict mapping function_name -> {function, schema}."""
    tools = {}
    for py_file in TOOLS_DIR.glob("*.py"):
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
            # build OpenAI-style function schema from signature
            sig = inspect.signature(func)
            properties = {}
            required = []
            for param_name, param in sig.parameters.items():
                properties[param_name] = {"type": "string", "description": param_name}
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

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

def run_cortex(task: str, think: bool = True, context: str = "") -> str:
    """Run the Cortex execution loop for a single task.

    Returns the final text response from the LLM after all tool calls
    have been resolved.
    """
    tools = load_tools()
    tool_schemas = [t["schema"] for t in tools.values()]

    # build initial prompt
    if context:
        full_prompt = f"{context}\n\n{task}"
    else:
        full_prompt = task
    if not think:
        full_prompt += " /no_think"

    messages = [{"role": "user", "content": full_prompt}]

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
            if len(tool_result) > 4000:
                tool_result = tool_result[:4000] + "\n... (truncated)"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result
            })

    # hit max rounds
    return f"[Cortex: hit max tool rounds ({MAX_TOOL_ROUNDS}). Last response may be incomplete.]"
