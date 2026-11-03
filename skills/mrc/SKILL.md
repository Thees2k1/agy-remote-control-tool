---
name: mrc
description: Manage Mobile Remote Control (MRC) daemon, cloud remote links, and hands-free review modes (/mrc serve, /mrc close, /mrc status, /mrc remote).
---

# Mobile Remote Control (MRC) Slash Commands & Management

Use this skill when the user invokes `/mrc` or asks to manage the Mobile Remote Control bridge, Antigravity Cloud Remote link, or hands-free permission routing.

## Available Subcommands

### 1. `/mrc status`
Inspect the operational state of the MRC daemon, listening port (48201), and active Antigravity Cloud Remote pairing.
- **Action**: Call the `mrc_status` MCP tool or run `python -m mrc status`.
- Report:
  - Daemon status (running or stopped)
  - Cloud Remote pairing name and link (`https://antigravity.google.com`)
  - Active session hands-free state

### 2. `/mrc serve`
Start the background daemon process to begin receiving out-of-band Telegram notifications.
- **Action**: Call the `mrc_serve` MCP tool or run `python -m mrc serve`.

### 3. `/mrc close`
Stop the background daemon process and release port 48201.
- **Action**: Call the `mrc_close` MCP tool or run `python -m mrc close`.

### 4. `/mrc remote`
Start Antigravity's built-in cloud remote service (`agy remote-control start`) and deliver the pairing link to Telegram.
- **Action**: Call the `mrc_cloud_remote` MCP tool or run `python -m mrc remote`.

### 5. `/mrc handsfree [on|off]`
Toggle chat-scoped hands-free mode for the active session.
- **Action**: Call `mrc_toggle_handsfree` with the current conversation ID.
- `on`: Routes reviews to Telegram with 8s auto-accept countdown.
- `off`: Prompts locally in the terminal.
