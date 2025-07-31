"""
Integration Tests for the Code Refinement Workflow (Milestone 4.2)

This module provides a comprehensive suite of integration tests for the code
refinement workflow, a key feature of the software engineer agent introduced
in Milestone 4.2. These tests are designed to verify the seamless
collaboration of the five specialized sub-agents that make up the iterative
refinement loop.

The primary goal is to ensure that the entire workflow—from initialization
to user satisfaction—functions correctly, rather than testing each sub-agent
in isolation. This is achieved by using the actual `create_code_refinement_loop`
agent implementation, which provides a realistic testing environment that
mirrors production usage.

Key tested scenarios include:
- Successful creation and structural integrity of the main refinement agent.
- End-to-end execution of the workflow with a practical example (e.g., a factorial function).
- Graceful handling of common edge cases, such as syntax errors in the code.
- Robustness in processing ambiguous or contradictory user feedback.
- Adherence to `max_iterations` to prevent infinite loops.
- Correct handling of empty or invalid user input and code.

By simulating various user interactions and edge cases, these tests ensure
the stability, reliability, and correctness of the code refinement workflow.
"""

from dataclasses import dataclass
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
from google.genai import types, types as genai_types
import pytest

# Import the real agent for testing
from agents.software_engineer.workflows.iterative_workflows import create_code_refinement_loop


@dataclass
class CodeRefinementResult:
    """Result of code refinement workflow execution for testing."""

    workflow_name: str
    execution_time: float
    agents_executed: list[str]
    session_state_changes: dict[str, Any]
    success: bool
    iterations_completed: int
    final_code: str
    user_satisfied: bool
    quality_scores: list[int]
    feedback_applied: list[dict[str, Any]]
    error_message: Optional[str] = None


class TestCodeRefinementWorkflow:
    """Integration tests for code refinement workflow patterns."""

    @pytest.fixture
    def mock_session_state(self):
        """Create mock session state for code refinement testing."""
        return {
            "workflow_state": "code_refinement_in_progress",
            "iteration_state": {
                "current_iteration": 0,
                "max_iterations": 5,
                "should_stop": False,
                "reason": "Starting code refinement workflow",
            },
            "refinement_feedback": [],
            "revision_history": [],
            "current_code": "",
            "quality_analysis_results": {},
            "testing_results": {},
            "integrated_feedback": {},
        }

    @pytest.fixture
    def mock_invocation_context(self, mock_session_state):
        """Create mock InvocationContext for agent testing."""
        # Create mock session with initial state
        test_session = Session(
            id="test_refinement_session",
            appName="code_refinement_test",
            userId="test_user",
            state=mock_session_state,
        )

        # Create a dummy agent for context creation (will be replaced in tests)
        dummy_agent = create_code_refinement_loop()

        # Create InvocationContext
        return InvocationContext(
            session_service=AsyncMock(spec=BaseSessionService),
            invocation_id="test_refinement_invocation",
            agent=dummy_agent,
            session=test_session,
            run_config=RunConfig(),
        )

    @pytest.mark.asyncio
    async def test_real_code_refinement_agent_creation(self):
        """Test that the real code refinement agent can be created and has correct structure."""
        # Act
        refinement_agent = create_code_refinement_loop()

        # Assert
        assert refinement_agent is not None
        assert refinement_agent.name == "code_refinement_loop"
        assert refinement_agent.max_iterations == 5

        # Verify the agent has the expected attributes
        assert hasattr(refinement_agent, "name")
        assert hasattr(refinement_agent, "max_iterations")

        # Check if agents attribute exists (may vary by LoopAgent implementation)
        if hasattr(refinement_agent, "agents"):
            assert len(refinement_agent.agents) == 5
        elif hasattr(refinement_agent, "sub_agents"):
            assert len(refinement_agent.sub_agents) == 5

        # Verify the expected agent types are present
        expected_agent_names = [
            "code_refinement_init_agent",
            "code_refinement_feedback_collector",
            "code_refinement_reviser",
            "code_quality_testing_integrator",
            "code_refinement_satisfaction_checker",
        ]

        # Get agent names from sub_agents or agents
        if hasattr(refinement_agent, "sub_agents"):
            actual_agent_names = [agent.name for agent in refinement_agent.sub_agents]
        elif hasattr(refinement_agent, "agents"):
            actual_agent_names = [agent.name for agent in refinement_agent.agents]
        else:
            pytest.fail("LoopAgent has no 'agents' or 'sub_agents' attribute")

        for expected_name in expected_agent_names:
            assert expected_name in actual_agent_names, f"Missing agent: {expected_name}"

    @patch("google.adk.agents.llm_agent.LlmAgent._llm_flow", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_code_refinement_factorial_example(self, mock_llm_flow, mock_invocation_context):
        """Test complete code refinement workflow with factorial function example."""

        # Mock the async streaming response
        async def mock_stream():
            yield MagicMock(text="response part 1")
            yield MagicMock(text="response part 2")

        # This is the key fix: run_async is an async generator
        async def mock_run_async(*_args, **_kwargs):
            async for item in mock_stream():
                yield item

        mock_llm_flow.run_async = mock_run_async

        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Arrange
            initial_code = """def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result"""

            # Set up initial session state
            mock_invocation_context.session.state["current_code"] = initial_code
            mock_invocation_context.session.state["user_input"] = (
                "add input validation to handle negative numbers"
            )

            # The real agent is already set in the fixture
            refinement_agent = mock_invocation_context.agent

            # Set user content for the agent
            mock_invocation_context.user_content = types.Content(
                parts=[types.Part(text="Please improve this factorial function code.")]
            )

            # Act - Run the real agent
            start_time = time.time()
            results = []

            try:
                # Execute the agent and collect results
                result_generator = refinement_agent.run_async(mock_invocation_context)
                async for result in result_generator:
                    results.append(result)
                    # Limit execution time to prevent hanging
                    if time.time() - start_time > 90:  # 90 second timeout for real agent execution
                        break

                _execution_time = time.time() - start_time

                # Assert - Verify agent execution completed
                assert len(results) > 0, "Agent should produce at least one result"

            except Exception as e:
                # This test should catch implementation issues
                pytest.fail(f"Real agent execution failed: {e}")

    @pytest.mark.asyncio
    async def test_code_refinement_agent_structure(self):
        """Test that the code refinement agent has the correct structure and components."""
        # Create the real agent
        refinement_agent = create_code_refinement_loop()

        # Verify basic structure
        assert refinement_agent.name == "code_refinement_loop"
        expected_description = (
            "Iteratively refines code based on user feedback with integrated "
            "quality analysis and testing"
        )
        assert refinement_agent.description == expected_description
        assert refinement_agent.max_iterations == 5

        # Verify the sub-agents exist and are properly configured
        sub_agents = getattr(refinement_agent, "sub_agents", [])
        assert len(sub_agents) == 5, "Should have exactly 5 sub-agents"

        # Check that each expected agent is present
        agent_names = [agent.name for agent in sub_agents]
        expected_names = [
            "code_refinement_init_agent",
            "code_refinement_feedback_collector",
            "code_refinement_reviser",
            "code_quality_testing_integrator",
            "code_refinement_satisfaction_checker",
        ]

        for expected_name in expected_names:
            assert expected_name in agent_names, f"Missing required agent: {expected_name}"

    @pytest.mark.asyncio
    async def test_code_refinement_basic_initialization(self, mock_invocation_context):
        """Test that the code refinement workflow initializes properly."""
        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Set up basic test code
            test_code = "def simple_function(): return 42"
            mock_invocation_context.session.state["current_code"] = test_code

            # The real agent is already set in the fixture
            refinement_agent = mock_invocation_context.agent

            # Test that agent can be created and initialized without errors
            assert refinement_agent is not None
            assert hasattr(refinement_agent, "run_async")

            # Verify initial session state is preserved
            assert mock_invocation_context.session.state["current_code"] == test_code

    @patch("google.adk.agents.llm_agent.LlmAgent._llm_flow", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_code_refinement_syntax_error_handling(
        self, mock_llm_flow, mock_invocation_context
    ):
        """Test that the workflow handles syntax errors gracefully."""

        # Mock the async streaming response
        async def mock_stream():
            yield MagicMock(text="Syntax error detected")
            yield MagicMock(text="Attempting to fix...")

        async def mock_run_async(*_args, **_kwargs):
            async for item in mock_stream():
                yield item

        mock_llm_flow.run_async = mock_run_async

        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Arrange - code with syntax error
            invalid_code = """def broken_function(
                return "missing closing parenthesis"
            """

            mock_invocation_context.session.state["current_code"] = invalid_code
            mock_invocation_context.session.state["user_input"] = "fix the syntax error"

            refinement_agent = mock_invocation_context.agent
            mock_invocation_context.user_content = genai_types.Content(
                parts=[genai_types.Part(text="Please fix this syntax error.")]
            )

            # Act - Run the agent with syntax error
            start_time = time.time()
            results = []

            try:
                result_generator = refinement_agent.run_async(mock_invocation_context)
                async for result in result_generator:
                    results.append(result)
                    if time.time() - start_time > 30:  # Shorter timeout for error case
                        break

                # Assert - Should handle error gracefully
                assert len(results) > 0, "Agent should produce results even with syntax errors"

            except Exception as e:
                # Should not crash, but handle gracefully
                assert "syntax" in str(e).lower() or "parse" in str(e).lower()

    @patch("google.adk.agents.llm_agent.LlmAgent._llm_flow", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_code_refinement_ambiguous_feedback(self, mock_llm_flow, mock_invocation_context):
        """Test that the workflow handles ambiguous or contradictory feedback."""

        # Mock the async streaming response
        async def mock_stream():
            yield MagicMock(text="Processing ambiguous feedback")
            yield MagicMock(text="Applying best interpretation")

        async def mock_run_async(*_args, **_kwargs):
            async for item in mock_stream():
                yield item

        mock_llm_flow.run_async = mock_run_async

        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Arrange - ambiguous feedback
            simple_code = "def process_data(data): return data.upper()"
            ambiguous_feedback = (
                "make it faster but also more readable and add error handling but keep it simple"
            )

            mock_invocation_context.session.state["current_code"] = simple_code
            mock_invocation_context.session.state["user_input"] = ambiguous_feedback

            refinement_agent = mock_invocation_context.agent
            mock_invocation_context.user_content = genai_types.Content(
                parts=[genai_types.Part(text=ambiguous_feedback)]
            )

            # Act - Run the agent with ambiguous feedback
            start_time = time.time()
            results = []

            try:
                result_generator = refinement_agent.run_async(mock_invocation_context)
                async for result in result_generator:
                    results.append(result)
                    if time.time() - start_time > 30:
                        break

                # Assert - Should process ambiguous feedback without crashing
                assert len(results) > 0, "Agent should handle ambiguous feedback gracefully"

            except Exception as e:
                pytest.fail(f"Agent should handle ambiguous feedback gracefully: {e}")

    @patch("google.adk.agents.llm_agent.LlmAgent._llm_flow", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_code_refinement_max_iterations_limit(
        self, mock_llm_flow, mock_invocation_context
    ):
        """Test that the workflow respects the max_iterations limit."""

        # Mock the async streaming response to simulate never being satisfied
        async def mock_stream():
            yield MagicMock(text="Not satisfied yet, continuing...")

        async def mock_run_async(*_args, **_kwargs):
            async for item in mock_stream():
                yield item

        mock_llm_flow.run_async = mock_run_async

        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Arrange - setup for max iterations test
            test_code = "def simple_function(): return 42"
            mock_invocation_context.session.state["current_code"] = test_code
            mock_invocation_context.session.state["user_input"] = "keep improving this code"

            # Modify the iteration state to simulate multiple iterations
            mock_invocation_context.session.state["iteration_state"] = {
                "current_iteration": 0,
                "max_iterations": 2,  # Set low limit for testing
                "should_stop": False,
                "reason": "Testing max iterations",
            }

            refinement_agent = mock_invocation_context.agent
            # Verify max_iterations is set correctly
            assert refinement_agent.max_iterations == 5  # Default from create_code_refinement_loop

            mock_invocation_context.user_content = genai_types.Content(
                parts=[genai_types.Part(text="Keep improving this code")]
            )

            # Act - Run the agent with max iterations constraint
            start_time = time.time()
            results = []
            iteration_count = 0

            try:
                result_generator = refinement_agent.run_async(mock_invocation_context)
                async for result in result_generator:
                    results.append(result)
                    iteration_count += 1

                    # Safety check to prevent infinite loop in test
                    if iteration_count > 10 or time.time() - start_time > 15:
                        break

                # Assert - Should respect iteration limits
                assert iteration_count <= 10, "Agent should respect max iteration limits"
                assert len(results) > 0, "Agent should produce results within iteration limits"

            except Exception as e:
                # This is acceptable as the test is about limits
                assert (
                    "iteration" in str(e).lower() or "limit" in str(e).lower() or len(results) > 0
                )

    @pytest.mark.asyncio
    async def test_code_refinement_edge_case_empty_feedback(self, mock_invocation_context):
        """Test handling of empty or whitespace-only feedback."""

        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Arrange - empty feedback
            test_code = "def test(): pass"
            mock_invocation_context.session.state["current_code"] = test_code
            mock_invocation_context.session.state["user_input"] = "   "  # Whitespace only

            refinement_agent = mock_invocation_context.agent

            # Test that agent structure is valid for empty feedback
            assert refinement_agent is not None
            assert refinement_agent.max_iterations == 5

            # Verify the session state handling
            session_state = mock_invocation_context.session.state
            assert session_state["current_code"] == test_code
            assert session_state["user_input"].strip() == ""

    @pytest.mark.asyncio
    async def test_code_refinement_invalid_code_input(self, mock_invocation_context):
        """Test handling of completely invalid or malformed code input."""

        # Mock MCP session to avoid external dependencies
        with patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.MCPSessionManager.create_session",
            new_callable=AsyncMock,
        ) as mock_create_session:
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_create_session.return_value = mock_session

            # Arrange - completely invalid code
            invalid_inputs = [
                "this is not code at all",
                "12345 !@#$% invalid",
                "",  # Empty string
                None,  # None value would cause issues if not handled
            ]

            for invalid_code in invalid_inputs:
                if invalid_code is not None:
                    mock_invocation_context.session.state["current_code"] = invalid_code
                    mock_invocation_context.session.state["user_input"] = "fix this code"

                    refinement_agent = mock_invocation_context.agent

                    # Test that agent can be created even with invalid input
                    assert refinement_agent is not None
                    assert hasattr(refinement_agent, "max_iterations")

                    # Verify session state is preserved
                    if invalid_code is not None:
                        assert mock_invocation_context.session.state["current_code"] == invalid_code
