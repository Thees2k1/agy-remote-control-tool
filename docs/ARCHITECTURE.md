# Mobile Remote Control (MRC): System Architecture

## 1. System Overview

Mobile Remote Control (MRC) bridges Antigravity's local agent execution runtime (`agy.exe` / `Jetski`) with remote communication channels (Telegram, Discord) to allow developers to safely monitor, inspect, and authorize tool calls while away from their workstation (AFK).

```mermaid
flowchart TD
    subgraph Antigravity ["Antigravity Runtime (Host Machine)"]
        AgyCLI["agy.exe / IDE"]
        Harness["OneHarness / Jetski Engine"]
        AgyCLI --> Harness
        Settings["antigravity-cli/settings.json\n(toolPermission: request-review)"]
        Harness <--> Settings
    end

    subgraph Hooks ["Lifecycle Hooks Layer"]
        PreHook["hooks/pre_tool_use.py\n(PreToolUse Hook)"]
        PostHook["hooks/post_tool_use.py\n(PostToolUse Hook)"]
        Harness -->|"stdin: ToolCall Payload"| PreHook
        PostHook -->|"stdin: PostToolUse Payload"| Harness
    end

    subgraph MRC_Daemon ["MRC Background Daemon (127.0.0.1:48201)"]
        HTTPServer["ThreadedHTTPServer\n(/request_approval, /resolve, /health)"]
        Registry["Pending Request Registry\n(threading.Event synchronization)"]
        Poller["Single-Thread Telegram Poller\n(getUpdates loop)"]
        Timer["Scoped Auto-Accept Timer\n(8s countdown)"]
        HTTPServer <--> Registry
        Registry <--> Poller
        Registry <--> Timer
    end

    subgraph Remote_Channel ["Remote Channel (Mobile)"]
        TelegramAPI["Telegram Bot API\n(@antiex_bot)"]
        Phone["Developer Smartphone\n(Inline Keyboard Actions)"]
        Poller <--> TelegramAPI
        TelegramAPI <--> Phone
    end

    PreHook -->|"POST /request_approval"| HTTPServer
    PostHook -->|"Purge Transient Grants"| Settings
```

---

## 2. Sequence Diagram: Tool Authorization Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant H as OneHarness (agy.exe)
    participant B as PreToolUse Bridge
    participant D as MRC Daemon (:48201)
    participant T as Telegram Bot API
    participant P as User Phone
    participant S as settings.json
    participant C as PostToolUse Cleanup

    H->>B: ToolCall Payload (run_command / write_to_file)
    B->>B: Evaluate Tier 1 (Hard Deny) & Tier 2 (Brain Allowlists)
    B->>B: Evaluate Tier 3 Predicate (auto_accept_eligible)
    B->>D: POST /request_approval (req_id, payload, timeout)
    D->>T: sendMessage (HTML diff preview + [Allow] / [Deny])
    T->>P: Push notification with interactive buttons
    
    alt User Taps [Allow] on Phone
        P->>T: callback_query (mrc:allow:req_id)
        T->>D: Poller receives callback_query
        D->>D: Set decision="allow", wake waiting request
        D->>T: editMessageText (Mark APPROVED ✅)
    else 8s Auto-Accept Timer Expires (Low-Risk Predicate)
        D->>D: Auto-accept timer fires (decision="allow")
        D->>T: editMessageText (Mark AUTO-APPROVED ⚡)
    else 90s Timeout Expires / User Taps [Deny]
        P->>T: callback_query (mrc:deny:req_id)
        D->>D: Set decision="deny"
        D->>T: editMessageText (Mark DENIED ❌)
    end

    D-->>B: 200 OK (decision, reason, source)
    
    alt If Approved
        B->>S: Inject transient grant for stepIdx (Tier 4)
        B-->>H: stdout: {"decision": "allow", "permissionOverrides": [...]}
        H->>H: Gate 2 Verified -> Execute Native Tool
        H->>C: PostToolUse Payload
        C->>S: Purge transient grant from settings.json
        C-->>H: stdout: {}
    else If Denied
        B-->>H: stdout: {"decision": "deny", "reason": "..."}
        H->>H: Tool Execution Aborted
    end
```

---

## 3. Four-Tier Policy Evaluation

MRC enforces security decisions through four strictly ordered tiers:

```
+-------------------------------------------------------------+
| Tier 1: Inviolable Hard Deny                                |
| - Blocks ~/.gemini/**, hooks.json, settings.json            |
| - Blocks credentials (.ssh, .aws, .env)                     |
| - Blocks git push --force, git reset --hard, git clean -fd  |
+-------------------------------------------------------------+
                              | (If not blocked)
                              v
+-------------------------------------------------------------+
| Tier 2: Project-Scoped Allowlists                           |
| - Agent brain artifacts (~/.gemini/.../brain/**) auto-allow |
| - Read-only safe tools proceed frictionless                 |
+-------------------------------------------------------------+
                              | (If not allowlisted)
                              v
+-------------------------------------------------------------+
| Tier 3: Scoped Auto-Accept Predicate                        |
| - Is it a safe inspection command or workspace file edit?   |
|   -> YES: 8s auto-accept countdown engaged                  |
|   -> NO:  90s full human review required                    |
+-------------------------------------------------------------+
                              | (Dispatched to Daemon)
                              v
+-------------------------------------------------------------+
| Tier 4: Remote Authorization & Transient Session Grants     |
| - Out-of-band human confirmation via Telegram / keyboard    |
| - Injects transient grant into settings.json for stepIdx    |
| - Gate 2 satisfied; PostToolUse hook purges grant on exit   |
+-------------------------------------------------------------+
```

---

## 4. Daemon Architecture & Concurrency Mechanics

The daemon ([src/mrc/daemon.py](file:///C:/Users/tongn/.gemini/antigravity/scratch/mrc-prototype/src/mrc/daemon.py)) operates as a standalone multi-threaded HTTP server:

1. **ThreadedHTTPServer**:
   - Subclasses `socketserver.ThreadingMixIn` and `http.server.HTTPServer` so incoming requests (`/request_approval`, `/resolve`, `/health`) are handled concurrently without head-of-line blocking.
2. **Dedicated Poller Thread**:
   - Exactly one long-lived background thread executes Telegram `getUpdates` with long-polling (`timeout=5`).
   - Guarantees zero dropped callbacks and completely prevents Telegram HTTP 409 Conflict errors.
3. **Pending Request Registry**:
   - Requests are stored in a synchronized dictionary indexed by `req_id`:
     ```python
     {
       "req_id": "abc12345",
       "event": threading.Event(),
       "decision": None,
       "source": None,
       "sent_msg_id": 1042
     }
     ```
   - Calling `/resolve` or receiving a Telegram callback query sets `req_entry["decision"]` and calls `req_entry["event"].set()`, terminating the wait in `< 5ms`.
4. **Local Keyboard Interception**:
   - The CLI bridge simultaneously polls `msvcrt.kbhit()` on Windows, allowing the developer at the desk to press `[Y]` to approve locally or `[N]` to deny, resolving the request and editing the Telegram message accordingly.
