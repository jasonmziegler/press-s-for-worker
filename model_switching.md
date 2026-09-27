# Dashboard model switching

Start LM Studio's local server, then run `python dashboard.py` and `python worker.py`.
Both processes must use the updated code. Open http://127.0.0.1:5000 and use
the Worker Model panel to choose a downloaded language model and context length.
The model list refreshes once when the page opens and every three seconds only
while a switch is in progress. Monitoring stops on completion or connection error.
Use Refresh models to pick up downloads or changes made directly in LM Studio,
or to reconnect after an error. Reload any existing dashboard tabs after updating.

Switching pauses new task claims, waits for the current task and its memory/tool
extraction, unloads the selected worker instance, loads the replacement, and runs
a short inference check. A successful switch persists the selection and resumes
the queue. The embedding model and unrelated loaded models are not unloaded.

If a switch fails or the dashboard exits during switching, the queue stays paused.
Select a model (including the previous model) and click Switch model to retry.
The selected model label is the last successful selection; the dropdown marks
instances currently reported as loaded by LM Studio. A readiness check verifies
basic inference, not coding quality or tool-call accuracy.

Model settings live in ignored `model_settings.db`; OS file locks coordinate the
dashboard and worker across processes on Windows. Do not delete these files while
either process is running. Only manage the worker model through this dashboard
while tasks are active; unloading it directly in LM Studio bypasses coordination.

The model controller uses LM Studio's native `/api/v1/models` endpoints (LM Studio
0.4 or later). Inference continues through `/v1/chat/completions`. If authentication
is enabled, set `LM_STUDIO_API_TOKEN` for the dashboard. Existing inference code
still assumes the original local unauthenticated server at localhost:1234.

Run automated tests with `python -m unittest test_model_control -v`.
