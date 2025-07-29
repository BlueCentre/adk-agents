from dataclasses import dataclass, field
import logging
import time

import pytest

from agents.software_engineer.shared_libraries.callbacks import create_retry_callbacks

# Test utilities
from tests.shared.helpers import (
    MockCallbackContext,
    MockLlmRequest,
    MockLlmResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class RetryTestMetrics:
    """Metrics collected during retry testing."""

    retry_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_retry_time: float = 0.0
    retry_delays: list[float] = field(default_factory=list)
    errors_encountered: list[str] = field(default_factory=list)
    non_retryable_errors: int = 0


class TestRetryCallbackCreation:
    """Test retry callback creation and configuration."""

    def test_create_retry_callbacks_default_config(self):
        """Test creating retry callbacks with default configuration."""
        agent_name = "test_agent"
        retry_callbacks = create_retry_callbacks(agent_name)

        # Verify all expected callbacks are created
        expected_callbacks = ["before_model", "after_model", "retry_handler"]
        assert all(key in retry_callbacks for key in expected_callbacks)

        # Verify callbacks are callable
        assert callable(retry_callbacks["before_model"])
        assert callable(retry_callbacks["after_model"])
        assert callable(retry_callbacks["retry_handler"])

    def test_create_retry_callbacks_custom_config(self):
        """Test creating retry callbacks with custom configuration."""
        agent_name = "custom_agent"
        custom_config = {
            "max_retries": 5,
            "base_delay": 0.5,
            "max_delay": 10.0,
            "backoff_multiplier": 1.5,
        }

        retry_callbacks = create_retry_callbacks(agent_name, **custom_config)

        # Verify callbacks are created with custom config
        assert "retry_handler" in retry_callbacks
        assert callable(retry_callbacks["retry_handler"])

    def test_retry_callback_logging(self, caplog):
        """Test that retry callback creation logs appropriately."""
        agent_name = "logging_test_agent"

        with caplog.at_level(logging.INFO):
            create_retry_callbacks(agent_name, max_retries=2, base_delay=0.1)

        # Verify creation is logged
        log_messages = [record.message for record in caplog.records]
        assert any(agent_name in msg and "Creating retry callbacks" in msg for msg in log_messages)

    def test_before_model_callback_execution(self):
        """Test before_model callback execution."""
        agent_name = "before_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name)

        callback_context = MockCallbackContext()
        llm_request = MockLlmRequest()

        # Execute before_model callback
        result = retry_callbacks["before_model"](callback_context, llm_request)

        # Should not return anything but should execute without error
        assert result is None
        # Note: Callback now just does logging - no state stored

    def test_after_model_callback_execution(self):
        """Test after_model callback execution."""
        agent_name = "after_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name)

        callback_context = MockCallbackContext()
        llm_response = MockLlmResponse()

        # Execute after_model callback
        result = retry_callbacks["after_model"](callback_context, llm_response)

        # Should not return anything but should execute without error
        assert result is None
        # Note: Callback now just does logging - no state stored


class TestRetryHandlerLogic:
    """Test the core retry handler logic."""

    @pytest.mark.asyncio
    async def test_retry_handler_success_first_attempt(self):
        """Test retry handler when function succeeds on first attempt."""
        agent_name = "success_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        call_count = 0
        expected_result = {"success": True}

        async def successful_function():
            nonlocal call_count
            call_count += 1
            return expected_result

        # Execute with retry handler
        result = await retry_handler(successful_function)

        # Verify success on first attempt
        assert result == expected_result
        assert call_count == 1

    @pytest.mark.skip(reason="Skipping flaky test: test_retry_handler_success_after_failure")
    @pytest.mark.asyncio
    async def test_retry_handler_success_after_failure(self):
        """Test retry handler when function fails once then succeeds."""
        agent_name = "retry_success_agent"
        retry_callbacks = create_retry_callbacks(agent_name, max_retries=2, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        call_count = 0
        expected_result = {"success": True, "attempt": 2}

        async def failing_then_success_function():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise ValueError("No message in response")
            return expected_result

        start_time = time.time()
        result = await retry_handler(failing_then_success_function)
        end_time = time.time()

        # Verify eventual success
        assert result == expected_result
        assert call_count == 2

        # Verify delay was applied (should be > 0.01s due to retry delay + jitter)
        assert end_time - start_time > 0.01

    @pytest.mark.asyncio
    async def test_retry_handler_exhaustion(self):
        """Test retry handler when all attempts are exhausted."""
        agent_name = "exhaustion_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name, max_retries=2, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        call_count = 0

        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("No message in response")

        # Should raise the error after exhausting retries
        with pytest.raises(ValueError, match="No message in response"):
            await retry_handler(always_failing_function)

        # Verify all attempts were made (initial + retries)
        assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_handler_non_retryable_error(self):
        """Test retry handler with non-retryable errors."""
        agent_name = "non_retryable_agent"
        retry_callbacks = create_retry_callbacks(agent_name, max_retries=2, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        call_count = 0

        async def non_retryable_error_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Different error message")

        # Should raise immediately without retries
        with pytest.raises(ValueError, match="Different error message"):
            await retry_handler(non_retryable_error_function)

        # Verify only one attempt was made
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_handler_with_non_async_function(self):
        """Test retry handler with synchronous functions."""
        agent_name = "sync_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        call_count = 0

        def sync_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("No message in response")
            return {"success": True, "attempt": call_count}

        # Execute with retry handler
        result = await retry_handler(sync_function)

        # Verify success after retry
        assert result == {"success": True, "attempt": 2}
        assert call_count == 2


class TestRetrySystemErrorHandling:
    """Test error handling and edge cases in retry system."""

    @pytest.mark.asyncio
    async def test_retry_handler_with_none_function(self):
        """Test retry handler with None function."""
        agent_name = "none_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name)
        retry_handler = retry_callbacks["retry_handler"]

        with pytest.raises(TypeError):
            await retry_handler(None)

    @pytest.mark.asyncio
    async def test_retry_handler_with_invalid_function(self):
        """Test retry handler with non-callable object."""
        agent_name = "invalid_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name)
        retry_handler = retry_callbacks["retry_handler"]

        with pytest.raises(TypeError):
            await retry_handler("not_a_function")

    def test_retry_callbacks_with_invalid_config(self):
        """Test retry callback creation with invalid configuration."""
        agent_name = "invalid_config_agent"

        # Test with negative max_retries
        with pytest.raises(ValueError):
            create_retry_callbacks(agent_name, max_retries=-1)

        # Test with zero or negative delays
        with pytest.raises(ValueError):
            create_retry_callbacks(agent_name, base_delay=0)

        with pytest.raises(ValueError):
            create_retry_callbacks(agent_name, max_delay=-1)

    @pytest.mark.asyncio
    async def test_retry_handler_exception_propagation(self):
        """Test that non-retryable exceptions are properly propagated."""
        agent_name = "exception_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name, max_retries=2)
        retry_handler = retry_callbacks["retry_handler"]

        async def exception_function():
            raise RuntimeError("Critical system error")

        # RuntimeError should not be retried and should propagate immediately
        with pytest.raises(RuntimeError, match="Critical system error"):
            await retry_handler(exception_function)

    def test_retry_system_logging_integration(self, caplog):
        """Test that retry system integrates properly with logging."""
        agent_name = "logging_integration_agent"

        with caplog.at_level(logging.INFO):
            create_retry_callbacks(agent_name, max_retries=1, base_delay=0.01)

        # Verify creation logs
        creation_logs = [
            record.message
            for record in caplog.records
            if "Creating retry callbacks" in record.message
        ]
        assert len(creation_logs) == 1
        assert agent_name in creation_logs[0]
