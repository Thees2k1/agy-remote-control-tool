import json
import urllib.request
import ssl

ctx = ssl.create_default_context()

try:
    with open("config.json", "r") as f:
        cfg = json.load(f)
    token = cfg["bot_token"]
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    req = urllib.request.Request(url, headers={"User-Agent": "Antigravity/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        data = json.loads(r.read().decode())
        print("OK:", data.get("ok"))
        updates = data.get("result", [])
        print("UPDATE_COUNT:", len(updates))
        for u in updates:
            msg = u.get("message", {})
            chat = msg.get("chat", {})
            print("FOUND_CHAT_ID:", chat.get("id"), "USERNAME:", chat.get("username"), "TEXT:", msg.get("text"))
except Exception as e:
    print("ERROR:", e)
