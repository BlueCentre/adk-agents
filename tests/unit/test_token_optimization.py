"""Unit tests for token optimization functionality."""

from unittest.mock import Mock, patch

from google import genai
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import CountTokensResponse

from agents.software_engineer.shared_libraries.callbacks import (
    create_token_optimized_callbacks,
)
from agents.software_engineer.shared_libraries.token_optimization import (
    ContextBudgetManager,
    TokenCounter,
    _token_counting_error_handler,
)


class TestTokenCounter:
    """Test cases for TokenCounter class."""

    def test_init_with_model_name(self):
        """Test TokenCounter initialization with model name."""
        counter = TokenCounter("gemini-2.0-flash")
        assert counter.model_name == "gemini-2.0-flash"
        assert counter.llm_client is None

    def test_init_with_client(self):
        """Test TokenCounter initialization with client."""
        mock_client = Mock(spec=genai.Client)
        counter = TokenCounter("gemini-2.0-flash", mock_client)
        assert counter.model_name == "gemini-2.0-flash"
        assert counter.llm_client == mock_client

    def test_character_count_fallback(self):
        """Test character count fallback strategy."""
        counter = TokenCounter("unknown-model")

        # Test normal text
        result = counter.count_tokens("Hello world")
        assert result == len("Hello world") // 4

        # Test empty text
        assert counter.count_tokens("") == 0

        # Test None conversion
        assert counter.count_tokens(None) == 0

    def test_count_tokens_with_non_string_input(self):
        """Test count_tokens handles non-string input gracefully."""
        counter = TokenCounter("test-model")

        # Test integer input - str(123) = "123", tiktoken encodes this as 1 token
        result = counter.count_tokens(123)
        assert result >= 0  # Token count should be non-negative
        assert isinstance(result, int)

        # Test dict input
        result = counter.count_tokens({"test": "value"})
        assert isinstance(result, int)
        assert result >= 0

    @patch("agents.software_engineer.shared_libraries.token_optimization.TIKTOKEN_AVAILABLE", True)
    @patch("tiktoken.encoding_for_model")
    def test_tiktoken_strategy_selection(self, mock_encoding_for_model):
        """Test tiktoken strategy selection when available."""
        mock_tokenizer = Mock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4]  # 4 tokens
        mock_encoding_for_model.return_value = mock_tokenizer

        counter = TokenCounter("gpt-4")
        # The init should have selected tiktoken strategy
        result = counter.count_tokens("test text")
        assert result == 4  # Should use tiktoken

    @patch("agents.software_engineer.shared_libraries.token_optimization.TIKTOKEN_AVAILABLE", True)
    @patch("tiktoken.encoding_for_model")
    @patch("tiktoken.get_encoding")
    def test_tiktoken_fallback_to_cl100k_base(self, mock_get_encoding, mock_encoding_for_model):
        """Test tiktoken fallback to cl100k_base when model-specific encoding not found."""
        mock_encoding_for_model.side_effect = KeyError("Model not found")
        mock_tokenizer = Mock()
        mock_tokenizer.encode.return_value = [1, 2, 3]  # 3 tokens
        mock_get_encoding.return_value = mock_tokenizer

        counter = TokenCounter("unknown-model")
        result = counter.count_tokens("test")
        assert result == 3

    def test_native_google_counter_not_available(self):
        """Test when native Google counter is not available."""
        # Test with None client
        counter = TokenCounter("gemini-2.0-flash", None)
        assert not counter._try_native_google_counter()

        # Test with invalid client
        mock_client = Mock()
        del mock_client.models  # Remove models attribute
        counter = TokenCounter("gemini-2.0-flash", mock_client)
        assert not counter._try_native_google_counter()

    def test_native_google_counter_available(self):
        """Test when native Google counter is available."""
        mock_client = Mock(spec=genai.Client)
        mock_response = Mock(spec=CountTokensResponse)
        mock_response.total_tokens = 5
        mock_client.models.count_tokens.return_value = mock_response

        counter = TokenCounter("gemini-2.0-flash", mock_client)

        # Test that it recognizes the counter as available
        assert counter._try_native_google_counter()

    def test_count_llm_request_tokens_basic(self):
        """Test basic LLM request token counting."""
        counter = TokenCounter("test-model")

        # Mock LLM request
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "You are a helpful assistant"
        mock_request.tools = ["tool1", "tool2"]
        mock_request.contents = []

        result = counter.count_llm_request_tokens(mock_request)

        assert isinstance(result, dict)
        assert "system_instruction" in result
        assert "tools" in result
        assert "user_message" in result
        assert "conversation_history" in result
        assert "total" in result
        assert result["total"] >= 0

    def test_count_llm_request_tokens_with_contents(self):
        """Test LLM request token counting with conversation contents."""
        counter = TokenCounter("test-model")

        # Create mock content structure
        mock_part = Mock()
        mock_part.text = "Hello, how can I help you?"

        mock_content = Mock()
        mock_content.role = "user"
        mock_content.parts = [mock_part]

        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "System prompt"
        mock_request.tools = None
        mock_request.contents = [mock_content]

        result = counter.count_llm_request_tokens(mock_request)

        assert result["conversation_history"] > 0
        assert result["user_message"] > 0
        assert result["total"] > 0

    def test_count_llm_request_tokens_error_handling(self):
        """Test error handling in LLM request token counting."""
        counter = TokenCounter("test-model")

        # Mock request that will cause errors
        mock_request = Mock()
        mock_request.system_instruction = None
        del mock_request.tools  # Remove attribute to cause AttributeError

        result = counter.count_llm_request_tokens(mock_request)

        # Should return default structure even with errors
        assert isinstance(result, dict)
        assert all(isinstance(v, int) for v in result.values())


class TestContextBudgetManager:
    """Test cases for ContextBudgetManager class."""

    def test_init_default_limit(self):
        """Test ContextBudgetManager initialization with default limit."""
        manager = ContextBudgetManager()
        assert manager.max_token_limit == 1_000_000

    def test_init_custom_limit(self):
        """Test ContextBudgetManager initialization with custom limit."""
        manager = ContextBudgetManager(500_000)
        assert manager.max_token_limit == 500_000

    def test_determine_safety_margin_large_capacity(self):
        """Test safety margin calculation with large remaining capacity."""
        manager = ContextBudgetManager(1_000_000)
        base_tokens = 50_000  # Leaves 950k remaining

        margin = manager.determine_safety_margin(base_tokens)
        assert margin == 2000

    def test_determine_safety_margin_moderate_capacity(self):
        """Test safety margin calculation with moderate remaining capacity."""
        manager = ContextBudgetManager(100_000)
        base_tokens = 40_000  # Leaves 60k remaining

        margin = manager.determine_safety_margin(base_tokens)
        assert margin == 1000

    def test_determine_safety_margin_tight_capacity(self):
        """Test safety margin calculation with tight remaining capacity."""
        manager = ContextBudgetManager(50_000)
        base_tokens = 35_000  # Leaves 15k remaining

        margin = manager.determine_safety_margin(base_tokens)
        assert margin == 500

    def test_determine_safety_margin_very_tight_capacity(self):
        """Test safety margin calculation with very tight remaining capacity."""
        manager = ContextBudgetManager(10_000)
        base_tokens = 8_000  # Leaves 2k remaining

        margin = manager.determine_safety_margin(base_tokens)
        assert margin == 200

    def test_determine_safety_margin_emergency_capacity(self):
        """Test safety margin calculation with emergency remaining capacity."""
        manager = ContextBudgetManager(5_000)
        base_tokens = 4_500  # Leaves 500 remaining

        margin = manager.determine_safety_margin(base_tokens)
        assert margin == 50

    def test_calculate_base_prompt_tokens(self):
        """Test base prompt token calculation."""
        manager = ContextBudgetManager()
        counter = TokenCounter("test-model")

        # Create mock request
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "System prompt"
        mock_request.tools = ["tool1"]
        mock_request.contents = []

        base_tokens = manager.calculate_base_prompt_tokens(mock_request, counter)
        assert isinstance(base_tokens, int)
        assert base_tokens >= 0

    def test_calculate_available_context_budget(self):
        """Test available context budget calculation."""
        manager = ContextBudgetManager(100_000)
        counter = TokenCounter("test-model")

        # Create simple mock request
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "System"
        mock_request.tools = None
        mock_request.contents = []

        budget, breakdown = manager.calculate_available_context_budget(mock_request, counter)

        assert isinstance(budget, int)
        assert budget >= 0
        assert isinstance(breakdown, dict)
        assert "max_limit" in breakdown
        assert "base_tokens" in breakdown
        assert "safety_margin" in breakdown
        assert "available_budget" in breakdown
        assert "utilization_pct" in breakdown
        assert breakdown["max_limit"] == 100_000

    def test_calculate_available_context_budget_negative_budget(self):
        """Test available context budget calculation when budget would be negative."""
        manager = ContextBudgetManager(1_000)  # Very small limit
        counter = TokenCounter("test-model")

        # Create request that would exceed limit
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "Very long system instruction " * 100
        mock_request.tools = ["tool"] * 100
        mock_request.contents = []

        budget, breakdown = manager.calculate_available_context_budget(mock_request, counter)

        # Budget should be 0 when it would be negative
        assert budget >= 0
        assert breakdown["available_budget"] >= 0


class TestTokenCountingErrorHandler:
    """Test cases for token counting error handler decorator."""

    def test_error_handler_with_string_arg(self):
        """Test error handler with string argument for fallback."""

        @_token_counting_error_handler
        def failing_function(_self, _text: str) -> int:
            raise ValueError("Test error")

        test_text = "test text"
        result = failing_function(None, test_text)
        assert result == len(test_text) // 4

    def test_error_handler_without_string_arg(self):
        """Test error handler without string argument."""

        @_token_counting_error_handler
        def failing_function(_self, _number: int) -> int:
            raise ValueError("Test error")

        result = failing_function(None, 123)
        assert result == 0

    def test_error_handler_success_case(self):
        """Test error handler when function succeeds."""

        @_token_counting_error_handler
        def working_function(_self, _text: str) -> int:
            return 42

        result = working_function(None, "test")
        assert result == 42


class TestIntegration:
    """Integration tests for token optimization components."""

    def test_token_counter_and_budget_manager_integration(self):
        """Test integration between TokenCounter and ContextBudgetManager."""
        counter = TokenCounter("test-model")
        manager = ContextBudgetManager(50_000)

        # Create realistic mock request
        mock_part = Mock()
        mock_part.text = "What is the weather like today?"

        mock_content = Mock()
        mock_content.role = "user"
        mock_content.parts = [mock_part]

        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "You are a helpful weather assistant."
        mock_request.tools = ["get_weather", "get_forecast"]
        mock_request.contents = [mock_content]

        # Test the integration
        budget, breakdown = manager.calculate_available_context_budget(mock_request, counter)

        assert isinstance(budget, int)
        assert budget >= 0
        assert budget < manager.max_token_limit
        assert breakdown["base_tokens"] > 0
        assert breakdown["safety_margin"] > 0
        assert breakdown["utilization_pct"] > 0


class TestTokenOptimizedCallbacks:
    """Test cases for token optimized callback factory."""

    def test_create_token_optimized_callbacks_basic(self):
        """Test basic creation of token optimized callbacks."""
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

    def test_token_optimized_before_model_callback(self):
        """Test token optimized before_model callback functionality."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=50000,
            enhanced_telemetry=False,
        )

        # Create mock callback context
        mock_context = Mock()
        mock_context.invocation_id = "test_inv_123"

        # Create mock LLM request
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "System prompt"
        mock_request.tools = None
        mock_request.contents = []

        # Call the before_model callback
        callbacks["before_model"](mock_context, mock_request)

        # Verify optimization state was stored
        assert hasattr(mock_context, "_token_optimization")
        optimization_data = mock_context._token_optimization

        assert "available_budget" in optimization_data
        assert "budget_breakdown" in optimization_data
        assert "pipeline_used" in optimization_data  # New advanced optimization structure
        assert "steps_completed" in optimization_data  # Advanced pipeline steps
        assert "optimization_applied" in optimization_data
        assert "original_content_count" in optimization_data

        # Verify advanced optimization structure
        assert optimization_data["pipeline_used"] in ["advanced", "basic"]
        assert isinstance(optimization_data["available_budget"], int)
        assert optimization_data["available_budget"] >= 0

    def test_token_optimized_after_model_callback(self):
        """Test token optimized after_model callback functionality."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=50000,
            enhanced_telemetry=False,
        )

        # Create mock callback context with optimization data
        mock_context = Mock()
        mock_context.invocation_id = "test_inv_123"
        mock_context._token_optimization = {
            "available_budget": 10000,
            "budget_breakdown": {"max_limit": 50000},
            "optimization_applied": False,
        }

        # Create mock LLM response
        mock_response = Mock(spec=LlmResponse)
        mock_usage = Mock()
        mock_usage.total_token_count = 5000
        mock_response.usage_metadata = mock_usage

        # Call the after_model callback
        callbacks["after_model"](mock_context, mock_response)

        # Verify the callback completed without errors
        # (main functionality is logging, so we just verify no exceptions)
        assert mock_context._token_optimization is not None

    def test_token_optimized_callbacks_error_handling(self):
        """Test error handling in token optimized callbacks."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=50000,
            enhanced_telemetry=False,
        )

        # Test with None callback context
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "Test"
        mock_request.tools = None
        mock_request.contents = []

        # Should not raise exception even with None context
        callbacks["before_model"](None, mock_request)

        # Test with malformed request
        mock_context = Mock()
        mock_context.invocation_id = "test_inv"

        malformed_request = Mock()
        del malformed_request.system_instruction  # Remove required attribute

        # Should handle error gracefully
        callbacks["before_model"](mock_context, malformed_request)

    def test_token_optimized_callbacks_with_enhanced_telemetry(self):
        """Test token optimized callbacks with enhanced telemetry enabled."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent",
            model_name="test-model",
            max_token_limit=100000,
            enhanced_telemetry=True,
        )

        # Verify callbacks are created successfully
        assert len(callbacks) == 6
        assert all(callable(cb) for cb in callbacks.values())

        # Test that enhanced telemetry doesn't break functionality
        mock_context = Mock()
        mock_context.invocation_id = "test_enhanced"

        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "Enhanced test"
        mock_request.tools = []
        mock_request.contents = []

        callbacks["before_model"](mock_context, mock_request)

        # Should still have optimization data
        assert hasattr(mock_context, "_token_optimization")

    def test_integration_with_base_callbacks(self):
        """Test integration with base telemetry callbacks."""
        callbacks = create_token_optimized_callbacks(
            agent_name="integration_test",
            model_name="test-model",
            max_token_limit=75000,
            enhanced_telemetry=False,
        )

        # Create test scenario that would trigger both base and optimized callbacks
        mock_context = Mock()
        mock_context.invocation_id = "integration_test_123"
        mock_context.session_id = "session_456"

        # Test before_agent callback (should be from base callbacks)
        callbacks["before_agent"](mock_context)

        # Test before_model callback (should be optimized)
        mock_request = Mock(spec=LlmRequest)
        mock_request.system_instruction = "Integration test prompt"
        mock_request.tools = ["test_tool"]
        mock_request.contents = []

        callbacks["before_model"](mock_context, mock_request)

        # Verify optimization state exists (from optimized callback)
        assert hasattr(mock_context, "_token_optimization")

        # Test after_model callback (should be optimized)
        mock_response = Mock(spec=LlmResponse)
        mock_usage = Mock()
        mock_usage.total_token_count = 2500
        mock_response.usage_metadata = mock_usage

        callbacks["after_model"](mock_context, mock_response)

        # Test after_agent callback (should be from base callbacks)
        callbacks["after_agent"](mock_context)
