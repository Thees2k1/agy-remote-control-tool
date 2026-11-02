"""
MRC Message & Diff Formatter
Generates structured HTML previews and summaries for Telegram/Discord notifications.
"""

import os
import json
from html import escape
from typing import Tuple, Dict, Any


def truncate(s: str, max_len: int = 1500) -> str:
    """Truncate text with an indicator if it exceeds max_len."""
    if not s:
        return ""
    if len(s) > max_len:
        return s[:max_len] + f"\n... [truncated {len(s) - max_len} chars]"
    return s


def build_message_and_summary(payload: Dict[str, Any]) -> Tuple[str, str]:
    """
    Builds rich HTML notification text and a short summary from the toolCall payload.
    """
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "unknown")
    args = tool_call.get("args", {})
    step = payload.get("stepIdx", "?")

    header = f"🚨 <b>Agent Tool Approval Request</b> (Step #{step})\n"
    diff_block = ""
    summary_text = ""

    if tool_name == "write_to_file":
        target = args.get("TargetFile", "")
        code = args.get("CodeContent", "")
        desc = args.get("Description", "")
        lines = len(code.splitlines()) if code else 0
        target_info = f"📁 <b>Target:</b> <code>{escape(target)}</code>\n"
        if desc:
            target_info += f"📝 <b>Desc:</b> {escape(desc)}\n"
        summary_text = f"Writing file (+{lines} lines)"
        snippet = truncate(code, 2000)
        diff_block = f"<pre><code class=\"language-text\">{escape(snippet)}</code></pre>"

    elif tool_name == "replace_file_content":
        target = args.get("TargetFile", "")
        instruction = args.get("Instruction", "")
        desc = args.get("Description", "")
        target_content = args.get("TargetContent", "")
        replacement = args.get("ReplacementContent", "")
        lines_range = f"L{args.get('StartLine', '?')}-L{args.get('EndLine', '?')}"
        target_info = f"📁 <b>Target:</b> <code>{escape(target)}</code> ({escape(lines_range)})\n"
        if instruction:
            target_info += f"📝 <b>Instruction:</b> {escape(instruction)}\n"
        elif desc:
            target_info += f"📝 <b>Desc:</b> {escape(desc)}\n"
        summary_text = f"Replace lines in {os.path.basename(target) if target else 'file'}"
        diff_preview = (
            f"--- Target Content ---\n{target_content}\n"
            f"+++ Replacement Content +++\n{replacement}"
        )
        diff_block = f"<pre><code class=\"language-diff\">{escape(truncate(diff_preview, 2200))}</code></pre>"

    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "")
        cwd = args.get("Cwd", "")
        desc = args.get("Description", "")
        target_info = f"💻 <b>Command:</b> <code>{escape(cmd)}</code>\n"
        if cwd:
            target_info += f"📂 <b>Cwd:</b> <code>{escape(cwd)}</code>\n"
        if desc:
            target_info += f"📝 <b>Desc:</b> {escape(desc)}\n"
        summary_text = f"Execute command: {cmd[:40]}..."
        diff_block = f"<pre><code class=\"language-bash\">{escape(cmd)}</code></pre>"

    else:
        target_info = f"🔧 <b>Tool:</b> <code>{escape(tool_name)}</code>\n"
        args_json = json.dumps(args, indent=2)
        diff_block = f"<pre>{escape(truncate(args_json, 1500))}</pre>"
        summary_text = f"Execute tool {tool_name}"

    full_message = f"{header}\n{target_info}\n<b>Summary:</b> {escape(summary_text)}\n\n{diff_block}"
    return full_message, summary_text
