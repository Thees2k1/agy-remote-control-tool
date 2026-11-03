#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - PreToolUse Lifecycle Hook Entry Point
Orchestrates 4-tier hybrid guardrail evaluation and delegates to daemon/terminal.
"""

import sys
import os
import json
import time
import uuid
import threading
import subprocess
import urllib.request
import urllib.error

# Ensure src/ is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.config import (
    DAEMON_URL, load_config, is_telegram_enabled,
    get_local_grace_period_seconds
)
from mrc.guardrails import (
    is_hard_deny, is_brain_artifact,
    is_eligible_for_auto_accept, build_permission_overrides
)
from mrc.session_grant import grant_transient_permission
from mrc.session_state import is_handsfree_enabled

try:
    import msvcrt
except ImportError:
    msvcrt = None


def check_local_keypress():
    """Poll keyboard for instantaneous desk approvals without blocking."""
    if not msvcrt:
        return None
    try:
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):
                msvcrt.getch()
                return None
            key = ch.decode("utf-8", errors="ignore").lower()
            if key in ('y', '1'):
                return "allow"
            elif key in ('n', '2', 'q'):
                return "deny"
    except Exception:
        pass
    return None


def send_decision(decision, reason="", overrides=None):
    """Emit strictly conformant protojson payload to stdout."""
    res = {"decision": decision}
    if reason:
        res["reason"] = reason
    if overrides and decision == "ask":
        res["permissionOverrides"] = overrides

    out_json = json.dumps(res, indent=2)
    sys.stdout.write(out_json + "\n")
    sys.stdout.flush()

    try:
        log_path = os.path.join(PROJECT_ROOT, "last_decision_sent.json")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(out_json)
    except Exception:
        pass

    sys.exit(0)


def fallback_terminal(reason):
    """Graceful degradation to native terminal confirmation gate."""
    send_decision("ask", f"Fallback to native terminal: {reason}")


def ensure_daemon_running():
    """Verify daemon health; auto-spawn background process if down."""
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/health")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    daemon_script = os.path.join(PROJECT_ROOT, "mrc_daemon.py")
    try:
        if os.name == 'nt':
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                [sys.executable, daemon_script],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
                cwd=PROJECT_ROOT
            )
        else:
            subprocess.Popen(
                [sys.executable, daemon_script],
                start_new_session=True,
                close_fds=True,
                cwd=PROJECT_ROOT
            )
        for _ in range(25):
            time.sleep(0.1)
            try:
                req = urllib.request.Request(f"{DAEMON_URL}/health")
                with urllib.request.urlopen(req, timeout=0.3) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def main():
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        fallback_terminal("Empty stdin input")

    try:
        payload = json.loads(raw_input)
        log_path = os.path.join(PROJECT_ROOT, "last_hook_payload.json")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(raw_input)
    except Exception as e:
        fallback_terminal(f"Failed to parse hook JSON from stdin: {e}")

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    artifact_dir = payload.get("artifactDirectoryPath", "")
    workspace_paths = payload.get("workspacePaths", [])

    # TIER 1: Inviolable Hard Deny
    is_blocked, deny_reason = is_hard_deny(tool_name, args)
    if is_blocked:
        sys.stderr.write(f"\n🛑 [MRC Tier 1 Hard Deny] {deny_reason}\n\n")
        sys.stderr.flush()
        send_decision("deny", deny_reason)

    # TIER 2: Project-Scoped Allowlists (Brain artifacts & safe tools)
    if is_brain_artifact(tool_name, args, artifact_dir):
        send_decision("auto_approve", "Auto-approved internal agent brain artifact")

    overrides = build_permission_overrides(payload)
    conversation_id = payload.get("conversationId", "")

    # Chat-scoped hands-free mode check:
    if not is_handsfree_enabled(conversation_id):
        send_decision("ask", "MRC hands-free disabled for this session; prompt in terminal.")

    config = load_config()
    telegram_enabled = config.get("telegram_enabled", False)
    remote_auto_accept = config.get("remote_auto_accept", False)
    auto_accept_timeout = int(config.get("auto_accept_timeout_seconds", 8))
    default_timeout = int(config.get("timeout_seconds", 90))

    # TIER 3: Scoped Auto-Accept Predicate
    auto_accept_eligible = is_eligible_for_auto_accept(tool_name, args, workspace_paths)
    timeout_sec = auto_accept_timeout if (remote_auto_accept and auto_accept_eligible) else default_timeout

    cmd_info = args.get("CommandLine", "") or args.get("TargetFile", "") or tool_name

    # LOCAL-ONLY WORKSTATION MODE (When Telegram is paused)
    if not telegram_enabled:
        sys.stderr.write(
            f"\n⚡ [Mobile Remote Control: Local Machine Mode (Telegram Paused)]\n"
            f"   Tool: {tool_name} -> {cmd_info[:60]}\n"
            f"   👉 Auto-approving for local execution on this workstation.\n\n"
        )
        sys.stderr.flush()
        grant_transient_permission(payload)
        send_decision("auto_approve", "Local workstation execution approved (Telegram paused)")

    # STAGE 1: Desk-First Local Grace Window (Active only in CLI / interactive terminal)
    transcript_path = payload.get("transcriptPath", "").replace("\\", "/")
    is_cli = "antigravity-cli" in transcript_path
    grace_period = get_local_grace_period_seconds() if is_cli else 0

    if grace_period > 0:
        sys.stderr.write(
            f"\n⚡ [Desk Grace Window ({grace_period}s)] {tool_name} -> {cmd_info[:60]}\n"
            f"   👉 Press [Y] to approve locally | [N] to deny | (Escalating to phone in {grace_period}s)...\n\n"
        )
        sys.stderr.flush()

        grace_start = time.time()
        while (time.time() - grace_start) < grace_period:
            key = check_local_keypress()
            if key == "allow":
                sys.stderr.write(f"\n✅ [Local Desk Approved] Workstation keypress [Y]\n\n")
                sys.stderr.flush()
                grant_transient_permission(payload)
                send_decision("auto_approve", "Approved at workstation keyboard")
                return
            elif key == "deny":
                sys.stderr.write(f"\n❌ [Local Desk Denied] Workstation keypress [N]\n\n")
                sys.stderr.flush()
                send_decision("deny", "Denied at workstation keyboard")
                return
            time.sleep(0.05)

    # STAGE 2: AFK Escalation to Remote Mobile Approval Mode (Daemon active)
    if grace_period > 0:
        sys.stderr.write(
            f"\n📡 [AFK Escalation] No local desk input detected — escalating to Telegram (@antiex_bot)...\n"
        )
        sys.stderr.flush()

    daemon_ok = ensure_daemon_running()
    if not daemon_ok:
        sys.stderr.write("\n⚠️ [MRC] Background daemon unavailable, falling back to terminal.\n")
        sys.stderr.flush()
        fallback_terminal("MRC background daemon unavailable")

    req_id = str(uuid.uuid4())[:8]
    decision_box = {"decision": None, "source": None}
    stop_event = threading.Event()

    def remote_request_thread():
        try:
            req_data = json.dumps({
                "req_id": req_id,
                "payload": payload,
                "timeout_seconds": timeout_sec,
                "auto_accept_eligible": auto_accept_eligible
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{DAEMON_URL}/request_approval",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec + 5) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    decision_box["decision"] = res_json.get("decision")
                    decision_box["source"] = res_json.get("source")
                    stop_event.set()
        except Exception as e:
            decision_box["decision"] = "ask"
            decision_box["source"] = f"Daemon error: {e}"
            stop_event.set()

    t = threading.Thread(target=remote_request_thread, daemon=True)
    t.start()

    countdown_text = f"⏱️ Auto-accepts in {timeout_sec}s unless denied.\n" if (remote_auto_accept and auto_accept_eligible) else ""
    sys.stderr.write(
        f"\n⚡ [Mobile Remote Control Active] Request dispatched to phone (@antiex_bot)!\n"
        f"   {countdown_text}"
        f"   👉 Press [Y] to approve locally | [N] to deny | or tap your phone...\n\n"
    )
    sys.stderr.flush()

    start_time = time.time()
    while not stop_event.is_set() and (time.time() - start_time) < (timeout_sec + 3):
        key = check_local_keypress()
        if key:
            decision_box["decision"] = key
            decision_box["source"] = "Workstation Terminal (Keyboard)"
            try:
                resolve_data = json.dumps({
                    "req_id": req_id,
                    "decision": key,
                    "source": "Workstation Terminal (Keyboard)"
                }).encode("utf-8")
                urllib.request.urlopen(
                    urllib.request.Request(f"{DAEMON_URL}/resolve", data=resolve_data, headers={"Content-Type": "application/json"}),
                    timeout=2
                )
            except Exception:
                pass
            stop_event.set()
            break
        time.sleep(0.05)

    decision = decision_box.get("decision")
    source = decision_box.get("source") or "timeout"

    if decision == "allow":
        sys.stderr.write(f"\n✅ [MRC Approved] Decision: AUTO_APPROVE via {source}\n\n")
        sys.stderr.flush()
        grant_transient_permission(payload)
        send_decision("auto_approve", f"Approved via {source}")
    elif decision == "deny":
        sys.stderr.write(f"\n❌ [MRC Denied] Decision: DENY via {source}\n\n")
        sys.stderr.flush()
        send_decision("deny", f"Denied via {source}")
    else:
        sys.stderr.write(f"\n⌛ [MRC Timeout ({timeout_sec}s)] Dropping to native terminal prompt.\n\n")
        sys.stderr.flush()
        fallback_terminal("Remote timeout expired")


if __name__ == "__main__":
    main()
