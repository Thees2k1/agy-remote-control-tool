# Mobile Remote Control (MRC) for Google Antigravity

[![Milestone](https://img.shields.io/badge/Milestone-M1%20Verified%20(Bonfire%20Save--Point)-success)](docs/ROADMAP.md)
[![Architecture](https://img.shields.io/badge/Architecture-ADR--001%20%7C%20ADR--002-blue)](docs/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Mobile Remote Control (MRC)** transforms your personal smartphone (via Telegram/Discord) into an out-of-band authorization terminal for Google Antigravity (`agy` CLI & GUI). It enables developers to step away from their desk (AFK) while retaining real-time visibility, diff inspection, and one-tap approval over agent tool executions.

---

## 🛡️ Core Philosophy: "Always Ask — Human in Control"

Unlike autonomous-by-default models that skip permission prompts, MRC strictly adheres to **Fail-Closed Safety**:
1. **Host Safety**: Your developer environment maintains `toolPermission: "request-review"` at all times. Wildcard allowlists (`"*"`) and global `"always-proceed"` bypasses are prohibited.
2. **Two-Gate Harmony**: Remote approvals clear both Gate 1 (extension hook audit) and Gate 2 (native UI confirmation gate) via single-use transient grants, avoiding duplicate prompts without opening security holes.
3. **Four-Tier Policy Engine**:
   - **Tier 1 (Inviolable Hard Deny)**: Protects safety configs (`~/.gemini/**`, `hooks.json`, `settings.json`), credentials (`.ssh`, `.aws`, `.env`), and destructive git operations (`push --force`, `reset --hard`, `clean -fd`).
   - **Tier 2 (Project Allowlists)**: Frictionless auto-approval for internal agent brain artifacts.
   - **Tier 3 (Scoped Auto-Accept Predicate)**: Safe inspection commands (`git status`, tests) and workspace code edits receive an 8-second countdown. Dangerous/mutating commands require explicit human taps within 90 seconds.
   - **Tier 4 (Transient Session Grants)**: Remote approvals inject a single-use permission for the active step, purged immediately upon completion by `PostToolUse`.

---

## 📂 Project Architecture & Layout

Refactored in accordance with [ADR-002](docs/ADR-002-package-structure-and-srp-refactoring.md) to enforce the Single Responsibility Principle (SRP):

```
mrc-prototype/
├── README.md                   # Project landing page & bonfire save-point
├── Task.md                     # Roadmap task tracker & checklist
├── pyproject.toml              # PEP 621 packaging metadata
├── config.json                 # User configuration (token, chat_id, toggles)
├── docs/                       # Architectural documentation
│   ├── ADR-001-guardrail-and-permission-architecture.md
│   ├── ADR-002-package-structure-and-srp-refactoring.md
│   ├── ARCHITECTURE.md         # Detailed sequence diagrams & component designs
│   ├── PROGRESS.md             # Incident analysis & chronological engineering log
│   ├── ROADMAP.md              # High-level model & evolutionary milestones (M1 -> M4)
│   └── SPEC_UABI.md            # Universal Agent-Bridge Interface wire protocol
├── src/
│   └── mrc/                    # Core library package
│       ├── __init__.py         # Version & exports
│       ├── config.py           # Paths, config loader, environment defaults
│       ├── guardrails.py       # Tier 1 Hard Deny & Tier 3 Risk Predicates
│       ├── session_grant.py    # Tier 4 Gate-2 transient injection & cleanup
│       ├── formatting.py       # Rich HTML diff preview & message formatting
│       ├── telegram_client.py  # Telegram API client & single-poller loop
│       └── daemon.py           # Threaded HTTP daemon (:48201) & registry
├── hooks/                      # Antigravity Lifecycle Hook Entry Points
│   ├── pre_tool_use.py         # PreToolUse hook (stdin -> 4-tier evaluation -> stdout)
│   └── post_tool_use.py        # PostToolUse cleanup hook (stdin -> purge -> stdout)
├── tests/                      # Modular Unit Test Suite
│   ├── __init__.py
│   ├── test_guardrails.py      # Tier 1 & Tier 3 security assertions
│   ├── test_session_grant.py   # Tier 4 Gate-2 grant & cleanup lifecycle
│   └── test_daemon.py          # Message formatting & daemon tests
├── mrc_bridge.py               # Backward-compat shim -> hooks/pre_tool_use.py
├── mrc_cleanup.py              # Backward-compat shim -> hooks/post_tool_use.py
└── mrc_daemon.py               # Backward-compat shim -> src/mrc/daemon.py
```

---

## ⚡ Quickstart & Setup

### 1. Configure Global Hooks
In your global Antigravity hooks configuration (`~/.gemini/config/hooks.json`), register `PreToolUse` and `PostToolUse`:

```json
{
  "mobile-remote-control": {
    "enabled": true,
    "PreToolUse": [
      {
        "matcher": "write_to_file|replace_file_content|run_command",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/tongn/.gemini/antigravity/scratch/mrc-prototype/hooks/pre_tool_use.py",
            "timeout": 120
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "write_to_file|replace_file_content|run_command",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/tongn/.gemini/antigravity/scratch/mrc-prototype/hooks/post_tool_use.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 2. Configure `config.json`
Edit `config.json` in this repository:

```json
{
  "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "chat_id": 6489467735,
  "telegram_enabled": true,
  "remote_auto_accept": true,
  "auto_accept_timeout_seconds": 8,
  "timeout_seconds": 90
}
```

---

## 🚦 Operating Modes

| Mode | Configuration | Behavior |
| :--- | :--- | :--- |
| **Remote Mobile Mode** | `telegram_enabled: true`<br>`remote_auto_accept: false` | Outbound tool requests push diffs to Telegram with `[✅ Allow]` and `[❌ Deny]` buttons. Waits up to 90s for human tap. Local desk keyboard (`[Y]` / `[N]`) also available. |
| **Scoped Auto-Accept** | `telegram_enabled: true`<br>`remote_auto_accept: true` | Low-risk workspace edits and test commands show an 8s countdown on phone. If no objection, auto-approves. Dangerous commands require explicit tap. |
| **Local Machine Mode** | `telegram_enabled: false` | Network calls to Telegram are paused. The hook auto-approves tool calls locally on your workstation for seamless offline development. |

---

## 🧪 Testing & Verification

Run the complete modular unit test suite:

```powershell
python -m unittest discover -s tests -v
```

All 10 tests across Tiers 1–4 execute in `< 10ms`:
```
test_build_message_run_command (test_daemon.TestDaemonFormatting) ... ok
test_build_message_write_to_file (test_daemon.TestDaemonFormatting) ... ok
test_truncate (test_daemon.TestDaemonFormatting) ... ok
test_permission_overrides_builder (test_guardrails.TestGuardrails) ... ok
test_tier_1_destructive_git_blocked (test_guardrails.TestGuardrails) ... ok
test_tier_1_scratch_permitted (test_guardrails.TestGuardrails) ... ok
test_tier_1_system_configs_blocked (test_guardrails.TestGuardrails) ... ok
test_tier_2_brain_artifact_allowed (test_guardrails.TestGuardrails) ... ok
test_tier_3_risk_classifier (test_guardrails.TestGuardrails) ... ok
test_transient_lifecycle (test_session_grant.TestSessionGrant) ... ok

Ran 10 tests in 0.009s
OK
```

---

## 🗺️ Evolutionary Roadmap

- **✅ Milestone 1 (M1)**: Python Prototype with ADR-001 Guardrails, Single-Poller Daemon, and Transient Gate-2 Resolution.
- **🔄 Milestone 1.1 (M1.1)**: Pedagogical architectural walkthrough, formal UABI specification, and standalone compiled Dart port (`mrc.exe`).
- **⏳ Milestone 1.5 (M1.5)**: Multi-Client Provider MVP supporting Telegram Forum Topics per conversation and Discord Channels/Threads.
- **⏳ Milestone 2 (M2)**: Production background service daemon with native OS desktop notifications.
- **⏳ Milestone 3 (M3)**: Cryptographic session leasing, WebAuthn biometrics, and token budget auditing.
- **⏳ Milestone 4 (M4)**: Branded Flutter companion mobile app with offline queuing and WebSockets.

---

## 📖 Key Documentation Links
* [ADR-001: Guardrail & Permission Architecture](docs/ADR-001-guardrail-and-permission-architecture.md)
* [ADR-002: Package Structure & SRP Refactoring](docs/ADR-002-package-structure-and-srp-refactoring.md)
* [System Architecture & Sequence Diagrams](docs/ARCHITECTURE.md)
* [Universal Agent-Bridge Interface (UABI) Spec](docs/SPEC_UABI.md)
* [Engineering Progress & Incident Log](docs/PROGRESS.md)
* [Evolutionary Roadmap](docs/ROADMAP.md)
* [Task Tracker & Checklist](Task.md)
