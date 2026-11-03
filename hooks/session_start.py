#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - SessionStart Lifecycle Hook Entry Point
Executes when a new agent conversation/session is initialized.
Checks if cloud remote is active or configured to auto-broadcast.
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

from mrc.config import load_config
from mrc.cloud_remote import broadcast_cloud_remote_url

logger = logging.getLogger("mrc.session_start")

def handle_session_start(payload_str: str) -> dict:
    """
    Processes the SessionStart payload.
    """
    try:
        data = json.loads(payload_str) if payload_str else {}
    except Exception:
        data = {}

    config = load_config()
    # If auto-broadcast is enabled (or true by default if cloud remote is active)
    if config.get("auto_broadcast_cloud_remote", True):
        try:
            broadcast_cloud_remote_url()
        except Exception as e:
            logger.debug(f"SessionStart cloud remote broadcast skipped/failed: {e}")

    # SessionStart contract expects {}
    return {}

def main():
    payload_str = ""
    try:
        if not sys.stdin.isatty():
            payload_str = sys.stdin.read()
    except Exception:
        pass

    out = handle_session_start(payload_str)
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
    sys.exit(0)

if __name__ == "__main__":
    main()
