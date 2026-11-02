"""
MRC Session Grant Manager
Manages transient Gate-2 permissions in settings.json and cleans them up post-execution.
"""

import os
import json
from typing import Dict, Any, List
from .config import CLI_SETTINGS_PATH, GRANTS_PATH
from .guardrails import build_permission_overrides


def grant_transient_permission(payload: Dict[str, Any]) -> None:
    """
    Tier 4 Session-Scoped Gate-2 Bridge:
    Injects single-use allowlist entries into settings.json for stepIdx,
    which are purged immediately upon tool execution by PostToolUse hook.
    Supports both terminal commands and filesystem file operations.
    """
    if not os.path.exists(CLI_SETTINGS_PATH):
        return

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    overrides = build_permission_overrides(payload)

    cmd = args.get("CommandLine", "").strip() if tool_name == "run_command" else ""
    if not cmd and not overrides:
        return

    try:
        with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)

        allowlist = settings.get("commandAllowlist", [])
        perms = settings.setdefault("permissions", {})
        allow_rules = perms.setdefault("allow", [])
        modified = False

        temp_commands: List[str] = []
        temp_rules: List[str] = []

        if cmd:
            temp_commands.append(cmd)
            if cmd not in allowlist:
                allowlist.append(cmd)
                settings["commandAllowlist"] = allowlist
                modified = True

        for rule in overrides:
            temp_rules.append(rule)
            if rule not in allow_rules:
                allow_rules.append(rule)
                modified = True

        if modified:
            with open(CLI_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

            # Record transient grants for PostToolUse cleanup
            with open(GRANTS_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "temp_commands": temp_commands,
                    "temp_rules": temp_rules,
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
    temp_rules = grants_data.get("temp_rules", [])

    if (temp_commands or temp_rules) and os.path.exists(CLI_SETTINGS_PATH):
        try:
            with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)

            if temp_commands:
                allowlist = settings.get("commandAllowlist", [])
                settings["commandAllowlist"] = [
                    c for c in allowlist if c not in temp_commands
                ]

            perms = settings.get("permissions", {})
            allow_rules = perms.get("allow", [])
            if allow_rules:
                # Filter out exact matches or command wrappers
                settings["permissions"]["allow"] = [
                    r for r in allow_rules
                    if r not in temp_rules
                    and not any(r in (f"command({c})", f"command({c}*)", f"command({c.strip()})") for c in temp_commands)
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

