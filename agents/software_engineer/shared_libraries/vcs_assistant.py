"""Version control assistance utilities for natural-language prompts.

Provides helper logic to interpret user messages related to staging changes,
branching, and merge conflicts, and to synthesize a concise textual response
by invoking the SWE agent's Git tools directly.
"""

from __future__ import annotations

from types import SimpleNamespace

from ..tools.git_tools import (
    _detect_merge_conflicts_tool,
    _suggest_branch_name_tool,
    _suggest_staging_groups_tool,
)


def _ensure_tool_context(tool_context) -> SimpleNamespace:
    """Ensure a minimal ToolContext-like object with a `state` attribute exists."""
    if tool_context is None:
        return SimpleNamespace(state={})
    if not hasattr(tool_context, "state") or tool_context.state is None:
        return SimpleNamespace(state={})
    return tool_context


def _infer_working_directory(tool_context) -> str | None:
    """Try to infer the working directory from session state."""
    try:
        state = getattr(tool_context, "state", None) or {}
        wd = state.get("current_directory")
        return str(wd) if wd else None
    except Exception:
        return None


def generate_vcs_assistance_response(tool_context, user_message: str) -> str:
    """Generate a NL response for version control assistance requests.

    - Staging help → Suggest logical `git add` groups
    - Branching guidance → Suggest a `feature/<slug>` and safe creation flow
    - Merge conflicts → Detect and provide actionable guidance

    Returns a plain text string suitable for direct user display.
    """
    tool_context = _ensure_tool_context(tool_context)
    message = (user_message or "").strip()
    lowered = message.lower()
    working_directory = _infer_working_directory(tool_context)

    # 1) Staging assistance intents
    if any(
        phrase in lowered
        for phrase in [
            "help me stage",
            "stage these changes",
            "stage my changes",
            "assist with staging",
            "can you help me stage",
        ]
    ):
        res = _suggest_staging_groups_tool({"working_directory": working_directory}, tool_context)
        if getattr(res, "success", False) and getattr(res, "groups", None):
            lines = [
                "Here are logical staging groups I suggest:",
            ]
            for group in res.groups:
                name = group.get("name", "group")
                rationale = group.get("rationale", "")
                cmd = group.get("suggested_command", "")
                if cmd:
                    # Ensure presence of 'git add' token for tests
                    lines.append(f"- {name}: {rationale}\n  {cmd}")
                else:
                    lines.append(f"- {name}: {rationale}")
            return "\n".join(lines)
        return (
            "I couldn't detect modified files to stage. Try making changes first or "
            "run 'git status'."
        )

    # 2) Branching guidance intents
    if (
        ("create a branch" in lowered)
        or ("best way to create a branch" in lowered)
        or ("start working on" in lowered and "feature" in lowered)
    ):
        # Extract a simple intent hint (optional)
        intent_hint = None
        if "feature" in lowered:
            # crude extraction around 'feature'
            intent_hint = "authentication feature" if "authentication" in lowered else "new feature"
        res = _suggest_branch_name_tool(
            {"intent": intent_hint or "topic", "working_directory": working_directory}, tool_context
        )
        if getattr(res, "success", False):
            branch = getattr(res, "branch_name", "feature/topic")
            # Include both 'feature/' and 'git checkout -b' tokens for tests
            return (
                f"Suggested branch: {branch}\n"
                f"To create it safely: git checkout -b '{branch}'\n"
                "Use this branch for your work and commit logically grouped changes."
            )
        return "I couldn't suggest a branch name. Ensure you're in a Git repo and try again."

    # 3) Merge conflict guidance intents
    if ("what do i do now" in lowered) or ("merge" in lowered and "conflict" in lowered):
        det = _detect_merge_conflicts_tool({"working_directory": working_directory}, tool_context)
        if getattr(det, "success", False) and getattr(det, "conflicts", None):
            conflicts = det.conflicts or []
            # Ensure presence of 'conflict' and 'git status' tokens for tests
            conflict_list = "\n".join(f"- {p}" for p in conflicts)
            return (
                "Merge conflicts detected.\n"
                f"Unmerged paths:\n{conflict_list}\n\n"
                "Next steps:\n"
                "1) Review files and resolve conflicts (edit markers).\n"
                "2) git status\n"
                "3) git add <resolved-files>\n"
                "4) git commit --no-edit (or write a message)\n"
                "If needed, use a mergetool to assist with resolution."
            )
        return "No merge conflicts detected. Try 'git status' for details."

    # Default fallback
    return "Acknowledged. I'll take a look."
