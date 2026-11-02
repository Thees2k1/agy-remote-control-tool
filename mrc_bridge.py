#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - PreToolUse Bridge
Implements ADR-001 Hybrid Ask-First Guardrails:
- Tier 1: Inviolable Hard Deny on sensitive configs, credentials, and destructive VCS
- Tier 2: Project-Scoped Allowlists (brain artifacts, safe read tools)
- Tier 3: Scoped Auto-Accept Predicate (8s timer for low-risk actions only)
- Tier 4: Session-Scoped Gate-2 Bridge for affirmative human mobile approvals
"""

import sys
import os
import re
import json
import time
import uuid
import threading
import subprocess
import urllib.request
import urllib.parse
import urllib.error

try:
    import msvcrt
except ImportError:
    msvcrt = None


def check_local_keypress():
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


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
DAEMON_PATH = os.path.join(SCRIPT_DIR, "mrc_daemon.py")
GRANTS_PATH = os.path.join(SCRIPT_DIR, "session_grants.json")
CLI_SETTINGS_PATH = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")
DAEMON_URL = "http://127.0.0.1:48201"


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def is_hard_deny(tool_name, args):
    """
    Tier 1 Inviolable Hard Deny Gate:
    Prevents unauthorized tampering with system configs, credentials, and destructive VCS.
    """
    if tool_name in ("write_to_file", "replace_file_content"):
        target = args.get("TargetFile", "").replace("/", "\\").lower()
        common_forbidden = [
            "hooks.json",
            "settings.json",
            "admin_settings.json",
            "\\.ssh\\",
            "id_rsa",
            "\\.aws\\",
            "\\.env"
        ]
        if "\\.gemini\\antigravity\\scratch\\" in target or "\\brain\\" in target:
            forbidden_substrings = common_forbidden
        else:
            forbidden_substrings = [
                "\\.gemini\\config\\",
                "\\.gemini\\antigravity-cli\\",
                "\\.gemini\\antigravity\\builtin\\"
            ] + common_forbidden

        for sub in forbidden_substrings:
            if sub in target:
                return True, f"Blocked modification targeting protected path: {target}"
    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "").strip()
        cmd_lower = cmd.lower()

        # Dangerous git commands
        if re.search(r"\bgit\s+push\b.*(--force|-f\b)", cmd_lower):
            return True, "Blocked destructive git push --force command."
        if re.search(r"\bgit\s+reset\b.*--hard", cmd_lower):
            return True, "Blocked destructive git reset --hard command."
        if re.search(r"\bgit\s+clean\b.*-[a-z]*f", cmd_lower):
            return True, "Blocked destructive git clean -f command."

        # Tampering with system configs via shell
        if re.search(r"(hooks\.json|settings\.json|\.gemini)", cmd_lower) and re.search(r"(>|>>|set-content|out-file|tee|echo\b)", cmd_lower):
            return True, "Blocked shell command targeting agent safety configurations."

    return False, ""


def is_eligible_for_auto_accept(tool_name, args, workspace_paths):
    """
    Tier 3 Scoped Auto-Accept Predicate:
    Only non-destructive workspace file edits and safe inspection/test commands
    qualify for the 8-second countdown. Everything else requires full human review.
    """
    if tool_name in ("write_to_file", "replace_file_content"):
        target = os.path.abspath(args.get("TargetFile", ""))
        # Must be strictly within configured workspace
        in_workspace = any(
            target.lower().startswith(os.path.abspath(ws).lower())
            for ws in workspace_paths
        )
        if not in_workspace:
            return False
        # Disallow dotfiles and root configs
        basename = os.path.basename(target).lower()
        if basename.startswith(".") or basename in ("package.json", "pubspec.yaml", "pyproject.toml"):
            return False
        return True

    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "").strip()
        cmd_lower = cmd.lower()
        safe_prefixes = [
            "git status", "git diff", "git log", "git branch",
            "fvm flutter test", "fvm flutter analyze", "fvm dart format",
            "melos list", "npm test", "npm run lint", "pytest",
            "get-childitem", "dir", "ls", "echo", "type", "cat"
        ]
        return any(cmd_lower.startswith(prefix) for prefix in safe_prefixes)

    return False


def grant_transient_permission(payload):
    """
    Tier 4 Session-Scoped Gate-2 Bridge:
    Injects a single-use allowlist entry into settings.json for stepIdx,
    which is purged immediately upon tool execution by mrc_cleanup.py (PostToolUse).
    """
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if tool_name == "run_command" and os.path.exists(CLI_SETTINGS_PATH):
        cmd = args.get("CommandLine", "").strip()
        if not cmd:
            return
        try:
            with open(CLI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            allowlist = settings.get("commandAllowlist", [])
            perm_rule = f"command({cmd})"
            perms = settings.setdefault("permissions", {})
            allow_rules = perms.setdefault("allow", [])
            modified = False
            if cmd not in allowlist:
                allowlist.append(cmd)
                settings["commandAllowlist"] = allowlist
                modified = True
            if perm_rule not in allow_rules:
                allow_rules.append(perm_rule)
                modified = True

            if modified:
                with open(CLI_SETTINGS_PATH, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)

                # Record transient grant for PostToolUse cleanup
                with open(GRANTS_PATH, "w", encoding="utf-8") as f:
                    json.dump({
                        "temp_commands": [cmd],
                        "stepIdx": payload.get("stepIdx")
                    }, f, indent=2)
        except Exception:
            pass


def ensure_daemon_running():
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/health")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    try:
        flags = 0
        if os.name == 'nt':
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        subprocess.Popen(
            [sys.executable, DAEMON_PATH],
            cwd=SCRIPT_DIR,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(20):
            time.sleep(0.1)
            try:
                req = urllib.request.Request(f"{DAEMON_URL}/health")
                with urllib.request.urlopen(req, timeout=0.5) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
    except Exception as e:
        sys.stderr.write(f"[MRC] Failed to spawn background daemon: {e}\n")
    return False


def build_permission_overrides(payload):
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    overrides = []
    if tool_name == "run_command":
        cmd = args.get("CommandLine", "")
        if cmd:
            overrides.append(f"command({cmd})")
    elif tool_name in ("write_to_file", "replace_file_content"):
        target = args.get("TargetFile", "")
        if target:
            overrides.append(f"write_file({target})")
            overrides.append(f"edit_file({target})")
    return overrides


def send_decision(decision, reason, overrides=None):
    out = {
        "decision": decision,
        "reason": reason,
    }
    if overrides and decision == "allow":
        out["permissionOverrides"] = overrides

    try:
        with open(os.path.join(SCRIPT_DIR, "last_decision_sent.json"), "w", encoding="utf-8") as debug_out:
            json.dump(out, debug_out, indent=2)
    except Exception:
        pass

    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()
    sys.exit(0)


def fallback_terminal(reason):
    out = {"decision": "ask", "reason": reason}
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()
    sys.exit(0)


def main():
    config = load_config()
    telegram_enabled = config.get("telegram_enabled", False)
    remote_auto_accept = config.get("remote_auto_accept", False)
    auto_accept_timeout = int(config.get("auto_accept_timeout_seconds", 8))
    default_timeout = int(config.get("timeout_seconds", 90))

    # Read hook payload from stdin
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            fallback_terminal("Empty stdin payload")
        payload = json.loads(raw_input)
        try:
            with open(os.path.join(SCRIPT_DIR, "last_hook_payload.json"), "w", encoding="utf-8") as debug_f:
                debug_f.write(raw_input)
        except Exception:
            pass
    except Exception as e:
        fallback_terminal(f"Failed to parse hook JSON from stdin: {e}")

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    target = args.get("TargetFile", "")
    artifact_dir = payload.get("artifactDirectoryPath", "")
    workspace_paths = payload.get("workspacePaths", [])

    # TIER 1: Inviolable Hard Deny
    is_blocked, deny_reason = is_hard_deny(tool_name, args)
    if is_blocked:
        sys.stderr.write(f"\n🛑 [MRC Tier 1 Hard Deny] {deny_reason}\n\n")
        sys.stderr.flush()
        send_decision("deny", deny_reason)

    # TIER 2: Project-Scoped Allowlists (Brain artifacts & safe tools)
    if tool_name in ("write_to_file", "replace_file_content"):
        norm_target = target.replace("/", "\\").lower()
        if (artifact_dir and norm_target.startswith(artifact_dir.replace("/", "\\").lower())) or "\\brain\\" in norm_target:
            send_decision("allow", "Auto-allowed internal agent brain artifact")

    overrides = build_permission_overrides(payload)

    # TIER 3: Scoped Auto-Accept Predicate
    auto_accept_eligible = is_eligible_for_auto_accept(tool_name, args, workspace_paths)
    timeout_sec = auto_accept_timeout if (remote_auto_accept and auto_accept_eligible) else default_timeout

    # LOCAL-ONLY WORKSTATION MODE (When Telegram is paused)
    if not telegram_enabled:
        cmd_info = args.get("CommandLine", "") or target or tool_name
        sys.stderr.write(
            f"\n⚡ [Mobile Remote Control: Local Machine Mode (Telegram Paused)]\n"
            f"   Tool: {tool_name} -> {cmd_info[:60]}\n"
            f"   👉 Auto-approving for local execution on this workstation.\n\n"
        )
        sys.stderr.flush()
        grant_transient_permission(payload)
        send_decision("allow", "Local workstation execution approved (Telegram paused)", overrides=overrides)

    # TIER 4: Remote Mobile Approval Mode (Daemon active)
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
                    timeout=1
                )
            except Exception:
                pass
            stop_event.set()
            break
        time.sleep(0.05)

    decision = decision_box.get("decision") or "ask"
    source = decision_box.get("source") or "Timeout"

    if decision == "allow":
        grant_transient_permission(payload)
        send_decision("allow", f"User chose ALLOW via {source}", overrides=overrides)
    elif decision == "deny":
        send_decision("deny", f"User chose DENY via {source}")
    else:
        fallback_terminal(f"Action fell back to terminal ({source})")


if __name__ == "__main__":
    main()
