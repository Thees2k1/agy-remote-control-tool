import os
import sys
import unittest
from unittest.mock import patch, MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
HOOKS_DIR = os.path.join(PROJECT_ROOT, "hooks")
for p in (SRC_DIR, HOOKS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from mrc.config import get_local_grace_period_seconds, DEFAULT_LOCAL_GRACE_PERIOD_SECONDS
import pre_tool_use


class TestDeskGracePeriod(unittest.TestCase):

    def test_config_grace_period_resolution(self):
        # Default fallback
        with patch("mrc.config.load_config", return_value={}):
            self.assertEqual(get_local_grace_period_seconds(), DEFAULT_LOCAL_GRACE_PERIOD_SECONDS)

        # Custom config value
        with patch("mrc.config.load_config", return_value={"local_grace_period_seconds": 6}):
            self.assertEqual(get_local_grace_period_seconds(), 6)

        # Invalid config fallback
        with patch("mrc.config.load_config", return_value={"local_grace_period_seconds": "invalid"}):
            self.assertEqual(get_local_grace_period_seconds(), DEFAULT_LOCAL_GRACE_PERIOD_SECONDS)

    @patch("pre_tool_use.check_local_keypress", return_value="allow")
    @patch("pre_tool_use.send_decision", side_effect=SystemExit(0))
    @patch("pre_tool_use.grant_transient_permission")
    @patch("pre_tool_use.ensure_daemon_running")
    def test_desk_keypress_allow_bypasses_telegram(self, mock_daemon, mock_grant, mock_send, mock_key):
        # When keypress returns "allow", daemon and telegram must NEVER be contacted
        payload = {
            "conversationId": "desk-test-allow",
            "stepIdx": 101,
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"}
            }
        }
        with patch("sys.stdin.read", return_value=pre_tool_use.json.dumps(payload)):
            with patch("pre_tool_use.get_local_grace_period_seconds", return_value=3):
                with self.assertRaises(SystemExit):
                    pre_tool_use.main()

        mock_grant.assert_called_once_with(payload)
        mock_send.assert_called_once_with("allow", "Approved at workstation keyboard")
        mock_daemon.assert_not_called()

    @patch("pre_tool_use.check_local_keypress", return_value="deny")
    @patch("pre_tool_use.send_decision", side_effect=SystemExit(0))
    @patch("pre_tool_use.ensure_daemon_running")
    def test_desk_keypress_deny_bypasses_telegram(self, mock_daemon, mock_send, mock_key):
        # When keypress returns "deny", daemon and telegram must NEVER be contacted
        payload = {
            "conversationId": "desk-test-deny",
            "stepIdx": 102,
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"}
            }
        }
        with patch("sys.stdin.read", return_value=pre_tool_use.json.dumps(payload)):
            with patch("pre_tool_use.get_local_grace_period_seconds", return_value=3):
                with self.assertRaises(SystemExit):
                    pre_tool_use.main()

        mock_send.assert_called_once_with("deny", "Denied at workstation keyboard")
        mock_daemon.assert_not_called()


if __name__ == "__main__":
    unittest.main()
