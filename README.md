# Mobile Remote Control (MRC) for Google Antigravity (Plugin v0.1.0)

[![Milestone](https://img.shields.io/badge/Milestone-M1%20Plugin%20Graduation%20(v0.1.0)-success)](docs/ROADMAP.md)
[![Architecture](https://img.shields.io/badge/Architecture-ADR--001%20%7C%20ADR--002-blue)](docs/)
[![Plugin](https://img.shields.io/badge/Antigravity-Native%20Plugin-orange)](plugin.json)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Mobile Remote Control (MRC)** transforms your personal smartphone (via Telegram/Discord) into an out-of-band authorization terminal for Google Antigravity (`agy` CLI & GUI). It enables developers to step away from their desk (AFK) while retaining real-time visibility, diff inspection, and one-tap approval over agent tool executions.

Graduated from the M1 Prototype into a native **Google Antigravity Plugin** with Model Context Protocol (MCP) management, chat-scoped hands-free mode, and automatic Antigravity Cloud Remote pairing broadcasts.

---

## 🚀 Native Plugin Features

- **Native Antigravity Plugin Packaging**: Directly installable into `.agents/plugins/` or `~/.gemini/config/plugins/` with `plugin.json`, declarative `hooks.json`, `rules/AGENTS.md`, and `skills/mrc/SKILL.md`.
- **Antigravity Cloud Remote Bridge**: Detects native `agy remote-control` state, extracts the active machine instance name, and broadcasts direct `https://antigravity.google.com` links to your Telegram bot.
- **Chat-Scoped Hands-Free Mode (`mrc handsfree [on|off]`)**: Switch between out-of-band mobile triage and local desktop prompts on a per-session or global basis.
- **MCP Management Server & Slash Commands (`/mrc`)**: Manage the daemon via stdio MCP tools (`mrc_status`, `mrc_serve`, `mrc_close`, `mrc_toggle_handsfree`, `mrc_cloud_remote`) or direct CLI commands.
- **Fail-Closed 4-Tier Security**: Maintains `toolPermission: "request-review"` at all times with strict protection for credentials and core configs.

---

## 📂 Project Architecture & Layout

```
mrc-prototype/
├── plugin.json                 # Antigravity Plugin Manifest (v0.1.0)
├── hooks.json                  # Declarative Plugin Hooks (SessionStart, PreToolUse, PostToolUse)
├── mcp_config.json             # Model Context Protocol Server declaration
├── mrc.py                      # Root CLI entrypoint (`python mrc.py status`)
├── README.md                   # Project landing page & documentation
├── Task.md                     # Roadmap task tracker & checklist
├── pyproject.toml              # PEP 621 packaging metadata
├── config.json                 # User configuration (token, chat_id, toggles)
├── rules/
│   └── AGENTS.md               # Antigravity agent behavior rules & hands-free contract
├── skills/
│   └── mrc/
│       └── SKILL.md            # `/mrc` slash command guide & MCP bindings
├── docs/                       # Architectural documentation
│   ├── ADR-001-guardrail-and-permission-architecture.md
│   ├── ADR-002-package-structure-and-srp-refactoring.md
│   ├── ARCHITECTURE.md         # Detailed sequence diagrams & component designs
│   ├── PROGRESS.md             # Incident analysis & chronological engineering log
│   ├── ROADMAP.md              # High-level model & evolutionary milestones (M1 -> M4)
│   └── SPEC_UABI.md            # Universal Agent-Bridge Interface wire protocol
├── src/
│   └── mrc/                    # Core library package
│       ├── __init__.py         # Version (0.1.0) & exports
│       ├── cli.py              # Unified CLI (`mrc serve|close|status|remote|handsfree`)
│       ├── cloud_remote.py     # Native `agy remote-control` extractor & broadcaster
│       ├── mcp_server.py       # MCP stdio JSON-RPC server (mrc-manager)
│       ├── session_state.py    # Per-conversation hands-free state manager
│       ├── config.py           # Paths, config loader, environment defaults
│       ├── guardrails.py       # Tier 1 Hard Deny & Tier 3 Risk Predicates
│       ├── session_grant.py    # Tier 4 Gate-2 transient injection & cleanup
│       ├── formatting.py       # Rich HTML diff preview & message formatting
│       ├── telegram_client.py  # Telegram API client & single-poller loop
│       └── daemon.py           # Threaded HTTP daemon (:48201) & registry
├── hooks/                      # Antigravity Lifecycle Hook Entry Points
│   ├── session_start.py        # SessionStart hook (cloud remote broadcast)
│   ├── pre_tool_use.py         # PreToolUse hook (stdin -> 4-tier evaluation -> stdout)
│   └── post_tool_use.py        # PostToolUse cleanup hook (stdin -> purge -> stdout)
└── tests/                      # Modular Unit Test Suite (38 unit tests)
```
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
