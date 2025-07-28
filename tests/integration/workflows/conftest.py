"""
Fixtures for workflows integration tests.
"""

import pytest

from tests.integration.conftest import (
    create_mock_workflow_config,
)
from tests.shared.mocks import (
    MockToolOrchestrator,
    MockWorkflowEngine,
)


# Workflow orchestration fixtures
@pytest.fixture(scope="function")
def mock_workflow_engine():
    """Create mock workflow engine for testing."""
    return MockWorkflowEngine()


@pytest.fixture(scope="function")
def mock_tool_orchestrator():
    """Create mock tool orchestrator for testing."""
    return MockToolOrchestrator()


@pytest.fixture(scope="function")
def workflow_configs():
    """Create test workflow configurations."""
    return {
        "sequential": create_mock_workflow_config("sequential"),
        "parallel": create_mock_workflow_config("parallel"),
        "iterative": create_mock_workflow_config("iterative"),
        "human_in_loop": create_mock_workflow_config("human_in_loop"),
    }
