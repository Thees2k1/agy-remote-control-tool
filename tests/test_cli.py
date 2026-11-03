import os
import sys
import unittest
from unittest.mock import patch, MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.cli import main

class TestCLI(unittest.TestCase):

    @patch("mrc.cli.is_daemon_alive", return_value=True)
    @patch("mrc.cli.get_cloud_remote_status", return_value={"instance_name": "rover-1", "url": "https://antigravity.google.com"})
    def test_cli_status(self, mock_remote, mock_alive):
        with patch("sys.argv", ["mrc", "status"]), patch("sys.stdout.write") as mock_stdout:
            exit_code = main()
            self.assertEqual(exit_code, 0)
            output = "".join(call[0][0] for call in mock_stdout.call_args_list)
            self.assertIn("running", output)
            self.assertIn("rover-1", output)

    @patch("mrc.cli.start_daemon_process", return_value=True)
    @patch("mrc.cli.is_daemon_alive", return_value=False)
    def test_cli_serve(self, mock_alive, mock_start):
        with patch("sys.argv", ["mrc", "serve"]), patch("sys.stdout.write"):
            exit_code = main()
            self.assertEqual(exit_code, 0)
            mock_start.assert_called_once()

    @patch("mrc.cli.stop_daemon_processes", return_value=True)
    def test_cli_close(self, mock_stop):
        with patch("sys.argv", ["mrc", "close"]), patch("sys.stdout.write"):
            exit_code = main()
            self.assertEqual(exit_code, 0)
            mock_stop.assert_called_once()

    @patch("mrc.cli.start_cloud_remote", return_value={"ok": True})
    @patch("mrc.cli.broadcast_cloud_remote_url", return_value=True)
    @patch("mrc.cli.get_cloud_remote_status", return_value={"instance_name": "sky-1", "url": "https://antigravity.google.com"})
    def test_cli_remote(self, mock_status, mock_broadcast, mock_start):
        with patch("sys.argv", ["mrc", "remote"]), patch("sys.stdout.write") as mock_stdout:
            exit_code = main()
            self.assertEqual(exit_code, 0)
            mock_start.assert_called_once()
            mock_broadcast.assert_called_once()
