"""
Fixtures for agent integration tests.
"""

import pytest

from tests.integration.conftest import (
    MockDevOpsAgent,
    MockSoftwareEngineerAgent,
    MockSWEAgent,
    create_mock_agent_pool,
)


# Agent fixtures
@pytest.fixture(scope="function")
def mock_devops_agent(mock_context_manager, mock_llm_client):
    """Create mock DevOps agent for testing."""
    return MockDevOpsAgent(context_manager=mock_context_manager, llm_client=mock_llm_client)


@pytest.fixture(scope="function")
def mock_software_engineer_agent(mock_context_manager, mock_llm_client):
    """Create mock Software Engineer agent for testing."""
    return MockSoftwareEngineerAgent(
        context_manager=mock_context_manager, llm_client=mock_llm_client
    )


@pytest.fixture(scope="function")
def mock_swe_agent(mock_context_manager, mock_llm_client):
    """Create mock SWE agent for testing."""
    return MockSWEAgent(context_manager=mock_context_manager, llm_client=mock_llm_client)


@pytest.fixture(scope="function")
def mock_agent_pool(mock_devops_agent, mock_software_engineer_agent, mock_swe_agent):
    """Create pool of mock agents for testing."""
    return create_mock_agent_pool([mock_devops_agent, mock_software_engineer_agent, mock_swe_agent])
