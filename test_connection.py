#!/usr/bin/env python3
"""
Mobile Remote Control (MRC) - Connection & Onboarding Tool
Verifies bot token, detects your chat_id automatically from Telegram,
and performs a live test interaction with your phone.
"""

import sys
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"bot_token": "", "chat_id": None, "timeout_seconds": 90}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def telegram_api(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            return err_body
        except Exception:
            return {"ok": False, "description": str(e)}
    except Exception as e:
        return {"ok": False, "description": str(e)}


def main():
    print("=" * 60)
    print(" 🚀 AGY Mobile Remote Control - Setup & Connection Test")
    print("=" * 60)

    cfg = load_config()

    # Determine token from arg or config
    token = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        token = sys.argv[1].strip()
    elif cfg.get("bot_token"):
        token = cfg.get("bot_token")

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("\n[!] No Telegram Bot Token found.")
        print("Usage: python test_connection.py <YOUR_BOT_TOKEN>")
        print("Or set 'bot_token' in config.json.\n")
        sys.exit(1)

    print(f"\n[*] Validating Bot Token with Telegram API...")
    me = telegram_api(token, "getMe")
    if not me.get("ok"):
        print(f"\n[X] Error: Token invalid or Telegram API unreachable!")
        print(f"    Details: {me.get('description')}")
        sys.exit(1)

    bot_user = me["result"]
    print(f"[✓] Connected successfully to bot: @{bot_user.get('username')} ({bot_user.get('first_name')})")

    # Detect Chat ID from updates
    chat_id = cfg.get("chat_id")
    if not chat_id:
        print("\n[*] Looking for your chat_id from recent messages...")
        updates = telegram_api(token, "getUpdates")
        found = False
        if updates.get("ok"):
            for u in reversed(updates.get("result", [])):
                msg = u.get("message")
                if msg and msg.get("chat"):
                    chat_id = msg["chat"]["id"]
                    user_handle = msg["chat"].get("username", msg["chat"].get("first_name", "User"))
                    print(f"[✓] Found chat from @{user_handle} (chat_id: {chat_id})")
                    found = True
                    break

        if not found:
            print(f"\n[!] No messages found yet.")
            print(f"👉 Please open Telegram on your phone, find @{bot_user.get('username')}, and tap Start (or send /start).")
            print("   Waiting for your message...", end="", flush=True)

            start_poll = time.time()
            while time.time() - start_poll < 60:
                print(".", end="", flush=True)
                time.sleep(2)
                check = telegram_api(token, "getUpdates")
                if check.get("ok") and check.get("result"):
                    for u in reversed(check.get("result", [])):
                        msg = u.get("message")
                        if msg and msg.get("chat"):
                            chat_id = msg["chat"]["id"]
                            print(f"\n[✓] Received message! Registered chat_id: {chat_id}")
                            found = True
                            break
                if found:
                    break

        if not found:
            print("\n[X] Timed out waiting for /start. Please send a message to your bot and run this script again.")
            sys.exit(1)

    # Save to config.json
    cfg["bot_token"] = token
    cfg["chat_id"] = chat_id
    save_config(cfg)
    print(f"[✓] Configuration saved to {CONFIG_PATH}")

    # Send interactive test button
    print("\n[*] Sending test interactive message to your Android phone...")
    test_id = "test-" + str(int(time.time()))[-4:]
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Test Allow", "callback_data": f"mrc:allow:{test_id}"},
                {"text": "❌ Test Deny", "callback_data": f"mrc:deny:{test_id}"}
            ]
        ]
    }
    test_payload = {
        "chat_id": chat_id,
        "text": (
            "📱 <b>AGY Mobile Remote Control Connection Test</b>\n\n"
            "Your workstation is now linked to this Telegram chat!\n"
            "Please tap one of the buttons below to test bidirectional decision delivery:"
        ),
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    sent = telegram_api(token, "sendMessage", test_payload)
    if not sent.get("ok"):
        print(f"[X] Failed to send test message: {sent.get('description')}")
        sys.exit(1)

    sent_msg_id = sent["result"]["message_id"]
    print(f"[✓] Test message sent! Check your phone notification.")
    print("   Awaiting button tap on phone...", end="", flush=True)

    start_wait = time.time()
    tapped_decision = None
    offset = 0

    while time.time() - start_wait < 60:
        print(".", end="", flush=True)
        time.sleep(1)
        res = telegram_api(token, "getUpdates", {
            "offset": offset,
            "timeout": 2,
            "allowed_updates": ["callback_query"]
        })
        if res.get("ok"):
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                cb = u.get("callback_query")
                if not cb:
                    continue
                data = cb.get("data", "")
                if data == f"mrc:allow:{test_id}":
                    tapped_decision = "ALLOW"
                elif data == f"mrc:deny:{test_id}":
                    tapped_decision = "DENY"

                if tapped_decision:
                    telegram_api(token, "answerCallbackQuery", {
                        "callback_query_id": cb["id"],
                        "text": f"Test successful: {tapped_decision} received!"
                    })
                    break
        if tapped_decision:
            break

    if tapped_decision:
        print(f"\n\n🎉 SUCCESS! Received '{tapped_decision}' decision from your phone!")
        telegram_api(token, "editMessageText", {
            "chat_id": chat_id,
            "message_id": sent_msg_id,
            "text": (
                "🎉 <b>Connection Verified!</b>\n\n"
                f"Received <b>{tapped_decision}</b> from your phone.\n"
                "Your Antigravity workstation is now ready for remote mobile approvals."
            ),
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": []}
        })
    else:
        print("\n[!] No button tap received within 60s. But connection to bot is established.")

    print("\n" + "=" * 60)
    print(" Setup complete! Next step: register the hook in hooks.json.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
