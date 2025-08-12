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
    name_res = _suggest_branch_name_tool(
        {"intent": input_data.intent, "kind": input_data.kind, "working_directory": cwd},
        tool_context,
    )
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
        }

        details = "\n".join(f"- {s}" for s in steps)
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
        exec_plan = tool_context.state.get("pending_pr_plan") or {
            "working_directory": plan.working_directory,
            "staging_commands": plan.staging_commands,
            "branch_name": plan.branch_name,
            "commit_message": plan.commit_message,
            "push_command": plan.push_command,
        }
        cwd = exec_plan.get("working_directory")

        # Stage
        for cmd in exec_plan.get("staging_commands", []) or []:
            execute_shell_command({"command": cmd, "working_directory": cwd}, tool_context)

        # Create branch (approval bypassed via force_edit)
        code, _out, err = _run_git(
            f"git checkout -b {_shell_quote_single(exec_plan['branch_name'])}", tool_context, cwd
        )
        if code != 0:
            logger.warning("Branch creation failed or already exists: %s", err.strip())

        # Commit
        # Ensure there are staged files before committing
        if _get_staged_files(tool_context, cwd):
            quoted_msg = _shell_quote_single(exec_plan["commit_message"])  # type: ignore[index]
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
