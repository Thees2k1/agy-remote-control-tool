import os
import sys
import json
import unittest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.config import CLI_SETTINGS_PATH, GRANTS_PATH
from mrc.session_grant import grant_transient_permission, purge_transient_grants

class TestSessionGrant(unittest.TestCase):

    def test_transient_lifecycle(self):
        mock_payload = {
            "conversationId": "test-session-m1",
            "stepIdx": 8888,
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "Write-Output 'VERIFY_MODULAR_LIFECYCLE'"
                }
            }
        }

        # 1. Inject transient grant
        grant_transient_permission(mock_payload)

        # Verify session_grants.json
        self.assertTrue(os.path.exists(GRANTS_PATH))
        with open(GRANTS_PATH, "r", encoding="utf-8") as f:
            grants = json.load(f)
        self.assertIn("Write-Output 'VERIFY_MODULAR_LIFECYCLE'", grants.get("temp_commands", []))

        # Verify settings.json
        with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertIn("Write-Output 'VERIFY_MODULAR_LIFECYCLE'", settings.get("commandAllowlist", []))

        # 2. Purge transient grant
        purge_transient_grants()

        # Verify settings.json cleaned
        with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings_clean = json.load(f)
        self.assertNotIn("Write-Output 'VERIFY_MODULAR_LIFECYCLE'", settings_clean.get("commandAllowlist", []))

        # Verify session_grants.json removed
        self.assertFalse(os.path.exists(GRANTS_PATH))

    def test_filesystem_transient_lifecycle(self):
        mock_payload = {
            "conversationId": "test-session-fs",
            "stepIdx": 8889,
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "C:\\fake\\workspace\\sample.txt"
                }
            }
        }

        # 1. Inject transient grant
        grant_transient_permission(mock_payload)

        # Verify session_grants.json recorded temp_rules
        self.assertTrue(os.path.exists(GRANTS_PATH))
        with open(GRANTS_PATH, "r", encoding="utf-8") as f:
            grants = json.load(f)
        self.assertIn("filesystem(C:\\fake\\workspace\\sample.txt)", grants.get("temp_rules", []))

        # Verify settings.json has permission
        with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertIn("filesystem(C:\\fake\\workspace\\sample.txt)", settings.get("permissions", {}).get("allow", []))

        # 2. Purge transient grant
        purge_transient_grants()

        # Verify settings.json cleaned
        with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings_clean = json.load(f)
        self.assertNotIn("filesystem(C:\\fake\\workspace\\sample.txt)", settings_clean.get("permissions", {}).get("allow", []))

        # Verify session_grants.json removed
        self.assertFalse(os.path.exists(GRANTS_PATH))


if __name__ == "__main__":
    unittest.main()

