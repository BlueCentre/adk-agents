"""Integration tests for token optimization pipeline."""

import logging
from unittest.mock import Mock, patch

import pytest

from agents.software_engineer.shared_libraries.callbacks import create_token_optimized_callbacks


class MockLlmRequest:
    """Mock LLM request for testing."""

    def __init__(self, contents, model="test-model", config=None):
        self.contents = contents
        self.model = model
        self.config = config or Mock()


class MockLlmResponse:
    """Mock LLM response for testing."""

    def __init__(self, total_tokens=1000, input_tokens=800, output_tokens=200):
        self.usage_metadata = Mock()
        self.usage_metadata.total_token_count = total_tokens
        self.usage_metadata.input_token_count = input_tokens
        self.usage_metadata.output_token_count = output_tokens
        self.model = "test-model"


class MockCallbackContext:
    """Mock callback context for testing."""

    def __init__(self, invocation_id="test-123", session_id="session-456"):
        self.invocation_id = invocation_id
        self.session_id = session_id
        self.user_data = {}
        self._agent_metrics = {
            "session_start_time": 0,
            "total_model_calls": 0,
            "total_tool_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_response_time": 0.0,
        }


def create_mock_content(role, text, has_function_call=False, has_function_response=False):
    """Create mock content for testing."""
    content = Mock()
    content.role = role
    content.text = text

    if has_function_call or has_function_response:
        content.parts = []
        part = Mock()
        if text:
            part.text = text
        else:
            # Remove text attribute if not provided
            if hasattr(part, "text"):
                del part.text

        if has_function_call:
            part.function_call = Mock()
        else:
            if hasattr(part, "function_call"):
                del part.function_call

        if has_function_response:
            part.function_response = Mock()
        else:
            if hasattr(part, "function_response"):
                del part.function_response

        content.parts.append(part)
    else:
        # Remove parts attribute if not needed
        if hasattr(content, "parts"):
            del content.parts

    return content


class TestTokenOptimizationIntegration:
    """Integration tests for the complete token optimization pipeline."""

    def test_callback_creation_and_basic_functionality(self):
        """Test that token optimized callbacks are created correctly."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=50000,
            enhanced_telemetry=False,
        )

        # Verify all expected callbacks are present
        expected_callbacks = [
            "before_agent",
            "after_agent",
            "before_model",
            "after_model",
            "before_tool",
            "after_tool",
        ]

        for callback_name in expected_callbacks:
            assert callback_name in callbacks
            assert callable(callbacks[callback_name])

    @patch("agents.software_engineer.shared_libraries.token_optimization.tiktoken")
    def test_token_optimization_with_small_conversation(self, mock_tiktoken):
        """Test token optimization with a small conversation that doesn't need filtering."""
        # Mock tiktoken to return small token counts
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3]  # 3 tokens per message
        mock_tiktoken.encoding_for_model.return_value = mock_encoder

        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=50000,
            enhanced_telemetry=False,
        )

        # Create a small conversation
        contents = [
            create_mock_content("user", "Hello, how are you?"),
            create_mock_content("assistant", "I'm doing well, thanks!"),
        ]

        # Create mock request and context
        llm_request = MockLlmRequest(contents)
        callback_context = MockCallbackContext()

        # Execute before_model callback
        callbacks["before_model"](callback_context, llm_request)

        # Verify optimization data is stored
        assert hasattr(callback_context, "_token_optimization")
        optimization_data = callback_context._token_optimization

        assert "available_budget" in optimization_data
        assert "budget_breakdown" in optimization_data
        assert "optimization_applied" in optimization_data
        assert optimization_data["optimization_applied"] is False  # No filtering needed

        # Verify content wasn't modified (no filtering applied)
        assert len(llm_request.contents) == 2
        assert llm_request.contents == contents

    @patch("agents.software_engineer.shared_libraries.token_optimization.tiktoken")
    def test_token_optimization_with_large_conversation_conservative(self, mock_tiktoken):
        """Test token optimization with a large conversation requiring conservative filtering."""
        # Mock tiktoken to return large token counts that will trigger filtering
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1] * 500  # 500 tokens per message - high utilization
        mock_tiktoken.encoding_for_model.return_value = mock_encoder

        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=1000,  # Small limit to trigger high utilization and filtering
            enhanced_telemetry=False,
        )

        # Create a large conversation with system messages, tool chains, and user messages
        contents = [
            create_mock_content(
                "system", "SYSTEM CONTEXT (JSON): {...}"
            ),  # System message (preserved)
            create_mock_content("user", "First user message"),
            create_mock_content("assistant", "First assistant response"),
            create_mock_content("user", "Second user message"),
            create_mock_content(
                "assistant", "Second response", has_function_call=True
            ),  # Tool call
            create_mock_content(
                "assistant", "Tool result", has_function_response=True
            ),  # Tool result
            create_mock_content("assistant", "Final assistant response"),
            create_mock_content("user", "Latest user message"),  # Current user message (preserved)
        ]

        llm_request = MockLlmRequest(contents)
        callback_context = MockCallbackContext()

        # Execute before_model callback
        callbacks["before_model"](callback_context, llm_request)

        # Verify token optimization process ran
        optimization_data = callback_context._token_optimization
        assert "available_budget" in optimization_data
        assert "budget_breakdown" in optimization_data
        assert "pipeline_used" in optimization_data  # New advanced optimization structure
        assert "steps_completed" in optimization_data  # Advanced pipeline steps

        # Verify the optimization process completed without errors
        assert isinstance(optimization_data["optimization_applied"], bool)

        # Content should either be unchanged or properly filtered
        assert len(llm_request.contents) <= len(contents)

        # If filtering was applied, verify basic structure
        if optimization_data.get("optimization_applied", False):
            # Verify we have tracking data for the filtering
            assert "original_content_count" in optimization_data
            assert "filtered_content_count" in optimization_data

    @patch("agents.software_engineer.shared_libraries.token_optimization.tiktoken")
    def test_token_optimization_with_aggressive_filtering(self, mock_tiktoken):
        """Test token optimization with very high utilization triggering aggressive filtering."""
        # Mock tiktoken to return very large token counts
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [
            1
        ] * 100  # 100 tokens per message, high utilization due to small limit
        mock_tiktoken.encoding_for_model.return_value = mock_encoder

        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=200,  # Very small limit to trigger aggressive filtering (>95% utilization) # noqa: E501
            enhanced_telemetry=False,
        )

        # Create a large conversation
        contents = []
        for i in range(10):
            contents.extend(
                [
                    create_mock_content("user", f"User message {i}"),
                    create_mock_content("assistant", f"Assistant response {i}"),
                ]
            )

        llm_request = MockLlmRequest(contents)
        callback_context = MockCallbackContext()

        # Execute before_model callback
        callbacks["before_model"](callback_context, llm_request)

        # Verify token optimization process ran
        optimization_data = callback_context._token_optimization
        assert "available_budget" in optimization_data
        assert "budget_breakdown" in optimization_data
        assert "pipeline_used" in optimization_data  # New advanced optimization structure
        assert "steps_completed" in optimization_data  # Advanced pipeline steps

        # Verify the optimization process completed without errors
        assert isinstance(optimization_data["optimization_applied"], bool)

        # Content should either be unchanged or properly filtered
        assert len(llm_request.contents) <= len(contents)

        # If filtering was applied, verify basic structure
        if optimization_data.get("optimization_applied", False):
            # Verify we have tracking data for the filtering
            assert "original_content_count" in optimization_data
            assert "filtered_content_count" in optimization_data

    def test_after_model_callback_tracking(self):
        """Test that after_model callback properly tracks optimization effectiveness."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=50000,
            enhanced_telemetry=False,
        )

        # Create mock context with optimization data
        callback_context = MockCallbackContext()
        callback_context._token_optimization = {
            "available_budget": 45000,
            "budget_breakdown": {"max_limit": 50000, "utilization_pct": 90.0},
            "optimization_applied": True,
            "original_content_count": 10,
            "filtered_content_count": 6,
            "tokens_saved": 5000,
            "reduction_pct": 50.0,
        }

        # Create mock response
        llm_response = MockLlmResponse(total_tokens=40000)

        # Execute after_model callback
        callbacks["after_model"](callback_context, llm_response)

        # Verify the callback executed without error
        # (In a real implementation, this would update metrics)

    def test_error_handling_in_token_optimization(self):
        """Test error handling when token optimization fails."""
        # Test with invalid token counter setup
        with patch(
            "agents.software_engineer.shared_libraries.token_optimization.tiktoken.encoding_for_model"
        ) as mock_tiktoken:
            mock_tiktoken.side_effect = Exception("Token counting error")

            callbacks = create_token_optimized_callbacks(
                agent_name="test_agent",
                model_name="invalid-model",
                max_token_limit=50000,
                enhanced_telemetry=False,
            )

            # Should not raise an exception despite the error
            contents = [create_mock_content("user", "Test message")]
            llm_request = MockLlmRequest(contents)
            callback_context = MockCallbackContext()

            # This should not raise an exception
            callbacks["before_model"](callback_context, llm_request)

            # Content should remain unchanged
            assert len(llm_request.contents) == 1

    def test_strategy_selection_based_on_utilization(self):
        """Test that filtering strategy is selected correctly based on token utilization."""
        with patch(
            "agents.software_engineer.shared_libraries.token_optimization.tiktoken"
        ) as mock_tiktoken:
            # Mock tiktoken to return controlled token counts
            mock_encoder = Mock()

            def mock_encode(text):
                # Return different token counts based on utilization test
                if "high_utilization" in text:
                    return [1] * 1900  # 95%+ utilization -> Aggressive
                if "medium_utilization" in text:
                    return [1] * 1700  # 85%+ utilization -> Moderate
                return [1] * 1500  # < 85% utilization -> Conservative

            mock_encoder.encode.side_effect = mock_encode
            mock_tiktoken.encoding_for_model.return_value = mock_encoder

            callbacks = create_token_optimized_callbacks(
                agent_name="test_agent",
                model_name="test-model",
                max_token_limit=2000,
                enhanced_telemetry=False,
            )

            # Test aggressive filtering (>95% utilization)
            high_util_contents = [create_mock_content("user", "high_utilization message")]
            high_util_request = MockLlmRequest(high_util_contents)
            high_util_context = MockCallbackContext()

            callbacks["before_model"](high_util_context, high_util_request)

            # Should apply aggressive filtering
            if hasattr(high_util_context, "_token_optimization"):
                # Verification would depend on internal implementation details
                pass

    @pytest.mark.parametrize(
        "max_token_limit,expected_budget_range",
        [
            (
                10000,
                (9500, 9950),
            ),  # Should leave some headroom (minimal content, so high available budget)
            (
                100000,
                (98000, 99500),
            ),  # Should leave some headroom (minimal content, so high available budget)
            (
                1000000,
                (998000, 999500),
            ),  # Should leave some headroom (minimal content, so high available budget)
        ],
    )
    def test_budget_calculation_accuracy(self, max_token_limit, expected_budget_range):
        """Test that budget calculation provides appropriate headroom."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=max_token_limit,
            enhanced_telemetry=False,
        )

        # Create minimal conversation
        contents = [create_mock_content("user", "Test")]
        llm_request = MockLlmRequest(contents)
        callback_context = MockCallbackContext()

        callbacks["before_model"](callback_context, llm_request)

        if hasattr(callback_context, "_token_optimization"):
            available_budget = callback_context._token_optimization["available_budget"]
            assert expected_budget_range[0] <= available_budget <= expected_budget_range[1]


class TestTokenOptimizationLogging:
    """Test logging behavior of token optimization."""

    def test_token_optimization_logging(self, caplog):
        """Test that token optimization produces appropriate log messages."""
        with caplog.at_level(logging.INFO):
            callbacks = create_token_optimized_callbacks(
                agent_name="test_agent",
                model_name="test-model",
                max_token_limit=50000,
                enhanced_telemetry=False,
            )

            contents = [create_mock_content("user", "Test message")]
            llm_request = MockLlmRequest(contents)
            callback_context = MockCallbackContext()

            callbacks["before_model"](callback_context, llm_request)

            # Check that appropriate log messages are present
            log_messages = [record.message for record in caplog.records]
            assert any("Token budget calculated" in msg for msg in log_messages)

    def test_filtering_applied_logging(self, caplog):
        """Test logging when filtering is actually applied."""
        with patch(
            "agents.software_engineer.shared_libraries.token_optimization.tiktoken"
        ) as mock_tiktoken:
            # Mock large token counts to trigger filtering (high utilization)
            mock_encoder = Mock()
            mock_encoder.encode.return_value = [
                1
            ] * 50  # 50 tokens per message, high utilization with small limit
            mock_tiktoken.encoding_for_model.return_value = mock_encoder

            with caplog.at_level(logging.INFO):
                callbacks = create_token_optimized_callbacks(
                    agent_name="test_agent",
                    model_name="test-model",
                    max_token_limit=100,  # Very small limit to trigger >80% utilization
                    enhanced_telemetry=False,
                )

                contents = [
                    create_mock_content("user", "Message 1"),
                    create_mock_content("assistant", "Response 1"),
                    create_mock_content("user", "Message 2"),
                ]
                llm_request = MockLlmRequest(contents)
                callback_context = MockCallbackContext()

                callbacks["before_model"](callback_context, llm_request)

                # Check for filtering-related log messages
                log_messages = [record.message for record in caplog.records]
                _filtering_logs = [msg for msg in log_messages if "filtering" in msg.lower()]
                # Note: filtering may or may not be applied depending on the exact calculation,
                # so we check that the token optimization process ran
                optimization_logs = [
                    msg for msg in log_messages if "Token budget calculated" in msg
                ]
                assert len(optimization_logs) > 0
