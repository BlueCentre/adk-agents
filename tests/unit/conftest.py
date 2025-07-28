"""
Unit test configuration and shared fixtures.
"""

from unittest.mock import Mock

import pytest

# Note: For now, we'll use the minimal versions from test_helpers
# to avoid importing the full devops_agent with its dependencies
from tests.shared.helpers import (
    MetricsCollector,
    MockCallbackContext,
    MockInvocationContext,
    MockLlmRequest,
    MockLlmResponse,
    MockTool,
    MockToolContext,
    StateManager,
    create_populated_state_manager,
    create_sample_legacy_state,
)


@pytest.fixture
def state_manager():
    """Provide a fresh StateManager instance for each test."""
    return StateManager()


@pytest.fixture
def populated_state_manager():
    """Provide a StateManager with sample data for testing."""
    return create_populated_state_manager()


@pytest.fixture
def sample_legacy_state():
    """Provide sample legacy state format for testing."""
    return create_sample_legacy_state()


@pytest.fixture
def mock_invocation_context():
    """Provide a mock invocation context for testing."""
    return MockInvocationContext()


@pytest.fixture
def mock_callback_context():
    """Provide a mock callback context for testing."""
    return MockCallbackContext()


@pytest.fixture
def mock_llm_request():
    """Provide a mock LLM request for testing."""
    return MockLlmRequest()


@pytest.fixture
def mock_llm_response():
    """Provide a mock LLM response for testing."""
    return MockLlmResponse(text="Test response")


@pytest.fixture
def mock_tool():
    """Provide a mock tool for testing."""
    return MockTool("test_tool", {"arg1": "value1"})


@pytest.fixture
def mock_tool_context():
    """Provide a mock tool context for testing."""
    return MockToolContext()


@pytest.fixture
def test_metrics():
    """Provide a MetricsCollector instance for collecting test metrics."""
    return MetricsCollector()


@pytest.fixture
def mock_agent():
    """Provide a mock DevOps agent for testing."""
    agent = Mock()
    agent.name = "test_agent"
    agent.model = "test_model"
    agent._state_manager = StateManager()
    agent._context_manager = Mock()
    agent._planning_manager = Mock()
    agent._console = Mock()
    agent._status_indicator = None
    agent._actual_llm_token_limit = 100000
    agent.llm_client = Mock()

    # Mock methods
    agent._is_retryable_error = Mock(return_value=True)
    agent._count_tokens = Mock(return_value=100)
    agent._start_status = Mock()
    agent._stop_status = Mock()

    return agent
