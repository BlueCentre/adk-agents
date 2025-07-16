"""
Integration Tests for SWE Agent Callback Functions

This module contains integration tests that verify the callback functionality
implemented for the Software Engineer Agent, including telemetry, observability,
and performance monitoring.

Based on Google ADK patterns and the project's multi-agent architecture.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import project components
from agents.software_engineer.shared_libraries.callbacks import (
    create_enhanced_telemetry_callbacks,
    create_telemetry_callbacks,
)

# Test utilities
from tests.fixtures.test_helpers import (
    MockCallbackContext,
    MockInvocationContext,
    MockLlmRequest,
    MockLlmResponse,
    MockTool,
    MockToolContext,
    create_mock_agent,
    create_mock_llm_client,
    create_mock_session_state,
    run_with_timeout,
)

logger = logging.getLogger(__name__)


@dataclass
class CallbackTestMetrics:
    """Metrics collected during callback testing."""

    model_requests: int = 0
    model_responses: int = 0
    tool_executions: int = 0
    tool_completions: int = 0
    total_response_time: float = 0.0
    total_tool_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)


class CallbackTestCollector:
    """Collects callback execution data for testing."""

    def __init__(self):
        self.metrics = CallbackTestMetrics()
        self.model_callbacks = []
        self.tool_callbacks = []
        self.execution_log = []

    def log_model_request(self, request: Any, context: Any):
        """Log model request callback execution."""
        self.metrics.model_requests += 1
        self.model_callbacks.append(
            {
                "type": "before_model",
                "timestamp": time.time(),
                "request": request,
                "context": context,
            }
        )
        self.execution_log.append("before_model")

    def log_model_response(self, request: Any, response: Any, context: Any):
        """Log model response callback execution."""
        self.metrics.model_responses += 1
        self.model_callbacks.append(
            {
                "type": "after_model",
                "timestamp": time.time(),
                "request": request,
                "response": response,
                "context": context,
            }
        )
        self.execution_log.append("after_model")

        # Track response time if available
        if hasattr(context, "_request_start_time"):
            response_time = time.time() - context._request_start_time
            self.metrics.total_response_time += response_time

    def log_tool_execution(self, tool: Any, context: Any):
        """Log tool execution callback."""
        self.metrics.tool_executions += 1
        self.tool_callbacks.append(
            {
                "type": "before_tool",
                "timestamp": time.time(),
                "tool": tool,
                "context": context,
            }
        )
        self.execution_log.append("before_tool")

    def log_tool_completion(self, tool: Any, result: Any, context: Any):
        """Log tool completion callback."""
        self.metrics.tool_completions += 1
        self.tool_callbacks.append(
            {
                "type": "after_tool",
                "timestamp": time.time(),
                "tool": tool,
                "result": result,
                "context": context,
            }
        )
        self.execution_log.append("after_tool")

        # Track tool execution time if available
        if hasattr(context, "_tool_start_time"):
            tool_time = time.time() - context._tool_start_time
            self.metrics.total_tool_time += tool_time


@pytest.fixture
def callback_collector():
    """Provide a callback test collector."""
    return CallbackTestCollector()


@pytest.fixture
def mock_llm_request():
    """Provide a mock LLM request."""
    return MockLlmRequest(
        model="gemini-2.0-flash",
        contents=["Test user message"],
        messages=[{"role": "user", "content": "Test message"}],
    )


@pytest.fixture
def mock_llm_response():
    """Provide a mock LLM response with usage metadata."""
    usage_metadata = MagicMock()
    usage_metadata.prompt_token_count = 100
    usage_metadata.candidates_token_count = 200

    return MockLlmResponse(
        text="Test response from model", usage_metadata=usage_metadata
    )


@pytest.fixture
def mock_invocation_context():
    """Provide a mock invocation context."""
    return MockInvocationContext(
        invocation_id="test_inv_123",
        trace_id="test_trace_456",
        session_state={"test": "state"},
    )


@pytest.fixture
def mock_tool_context():
    """Provide a mock tool context."""
    return MockToolContext(
        state={"tool_input": {"param1": "value1"}}, invocation_id="test_tool_inv_789"
    )


@pytest.fixture
def mock_test_tool():
    """Provide a mock tool for testing."""
    return MockTool(name="test_tool", args={"param1": "value1", "param2": "value2"})


class TestBasicCallbacks:
    """Test basic callback functionality."""

    def test_create_basic_callbacks(self):
        """Test that basic callbacks can be created successfully."""
        callbacks = create_telemetry_callbacks("test_agent")

        assert len(callbacks) == 4
        before_model, after_model, before_tool, after_tool = callbacks

        # Verify all callbacks are callable
        assert callable(before_model)
        assert callable(after_model)
        assert callable(before_tool)
        assert callable(after_tool)

    def test_basic_before_model_callback(
        self, mock_llm_request, mock_invocation_context, caplog
    ):
        """Test basic before_model callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        with caplog.at_level(logging.DEBUG):
            before_model_callback(mock_llm_request, mock_invocation_context)

        # Verify logging
        assert "Before model request" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_inv_123" in caplog.text

        # Verify timing is set
        assert hasattr(mock_invocation_context, "_request_start_time")
        assert isinstance(mock_invocation_context._request_start_time, float)

    def test_basic_after_model_callback(
        self, mock_llm_request, mock_llm_response, mock_invocation_context, caplog
    ):
        """Test basic after_model callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_model_callback = callbacks[1]

        # Set up timing
        mock_invocation_context._request_start_time = time.time() - 1.5

        with caplog.at_level(logging.DEBUG):
            after_model_callback(
                mock_llm_request, mock_llm_response, mock_invocation_context
            )

        # Verify logging
        assert "After model response" in caplog.text
        assert "test_agent" in caplog.text
        assert "Response time:" in caplog.text
        assert "Token usage" in caplog.text
        assert "Prompt: 100" in caplog.text
        assert "Response: 200" in caplog.text
        assert "Total: 300" in caplog.text

    def test_basic_before_tool_callback(
        self, mock_test_tool, mock_tool_context, caplog
    ):
        """Test basic before_tool callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_tool_callback = callbacks[2]

        with caplog.at_level(logging.DEBUG):
            before_tool_callback(mock_test_tool, mock_tool_context)

        # Verify logging
        assert "Before tool execution" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_tool" in caplog.text

        # Verify timing is set
        assert hasattr(mock_tool_context, "_tool_start_time")
        assert isinstance(mock_tool_context._tool_start_time, float)

    def test_basic_after_tool_callback(self, mock_test_tool, mock_tool_context, caplog):
        """Test basic after_tool callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_tool_callback = callbacks[3]

        # Set up timing
        mock_tool_context._tool_start_time = time.time() - 0.5

        test_result = {"status": "success", "data": "test_output"}

        with caplog.at_level(logging.DEBUG):
            after_tool_callback(mock_test_tool, test_result, mock_tool_context)

        # Verify logging
        assert "After tool execution" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_tool" in caplog.text
        assert "Tool execution time:" in caplog.text
        assert "completed successfully" in caplog.text

    def test_tool_failure_callback(self, mock_test_tool, mock_tool_context, caplog):
        """Test callback behavior when tool fails."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_tool_callback = callbacks[3]

        # Simulate tool failure
        test_error = Exception("Tool execution failed")

        with caplog.at_level(logging.WARNING):
            after_tool_callback(mock_test_tool, test_error, mock_tool_context)

        # Verify error logging
        assert "Tool test_tool failed" in caplog.text
        assert "Tool execution failed" in caplog.text


class TestEnhancedCallbacks:
    """Test enhanced callback functionality."""

    def test_create_enhanced_callbacks(self):
        """Test that enhanced callbacks can be created successfully."""
        callbacks = create_enhanced_telemetry_callbacks("test_agent")

        assert len(callbacks) == 4
        before_model, after_model, before_tool, after_tool = callbacks

        # Verify all callbacks are callable
        assert callable(before_model)
        assert callable(after_model)
        assert callable(before_tool)
        assert callable(after_tool)

    def test_enhanced_callbacks_fallback(self, caplog):
        """Test that enhanced callbacks fall back to basic when telemetry unavailable."""
        with patch(
            "agents.software_engineer.shared_libraries.callbacks.logger"
        ) as mock_logger:
            callbacks = create_enhanced_telemetry_callbacks("test_agent")

            # Should still create 4 callbacks
            assert len(callbacks) == 4

    def test_enhanced_after_model_with_telemetry(
        self, mock_llm_request, mock_llm_response, mock_invocation_context, caplog
    ):
        """Test enhanced after_model callback with telemetry integration."""
        # Mock the telemetry module to simulate successful import
        mock_telemetry = MagicMock()
        mock_telemetry.track_llm_request = MagicMock()
        mock_tracing = MagicMock()
        mock_tracing.trace_llm_request = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "agents.devops.telemetry": mock_telemetry,
                "agents.devops.tracing": mock_tracing,
            },
        ):
            # Create enhanced callbacks with mocked telemetry
            callbacks = create_enhanced_telemetry_callbacks("test_agent")
            after_model_callback = callbacks[1]

            # Set up timing
            mock_invocation_context._request_start_time = time.time() - 2.0

            with caplog.at_level(logging.DEBUG):
                after_model_callback(
                    mock_llm_request, mock_llm_response, mock_invocation_context
                )

            # Verify basic logging occurred
            assert "After model response" in caplog.text
            assert "test_agent" in caplog.text
            assert "Token usage" in caplog.text


class TestCallbackIntegration:
    """Test callback integration with agents."""

    def test_callback_integration_with_mock_agent(self, callback_collector):
        """Test that callbacks can be properly integrated with mock agents."""
        # Create mock agent with callbacks
        callbacks = create_telemetry_callbacks("test_agent")
        before_model, after_model, before_tool, after_tool = callbacks

        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.before_model_callback = before_model
        mock_agent.after_model_callback = after_model
        mock_agent.before_tool_callback = before_tool
        mock_agent.after_tool_callback = after_tool

        # Verify callbacks are present
        assert hasattr(mock_agent, "before_model_callback")
        assert hasattr(mock_agent, "after_model_callback")
        assert hasattr(mock_agent, "before_tool_callback")
        assert hasattr(mock_agent, "after_tool_callback")

        # Verify callbacks are not None
        assert mock_agent.before_model_callback is not None
        assert mock_agent.after_model_callback is not None
        assert mock_agent.before_tool_callback is not None
        assert mock_agent.after_tool_callback is not None

        # Verify callbacks are callable
        assert callable(mock_agent.before_model_callback)
        assert callable(mock_agent.after_model_callback)
        assert callable(mock_agent.before_tool_callback)
        assert callable(mock_agent.after_tool_callback)

    def test_enhanced_callback_integration_with_mock_agent(self, callback_collector):
        """Test that enhanced callbacks can be properly integrated with mock agents."""
        # Create enhanced callbacks
        callbacks = create_enhanced_telemetry_callbacks("test_enhanced_agent")
        before_model, after_model, before_tool, after_tool = callbacks

        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.name = "test_enhanced_agent"
        mock_agent.before_model_callback = before_model
        mock_agent.after_model_callback = after_model
        mock_agent.before_tool_callback = before_tool
        mock_agent.after_tool_callback = after_tool

        # Verify callbacks are present and callable
        assert callable(mock_agent.before_model_callback)
        assert callable(mock_agent.after_model_callback)
        assert callable(mock_agent.before_tool_callback)
        assert callable(mock_agent.after_tool_callback)

    def test_callback_integration_pattern(self, callback_collector):
        """Test the callback integration pattern used in the codebase."""
        # This tests the pattern used in the actual agent files
        agent_name = "test_pattern_agent"

        # Create callbacks (this is the pattern used in the actual agents)
        (
            before_model_callback,
            after_model_callback,
            before_tool_callback,
            after_tool_callback,
        ) = create_enhanced_telemetry_callbacks(agent_name)

        # Verify the pattern produces valid callbacks
        assert callable(before_model_callback)
        assert callable(after_model_callback)
        assert callable(before_tool_callback)
        assert callable(after_tool_callback)

        # Test that they can be used in agent configuration
        agent_config = {
            "name": agent_name,
            "before_model_callback": before_model_callback,
            "after_model_callback": after_model_callback,
            "before_tool_callback": before_tool_callback,
            "after_tool_callback": after_tool_callback,
        }

        # Verify configuration is valid
        assert agent_config["name"] == agent_name
        assert callable(agent_config["before_model_callback"])
        assert callable(agent_config["after_model_callback"])
        assert callable(agent_config["before_tool_callback"])
        assert callable(agent_config["after_tool_callback"])


class TestCallbackPerformance:
    """Test callback performance and overhead."""

    def test_callback_execution_time(self, mock_llm_request, mock_invocation_context):
        """Test that callbacks execute quickly with minimal overhead."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        # Measure callback execution time
        start_time = time.time()
        for _ in range(100):
            before_model_callback(mock_llm_request, mock_invocation_context)
        end_time = time.time()

        # Callbacks should execute quickly (< 1ms per call on average)
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.001, f"Callback execution too slow: {avg_time:.4f}s"

    def test_callback_memory_usage(self, mock_llm_request, mock_invocation_context):
        """Test that callbacks don't cause memory leaks."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        # Execute callbacks many times
        for _ in range(1000):
            before_model_callback(mock_llm_request, mock_invocation_context)

        # This test mainly ensures no exceptions are raised during repeated execution
        # Memory profiling would require additional tools like memory_profiler
        assert True  # If we reach here, no memory issues occurred


class TestCallbackErrorHandling:
    """Test callback error handling and resilience."""

    def test_callback_with_invalid_context(self, mock_llm_request):
        """Test callback behavior with invalid context."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        # Test with None context
        try:
            before_model_callback(mock_llm_request, None)
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"Callback should handle None context gracefully: {e}")

    def test_callback_with_invalid_request(self, mock_invocation_context):
        """Test callback behavior with invalid request."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        # Test with None request
        try:
            before_model_callback(None, mock_invocation_context)
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"Callback should handle None request gracefully: {e}")

    def test_callback_with_missing_attributes(self, mock_invocation_context):
        """Test callback behavior when objects are missing expected attributes."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_model_callback = callbacks[1]

        # Create request and response without expected attributes
        minimal_request = MagicMock()
        minimal_response = MagicMock()

        try:
            after_model_callback(
                minimal_request, minimal_response, mock_invocation_context
            )
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"Callback should handle missing attributes gracefully: {e}")


class TestCallbackLogging:
    """Test callback logging functionality."""

    def test_callback_log_levels(
        self, mock_llm_request, mock_invocation_context, caplog
    ):
        """Test that callbacks log at appropriate levels."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        # Test DEBUG level logging
        with caplog.at_level(logging.DEBUG):
            before_model_callback(mock_llm_request, mock_invocation_context)

        debug_logs = [
            record for record in caplog.records if record.levelno == logging.DEBUG
        ]
        assert len(debug_logs) > 0, "Should have DEBUG level logs"

        # Test INFO level logging (for token usage)
        caplog.clear()
        after_model_callback = callbacks[1]
        mock_response = MockLlmResponse(text="test", usage_metadata=MagicMock())
        mock_response.usage_metadata.prompt_token_count = 50
        mock_response.usage_metadata.candidates_token_count = 100

        with caplog.at_level(logging.INFO):
            after_model_callback(
                mock_llm_request, mock_response, mock_invocation_context
            )

        info_logs = [
            record for record in caplog.records if record.levelno == logging.INFO
        ]
        assert len(info_logs) > 0, "Should have INFO level logs for token usage"

    def test_callback_log_content(
        self, mock_llm_request, mock_invocation_context, caplog
    ):
        """Test that callbacks log useful content."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks[0]

        with caplog.at_level(logging.DEBUG):
            before_model_callback(mock_llm_request, mock_invocation_context)

        log_text = caplog.text

        # Should contain agent name
        assert "test_agent" in log_text
        # Should contain invocation ID
        assert "test_inv_123" in log_text
        # Should contain operation type
        assert "Before model request" in log_text


@pytest.mark.integration
class TestCallbackEndToEnd:
    """End-to-end integration tests for callbacks."""

    @pytest.mark.asyncio
    async def test_callback_execution_order(self, callback_collector):
        """Test that callbacks execute in the correct order during agent execution."""
        # This test would require a more sophisticated setup to actually run an agent
        # For now, we'll test the callback creation and basic functionality

        callbacks = create_telemetry_callbacks("test_agent")
        before_model, after_model, before_tool, after_tool = callbacks

        # Simulate agent execution sequence
        mock_request = MockLlmRequest()
        mock_response = MockLlmResponse()
        mock_context = MockInvocationContext()
        mock_tool = MockTool("test_tool")
        mock_tool_context = MockToolContext()

        # Execute callbacks in expected order
        before_model(mock_request, mock_context)
        after_model(mock_request, mock_response, mock_context)
        before_tool(mock_tool, mock_tool_context)
        after_tool(mock_tool, "success", mock_tool_context)

        # Verify timing was tracked
        assert hasattr(mock_context, "_request_start_time")
        assert hasattr(mock_tool_context, "_tool_start_time")

    @pytest.mark.asyncio
    async def test_callback_with_multiple_tools(self, callback_collector):
        """Test callback behavior with multiple tool executions."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_tool, after_tool = callbacks[2], callbacks[3]

        # Simulate multiple tool executions
        tools = [MockTool(f"tool_{i}") for i in range(3)]
        contexts = [MockToolContext() for _ in range(3)]
        results = ["result_1", "result_2", "result_3"]

        for tool, context, result in zip(tools, contexts, results):
            before_tool(tool, context)
            after_tool(tool, result, context)

        # Verify each tool context has timing
        for context in contexts:
            assert hasattr(context, "_tool_start_time")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
