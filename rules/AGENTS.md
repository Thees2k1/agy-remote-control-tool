# Mobile Remote Control (MRC) Agent Guidelines

These rules apply when the `mobile-remote-control` plugin is active.

## Core Behavioral Principles

1. **Fail-Closed Security Posture**:
   - The environment operates under `toolPermission: "request-review"` at all times.
   - Do NOT bypass security checks or write to protected configuration files (`~/.gemini/config/hooks.json`, `settings.json`, credentials in `.ssh`, `.aws`, `.env`).

2. **Hands-Free Mode Operation (`mrc --handsfree`)**:
   - When hands-free mode is enabled for the session, mutating tool calls (`write_to_file`, `replace_file_content`, `run_command`) are intercepted and routed to the user's mobile device (e.g. Telegram bot) for out-of-band diff inspection and approval.
   - For safe read-only commands and internal project edits, an 8-second countdown provides auto-approval without waking the user unless they intervene.
   - Destructive actions (e.g. git reset, file deletion, rm -rf) wait up to 90 seconds for explicit human authorization.

3. **Remote Control Integration**:
   - When launching or interacting with Antigravity Remote Control (`agy remote-control`), the cloud connection URL (`https://antigravity.google.com`) is broadcast directly to the user's mobile chat surface.

4. **Slash Commands & MCP Tools**:
   - Use `/mrc serve` or `mrc_serve` to ensure the background bridge daemon is running.
   - Use `/mrc close` or `mrc_close` to stop the bridge when finished.
   - Use `/mrc status` or `mrc_status` to inspect active connections and session modes.
   - Use `/mrc remote` to initialize Antigravity Cloud Remote and deliver the pairing link.
