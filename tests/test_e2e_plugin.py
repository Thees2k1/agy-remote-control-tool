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

import session_start
import post_tool_use
from mrc.mcp_server import handle_mcp_request
from mrc.session_state import is_handsfree_enabled, set_handsfree, clear_session_state
from mrc.guardrails import is_hard_deny

class TestE2EPlugin(unittest.TestCase):

    def setUp(self):
        self.conv_id = "e2e-session-001"
        clear_session_state(self.conv_id)

    def tearDown(self):
        clear_session_state(self.conv_id)

    def test_full_plugin_lifecycle_flow(self):
        # 1. Plugin structure integrity
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "plugin.json")))
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "hooks.json")))
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "mcp_config.json")))
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "rules", "AGENTS.md")))
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "skills", "mrc", "SKILL.md")))

        # 2. SessionStart hook executes cleanly
        start_payload = json.dumps({"conversationId": self.conv_id})
        with patch("mrc.cloud_remote.broadcast_cloud_remote_url", return_value=True):
            res_start = session_start.handle_session_start(start_payload)
            self.assertEqual(res_start, {})

        # 3. Guardrail safety tier 1
        blocked, reason = is_hard_deny("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\config\hooks.json"})
        self.assertTrue(blocked)

        # 4. Hands-free toggle via MCP
        mcp_req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "mrc_toggle_handsfree",
                "arguments": {
                    "conversation_id": self.conv_id,
                    "enabled": False
                }
            }
        }
        res_mcp = handle_mcp_request(mcp_req)
        self.assertEqual(res_mcp.get("id"), 10)
        self.assertFalse(is_handsfree_enabled(self.conv_id))

        # 5. PostToolUse cleans up transient grants
        post_payload = json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"}
            }
        })
        with patch("post_tool_use.purge_transient_grants") as mock_purge:
            res_post = post_tool_use.handle_post_tool_use(post_payload)
            self.assertEqual(res_post, {})
            mock_purge.assert_called_once()
