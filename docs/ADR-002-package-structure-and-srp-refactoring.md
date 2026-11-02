# ADR-002: Modular Python Package Structure & Single Responsibility Principle (SRP) Refactoring

## Status
**Accepted** (2026-11-03)

## Context & Problem Statement
During Milestone 1 (M1), rapid iteration produced a flat, monolithic directory structure:
- `mrc_bridge.py` contained hook parsing, hard-deny security gates, brain allowlists, risk classification predicates, transient Gate-2 permission injection, Telegram request formatting, workstation keyboard interception, and fallback logic.
- `mrc_daemon.py` combined Telegram Bot API polling, HTTP request handling, threading coordination, auto-accept countdown timers, and HTML message editing.
- `mrc_cleanup.py` was a standalone script directly manipulating `settings.json`.

While effective for fast-track prototyping, this flat layout exhibits several structural deficiencies:
1. **Violations of Single Responsibility Principle (SRP)**: Security policies, network I/O, message rendering, and lifecycle hook orchestration were intertwined. Modifying HTML diff formatting risked regressing security guardrails.
2. **Impediment to Multi-Client Evolution (M1.5 / M2)**: Telegram-specific polling logic was embedded in the core HTTP daemon. Adding Discord, Slack, or local webhooks would require invasive modifications to monolithic files.
3. **Friction in Multi-Language Compilation (M1.1)**: Porting the system to compiled Dart or Go requires clearly demarcated domain boundaries: Core Protocol / UABI DTOs, Security Guardrail Engine, Provider Clients, and Hook Shims.
4. **Testability & Regression Hazards**: Unit tests had to import monolithic scripts that executed side-effects on import or required complex monkey-patching.

## Decision Drivers
1. **Single Responsibility Principle (SRP)**: Every module must have exactly one reason to change.
2. **Language-Agnostic Blueprint**: The package layout must mirror the intended Dart package structure for M1.1 (`lib/src/guardrails/`, `lib/src/providers/`, `lib/src/daemon/`).
3. **Zero-Downtime Backward Compatibility**: Root hook entry points (`mrc_bridge.py`, `mrc_cleanup.py`, `mrc_daemon.py`) must remain as lightweight delegations so existing `hooks.json` configs never break.
4. **Clean Test Isolation**: Security rules, session grants, and daemon timers must be independently testable using standard Python `unittest`.

## Considered Alternatives
- **Alternative 1: Keep flat root structure**: Minimal file movement, but technical debt compounds as multi-client features (Discord, Topics) are added.
- **Alternative 2: Full enterprise microservices framework (FastAPI/Celery)**: Excessive overhead for a local background daemon running alongside `agy.exe`. Adds external pip dependencies.
- **Alternative 3: Modular `src/mrc/` layout with standard library only (Selected)**: Idiomatic Python package structure adhering to SRP, zero external dependencies, seamless migration to Dart.

## Decision: The Modular `src/mrc/` Architecture

We refactor the flat prototype into the following modular layout:

```
mrc-prototype/
├── pyproject.toml              # Packaging & test metadata (PEP 621)
├── Task.md                     # Granular task tracking
├── README.md                   # Project landing page & save-point guide
├── config.json                 # User configuration
├── docs/                       # Architecture, ADRs, Roadmap, Progress
│   ├── ADR-001-guardrail-and-permission-architecture.md
│   ├── ADR-002-package-structure-and-srp-refactoring.md
│   ├── ARCHITECTURE.md
│   ├── PROGRESS.md
│   ├── ROADMAP.md
│   └── SPEC_UABI.md
├── src/
│   └── mrc/                    # Core library package
│       ├── __init__.py         # Public exports & version
│       ├── config.py           # Paths, config loading, environment constants
│       ├── guardrails.py       # Tier 1 (Hard Deny) & Tier 3 (Auto-Accept Predicate)
│       ├── session_grant.py    # Tier 4 Gate-2 transient injection & cleanup
│       ├── formatting.py       # Message formatting & diff preview generator
│       ├── telegram_client.py  # Telegram API wrapper, single-thread poller
│       └── daemon.py           # Threaded HTTP daemon & request registry
├── hooks/
│   ├── pre_tool_use.py         # Entry point for Antigravity PreToolUse hook
│   └── post_tool_use.py        # Entry point for Antigravity PostToolUse hook
├── tests/
│   ├── __init__.py
│   ├── test_guardrails.py      # Unit tests for Tier 1 & Tier 3
│   ├── test_session_grant.py   # Unit tests for Tier 4 injection & cleanup
│   └── test_daemon.py          # Unit tests for HTTP daemon & timers
├── mrc_bridge.py               # Backward-compat shim -> hooks/pre_tool_use.py
├── mrc_cleanup.py              # Backward-compat shim -> hooks/post_tool_use.py
└── mrc_daemon.py               # Backward-compat shim -> src/mrc/daemon.py
```

### Module Responsibilities (SRP Breakdown):

| Module | Single Responsibility | Reason to Change |
| :--- | :--- | :--- |
| `src/mrc/config.py` | Centralizes path resolution and `config.json` loading. | Config schema changes or new system paths. |
| `src/mrc/guardrails.py` | Pure business logic evaluating Tier 1 (Hard Deny) and Tier 3 (Risk Predicate). | Security policy updates, new protected paths, or safe command allowlists. |
| `src/mrc/session_grant.py` | Manages transient Gate-2 grants in `settings.json` and `session_grants.json`. | Changes to Antigravity's settings schema (`permissions.allow` vs `commandAllowlist`). |
| `src/mrc/formatting.py` | Transforms tool payloads (`run_command`, `write_to_file`, etc.) into HTML/Markdown diff previews. | UI/UX adjustments to diff presentation on mobile devices. |
| `src/mrc/telegram_client.py` | Telegram Bot API client and dedicated single-thread update poller. | Telegram Bot API updates or callback handling. |
| `src/mrc/daemon.py` | Local HTTP daemon (`127.0.0.1:48201`), pending request registry, auto-accept timer, `/resolve`. | Daemon lifecycle, timeout policies, or IPC mechanics. |
| `hooks/pre_tool_use.py` | CLI stdin/stdout hook adapter that orchestrates the 4 tiers. | Protobuf / protojson hook wire format changes. |
| `hooks/post_tool_use.py` | CLI stdin/stdout hook adapter that triggers session grant purging. | PostToolUse lifecycle hook contract changes. |

## Consequences

### Positive:
- **High Cohesion, Low Coupling**: Guardrail security tests can run in 5ms without launching HTTP servers or mocking Telegram network calls.
- **Provider Agnostic**: The `daemon.py` request registry is decoupled from Telegram. Replacing Telegram with Discord or a Web UI in M1.5 requires only implementing a new provider adapter implementing the UABI interface.
- **Direct 1:1 Mapping to Dart**: The Dart port in M1.1 will mirror this exact structure: `lib/src/guardrails/`, `lib/src/daemon/`, `lib/src/providers/`.
- **Zero Disruption**: Existing global `hooks.json` registrations pointing to `mrc_bridge.py` and `mrc_cleanup.py` continue to function seamlessly via root forwarding shims.

### Negative:
- Adds a small directory hierarchy (`src/mrc/`, `hooks/`, `tests/`) compared to a flat directory.
- Requires relative module imports or `PYTHONPATH` configuration in entry points.
