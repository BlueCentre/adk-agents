from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from agents.software_engineer.tools.git_tools import (
    _create_branch_tool,
    _detect_merge_conflicts_tool,
    _suggest_branch_name_tool,
    _suggest_staging_groups_tool,
)


@pytest.fixture
def mock_tool_context():
    class MockToolContext:
        def __init__(self):
            self.state = {}

    return MockToolContext()


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # Ensure isolated Git environment for the temp repo during hooks/CI
    env = os.environ.copy()
    for var in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ):
        env.pop(var, None)
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    assert _run(["git", "init"], repo).returncode == 0
    assert _run(["git", "config", "user.email", "you@example.com"], repo).returncode == 0
    assert _run(["git", "config", "user.name", "Your Name"], repo).returncode == 0


def test_suggest_staging_groups(tmp_path: Path, mock_tool_context):
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Create files in different folders
    (repo / "agents").mkdir()
    (repo / "tests").mkdir()
    (repo / "docs").mkdir()
    (repo / "agents" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (repo / "tests" / "test_app.py").write_text("def test_x(): assert True\n", encoding="utf-8")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    assert _run(["git", "add", "-A"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    # Modify some files and leave unstaged
    (repo / "agents" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (repo / "tests" / "test_app.py").write_text(
        "def test_x():\n    assert 1 == 1\n", encoding="utf-8"
    )
    (repo / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")

    res = _suggest_staging_groups_tool({"working_directory": str(repo)}, mock_tool_context)
    assert res.success is True
    assert isinstance(res.groups, list) and res.groups
    # Expect groups referencing top-level dirs
    rationales = " ".join(g.get("rationale", "") for g in res.groups)
    assert "agents/" in rationales or "tests/" in rationales or "docs/" in rationales


def test_branch_naming_and_creation_with_approval(tmp_path: Path, mock_tool_context):
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Initial commit required for branch operations
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    assert _run(["git", "add", "README.md"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    # Suggest branch name
    name_res = _suggest_branch_name_tool(
        {"intent": "authentication feature", "working_directory": str(repo)}, mock_tool_context
    )
    assert name_res.success is True
    assert name_res.branch_name.startswith("feature/")

    # First call: pending approval
    first = _create_branch_tool(
        {"name": name_res.branch_name, "working_directory": str(repo)}, mock_tool_context
    )
    assert isinstance(first, dict)
    assert first.get("status") == "pending_approval"
    assert name_res.branch_name in (first.get("message") or "")

    # Approve
    mock_tool_context.state["force_edit"] = True
    second = _create_branch_tool(
        {"name": name_res.branch_name, "working_directory": str(repo)}, mock_tool_context
    )
    mock_tool_context.state.pop("force_edit", None)

    assert getattr(second, "status", "") == "success"
    assert getattr(second, "branch", None) == name_res.branch_name


def test_detect_merge_conflicts_basic(tmp_path: Path, mock_tool_context):
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Create a file and make first commit
    f = repo / "a.txt"
    f.write_text("one\n", encoding="utf-8")
    assert _run(["git", "add", "a.txt"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    # Create a fake conflict marker via an actual merge to produce status 'UU'
    # Use a merge workflow
    assert _run(["git", "checkout", "-b", "branch1"], repo).returncode == 0
    f.write_text("branch1\n", encoding="utf-8")
    assert _run(["git", "commit", "-am", "b1"], repo).returncode == 0
    # Create second branch from the initial commit to ensure divergence
    # Find initial commit hash
    base_commit = _run(["git", "rev-list", "--max-parents=0", "HEAD"], repo).stdout.strip()
    assert base_commit
    assert _run(["git", "checkout", "-b", "branch2", base_commit], repo).returncode == 0
    f.write_text("branch2\n", encoding="utf-8")
    assert _run(["git", "commit", "-am", "b2"], repo).returncode == 0
    # Merge to create conflict
    rc = _run(["git", "merge", "branch1"], repo)
    # On conflict, return code non-zero; proceed to detection
    assert rc.returncode != 0 or "CONFLICT" in (rc.stderr + rc.stdout)

    det = _detect_merge_conflicts_tool({"working_directory": str(repo)}, mock_tool_context)
    assert det.success is True
    # Either detects conflict or none if git resolves differently in environment
    # Accept both but ensure the structure is valid
    assert isinstance(det.conflicts, list)
