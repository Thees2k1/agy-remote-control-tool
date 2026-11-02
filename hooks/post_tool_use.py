#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - PostToolUse Lifecycle Hook Entry Point
Purges single-use transient Gate-2 permissions from settings.json and cleans up state.
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.session_grant import purge_transient_grants


def main():
    # Read optional PostToolUse payload from stdin safely without blocking
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass

    # Purge transient grants
    purge_transient_grants()

    # PostToolUse contract expects empty JSON object {}
    sys.stdout.write("{}\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
