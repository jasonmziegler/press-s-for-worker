"""Shared model selection and cross-process coordination for local workers."""
import json
import msvcrt
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import requests

ROOT = Path(__file__).parent
BASE_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234").rstrip("/")
DEFAULT_MODEL = "qwen/qwen3-14b"


def _db():
    conn = sqlite3.connect(ROOT / "model_settings.db", timeout=15)
    conn.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT OR IGNORE INTO settings VALUES (1, ?)", (json.dumps({
        "model": DEFAULT_MODEL, "instance_id": DEFAULT_MODEL,
        "paused": False, "phase": "Ready", "error": "", "context_length": 16384,
    }),))
    conn.commit()
    return conn


def state():
    with _db() as conn:
        result = json.loads(conn.execute("SELECT data FROM settings WHERE id=1").fetchone()[0])
    conn.close()
    return result


def update(**values):
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = json.loads(conn.execute("SELECT data FROM settings WHERE id=1").fetchone()[0])
        current.update(values)
        conn.execute("UPDATE settings SET data=? WHERE id=1", (json.dumps(current),))
    conn.close()


def active_model():
    return state()["instance_id"]


@contextmanager
def mutex(name, wait=True):
    """OS releases byte locks even if a worker or dashboard crashes."""
    handle = open(ROOT / (name + ".lock"), "a+b")
    handle.seek(0, 2)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    acquired = False
    try:
        while not acquired:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError:
                if not wait:
                    raise RuntimeError("A model switch is already in progress")
                time.sleep(0.2)
        yield
    finally:
        if acquired:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        handle.close()


def api(method, path, **kwargs):
    token = os.environ.get("LM_STUDIO_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.request(method, BASE_URL + path, headers=headers,
                                timeout=kwargs.pop("timeout", 30), **kwargs)
    response.raise_for_status()
    return response.json()


def inventory():
    return api("GET", "/api/v1/models")["models"]


def _switch(model, context_length):
    with mutex("worker_model"):
        try:
            previous = state()
            models = inventory()
            target = next(m for m in models if m["key"] == model and m["type"] == "llm")
            update(phase="Unloading current worker model")
            # Only unload the worker's selected instance; leave embeddings and other models alone.
            for item in models:
                for instance in item.get("loaded_instances", []):
                    if instance["id"] == previous["instance_id"]:
                        api("POST", "/api/v1/models/unload",
                            json={"instance_id": instance["id"]}, timeout=120)
            update(phase="Loading " + target["display_name"])
            loaded = api("POST", "/api/v1/models/load", timeout=600,
                         json={"model": model, "context_length": context_length})
            instance_id = loaded["instance_id"]
            update(phase="Checking model readiness")
            if not any(i["id"] == instance_id for m in inventory()
                       for i in m.get("loaded_instances", [])):
                raise RuntimeError("LM Studio did not report the loaded instance")
            check = api("POST", "/v1/chat/completions", timeout=120, json={
                "model": instance_id, "messages": [{"role": "user", "content": "Reply OK."}],
                "max_tokens": 32, "stream": False,
            })
            if not check.get("choices"):
                raise RuntimeError("Model returned no inference choices")
            update(model=model, instance_id=instance_id, context_length=context_length,
                   paused=False, phase="Ready", error="")
        except Exception as exc:
            update(paused=True, phase="Switch failed — queue paused", error=str(exc))


def start_switch(model, context_length):
    if isinstance(context_length, bool) or not isinstance(context_length, int):
        raise ValueError("Context length must be an integer")
    models = inventory()
    target = next((m for m in models if m["key"] == model and m["type"] == "llm"), None)
    if target is None:
        raise ValueError("Select a downloaded language model")
    if not 1024 <= context_length <= min(target.get("max_context_length", 32768), 32768):
        raise ValueError("Context must be between 1024 and the model limit (maximum 32768)")
    lock = mutex("model_switch", wait=False)
    lock.__enter__()
    try:
        update(paused=True, phase="Waiting for current task to finish", error="")
        def run():
            try:
                _switch(model, context_length)
            finally:
                lock.__exit__(None, None, None)
        threading.Thread(target=run, daemon=True).start()
    except Exception:
        lock.__exit__(None, None, None)
        raise


def switch_busy():
    try:
        with mutex("model_switch", wait=False):
            return False
    except RuntimeError:
        return True
