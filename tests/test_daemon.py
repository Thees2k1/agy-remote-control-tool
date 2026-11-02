import os
import sys
import unittest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.formatting import build_message_and_summary, truncate

class TestDaemonFormatting(unittest.TestCase):

    def test_truncate(self):
        self.assertEqual(truncate("hello", 10), "hello")
        long_str = "a" * 20
        truncated = truncate(long_str, 10)
        self.assertTrue(truncated.startswith("aaaaaaaaaa\n... [truncated 10 chars]"))

    def test_build_message_run_command(self):
        payload = {
            "stepIdx": 5,
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git status",
                    "Cwd": "C:/projects"
                }
            }
        }
        msg, summary = build_message_and_summary(payload)
        self.assertIn("Step #5", msg)
        self.assertIn("git status", msg)
        self.assertIn("Execute command: git status", summary)

    def test_build_message_write_to_file(self):
        payload = {
            "stepIdx": 3,
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "C:/test.py",
                    "CodeContent": "print('hello')\n"
                }
            }
        }
        msg, summary = build_message_and_summary(payload)
        self.assertIn("C:/test.py", msg)
        self.assertIn("Writing file (+1 lines)", summary)

if __name__ == "__main__":
    unittest.main()
