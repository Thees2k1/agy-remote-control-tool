import json
import urllib.request
import time
import ssl

ctx = ssl.create_default_context()

with open("config.json", "r") as f:
    cfg = json.load(f)

token = cfg["bot_token"]
chat_id = cfg["chat_id"]

test_id = "test-" + str(int(time.time()))[-4:]
keyboard = {
    "inline_keyboard": [
        [
            {"text": "✅ Test Allow", "callback_data": f"mrc:allow:{test_id}"},
            {"text": "❌ Test Deny", "callback_data": f"mrc:deny:{test_id}"}
        ]
    ]
}
payload = {
    "chat_id": chat_id,
    "text": (
        "🚀 <b>Antigravity Mobile Remote Control</b>\n\n"
        "Your Android phone is now linked!\n"
        "Tap a button below to test decision delivery:"
    ),
    "parse_mode": "HTML",
    "reply_markup": keyboard
}

url = f"https://api.telegram.org/bot{token}/sendMessage"
req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    res = json.loads(r.read().decode())
    print("SEND_STATUS:", res.get("ok"))
    msg_id = res.get("result", {}).get("message_id")
    print("MSG_ID:", msg_id)

print("Awaiting tap from phone for 45s...")
start = time.time()
offset = 0
decision = None

while time.time() - start < 45:
    poll_url = f"https://api.telegram.org/bot{token}/getUpdates"
    poll_data = json.dumps({"offset": offset, "timeout": 2, "allowed_updates": ["callback_query"]}).encode("utf-8")
    req = urllib.request.Request(poll_url, data=poll_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            updates = json.loads(r.read().decode()).get("result", [])
            for u in updates:
                offset = u["update_id"] + 1
                cb = u.get("callback_query")
                if not cb:
                    continue
                data = cb.get("data", "")
                if data == f"mrc:allow:{test_id}":
                    decision = "ALLOW"
                elif data == f"mrc:deny:{test_id}":
                    decision = "DENY"

                if decision:
                    # Answer callback
                    ans_url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                    ans_req = urllib.request.Request(ans_url, data=json.dumps({"callback_query_id": cb["id"], "text": f"Registered: {decision}"}).encode("utf-8"), headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(ans_req, timeout=5, context=ctx)

                    # Edit message
                    edit_url = f"https://api.telegram.org/bot{token}/editMessageText"
                    edit_payload = {
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "text": f"🎉 <b>Connection Verified!</b>\n\nYou tapped: <b>{decision}</b>\nAntigravity is now linked to your phone.",
                        "parse_mode": "HTML",
                        "reply_markup": {"inline_keyboard": []}
                    }
                    edit_req = urllib.request.Request(edit_url, data=json.dumps(edit_payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(edit_req, timeout=5, context=ctx)
                    break
    except Exception as e:
        print("POLL_ERR:", e)
    if decision:
        break
    time.sleep(1)

if decision:
    print("SUCCESS: User tapped", decision)
else:
    print("No tap received within 45s.")
