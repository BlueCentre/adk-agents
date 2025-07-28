"""
Pytest configuration and common fixtures for DevOps agent tests.

This file provides pytest configuration and shared fixtures that can be
used across all test modules.
"""

import asyncio
import logging
import os
import time
from unittest.mock import patch

import pytest

# Global flag to track if we've set up aiohttp cleanup suppression
_aiohttp_cleanup_suppressed = False

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Clean up any pending tasks before closing
    try:
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            # Cancel pending tasks
            for task in pending_tasks:
                task.cancel()
            # Wait for tasks to be cancelled
            if pending_tasks:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
    except Exception:
        # Ignore cleanup errors - they're from external libraries
        pass
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def suppress_aiohttp_cleanup_errors():
    """Suppress aiohttp connection cleanup logging errors from external libraries."""
    import logging

    class AiohttpCleanupFilter(logging.Filter):
        def filter(self, record):
            # Suppress aiohttp cleanup errors that occur during test teardown
            if (
                hasattr(record, "getMessage")
                and record.levelno == logging.ERROR
                and (
                    "Unclosed client session" in record.getMessage()
                    or "Unclosed connector" in record.getMessage()
                    or "I/O operation on closed file" in record.getMessage()
                )
            ):
                # These are cleanup issues from external libraries (Google ADK)
                return False
            return True

    # Apply filter to root logger to catch all aiohttp cleanup errors
    root_logger = logging.getLogger()
    cleanup_filter = AiohttpCleanupFilter()
    root_logger.addFilter(cleanup_filter)

    # Also patch asyncio's default exception handler to suppress aiohttp cleanup errors
    original_exception_handler = None
    loop = None

    try:
        loop = asyncio.get_event_loop()
        original_exception_handler = loop.get_exception_handler()

        def custom_exception_handler(loop, context):
            # Suppress aiohttp cleanup exceptions
            exception = context.get("exception")

            if exception and (
                "Unclosed client session" in str(exception)
                or "Unclosed connector" in str(exception)
                or "I/O operation on closed file" in str(exception)
            ):
                # Silently ignore aiohttp cleanup errors from external libraries
                return

            # For all other exceptions, use the original handler
            if original_exception_handler:
                original_exception_handler(loop, context)
            else:
                loop.default_exception_handler(context)

        loop.set_exception_handler(custom_exception_handler)
    except RuntimeError:
        # No event loop available, skip asyncio patching
        pass

    yield

    # Restore original handlers
    if loop and original_exception_handler:
        loop.set_exception_handler(original_exception_handler)
    elif loop:
        loop.set_exception_handler(None)  # Reset to default

    root_logger.removeFilter(cleanup_filter)


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
        format="%(levelname)s:%(name)s:%(message)s",
    )


@pytest.fixture
def mock_time():
    """Mock time.time() for consistent testing."""
    with patch("time.time", return_value=1234567890.0):
        yield


@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep for faster tests."""
    with patch("asyncio.sleep", return_value=None):
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
    """Configure pytest with custom markers and global aiohttp cleanup suppression."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "async_test: mark test as async")
    config.addinivalue_line("markers", "performance: Performance test")
    config.addinivalue_line("markers", "stress: Stress test")
    config.addinivalue_line("markers", "load: Load test")
    config.addinivalue_line("markers", "foundation: Foundation phase tests")
    config.addinivalue_line("markers", "core: Core integration phase tests")
    config.addinivalue_line("markers", "orchestration: Tool orchestration phase tests")
    config.addinivalue_line("markers", "verification: Performance verification phase tests")

    # Set up global aiohttp cleanup suppression
    global _aiohttp_cleanup_suppressed
    if not _aiohttp_cleanup_suppressed:
        # Monkey patch the logging module to suppress aiohttp cleanup errors
        original_error = logging.Logger.error

        def patched_error(self, msg, *args, **kwargs):
            # Suppress specific aiohttp cleanup error messages
            if isinstance(msg, str) and (
                "Unclosed client session" in msg or "Unclosed connector" in msg
            ):
                return None  # Silently ignore these errors
            return original_error(self, msg, *args, **kwargs)

        logging.Logger.error = patched_error
        _aiohttp_cleanup_suppressed = True


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
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
        "log_level": "WARNING",
    }


# Custom pytest hooks for better test reporting
def pytest_runtest_setup(item):
    """Setup for each test run."""
    # Log test start
    logging.getLogger("test").info(f"Starting test: {item.name}")

    # Skip performance tests on slow systems
    if "performance" in item.keywords:
        if os.environ.get("SKIP_PERFORMANCE_TESTS", "false").lower() == "true":
            pytest.skip("Performance tests skipped on slow systems")

    # Skip stress tests unless explicitly requested
    if "stress" in item.keywords:
        if os.environ.get("RUN_STRESS_TESTS", "false").lower() != "true":
            pytest.skip("Stress tests skipped unless explicitly requested")

    # Skip load tests unless explicitly requested
    if "load" in item.keywords and os.environ.get("RUN_LOAD_TESTS", "false").lower() != "true":
        pytest.skip("Load tests skipped unless explicitly requested")


def pytest_runtest_teardown(item, nextitem):  # noqa: ARG001
    """Teardown hook called after each test."""
    # Log test completion
    logging.getLogger("test").info(f"Completed test: {item.name}")
    if hasattr(item, "_integration_test_start_time"):
        execution_time = time.time() - item._integration_test_start_time

        # Log slow tests
        if execution_time > 5.0:
            logging.warning(f"Slow test detected: {item.name} took {execution_time:.2f}s")

        # Store execution time for reporting
        if not hasattr(item, "_integration_test_metrics"):
            item._integration_test_metrics = {}
        item._integration_test_metrics["execution_time"] = execution_time


def pytest_unconfigure(config):  # noqa: ARG001
    """Cleanup after integration tests."""
    # Clean up environment variables
    env_vars = [
        "DEVOPS_AGENT_TESTING",
        "DEVOPS_AGENT_LOG_LEVEL",
        "DEVOPS_AGENT_INTEGRATION_TEST",
    ]

    for var in env_vars:
        if var in os.environ:
            del os.environ[var]

    logging.getLogger("test").info("Integration test environment cleaned up")


def pytest_exception_interact(node, call, report):  # noqa: ARG001
    """Hook called when an exception occurs during test execution."""
    if report.failed:
        logging.getLogger("test").error(f"Test {node.name} failed with: {report.longrepr}")


# Test execution hooks
def pytest_runtest_call(item):
    """Called to execute the test."""
    start_time = time.time()

    # Store start time for later use
    item._integration_test_start_time = start_time
