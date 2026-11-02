# Antigravity Guardrail & Permission Rules

## 1. Posture & Mode
- Maintain `toolPermission: "request-review"` across all CLI and GUI sessions.
- Do NOT configure wildcard `commandAllowlist: ["*"]` or `always-proceed` on host developer machines.
- Fail-closed is the fundamental invariant: failure to reach remote decision drops to terminal or aborts safely.

## 2. Hard Inviolable Boundaries (Tier 1)
- The agent must never write to, edit, or tamper with configuration files under `~/.gemini/` or lifecycle hook definitions (`hooks.json`).
- Destructive git operations (e.g. `push --force`, `clean -fdx`, `reset --hard`) require explicit, un-timer-gated human confirmation.
- Secrets and credentials (`.env`, `.ssh`, `id_rsa`, `.aws`) are hard-blocked from automated modification.

## 3. Scoped Risk & Auto-Accept (Tier 3)
- The 8-second auto-accept countdown is strictly scoped by predicate to:
  - Non-destructive workspace file edits (excluding root project manifests like `package.json`, `pubspec.yaml`, `pyproject.toml`).
  - Read-only or safe inspection/test commands (`git status`, `git diff`, `npm test`, `pytest`, `flutter test`, `fvm dart format`).
- Arbitrary, mutating, or deployment shell commands require affirmative human tap within the 90-second timeout window.

## 4. Remote Control Delegation & Single Resolution (Tier 4)
- When Mobile Remote Control is enabled, un-allowlisted tool calls dispatch rich diffs to Telegram/MRC for affirmative human review.
- Approvals granted via mobile remote satisfy the active turn without prompting secondary terminal dialogs.
- Transient permissions injected for remote resolution must be immediately purged post-execution.