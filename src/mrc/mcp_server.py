"""
MRC Management MCP Server.

Provides a Model Context Protocol (MCP) stdio interface for managing the MRC daemon,
toggling chat-scoped hands-free mode, and coordinating Antigravity Cloud Remote links.
"""

import sys
import os
import json
import logging
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List

from mrc.config import DAEMON_URL, DAEMON_PORT, PROJECT_ROOT
from mrc.cloud_remote import get_cloud_remote_status, start_cloud_remote, broadcast_cloud_remote_url
from mrc.session_state import set_handsfree, is_handsfree_enabled

logger = logging.getLogger("mrc.mcp")

def is_daemon_alive() -> bool:
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/health")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def stop_daemon_processes() -> bool:
    try:
        if os.name == "nt":
            # Find python processes running mrc_daemon or mrc.daemon
            cmd = 'powershell.exe -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*mrc*daemon*\' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"'
            subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
        else:
            subprocess.run(["pkill", "-f", "mrc_daemon"], capture_output=True, timeout=10)
        return True
    except Exception as e:
        logger.error(f"Failed to stop daemon processes: {e}")
        return False

def start_daemon_process() -> bool:
    if is_daemon_alive():
        return True
    try:
        daemon_script = os.path.join(PROJECT_ROOT, "mrc_daemon.py")
        if os.name == "nt":
            subprocess.Popen(
                ["python", daemon_script],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["python3", daemon_script],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
        return True
    except Exception as e:
        logger.error(f"Failed to start daemon process: {e}")
        return False

TOOLS_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": "mrc_status",
        "description": "Inspects the status of the MRC background daemon and Antigravity Cloud Remote pairing.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "mrc_serve",
        "description": "Starts the MRC background authorization daemon on port 48201.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "mrc_close",
        "description": "Stops the MRC background authorization daemon and releases port 48201.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "mrc_toggle_handsfree",
        "description": "Toggles chat-scoped hands-free mode for a conversation (routes review to Telegram vs terminal).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The conversation/session ID to configure."
                },
                "enabled": {
                    "type": "boolean",
                    "description": "True for hands-free out-of-band mobile reviews; False for desktop terminal prompts."
                }
            },
            "required": ["conversation_id", "enabled"]
        }
    },
    {
        "name": "mrc_cloud_remote",
        "description": "Starts Antigravity Cloud Remote daemon (if needed) and broadcasts pairing URL to Telegram.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_if_stopped": {
                    "type": "boolean",
                    "description": "Whether to start the daemon if not currently active."
                }
            }
        }
    }
]

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    if name == "mrc_status":
        daemon_active = is_daemon_alive()
        cloud_status = get_cloud_remote_status()
        status_text = (
            f"MRC Daemon: {'running (port 48201)' if daemon_active else 'stopped'}\n"
            f"Cloud Remote Instance: {cloud_status.get('instance_name') or 'none'}\n"
            f"Cloud Remote URL: {cloud_status.get('url') or 'none'}"
        )
        return status_text

    elif name == "mrc_serve":
        if is_daemon_alive():
            return "MRC Daemon is already running on port 48201."
        started = start_daemon_process()
        return "Started MRC Daemon on port 48201." if started else "Failed to start MRC Daemon."

    elif name == "mrc_close":
        stopped = stop_daemon_processes()
        return "Stopped MRC Daemon processes." if stopped else "Failed to stop MRC Daemon."

    elif name == "mrc_toggle_handsfree":
        conv_id = arguments.get("conversation_id", "")
        enabled = bool(arguments.get("enabled", True))
        set_handsfree(conv_id, enabled)
        return f"Hands-free mode set to {enabled} for conversation '{conv_id}'."

    elif name == "mrc_cloud_remote":
        start_needed = arguments.get("start_if_stopped", True)
        if start_needed:
            start_cloud_remote()
        sent = broadcast_cloud_remote_url()
        status = get_cloud_remote_status()
        return (
            f"Cloud Remote Instance: {status.get('instance_name')}\n"
            f"Broadcast to Telegram: {'Success' if sent else 'Pending/Failed'}"
        )

    else:
        return f"Unknown tool: {name}"

def handle_mcp_request(req: Dict[str, Any]) -> Dict[str, Any]:
    msg_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mrc-manager",
                    "version": "0.1.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS_REGISTRY
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        result_text = execute_tool(tool_name, tool_args)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }
        }

    elif method == "notifications/initialized":
        return {}

    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found."
            }
        }

def run_stdio_server():
    """Stdio loop for MCP server."""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_mcp_request(req)
            if resp:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_stdio_server()
