"""
MRC Telegram Client & API Wrapper
Provides HTTP communication with Telegram Bot API and manages callback polling.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional


def telegram_api(bot_token: str, method: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call a Telegram Bot API endpoint."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "error": str(e), "status_code": e.code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_approval_message(bot_token: str, chat_id: str, req_id: str, msg_text: str) -> Optional[int]:
    """Send an approval request with inline Allow and Deny buttons."""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ 1. Allow", "callback_data": f"mrc:allow:{req_id}"},
                {"text": "❌ 2. Deny", "callback_data": f"mrc:deny:{req_id}"}
            ]
        ]
    }
    res = telegram_api(bot_token, "sendMessage", {
        "chat_id": chat_id,
        "text": msg_text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    })
    if res.get("ok"):
        return res["result"]["message_id"]
    return None


def update_message_resolution(bot_token: str, chat_id: str, message_id: int, original_text: str, resolution_text: str) -> None:
    """Edit message to show resolution outcome and remove action buttons."""
    updated_text = (
        f"{original_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{resolution_text}"
    )
    telegram_api(bot_token, "editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": updated_text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": []}
    })


def answer_callback(bot_token: str, callback_query_id: str, text: str = "Handled") -> None:
    """Acknowledge Telegram callback query to stop loading spinner on mobile."""
    telegram_api(bot_token, "answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text
    })


class TelegramClient:
    """Convenience OOP wrapper around Telegram Bot API."""
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        from mrc.config import load_config
        cfg = load_config()
        self.bot_token = bot_token or cfg.get("telegram_bot_token") or ""
        self.chat_id = chat_id or cfg.get("telegram_chat_id") or ""

    def send_message(self, text: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
        target_chat = chat_id or self.chat_id
        if not self.bot_token or not target_chat:
            return {"ok": False, "error": "Missing bot token or chat ID"}
        return telegram_api(self.bot_token, "sendMessage", {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": "HTML"
        })

