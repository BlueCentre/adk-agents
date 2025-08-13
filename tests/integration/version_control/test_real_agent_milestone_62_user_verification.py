"""Real integration tests for Milestone 6.2 user verification steps.

These tests exercise the enhanced software engineer agent end-to-end using
natural language prompts. They replicate the "User Verification Steps" from
Milestone 6.2 in `PLAN_AGENT_FEATURES.md`:

1. Modify several files (feature + bug fix) without staging, then ask the agent
   for staging help. Expect logical grouping suggestions (e.g., git add groups).
2. Ask for branching guidance for a new authentication feature. Expect a
   Conventional Commit-style branch suggestion (e.g., feature/<slug>) and a safe
   creation flow.
3. Simulate a merge conflict and ask for guidance. Expect conflict detection and
   actionable guidance.

Current agent behavior does not satisfy these end-to-end flows via natural
language, so these tests are expected to fail until the implementation is
completed.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
import pytest


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # Isolate Git environment so commits operate on the temp repo only
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


def _gather_agent_text_results(result_generator) -> str:
    """Collect text parts from an async agent result generator into a single string."""

    # This helper is awaited inside async tests
    async def _collect():
        texts: list[str] = []
        async for res in result_generator:
            try:
                # The ADK responses expose res.content.parts[0].text in tests elsewhere
                part_text = (
                    res.content.parts[0].text
                    if getattr(res, "content", None)
                    and getattr(res.content, "parts", None)
                    and len(res.content.parts) > 0
                    and getattr(res.content.parts[0], "text", None) is not None
                    else None
                )
                if isinstance(part_text, str):
                    texts.append(part_text)
            except Exception:
                # Ignore any partial or tool events that don't match the shape
                continue
        return " ".join(texts)

    return _collect()


def _stub_llm_generate_content(agent) -> None:
    """Replace the agent model's generate_content_async with a deterministic stub.

    This avoids external API calls while allowing the agent run loop to complete.
    The stub returns a minimal content structure without any tooling.
    """

    async def fake_generate_content_async(llm_request, stream=False):  # noqa: ARG001
        # Provide a minimal result object compatible with ADK expectations
        text = "Acknowledged. I'll take a look."

        class FakeLlmResponse:
            def __init__(self, text: str):
                self.partial = False
                self.content = SimpleNamespace(parts=[SimpleNamespace(text=text)])

            # Pydantic-like API used by ADK
            def model_dump(self, exclude_none: bool = True):  # noqa: ARG002
                return {
                    "partial": self.partial,
                    "content": {"parts": [{"text": text}]},
                }

        yield FakeLlmResponse(text)

    # Pydantic models may block attribute assignment; use object.__setattr__ like the codebase does
    object.__setattr__(agent.model, "generate_content_async", fake_generate_content_async)


@pytest.mark.integration
@pytest.mark.real_behavior
@pytest.mark.asyncio
async def test_m62_staging_group_suggestions_real_agent(tmp_path: Path):
    """Step 1-2: Ask the agent to help stage un-staged changes; expect grouped suggestions.

    Expected (when implemented): response should include logical groups and suggested commands
    like 'git add ...' grouped by top-level directories or related stems.
    """
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Seed baseline
    (repo / "agents").mkdir()
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    assert _run(["git", "add", "-A"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    # Modify multiple files without staging (feature + bug fix flavor)
    (repo / "agents" / "feature_impl.py").write_text("print('new feature')\n", encoding="utf-8")
    (repo / "src" / "buggy.py").write_text("raise Exception('bug')\n", encoding="utf-8")
    (repo / "tests" / "test_buggy.py").write_text(
        "def test_bug():\n    assert True\n", encoding="utf-8"
    )

    # Build real agent and stub its LLM to avoid network
    with patch(
        "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
        new_callable=AsyncMock,
    ) as mock_create_session:
        mock_mcp_session = AsyncMock()
        mock_mcp_session.list_tools.return_value = SimpleNamespace(tools=[])
        mock_create_session.return_value = mock_mcp_session

        from agents.software_engineer.enhanced_agent import (
            create_enhanced_software_engineer_agent,
        )

        agent = create_enhanced_software_engineer_agent()
        _stub_llm_generate_content(agent)

        test_session = Session(
            id="m62_staging",
            appName="test_app",
            userId="test_user",
            state={
                "require_edit_approval": True,
                "current_directory": str(repo),
            },
        )

        invocation_context = InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="invocation_m62_staging",
            agent=agent,
            session=test_session,
            run_config=RunConfig(),
        )

        # Natural language request per plan
        from google.genai import types

        invocation_context.user_content = types.Content(
            parts=[types.Part(text="Can you help me stage these changes?")]
        )

        response_text = await _gather_agent_text_results(agent.run_async(invocation_context))

        # Assert expected behavior: logical staging groups with suggested git add commands
        # This currently FAILS because the agent does not wire this end-to-end via NL prompts
        assert "git add" in response_text or "stage-" in response_text, (
            "Agent should suggest logical staging groups with git add commands"
        )


@pytest.mark.integration
@pytest.mark.real_behavior
@pytest.mark.asyncio
async def test_m62_branching_guidance_real_agent(tmp_path: Path):
    """Step 3: Ask the agent for branching guidance for a new authentication feature.

    Expected (when implemented): response should include a suggested branch name such as
    'feature/authentication-feature' and a safe creation flow (approval-gated message like
    'git checkout -b <branch>').
    """
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    assert _run(["git", "add", "README.md"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    with patch(
        "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
        new_callable=AsyncMock,
    ) as mock_create_session:
        mock_mcp_session = AsyncMock()
        mock_mcp_session.list_tools.return_value = SimpleNamespace(tools=[])
        mock_create_session.return_value = mock_mcp_session

        from agents.software_engineer.enhanced_agent import (
            create_enhanced_software_engineer_agent,
        )

        agent = create_enhanced_software_engineer_agent()
        _stub_llm_generate_content(agent)

        test_session = Session(
            id="m62_branch",
            appName="test_app",
            userId="test_user",
            state={
                "require_edit_approval": True,
                "current_directory": str(repo),
            },
        )

        invocation_context = InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="invocation_m62_branch",
            agent=agent,
            session=test_session,
            run_config=RunConfig(),
        )

        from google.genai import types

        invocation_context.user_content = types.Content(
            parts=[
                types.Part(
                    text=(
                        "I want to start working on a new authentication feature. "
                        "What's the best way to create a branch?"
                    )
                )
            ]
        )

        response_text = await _gather_agent_text_results(agent.run_async(invocation_context))

        # Expected indicators when implemented
        assert "feature/" in response_text and "git checkout -b" in response_text, (
            "Agent should suggest a 'feature/<slug>' name and safe creation flow"
        )


@pytest.mark.integration
@pytest.mark.real_behavior
@pytest.mark.asyncio
async def test_m62_merge_conflict_guidance_real_agent(tmp_path: Path):
    """Step 4: Simulate a merge conflict and ask for guidance.

    Expected (when implemented): response should detect conflicts and provide actionable steps
    to resolve (e.g., mention unmerged paths, suggest commands like git status, git mergetool,
    add, commit, etc.).
    """
    repo = tmp_path / "repo"
    _init_repo(repo)

    f = repo / "a.txt"
    f.write_text("one\n", encoding="utf-8")
    assert _run(["git", "add", "a.txt"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "init"], repo).returncode == 0

    # Create conflict via diverging branches
    assert _run(["git", "checkout", "-b", "branch1"], repo).returncode == 0
    f.write_text("branch1\n", encoding="utf-8")
    assert _run(["git", "commit", "-am", "b1"], repo).returncode == 0
    base_commit = _run(["git", "rev-list", "--max-parents=0", "HEAD"], repo).stdout.strip()
    assert base_commit
    assert _run(["git", "checkout", "-b", "branch2", base_commit], repo).returncode == 0
    f.write_text("branch2\n", encoding="utf-8")
    assert _run(["git", "commit", "-am", "b2"], repo).returncode == 0
    rc = _run(["git", "merge", "branch1"], repo)
    # On conflict, rc.returncode is non-zero; proceed regardless
    assert rc.returncode != 0 or "CONFLICT" in (rc.stderr + rc.stdout)

    with patch(
        "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
        new_callable=AsyncMock,
    ) as mock_create_session:
        mock_mcp_session = AsyncMock()
        mock_mcp_session.list_tools.return_value = SimpleNamespace(tools=[])
        mock_create_session.return_value = mock_mcp_session

        from agents.software_engineer.enhanced_agent import (
            create_enhanced_software_engineer_agent,
        )

        agent = create_enhanced_software_engineer_agent()
        _stub_llm_generate_content(agent)

        test_session = Session(
            id="m62_conflict",
            appName="test_app",
            userId="test_user",
            state={
                "require_edit_approval": True,
                "current_directory": str(repo),
            },
        )

        invocation_context = InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="invocation_m62_conflict",
            agent=agent,
            session=test_session,
            run_config=RunConfig(),
        )

        from google.genai import types

        invocation_context.user_content = types.Content(
            parts=[types.Part(text="What do I do now?")]
        )

        response_text = await _gather_agent_text_results(agent.run_async(invocation_context))

        # Expected indicators when implemented
        assert "conflict" in response_text.lower() and (
            "git status" in response_text or "resolve" in response_text.lower()
        ), "Agent should detect merge conflicts and provide actionable guidance"
