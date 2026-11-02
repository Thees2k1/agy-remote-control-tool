"""
MRC Configuration & Path Registry
Centralizes path resolution, user configuration loading, and environment defaults.
"""

import os
import json

# Project directory structure
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SRC_DIR))

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
GRANTS_PATH = os.path.join(PROJECT_ROOT, "session_grants.json")
CLI_SETTINGS_PATH = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")

# Daemon networking defaults
DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 48201
DAEMON_URL = f"http://{DAEMON_HOST}:{DAEMON_PORT}"


# Timing defaults
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_AUTO_ACCEPT_TIMEOUT_SECONDS = 8
DEFAULT_LOCAL_GRACE_PERIOD_SECONDS = 4


def load_config() -> dict:
    """Load configuration from config.json with fallback defaults."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def is_telegram_enabled() -> bool:
    """Check if remote Telegram dispatch is active."""
    return load_config().get("telegram_enabled", False)


def get_local_grace_period_seconds() -> int:
    """Get local desk keyboard grace period before escalating to Telegram."""
    val = load_config().get("local_grace_period_seconds", DEFAULT_LOCAL_GRACE_PERIOD_SECONDS)
    try:
        return max(0, int(val))
    except (ValueError, TypeError):
        return DEFAULT_LOCAL_GRACE_PERIOD_SECONDS

