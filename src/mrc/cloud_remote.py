"""
Antigravity Cloud Remote Interception & Broadcaster.

Interacts with the native `agy remote-control` CLI command, extracts the
cloud instance name, and broadcasts connection URLs to Telegram.
"""

import os
import re
import subprocess
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CLOUD_REMOTE_BASE_URL = "https://antigravity.google.com"

def parse_instance_name(output_text: str) -> Optional[str]:
    """
    Extracts the instance name from `agy remote-control status` output.
    Example line:
    'Instance name: workally-starlit-mars (find it at https://antigravity.google.com)'
    """
    if not output_text:
        return None
    
    match = re.search(r"Instance name:\s*([a-zA-Z0-9_\-]+)", output_text)
    if match:
        name = match.group(1).strip()
        if name.lower() not in ("not", "none", "unknown"):
            return name
    return None

def get_cloud_remote_status() -> Dict[str, Any]:
    """
    Queries `agy remote-control status`.
    """
    try:
        res = subprocess.run(
            ["agy", "remote-control", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=True
        )
        combined = f"{res.stdout}\n{res.stderr}"
        instance_name = parse_instance_name(combined)
        return {
            "ok": res.returncode == 0,
            "raw_output": combined.strip(),
            "instance_name": instance_name,
            "url": CLOUD_REMOTE_BASE_URL if instance_name else None
        }
    except Exception as e:
        logger.error(f"Failed to query agy remote-control status: {e}")
        return {
            "ok": False,
            "error": str(e),
            "instance_name": None,
            "url": None
        }

def start_cloud_remote(session_only: bool = True) -> Dict[str, Any]:
    """
    Starts the Antigravity remote-control daemon.
    """
    cmd = ["agy", "remote-control", "start"]
    if session_only:
        cmd.append("--session")

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            shell=True
        )
        combined = f"{res.stdout}\n{res.stderr}"
        instance_name = parse_instance_name(combined)
        if not instance_name:
            # Query status to see if it was assigned
            status = get_cloud_remote_status()
            instance_name = status.get("instance_name")

        return {
            "ok": res.returncode == 0 or "started" in combined.lower(),
            "raw_output": combined.strip(),
            "instance_name": instance_name,
            "url": CLOUD_REMOTE_BASE_URL if instance_name else None
        }
    except Exception as e:
        logger.error(f"Failed to start agy remote-control: {e}")
        return {
            "ok": False,
            "error": str(e),
            "instance_name": None,
            "url": None
        }

def broadcast_cloud_remote_url(telegram_client=None, chat_id: Optional[str] = None) -> bool:
    """
    Extracts the cloud remote link and dispatches an announcement message to Telegram.
    """
    status = get_cloud_remote_status()
    instance_name = status.get("instance_name")
    if not instance_name:
        logger.warning("No active cloud remote instance name found to broadcast.")
        return False

    message_html = (
        "🌐 <b>Antigravity Cloud Remote Active</b>\n\n"
        f"Instance Name: <code>{instance_name}</code>\n"
        f"Direct Link: <a href=\"{CLOUD_REMOTE_BASE_URL}\">{CLOUD_REMOTE_BASE_URL}</a>\n\n"
        "<i>Open the link in your mobile browser to view or pair with this session.</i>"
    )

    if telegram_client is None:
        try:
            from mrc.telegram_client import TelegramClient
            telegram_client = TelegramClient()
        except Exception as e:
            logger.error(f"Could not initialize TelegramClient: {e}")
            return False

    try:
        res = telegram_client.send_message(message_html, chat_id=chat_id)
        return bool(res and res.get("ok"))
    except Exception as e:
        logger.error(f"Failed to broadcast cloud remote URL: {e}")
        return False
