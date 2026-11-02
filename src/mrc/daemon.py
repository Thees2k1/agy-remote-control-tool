"""
MRC Background Daemon & Request Registry
Runs a multi-threaded HTTP server (127.0.0.1:48201) and manages single-thread Telegram polling.
"""

import sys
import os
import json
import time
import uuid
import threading
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler

from .config import (
    DAEMON_HOST, DAEMON_PORT,
    load_config
)
from .formatting import build_message_and_summary
from .telegram_client import (
    telegram_api, send_approval_message,
    update_message_resolution, answer_callback
)

pending_lock = threading.Lock()
pending_requests = {}
stop_daemon_event = threading.Event()


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

    cb_id = cb.get("id")
    cb_data = cb.get("data", "")
    from_user = cb.get("from", {}).get("username") or cb.get("from", {}).get("first_name", "Remote User")

    if cb_data.startswith("mrc:"):
        parts = cb_data.split(":")
        if len(parts) >= 3:
            dec = parts[1]
            req_id = parts[2]
            with pending_lock:
                req_entry = pending_requests.get(req_id)
                if req_entry and not req_entry["resolved"]:
                    req_entry["decision"] = dec
                    req_entry["source"] = f"Telegram (@{from_user})"
                    req_entry["resolved"] = True
                    req_entry["event"].set()

            answer_callback(bot_token, cb_id, text=f"Decision: {dec.upper()} ✅")
            return

    answer_callback(bot_token, cb_id, text="Handled")


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
                sent_msg_id = send_approval_message(bot_token, str(chat_id), req_id, msg_text)

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
                res_text = f"{status_emoji} <b>{status_label}</b> via {source or 'MRC'}"
                update_message_resolution(bot_token, str(chat_id), sent_msg_id, msg_text, res_text)

            elif not decision and should_auto_accept:
                decision = "allow"
                source = f"Auto-Accept Timer ({timeout_sec}s)"
                if sent_msg_id and bot_token and chat_id:
                    auto_text = f"⚡ <b>AUTO-APPROVED</b> ({timeout_sec}s elapsed without objection)"
                    update_message_resolution(bot_token, str(chat_id), sent_msg_id, msg_text, auto_text)

            elif not decision and sent_msg_id and bot_token and chat_id:
                timeout_text = f"⌛ <b>TIMED OUT ({timeout_sec}s)</b> — Dropping back to terminal."
                update_message_resolution(bot_token, str(chat_id), sent_msg_id, msg_text, timeout_text)

            resp_payload = {
                "req_id": req_id,
                "decision": decision or "ask",
                "source": source or "timeout",
                "reason": f"Decision: {decision.upper() if decision else 'TIMED OUT'} via {source or 'local'}"
            }
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
            except (ConnectionResetError, BrokenPipeError):
                pass

        elif self.path == "/resolve":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                body = json.loads(raw_body)
                req_id = body.get("req_id")
                dec = body.get("decision", "allow")
                src = body.get("source", "Workstation Keyboard")
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            resolved = False
            with pending_lock:
                req_entry = pending_requests.get(req_id)
                if req_entry and not req_entry["resolved"]:
                    req_entry["decision"] = dec
                    req_entry["source"] = src
                    req_entry["resolved"] = True
                    req_entry["event"].set()
                    resolved = True

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "resolved" if resolved else "not_found", "req_id": req_id}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def start_daemon(host: str = DAEMON_HOST, port: int = DAEMON_PORT):
    server = ThreadedHTTPServer((host, port), RequestHandler)
    poller_thread = threading.Thread(target=telegram_polling_loop, daemon=True)
    poller_thread.start()

    sys.stderr.write(f"\n🚀 [MRC Background Daemon] Running on http://{host}:{port}\n")
    sys.stderr.write(f"   Single-thread Telegram Poller active.\n")
    sys.stderr.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_daemon_event.set()
        server.server_close()


def main():
    start_daemon()


if __name__ == "__main__":
    main()
