from flask import Flask, request, jsonify, render_template_string
from taskqueue import add_task, list_tasks
from memory import list_memories, delete_memory
from toolbox import list_tools, delete_tool

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Worker Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Consolas', 'Courier New', monospace;
    background: #0a0e14;
    color: #c5c8c6;
    padding: 24px;
    max-width: 1100px;
    margin: 0 auto;
  }
  h1 {
    color: #66ccff;
    font-size: 1.4em;
    margin-bottom: 4px;
  }
  .subtitle {
    color: #555;
    font-size: 0.85em;
    margin-bottom: 24px;
  }
  .stats {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
  }
  .stat-box {
    background: #111820;
    border: 1px solid #1e2a36;
    border-radius: 6px;
    padding: 12px 20px;
    text-align: center;
    flex: 1;
  }
  .stat-box .number {
    font-size: 2em;
    font-weight: bold;
  }
  .stat-box .label {
    font-size: 0.75em;
    color: #666;
    text-transform: uppercase;
    margin-top: 2px;
  }
  .stat-pending .number { color: #f0c674; }
  .stat-running .number { color: #66ccff; }
  .stat-done .number { color: #a6e22e; }
  .stat-failed .number { color: #f92672; }

  .add-form {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
    align-items: center;
  }
  .add-form input[type="text"] {
    flex: 1;
    background: #111820;
    border: 1px solid #1e2a36;
    border-radius: 6px;
    padding: 10px 14px;
    color: #c5c8c6;
    font-family: inherit;
    font-size: 0.9em;
  }
  .add-form input[type="text"]:focus {
    outline: none;
    border-color: #66ccff;
  }
  .add-form button {
    background: #1a3a4a;
    color: #66ccff;
    border: 1px solid #264d60;
    border-radius: 6px;
    padding: 10px 20px;
    font-family: inherit;
    font-size: 0.9em;
    cursor: pointer;
    white-space: nowrap;
  }
  .add-form button:hover {
    background: #264d60;
  }

  .think-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    user-select: none;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #1e2a36;
    background: #111820;
    font-size: 0.8em;
    white-space: nowrap;
  }
  .think-toggle.active {
    border-color: #8a6de9;
    background: #1a1530;
    color: #b49cff;
  }
  .think-toggle.inactive {
    border-color: #3b3015;
    background: #1a1510;
    color: #f0c674;
  }
  .think-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .think-toggle.active .think-dot { background: #8a6de9; }
  .think-toggle.inactive .think-dot { background: #f0c674; }

  .task-list { list-style: none; }
  .task-item {
    background: #111820;
    border: 1px solid #1e2a36;
    border-radius: 6px;
    margin-bottom: 8px;
    overflow: hidden;
  }
  .task-header {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    gap: 12px;
  }
  .task-header:hover { background: #151d27; }
  .task-id {
    color: #555;
    font-size: 0.8em;
    min-width: 30px;
  }
  .badge {
    font-size: 0.7em;
    padding: 2px 8px;
    border-radius: 3px;
    text-transform: uppercase;
    font-weight: bold;
    min-width: 60px;
    text-align: center;
  }
  .badge-pending { background: #3b3015; color: #f0c674; }
  .badge-running { background: #0f2a3d; color: #66ccff; }
  .badge-done { background: #1a2e10; color: #a6e22e; }
  .badge-failed { background: #3d0f1a; color: #f92672; }
  .badge-think { background: #1a1530; color: #b49cff; font-size: 0.6em; min-width: auto; }
  .badge-nothink { background: #1a1510; color: #f0c674; font-size: 0.6em; min-width: auto; }
  .task-text {
    flex: 1;
    font-size: 0.9em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .task-time {
    color: #444;
    font-size: 0.75em;
    min-width: 140px;
    text-align: right;
  }
  .task-output {
    display: none;
    padding: 16px;
    border-top: 1px solid #1e2a36;
    background: #0d1117;
    font-size: 0.85em;
    line-height: 1.6;
    white-space: pre-wrap;
    max-height: 400px;
    overflow-y: auto;
  }
  .task-item.expanded .task-output { display: block; }
  .arrow {
    color: #444;
    font-size: 0.8em;
    transition: transform 0.2s;
  }
  .task-item.expanded .arrow { transform: rotate(90deg); }
  .section-header {
    color: #66ccff;
    font-size: 1.1em;
    margin: 28px 0 12px 0;
    border-bottom: 1px solid #1e2a36;
    padding-bottom: 6px;
  }
  .memory-list { list-style: none; }
  .memory-item {
    background: #111820;
    border: 1px solid #1a1530;
    border-left: 3px solid #8a6de9;
    border-radius: 4px;
    margin-bottom: 6px;
    padding: 10px 14px;
    font-size: 0.85em;
  }
  .memory-summary { color: #c5c8c6; }
  .memory-delete {
    background: none;
    border: 1px solid #3d0f1a;
    color: #f92672;
    font-family: inherit;
    font-size: 0.7em;
    padding: 2px 8px;
    border-radius: 3px;
    cursor: pointer;
    float: right;
  }
  .memory-delete:hover { background: #3d0f1a; }
  .memory-meta {
    color: #555;
    font-size: 0.75em;
    margin-top: 4px;
  }
  .tool-item {
    background: #111820;
    border: 1px solid #152a15;
    border-left: 3px solid #a6e22e;
    border-radius: 4px;
    margin-bottom: 6px;
    padding: 10px 14px;
    font-size: 0.85em;
  }
  .tool-name { color: #a6e22e; font-weight: bold; }
  .tool-desc { color: #c5c8c6; margin-top: 2px; }
  .tool-meta {
    color: #555;
    font-size: 0.75em;
    margin-top: 4px;
  }
  .tool-delete {
    background: none;
    border: 1px solid #3d0f1a;
    color: #f92672;
    font-family: inherit;
    font-size: 0.7em;
    padding: 2px 8px;
    border-radius: 3px;
    cursor: pointer;
    margin-left: 8px;
  }
  .tool-delete:hover { background: #3d0f1a; }
  .memory-tag {
    background: #1a1530;
    color: #8a6de9;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.7em;
    margin-right: 4px;
  }
  .tab-bar {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
  }
  .tab {
    padding: 8px 20px;
    background: #111820;
    border: 1px solid #1e2a36;
    border-radius: 6px 6px 0 0;
    color: #555;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.85em;
  }
  .tab.active {
    color: #66ccff;
    border-bottom-color: #0a0e14;
    background: #0a0e14;
  }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  .refresh-note {
    color: #333;
    font-size: 0.75em;
    text-align: center;
    margin-top: 16px;
  }
</style>
</head>
<body>

<h1>// WORKER DASHBOARD</h1>
<div class="subtitle">press-s-for-worker</div>

<div class="stats">
  <div class="stat-box stat-pending">
    <div class="number" id="count-pending">-</div>
    <div class="label">Pending</div>
  </div>
  <div class="stat-box stat-running">
    <div class="number" id="count-running">-</div>
    <div class="label">Running</div>
  </div>
  <div class="stat-box stat-done">
    <div class="number" id="count-done">-</div>
    <div class="label">Done</div>
  </div>
  <div class="stat-box stat-failed">
    <div class="number" id="count-failed">-</div>
    <div class="label">Failed</div>
  </div>
</div>

<form class="add-form" onsubmit="addTask(event)">
  <input type="text" id="task-input" placeholder="Enter a task..." autocomplete="off" />
  <div class="think-toggle active" id="think-toggle" onclick="toggleThink(event)">
    <span class="think-dot"></span>
    <span id="think-label">THINK</span>
  </div>
  <button type="submit">Queue Task</button>
</form>

<div class="tab-bar">
  <div class="tab active" onclick="switchTab('tasks')">Tasks</div>
  <div class="tab" onclick="switchTab('memories')">Memories <span id="memory-count"></span></div>
  <div class="tab" onclick="switchTab('tools')">Tools <span id="tool-count"></span></div>
</div>

<div id="tab-tasks" class="tab-content active">
  <ul class="task-list" id="task-list"></ul>
</div>

<div id="tab-memories" class="tab-content">
  <ul class="memory-list" id="memory-list"></ul>
</div>

<div id="tab-tools" class="tab-content">
  <ul class="memory-list" id="tool-list"></ul>
</div>

<div class="refresh-note">Auto-refreshes every 3s | v0.6</div>

<script>
let thinkMode = true;

function toggleThink(e) {
  e.preventDefault();
  thinkMode = !thinkMode;
  const el = document.getElementById('think-toggle');
  const label = document.getElementById('think-label');
  if (thinkMode) {
    el.className = 'think-toggle active';
    label.textContent = 'THINK';
  } else {
    el.className = 'think-toggle inactive';
    label.textContent = 'FAST';
  }
}

function toggleTask(el) {
  el.closest('.task-item').classList.toggle('expanded');
}

function addTask(e) {
  e.preventDefault();
  const input = document.getElementById('task-input');
  const task = input.value.trim();
  if (!task) return;
  fetch('/api/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({task, think: thinkMode})
  }).then(() => {
    input.value = '';
    refresh();
  });
}

function refresh() {
  fetch('/api/tasks')
    .then(r => r.json())
    .then(data => {
      const counts = {pending: 0, running: 0, done: 0, failed: 0};
      data.forEach(t => counts[t.status] = (counts[t.status] || 0) + 1);
      document.getElementById('count-pending').textContent = counts.pending;
      document.getElementById('count-running').textContent = counts.running;
      document.getElementById('count-done').textContent = counts.done;
      document.getElementById('count-failed').textContent = counts.failed;

      const list = document.getElementById('task-list');
      const expanded = new Set(
        [...list.querySelectorAll('.task-item.expanded')].map(el => el.dataset.id)
      );
      list.innerHTML = data.slice().reverse().map(t => {
        const thinkBadge = t.think
          ? '<span class="badge badge-think">think</span>'
          : '<span class="badge badge-nothink">fast</span>';
        return `
          <li class="task-item ${expanded.has(String(t.id)) ? 'expanded' : ''}" data-id="${t.id}">
            <div class="task-header" onclick="toggleTask(this)">
              <span class="arrow">&#9654;</span>
              <span class="task-id">#${t.id}</span>
              <span class="badge badge-${t.status}">${t.status}</span>
              ${thinkBadge}
              <span class="task-text">${esc(t.task)}</span>
              <span class="task-time">${t.completed_at || t.started_at || t.created_at}</span>
            </div>
            <div class="task-output">${t.result ? esc(t.result) : 'No output yet.'}</div>
          </li>
        `;
      }).join('');
    });
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab-content#tab-${tab}`).classList.add('active');
  event.target.classList.add('active');
}

function refreshMemories() {
  fetch('/api/memories')
    .then(r => r.json())
    .then(data => {
      document.getElementById('memory-count').textContent = `(${data.length})`;
      const list = document.getElementById('memory-list');
      list.innerHTML = data.map(m => {
        const tags = m.tags ? m.tags.split(',').map(t =>
          `<span class="memory-tag">${esc(t.trim())}</span>`
        ).join('') : '';
        return `
          <li class="memory-item">
            <button class="memory-delete" onclick="deleteMemory(${m.id})">delete</button>
            <div class="memory-summary">${esc(m.summary)}</div>
            <div class="memory-meta">
              ${tags}
              ${m.source_task_id ? `from task #${m.source_task_id}` : ''}
              &middot; ${m.created_at}
            </div>
          </li>
        `;
      }).join('') || '<li class="memory-item"><div class="memory-summary" style="color:#555">No memories yet. Memories are created automatically after tasks complete.</div></li>';
    });
}

function deleteMemory(id) {
  if (!confirm('Delete this memory?')) return;
  fetch(`/api/memories/${id}`, {method: 'DELETE'}).then(() => refreshMemories());
}

function deleteTool(id, name) {
  if (!confirm(`Delete tool "${name}"?`)) return;
  fetch(`/api/tools/${id}`, {method: 'DELETE'}).then(() => refreshTools());
}

function refreshTools() {
  fetch('/api/tools')
    .then(r => r.json())
    .then(data => {
      document.getElementById('tool-count').textContent = `(${data.length})`;
      const list = document.getElementById('tool-list');
      list.innerHTML = data.map(t => `
        <li class="tool-item">
          <div class="tool-name">${esc(t.name)}
            <button class="tool-delete" onclick="deleteTool(${t.id}, '${esc(t.name)}')">delete</button>
          </div>
          <div class="tool-desc">${esc(t.description)}</div>
          <div class="tool-meta">
            tools/${esc(t.filename)}
            ${t.source_task_id ? `&middot; from task #${t.source_task_id}` : ''}
            &middot; ${t.created_at}
          </div>
        </li>
      `).join('') || '<li class="tool-item"><div class="tool-desc" style="color:#555">No tools yet. The system creates tools when tasks produce reusable code.</div></li>';
    });
}

refresh();
refreshMemories();
refreshTools();
setInterval(refresh, 3000);
setInterval(refreshMemories, 5000);
setInterval(refreshTools, 5000);
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/tasks", methods=["GET"])
def api_list_tasks():
    return jsonify(list_tasks())

@app.route("/api/tasks", methods=["POST"])
def api_add_task():
    data = request.get_json()
    task_text = data.get("task", "").strip()
    if not task_text:
        return jsonify({"error": "task is required"}), 400
    think = data.get("think", True)
    task_id = add_task(task_text, think=think)
    return jsonify({"id": task_id, "status": "pending"})

@app.route("/api/tools", methods=["GET"])
def api_list_tools():
    return jsonify(list_tools())

@app.route("/api/tools/<int:tool_id>", methods=["DELETE"])
def api_delete_tool(tool_id):
    if delete_tool(tool_id):
        return jsonify({"status": "deleted"})
    return jsonify({"error": "not found"}), 404

@app.route("/api/memories/<int:memory_id>", methods=["DELETE"])
def api_delete_memory(memory_id):
    if delete_memory(memory_id):
        return jsonify({"status": "deleted"})
    return jsonify({"error": "not found"}), 404

@app.route("/api/memories", methods=["GET"])
def api_list_memories():
    return jsonify(list_memories())

if __name__ == "__main__":
    print("Dashboard: http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
