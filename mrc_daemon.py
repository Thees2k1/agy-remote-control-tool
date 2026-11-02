#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - Background Single-Poller Daemon
Maintains a single long-polling connection to Telegram to prevent
duplicate updates, race conditions, and HTTP 409 conflict errors.
Listens on local HTTP port 48201 for approval requests from mrc_bridge.py.
"""

import sys
import os
import json
import time
import html
import uuid
import threading
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
DAEMON_PORT = 48201

pending_requests = {}
pending_lock = threading.Lock()
stop_daemon_event = threading.Event()


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def telegram_api(token, method, data=None):
    if not token:
        return {"ok": False, "description": "No bot token provided"}
    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "description": str(e)}


def escape(text):
    if text is None:
        return ""
    return html.escape(str(text))


def truncate(text, max_len=1500):
    if not text:
        return ""
    if len(text) > max_len:
        return text[:max_len] + f"\n... [truncated {len(text) - max_len} chars]"
    return text


def build_message_and_summary(payload):
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "unknown_tool")
    args = tool_call.get("args", {})
    step_idx = payload.get("stepIdx", "?")

    header = f"🤖 <b>AGY Action Approval Request</b> (Step #{escape(step_idx)})\n"

    target_info = ""
    diff_block = ""
    summary_text = ""

    if tool_name == "write_to_file":
        target = args.get("TargetFile", "")
        code = args.get("CodeContent", "")
        desc = args.get("Description", "")
        lines = code.count("\n") + 1 if code else 0
        target_info = f"📁 <b>Target:</b> <code>{escape(target)}</code>\n"
        if desc:
            target_info += f"📝 <b>Desc:</b> {escape(desc)}\n"
        summary_text = f"Writing file (+{lines} lines)"
        snippet = truncate(code, 2000)
        diff_block = f"<pre><code class=\"language-text\">{escape(snippet)}</code></pre>"

    elif tool_name == "replace_file_content":
        target = args.get("TargetFile", "")
        instruction = args.get("Instruction", "")
        desc = args.get("Description", "")
        target_content = args.get("TargetContent", "")
        replacement = args.get("ReplacementContent", "")
        lines_range = f"L{args.get('StartLine', '?')}-L{args.get('EndLine', '?')}"
        target_info = f"📁 <b>Target:</b> <code>{escape(target)}</code> ({escape(lines_range)})\n"
        if instruction:
            target_info += f"📝 <b>Instruction:</b> {escape(instruction)}\n"
        elif desc:
            target_info += f"📝 <b>Desc:</b> {escape(desc)}\n"
        summary_text = f"Replace lines in {os.path.basename(target) if target else 'file'}"
        diff_preview = (
            f"--- Target Content ---\n{target_content}\n"
            f"+++ Replacement Content +++\n{replacement}"
        )
        diff_block = f"<pre><code class=\"language-diff\">{escape(truncate(diff_preview, 2200))}</code></pre>"

    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "")
        cwd = args.get("Cwd", "")
        desc = args.get("Description", "")
        target_info = f"💻 <b>Command:</b> <code>{escape(cmd)}</code>\n"
        if cwd:
            target_info += f"📂 <b>Cwd:</b> <code>{escape(cwd)}</code>\n"
        if desc:
            target_info += f"📝 <b>Desc:</b> {escape(desc)}\n"
        summary_text = f"Execute command: {cmd[:40]}..."
    else:
        target_info = f"🔧 <b>Tool:</b> <code>{escape(tool_name)}</code>\n"
        args_json = json.dumps(args, indent=2)
        diff_block = f"<pre>{escape(truncate(args_json, 1500))}</pre>"
        summary_text = f"Execute tool {tool_name}"

    full_message = f"{header}\n{target_info}\n<b>Summary:</b> {escape(summary_text)}\n\n{diff_block}"
    return full_message, summary_text


def telegram_polling_loop():
    """
    Dedicated single-poller thread that receives callback updates from Telegram.
    Guarantees no competing pollers and handles callback query acknowledgment.
    """
    config = load_config()
    bot_token = config.get("bot_token")
    if not bot_token or not config.get("telegram_enabled", False):
        return

    offset = 0
    # Fetch latest update to determine starting offset without dropping pending events
    try:
        init_res = telegram_api(bot_token, "getUpdates", {"offset": -1, "timeout": 1})
        if init_res.get("ok") and init_res.get("result"):
            for update in init_res["result"]:
                process_update(bot_token, update)
                offset = max(offset, update["update_id"] + 1)
    except Exception:
        pass

    while not stop_daemon_event.is_set():
        config = load_config()
        if not config.get("telegram_enabled", False):
            time.sleep(1)
            continue

        try:
            poll_res = telegram_api(bot_token, "getUpdates", {
                "offset": offset,
                "timeout": 5,
                "allowed_updates": ["callback_query"]
            })
            if poll_res.get("ok"):
                for update in poll_res.get("result", []):
                    offset = max(offset, update["update_id"] + 1)
                    process_update(bot_token, update)
        except Exception:
            time.sleep(1)
        time.sleep(0.1)


def process_update(bot_token, update):
    cb = update.get("callback_query")
    if not cb:
        return
    data = cb.get("data", "")
    cb_id = cb.get("id")

    # Format: mrc:<decision>:<req_id>
    parts = data.split(":")
    if len(parts) == 3 and parts[0] == "mrc":
        dec = parts[1]
        req_id = parts[2]

        with pending_lock:
            req = pending_requests.get(req_id)
            if req and not req["resolved"]:
                req["decision"] = dec
                req["source"] = "Mobile Phone (Telegram)"
                req["resolved"] = True
                req["event"].set()

                telegram_api(bot_token, "answerCallbackQuery", {
                    "callback_query_id": cb_id,
                    "text": f"Decision: {dec.upper()} ✅"
                })
                return

    telegram_api(bot_token, "answerCallbackQuery", {
        "callback_query_id": cb_id,
        "text": "Handled"
    })


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default stdout request logging

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "pending": len(pending_requests)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/request_approval":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            req_id = body.get("req_id") or str(uuid.uuid4())[:8]
            payload = body.get("payload", {})
            timeout_sec = int(body.get("timeout_seconds", 90))

            config = load_config()
            bot_token = config.get("bot_token")
            chat_id = config.get("chat_id")
            telegram_enabled = config.get("telegram_enabled", False)
            remote_auto_accept = config.get("remote_auto_accept", False)
            auto_accept_timeout = int(config.get("auto_accept_timeout_seconds", 8))
            default_timeout = int(config.get("timeout_seconds", 90))

            auto_accept_eligible = body.get("auto_accept_eligible", False)
            should_auto_accept = remote_auto_accept and auto_accept_eligible
            timeout_sec = auto_accept_timeout if should_auto_accept else int(body.get("timeout_seconds", default_timeout))

            msg_text, summary_text = build_message_and_summary(payload)
            if should_auto_accept:
                msg_text += f"\n\n⏱️ <i>Auto-approving in {timeout_sec}s unless denied...</i>"
            sent_msg_id = None

            if telegram_enabled and bot_token and chat_id:
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ 1. Allow", "callback_data": f"mrc:allow:{req_id}"},
                            {"text": "❌ 2. Deny", "callback_data": f"mrc:deny:{req_id}"}
                        ]
                    ]
                }
                send_res = telegram_api(bot_token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": msg_text,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard
                })
                if send_res.get("ok"):
                    sent_msg_id = send_res["result"]["message_id"]

            req_entry = {
                "req_id": req_id,
                "event": threading.Event(),
                "decision": None,
                "source": None,
                "resolved": False,
                "sent_msg_id": sent_msg_id,
                "msg_text": msg_text,
                "chat_id": chat_id,
                "bot_token": bot_token
            }

            with pending_lock:
                pending_requests[req_id] = req_entry

            # Block until resolved or timeout
            req_entry["event"].wait(timeout_sec)

            with pending_lock:
                decision = req_entry["decision"]
                source = req_entry["source"]
                pending_requests.pop(req_id, None)

            if decision and sent_msg_id and bot_token and chat_id:
                status_emoji = "✅" if decision == "allow" else "❌"
                status_label = "APPROVED" if decision == "allow" else "DENIED"
                updated_text = (
                    f"{msg_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"{status_emoji} <b>{status_label}</b> via {source or 'MRC'}"
                )
                telegram_api(bot_token, "editMessageText", {
                    "chat_id": chat_id,
                    "message_id": sent_msg_id,
                    "text": updated_text,
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": []}
                })

            elif not decision and should_auto_accept:
                decision = "allow"
                source = f"Auto-Accept Timer ({timeout_sec}s)"
                if sent_msg_id and bot_token and chat_id:
                    auto_text = (
                        f"{msg_text}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ <b>AUTO-APPROVED</b> ({timeout_sec}s elapsed without objection)"
                    )
                    telegram_api(bot_token, "editMessageText", {
                        "chat_id": chat_id,
                        "message_id": sent_msg_id,
                        "text": auto_text,
                        "parse_mode": "HTML",
                        "reply_markup": {"inline_keyboard": []}
                    })

            elif not decision and sent_msg_id and bot_token and chat_id:
                timeout_text = (
                    f"{msg_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"⌛ <b>TIMED OUT ({timeout_sec}s)</b> — Dropping back to terminal."
                )
                telegram_api(bot_token, "editMessageText", {
                    "chat_id": chat_id,
                    "message_id": sent_msg_id,
                    "text": timeout_text,
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": []}
                })

            resp_payload = {
                "req_id": req_id,
                "decision": decision or "ask",
                "source": source or "timeout",
                "reason": f"Decision: {decision.upper() if decision else 'TIMED OUT'} via {source or 'local'}"
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload).encode("utf-8"))

        elif self.path == "/resolve":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                body = json.loads(raw_body)
                req_id = body.get("req_id")
                dec = body.get("decision", "allow")
                src = body.get("source", "Workstation Keyboard")
                with pending_lock:
                    req = pending_requests.get(req_id)
                    if req and not req["resolved"]:
                        req["decision"] = dec
                        req["source"] = src
                        req["resolved"] = True
                        req["event"].set()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

        elif self.path == "/shutdown":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"shutting down"}')
            stop_daemon_event.set()
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_response(404)
            self.end_headers()


def run_daemon():
    server = ThreadedHTTPServer(("127.0.0.1", DAEMON_PORT), RequestHandler)
    poller = threading.Thread(target=telegram_polling_loop, daemon=True)
    poller.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_daemon_event.set()
        server.server_close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(f"Daemon configuration check OK. Listening port: {DAEMON_PORT}")
        sys.exit(0)
    run_daemon()
