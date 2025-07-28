"""
Fixtures for performance integration tests.
"""

import pytest

from tests.integration.conftest import MockPerformanceMonitor, MockResourceMonitor


# Performance monitoring fixtures
@pytest.fixture(scope="function")
def mock_performance_monitor():
    """Create mock performance monitor for testing."""
    return MockPerformanceMonitor()


@pytest.fixture(scope="function")
def mock_resource_monitor():
    """Create mock resource monitor for testing."""
    return MockResourceMonitor()
