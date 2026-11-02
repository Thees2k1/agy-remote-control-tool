# ADR-001: Hybrid Ask-First Guardrail Architecture & Fail-Closed Permission Model

* **Status**: Accepted
* **Date**: 2026-11-02
* **Authors**: Antigravity MRC Team
* **Scope**: Mobile Remote Control (MRC) Prototype, Antigravity CLI (`agy`), and GUI Workspaces

---

## 1. Context & Problem Statement

Autonomous and semi-autonomous coding agents execute shell commands and modify file systems. Developers face a fundamental architectural choice when establishing safety guardrails:

1. **Option A: Autonomous-by-Default (Fail-Open)**: Run tools automatically unless an explicit blocking rule, constraint, or safety net intercepts them.
2. **Option B: Ask-First by Default (Fail-Closed)**: Require human authorization before executing any mutating tool, selectively creating allowlists for known-safe actions.

During recent prototyping of Mobile Remote Control (MRC), attempting to bypass duplicate confirmation dialogs by configuring `"toolPermission": "always-proceed"` and `"commandAllowlist": ["*"]` inadvertently placed the entire agent into an unattended **auto-pilot** mode. This demonstrated the acute dangers of blanket autonomy: safety was eliminated rather than delegated.

Furthermore, Antigravity enforces a two-gate permission pipeline:
* **Gate 1 (Extension Hooks)**: `PreToolUse` lifecycle hooks running external audit scripts.
* **Gate 2 (Native UI Security Gate)**: `tool_confirmation_manager.go` in CLI / modal prompt in GUI, enforcing session-level user consent when `toolPermission` is set to `request-review`.

We need an architectural decision that preserves the core Antigravity philosophy of **"Human in Control"** while providing seamless, single-touch mobile oversight without duplicate prompts.

---

## 2. Decision: Hybrid Ask-First with Evidence-Based Allowlisting

We adopt **Ask-First, Then Allowlist** (Fail-Closed) as the foundational security architecture for MRC and workspace operations.

### 2.1 Core Architectural Principles

1. **Failure Asymmetry**:
   * *Ask-First Failure*: A missing allow rule costs one human tap (low-cost, immediately visible, safe).
   * *Autonomous-First Failure*: A missing block rule costs deleted directories, forced git pushes, corrupted environments, or leaked credentials (catastrophic, irreversible, silent).

2. **Blocklist Incompleteness**:
   * In modern shells (PowerShell, bash, zsh), an agent has infinite syntactical avenues to achieve destructive outcomes (`rm`, `Remove-Item`, `del`, piped scripts, dynamically written helper scripts). A blocklist can never be exhaustive.
   * An allowlist only needs to enumerate trusted, verified operations. Anything unlisted fails closed.

3. **Evidence-Based Policy Formation**:
   * Approvals provide empirical telemetry. Routine, repetitive actions that the developer repeatedly approves on mobile are gradually promoted to project-scoped allowlists based on actual usage evidence.

4. **Environmental Scoping**:
   * Autonomous-first is strictly reserved for throwaway sandboxes, isolated containers, or CLI sessions running with `--sandbox`.
   * Workstation host environments (containing user credentials, `~/.gemini`, SSH keys, and production repos) must strictly enforce Ask-First.

---

## 3. Four-Tier Hybrid Enforcement Model

All tool execution requests are evaluated through four hierarchical tiers:

```
                  [ Agent Emits Tool Call ]
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │ Tier 1: Hard Deny Gate (Inviolable)       │
        │ - Protected paths (~/.gemini/**, hooks)   │
        │ - Destructive VCS (git push --force)      │
        └───────────────────────────────────────────┘
                       │ Allowed
                       ▼
        ┌───────────────────────────────────────────┐
        │ Tier 2: Project-Scoped Allowlist          │
        │ - Read-only / verification commands       │
        │ - Pre-approved linters, tests, builds     │
        │ - Agent internal scratch/brain writes     │
        └───────────────────────────────────────────┘
                       │ Unmatched
                       ▼
        ┌───────────────────────────────────────────┐
        │ Tier 3: Scoped Auto-Accept (8s Timer)     │
        │ - Non-destructive, reversible operations  │
        │ - Explicitly guarded by predicates        │
        │ - Auto-accepts ONLY if no objection       │
        └───────────────────────────────────────────┘
                       │ Unmatched / High-Risk
                       ▼
        ┌───────────────────────────────────────────┐
        │ Tier 4: Remote Mobile Approval (MRC)      │
        │ - Dispatches diff & context to Telegram   │
        │ - Blocks execution until explicit tap     │
        │ - Resolves Gate 2 without duplicate UI    │
        └───────────────────────────────────────────┘
```

### Tier 1: Hard Deny Gate (Non-Overridable)
* Any command or file modification targeting system safety configurations (`~/.gemini/**`, `hooks.json`, `settings.json`, `admin_settings.json`), credentials, or dangerous git operations (`push --force`, `reset --hard` outside workspace) is **hard-blocked immediately** by the bridge. No mobile or local approval can override Tier 1.

### Tier 2: Project-Scoped Allowlist (Zero Friction)
* High-frequency, low-risk, idempotent operations are auto-approved without triggering remote notifications:
  * Safe tools: `view_file`, `list_dir`, `read_url_content`, `grep_search`.
  * Safe commands: `git status`, `git diff`, `fvm dart analyze`, `melos list`, read-only queries.
  * Internal agent artifacts: writes to `brain/`, `walkthrough.md`, `implementation_plan.md`.

### Tier 3: Scoped Auto-Accept (Constrained Convenience)
* The 8-second auto-accept timer must **never be applied as a blanket rule to all commands**.
* Auto-accept is restricted via predicates strictly to low-risk, reversible changes. If an action is high-risk (unrecognized shell command, critical source file deletion), the timer is disabled, requiring explicit human affirmation.

### Tier 4: Remote Mobile Approval (Human Oversight)
* For all un-allowlisted actions, the execution loop pauses and routes context/diff to the developer's mobile device via MRC.
* The developer taps `[✅ Allow]` or `[❌ Deny]`.
* **Gate 2 Bridge**: The mobile decision directly satisfies the native UI security gate (`tool_confirmation_manager.go`), eliminating duplicate prompts while preserving `request-review` as the active posture.

---

## 4. Consequences & Impact

### Positive
* **Safety Invariant Maintained**: The workstation is immune to rogue or hallucinated destructive agent actions.
* **Elimination of Auto-Pilot**: Reverts `settings.json` from `always-proceed` to `request-review`, ensuring the agent never runs unattended without explicit policy backing.
* **Optimized Developer Ergonomics**: Routine tasks stay fast via Tier 2 allowlists; novel tasks require only a single tap on mobile via Tier 4.
* **Deterministic Audit Trail**: All decisions are recorded in `last_decision_sent.json` and session transcripts with clear source provenance (`Mobile Phone`, `Workstation Keyboard`, `Allowlist`, `Auto-Accept Timer`).

### Negative / Trade-Offs
* Developers must maintain project allowlists as new workflows emerge.
* New shell commands require active mobile approval until promoted to Tier 2.

---

## 5. Compliance & Next Steps

1. **Revert Settings**: Immediately restore `~/.gemini/antigravity-cli/settings.json` to `"toolPermission": "request-review"` and remove wildcard `"*"` from `commandAllowlist`.
2. **Align Bridge Logic**: Update `mrc_bridge.py` and `mrc_daemon.py` to enforce Tier 1 hard denies and predicate-scoped Tier 3 auto-accepts.
3. **Persist Invariants**: Embed these rules into the project guidelines via `learning_proposal.md`.
