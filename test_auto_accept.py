import urllib.request
import json
import time
import subprocess
import sys
import threading
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_PATH = os.path.join(SCRIPT_DIR, "mrc_daemon.py")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

old_timeout = cfg.get('auto_accept_timeout_seconds', 8)
cfg['auto_accept_timeout_seconds'] = 2
with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2)

try:
    proc = subprocess.Popen([sys.executable, DAEMON_PATH])
    time.sleep(1)

    # 1. Test auto-accept (let 2s expire)
    req_data = json.dumps({
        'req_id': 'auto-test-1',
        'payload': {'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'echo auto'}}}
    }).encode()
    start = time.time()
    req = urllib.request.Request('http://127.0.0.1:48201/request_approval', data=req_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as resp:
        res = json.loads(resp.read().decode())
        elapsed = time.time() - start
        print(f"Test 1 (Auto-Accept): elapsed={elapsed:.2f}s, decision={res.get('decision')}, source={res.get('source')}")

    # 2. Test early deny via /resolve (before 2s expires)
    def client_call():
        req_data = json.dumps({
            'req_id': 'deny-test-2',
            'payload': {'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'echo deny'}}}
        }).encode()
        req = urllib.request.Request('http://127.0.0.1:48201/request_approval', data=req_data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode())
            print(f"Test 2 (Early Deny): decision={res.get('decision')}, source={res.get('source')}")

    t = threading.Thread(target=client_call)
    t.start()
    time.sleep(0.5)

    # Send deny
    resolve_data = json.dumps({'req_id': 'deny-test-2', 'decision': 'deny', 'source': 'Mobile Phone (Telegram)'}).encode()
    urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:48201/resolve', data=resolve_data, headers={'Content-Type': 'application/json'}))
    t.join()

    # Shutdown
    urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:48201/shutdown', data=b'{}'))
    proc.terminate()
finally:
    cfg['auto_accept_timeout_seconds'] = old_timeout
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
