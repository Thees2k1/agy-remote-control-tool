import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure src/ is on sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.cloud_remote import (
    parse_instance_name,
    get_cloud_remote_status,
    start_cloud_remote,
    broadcast_cloud_remote_url,
    CLOUD_REMOTE_BASE_URL
)

class TestCloudRemote(unittest.TestCase):

    def test_parse_instance_name_valid(self):
        sample_output = (
            "Daemon status: not registered\n"
            "Instance name: workally-starlit-mars (find it at https://antigravity.google.com)\n"
        )
        name = parse_instance_name(sample_output)
        self.assertEqual(name, "workally-starlit-mars")

    def test_parse_instance_name_not_assigned(self):
        sample_output = (
            "Daemon status: not registered\n"
            "Instance name: not assigned yet; the daemon generates one on its first start.\n"
        )
        name = parse_instance_name(sample_output)
        self.assertIsNone(name)

    @patch("subprocess.run")
    def test_get_cloud_remote_status_active(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Daemon status: registered\nInstance name: test-star-42 (find it at https://antigravity.google.com)\n",
            stderr=""
        )
        status = get_cloud_remote_status()
        self.assertTrue(status["ok"])
        self.assertEqual(status["instance_name"], "test-star-42")
        self.assertEqual(status["url"], CLOUD_REMOTE_BASE_URL)

    @patch("subprocess.run")
    def test_start_cloud_remote(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Remote-control daemon started.\nInstance name: star-gemini-7\n",
            stderr=""
        )
        res = start_cloud_remote(session_only=True)
        self.assertTrue(res["ok"])
        self.assertEqual(res["instance_name"], "star-gemini-7")
        args = mock_run.call_args_list[0][0][0]
        self.assertIn("--session", args)

    @patch("mrc.cloud_remote.get_cloud_remote_status")
    def test_broadcast_cloud_remote_url(self, mock_status):
        mock_status.return_value = {
            "ok": True,
            "instance_name": "mars-rover-99",
            "url": "https://antigravity.google.com"
        }
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"ok": True, "message_id": 1234}

        success = broadcast_cloud_remote_url(telegram_client=mock_client, chat_id="123456")
        self.assertTrue(success)
        mock_client.send_message.assert_called_once()
        msg = mock_client.send_message.call_args[0][0]
        self.assertIn("mars-rover-99", msg)
        self.assertIn("https://antigravity.google.com", msg)
