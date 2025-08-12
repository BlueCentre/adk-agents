"""Git-related tools for version control workflows (Milestones 6.1 and 6.2).

Implements:
- _get_staged_diff: obtain staged diff for context-aware commit messages
- generate_commit_message: suggest a commit message from diff + context
- commit_staged_changes: propose commit message for approval, then commit
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Optional  # noqa: F401

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
    return int(result.exit_code), (result.stdout or ""), (result.stderr or "")


def _get_current_branch(tool_context: ToolContext, cwd: str | None) -> str:
    code, out, _ = _run_git("git rev-parse --abbrev-ref HEAD", tool_context, cwd)
    return out.strip() if code == 0 else ""


def _get_git_status_porcelain(tool_context: ToolContext, cwd: str | None) -> list[str]:
    """Return lines from `git status --porcelain=v1 -b`.

    Includes branch header followed by file status entries.
    """
    code, out, err = _run_git("git status --porcelain=v1 -b", tool_context, cwd)
    if code != 0:
        logger.warning("Failed to get git status: %s", err.strip())
        return []
    return [ln for ln in out.splitlines() if ln]


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
    """Extract a JIRA-style ticket like ABC-123 from a string if present (case-insensitive)."""
    m = re.search(r"([A-Z]{2,10}-\d{1,6})", text or "", re.IGNORECASE)
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
    """Infer a Conventional Commits scope from file paths.

    Prefer top-level directories like `src/`, `agents/`, or `tests/`. As a fallback, use
    the stem (filename without extension) of the first changed file, truncated to 20 chars.
    """
    from pathlib import Path

    for prefix in ["src/", "agents/", "tests/", "docs/", "scripts/"]:
        for file_path in files:
            if file_path.startswith(prefix):
                return prefix.rstrip("/")

    if files:
        first = files[0]
        base = first.rsplit("/", 1)[-1]
        scope = Path(base).stem
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


def _slugify_topic(text: str) -> str:
    """Create a lowercase, hyphenated slug from the topic text."""
    text = (text or "").strip().lower()
    # Replace non-alphanumeric with hyphen, collapse duplicates
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "topic"


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
    """Return the staged diff for the current repo.

    Usage: when the user asks to "show staged changes" or before proposing a commit.
    Args may be omitted; defaults to the current working directory.
    """
    input_data = GetStagedDiffInput(**(args or {}))
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
    """Suggest a Conventional Commits message for staged changes.

    Works without args. Optionally provide `context_hint` (e.g., ticket ID) and
    `working_directory`. The result follows Conventional Commits style.
    """
    input_data = GenerateCommitMessageInput(**(args or {}))
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
    """Propose a Conventional Commits message and commit upon approval.

    Behavior:
    - No args needed. If `message` is omitted, generates a Conventional Commits title
      (with optional body) from staged files, branch and optional `context_hint`.
    - First call returns a `pending_approval` payload with the proposal.
    - After approval, re-run (the agent sets `force_edit`) and the commit is created.
    """
    input_data = CommitStagedChangesInput(**(args or {}))
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
    if not tool_context.state.get("force_edit", False):
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

    # Cleanup pending proposal without relying on __delitem__
    try:
        tool_context.state["pending_commit_proposal"] = None
    except Exception:
        pass

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


# ------------------------------ Tool: staging suggestions ------------------------------


class SuggestStagingGroupsInput(BaseModel):
    working_directory: str | None = Field(default=None)


class SuggestStagingGroupsOutput(BaseModel):
    success: bool
    groups: list[dict]
    message: str


def _cluster_files_for_staging(files: list[str]) -> list[dict]:
    """Cluster files into logical staging groups.

    Heuristics:
    - Group by top-level directory (e.g., agents/, src/, tests/, docs/, scripts/)
    - Separate tests from src when stems match
    - Fallback single group for remaining files
    """
    from collections import defaultdict
    from pathlib import Path

    buckets: dict[str, list[str]] = defaultdict(list)
    for path in files:
        if "/" in path:
            top = path.split("/", 1)[0]
        else:
            top = "root"
        key = top
        # Normalize some common folders
        if top in {"tests", "test"}:
            key = "tests"
        elif top in {"docs"}:
            key = "docs"
        elif top in {"scripts"}:
            key = "scripts"
        buckets[key].append(path)

    groups: list[dict] = []
    for key, members in buckets.items():
        rationale = f"Files under {key}/" if key != "root" else "Repository root files"
        # Provide a suggested command
        file_list = " ".join(_shell_quote_single(m) for m in members)
        groups.append(
            {
                "name": f"stage-{key}",
                "files": members,
                "rationale": rationale,
                "suggested_command": f"git add {file_list}",
            }
        )

    # Additional test/src pairing suggestion
    stems = {}
    for f in files:
        stems.setdefault(Path(f).stem, []).append(f)
    for stem, members in stems.items():
        if len(members) > 1 and any("test" in m for m in members):
            quoted_members = " ".join(_shell_quote_single(m) for m in members)
            groups.append(
                {
                    "name": f"stage-related-{stem}",
                    "files": members,
                    "rationale": (f"Related files by stem '{stem}' (tests and implementation)"),
                    "suggested_command": f"git add {quoted_members}",
                }
            )

    return groups


def _suggest_staging_groups_tool(
    args: dict, tool_context: ToolContext
) -> SuggestStagingGroupsOutput:
    input_data = SuggestStagingGroupsInput(**(args or {}))
    status_lines = _get_git_status_porcelain(tool_context, input_data.working_directory)
    if not status_lines:
        return SuggestStagingGroupsOutput(success=False, groups=[], message="No changes detected")

    # Parse porcelain lines: status columns then path; ignore branch header starting with '##'
    changed_files: list[str] = []
    for ln in status_lines:
        if ln.startswith("##"):
            continue
        # format: XY path (or rename format 'R path1 -> path2')
        # We take the last path token after space or arrow
        try:
            if "->" in ln:
                path = ln.split("->", 1)[1].strip()
            else:
                path = ln[3:].strip()
        except Exception:
            continue
        if path:
            changed_files.append(path)

    if not changed_files:
        return SuggestStagingGroupsOutput(success=False, groups=[], message="No modified files")

    groups = _cluster_files_for_staging(changed_files)
    return SuggestStagingGroupsOutput(
        success=True, groups=groups, message="Staging suggestions ready"
    )


suggest_staging_groups_tool = FunctionTool(func=_suggest_staging_groups_tool)


# ------------------------------ Tools: branching assistance -----------------------------


class SuggestBranchNameInput(BaseModel):
    intent: str = Field(
        default="",
        description="Short description of the work, e.g., 'authentication feature' (optional)",
    )
    kind: str | None = Field(
        default=None,
        description="Optional type: feature|fix|chore|docs|refactor|test. Guessed if omitted.",
    )
    working_directory: str | None = Field(default=None)


class SuggestBranchNameOutput(BaseModel):
    success: bool
    branch_name: str
    message: str


def _suggest_branch_name_tool(args: dict, tool_context: ToolContext) -> SuggestBranchNameOutput:  # noqa: ARG001
    input_data = SuggestBranchNameInput(**(args or {}))
    # Prefer 'feature' by default when intent is provided; allow override via kind.
    guessed_kind = input_data.kind or "feat"
    # Map Conventional Commit type to common branch prefixes
    prefix_map = {
        "feat": "feature",
        "fix": "fix",
        "refactor": "refactor",
        "docs": "docs",
        "test": "test",
        "chore": "chore",
    }
    prefix = prefix_map.get(guessed_kind, "feature")
    # Fallback to "topic" if no intent is provided
    slug = _slugify_topic(input_data.intent or "topic")
    suggested = f"{prefix}/{slug}"
    return SuggestBranchNameOutput(
        success=True, branch_name=suggested, message="Suggested branch name"
    )


class CreateBranchInput(BaseModel):
    name: str | None = Field(
        default=None, description="Branch name to create. If omitted, derive from intent."
    )
    intent: str | None = Field(
        default=None, description="Optional intent to derive name when `name` absent"
    )
    kind: str | None = Field(default=None, description="Optional type to influence naming")
    working_directory: str | None = Field(default=None)


class CreateBranchOutput(BaseModel):
    status: str
    message: str
    branch: str | None = None


def _create_branch_tool(args: dict, tool_context: ToolContext) -> CreateBranchOutput | dict:
    """Create a new branch after human approval.

    First call returns a pending approval proposal with the suggested name and commands.
    On approval (agent sets force_edit), the branch is created via `git checkout -b`.
    """
    input_data = CreateBranchInput(**(args or {}))
    cwd = input_data.working_directory

    branch_name = input_data.name
    if not branch_name:
        # Derive from intent/kind (intent optional)
        suggested = _suggest_branch_name_tool(
            {"intent": input_data.intent, "kind": input_data.kind, "working_directory": cwd},
            tool_context,
        )
        branch_name = suggested.branch_name

    # If approval not granted yet, return proposal
    if not tool_context.state.get("force_edit", False):
        details = f"This will create and switch to a new branch: {branch_name}"
        tool_context.state["pending_branch_proposal"] = {
            "branch_name": branch_name,
            "working_directory": cwd,
        }
        return {
            "status": "pending_approval",
            "type": "generic",
            "title": "Create Git Branch",
            "description": "Proposed new branch creation",
            "details": details,
            "message": f"Run: git checkout -b {_shell_quote_single(branch_name)}",
        }

    # Approval granted: execute command
    quoted_branch = _shell_quote_single(branch_name)
    code, out, err = _run_git(f"git checkout -b {quoted_branch}", tool_context, cwd)
    # Clear proposal without relying on pop/__delitem__
    try:
        tool_context.state["pending_branch_proposal"] = None
    except Exception:
        pass
    if code != 0:
        return CreateBranchOutput(status="error", message=(err.strip() or out.strip()), branch=None)
    return CreateBranchOutput(status="success", message="Branch created", branch=branch_name)


suggest_branch_name_tool = FunctionTool(func=_suggest_branch_name_tool)
create_branch_tool = FunctionTool(func=_create_branch_tool)


# --------------------------- Tool: detect merge conflicts (basic) ---------------------------


class DetectMergeConflictsInput(BaseModel):
    working_directory: str | None = Field(default=None)


class DetectMergeConflictsOutput(BaseModel):
    success: bool
    conflicts: list[str]
    message: str


def _detect_merge_conflicts_tool(
    args: dict, tool_context: ToolContext
) -> DetectMergeConflictsOutput:
    input_data = DetectMergeConflictsInput(**(args or {}))
    status_lines = _get_git_status_porcelain(tool_context, input_data.working_directory)
    conflicts: list[str] = []
    for ln in status_lines:
        if ln.startswith("##"):
            continue
        # X or Y value of 'U' indicates unmerged path
        if ln and (ln[0] == "U" or (len(ln) > 1 and ln[1] == "U")):
            path = ln[3:].strip()
            if path:
                conflicts.append(path)

    if not conflicts:
        return DetectMergeConflictsOutput(
            success=True, conflicts=[], message="No merge conflicts detected"
        )
    return DetectMergeConflictsOutput(
        success=True, conflicts=conflicts, message="Merge conflicts detected"
    )


detect_merge_conflicts_tool = FunctionTool(func=_detect_merge_conflicts_tool)


# Extend exports
__all__ += [
    "create_branch_tool",
    "detect_merge_conflicts_tool",
    "suggest_branch_name_tool",
    "suggest_staging_groups_tool",
]
