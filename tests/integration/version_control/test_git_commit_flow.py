from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from agents.software_engineer.tools.git_tools import (
    _commit_staged_changes,
    _generate_commit_message_tool,
    _get_staged_diff_tool,
)


@pytest.fixture
def mock_tool_context():
    class MockToolContext:
        def __init__(self):
            # No approval bypass by default to exercise pending_approval flow
            self.state = {}

    return MockToolContext()


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    assert _run(["git", "init"], repo).returncode == 0
    # Ensure identity for commit
    assert _run(["git", "config", "user.email", "you@example.com"], repo).returncode == 0
    assert _run(["git", "config", "user.name", "Your Name"], repo).returncode == 0


def test_git_commit_flow_pending_then_commit(tmp_path: Path, mock_tool_context):
    repo = tmp_path / "repo"
    _init_repo(repo)

    file_path = repo / "README.md"
    file_path.write_text("hello\n", encoding="utf-8")
    assert _run(["git", "add", "README.md"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    # Modify file and stage
    file_path.write_text("hello\nworld\n", encoding="utf-8")
    assert _run(["git", "add", "README.md"], repo).returncode == 0

    # Obtain staged diff via tool
    diff_res = _get_staged_diff_tool({"working_directory": str(repo)}, mock_tool_context)
    assert diff_res.success is True
    # Accept either traditional unified diff or porcelain formats;
    # must contain the new token 'world'
    assert "world" in diff_res.diff

    # Generate commit message suggestion
    gen_res = _generate_commit_message_tool(
        {"context_hint": "PROJ-123 improve readme", "working_directory": str(repo)},
        mock_tool_context,
    )
    assert gen_res.suggested_message.strip() != ""
    assert isinstance(gen_res.branch, str)

    # First call should request approval
    first = _commit_staged_changes({"working_directory": str(repo)}, mock_tool_context)
    assert isinstance(first, dict)
    assert first.get("status") == "pending_approval"
    assert "Proposed commit message" in (first.get("message") or "")

    # Simulate approval by setting force flag and rerunning
    mock_tool_context.state["force_edit"] = True
    try:
        second = _commit_staged_changes({"working_directory": str(repo)}, mock_tool_context)
    finally:
        mock_tool_context.state.pop("force_edit", None)

    # On approval, commit should be created
    assert getattr(second, "status", "") == "success"
    assert getattr(second, "commit_hash", None)
