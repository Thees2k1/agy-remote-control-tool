# Mobile Remote Control (MRC) Antigravity Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the M1 Mobile Remote Control (MRC) prototype into a production-ready, first-class Google Antigravity Plugin that provides out-of-band mobile authorization, chat-scoped hands-free mode, management MCP/slash-commands, and automatic interception/dispatch of the Antigravity Cloud Remote URL to Telegram.

**Architecture:** Package MRC into the standard Antigravity plugin structure (`plugin.json`, `hooks.json`, `mcp_config.json`, `rules/`, `skills/`). Intercept session start and tool lifecycles through declarative hooks (`SessionStart`, `PreToolUse`, `PostToolUse`). Provide an MCP server and skill definition (`skills/mrc/SKILL.md`) for seamless `/mrc` command orchestration, while managing the background bridge daemon via unified CLI commands (`mrc serve`, `mrc close`, `mrc remote`).

**Tech Stack:** Python 3.10+ (standard library + minimal dependencies), Model Context Protocol (MCP) JSON-RPC over stdio, Antigravity Customization Plugin Spec, Telegraf/HTTP Telegram Bot API.

**Spec:** [docs/ROADMAP.md](file:///C:/Users/tongn/.gemini/antigravity/scratch/mrc-prototype/docs/ROADMAP.md), [docs/ADR-001-guardrail-and-permission-architecture.md](file:///C:/Users/tongn/.gemini/antigravity/scratch/mrc-prototype/docs/ADR-001-guardrail-and-permission-architecture.md), [docs/ADR-002-package-structure-and-srp-refactoring.md](file:///C:/Users/tongn/.gemini/antigravity/scratch/mrc-prototype/docs/ADR-002-package-structure-and-srp-refactoring.md)

---

## Global Constraints

- **Fail-Closed Safety**: Maintain `toolPermission: "request-review"` at all times. No blanket wildcard bypasses (`"*"`).
- **Standard Plugin Layout**: Plugin root must contain valid `plugin.json` and root-level `hooks.json` conforming to Antigravity plugin specifications.
- **Zero Heavy Runtime Dependencies**: Core daemon and hooks must run on Python standard library without requiring external compiled C-extensions.
- **Backward Compatibility**: Existing `mrc_bridge.py`, `mrc_daemon.py`, and `mrc_cleanup.py` compatibility shims must remain functional.
- **Idempotent Lifecycle Operations**: Starting or stopping the daemon/service must never produce dangling socket locks or orphaned pollers.

## Review Focus

1. **Daemon State Transitions**: Calling `mrc close` when daemon is already stopped, or `mrc serve` when already active, must exit cleanly without port conflict errors.
2. **Cloud Remote Output Parsing**: If `agy remote-control status` has not yet generated an instance name, it must report a helpful pending state rather than crashing regex parsers.
3. **Session Hands-free Isolation**: Turning hands-free mode on or off for one conversation must not clobber global user defaults or affect distinct parallel conversation IDs.
4. **Network Outages**: If Telegram API is unreachable during cloud URL dispatch or tool authorization, fall back gracefully to local interactive terminal review (`ask`).
5. **Hook Payloads**: All hook inputs (`stdin`) and outputs (`stdout`) must strictly follow camelCase JSON contracts (`conversationId`, `stepIdx`, `toolCall`, `decision`).

---

## Task Decomposition

### Task 1: Plugin Manifest, Packaging & Directory Structure

**Files:**
- Create: `plugin.json`
- Create: `rules/AGENTS.md`
- Modify: `pyproject.toml`
- Test: `tests/test_plugin_manifest.py`

- [x] **Step 1: Write the failing manifest test**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Create `plugin.json`**
- [x] **Step 4: Create `rules/AGENTS.md`**
- [x] **Step 5: Update `pyproject.toml`**
- [x] **Step 6: Run test to confirm passing**

---

### Task 2: Cloud Remote URL Extractor & Telegram Broadcaster

**Files:**
- Create: `src/mrc/cloud_remote.py`
- Create: `tests/test_cloud_remote.py`
- Modify: `src/mrc/__init__.py`

- [x] **Step 1: Write the failing unit tests for cloud remote extractor**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement `src/mrc/cloud_remote.py`**
- [x] **Step 4: Run test to confirm passing**

---

### Task 3: Antigravity Plugin Hooks Integration (`SessionStart`, `PreToolUse`, `PostToolUse`)

**Files:**
- Create: `hooks.json`
- Create: `hooks/session_start.py`
- Modify: `hooks/pre_tool_use.py`
- Modify: `hooks/post_tool_use.py`
- Create: `tests/test_hooks_lifecycle.py`

- [x] **Step 1: Write the failing lifecycle hooks test**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement `hooks/session_start.py`**
- [x] **Step 4: Update `hooks/post_tool_use.py`**
- [x] **Step 5: Create root `hooks.json`**
- [x] **Step 6: Run test to confirm passing**

---

### Task 4: Chat-Scoped Hands-Free Mode Management

**Files:**
- Create: `src/mrc/session_state.py`
- Modify: `hooks/pre_tool_use.py`
- Create: `tests/test_session_state.py`

- [x] **Step 1: Write failing tests for session state manager**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement `src/mrc/session_state.py`**
- [x] **Step 4: Update `hooks/pre_tool_use.py`**
- [x] **Step 5: Run test to confirm passing**

---

### Task 5: Management MCP Server & `/mrc` Slash Command Skill

**Files:**
- Create: `src/mrc/mcp_server.py`
- Create: `mcp_config.json`
- Create: `skills/mrc/SKILL.md`
- Create: `tests/test_mcp_server.py`

- [x] **Step 1: Write failing tests for MCP Server**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement `src/mrc/mcp_server.py`**
- [x] **Step 4: Create `mcp_config.json`**
- [x] **Step 5: Create `skills/mrc/SKILL.md`**
- [x] **Step 6: Run test to confirm passing**

---

### Task 6: Unified CLI Entrypoint & Deliverable Installation Helper

**Files:**
- Create: `src/mrc/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/test_cli.py`
- Modify: `README.md`

- [x] **Step 1: Write failing CLI tests**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement `src/mrc/cli.py`**
- [x] **Step 4: Update `pyproject.toml`**
- [x] **Step 5: Run test to confirm passing**

---

### Task 7: Full System Verification & Regression Suite

**Files:**
- Create: `tests/test_e2e_plugin.py`
- Modify: `docs/ROADMAP.md`

- [x] **Step 1: Write end-to-end integration test**
- [x] **Step 2: Run full regression test suite**
- [x] **Step 3: Update documentation**
