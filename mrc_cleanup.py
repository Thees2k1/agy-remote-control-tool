#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - PostToolUse Cleanup Hook
Cleans up temporary session-scoped grants created during PreToolUse,
ensuring settings.json remains pristine and request-review posture is maintained.
"""

import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GRANTS_PATH = os.path.join(SCRIPT_DIR, "session_grants.json")
CLI_SETTINGS_PATH = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")


def cleanup():
    # Read PostToolUse payload from stdin
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
        step_idx = payload.get("stepIdx")
    except Exception:
        step_idx = None

    # Check if there are active transient grants
    if os.path.exists(GRANTS_PATH):
        try:
            with open(GRANTS_PATH, "r", encoding="utf-8") as f:
                grants_data = json.load(f)
        except Exception:
            grants_data = {}

        temp_commands = grants_data.get("temp_commands", [])

        # Clean up temporary commands from CLI settings.json if present
        if temp_commands and os.path.exists(CLI_SETTINGS_PATH):
            try:
                with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                allowlist = settings.get("commandAllowlist", [])
                # Remove transient commands
                settings["commandAllowlist"] = [
                    cmd for cmd in allowlist if cmd not in temp_commands
                ]

                # Clean up permissions.allow if present
                perms = settings.get("permissions", {})
                allow_rules = perms.get("allow", [])
                if allow_rules:
                    settings["permissions"]["allow"] = [
                        r for r in allow_rules
                        if not any(r in (f"command({c})", f"command({c}*)", f"command({c.strip()})") for c in temp_commands)
                    ]
                    if not settings["permissions"]["allow"]:
                        settings.pop("permissions", None)

                with open(CLI_SETTINGS_PATH, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)
            except Exception:
                pass

        # Clear session grants
        try:
            os.remove(GRANTS_PATH)
        except Exception:
            pass

    # PostToolUse contract expects empty JSON object {}
    sys.stdout.write("{}\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    cleanup()
