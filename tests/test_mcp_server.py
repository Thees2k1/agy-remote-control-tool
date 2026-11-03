import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.mcp_server import handle_mcp_request

class TestMCPServer(unittest.TestCase):

    def test_initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        resp = handle_mcp_request(req)
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 1)
        res = resp.get("result", {})
        self.assertIn("serverInfo", res)
        self.assertEqual(res["serverInfo"]["name"], "mrc-manager")

    def test_tools_list(self):
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        resp = handle_mcp_request(req)
        self.assertEqual(resp.get("id"), 2)
        tools = resp.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]
        self.assertIn("mrc_status", tool_names)
        self.assertIn("mrc_serve", tool_names)
        self.assertIn("mrc_close", tool_names)
        self.assertIn("mrc_toggle_handsfree", tool_names)
        self.assertIn("mrc_cloud_remote", tool_names)

    @patch("mrc.mcp_server.get_cloud_remote_status")
    @patch("mrc.mcp_server.is_daemon_alive")
    def test_tools_call_status(self, mock_alive, mock_remote):
        mock_alive.return_value = True
        mock_remote.return_value = {
            "ok": True,
            "instance_name": "earth-lander-01",
            "url": "https://antigravity.google.com"
        }
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "mrc_status",
                "arguments": {}
            }
        }
        resp = handle_mcp_request(req)
        self.assertEqual(resp.get("id"), 3)
        content = resp.get("result", {}).get("content", [])
        self.assertTrue(len(content) > 0)
        text = content[0].get("text", "")
        self.assertIn("running", text)
        self.assertIn("earth-lander-01", text)

    def test_tools_call_toggle_handsfree(self):
        conv_id = "test-conv-mcp"
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "mrc_toggle_handsfree",
                "arguments": {
                    "conversation_id": conv_id,
                    "enabled": False
                }
            }
        }
        resp = handle_mcp_request(req)
        self.assertEqual(resp.get("id"), 4)
        from mrc.session_state import is_handsfree_enabled, clear_session_state
        self.assertFalse(is_handsfree_enabled(conv_id))
        clear_session_state(conv_id)
