#!/usr/bin/env python3
"""
Backward-compatibility root shim for MRC Daemon.
Delegates to src/mrc/daemon.py.
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.daemon import main, start_daemon, ThreadedHTTPServer, RequestHandler, pending_requests, pending_lock

if __name__ == "__main__":
    main()
