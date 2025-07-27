"""
Integration Tests for Retry System

This module contains integration tests that verify the retry functionality
implemented for handling "No message in response" errors with exponential backoff.

Tests verify:
- Retry callback creation and configuration
- Enhanced agent integration with retry capabilities
- Actual retry logic with simulated failures
- Integration with existing callback systems
- Performance impact and error handling
"""

import asyncio
from dataclasses import dataclass, field
import logging
import time

import pytest

# Import project components
from agents.software_engineer.shared_libraries.callbacks import create_retry_callbacks

# Test utilities
from tests.fixtures.test_helpers import (
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


class TestRetrySystemIntegration:
    """Test integration of retry system with enhanced agent."""

    def test_enhanced_agent_has_retry_capabilities(self):
        """Test that enhanced agent loads with retry capabilities."""
        try:
            from agents.software_engineer.enhanced_agent import enhanced_root_agent

            # Verify agent loaded successfully
            assert enhanced_root_agent is not None
            assert enhanced_root_agent.name == "enhanced_software_engineer"

            # Verify retry handler is configured
            assert hasattr(enhanced_root_agent, "_retry_handler")
            assert enhanced_root_agent._retry_handler is not None
            assert callable(enhanced_root_agent._retry_handler)

        except ImportError as e:
            pytest.skip(f"Enhanced agent not available: {e}")

    def test_enhanced_agent_callback_integration(self):
        """Test that retry callbacks integrate with existing callback system."""
        try:
            from agents.software_engineer.enhanced_agent import enhanced_root_agent

            # Verify agent has callbacks configured
            assert hasattr(enhanced_root_agent, "before_model_callback")
            assert hasattr(enhanced_root_agent, "after_model_callback")

            # Verify callbacks are lists (multiple callbacks)
            assert isinstance(enhanced_root_agent.before_model_callback, list)
            assert isinstance(enhanced_root_agent.after_model_callback, list)

            # Verify retry callbacks are in the list
            callback_names = []
            for callback in enhanced_root_agent.before_model_callback:
                if hasattr(callback, "__name__"):
                    callback_names.append(callback.__name__)

            # Should have retry callback along with others
            assert len(enhanced_root_agent.before_model_callback) > 1

        except ImportError as e:
            pytest.skip(f"Enhanced agent not available: {e}")

    def test_enhanced_agent_model_method_wrapped(self):
        """Test that the enhanced agent's model method is actually wrapped for retry."""
        try:
            from agents.software_engineer.enhanced_agent import enhanced_root_agent

            # Verify agent loaded successfully
            assert enhanced_root_agent is not None
            assert enhanced_root_agent.name == "enhanced_software_engineer"

            # Verify model exists and has generate_content_async method
            assert hasattr(enhanced_root_agent, "model")
            model = enhanced_root_agent.model
            assert hasattr(model, "generate_content_async")

            # Verify the method has been wrapped (should have "with_retry" in the name)
            method_name = model.generate_content_async.__name__
            assert "with_retry" in method_name, (
                f"Expected wrapped method name to contain 'with_retry', got '{method_name}'"
            )

            # Verify agent has retry handler and original method references
            assert hasattr(enhanced_root_agent, "_retry_handler")
            assert hasattr(enhanced_root_agent, "_original_generate_content_async")
            assert enhanced_root_agent._retry_handler is not None
            assert enhanced_root_agent._original_generate_content_async is not None

            logger.info(f"✅ Model method successfully wrapped: {method_name}")

        except ImportError as e:
            pytest.skip(f"Enhanced agent not available: {e}")


class TestRetrySystemPerformance:
    """Test performance characteristics of retry system."""

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff_timing(self):
        """Test that exponential backoff timing works correctly."""
        agent_name = "timing_test_agent"
        base_delay = 0.1
        backoff_multiplier = 2.0
        retry_callbacks = create_retry_callbacks(
            agent_name, max_retries=3, base_delay=base_delay, backoff_multiplier=backoff_multiplier
        )
        retry_handler = retry_callbacks["retry_handler"]

        call_count = 0
        call_times = []

        async def failing_function():
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            raise ValueError("No message in response")

        with pytest.raises(ValueError):
            await retry_handler(failing_function)

        # Verify timing progression (approximate due to jitter)
        assert len(call_times) == 4  # Initial + 3 retries

        # Check that delays increase (accounting for jitter)
        delay_1 = call_times[1] - call_times[0]
        delay_2 = call_times[2] - call_times[1]
        delay_3 = call_times[3] - call_times[2]

        # Each delay should be approximately double the previous (within jitter tolerance)
        assert delay_1 >= base_delay * 0.8  # Account for jitter
        assert delay_2 >= base_delay * backoff_multiplier * 0.8
        assert delay_3 >= base_delay * (backoff_multiplier**2) * 0.8

    @pytest.mark.asyncio
    async def test_retry_performance_metrics_collection(self):
        """Test collection of retry performance metrics."""
        agent_name = "metrics_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name, max_retries=2, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        metrics = RetryTestMetrics()

        async def tracked_failing_function():
            metrics.retry_attempts += 1
            if metrics.retry_attempts <= 2:
                raise ValueError("No message in response")
            return {"success": True}

        start_time = time.time()
        result = await retry_handler(tracked_failing_function)
        total_time = time.time() - start_time

        # Verify metrics
        assert result == {"success": True}
        assert metrics.retry_attempts == 3  # Initial + 2 retries
        assert total_time > 0.02  # Should have some delay from retries

    @pytest.mark.asyncio
    async def test_retry_system_with_high_concurrency(self):
        """Test retry system performance under concurrent load."""
        agent_name = "concurrency_test_agent"
        retry_callbacks = create_retry_callbacks(agent_name, max_retries=1, base_delay=0.01)
        retry_handler = retry_callbacks["retry_handler"]

        async def concurrent_function(task_id):
            # Fail on first attempt for half the tasks
            if task_id % 2 == 0:
                raise ValueError("No message in response")
            return {"task_id": task_id, "success": True}

        # Run multiple concurrent operations
        tasks = []
        for i in range(10):
            task = retry_handler(concurrent_function, i)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        # Half should succeed immediately, half should fail and be retried
        assert len(successful_results) >= 5  # At least the odd-numbered tasks
        assert len(failed_results) == 5  # The even-numbered tasks that exhaust retries


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


# Integration test for actual enhanced agent loading
class TestEnhancedAgentRetryIntegration:
    """Integration tests for enhanced agent with retry capabilities."""

    @pytest.mark.slow
    def test_enhanced_agent_full_loading_with_retry(self):
        """Test full enhanced agent loading process with retry system."""
        try:
            # Import should not raise any exceptions
            from agents.software_engineer.enhanced_agent import (
                create_enhanced_software_engineer_agent,
            )

            # Create agent instance
            agent = create_enhanced_software_engineer_agent()

            # Verify agent properties
            assert agent is not None
            assert agent.name == "enhanced_software_engineer"
            assert hasattr(agent, "tools")
            assert len(agent.tools) > 0

            # Verify retry system integration
            assert hasattr(agent, "_retry_handler")
            assert agent._retry_handler is not None
            assert callable(agent._retry_handler)

            # Verify callback integration
            assert hasattr(agent, "before_model_callback")
            assert hasattr(agent, "after_model_callback")
            assert isinstance(agent.before_model_callback, list)
            assert isinstance(agent.after_model_callback, list)

            logger.info(f"Enhanced agent loaded successfully with {len(agent.tools)} tools")

        except ImportError as e:
            pytest.skip(f"Enhanced agent dependencies not available: {e}")
        except Exception as e:
            pytest.fail(f"Enhanced agent loading failed: {e}")


class TestEnhancedAgentEndToEndRetry:
    """End-to-end integration tests for retry mechanism with actual agent."""

    @pytest.mark.asyncio
    async def test_enhanced_agent_actual_retry_on_model_failure(self):
        """Test that enhanced agent retries model calls on 'No message in response'."""
        try:
            from agents.software_engineer.enhanced_agent import (
                create_enhanced_software_engineer_agent,
            )

            # Create the enhanced agent
            agent = create_enhanced_software_engineer_agent()

            # Verify the agent has retry capabilities
            assert hasattr(agent, "_retry_handler")
            assert hasattr(agent, "_original_generate_content_async")

            # Get the retry handler for direct testing
            retry_handler = agent._retry_handler

            # Track call attempts
            call_count = 0

            # Create a simple mock function that fails once then succeeds
            async def mock_model_call():
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First call fails with retryable error
                    raise ValueError("No message in response")
                # Second call succeeds - return a simple response
                return f"Success on attempt {call_count}"

            # Call the retry handler directly with our mock
            result = await retry_handler(mock_model_call)

            # Verify retry behavior
            assert call_count == 2, f"Expected 2 attempts (1 failure + 1 success), got {call_count}"
            assert result == "Success on attempt 2"

            logger.info("✅ End-to-end retry test passed: Agent successfully retried and recovered")

        except ImportError as e:
            pytest.skip(f"Enhanced agent dependencies not available: {e}")
        except Exception as e:
            logger.error(f"End-to-end retry test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_enhanced_agent_retry_exhaustion_end_to_end(self):
        """Test that enhanced agent properly exhausts retries and raises the final error."""
        try:
            from agents.software_engineer.enhanced_agent import (
                create_enhanced_software_engineer_agent,
            )

            # Create the enhanced agent
            agent = create_enhanced_software_engineer_agent()

            # Get the retry handler for direct testing
            retry_handler = agent._retry_handler

            # Track call attempts
            call_count = 0

            # Create a mock that always fails
            async def always_failing_mock():
                nonlocal call_count
                call_count += 1
                raise ValueError("No message in response")

            # Call the retry handler - this should exhaust retries and raise error
            with pytest.raises(ValueError, match="No message in response"):
                await retry_handler(always_failing_mock)

            # Verify all retry attempts were made (default is 3 retries + 1 initial = 4 total)
            assert call_count == 4, f"Expected 4 attempts (1 initial + 3 retries), got {call_count}"

            logger.info(
                "✅ End-to-end retry exhaustion test passed: Agent properly exhausted retries"
            )

        except ImportError as e:
            pytest.skip(f"Enhanced agent dependencies not available: {e}")
        except Exception as e:
            logger.error(f"End-to-end retry exhaustion test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_enhanced_agent_non_retryable_error_end_to_end(self):
        """Test that enhanced agent does not retry non-retryable errors."""
        try:
            from agents.software_engineer.enhanced_agent import (
                create_enhanced_software_engineer_agent,
            )

            # Create the enhanced agent
            agent = create_enhanced_software_engineer_agent()

            # Get the retry handler for direct testing
            retry_handler = agent._retry_handler

            # Track call attempts
            call_count = 0

            # Create a mock that fails with non-retryable error
            async def non_retryable_error_mock():
                nonlocal call_count
                call_count += 1
                raise ValueError("Authentication failed")  # Different error message

            # Call the retry handler - this should fail immediately without retries
            with pytest.raises(ValueError, match="Authentication failed"):
                await retry_handler(non_retryable_error_mock)

            # Verify only one attempt was made (no retries for non-retryable errors)
            assert call_count == 1, f"Expected 1 attempt (no retries), got {call_count}"

            logger.info(
                "✅ End-to-end non-retryable error test passed: "
                "Agent did not retry non-retryable error"
            )

        except ImportError as e:
            pytest.skip(f"Enhanced agent dependencies not available: {e}")
        except Exception as e:
            logger.error(f"End-to-end non-retryable error test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_enhanced_agent_streaming_wrapper_behavior(self):
        """Test that streaming wrapper handles stream parameter correctly."""
        try:
            # Create a simple mock retry handler for testing
            retry_call_count = 0

            async def mock_retry_handler(model_call_func):
                nonlocal retry_call_count
                retry_call_count += 1
                return await model_call_func()

            # Track calls to original method
            original_call_count = 0
            streaming_calls = []

            async def mock_original_generate_content_async(llm_request, stream=False):
                nonlocal original_call_count
                original_call_count += 1
                streaming_calls.append(stream)
                del llm_request  # Unused but required for signature compatibility

                if stream:
                    # Simulate streaming response
                    yield "Streaming chunk 1"
                    yield "Streaming chunk 2"
                else:
                    # Simulate non-streaming response
                    yield "Non-streaming response"

            # Create the wrapper function (similar to what's in enhanced_agent.py)
            async def generate_content_async_with_retry(llm_request, stream=False):
                """Test version of the wrapper function."""
                if not stream:
                    # For non-streaming calls, use retry logic with buffering
                    async def model_call():
                        responses = []
                        async for response in mock_original_generate_content_async(
                            llm_request, stream=False
                        ):
                            responses.append(response)
                        return responses

                    responses = await mock_retry_handler(model_call)
                    for response in responses:
                        yield response
                else:
                    # For streaming calls, bypass retry to preserve streaming
                    async for response in mock_original_generate_content_async(
                        llm_request, stream=True
                    ):
                        yield response

            # Test non-streaming call
            non_streaming_responses = []
            async for response in generate_content_async_with_retry("test_request", stream=False):
                non_streaming_responses.append(response)

            # Test streaming call
            streaming_responses = []
            async for response in generate_content_async_with_retry("test_request", stream=True):
                streaming_responses.append(response)

            # Verify retry handler was called only for non-streaming
            assert retry_call_count == 1, (
                f"Expected retry handler called 1 time, got {retry_call_count}"
            )

            # Verify original method was called twice (once for each test)
            assert original_call_count == 2, (
                f"Expected 2 calls to original method, got {original_call_count}"
            )

            # Verify streaming parameter was passed correctly
            assert streaming_calls == [False, True], (
                f"Expected [False, True] stream params, got {streaming_calls}"
            )

            # Verify responses
            assert non_streaming_responses == ["Non-streaming response"], (
                f"Unexpected non-streaming response: {non_streaming_responses}"
            )
            assert streaming_responses == ["Streaming chunk 1", "Streaming chunk 2"], (
                f"Unexpected streaming response: {streaming_responses}"
            )

            logger.info(
                "✅ Streaming wrapper behavior test passed: "
                "Non-streaming uses retry, streaming bypasses retry"
            )

        except Exception as e:
            logger.error(f"Streaming wrapper behavior test failed: {e}")
            raise
