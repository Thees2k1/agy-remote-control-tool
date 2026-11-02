#!/usr/bin/env python3
"""
Backward-compatibility root shim for PreToolUse hook.
Delegates to hooks/pre_tool_use.py and re-exports core utilities.
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "src")
HOOKS_DIR = os.path.join(SCRIPT_DIR, "hooks")
for p in (SRC_DIR, HOOKS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from mrc.guardrails import is_hard_deny, is_eligible_for_auto_accept, is_brain_artifact, build_permission_overrides
from mrc.session_grant import grant_transient_permission, purge_transient_grants
from mrc.config import CLI_SETTINGS_PATH, GRANTS_PATH, CONFIG_PATH, DAEMON_URL, load_config
import pre_tool_use

if __name__ == "__main__":
    pre_tool_use.main()
