import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import model_control as control
from dashboard import app


class ModelSwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(control, "ROOT", Path(self.temp.name))
        self.root_patch.start()
        self.models = [
            {"key": control.DEFAULT_MODEL, "type": "llm", "display_name": "Old",
             "loaded_instances": [{"id": control.DEFAULT_MODEL}]},
            {"key": "new", "type": "llm", "display_name": "New", "max_context_length": 32768,
             "loaded_instances": []},
            {"key": "embedding", "type": "embedding", "loaded_instances": [{"id": "embedding"}]},
            {"key": "other", "type": "llm", "loaded_instances": [{"id": "other"}]},
        ]
        self.calls = []

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def fake_api(self, method, path, **kwargs):
        self.calls.append((path, kwargs.get("json")))
        if path == "/api/v1/models":
            return {"models": self.models}
        if path.endswith("/unload"):
            self.models[0]["loaded_instances"] = []
            return {}
        if path.endswith("/load"):
            self.models[1]["loaded_instances"] = [{"id": "new-instance"}]
            return {"instance_id": "new-instance"}
        return {"choices": [{"message": {"content": "OK"}}]}

    def wait_switch(self):
        limit = time.monotonic() + 5
        while control.switch_busy() and time.monotonic() < limit:
            time.sleep(.02)
        self.assertFalse(control.switch_busy())

    def test_success_preserves_other_models_and_embedding(self):
        with patch.object(control, "api", side_effect=self.fake_api):
            control.start_switch("new", 16384)
            self.wait_switch()
        self.assertEqual(control.active_model(), "new-instance")
        self.assertFalse(control.state()["paused"])
        unloads = [body for path, body in self.calls if path.endswith("/unload")]
        self.assertEqual(unloads, [{"instance_id": control.DEFAULT_MODEL}])
        self.assertEqual(self.models[2]["loaded_instances"], [{"id": "embedding"}])

    def test_waits_for_whole_task_and_rejects_duplicate(self):
        with patch.object(control, "api", side_effect=self.fake_api):
            with control.mutex("worker_model"):
                control.start_switch("new", 8192)
                time.sleep(.1)
                self.assertTrue(control.state()["paused"])
                self.assertFalse(any(p.endswith('/unload') for p, _ in self.calls))
                with self.assertRaises(RuntimeError):
                    control.start_switch("new", 8192)
            self.wait_switch()
        self.assertEqual(control.state()["phase"], "Ready")

    def test_failure_stays_paused_then_retry_recovers(self):
        def fail(method, path, **kwargs):
            if path.endswith('/load'):
                raise RuntimeError('Not enough VRAM')
            return self.fake_api(method, path, **kwargs)
        with patch.object(control, "api", side_effect=fail):
            control.start_switch("new", 16384)
            self.wait_switch()
        self.assertTrue(control.state()["paused"])
        self.assertIn("VRAM", control.state()["error"])
        self.assertEqual(control.active_model(), control.DEFAULT_MODEL)
        with patch.object(control, "api", side_effect=self.fake_api):
            control.start_switch("new", 8192)
            self.wait_switch()
        self.assertFalse(control.state()["paused"])

    def test_invalid_input_does_not_pause_or_unload(self):
        with patch.object(control, "api", side_effect=self.fake_api):
            for model, context in [('embedding', 8192), ('missing', 8192), ('new', 999999), ('new', True)]:
                with self.assertRaises(ValueError):
                    control.start_switch(model, context)
        self.assertFalse(control.state()["paused"])
        self.assertFalse(any(p.endswith('/unload') for p, _ in self.calls))

    def test_routes_and_dashboard(self):
        client = app.test_client()
        self.assertIn(b'model-select', client.get('/').data)
        with client.get('/static/models.js') as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(client.post('/api/models/switch', json=[]).status_code, 400)
        with patch.object(control, 'inventory', side_effect=RuntimeError('offline')):
            self.assertEqual(client.get('/api/models').status_code, 503)


if __name__ == '__main__':
    unittest.main()
