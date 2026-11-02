# Mobile Remote Control (MRC): Task Tracker & Roadmap Checklist

## Milestone 1: Fast-Track Prototype (Completed ✅)
- [x] Fix duplicate CLI/GUI confirmation prompts without disabling security posture.
- [x] Restore `toolPermission: "request-review"` and purge permanent wildcard allowlists (`*`).
- [x] Implement Tier 1 Hard Deny (block `~/.gemini/**`, `hooks.json`, `settings.json`, credentials, force-push).
- [x] Implement Tier 2 Project Allowlists (auto-approve internal agent brain artifacts).
- [x] Implement Tier 3 Scoped Auto-Accept Predicate (8s timer for low-risk actions; 90s for mutating actions).
- [x] Implement Tier 4 Transient Session Grants in `settings.json` with immediate `PostToolUse` cleanup.
- [x] Solve Telegram double-tap bug via dedicated single-thread poller in `mrc_daemon.py`.
- [x] Add `/resolve` endpoint for instantaneous desk keyboard resolution (`[Y]` / `[N]`).
- [x] Build automated test suite (`test_suite_m1.py`) validating Tiers 1–4 with 100% pass rate.
- [x] Document [ADR-001: Guardrail & Permission Architecture](docs/ADR-001-guardrail-and-permission-architecture.md).

---

## Current: M1 "Bonfire Save-Point" & SRP Refactoring (Completed ✅)
- [x] Document [ADR-002: Package Structure & SRP Refactoring](docs/ADR-002-package-structure-and-srp-refactoring.md).
- [x] Distill session context into [ROADMAP.md](docs/ROADMAP.md) & [PROGRESS.md](docs/PROGRESS.md).
- [x] Create [ARCHITECTURE.md](docs/ARCHITECTURE.md) & [SPEC_UABI.md](docs/SPEC_UABI.md).
- [x] Create `pyproject.toml` and directory skeleton (`src/mrc/`, `hooks/`, `tests/`).
- [x] Refactor modular Python packages:
  - [x] `src/mrc/config.py` (Paths and config loader)
  - [x] `src/mrc/guardrails.py` (Tier 1 & Tier 3 logic)
  - [x] `src/mrc/session_grant.py` (Tier 4 Gate-2 injection & cleanup)
  - [x] `src/mrc/formatting.py` (Diff rendering & Telegram HTML)
  - [x] `src/mrc/telegram_client.py` (Telegram API client & single poller)
  - [x] `src/mrc/daemon.py` (Threaded HTTP server & registry)
- [x] Implement entry points in `hooks/pre_tool_use.py` and `hooks/post_tool_use.py`.
- [x] Provide backward-compatible root shims (`mrc_bridge.py`, `mrc_cleanup.py`, `mrc_daemon.py`).
- [x] Migrate tests to standard modular layout (`tests/test_guardrails.py`, `tests/test_session_grant.py`, `tests/test_daemon.py`).
- [x] Verify test suite passes via `python -m unittest discover -s tests -v`.
- [x] Write comprehensive [README.md](README.md) save-point guide.
- [x] Toggle `"telegram_enabled": true` in `config.json` and validate live Telegram remote control & auto-accept.
- [x] Implement Desk-First Grace Period (4s local keyboard window before mobile escalation).
- [x] Implement Universal Transient Gate-2 Session Grants (commands + filesystem operations).
- [x] Add automated test suite for Desk Grace Period (`tests/test_desk_grace.py`).
- [x] Save-point commits recorded (`ed27021`, `b845280`).

---

## Milestone 1.1: Pedagogical Deep-Dive & Dart Port (Upcoming ⏳)
- [ ] Comprehensive architectural walkthrough of the refactored system.
- [ ] Initialize Dart package (`dart create -t console mrc_dart`).
- [ ] Implement UABI DTOs in Dart (`package:mrc/src/protocol/`).
- [ ] Implement Guardrails & Gate-2 Bridge in Dart (`package:mrc/src/guardrails/`).
- [ ] Implement single-thread Telegram long-poller via `dart:io` `HttpClient`.
- [ ] Compile standalone native binary (`dart compile exe bin/mrc.dart -o mrc.exe`).
- [ ] Benchmark startup latency and memory footprint against Python prototype.

---

## Milestone 1.5: Multi-Client Adapter MVP (Telegram Topics + Discord ⏳)
- [ ] Implement Telegram Forum Topics (`message_thread_id`) per agent conversation.
- [ ] Implement Discord bot provider with ActionRow buttons (`type: 2`).
- [ ] Verify concurrent multi-agent approvals across channels without collision.
