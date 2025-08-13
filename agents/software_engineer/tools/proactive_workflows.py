"""Proactive workflow tools that aggregate multi-step actions behind one approval.

This module provides a single-call tool for preparing a pull request plan that:
- analyzes the repository state,
- suggests staging groups, branch name, and commit message,
- proposes an optional push command if a remote exists,
- asks the user for a single confirmation, and
- upon approval, executes the plan end-to-end.

Goal: reduce back-and-forth and avoid trivial questions. Only ask to confirm.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

from .git_tools import (
    _generate_commit_message_tool,
    _get_git_status_porcelain,
    _get_staged_files,
    _run_git,
    _shell_quote_single,
    _suggest_branch_name_tool,
)
from .shell_command import execute_shell_command

logger = logging.getLogger(__name__)


class PreparePullRequestInput(BaseModel):
    intent: str | None = Field(
        default=None, description="Short intent for naming, e.g., 'authentication feature'"
    )
    kind: str | None = Field(
        default=None, description="Optional type: feature|fix|chore|docs|refactor|test"
    )
    working_directory: str | None = Field(default=None)


class PreparePullRequestOutput(BaseModel):
    status: str
    message: str
    steps: list[str] = Field(default_factory=list)
    branch: str | None = None
    commit_message: str | None = None
    pushed: bool | None = None


@dataclass
class _Plan:
    working_directory: str | None
    staging_commands: list[str]
    branch_name: str
    commit_message: str
    push_command: str | None


def _detect_remote_origin(tool_context: ToolContext, cwd: str | None) -> bool:
    code, out, _ = _run_git("git remote -v", tool_context, cwd)
    if code != 0:
        return False
    return any(line.split()[0] == "origin" for line in out.splitlines() if line.strip())


def _get_origin_https_url(tool_context: ToolContext, cwd: str | None) -> str | None:
    """Return the HTTPS GitHub URL for the origin remote if derivable.

    Examples:
    - git@github.com:owner/repo.git -> https://github.com/owner/repo
    - https://github.com/owner/repo.git -> https://github.com/owner/repo
    - other hosts return None
    """
    code, out, _ = _run_git("git remote get-url origin", tool_context, cwd)
    if code != 0:
        return None
    url = out.strip()
    if not url:
        return None
    pattern = r"(?:git@github\.com:|https://github\.com/)(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$"
    m = re.match(pattern, url)
    if m:
        return f"https://github.com/{m.group('owner')}/{m.group('repo')}"
    return None


def _compute_staging_commands(tool_context: ToolContext, cwd: str | None) -> list[str]:
    status_lines = _get_git_status_porcelain(tool_context, cwd)
    files: list[str] = []
    for ln in status_lines:
        if ln.startswith("##"):
            continue
        try:
            path = ln.split("->", 1)[1].strip() if "->" in ln else ln[3:].strip()
        except Exception:
            continue
        if path:
            files.append(path)
    if not files:
        return []
    quoted = " ".join(_shell_quote_single(p) for p in files)
    return [f"git add {quoted}"]


def _build_plan(input_data: PreparePullRequestInput, tool_context: ToolContext) -> _Plan | None:
    cwd = input_data.working_directory

    staging_cmds = _compute_staging_commands(tool_context, cwd)

    # Determine branch suggestion
    # Filter out None values to avoid Pydantic validation errors
    name_args = {"working_directory": cwd}
    if input_data.intent is not None:
        name_args["intent"] = input_data.intent
    if input_data.kind is not None:
        name_args["kind"] = input_data.kind

    name_res = _suggest_branch_name_tool(name_args, tool_context)
    branch_name = getattr(name_res, "branch_name", "feature/topic")

    # Determine commit message suggestion (works even if nothing staged yet)
    msg_res = _generate_commit_message_tool(
        {"context_hint": input_data.intent, "working_directory": cwd}, tool_context
    )
    commit_message = getattr(msg_res, "suggested_message", "chore: update changes")

    # Optional push step
    push_cmd: str | None = None
    if _detect_remote_origin(tool_context, cwd):
        push_cmd = f"git push -u origin {_shell_quote_single(branch_name)}"

    return _Plan(
        working_directory=cwd,
        staging_commands=staging_cmds,
        branch_name=branch_name,
        commit_message=commit_message,
        push_command=push_cmd,
    )


def _prepare_pull_request(args: dict, tool_context: ToolContext) -> PreparePullRequestOutput | dict:
    input_data = PreparePullRequestInput(**(args or {}))

    plan = _build_plan(input_data, tool_context)
    if plan is None:
        return PreparePullRequestOutput(status="error", message="Failed to build PR plan", steps=[])

    # If approval not yet granted, return a single aggregated proposal
    if not tool_context.state.get("force_edit", False):
        steps: list[str] = []
        if plan.staging_commands:
            steps.append(f"Stage changes: {' && '.join(plan.staging_commands)}")
        steps.append(f"Create branch: git checkout -b {_shell_quote_single(plan.branch_name)}")
        # Commit message preview
        steps.append(
            f"Commit staged changes with Conventional Commit message: '{plan.commit_message}'"
        )
        if plan.push_command:
            steps.append(f"Push branch: {plan.push_command}")

        # Persist minimal execution plan to state
        tool_context.state["pending_pr_plan"] = {
            "working_directory": plan.working_directory,
            "staging_commands": plan.staging_commands,
            "branch_name": plan.branch_name,
            "commit_message": plan.commit_message,
            "push_command": plan.push_command,
            "presented": True,
        }

        # Add preflight verification block to details
        preflight_lines: list[str] = []
        code_branch, out_branch, _ = _run_git(
            "git rev-parse --abbrev-ref HEAD", tool_context, plan.working_directory
        )
        preflight_lines.append(
            f"Current branch: {out_branch.strip() if code_branch == 0 else 'unknown'}"
        )
        status_lines = _get_git_status_porcelain(tool_context, plan.working_directory)
        if status_lines:
            preflight_lines.append("Git status (porcelain):")
            preflight_lines.extend([f"  {ln}" for ln in status_lines])
        else:
            preflight_lines.append("Git status: unavailable or clean")
        staged_files = _get_staged_files(tool_context, plan.working_directory)
        if staged_files:
            preflight_lines.append("Staged files:")
            preflight_lines.extend([f"  {p}" for p in staged_files])
        else:
            preflight_lines.append("Staged files: none")
        has_origin = _detect_remote_origin(tool_context, plan.working_directory)
        preflight_lines.append(f"Remote 'origin' configured: {has_origin}")

        details = "\n".join([*(f"- {s}" for s in steps), "", "Preflight:", *preflight_lines])
        return {
            "status": "pending_approval",
            "type": "multi_step_plan",
            "title": "Prepare Pull Request Plan",
            "description": "Execute a streamlined PR prep: stage, branch, commit, (optional) push",
            "details": details,
            "message": (
                "I will perform these steps after your approval. This is a single confirmation "
                "for the whole plan."
            ),
        }

    # Approval granted: execute the plan
    prior_force = tool_context.state.get("force_edit", False)
    tool_context.state["force_edit"] = True
    try:
        exec_plan = tool_context.state.get("pending_pr_plan")
        if not exec_plan or not exec_plan.get("presented"):
            return {
                "status": "pending_approval",
                "type": "multi_step_plan",
                "title": "Prepare Pull Request Plan",
                "description": (
                    "Execute a streamlined PR prep: stage, branch, commit, (optional) push"
                ),
                "details": (
                    "Approval required. No previously presented plan found. "
                    "Please approve the plan first."
                ),
                "message": "Please confirm to proceed.",
            }
        cwd = exec_plan.get("working_directory")

        # Stage
        for cmd in exec_plan.get("staging_commands", []) or []:
            res = execute_shell_command({"command": cmd, "working_directory": cwd}, tool_context)
            logger.info(f"Staging command '{cmd}' exit={getattr(res, 'exit_code', 'unknown')}")

        # Create branch (approval bypassed via force_edit)
        branch_name = exec_plan.get("branch_name")
        if not branch_name:
            err_msg = "Branch name not found in execution plan. Aborting."
            logger.error(err_msg)
            return PreparePullRequestOutput(status="error", message=err_msg)

        code, out_b, err = _run_git(
            f"git checkout -b {_shell_quote_single(branch_name)}", tool_context, cwd
        )
        if code != 0:
            logger.warning("Branch creation failed or already exists: %s", err.strip())
        # Verify branch actually switched to approved branch name
        code_now, out_now, _ = _run_git("git rev-parse --abbrev-ref HEAD", tool_context, cwd)
        current_branch = out_now.strip() if code_now == 0 else "unknown"
        if current_branch != branch_name:
            err_msg = (
                f"Failed to switch to branch '{branch_name}' after creation attempt."
                f"Currently on branch '{current_branch}'. Aborting to prevent commit on wrong branch."  # noqa: E501
            )
            logger.error(err_msg)
            return PreparePullRequestOutput(
                status="error",
                message=err_msg,
                branch=current_branch,
            )

        # Commit
        # Ensure there are staged files before committing
        if _get_staged_files(tool_context, cwd):
            commit_msg = exec_plan.get("commit_message") or "chore: update changes"
            quoted_msg = _shell_quote_single(commit_msg)
            _run_git(f"git commit -m {quoted_msg}", tool_context, cwd)

        # Optional push
        pushed = None
        if exec_plan.get("push_command"):
            res = execute_shell_command(
                {"command": exec_plan["push_command"], "working_directory": cwd}, tool_context
            )
            pushed = bool(res.success)

        # Cleanup stored plan without relying on __delitem__ support
        try:
            tool_context.state["pending_pr_plan"] = None
        except Exception:
            pass

        steps_out = [
            *(["staged changes"] if plan.staging_commands else []),
            f"branch: {plan.branch_name}",
            "commit: completed"
            if _get_staged_files(tool_context, cwd) == []
            else "commit: attempted",
            f"push: {pushed}" if exec_plan.get("push_command") else "push: skipped",
        ]
        return PreparePullRequestOutput(
            status="success",
            message="PR preparation executed",
            steps=steps_out,
            branch=plan.branch_name,
            commit_message=plan.commit_message,
            pushed=pushed,
        )
    finally:
        tool_context.state["force_edit"] = prior_force


prepare_pull_request_tool = FunctionTool(func=_prepare_pull_request)


__all__ = ["prepare_pull_request_tool"]
