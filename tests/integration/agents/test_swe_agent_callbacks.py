"""
Integration Tests for SWE Agent Callback Functions

This module contains integration tests that verify the callback functionality
implemented for the Software Engineer Agent, including telemetry, observability,
and performance monitoring.

Based on Google ADK patterns and the project's multi-agent architecture.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Import project components
from agents.software_engineer.shared_libraries.callbacks import (
    create_enhanced_telemetry_callbacks,
    create_telemetry_callbacks,
)

# Test utilities
from tests.shared.helpers import (
    MockInvocationContext,
    MockLlmRequest,
    MockLlmResponse,
    MockTool,
    MockToolContext,
)

logger = logging.getLogger(__name__)


@dataclass
class CallbackTestMetrics:
    """Metrics collected during callback testing."""

    model_requests: int = 0
    model_responses: int = 0
    tool_executions: int = 0
    tool_completions: int = 0
    agent_sessions: int = 0
    agent_completions: int = 0
    total_response_time: float = 0.0
    total_tool_time: float = 0.0
    total_session_time: float = 0.0
    errors: list[str] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    project_contexts: list[dict[str, Any]] = field(default_factory=list)


class CallbackTestCollector:
    """Collects callback execution data for testing."""

    def __init__(self):
        self.metrics = CallbackTestMetrics()
        self.model_callbacks = []
        self.tool_callbacks = []
        self.agent_callbacks = []
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
        """Log tool completion callback execution."""
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

        # Track tool time if available
        if hasattr(context, "_tool_start_time"):
            tool_time = time.time() - context._tool_start_time
            self.metrics.total_tool_time += tool_time

    def log_agent_session_start(self, context: Any):
        """Log agent session start callback execution."""
        self.metrics.agent_sessions += 1
        self.agent_callbacks.append(
            {
                "type": "before_agent",
                "timestamp": time.time(),
                "context": context,
            }
        )
        self.execution_log.append("before_agent")

    def log_agent_session_end(self, context: Any):
        """Log agent session end callback execution."""
        self.metrics.agent_completions += 1
        self.agent_callbacks.append(
            {
                "type": "after_agent",
                "timestamp": time.time(),
                "context": context,
            }
        )
        self.execution_log.append("after_agent")

        # Track session time if available
        if hasattr(context, "_agent_session_start_time"):
            session_time = time.time() - context._agent_session_start_time
            self.metrics.total_session_time += session_time

        # Track project context if available
        if hasattr(context, "_agent_metrics") and context._agent_metrics.get("project_context"):
            self.metrics.project_contexts.append(context._agent_metrics["project_context"])

    def get_execution_summary(self) -> dict[str, Any]:
        """Get summary of callback execution."""
        return {
            "total_callbacks": len(self.execution_log),
            "execution_order": self.execution_log,
            "metrics": self.metrics,
            "callback_counts": {
                "model_callbacks": len(self.model_callbacks),
                "tool_callbacks": len(self.tool_callbacks),
                "agent_callbacks": len(self.agent_callbacks),
            },
        }


@pytest.fixture
def callback_collector():
    """Fixture providing a callback test collector."""
    return CallbackTestCollector()


@pytest.fixture
def mock_llm_request():
    """Fixture providing a mock LLM request."""
    return MockLlmRequest(
        contents=["Test request content"],
        model="test-model",
        messages=[{"role": "user", "content": "Test message"}],
    )


@pytest.fixture
def mock_llm_response():
    """Fixture providing a mock LLM response."""
    response = MockLlmResponse(text="Test response content")
    # Use the new usage format that the callback code expects
    response.usage = MagicMock()
    response.usage.input_tokens = 100
    response.usage.output_tokens = 200
    return response


@pytest.fixture
def mock_invocation_context():
    """Fixture providing a mock invocation context."""
    return MockInvocationContext(
        invocation_id="test_inv_123", trace_id="test_trace_456", session_state={}
    )


@pytest.fixture
def mock_tool_context():
    """Fixture providing a mock tool context."""
    return MockToolContext(state={})


@pytest.fixture
def mock_test_tool():
    """Fixture providing a mock tool."""
    return MockTool(name="test_tool", args={"param1": "value1", "param2": "value2"})


class TestBasicCallbacks:
    """Test basic callback functionality."""

    def test_create_basic_callbacks(self):
        """Test that basic callbacks can be created successfully."""
        callbacks = create_telemetry_callbacks("test_agent")

        assert len(callbacks) == 6  # Updated from 4 to 6

        # Check that all expected keys are present
        expected_keys = [
            "before_agent",
            "after_agent",
            "before_model",
            "after_model",
            "before_tool",
            "after_tool",
        ]
        for key in expected_keys:
            assert key in callbacks
            assert callable(callbacks[key])

    def test_basic_before_model_callback(self, mock_llm_request, mock_invocation_context, caplog):
        """Test basic before_model callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks["before_model"]

        with caplog.at_level(logging.DEBUG):
            before_model_callback(mock_invocation_context, mock_llm_request)

        # Verify logging
        assert "Before model request" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_inv_123" in caplog.text

        # Verify timing is set (new attribute name)
        assert hasattr(mock_invocation_context, "_model_request_start_time")
        assert isinstance(mock_invocation_context._model_request_start_time, float)

    def test_basic_after_model_callback(self, mock_llm_response, mock_invocation_context, caplog):
        """Test basic after_model callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_model_callback = callbacks["after_model"]

        # Set up timing (new attribute name)
        mock_invocation_context._model_request_start_time = time.time() - 1.5

        with caplog.at_level(logging.DEBUG):
            after_model_callback(mock_invocation_context, mock_llm_response)

        # Verify logging
        assert "After model response" in caplog.text
        assert "test_agent" in caplog.text
        # Note: Response time logging is removed from the new implementation
        # assert "Response time:" in caplog.text
        # assert "Token usage" in caplog.text
        # assert "Prompt: 100" in caplog.text
        # assert "Response: 200" in caplog.text
        # assert "Total: 300" in caplog.text

    def test_basic_before_tool_callback(
        self, mock_test_tool, mock_tool_context, mock_invocation_context, caplog
    ):
        """Test basic before_tool callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_tool_callback = callbacks["before_tool"]

        with caplog.at_level(logging.DEBUG):
            before_tool_callback(
                mock_test_tool,
                {"param1": "value1"},
                mock_tool_context,
                mock_invocation_context,
            )

        # Verify logging
        assert "Before tool execution" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_tool" in caplog.text

        # Verify timing is set
        assert hasattr(mock_invocation_context, "_tool_start_time")
        assert isinstance(mock_invocation_context._tool_start_time, float)

    def test_basic_after_tool_callback(
        self, mock_test_tool, mock_tool_context, mock_invocation_context, caplog
    ):
        """Test basic after_tool callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_tool_callback = callbacks["after_tool"]

        # Set up timing
        mock_invocation_context._tool_start_time = time.time() - 0.5

        with caplog.at_level(logging.DEBUG):
            after_tool_callback(
                mock_test_tool,
                "Tool execution successful",
                mock_invocation_context,
                {"param1": "value1"},
                mock_tool_context,
            )

        # Verify logging
        assert "After tool execution" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_tool" in caplog.text
        # Note: Tool execution time logging is removed from the new implementation
        # assert "Tool execution time:" in caplog.text
        assert "Tool result preview: Tool execution successful" in caplog.text

    def test_basic_before_agent_callback(self, mock_invocation_context, caplog):
        """Test basic before_agent callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        with caplog.at_level(logging.INFO):
            before_agent_callback(mock_invocation_context)

        # Verify logging
        assert "Basic agent session started" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_session_456" in caplog.text
        assert "Agent lifecycle: SESSION_START" in caplog.text

        # Verify session metrics are initialized
        assert hasattr(mock_invocation_context, "_agent_session_start_time")
        assert hasattr(mock_invocation_context, "_agent_metrics")
        assert isinstance(mock_invocation_context._agent_metrics, dict)

    def test_basic_after_agent_callback(self, mock_invocation_context, caplog):
        """Test basic after_agent callback execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        after_agent_callback = callbacks["after_agent"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        # Set up session timing and metrics (new structure)
        mock_invocation_context._agent_session_start_time = time.time() - 5.0
        mock_invocation_context._agent_metrics = {
            "session_start_time": time.time() - 5.0,
            "total_model_calls": 3,
            "total_tool_calls": 5,
            "total_input_tokens": 100,
            "total_output_tokens": 200,
            "total_response_time": 1.5,
            "project_context": {"project_type": "python", "total_files": 42},
        }

        with caplog.at_level(logging.INFO):
            after_agent_callback(mock_invocation_context)

        # Verify logging (updated message)
        assert "Basic agent session completed" in caplog.text
        assert "test_agent" in caplog.text
        assert "test_session_456" in caplog.text
        assert "Session duration: 5.00 seconds" in caplog.text
        assert "Session summary:" in caplog.text
        assert "Total model calls: 3" in caplog.text
        assert "Total tool calls: 5" in caplog.text
        assert "Total input tokens: 100" in caplog.text
        assert "Total output tokens: 200" in caplog.text
        assert "Total response time: 1.50s" in caplog.text
        assert "Agent lifecycle: SESSION_END" in caplog.text


class TestEnhancedCallbacks:
    """Test enhanced callback functionality."""

    def test_create_enhanced_callbacks(self):
        """Test that enhanced callbacks can be created successfully."""
        callbacks = create_enhanced_telemetry_callbacks("test_enhanced_agent")

        assert len(callbacks) == 6  # Updated from 4 to 6

        # Check that all expected keys are present
        expected_keys = [
            "before_agent",
            "after_agent",
            "before_model",
            "after_model",
            "before_tool",
            "after_tool",
        ]
        for key in expected_keys:
            assert key in callbacks
            assert callable(callbacks[key])

    def test_enhanced_before_agent_callback(self, mock_invocation_context, caplog):
        """Test enhanced before_agent callback execution."""
        callbacks = create_enhanced_telemetry_callbacks("test_enhanced_agent")
        before_agent_callback = callbacks["before_agent"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        with caplog.at_level(logging.INFO):
            before_agent_callback(mock_invocation_context)

        # Verify enhanced logging (falls back to basic when telemetry not available)
        assert "Enhanced agent session started" in caplog.text
        assert "test_enhanced_agent" in caplog.text
        assert "Project context loaded:" in caplog.text
        assert "Agent lifecycle: SESSION_START" in caplog.text

        # Verify enhanced session metrics are initialized
        assert hasattr(mock_invocation_context, "_agent_session_start_time")
        assert hasattr(mock_invocation_context, "_agent_metrics")

        metrics = mock_invocation_context._agent_metrics
        # When telemetry is not available, enhanced callbacks fall back to basic
        # so we check for the new metrics structure
        assert "project_context" in metrics
        assert metrics["total_model_calls"] == 0
        assert metrics["total_tool_calls"] == 0
        assert metrics["total_input_tokens"] == 0
        assert metrics["total_output_tokens"] == 0
        assert metrics["total_response_time"] == 0.0

    def test_enhanced_after_agent_callback(self, mock_invocation_context, caplog):
        """Test enhanced after_agent callback execution."""
        callbacks = create_enhanced_telemetry_callbacks("test_enhanced_agent")
        after_agent_callback = callbacks["after_agent"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        # Set up enhanced session timing and metrics (new structure)
        mock_invocation_context._agent_session_start_time = time.time() - 10.0
        mock_invocation_context._agent_metrics = {
            "session_start_time": time.time() - 10.0,
            "total_model_calls": 8,
            "total_tool_calls": 15,
            "total_input_tokens": 2000,
            "total_output_tokens": 1500,
            "total_response_time": 5.0,
            "project_context": {
                "project_type": "python",
                "total_files": 128,
                "python_files": 85,
                "javascript_files": 12,
            },
        }

        with caplog.at_level(logging.INFO):
            after_agent_callback(mock_invocation_context)

        # Verify enhanced logging (updated message)
        assert "Enhanced agent session completed" in caplog.text
        assert "test_enhanced_agent" in caplog.text
        assert "test_session_456" in caplog.text
        assert "Session duration: 10.00 seconds" in caplog.text
        assert "Session summary:" in caplog.text
        assert "Total model calls: 8" in caplog.text
        assert "Total tool calls: 15" in caplog.text
        assert "Total input tokens: 2000" in caplog.text
        assert "Total output tokens: 1500" in caplog.text
        assert "Total response time: 5.00s" in caplog.text
        assert "Agent lifecycle: SESSION_END" in caplog.text

    def test_enhanced_session_metrics_tracking(
        self,
        mock_invocation_context,
        mock_llm_request,
        mock_llm_response,
        mock_test_tool,
    ):
        """Test that enhanced callbacks track session metrics correctly."""
        # Use basic callbacks for testing metrics tracking since enhanced callbacks fall back to
        # basic when telemetry is not available
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent = callbacks["before_agent"]
        after_agent = callbacks["after_agent"]
        before_model = callbacks["before_model"]
        after_model = callbacks["after_model"]
        before_tool = callbacks["before_tool"]
        after_tool = callbacks["after_tool"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        # Start agent session
        before_agent(mock_invocation_context)

        # Verify initial metrics (new structure)
        assert hasattr(mock_invocation_context, "_agent_metrics")
        metrics = mock_invocation_context._agent_metrics
        assert metrics["total_model_calls"] == 0
        assert metrics["total_tool_calls"] == 0
        assert metrics["total_input_tokens"] == 0
        assert metrics["total_output_tokens"] == 0
        assert metrics["total_response_time"] == 0.0

        # Simulate model call
        before_model(mock_invocation_context, mock_llm_request)
        after_model(mock_invocation_context, mock_llm_response)

        # Verify metrics updated
        assert metrics["total_model_calls"] == 1
        assert metrics["total_input_tokens"] == 100  # from mock response
        assert metrics["total_output_tokens"] == 200  # from mock response

        # Simulate tool call
        before_tool(mock_test_tool, {"param": "value"}, None, mock_invocation_context)
        after_tool(mock_test_tool, "success", mock_invocation_context, {"param": "value"}, None)

        # Verify final metrics
        assert metrics["total_model_calls"] == 1
        assert metrics["total_tool_calls"] == 1
        assert metrics["total_input_tokens"] == 100
        assert metrics["total_output_tokens"] == 200

        # End session
        after_agent(mock_invocation_context)


class TestProjectContextLoading:
    """Test project context loading functionality."""

    @patch("agents.software_engineer.shared_libraries.callbacks.os.getcwd")
    @patch("agents.software_engineer.shared_libraries.callbacks.Path.exists")
    @patch("agents.software_engineer.shared_libraries.callbacks.Path.is_dir")
    @patch("agents.software_engineer.shared_libraries.callbacks.os.scandir")
    @patch("agents.software_engineer.shared_libraries.callbacks.os.getenv")
    def test_project_context_python_detection(
        self, mock_getenv, mock_scandir, mock_is_dir, mock_exists, mock_getcwd
    ):
        """Test that Python projects are detected correctly."""
        mock_getcwd.return_value = "/test/python_project"
        mock_getenv.return_value = None  # No environment variables set
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        # Create mock scandir entries with proper name attribute
        mock_entries = []
        for filename in [
            "pyproject.toml",
            "src",
            "tests",
            "main.py",
            "requirements.txt",
        ]:
            entry = MagicMock()
            entry.name = filename
            mock_entries.append(entry)
        mock_scandir.return_value.__enter__.return_value = iter(mock_entries)

        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        mock_context = MockInvocationContext()
        mock_context.user_data = {}
        before_agent_callback(mock_context)

        # Verify project context was loaded
        assert hasattr(mock_context, "_agent_metrics")
        project_context = mock_context._agent_metrics["project_context"]
        assert project_context["project_type"] == "python"
        assert project_context["project_name"] == "python_project"
        assert project_context["total_files"] == 5
        assert project_context["python_files"] == 1
        assert "pyproject.toml" in project_context["files_found"]

    @patch("agents.software_engineer.shared_libraries.callbacks.os.getcwd")
    @patch("agents.software_engineer.shared_libraries.callbacks.Path.exists")
    @patch("agents.software_engineer.shared_libraries.callbacks.Path.is_dir")
    @patch("agents.software_engineer.shared_libraries.callbacks.os.scandir")
    @patch("agents.software_engineer.shared_libraries.callbacks.os.getenv")
    def test_project_context_javascript_detection(
        self, mock_getenv, mock_scandir, mock_is_dir, mock_exists, mock_getcwd
    ):
        """Test that JavaScript projects are detected correctly."""
        mock_getcwd.return_value = "/test/js_project"
        mock_getenv.return_value = None  # No environment variables set
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        # Create mock scandir entries with proper name attribute
        mock_entries = []
        for filename in ["package.json", "src", "node_modules", "index.js", "app.ts"]:
            entry = MagicMock()
            entry.name = filename
            mock_entries.append(entry)
        mock_scandir.return_value.__enter__.return_value = iter(mock_entries)

        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        mock_context = MockInvocationContext()
        mock_context.user_data = {}
        before_agent_callback(mock_context)

        # Verify project context was loaded
        assert hasattr(mock_context, "_agent_metrics")
        project_context = mock_context._agent_metrics["project_context"]
        assert project_context["project_type"] == "javascript"
        assert project_context["project_name"] == "js_project"
        assert project_context["total_files"] == 5
        assert project_context["javascript_files"] == 2
        assert "package.json" in project_context["files_found"]

    @patch("agents.software_engineer.shared_libraries.callbacks.os.getcwd")
    @patch("agents.software_engineer.shared_libraries.callbacks.Path.exists")
    @patch("agents.software_engineer.shared_libraries.callbacks.Path.is_dir")
    @patch("agents.software_engineer.shared_libraries.callbacks.os.scandir")
    @patch("agents.software_engineer.shared_libraries.callbacks.os.getenv")
    def test_project_context_unknown_detection(
        self, mock_getenv, mock_scandir, mock_is_dir, mock_exists, mock_getcwd
    ):
        """Test that unknown projects are handled correctly."""
        mock_getcwd.return_value = "/test/unknown_project"
        mock_getenv.return_value = None  # No environment variables set
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        # Create mock scandir entries with proper name attribute
        mock_entries = []
        for filename in ["README.md", "data.csv", "config.ini"]:
            entry = MagicMock()
            entry.name = filename
            mock_entries.append(entry)
        mock_scandir.return_value.__enter__.return_value = iter(mock_entries)

        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        mock_context = MockInvocationContext()
        mock_context.user_data = {}
        before_agent_callback(mock_context)

        # Verify project context was loaded
        assert hasattr(mock_context, "_agent_metrics")
        project_context = mock_context._agent_metrics["project_context"]
        assert project_context["project_type"] == "unknown"
        assert project_context["project_name"] == "unknown_project"
        assert project_context["total_files"] == 3
        assert project_context["python_files"] == 0
        assert project_context["javascript_files"] == 0


class TestCallbackLogging:
    """Test callback logging functionality."""

    def test_callback_log_levels(self, mock_llm_request, mock_invocation_context, caplog):
        """Test that callbacks log at appropriate levels."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks["before_model"]

        # Test DEBUG level logging
        with caplog.at_level(logging.DEBUG):
            before_model_callback(mock_invocation_context, mock_llm_request)

        debug_logs = [record for record in caplog.records if record.levelno == logging.DEBUG]
        assert len(debug_logs) > 0, "Should have DEBUG level logs"

        # Test INFO level logging for agent callbacks
        caplog.clear()
        before_agent_callback = callbacks["before_agent"]
        with caplog.at_level(logging.INFO):
            before_agent_callback(mock_invocation_context)

        info_logs = [record for record in caplog.records if record.levelno == logging.INFO]
        assert len(info_logs) > 0, "Should have INFO level logs for agent callbacks"

    def test_callback_log_content(self, mock_llm_request, mock_invocation_context, caplog):
        """Test that callbacks log useful content."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks["before_model"]

        with caplog.at_level(logging.DEBUG):
            before_model_callback(mock_invocation_context, mock_llm_request)

        log_text = caplog.text

        # Should contain agent name
        assert "test_agent" in log_text
        # Should contain invocation ID
        assert "test_inv_123" in log_text
        # Should contain operation type
        assert "Before model request" in log_text

    def test_agent_callback_log_content(self, mock_invocation_context, caplog):
        """Test that agent callbacks log useful content."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        with caplog.at_level(logging.INFO):
            before_agent_callback(mock_invocation_context)

        log_text = caplog.text

        # Should contain agent name
        assert "test_agent" in log_text
        # Should contain session ID
        assert "test_session_456" in log_text
        # Should contain lifecycle event
        assert "Agent lifecycle: SESSION_START" in log_text
        # Should contain project context
        assert "Project context loaded:" in log_text


class TestCallbackIntegration:
    """Test callback integration functionality."""

    @pytest.mark.asyncio
    async def test_callback_execution_order(self):
        """Test that callbacks execute in the correct order during agent execution."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent = callbacks["before_agent"]
        after_agent = callbacks["after_agent"]
        before_model = callbacks["before_model"]
        after_model = callbacks["after_model"]
        before_tool = callbacks["before_tool"]
        after_tool = callbacks["after_tool"]

        # Simulate agent execution sequence
        mock_request = MockLlmRequest()
        mock_response = MockLlmResponse()
        # Add usage attribute to mock response
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 200
        mock_context = MockInvocationContext()
        mock_context.session_id = "test_session_456"
        mock_tool = MockTool("test_tool")
        mock_tool_context = MockToolContext()

        # Execute callbacks in expected order
        before_agent(mock_context)
        before_model(mock_context, mock_request)
        after_model(mock_context, mock_response)
        before_tool(mock_tool, {"param": "value"}, mock_tool_context, mock_context)
        after_tool(mock_tool, "success", mock_context, {"param": "value"}, mock_tool_context)
        after_agent(mock_context)

        # Verify timing was tracked (new attribute name)
        assert hasattr(mock_context, "_model_request_start_time")
        assert hasattr(mock_context, "_tool_start_time")
        assert hasattr(mock_context, "_agent_session_start_time")

        # Verify metrics were tracked (new structure)
        assert hasattr(mock_context, "_agent_metrics")
        metrics = mock_context._agent_metrics
        assert metrics["total_model_calls"] == 1
        assert metrics["total_tool_calls"] == 1
        assert metrics["total_input_tokens"] == 100
        assert metrics["total_output_tokens"] == 200

    @pytest.mark.asyncio
    async def test_callback_with_multiple_tools(self):
        """Test callback behavior with multiple tool executions."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_tool, after_tool = callbacks["before_tool"], callbacks["after_tool"]

        # Simulate multiple tool executions
        tools = [MockTool(f"tool_{i}") for i in range(3)]
        contexts = [MockToolContext() for _ in range(3)]
        callback_contexts = [MockInvocationContext() for _ in range(3)]
        results = ["result_1", "result_2", "result_3"]

        for tool, context, callback_context, result in zip(
            tools, contexts, callback_contexts, results
        ):
            before_tool(tool, {"param": "value"}, context, callback_context)
            after_tool(tool, result, callback_context, {"param": "value"}, context)

        # Verify each tool context has timing
        for context in callback_contexts:
            assert hasattr(context, "_tool_start_time")

    @pytest.mark.asyncio
    async def test_full_agent_session_simulation(self):
        """Test a complete agent session from start to finish."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent = callbacks["before_agent"]
        after_agent = callbacks["after_agent"]
        before_model = callbacks["before_model"]
        after_model = callbacks["after_model"]
        before_tool = callbacks["before_tool"]
        after_tool = callbacks["after_tool"]

        # Mock objects
        mock_context = MockInvocationContext()
        mock_context.session_id = "test_session_456"
        mock_request = MockLlmRequest()
        mock_response = MockLlmResponse()
        # Add usage metadata to mock response (new format)
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 200
        mock_tool = MockTool("test_tool")
        mock_tool_context = MockToolContext()

        # Simulate complete agent session
        before_agent(mock_context)

        # Simulate multiple interactions
        for i in range(3):
            before_model(mock_context, mock_request)
            after_model(mock_context, mock_response)

            before_tool(mock_tool, {"iteration": i}, mock_tool_context, mock_context)
            after_tool(
                mock_tool,
                f"result_{i}",
                mock_context,
                {"iteration": i},
                mock_tool_context,
            )

        after_agent(mock_context)

        # Verify session metrics were tracked (new structure)
        assert hasattr(mock_context, "_agent_metrics")
        metrics = mock_context._agent_metrics
        assert metrics["total_model_calls"] == 3
        assert metrics["total_tool_calls"] == 3
        assert metrics["total_input_tokens"] == 300  # 3 * 100 tokens
        assert metrics["total_output_tokens"] == 600  # 3 * 200 tokens
        assert metrics["total_response_time"] > 0  # Should have some response time


class TestCallbackErrorHandling:
    """Test callback error handling."""

    def test_callback_handles_none_context(self, mock_llm_request, caplog):
        """Test that callbacks handle None context gracefully."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_model_callback = callbacks["before_model"]

        # This should not raise an exception
        with caplog.at_level(logging.DEBUG):
            before_model_callback(None, mock_llm_request)

        # Should log with "unknown" identifiers
        assert "unknown" in caplog.text

    def test_callback_handles_missing_attributes(self, mock_invocation_context, caplog):
        """Test that callbacks handle missing attributes gracefully."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        # Don't add session_id to test missing attribute handling
        # The callback should handle this gracefully

        # This should not raise an exception
        with caplog.at_level(logging.INFO):
            before_agent_callback(mock_invocation_context)

        # Should log with "unknown" identifiers
        assert "unknown" in caplog.text

    def test_callback_handles_project_context_errors(self, mock_invocation_context, caplog):
        """Test that callbacks handle project context loading errors gracefully."""
        callbacks = create_telemetry_callbacks("test_agent")
        before_agent_callback = callbacks["before_agent"]

        # Add session_id attribute to mock context
        mock_invocation_context.session_id = "test_session_456"

        # Mock os.getcwd to raise an exception
        with patch("os.getcwd", side_effect=OSError("Permission denied")):
            with caplog.at_level(logging.INFO):
                before_agent_callback(mock_invocation_context)

        # Should still complete without raising an exception
        assert "Basic agent session started" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
