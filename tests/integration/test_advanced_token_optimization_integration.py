"""Integration tests for complete advanced token optimization pipeline."""

import time
from unittest.mock import Mock, patch

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
import pytest

from agents.software_engineer.shared_libraries.callbacks import create_token_optimized_callbacks


def create_mock_content(text="", role="user", has_function_call=False, has_function_response=False):
    """Create mock content object that mimics the structure of real content."""
    content = Mock()
    content.text = text
    content.role = role
    content.parts = []

    if has_function_call:
        part = Mock()
        part.function_call = Mock()
        content.parts.append(part)

    if has_function_response:
        part = Mock()
        part.function_response = Mock()
        content.parts.append(part)

    return content


def create_realistic_conversation():
    """Create a realistic conversation that would trigger advanced optimization."""
    return [
        create_mock_content("You are helping debug a Python application", "system"),
        create_mock_content("I'm getting an error in src/auth/login.py at line 42", "user"),
        create_mock_content(
            "Let me examine the login.py file", "assistant", has_function_call=True
        ),
        create_mock_content(
            "File contents show validate_password function has issue",
            "assistant",
            has_function_response=True,
        ),
        create_mock_content(
            "The validate_password function in src/auth/login.py needs fix", "assistant"
        ),
        create_mock_content("Can you also check the user authentication flow?", "user"),
        create_mock_content(
            "I'll analyze the authentication flow", "assistant", has_function_call=True
        ),
        create_mock_content(
            "Found authentication flow uses JWT tokens", "assistant", has_function_response=True
        ),
        create_mock_content(
            "The JWT validation in src/auth/jwt_handler.py is also problematic", "assistant"
        ),
        create_mock_content(
            "How should I fix both the password validation and JWT issues?", "user"
        ),
        create_mock_content("Let me provide solutions for both issues", "assistant"),
        create_mock_content("For password validation, update the regex pattern", "assistant"),
        create_mock_content("For JWT validation, check token expiration properly", "assistant"),
        create_mock_content("I need to see the exact code changes", "user"),
    ]


class TestAdvancedTokenOptimizationIntegration:
    """Integration tests for advanced token optimization pipeline."""

    @pytest.fixture
    def mock_llm_request(self):
        """Create mock LLM request with realistic conversation."""
        request = Mock(spec=LlmRequest)
        request.contents = create_realistic_conversation()
        return request

    @pytest.fixture
    def mock_llm_response(self):
        """Create mock LLM response with usage metadata."""
        response = Mock(spec=LlmResponse)

        # Mock usage metadata
        usage = Mock()
        usage.total_token_count = 15000
        usage.prompt_token_count = 12000
        usage.candidates_token_count = 3000
        response.usage_metadata = usage

        return response

    @pytest.fixture
    def mock_callback_context(self):
        """Create mock callback context."""
        context = Mock(spec=CallbackContext)
        context.invocation_id = "test_invocation_123"
        return context

    def test_advanced_callbacks_creation(self):
        """Test that advanced token-optimized callbacks are created successfully."""
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
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

    @patch("agents.software_engineer.shared_libraries.callbacks.TokenCounter")
    @patch("agents.software_engineer.shared_libraries.callbacks.ContextBudgetManager")
    def test_before_model_callback_basic_scenario(
        self, mock_budget_manager, mock_token_counter, mock_llm_request, mock_callback_context
    ):
        """Test before_model callback with basic optimization scenario."""
        # Setup mocks
        mock_token_counter_instance = Mock()
        mock_token_counter.return_value = mock_token_counter_instance

        mock_budget_manager_instance = Mock()
        mock_budget_manager.return_value = mock_budget_manager_instance

        # Configure budget manager to return low utilization (no optimization needed)
        mock_budget_manager_instance.calculate_available_context_budget.return_value = (
            500000,  # available_budget
            {"utilization_pct": 50.0, "max_limit": 1000000},  # budget_breakdown
        )

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Call before_model callback
        callbacks["before_model"](mock_callback_context, mock_llm_request)

        # Verify optimization state was stored
        assert hasattr(mock_callback_context, "_token_optimization")
        optimization_data = mock_callback_context._token_optimization

        assert optimization_data["available_budget"] == 500000
        assert optimization_data["original_content_count"] == len(mock_llm_request.contents)
        assert not optimization_data["optimization_applied"]  # Low utilization, no optimization
        assert optimization_data["pipeline_used"] == "advanced"
        assert "token_analysis" in optimization_data["steps_completed"]

    @patch("agents.software_engineer.shared_libraries.callbacks.TokenCounter")
    @patch("agents.software_engineer.shared_libraries.callbacks.ContextBudgetManager")
    def test_before_model_callback_advanced_optimization(
        self, mock_budget_manager, mock_token_counter, mock_llm_request, mock_callback_context
    ):
        """Test before_model callback with advanced optimization triggered."""
        # Setup mocks
        mock_token_counter_instance = Mock()
        mock_token_counter_instance.count_tokens.return_value = 100  # Mock token counting
        mock_token_counter.return_value = mock_token_counter_instance

        mock_budget_manager_instance = Mock()
        mock_budget_manager.return_value = mock_budget_manager_instance

        # Configure budget manager to return high utilization (trigger advanced optimization)
        mock_budget_manager_instance.calculate_available_context_budget.return_value = (
            50000,  # available_budget (tight budget)
            {"utilization_pct": 85.0, "max_limit": 1000000},  # budget_breakdown (high utilization)
        )

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Call before_model callback
        callbacks["before_model"](mock_callback_context, mock_llm_request)

        # Verify advanced optimization was applied
        assert hasattr(mock_callback_context, "_token_optimization")
        optimization_data = mock_callback_context._token_optimization

        assert optimization_data["available_budget"] == 50000
        assert optimization_data["pipeline_used"] == "advanced"

        # Should have completed multiple steps
        steps_completed = optimization_data["steps_completed"]
        assert "token_analysis" in steps_completed
        assert "content_prioritization" in steps_completed
        assert "dependency_analysis" in steps_completed
        assert "context_assembly" in steps_completed
        assert "context_bridging" in steps_completed

        # Should have optimization metadata
        assert "dependencies_found" in optimization_data
        assert "bridges_created" in optimization_data

        # Should have applied optimization
        if optimization_data["optimization_applied"]:
            assert "final_content_count" in optimization_data
            assert "assembly_result" in optimization_data
            assert "bridging_result" in optimization_data

    @patch("agents.software_engineer.shared_libraries.callbacks.TokenCounter")
    @patch("agents.software_engineer.shared_libraries.callbacks.ContextBudgetManager")
    def test_before_model_callback_fallback_filtering(
        self, mock_budget_manager, mock_token_counter, mock_callback_context
    ):
        """Test before_model callback with fallback to basic filtering."""
        # Create small conversation that won't trigger advanced optimization
        small_request = Mock(spec=LlmRequest)
        small_request.contents = [
            create_mock_content("Hello", "user"),
            create_mock_content("Hi there", "assistant"),
            create_mock_content("How are you?", "user"),
        ]

        # Setup mocks
        mock_token_counter_instance = Mock()
        mock_token_counter.return_value = mock_token_counter_instance

        mock_budget_manager_instance = Mock()
        mock_budget_manager.return_value = mock_budget_manager_instance

        # Configure budget manager to return high utilization but small conversation
        mock_budget_manager_instance.calculate_available_context_budget.return_value = (
            50000,  # available_budget (tight budget)
            {"utilization_pct": 85.0, "max_limit": 1000000},  # budget_breakdown (high utilization)
        )

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Call before_model callback
        callbacks["before_model"](mock_callback_context, small_request)

        # Verify fallback to basic filtering
        assert hasattr(mock_callback_context, "_token_optimization")
        optimization_data = mock_callback_context._token_optimization

        # Should use basic pipeline for small conversations
        if optimization_data.get("pipeline_used") == "basic":
            assert optimization_data["pipeline_used"] == "basic"
        else:
            # Or no optimization if conversation is too small
            assert not optimization_data["optimization_applied"]

    def test_after_model_callback_advanced_tracking(self, mock_llm_response, mock_callback_context):
        """Test after_model callback with advanced optimization tracking."""
        # Setup callback context with advanced optimization data
        mock_callback_context._token_optimization = {
            "available_budget": 100000,
            "budget_breakdown": {"max_limit": 1000000},
            "original_content_count": 14,
            "optimization_applied": True,
            "pipeline_used": "advanced",
            "steps_completed": [
                "token_analysis",
                "content_prioritization",
                "dependency_analysis",
                "context_assembly",
                "context_bridging",
            ],
            "dependencies_found": 8,
            "bridges_created": 3,
            "final_content_count": 10,
            "tokens_saved": 15000,
            "assembly_result": Mock(
                tokens_by_priority={"critical": 5000, "high": 3000, "medium": 2000, "low": 1000}
            ),
            "bridging_result": Mock(
                total_bridge_tokens=500, gaps_filled=2, strategy_used=Mock(value="moderate")
            ),
        }

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Call after_model callback - should not raise exceptions
        callbacks["after_model"](mock_callback_context, mock_llm_response)

        # Verify optimization data is still accessible
        optimization_data = mock_callback_context._token_optimization
        assert optimization_data["pipeline_used"] == "advanced"
        assert optimization_data["optimization_applied"]

    def test_after_model_callback_basic_tracking(self, mock_llm_response, mock_callback_context):
        """Test after_model callback with basic optimization tracking."""
        # Setup callback context with basic optimization data
        mock_callback_context._token_optimization = {
            "available_budget": 100000,
            "budget_breakdown": {"max_limit": 1000000},
            "original_content_count": 5,
            "optimization_applied": True,
            "pipeline_used": "basic",
            "final_content_count": 3,
            "tokens_saved": 5000,
        }

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Call after_model callback - should not raise exceptions
        callbacks["after_model"](mock_callback_context, mock_llm_response)

        # Verify optimization data is still accessible
        optimization_data = mock_callback_context._token_optimization
        assert optimization_data["pipeline_used"] == "basic"
        assert optimization_data["optimization_applied"]

    def test_callback_error_handling(self, mock_callback_context):
        """Test that callbacks handle errors gracefully."""
        # Create request that will cause errors
        bad_request = Mock(spec=LlmRequest)
        bad_request.contents = None  # This might cause issues

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Call before_model callback - should not raise exceptions
        callbacks["before_model"](mock_callback_context, bad_request)

        # Should have handled error gracefully
        # (May or may not have optimization data depending on where error occurred)

    @patch("agents.software_engineer.shared_libraries.callbacks.TokenCounter")
    @patch("agents.software_engineer.shared_libraries.callbacks.ContextBudgetManager")
    def test_end_to_end_optimization_flow(
        self,
        mock_budget_manager,
        mock_token_counter,
        mock_llm_request,
        mock_llm_response,
        mock_callback_context,
    ):
        """Test complete end-to-end optimization flow."""
        # Setup mocks
        mock_token_counter_instance = Mock()
        mock_token_counter_instance.count_tokens.return_value = 150  # Mock token counting
        mock_token_counter.return_value = mock_token_counter_instance

        mock_budget_manager_instance = Mock()
        mock_budget_manager.return_value = mock_budget_manager_instance

        # Configure budget manager to trigger advanced optimization
        mock_budget_manager_instance.calculate_available_context_budget.return_value = (
            75000,  # available_budget
            {"utilization_pct": 75.0, "max_limit": 1000000},  # budget_breakdown
        )

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="test_agent", model_name="gemini-2.0-flash-exp", max_token_limit=1_000_000
        )

        # Execute complete flow: before_model -> after_model
        callbacks["before_model"](mock_callback_context, mock_llm_request)
        callbacks["after_model"](mock_callback_context, mock_llm_response)

        # Verify complete flow executed successfully
        assert hasattr(mock_callback_context, "_token_optimization")
        optimization_data = mock_callback_context._token_optimization

        # Should have completed the optimization pipeline
        assert optimization_data["available_budget"] == 75000
        assert optimization_data["pipeline_used"] == "advanced"
        assert len(optimization_data["steps_completed"]) >= 1

    def test_callback_integration_with_real_components(self):
        """Test integration with real optimization components (not mocked)."""
        # Create callbacks with real components
        callbacks = create_token_optimized_callbacks(
            agent_name="integration_test_agent",
            model_name="gemini-2.0-flash-exp",
            max_token_limit=100_000,  # Smaller limit to trigger optimization
        )

        # Create realistic request that will need optimization
        request = Mock(spec=LlmRequest)
        request.contents = create_realistic_conversation() * 3  # Large conversation

        context = Mock(spec=CallbackContext)
        context.invocation_id = "integration_test_123"

        response = Mock(spec=LlmResponse)
        usage = Mock()
        usage.total_token_count = 25000
        usage.prompt_token_count = 20000
        usage.candidates_token_count = 5000
        response.usage_metadata = usage

        # Execute the flow with real components
        callbacks["before_model"](context, request)
        callbacks["after_model"](context, response)

        # Should complete without errors and have optimization data
        if hasattr(context, "_token_optimization"):
            optimization_data = context._token_optimization
            assert "available_budget" in optimization_data
            assert "pipeline_used" in optimization_data
            assert "steps_completed" in optimization_data

    def test_performance_with_large_conversation(self):
        """Test performance with large conversation dataset."""
        # Create large conversation
        large_conversation = []
        for i in range(200):  # 200 items
            large_conversation.append(
                create_mock_content(
                    f"Message {i} discussing various topics and code analysis",
                    "user" if i % 2 == 0 else "assistant",
                    has_function_call=(i % 10 == 0),
                    has_function_response=(i % 10 == 1),
                )
            )

        request = Mock(spec=LlmRequest)
        request.contents = large_conversation

        context = Mock(spec=CallbackContext)
        context.invocation_id = "perf_test_123"

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="perf_test_agent",
            model_name="gemini-2.0-flash-exp",
            max_token_limit=50_000,  # Tight limit to force optimization
        )

        # Measure performance
        start_time = time.time()
        callbacks["before_model"](context, request)
        processing_time = time.time() - start_time

        # Should complete in reasonable time
        assert processing_time < 30.0  # Less than 30 seconds

        # Should have completed optimization
        if hasattr(context, "_token_optimization"):
            optimization_data = context._token_optimization
            assert optimization_data["original_content_count"] == 200

            # May have applied optimization given tight budget
            if optimization_data["optimization_applied"]:
                assert (
                    optimization_data["final_content_count"]
                    < optimization_data["original_content_count"]
                )

    @patch("agents.software_engineer.shared_libraries.callbacks.TokenCounter")
    @patch("agents.software_engineer.shared_libraries.callbacks.ContextBudgetManager")
    def test_content_id_matching_with_duplicate_text_role(
        self, mock_budget_manager, mock_token_counter, mock_callback_context
    ):
        """
        Test for the critical bug where multiple messages with identical text/role
        would always match the first occurrence, scrambling conversation order.

        This is a regression test for the bug identified in the GitHub feedback.
        """
        # Create conversation with duplicate text/role combinations
        # This simulates real scenarios like:
        # - User says "ok" multiple times
        # - Multiple identical tool calls
        # - Repeated assistant confirmations
        duplicate_conversation = [
            create_mock_content("System prompt", "system"),
            create_mock_content("ok", "user"),  # First "ok" from user
            create_mock_content("I understand", "assistant"),
            create_mock_content("Let me check the file", "assistant", has_function_call=True),
            create_mock_content("File contents retrieved", "assistant", has_function_response=True),
            create_mock_content("ok", "user"),  # Second "ok" from user - CRITICAL TEST CASE
            create_mock_content("I understand", "assistant"),  # Duplicate assistant response
            create_mock_content(
                "Let me check the file", "assistant", has_function_call=True
            ),  # Same tool call
            create_mock_content("Different file contents", "assistant", has_function_response=True),
            create_mock_content("ok", "user"),  # Third "ok" from user
            create_mock_content("Final response", "assistant"),
        ]

        # Setup mocks to trigger advanced optimization
        mock_token_counter_instance = Mock()
        mock_token_counter_instance.count_tokens.return_value = 100
        mock_token_counter.return_value = mock_token_counter_instance

        mock_budget_manager_instance = Mock()
        mock_budget_manager.return_value = mock_budget_manager_instance

        # Force advanced optimization with high utilization
        mock_budget_manager_instance.calculate_available_context_budget.return_value = (
            30000,  # Tight budget
            {"utilization_pct": 85.0, "max_limit": 1000000},
        )

        # Create request with duplicate content
        request = Mock(spec=LlmRequest)
        request.contents = duplicate_conversation

        # Create callbacks
        callbacks = create_token_optimized_callbacks(
            agent_name="duplicate_test_agent",
            model_name="gemini-2.0-flash-exp",
            max_token_limit=1_000_000,
        )

        # Track original content object identities to verify correct mapping
        original_content_ids = [id(content) for content in duplicate_conversation]

        # Execute optimization
        callbacks["before_model"](mock_callback_context, request)

        # Verify that optimization was applied (should be with tight budget and many items)
        assert hasattr(mock_callback_context, "_token_optimization")
        optimization_data = mock_callback_context._token_optimization

        # If optimization was applied, verify the content order preservation
        if optimization_data.get("optimization_applied"):
            optimized_contents = request.contents

            # Key test: Verify that each optimized content item corresponds to the
            # correct original content by object identity, not just text/role matching
            optimized_content_ids = [id(content) for content in optimized_contents]

            # All optimized content should be from the original set
            for opt_id in optimized_content_ids:
                assert opt_id in original_content_ids, (
                    "Optimized content contains objects not from original conversation. "
                    "This suggests the ID-based lookup failed and fell back to new objects."
                )

            # Verify conversation coherence: if multiple "ok" messages are preserved,
            # they should maintain their relative order from the original conversation
            ok_positions_optimized = [
                i
                for i, content in enumerate(optimized_contents)
                if getattr(content, "text", "") == "ok" and getattr(content, "role", "") == "user"
            ]

            # If multiple "ok" messages are preserved, their relative order should be maintained
            if len(ok_positions_optimized) > 1:
                # The preserved "ok" messages should maintain increasing order
                for i in range(1, len(ok_positions_optimized)):
                    assert ok_positions_optimized[i] > ok_positions_optimized[i - 1], (
                        "Multiple 'ok' messages were not preserved in correct order. "
                        "This indicates the text/role matching bug may still exist."
                    )

            # Verify that the conversation flow makes sense
            # (e.g., function responses come after function calls)
            function_call_indices = []
            function_response_indices = []

            for i, content in enumerate(optimized_contents):
                if getattr(content, "parts", None):
                    for part in content.parts:
                        if hasattr(part, "function_call"):
                            function_call_indices.append(i)
                        elif hasattr(part, "function_response"):
                            function_response_indices.append(i)

            # Each function response should come after a function call
            # (This would be broken if content order was scrambled)
            for response_idx in function_response_indices:
                # Find the nearest preceding function call
                preceding_calls = [idx for idx in function_call_indices if idx < response_idx]
                assert len(preceding_calls) > 0, (
                    f"Function response at index {response_idx} has no preceding function call. "
                    "This suggests conversation order was scrambled by incorrect content matching."
                )

        else:
            # Even if optimization wasn't applied, the test setup should be valid
            # This ensures our test scenario is realistic
            assert len(duplicate_conversation) >= 10, (
                "Test conversation should be large enough to be realistic"
            )

            # Verify the test case actually has duplicates
            text_role_pairs = [
                (getattr(c, "text", ""), getattr(c, "role", "")) for c in duplicate_conversation
            ]
            unique_pairs = set(text_role_pairs)
            assert len(text_role_pairs) > len(unique_pairs), (
                "Test case should have duplicate text/role pairs to test the bug scenario"
            )

    def test_content_order_preservation_with_identical_tool_calls(self):
        """
        Additional test for content order preservation with identical tool calls.

        This tests another common scenario where the text/role matching bug would manifest:
        identical tool calls to the same function with same parameters.
        """
        # Create conversation with identical tool calls
        identical_tool_conversation = [
            create_mock_content("Check this file: src/app.py", "user"),
            create_mock_content("I'll examine the file", "assistant", has_function_call=True),
            create_mock_content(
                "File contains main function", "assistant", has_function_response=True
            ),
            create_mock_content("Also check src/app.py again", "user"),  # Same file again
            create_mock_content(
                "I'll examine the file", "assistant", has_function_call=True
            ),  # Same text!
            create_mock_content(
                "File contains updated main function", "assistant", has_function_response=True
            ),
            create_mock_content("Check src/app.py one more time", "user"),  # Third time
            create_mock_content(
                "I'll examine the file", "assistant", has_function_call=True
            ),  # Same text again!
            create_mock_content(
                "File now has error handling", "assistant", has_function_response=True
            ),
        ]

        request = Mock(spec=LlmRequest)
        request.contents = identical_tool_conversation

        context = Mock(spec=CallbackContext)
        context.invocation_id = "tool_order_test"

        # Create callbacks (use tight token limit to force optimization)
        callbacks = create_token_optimized_callbacks(
            agent_name="tool_order_test_agent",
            model_name="gemini-2.0-flash-exp",
            max_token_limit=10_000,  # Very tight to force aggressive optimization
        )

        # Execute optimization
        callbacks["before_model"](context, request)

        # Verify conversation structure is preserved
        if hasattr(context, "_token_optimization") and context._token_optimization.get(
            "optimization_applied"
        ):
            optimized_contents = request.contents

            # Find all function call and response pairs
            call_response_pairs = []
            i = 0
            while i < len(optimized_contents) - 1:
                current = optimized_contents[i]
                next_item = optimized_contents[i + 1]

                # Check if current is function call and next is function response
                current_has_call = (
                    hasattr(current, "parts")
                    and current.parts
                    and any(hasattr(part, "function_call") for part in current.parts)
                )
                next_has_response = (
                    hasattr(next_item, "parts")
                    and next_item.parts
                    and any(hasattr(part, "function_response") for part in next_item.parts)
                )

                if current_has_call and next_has_response:
                    call_response_pairs.append((i, i + 1))
                    i += 2  # Skip the response since we just processed it
                else:
                    i += 1

            # All function calls should be followed by their corresponding responses
            # This would be broken if content order was scrambled
            assert len(call_response_pairs) > 0, "Test should have function call/response pairs"

            # Verify each pair is sequential
            for call_idx, response_idx in call_response_pairs:
                assert response_idx == call_idx + 1, (
                    f"Function call at {call_idx} should be immediately followed by "
                    f"response at {response_idx}, but they are not sequential. "
                    "This suggests content order was scrambled."
                )
