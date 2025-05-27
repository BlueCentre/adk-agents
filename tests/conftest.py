"""
Pytest configuration and common fixtures for DevOps agent tests.

This file provides pytest configuration and shared fixtures that can be
used across all test modules.
"""

import pytest
import asyncio
import logging
from typing import Dict, Any
from unittest.mock import Mock, patch

# Note: For now, we'll use the minimal versions from test_helpers
# to avoid importing the full devops_agent with its dependencies
from tests.fixtures.test_helpers import (
    create_sample_legacy_state,
    create_populated_state_manager,
    MockInvocationContext,
    MockCallbackContext,
    MockLlmRequest,
    MockLlmResponse,
    MockTool,
    MockToolContext,
    MetricsCollector,
    StateManager,
    StateValidationError
)


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


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


@pytest.fixture
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up basic configuration for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise in tests
        format='%(levelname)s:%(name)s:%(message)s'
    )


@pytest.fixture
def mock_time():
    """Mock time.time() for consistent testing."""
    with patch('time.time', return_value=1234567890.0):
        yield


@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep for faster tests."""
    with patch('asyncio.sleep', return_value=None):
        yield


@pytest.fixture
def capture_logs():
    """Capture log messages during tests."""
    import io
    import logging
    
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Clean up
    root_logger.removeHandler(handler)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "async_test: mark test as async"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add e2e marker to tests in e2e/ directory
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Add async_test marker to async test functions
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.async_test)


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration settings."""
    return {
        "timeout": 30.0,
        "max_retries": 3,
        "test_model": "test_model",
        "mock_responses": True,
        "log_level": "WARNING"
    }


# Custom pytest hooks for better test reporting
def pytest_runtest_setup(item):
    """Setup hook called before each test."""
    # Log test start
    logging.getLogger("test").info(f"Starting test: {item.name}")


def pytest_runtest_teardown(item, nextitem):
    """Teardown hook called after each test."""
    # Log test completion
    logging.getLogger("test").info(f"Completed test: {item.name}")


def pytest_exception_interact(node, call, report):
    """Hook called when an exception occurs during test execution."""
    if report.failed:
        logging.getLogger("test").error(
            f"Test {node.name} failed with: {report.longrepr}"
        ) 