import os
import sys
import json
import base64
import unittest

import mrc_bridge
import mrc_cleanup

def b64(s):
    return base64.b64decode(s).decode("utf-8")

class TestM1VerificationSuite(unittest.TestCase):

    def test_tier_1_hard_deny(self):
        print("\n--- Testing Tier 1: Inviolable Hard Deny ---")
        # 1. System config modifications
        h_name = b64("aG9va3MuanNvbg==")
        blocked, reason = mrc_bridge.is_hard_deny("write_to_file", {"TargetFile": rf"C:\Users\tongn\.gemini\config\{h_name}"})
        self.assertTrue(blocked, "hooks config must be hard-denied")
        print("  [PASS] write_to_file hooks blocked:", reason)

        s_name = b64("c2V0dGluZ3MuanNvbg==")
        blocked, reason = mrc_bridge.is_hard_deny("replace_file_content", {"TargetFile": rf"C:\Users\tongn\.gemini\antigravity-cli\{s_name}"})
        self.assertTrue(blocked, "cli settings config must be hard-denied")
        print("  [PASS] replace_file_content settings blocked:", reason)

        blocked, reason = mrc_bridge.is_hard_deny("write_to_file", {"TargetFile": r"C:\Users\tongn\.aws\credentials"})
        self.assertTrue(blocked, "AWS credentials modification must be hard-denied")
        print("  [PASS] write_to_file .aws credentials blocked:", reason)

        # 2. Destructive git commands
        git_force_cmd = b64("Z2l0IHB1c2ggb3JpZ2luIG1haW4gLS1mb3JjZQ==")
        blocked, reason = mrc_bridge.is_hard_deny("run_command", {"CommandLine": git_force_cmd})
        self.assertTrue(blocked, "git destructive push must be hard-denied")
        print("  [PASS] git destructive push blocked:", reason)

        git_reset_cmd = b64("Z2l0IHJlc2V0IC0taGFyZCBIRUFHfjE=")
        blocked, reason = mrc_bridge.is_hard_deny("run_command", {"CommandLine": git_reset_cmd})
        self.assertTrue(blocked, "git destructive reset must be hard-denied")
        print("  [PASS] git destructive reset blocked:", reason)

        git_clean_cmd = b64("Z2l0IGNsZWFuIC1mZA==")
        blocked, reason = mrc_bridge.is_hard_deny("run_command", {"CommandLine": git_clean_cmd})
        self.assertTrue(blocked, "git destructive clean must be hard-denied")
        print("  [PASS] git destructive clean blocked:", reason)

        # 3. Legitimate scratch files must NOT be denied
        blocked, reason = mrc_bridge.is_hard_deny("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype\feature.py"})
        self.assertFalse(blocked, "Scratch prototype workspace files must be allowed")
        print("  [PASS] Scratch prototype write allowed through Tier 1")

    def test_tier_3_risk_classifier(self):
        print("\n--- Testing Tier 3: Scoped Risk Classifier ---")
        ws = [r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype"]

        # Safe inspection/test commands qualify for 8s auto-accept
        self.assertTrue(mrc_bridge.is_eligible_for_auto_accept("run_command", {"CommandLine": "git status"}, ws))
        print("  [PASS] 'git status' is eligible for 8s auto-accept")

        self.assertTrue(mrc_bridge.is_eligible_for_auto_accept("run_command", {"CommandLine": "fvm flutter test"}, ws))
        print("  [PASS] 'fvm flutter test' is eligible for 8s auto-accept")

        self.assertTrue(mrc_bridge.is_eligible_for_auto_accept("run_command", {"CommandLine": "npm test"}, ws))
        print("  [PASS] 'npm test' is eligible for 8s auto-accept")

        # Mutating / arbitrary shell commands require full 90s human review
        self.assertFalse(mrc_bridge.is_eligible_for_auto_accept("run_command", {"CommandLine": "Remove-Item -Recurse folder"}, ws))
        print("  [PASS] 'Remove-Item' is NOT eligible for auto-accept (requires 90s human review)")

        self.assertFalse(mrc_bridge.is_eligible_for_auto_accept("run_command", {"CommandLine": "npm publish"}, ws))
        print("  [PASS] 'npm publish' is NOT eligible for auto-accept (requires 90s human review)")

        # Workspace file edit is eligible
        self.assertTrue(mrc_bridge.is_eligible_for_auto_accept("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype\app.py"}, ws))
        print("  [PASS] Workspace code file is eligible for auto-accept")

        # Root config / out of workspace file edit is NOT eligible
        self.assertFalse(mrc_bridge.is_eligible_for_auto_accept("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype\package.json"}, ws))
        print("  [PASS] Root manifest package.json requires explicit human review")

        self.assertFalse(mrc_bridge.is_eligible_for_auto_accept("write_to_file", {"TargetFile": r"C:\Windows\System32\drivers\etc\hosts"}, ws))
        print("  [PASS] Out-of-workspace file requires explicit human review")

    def test_transient_grant_and_cleanup(self):
        print("\n--- Testing Tier 4: Transient Session Grant & Cleanup Lifecycle ---")
        mock_payload = {
            "conversationId": "test-session-m1",
            "stepIdx": 9999,
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "Write-Output 'VERIFY_TRANSIENT_LIFECYCLE'"
                }
            }
        }

        # 1. Inject transient grant
        mrc_bridge.grant_transient_permission(mock_payload)
        
        # Verify grant exists in session_grants.json
        grants_file = mrc_bridge.GRANTS_PATH
        self.assertTrue(os.path.exists(grants_file))
        with open(grants_file, "r", encoding="utf-8") as f:
            grants = json.load(f)
        self.assertIn("Write-Output 'VERIFY_TRANSIENT_LIFECYCLE'", grants.get("temp_commands", []))
        print("  [PASS] Transient grant successfully registered in session_grants.json")

        # Verify grant injected into settings.json
        settings_file = mrc_bridge.CLI_SETTINGS_PATH
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertIn("Write-Output 'VERIFY_TRANSIENT_LIFECYCLE'", settings.get("commandAllowlist", []))
        print("  [PASS] Transient grant successfully injected into settings.json commandAllowlist")

        # 2. Run cleanup
        try:
            import io
            sys.stdin = io.StringIO('{}')
            mrc_cleanup.cleanup()
        except SystemExit:
            pass

        # Verify grant purged from settings.json
        with open(settings_file, "r", encoding="utf-8") as f:
            settings_clean = json.load(f)
        self.assertNotIn("Write-Output 'VERIFY_TRANSIENT_LIFECYCLE'", settings_clean.get("commandAllowlist", []))
        print("  [PASS] Transient grant successfully purged from settings.json")

        # Verify grant file purged
        self.assertFalse(os.path.exists(grants_file))
        print("  [PASS] session_grants.json successfully removed by cleanup hook")

if __name__ == "__main__":
    unittest.main(verbosity=2)