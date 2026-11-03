"""
Mobile Remote Control (MRC) Unified CLI.

Usage:
  mrc serve              Start the MRC authorization daemon
  mrc close              Stop the MRC authorization daemon
  mrc status             Display status of daemon, port 48201, and cloud remote
  mrc remote             Start agy cloud remote and broadcast URL to Telegram
  mrc handsfree [on|off] Toggle default hands-free mode
  mrc install [--global] Link this repository as an Antigravity plugin
"""

import sys
import os
import argparse
import logging
from typing import Optional

from mrc.config import PROJECT_ROOT, DAEMON_URL, DAEMON_PORT, load_config
from mrc.mcp_server import is_daemon_alive, start_daemon_process, stop_daemon_processes
from mrc.cloud_remote import get_cloud_remote_status, start_cloud_remote, broadcast_cloud_remote_url

logger = logging.getLogger("mrc.cli")

def install_plugin(global_install: bool = True) -> int:
    """
    Registers this repository into Antigravity plugins directory.
    """
    target_base = os.path.expanduser("~/.gemini/config/plugins") if global_install else os.path.join(os.getcwd(), ".agents", "plugins")
    target_dir = os.path.join(target_base, "mobile-remote-control")

    try:
        os.makedirs(target_base, exist_ok=True)
        if os.path.exists(target_dir):
            sys.stdout.write(f"Plugin target directory already exists at: {target_dir}\n")
            return 0

        # Create directory symlink or junction on Windows
        if os.name == "nt":
            import subprocess
            subprocess.run(f'cmd /c mklink /J "{target_dir}" "{PROJECT_ROOT}"', shell=True, check=True)
        else:
            os.symlink(PROJECT_ROOT, target_dir, target_is_directory=True)

        sys.stdout.write(f"Successfully installed MRC plugin to: {target_dir}\n")
        return 0
    except Exception as e:
        sys.stderr.write(f"Failed to link plugin: {e}\n")
        return 1

def main(args: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mrc",
        description="Mobile Remote Control (MRC) CLI for Google Antigravity"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    subparsers.add_parser("serve", help="Start the background authorization daemon")
    subparsers.add_parser("close", help="Stop the background authorization daemon")
    subparsers.add_parser("status", help="Inspect status of daemon and cloud remote")
    subparsers.add_parser("remote", help="Start cloud remote and send link to Telegram")

    hf_parser = subparsers.add_parser("handsfree", help="Toggle hands-free mode")
    hf_parser.add_argument("state", choices=["on", "off", "status"], nargs="?", default="status")

    install_parser = subparsers.add_parser("install", help="Install as Antigravity plugin")
    install_parser.add_argument("--global", dest="is_global", action="store_true", default=True, help="Install globally to ~/.gemini/config/plugins")

    parsed = parser.parse_args(args)

    if not parsed.subcommand or parsed.subcommand == "status":
        daemon_active = is_daemon_alive()
        cloud_status = get_cloud_remote_status()
        sys.stdout.write("=== Mobile Remote Control (MRC) Status ===\n")
        sys.stdout.write(f"Daemon:        {'running (listening on port ' + str(DAEMON_PORT) + ')' if daemon_active else 'stopped'}\n")
        sys.stdout.write(f"Cloud Remote:  {cloud_status.get('instance_name') or 'inactive'}\n")
        if cloud_status.get("url"):
            sys.stdout.write(f"Cloud Link:    {cloud_status.get('url')}\n")
        sys.stdout.write("==========================================\n")
        return 0

    elif parsed.subcommand == "serve":
        if is_daemon_alive():
            sys.stdout.write("MRC Daemon is already running.\n")
            return 0
        started = start_daemon_process()
        if started:
            sys.stdout.write(f"Started MRC Daemon on port {DAEMON_PORT}.\n")
            return 0
        else:
            sys.stderr.write("Failed to start MRC Daemon.\n")
            return 1

    elif parsed.subcommand == "close":
        stopped = stop_daemon_processes()
        if stopped:
            sys.stdout.write("Stopped MRC Daemon processes.\n")
            return 0
        else:
            sys.stderr.write("Failed to stop MRC Daemon.\n")
            return 1

    elif parsed.subcommand == "remote":
        sys.stdout.write("Initializing Antigravity Cloud Remote...\n")
        start_cloud_remote(session_only=True)
        sent = broadcast_cloud_remote_url()
        status = get_cloud_remote_status()
        inst = status.get("instance_name") or "unknown"
        if sent:
            sys.stdout.write(f"Cloud Remote '{inst}' active and pairing link sent to Telegram!\n")
        else:
            sys.stdout.write(f"Cloud Remote '{inst}' active. (Telegram broadcast pending or disabled in config)\n")
        return 0

    elif parsed.subcommand == "handsfree":
        from mrc.session_state import set_handsfree, is_handsfree_enabled
        if parsed.state == "on":
            set_handsfree("global", True)
            sys.stdout.write("Hands-free mode enabled.\n")
        elif parsed.state == "off":
            set_handsfree("global", False)
            sys.stdout.write("Hands-free mode disabled.\n")
        else:
            state = is_handsfree_enabled("global")
            sys.stdout.write(f"Hands-free mode is currently: {'ON' if state else 'OFF'}\n")
        return 0

    elif parsed.subcommand == "install":
        return install_plugin(global_install=parsed.is_global)

    return 0

if __name__ == "__main__":
    sys.exit(main())
