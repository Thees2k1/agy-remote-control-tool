#!/usr/bin/env python3
"""
Backward-compatibility root shim for PostToolUse hook.
Delegates to hooks/post_tool_use.py and re-exports cleanup utilities.
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "src")
HOOKS_DIR = os.path.join(SCRIPT_DIR, "hooks")
for p in (SRC_DIR, HOOKS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from mrc.session_grant import purge_transient_grants, CLI_SETTINGS_PATH, GRANTS_PATH
import post_tool_use

def cleanup():
    post_tool_use.main()

if __name__ == "__main__":
    post_tool_use.main()
