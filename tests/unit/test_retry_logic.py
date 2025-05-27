#!/usr/bin/env python3
"""
Unit tests for retry logic and error classification.

Tests the retry mechanisms, error classification, and context optimization
strategies implemented in the DevOps agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import mock agent for testing (avoiding full devops_agent dependencies)
from tests.fixtures.test_helpers import create_mock_agent


class TestErrorClassification:
    """Test cases for error classification logic."""
    
    def setup_method(self):
        """Set up a mock agent for testing."""
        self.agent = create_mock_agent(name="test_agent", model="test_model")
    
    def test_retryable_api_errors(self):
        """Test that API rate limiting and quota errors are retryable."""
        retryable_errors = [
            ("429 RESOURCE_EXHAUSTED", "RateLimitError"),
            ("quota exceeded", "QuotaError"),
            ("rate limit", "APIError"),
            ("RESOURCE_EXHAUSTED: quota", "GoogleAPIError")
        ]
        
        for error_message, error_type in retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is True
    
    def test_retryable_server_errors(self):
        """Test that temporary server errors are retryable."""
        retryable_errors = [
            ("500 Internal Server Error", "ServerError"),
            ("502 Bad Gateway", "HTTPError"),
            ("503 Service Unavailable", "ServiceError"),
            ("504 Gateway Timeout", "TimeoutError"),
            ("INTERNAL server error", "GoogleAPIError"),
            ("ServerError occurred", "APIError"),
            ("timeout waiting for response", "TimeoutError")
        ]
        
        for error_message, error_type in retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is True
    
    def test_retryable_network_errors(self):
        """Test that network and connection errors are retryable."""
        retryable_errors = [
            ("connection failed", "ConnectionError"),
            ("network unreachable", "NetworkError"),
            ("timeout connecting", "TimeoutError"),
            ("connection reset", "ConnectionResetError")
        ]
        
        for error_message, error_type in retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is True
    
    def test_retryable_json_errors(self):
        """Test that JSON parsing errors are retryable."""
        retryable_errors = [
            ("Invalid JSON response", "JSONDecodeError"),
            ("json parsing failed", "ValueError"),
            ("malformed json", "JSONError")
        ]
        
        for error_message, error_type in retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is True
    
    def test_retryable_token_errors(self):
        """Test that token limit errors are retryable."""
        retryable_errors = [
            ("token limit exceeded", "TokenLimitError"),
            ("context length too long", "ContextError"),
            ("maximum context reached", "LimitError"),
            ("too many tokens", "TokenError")
        ]
        
        for error_message, error_type in retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is True
    
    def test_retryable_google_api_errors(self):
        """Test that specific Google API errors are retryable."""
        retryable_errors = [
            ("DEADLINE_EXCEEDED", "GoogleAPIError"),
            ("UNAVAILABLE service", "GoogleAPIError"),
            ("ABORTED operation", "GoogleAPIError")
        ]
        
        for error_message, error_type in retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is True
    
    def test_non_retryable_auth_errors(self):
        """Test that authentication and authorization errors are not retryable."""
        non_retryable_errors = [
            ("PERMISSION_DENIED", "AuthError"),
            ("UNAUTHENTICATED request", "AuthError"),
            ("invalid api key", "AuthenticationError"),
            ("authentication failed", "AuthError"),
            ("authorization denied", "AuthError")
        ]
        
        for error_message, error_type in non_retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is False
    
    def test_non_retryable_validation_errors(self):
        """Test that validation and argument errors are not retryable."""
        non_retryable_errors = [
            ("INVALID_ARGUMENT provided", "ValidationError"),
            ("NOT_FOUND resource", "NotFoundError"),
            ("ALREADY_EXISTS entity", "ConflictError"),
            ("FAILED_PRECONDITION", "PreconditionError"),
            ("model not found", "ModelError"),
            ("unsupported operation", "UnsupportedError")
        ]
        
        for error_message, error_type in non_retryable_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is False
    
    def test_unknown_errors_non_retryable(self):
        """Test that unknown errors default to non-retryable."""
        unknown_errors = [
            ("some random error", "UnknownError"),
            ("mysterious failure", "WeirdError"),
            ("unexpected issue", "CustomError")
        ]
        
        for error_message, error_type in unknown_errors:
            assert self.agent._is_retryable_error(error_message, error_type) is False


class TestContextOptimization:
    """Test cases for context optimization during retries."""
    
    def setup_method(self):
        """Set up a mock agent with state manager for testing."""
        self.agent = create_mock_agent(name="test_agent", model="test_model")
        # Initialize state manager
        self.agent._state_manager.start_new_turn("Test message")
        
        # Add some conversation history
        for i in range(5):
            turn = self.agent._state_manager.start_new_turn(f"Message {i}")
            turn.agent_message = f"Response {i}"
            self.agent._state_manager.complete_current_turn()
        
        # Add code snippets to app state
        self.agent._state_manager.app_state['code_snippets'] = [
            {'file_path': f'file{i}.py', 'code': f'code snippet {i}'}
            for i in range(10)
        ]
        
        # Start a current turn
        self.agent._state_manager.start_new_turn("Current message")
        for i in range(3):
            self.agent._state_manager.add_tool_result(f"tool{i}", f"result{i}")
    
    @pytest.mark.asyncio
    async def test_optimization_level_1(self):
        """Test first level optimization (moderate reduction)."""
        # Mock context to simulate invocation context
        mock_ctx = Mock()
        mock_ctx.state = self.agent._state_manager.get_state_for_context()
        
        # Test level 1 optimization
        success = await self.agent._optimize_input_for_retry(mock_ctx, 1)
        
        assert success is True
        # Should reduce conversation history to 2 turns
        assert len(self.agent._state_manager.conversation_history) <= 2
        # Should reduce code snippets to 3
        assert len(self.agent._state_manager.app_state['code_snippets']) <= 3
    
    @pytest.mark.asyncio
    async def test_optimization_level_2(self):
        """Test second level optimization (aggressive reduction)."""
        mock_ctx = Mock()
        mock_ctx.state = self.agent._state_manager.get_state_for_context()
        
        # Test level 2 optimization
        success = await self.agent._optimize_input_for_retry(mock_ctx, 2)
        
        assert success is True
        # Should reduce conversation history to 1 turn
        assert len(self.agent._state_manager.conversation_history) <= 1
        # Should remove all code snippets
        assert len(self.agent._state_manager.app_state['code_snippets']) == 0
        # Should remove tool results from current turn
        if self.agent._state_manager.current_turn:
            assert len(self.agent._state_manager.current_turn.tool_results) == 0
    
    @pytest.mark.asyncio
    async def test_optimization_level_3_plus(self):
        """Test third+ level optimization (minimal context)."""
        mock_ctx = Mock()
        mock_ctx.state = self.agent._state_manager.get_state_for_context()
        
        # Test level 3+ optimization
        success = await self.agent._optimize_input_for_retry(mock_ctx, 3)
        
        assert success is True
        # Should clear conversation history
        assert len(self.agent._state_manager.conversation_history) == 0
        # Should clear all app state
        assert len(self.agent._state_manager.app_state['code_snippets']) == 0
        assert self.agent._state_manager.app_state['core_goal'] == ''
        assert len(self.agent._state_manager.app_state['key_decisions']) == 0
        # Should keep only user message in current turn
        if self.agent._state_manager.current_turn:
            assert self.agent._state_manager.current_turn.user_message is not None
            assert self.agent._state_manager.current_turn.turn_number == 1
    
    @pytest.mark.asyncio
    async def test_context_manager_optimization(self):
        """Test that context manager limits are also adjusted."""
        # Mock context manager
        mock_context_manager = Mock()
        mock_context_manager.target_recent_turns = 10
        mock_context_manager.target_code_snippets = 10
        mock_context_manager.target_tool_results = 10
        self.agent._context_manager = mock_context_manager
        
        mock_ctx = Mock()
        mock_ctx.state = {}
        
        # Test level 1 optimization
        await self.agent._optimize_input_for_retry(mock_ctx, 1)
        
        assert mock_context_manager.target_recent_turns <= 2
        assert mock_context_manager.target_code_snippets <= 3
        assert mock_context_manager.target_tool_results <= 3
    
    @pytest.mark.asyncio
    async def test_optimization_error_handling(self):
        """Test that optimization handles errors gracefully."""
        # Mock state manager to raise an exception
        with patch.object(self.agent._state_manager, 'sync_from_legacy_state', side_effect=Exception("test error")):
            mock_ctx = Mock()
            mock_ctx.state = {}
            
            success = await self.agent._optimize_input_for_retry(mock_ctx, 1)
            
            # Should return False but not raise exception
            assert success is False
    
    @pytest.mark.asyncio
    async def test_optimization_without_state_manager(self):
        """Test optimization when state manager is not available."""
        # Remove state manager
        self.agent._state_manager = None
        
        mock_ctx = Mock()
        mock_ctx.state = {}
        
        success = await self.agent._optimize_input_for_retry(mock_ctx, 1)
        
        # Should return False gracefully
        assert success is False


class TestRetryMechanism:
    """Test cases for the overall retry mechanism."""
    
    def setup_method(self):
        """Set up a mock agent for testing."""
        self.agent = create_mock_agent(name="test_agent", model="test_model")
    
    @pytest.mark.asyncio
    async def test_retry_with_retryable_error(self):
        """Test that retryable errors trigger retry logic."""
        # Mock the super()._run_async_impl to raise a retryable error
        with patch.object(self.agent.__class__.__bases__[0], '_run_async_impl') as mock_super:
            # First call raises retryable error, second succeeds
            mock_super.side_effect = [
                Exception("429 RESOURCE_EXHAUSTED"),
                AsyncMock(return_value=iter([]))()  # Empty async generator
            ]
            
            # Mock optimization
            with patch.object(self.agent, '_optimize_input_for_retry', return_value=True):
                # Mock sleep to speed up test
                with patch('asyncio.sleep'):
                    mock_ctx = Mock()
                    
                    # Should not raise exception, should retry
                    events = []
                    async for event in self.agent._run_async_impl(mock_ctx):
                        events.append(event)
                    
                    # Should have called super twice (original + 1 retry)
                    assert mock_super.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_with_non_retryable_error(self):
        """Test that non-retryable errors don't trigger retry."""
        # Mock the super()._run_async_impl to raise a non-retryable error
        with patch.object(self.agent.__class__.__bases__[0], '_run_async_impl') as mock_super:
            mock_super.side_effect = Exception("PERMISSION_DENIED")
            
            mock_ctx = Mock()
            
            # Should yield error event and end
            events = []
            async for event in self.agent._run_async_impl(mock_ctx):
                events.append(event)
            
            # Should have called super only once (no retry)
            assert mock_super.call_count == 1
            # Should have yielded an error event
            assert len(events) == 1
            assert "internal issue" in events[0].content.parts[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        # Mock the super()._run_async_impl to always raise retryable error
        with patch.object(self.agent.__class__.__bases__[0], '_run_async_impl') as mock_super:
            mock_super.side_effect = Exception("429 RESOURCE_EXHAUSTED")
            
            # Mock optimization
            with patch.object(self.agent, '_optimize_input_for_retry', return_value=True):
                # Mock sleep to speed up test
                with patch('asyncio.sleep'):
                    mock_ctx = Mock()
                    
                    events = []
                    async for event in self.agent._run_async_impl(mock_ctx):
                        events.append(event)
                    
                    # Should have called super 4 times (original + 3 retries)
                    assert mock_super.call_count == 4
                    # Should yield error event after max retries
                    assert len(events) == 1
    
    @pytest.mark.asyncio
    async def test_consecutive_error_limit(self):
        """Test that consecutive error limit prevents infinite loops."""
        # Mock the super()._run_async_impl to always raise errors
        with patch.object(self.agent.__class__.__bases__[0], '_run_async_impl') as mock_super:
            mock_super.side_effect = Exception("500 Internal Server Error")
            
            # Mock optimization
            with patch.object(self.agent, '_optimize_input_for_retry', return_value=True):
                # Mock sleep to speed up test
                with patch('asyncio.sleep'):
                    mock_ctx = Mock()
                    
                    events = []
                    async for event in self.agent._run_async_impl(mock_ctx):
                        events.append(event)
                    
                    # Should stop before max retries due to consecutive error limit
                    assert mock_super.call_count <= 4
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that exponential backoff is applied between retries."""
        with patch.object(self.agent.__class__.__bases__[0], '_run_async_impl') as mock_super:
            mock_super.side_effect = [
                Exception("429 RESOURCE_EXHAUSTED"),
                Exception("429 RESOURCE_EXHAUSTED"),
                AsyncMock(return_value=iter([]))()  # Success on third try
            ]
            
            with patch.object(self.agent, '_optimize_input_for_retry', return_value=True):
                with patch('asyncio.sleep') as mock_sleep:
                    mock_ctx = Mock()
                    
                    events = []
                    async for event in self.agent._run_async_impl(mock_ctx):
                        events.append(event)
                    
                    # Should have called sleep for backoff
                    assert mock_sleep.call_count >= 2
                    
                    # Check that delays increase (exponential backoff)
                    delays = [call.args[0] for call in mock_sleep.call_args_list]
                    assert len(delays) >= 2
                    # Second delay should be longer than first (with jitter tolerance)
                    assert delays[1] > delays[0] * 0.8  # Allow for jitter


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 