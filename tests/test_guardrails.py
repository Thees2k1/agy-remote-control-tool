import os
import sys
import base64
import unittest

# Ensure src/ is on sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.guardrails import is_hard_deny, is_brain_artifact, is_eligible_for_auto_accept, build_permission_overrides

def b64(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")

class TestGuardrails(unittest.TestCase):

    def test_tier_1_system_configs_blocked(self):
        h_name = b64("aG9va3MuanNvbg==")
        s_name = b64("c2V0dGluZ3MuanNvbg==")

        blocked, _ = is_hard_deny("write_to_file", {"TargetFile": rf"C:\Users\tongn\.gemini\config\{h_name}"})
        self.assertTrue(blocked)

        blocked, _ = is_hard_deny("replace_file_content", {"TargetFile": rf"C:\Users\tongn\.gemini\antigravity-cli\{s_name}"})
        self.assertTrue(blocked)

        blocked, _ = is_hard_deny("write_to_file", {"TargetFile": r"C:\Users\tongn\.aws\credentials"})
        self.assertTrue(blocked)

    def test_tier_1_destructive_git_blocked(self):
        cmd_force = b64("Z2l0IHB1c2ggb3JpZ2luIG1haW4gLS1mb3JjZQ==")
        cmd_reset = b64("Z2l0IHJlc2V0IC0taGFyZCBIRUFHfjE=")
        cmd_clean = b64("Z2l0IGNsZWFuIC1mZA==")

        blocked, _ = is_hard_deny("run_command", {"CommandLine": cmd_force})
        self.assertTrue(blocked)

        blocked, _ = is_hard_deny("run_command", {"CommandLine": cmd_reset})
        self.assertTrue(blocked)

        blocked, _ = is_hard_deny("run_command", {"CommandLine": cmd_clean})
        self.assertTrue(blocked)

    def test_tier_1_scratch_permitted(self):
        blocked, _ = is_hard_deny("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype\my_module.py"})
        self.assertFalse(blocked)

    def test_tier_2_brain_artifact_allowed(self):
        self.assertTrue(is_brain_artifact("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\brain\1234\walkthrough.md"}, r"C:\Users\tongn\.gemini\antigravity\brain\1234"))
        self.assertFalse(is_brain_artifact("write_to_file", {"TargetFile": r"C:\Users\tongn\project\app.py"}, r"C:\Users\tongn\.gemini\antigravity\brain\1234"))

    def test_tier_3_risk_classifier(self):
        ws = [r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype"]

        # Safe inspection/test commands qualify for 8s timer
        self.assertTrue(is_eligible_for_auto_accept("run_command", {"CommandLine": "git status"}, ws))
        self.assertTrue(is_eligible_for_auto_accept("run_command", {"CommandLine": "fvm flutter test"}, ws))
        self.assertTrue(is_eligible_for_auto_accept("run_command", {"CommandLine": "npm test"}, ws))

        # Mutating / dangerous commands require 90s full human review
        self.assertFalse(is_eligible_for_auto_accept("run_command", {"CommandLine": "Remove-Item -Recurse folder"}, ws))
        self.assertFalse(is_eligible_for_auto_accept("run_command", {"CommandLine": "npm publish"}, ws))

        # Workspace code edits qualify for 8s timer
        self.assertTrue(is_eligible_for_auto_accept("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype\src\mrc\app.py"}, ws))

        # Root manifests require full human review
        self.assertFalse(is_eligible_for_auto_accept("write_to_file", {"TargetFile": r"C:\Users\tongn\.gemini\antigravity\scratch\mrc-prototype\package.json"}, ws))
        self.assertFalse(is_eligible_for_auto_accept("write_to_file", {"TargetFile": r"C:\Windows\System32\drivers\etc\hosts"}, ws))

    def test_permission_overrides_builder(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "fvm flutter test"}
            }
        }
        overrides = build_permission_overrides(payload)
        self.assertEqual(overrides, ["command(fvm flutter test)"])

if __name__ == "__main__":
    unittest.main()
