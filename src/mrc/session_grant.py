"""
MRC Session Grant Manager
Manages transient Gate-2 permissions in settings.json and cleans them up post-execution.
"""

import os
import json
from typing import Dict, Any
from .config import CLI_SETTINGS_PATH, GRANTS_PATH


def grant_transient_permission(payload: Dict[str, Any]) -> None:
    """
    Tier 4 Session-Scoped Gate-2 Bridge:
    Injects a single-use allowlist entry into settings.json for stepIdx,
    which is purged immediately upon tool execution by PostToolUse hook.
    """
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if tool_name == "run_command" and os.path.exists(CLI_SETTINGS_PATH):
        cmd = args.get("CommandLine", "").strip()
        if not cmd:
            return
        try:
            with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)

            allowlist = settings.get("commandAllowlist", [])
            perm_rule = f"command({cmd})"
            perms = settings.setdefault("permissions", {})
            allow_rules = perms.setdefault("allow", [])
            modified = False

            if cmd not in allowlist:
                allowlist.append(cmd)
                settings["commandAllowlist"] = allowlist
                modified = True
            if perm_rule not in allow_rules:
                allow_rules.append(perm_rule)
                modified = True

            if modified:
                with open(CLI_SETTINGS_PATH, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)

                # Record transient grant for PostToolUse cleanup
                with open(GRANTS_PATH, "w", encoding="utf-8") as f:
                    json.dump({
                        "temp_commands": [cmd],
                        "stepIdx": payload.get("stepIdx")
                    }, f, indent=2)
        except Exception:
            pass


def purge_transient_grants() -> None:
    """
    Tier 4 PostToolUse Cleanup:
    Removes temporary session-scoped grants from settings.json and purges session_grants.json.
    """
    if not os.path.exists(GRANTS_PATH):
        return

    try:
        with open(GRANTS_PATH, "r", encoding="utf-8") as f:
            grants_data = json.load(f)
    except Exception:
        grants_data = {}

    temp_commands = grants_data.get("temp_commands", [])

    if temp_commands and os.path.exists(CLI_SETTINGS_PATH):
        try:
            with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)

            allowlist = settings.get("commandAllowlist", [])
            settings["commandAllowlist"] = [
                cmd for cmd in allowlist if cmd not in temp_commands
            ]

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

    try:
        os.remove(GRANTS_PATH)
    except Exception:
        pass
