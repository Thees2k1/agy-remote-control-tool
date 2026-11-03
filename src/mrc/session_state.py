"""
MRC Session State Manager.

Maintains per-conversation state, specifically chat-scoped hands-free mode
(`mrc --handsfree` vs `mrc --no-handsfree`).
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from mrc.config import SESSION_STATE_PATH, load_config

logger = logging.getLogger(__name__)

def _read_all_states() -> Dict[str, Any]:
    if not os.path.exists(SESSION_STATE_PATH):
        return {}
    try:
        with open(SESSION_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading session states: {e}")
        return {}

def _write_all_states(states: Dict[str, Any]) -> None:
    try:
        temp_path = f"{SESSION_STATE_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(states, f, indent=2)
        os.replace(temp_path, SESSION_STATE_PATH)
    except Exception as e:
        logger.error(f"Error writing session states: {e}")

def get_all_session_states() -> Dict[str, Any]:
    return _read_all_states()

def is_handsfree_enabled(conversation_id: Optional[str]) -> bool:
    """
    Checks if hands-free mode is enabled for the given conversation ID.
    If not explicitly set for this conversation, falls back to config `handsfree_default` (default True).
    """
    default_val = load_config().get("handsfree_default", True)
    if not conversation_id:
        return default_val

    states = _read_all_states()
    session = states.get(conversation_id)
    if session is not None and "handsfree" in session:
        return bool(session["handsfree"])

    return default_val

def set_handsfree(conversation_id: str, enabled: bool) -> None:
    """
    Sets the hands-free mode for a specific conversation.
    """
    if not conversation_id:
        return

    states = _read_all_states()
    if conversation_id not in states:
        states[conversation_id] = {}
    states[conversation_id]["handsfree"] = bool(enabled)
    _write_all_states(states)

def clear_session_state(conversation_id: str) -> None:
    """
    Removes the state for a specific conversation.
    """
    if not conversation_id:
        return

    states = _read_all_states()
    if conversation_id in states:
        del states[conversation_id]
        _write_all_states(states)
