"""
MRC Guardrails & Risk Classification Engine
Implements Tier 1 (Inviolable Hard Deny), Tier 2 (Brain Artifact Allowlists),
and Tier 3 (Scoped Auto-Accept Predicate) according to ADR-001.
"""

import os
import re
from typing import Tuple, List, Dict, Any


def is_hard_deny(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Tier 1 Inviolable Hard Deny Gate:
    Prevents unauthorized tampering with system configs, credentials, and destructive VCS.
    """
    if tool_name in ("write_to_file", "replace_file_content"):
        target = args.get("TargetFile", "").replace("/", "\\").lower()
        common_forbidden = [
            "hooks.json",
            "settings.json",
            "admin_settings.json",
            "\\.ssh\\",
            "id_rsa",
            "\\.aws\\",
            "\\.env"
        ]
        if "\\.gemini\\antigravity\\scratch\\" in target or "\\brain\\" in target:
            forbidden_substrings = common_forbidden
        else:
            forbidden_substrings = [
                "\\.gemini\\config\\",
                "\\.gemini\\antigravity-cli\\",
                "\\.gemini\\antigravity\\builtin\\"
            ] + common_forbidden

        for sub in forbidden_substrings:
            if sub in target:
                return True, f"Blocked modification targeting protected path: {target}"

    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "").strip()
        cmd_lower = cmd.lower()

        # Dangerous git commands
        if re.search(r"\bgit\s+push\b.*(--force|-f\b)", cmd_lower):
            return True, "Blocked destructive git push --force command."
        if re.search(r"\bgit\s+reset\b.*--hard", cmd_lower):
            return True, "Blocked destructive git reset --hard command."
        if re.search(r"\bgit\s+clean\b.*-[a-z]*f", cmd_lower):
            return True, "Blocked destructive git clean -f command."

        # Tampering with system configs via shell
        if re.search(r"(hooks\.json|settings\.json|\.gemini)", cmd_lower) and re.search(r"(>|>>|set-content|out-file|tee|echo\b)", cmd_lower):
            return True, "Blocked shell command targeting agent safety configurations."

    return False, ""


def is_brain_artifact(tool_name: str, args: Dict[str, Any], artifact_dir: str) -> bool:
    """
    Tier 2 Project-Scoped Allowlists:
    Internal agent brain artifacts (~/.gemini/.../brain/**) are auto-approved.
    """
    if tool_name in ("write_to_file", "replace_file_content"):
        target = args.get("TargetFile", "").replace("/", "\\").lower()
        if (artifact_dir and target.startswith(artifact_dir.replace("/", "\\").lower())) or "\\brain\\" in target:
            return True
    return False


def is_eligible_for_auto_accept(tool_name: str, args: Dict[str, Any], workspace_paths: List[str]) -> bool:
    """
    Tier 3 Scoped Auto-Accept Predicate:
    Only non-destructive workspace file edits and safe inspection/test commands
    qualify for the 8-second countdown. Everything else requires full human review.
    """
    if tool_name in ("write_to_file", "replace_file_content"):
        target_raw = args.get("TargetFile", "")
        if not target_raw:
            return False
        target = os.path.abspath(target_raw)
        
        # Must be strictly within configured workspace
        in_workspace = any(
            target.lower().startswith(os.path.abspath(ws).lower())
            for ws in workspace_paths
        )
        if not in_workspace:
            return False
            
        # Disallow dotfiles and root configs
        basename = os.path.basename(target).lower()
        if basename.startswith(".") or basename in ("package.json", "pubspec.yaml", "pyproject.toml"):
            return False
        return True

    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "").strip()
        cmd_lower = cmd.lower()
        safe_prefixes = [
            "git status", "git diff", "git log", "git branch",
            "fvm flutter test", "fvm flutter analyze", "fvm dart format",
            "melos list", "npm test", "npm run lint", "pytest",
            "get-childitem", "dir", "ls", "echo", "type", "cat"
        ]
        return any(cmd_lower.startswith(prefix) for prefix in safe_prefixes)

    return False


def build_permission_overrides(payload: Dict[str, Any]) -> List[str]:
    """Constructs protojson permission resource strings for Gate 2."""
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    overrides = []

    if tool_name == "run_command":
        cmd = args.get("CommandLine", "").strip()
        if cmd:
            overrides.append(f"command({cmd})")
    elif tool_name in ("write_to_file", "replace_file_content"):
        target = args.get("TargetFile", "").strip()
        if target:
            overrides.append(f"filesystem({target})")
    return overrides
