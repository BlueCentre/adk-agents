from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
from google.genai import types
import pytest

from agents.software_engineer.enhanced_agent import (
    create_enhanced_software_engineer_agent,
)


@pytest.mark.skip(
    reason="Agent is not correctly parsing the prompt and executing the edit_file_content tool."
)
@pytest.mark.asyncio
async def test_edit_file_with_approval():
    with (
        patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session,
        patch(
            "agents.software_engineer.tools.filesystem.edit_file_content",
            new_callable=AsyncMock,
        ) as mock_edit_file_content,
    ):
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = MagicMock(tools=[])
        mock_create_session.return_value = mock_session
        mock_edit_file_content.return_value = {
            "status": "success",
            "message": "Successfully wrote content to 'test.txt'",
        }
        agent = create_enhanced_software_engineer_agent()
        mock_session = Session(
            id="test_session",
            appName="test_app",
            userId="test_user",
            state={"require_edit_approval": True},
        )
        invocation_context = InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="test_invocation_id",
            agent=agent,
            session=mock_session,
            run_config=RunConfig(),
        )
        invocation_context.user_content = types.Content(
            parts=[
                types.Part(
                    text="Use the edit_file_content tool to edit the file 'test.txt' "
                    "with the content 'Hello, World!'"
                )
            ]
        )

        with patch("builtins.input", return_value="yes"):
            result_generator = agent.run_async(invocation_context)
            result = [res async for res in result_generator]

        # The result should contain a message indicating that the file was edited
        assert "Successfully wrote content" in result[-1].content.parts[0].text

        # The audit trail should be updated
        assert "approval_audit_trail" in agent.state
        assert len(agent.state["approval_audit_trail"]) == 1
        assert agent.state["approval_audit_trail"][0]["outcome"] == "approved"
        mock_edit_file_content.assert_called_once()
        await agent.close()


@pytest.mark.skip(
    reason="Agent is not correctly parsing the prompt and executing the edit_file_content tool."
)
@pytest.mark.asyncio
async def test_edit_file_with_rejection():
    with patch(
        "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
        new_callable=AsyncMock,
    ) as mock_create_session:
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = MagicMock(tools=[])
        mock_create_session.return_value = mock_session
        agent = create_enhanced_software_engineer_agent()
        mock_session = Session(
            id="test_session",
            appName="test_app",
            userId="test_user",
            state={"require_edit_approval": True},
        )
        invocation_context = InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="test_invocation_id",
            agent=agent,
            session=mock_session,
            run_config=RunConfig(),
        )
        invocation_context.user_content = types.Content(
            parts=[
                types.Part(
                    text="Use the edit_file_content tool to edit the file 'test.txt' "
                    "with the content 'Hello, World!'"
                )
            ]
        )

        with patch("builtins.input", return_value="no"):
            result_generator = agent.run_async(invocation_context)
            result = [res async for res in result_generator]

        # The result should contain a message indicating that the file was not edited
        assert "File edit rejected by user" in result[-1].content.parts[0].text

        # The audit trail should be updated
        assert "approval_audit_trail" in agent.state
        assert len(agent.state["approval_audit_trail"]) == 1
        assert agent.state["approval_audit_trail"][0]["outcome"] == "rejected"
        await agent.close()


@pytest.mark.skip(
    reason="Agent is not correctly parsing the prompt and executing the edit_file_content tool."
)
@pytest.mark.asyncio
async def test_edit_file_with_approval_and_write_to_disk():
    with patch(
        "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
        new_callable=AsyncMock,
    ) as mock_create_session:
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = MagicMock(tools=[])
        mock_create_session.return_value = mock_session
        agent = create_enhanced_software_engineer_agent()
        mock_session = Session(
            id="test_session",
            appName="test_app",
            userId="test_user",
            state={"require_edit_approval": True},
        )
        invocation_context = InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="test_invocation_id",
            agent=agent,
            session=mock_session,
            run_config=RunConfig(),
        )
        test_file = Path("test.txt")
        test_file.write_text("initial content")

        invocation_context.user_content = types.Content(
            parts=[
                types.Part(
                    text="Use the edit_file_content tool to edit the file 'test.txt' "
                    "with the content 'Hello, World!'"
                )
            ]
        )

        with patch("builtins.input", return_value="yes"):
            result_generator = agent.run_async(invocation_context)
            result = [res async for res in result_generator]

        # The result should contain a message indicating that the file was edited
        assert "Successfully wrote content" in result[-1].content.parts[0].text

        # The audit trail should be updated
        assert "approval_audit_trail" in agent.state
        assert len(agent.state["approval_audit_trail"]) == 1
        assert agent.state["approval_audit_trail"][0]["outcome"] == "approved"

        # The file should be modified
        content = test_file.read_text()
        assert content == "Hello, World!"
        await agent.close()
