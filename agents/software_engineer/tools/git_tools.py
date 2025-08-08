"""Git-related tools for version control workflows (Milestone 6.1).

Implements:
- _get_staged_diff: obtain staged diff for context-aware commit messages
- generate_commit_message: suggest a commit message from diff + context
- commit_staged_changes: propose commit message for approval, then commit
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

from .shell_command import execute_shell_command

logger = logging.getLogger(__name__)


# ---------------------- Internal helpers (not exposed as tools) ----------------------


def _run_git(
    command: str, tool_context: ToolContext, cwd: str | None = None
) -> tuple[int, str, str]:
    """Run a git command via the shell tool for consistent history and error tracking."""
    result = execute_shell_command({"command": command, "working_directory": cwd}, tool_context)
    return int(result.exit_code), str(result.stdout or ""), str(result.stderr or "")


def _get_current_branch(tool_context: ToolContext, cwd: str | None) -> str:
    code, out, _ = _run_git("git rev-parse --abbrev-ref HEAD", tool_context, cwd)
    return out.strip() if code == 0 else ""


def _get_staged_files(tool_context: ToolContext, cwd: str | None) -> list[str]:
    code, out, _ = _run_git("git diff --staged --name-only", tool_context, cwd)
    if code != 0:
        return []
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _get_staged_diff(tool_context: ToolContext, cwd: str | None) -> str:
    """Return the full staged diff as a string."""
    code, out, err = _run_git("git diff --staged", tool_context, cwd)
    if code != 0:
        logger.warning("Failed to get staged diff: %s", err.strip())
        return ""
    return out


def _get_staged_numstat(tool_context: ToolContext, cwd: str | None) -> list[tuple[str, int, int]]:
    """Return (file, added, deleted) tuples for staged changes using numstat."""
    code, out, _ = _run_git("git diff --staged --numstat", tool_context, cwd)
    if code != 0:
        return []
    rows: list[tuple[str, int, int]] = []
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) == 3:
            try:
                added = int(parts[0]) if parts[0].isdigit() else 0
                deleted = int(parts[1]) if parts[1].isdigit() else 0
                rows.append((parts[2], added, deleted))
            except (ValueError, IndexError):
                continue
    return rows


def _detect_ticket(text: str) -> str:
    """Extract a JIRA-style ticket like ABC-123 from a string if present."""
    m = re.search(r"([A-Z]{2,10}-\d{1,6})", text or "")
    return m.group(1) if m else ""


def _guess_type_from_branch(branch: str) -> str:
    lowered = branch.lower()
    if lowered.startswith("feat/"):
        return "feat"
    if lowered.startswith("fix/"):
        return "fix"
    if lowered.startswith("refactor/"):
        return "refactor"
    if lowered.startswith("docs/"):
        return "docs"
    if lowered.startswith(("test/", "tests/")):
        return "test"
    return "chore"


def _guess_scope_from_files(files: list[str]) -> str:
    # Prefer a directory name like agents/, src/, tests/ as scope
    for prefix in ["src/", "agents/", "tests/", "docs/", "scripts/"]:
        for f in files:
            if f.startswith(prefix):
                # Use the first path segment (without trailing slash)
                return prefix.rstrip("/")
    # Fallback to first file stem
    if files:
        first = files[0]
        # Strip directories and extension
        base = first.rsplit("/", 1)[-1]
        scope = base.split(".")[0]
        return scope[:20]
    return ""


def _summarize_changes(numstats: list[tuple[str, int, int]]) -> str:
    files_changed = len(numstats)
    added = sum(a for _, a, _ in numstats)
    deleted = sum(d for _, _, d in numstats)
    return f"{files_changed} files changed, +{added}/-{deleted} lines"


def _shell_quote_single(s: str) -> str:
    """Safely quote a string for single-quoted shell arg: ' -> '\'' pattern."""
    return "'" + s.replace("'", "'\\''") + "'"


@dataclass
class _GeneratedMessage:
    title: str
    body: str


def _generate_conventional_message(
    diff_files: list[str], branch: str, context_hint: str | None
) -> _GeneratedMessage:
    ticket = _detect_ticket(context_hint or "") or _detect_ticket(branch)
    type_token = _guess_type_from_branch(branch)
    scope = _guess_scope_from_files(diff_files)
    scope_part = f"({scope})" if scope else ""

    # Heuristic title
    if diff_files:
        primary = diff_files[0].rsplit("/", 1)[-1]
    else:
        primary = "changes"

    title = f"{type_token}{scope_part}: update {primary}"

    body_lines: list[str] = []
    if ticket:
        body_lines.append(f"Refs: {ticket}")
    # The caller can augment body. Keep minimal to satisfy CI style checks.
    body = "\n".join(body_lines)
    return _GeneratedMessage(title=title, body=body)


# ------------------------------- Tool: get_staged_diff -------------------------------


class GetStagedDiffInput(BaseModel):
    working_directory: str | None = Field(
        default=None, description="Optional working directory of the Git repo"
    )


class GetStagedDiffOutput(BaseModel):
    success: bool
    diff: str
    message: str


def _get_staged_diff_tool(args: dict, tool_context: ToolContext) -> GetStagedDiffOutput:
    input_data = GetStagedDiffInput(**args)
    diff = _get_staged_diff(tool_context, input_data.working_directory)
    ok = bool(diff)
    msg = "Staged diff retrieved" if ok else "No staged changes or failed to get diff"
    return GetStagedDiffOutput(success=ok, diff=diff, message=msg)


get_staged_diff_tool = FunctionTool(func=_get_staged_diff_tool)


# --------------------------- Tool: generate_commit_message ---------------------------


class GenerateCommitMessageInput(BaseModel):
    context_hint: str | None = Field(
        default=None,
        description=(
            "Optional context such as a ticket ID or brief description to influence the message"
        ),
    )
    working_directory: str | None = Field(default=None)


class GenerateCommitMessageOutput(BaseModel):
    success: bool
    suggested_message: str
    branch: str
    details: dict | None = None


def _generate_commit_message_tool(
    args: dict, tool_context: ToolContext
) -> GenerateCommitMessageOutput:
    input_data = GenerateCommitMessageInput(**args)
    branch = _get_current_branch(tool_context, input_data.working_directory)
    files = _get_staged_files(tool_context, input_data.working_directory)
    gen = _generate_conventional_message(files, branch, input_data.context_hint)
    suggested = gen.title if not gen.body else f"{gen.title}\n\n{gen.body}"

    numstats = _get_staged_numstat(tool_context, input_data.working_directory)
    details = {
        "files": files,
        "summary": _summarize_changes(numstats),
    }
    return GenerateCommitMessageOutput(
        success=bool(files), suggested_message=suggested, branch=branch, details=details
    )


generate_commit_message_tool = FunctionTool(func=_generate_commit_message_tool)


# ----------------------------- Tool: commit_staged_changes ---------------------------


class CommitStagedChangesInput(BaseModel):
    message: str | None = Field(default=None, description="Optional explicit commit message to use")
    context_hint: str | None = Field(
        default=None, description="Optional context (e.g., ticket or short description)"
    )
    working_directory: str | None = Field(default=None)


class CommitStagedChangesOutput(BaseModel):
    status: str
    message: str
    branch: str | None = None
    used_message: str | None = None
    commit_hash: str | None = None
    proposed_message: str | None = None
    details: dict | None = None


def _commit_staged_changes(
    args: dict, tool_context: ToolContext
) -> CommitStagedChangesOutput | dict:
    """Propose a commit message for approval; on approval, perform the commit."""
    input_data = CommitStagedChangesInput(**args)
    cwd = input_data.working_directory

    # Gather context
    branch = _get_current_branch(tool_context, cwd)
    files = _get_staged_files(tool_context, cwd)
    if not files:
        return CommitStagedChangesOutput(
            status="error",
            message="No staged changes to commit.",
            branch=branch,
        )

    # Determine the message
    proposed_message = input_data.message
    if not proposed_message:
        gen = _generate_conventional_message(files, branch, input_data.context_hint)
        proposed_message = gen.title if not gen.body else f"{gen.title}\n\n{gen.body}"

    # If approval not yet granted, return pending proposal
    force = bool(tool_context.state.get("force_edit", False))
    if not force:
        numstats = _get_staged_numstat(tool_context, cwd)
        summary = _summarize_changes(numstats)
        # Persist proposal to state for the approval rerun
        tool_context.state["pending_commit_proposal"] = {
            "branch": branch,
            "message": proposed_message,
            "working_directory": cwd,
            "files": files,
            "summary": summary,
        }
        # Construct a generic approval proposal compatible with the existing workflow
        return {
            "status": "pending_approval",
            "type": "generic",
            "title": "Commit Message Proposal",
            "description": "Proposed commit message generated from staged changes.",
            "details": f"Branch: {branch}\n{summary}",
            # The approval UI prints the 'message' field
            "message": f"Proposed commit message:\n\n{proposed_message}",
            "proposed_message": proposed_message,
        }

    # Approval granted: perform the commit
    proposal = tool_context.state.get("pending_commit_proposal", {})
    final_message = input_data.message or proposal.get("message") or proposed_message
    # Safety: ensure we still have a message
    if not final_message:
        return CommitStagedChangesOutput(
            status="error", message="No commit message available after approval.", branch=branch
        )

    quoted = _shell_quote_single(final_message)
    code, out, err = _run_git(f"git commit -m {quoted}", tool_context, cwd)
    if code != 0:
        return CommitStagedChangesOutput(
            status="error",
            message=f"Failed to commit: {err.strip() or out.strip()}",
            branch=branch,
            used_message=final_message,
        )

    # Retrieve the commit hash
    _, hash_out, _ = _run_git("git rev-parse HEAD", tool_context, cwd)
    commit_hash = hash_out.strip() if hash_out else None

    # Cleanup pending proposal
    if "pending_commit_proposal" in tool_context.state:
        del tool_context.state["pending_commit_proposal"]

    return CommitStagedChangesOutput(
        status="success",
        message="Commit created successfully.",
        branch=branch,
        used_message=final_message,
        commit_hash=commit_hash,
    )


commit_staged_changes_tool = FunctionTool(func=_commit_staged_changes)


__all__ = [
    "commit_staged_changes_tool",
    "generate_commit_message_tool",
    "get_staged_diff_tool",
]
