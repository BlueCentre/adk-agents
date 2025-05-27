#!/usr/bin/env python3
"""
Integration tests for DevOps agent lifecycle.

Tests the complete agent execution flow including state management,
tool execution, and error handling across multiple components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Any

# Import mock implementations for testing (avoiding full devops_agent dependencies)
from tests.fixtures.test_helpers import create_mock_agent, TurnPhase
from tests.fixtures.test_helpers import (
    MockInvocationContext,
    MockCallbackContext,
    MockLlmRequest,
    MockLlmResponse,
    MockTool,
    MockToolContext,
    create_sample_legacy_state,
    assert_state_manager_valid
)


class TestAgentLifecycle:
    """Integration tests for complete agent lifecycle."""
    
    def setup_method(self):
        """Set up agent for testing."""
        self.agent = create_mock_agent(name="test_agent", model="test_model")
    
    @pytest.mark.asyncio
    async def test_complete_conversation_turn(self):
        """Test a complete conversation turn from start to finish."""
        # Setup
        callback_context = MockCallbackContext(create_sample_legacy_state())
        llm_request = MockLlmRequest(messages=[{"role": "user", "content": "Hello"}])
        llm_response = MockLlmResponse(text="Hello back!")
        
        # Test before_model callback
        result = await self.agent.handle_before_model(callback_context, llm_request)
        assert result is None  # Should not intercept
        
        # Verify state was updated
        assert self.agent._state_manager.current_turn is not None
        assert self.agent._state_manager.current_turn.phase == TurnPhase.PROCESSING_USER_INPUT
        
        # Test after_model callback
        result = await self.agent.handle_after_model(callback_context, llm_response)
        assert result is None  # Should not intercept
        
        # Verify response was recorded
        assert self.agent._state_manager.current_turn.agent_message == "Hello back!"
        
        # Verify state manager is valid
        assert_state_manager_valid(self.agent._state_manager)
    
    @pytest.mark.asyncio
    async def test_tool_execution_flow(self):
        """Test complete tool execution flow."""
        # Setup
        callback_context = MockCallbackContext(create_sample_legacy_state())
        tool = MockTool("test_tool", {"arg1": "value1"})
        tool_context = MockToolContext()
        tool_response = {"status": "success", "result": "test result"}
        
        # Start a turn
        self.agent._state_manager.start_new_turn("Execute tool")
        
        # Test before_tool callback
        result = await self.agent.handle_before_tool(
            tool, tool.args, tool_context, callback_context
        )
        assert result is None
        
        # Verify tool call was recorded
        assert len(self.agent._state_manager.current_turn.tool_calls) == 1
        assert self.agent._state_manager.current_turn.tool_calls[0]["tool_name"] == "test_tool"
        
        # Test after_tool callback
        result = await self.agent.handle_after_tool(
            tool, tool_response, callback_context, tool.args, tool_context
        )
        assert result is None
        
        # Verify tool result was recorded
        assert len(self.agent._state_manager.current_turn.tool_results) == 1
        assert self.agent._state_manager.current_turn.tool_results[0]["tool_name"] == "test_tool"
        assert self.agent._state_manager.current_turn.tool_results[0]["result"] == tool_response
    
    @pytest.mark.asyncio
    async def test_multiple_turns_with_state_persistence(self):
        """Test multiple conversation turns with state persistence."""
        callback_context = MockCallbackContext(create_sample_legacy_state())
        
        # First turn
        llm_request1 = MockLlmRequest(messages=[{"role": "user", "content": "First message"}])
        llm_response1 = MockLlmResponse(text="First response")
        
        await self.agent.handle_before_model(callback_context, llm_request1)
        await self.agent.handle_after_model(callback_context, llm_response1)
        
        # Complete first turn
        self.agent._state_manager.complete_current_turn()
        
        # Second turn
        llm_request2 = MockLlmRequest(messages=[{"role": "user", "content": "Second message"}])
        llm_response2 = MockLlmResponse(text="Second response")
        
        await self.agent.handle_before_model(callback_context, llm_request2)
        await self.agent.handle_after_model(callback_context, llm_response2)
        
        # Verify conversation history
        assert len(self.agent._state_manager.conversation_history) == 1
        assert self.agent._state_manager.conversation_history[0].user_message == "First message"
        assert self.agent._state_manager.conversation_history[0].agent_message == "First response"
        assert self.agent._state_manager.conversation_history[0].phase == TurnPhase.COMPLETED
        
        # Verify current turn
        assert self.agent._state_manager.current_turn is not None
        assert self.agent._state_manager.current_turn.user_message == "Second message"
        assert self.agent._state_manager.current_turn.agent_message == "Second response"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_lifecycle(self):
        """Test error handling throughout the agent lifecycle."""
        callback_context = MockCallbackContext()
        
        # Test error in before_model
        with patch.object(self.agent._state_manager, 'start_new_turn', side_effect=Exception("test error")):
            llm_request = MockLlmRequest()
            result = await self.agent.handle_before_model(callback_context, llm_request)
            # Should not raise exception, should handle gracefully
            assert result is None
        
        # Test error in tool execution
        tool = MockTool("error_tool")
        tool_context = MockToolContext()
        
        # Start a turn manually since the previous one failed
        self.agent._state_manager.start_new_turn("Test error handling")
        
        with patch.object(self.agent._state_manager, 'add_tool_call', side_effect=Exception("tool error")):
            result = await self.agent.handle_before_tool(tool, {}, tool_context, callback_context)
            # Should handle error gracefully
            assert result is None
    
    @pytest.mark.asyncio
    async def test_state_synchronization_with_callback_context(self):
        """Test that state is properly synchronized with callback context."""
        # Start with legacy state
        legacy_state = create_sample_legacy_state()
        callback_context = MockCallbackContext(legacy_state)
        
        # Process a request
        llm_request = MockLlmRequest()
        await self.agent.handle_before_model(callback_context, llm_request)
        
        # Verify state was synced from legacy format
        assert len(self.agent._state_manager.conversation_history) > 0
        assert self.agent._state_manager.app_state['core_goal'] != ''
        
        # Make changes to state
        self.agent._state_manager.app_state['core_goal'] = 'Updated goal'
        
        # Process response
        llm_response = MockLlmResponse(text="Updated response")
        await self.agent.handle_after_model(callback_context, llm_response)
        
        # Verify callback context was updated
        updated_state = self.agent._state_manager.get_state_for_context()
        assert updated_state['app:core_goal'] == 'Updated goal'
    
    @pytest.mark.asyncio
    async def test_context_optimization_integration(self):
        """Test context optimization integration with state management."""
        # Create agent with large context
        callback_context = MockCallbackContext(create_sample_legacy_state())
        
        # Add lots of conversation history
        for i in range(10):
            turn = self.agent._state_manager.start_new_turn(f"Message {i}")
            turn.agent_message = f"Response {i}"
            self.agent._state_manager.complete_current_turn()
        
        # Add lots of code snippets
        self.agent._state_manager.app_state['code_snippets'] = [
            {'file_path': f'file{i}.py', 'code': f'code {i}'}
            for i in range(20)
        ]
        
        # Mock context to simulate retry scenario
        mock_ctx = MockInvocationContext()
        mock_ctx.state = self.agent._state_manager.get_state_for_context()
        
        # Test optimization
        success = await self.agent._optimize_input_for_retry(mock_ctx, 1)
        assert success is True
        
        # Verify optimization was applied
        assert len(self.agent._state_manager.conversation_history) <= 2
        assert len(self.agent._state_manager.app_state['code_snippets']) <= 3


class TestAgentErrorRecovery:
    """Integration tests for agent error recovery."""
    
    def setup_method(self):
        """Set up agent for testing."""
        self.agent = create_mock_agent(name="test_agent", model="test_model")
    
    @pytest.mark.asyncio
    async def test_state_corruption_recovery(self):
        """Test recovery from state corruption."""
        callback_context = MockCallbackContext()
        
        # Corrupt the state manager
        self.agent._state_manager = None
        
        # Should create new state manager and continue
        llm_request = MockLlmRequest()
        result = await self.agent.handle_before_model(callback_context, llm_request)
        
        # Should handle gracefully without crashing
        assert result is None
    
    @pytest.mark.asyncio
    async def test_partial_turn_completion(self):
        """Test handling of partially completed turns."""
        # Start a turn but don't complete it properly
        turn = self.agent._state_manager.start_new_turn("Incomplete turn")
        turn.phase = TurnPhase.EXECUTING_TOOLS
        
        # Start another turn - should auto-complete the previous one
        callback_context = MockCallbackContext()
        llm_request = MockLlmRequest()
        await self.agent.handle_before_model(callback_context, llm_request)
        
        # Verify previous turn was completed
        assert len(self.agent._state_manager.conversation_history) == 1
        assert self.agent._state_manager.conversation_history[0].phase == TurnPhase.COMPLETED
        assert self.agent._state_manager.conversation_history[0].completed_at is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_access_protection(self):
        """Test protection against concurrent state modifications."""
        # Simulate concurrent access by manually acquiring lock
        self.agent._state_manager._acquire_lock()
        
        callback_context = MockCallbackContext()
        llm_request = MockLlmRequest()
        
        # Should handle lock gracefully
        result = await self.agent.handle_before_model(callback_context, llm_request)
        
        # Should not crash, may degrade gracefully
        assert result is None
        
        # Release lock for cleanup
        self.agent._state_manager._release_lock()


class TestAgentPerformance:
    """Integration tests for agent performance characteristics."""
    
    def setup_method(self):
        """Set up agent for testing."""
        self.agent = create_mock_agent(name="test_agent", model="test_model")
    
    @pytest.mark.asyncio
    async def test_large_conversation_handling(self):
        """Test handling of large conversation histories."""
        callback_context = MockCallbackContext()
        
        # Create large conversation history
        for i in range(100):
            turn = self.agent._state_manager.start_new_turn(f"Message {i}")
            turn.agent_message = f"Response {i}"
            # Add some tool calls to make it more realistic
            if i % 5 == 0:
                self.agent._state_manager.add_tool_call(f"tool_{i}", {"data": f"value_{i}"})
                self.agent._state_manager.add_tool_result(f"tool_{i}", {"result": f"success_{i}"})
            self.agent._state_manager.complete_current_turn()
        
        # Process a new request
        llm_request = MockLlmRequest()
        start_time = asyncio.get_event_loop().time()
        
        result = await self.agent.handle_before_model(callback_context, llm_request)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second)
        assert duration < 1.0
        assert result is None
        
        # Verify state is still valid
        assert_state_manager_valid(self.agent._state_manager)
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency with large amounts of data."""
        import sys
        
        # Get initial memory usage
        initial_size = sys.getsizeof(self.agent._state_manager)
        
        # Add large amounts of data
        for i in range(1000):
            turn = self.agent._state_manager.start_new_turn(f"Large message {i} " * 100)
            turn.agent_message = f"Large response {i} " * 100
            self.agent._state_manager.complete_current_turn()
        
        # Check memory growth
        final_size = sys.getsizeof(self.agent._state_manager)
        growth_ratio = final_size / initial_size
        
        # Memory growth should be reasonable (less than 100x)
        assert growth_ratio < 100
        
        # Test optimization reduces memory usage
        mock_ctx = MockInvocationContext()
        mock_ctx.state = self.agent._state_manager.get_state_for_context()
        
        await self.agent._optimize_input_for_retry(mock_ctx, 3)  # Aggressive optimization
        
        optimized_size = sys.getsizeof(self.agent._state_manager)
        reduction_ratio = optimized_size / final_size
        
        # Should significantly reduce memory usage
        assert reduction_ratio < 0.1  # At least 90% reduction


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 