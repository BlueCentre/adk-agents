"""
Fixtures for context management integration tests.
"""

import pytest

from tests.shared.mocks import (
    MockContextManager,
    MockCrossTurnCorrelator,
    MockIntelligentSummarizer,
    MockRAGSystem,
    MockSmartPrioritizer,
)


# Context management fixtures
@pytest.fixture(scope="function")
def mock_context_manager(mock_llm_client):
    """Create mock context manager with realistic behavior."""
    return MockContextManager(
        model_name="test-model", max_llm_token_limit=100000, llm_client=mock_llm_client
    )


@pytest.fixture(scope="function")
def mock_smart_prioritizer():
    """Create mock smart prioritizer for testing."""
    return MockSmartPrioritizer()


@pytest.fixture(scope="function")
def mock_cross_turn_correlator():
    """Create mock cross-turn correlator for testing."""
    return MockCrossTurnCorrelator()


@pytest.fixture(scope="function")
def mock_intelligent_summarizer():
    """Create mock intelligent summarizer for testing."""
    return MockIntelligentSummarizer()


@pytest.fixture(scope="function")
def mock_rag_system():
    """Create mock RAG system for testing."""
    return MockRAGSystem()
