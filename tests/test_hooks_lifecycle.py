import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
HOOKS_DIR = os.path.join(PROJECT_ROOT, "hooks")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for d in (PROJECT_ROOT, HOOKS_DIR, SRC_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

class TestHooksLifecycle(unittest.TestCase):

    def test_root_hooks_json_valid(self):
        hooks_json_path = os.path.join(PROJECT_ROOT, "hooks.json")
        self.assertTrue(os.path.exists(hooks_json_path), "hooks.json must exist at plugin root")
        with open(hooks_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("mrc-lifecycle", data)
        cfg = data["mrc-lifecycle"]
        self.assertIn("SessionStart", cfg)
        self.assertIn("PreToolUse", cfg)
        self.assertIn("PostToolUse", cfg)

    def test_session_start_hook_broadcasts_when_enabled(self):
        import session_start
        sample_input = json.dumps({
            "conversationId": "test-session-1234",
            "modelName": "gemini-test"
        })
        with patch("session_start.broadcast_cloud_remote_url", return_value=True) as mock_broadcast, \
             patch("sys.stdin.read", return_value=sample_input), \
             patch("sys.stdin.isatty", return_value=False), \
             patch("mrc.config.load_config", return_value={"auto_broadcast_cloud_remote": True}):
            out = session_start.handle_session_start(sample_input)
            self.assertEqual(out, {})
            mock_broadcast.assert_called_once()

    def test_post_tool_use_detects_remote_control_command(self):
        import post_tool_use
        sample_payload = json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "agy remote-control start --session"
                }
            },
            "stepIdx": 5
        })
        with patch("post_tool_use.purge_transient_grants"), \
             patch("post_tool_use.broadcast_cloud_remote_url", return_value=True) as mock_broadcast:
            out = post_tool_use.handle_post_tool_use(sample_payload)
            self.assertEqual(out, {})
            mock_broadcast.assert_called_once()
