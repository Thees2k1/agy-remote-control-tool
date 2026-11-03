#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - PostToolUse Lifecycle Hook Entry Point
Purges single-use transient Gate-2 permissions from settings.json and cleans up state.
Also checks if an agy remote-control command was executed to broadcast the URL.
"""

import sys
import os
import json
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.session_grant import purge_transient_grants
from mrc.cloud_remote import broadcast_cloud_remote_url

logger = logging.getLogger("mrc.post_tool_use")

def handle_post_tool_use(payload_str: str) -> dict:
    """
    Cleans up transient grants and checks for remote-control triggers.
    """
    # 1. Purge transient grants
    try:
        purge_transient_grants()
    except Exception as e:
        logger.error(f"Error purging transient grants: {e}")

    # 2. Check if the tool execution was an agy remote-control command
    if payload_str:
        try:
            data = json.loads(payload_str)
            tool_call = data.get("toolCall", {})
            name = tool_call.get("name")
            args = tool_call.get("args", {})
            if name == "run_command":
                cmd = args.get("CommandLine", "")
                if "remote-control" in cmd:
                    broadcast_cloud_remote_url()
        except Exception as e:
            logger.debug(f"PostToolUse inspection skipped/failed: {e}")

    # PostToolUse contract expects empty JSON object {}
    return {}

def main():
    payload_str = ""
    try:
        if not sys.stdin.isatty():
            payload_str = sys.stdin.read()
    except Exception:
        pass

    out = handle_post_tool_use(payload_str)
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
    sys.exit(0)

if __name__ == "__main__":
    main()
