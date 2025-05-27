#!/usr/bin/env python3
"""
Unit tests for state management classes.

Tests the StateManager, TurnState, and related classes for:
- Basic functionality
- Error handling and validation
- Concurrent access protection
- State transitions and validation
"""

import time
import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any, Optional

# Import the classes from test helpers (minimal versions for testing)
from tests.fixtures.test_helpers import TurnPhase, TurnState, StateManager, StateValidationError


class TestTurnState:
    """Test cases for TurnState class."""
    
    def test_turn_state_creation(self):
        """Test basic TurnState creation."""
        turn = TurnState(turn_number=1, user_message="Hello")
        assert turn.turn_number == 1
        assert turn.user_message == "Hello"
        assert turn.phase == TurnPhase.INITIALIZING
        assert turn.completed_at is None
        assert len(turn.tool_calls) == 0
        assert len(turn.tool_results) == 0
        assert len(turn.errors) == 0
    
    def test_mark_completed(self):
        """Test marking a turn as completed."""
        turn = TurnState(turn_number=1)
        assert turn.phase != TurnPhase.COMPLETED
        assert turn.completed_at is None
        
        turn.mark_completed()
        assert turn.phase == TurnPhase.COMPLETED
        assert turn.completed_at is not None
        assert isinstance(turn.completed_at, float)
    
    def test_add_error(self):
        """Test adding errors to a turn."""
        turn = TurnState(turn_number=1)
        assert len(turn.errors) == 0
        
        turn.add_error("Test error")
        assert len(turn.errors) == 1
        assert turn.errors[0] == "Test error"
        
        turn.add_error("Another error")
        assert len(turn.errors) == 2
    
    def test_validation_success(self):
        """Test successful validation."""
        turn = TurnState(turn_number=1)
        assert turn.validate() is True
        
        turn.mark_completed()
        assert turn.validate() is True
    
    def test_validation_invalid_turn_number(self):
        """Test validation with invalid turn number."""
        turn = TurnState(turn_number=0)
        with pytest.raises(StateValidationError, match="Invalid turn number"):
            turn.validate()
        
        turn = TurnState(turn_number=-1)
        with pytest.raises(StateValidationError, match="Invalid turn number"):
            turn.validate()
    
    def test_validation_completed_without_time(self):
        """Test validation of completed turn without completion time."""
        turn = TurnState(turn_number=1)
        turn.phase = TurnPhase.COMPLETED
        # Don't set completed_at
        
        with pytest.raises(StateValidationError, match="marked completed but no completion time"):
            turn.validate()


class TestStateManager:
    """Test cases for StateManager class."""
    
    def setup_method(self):
        """Set up a fresh StateManager for each test."""
        self.state_manager = StateManager()
    
    def test_initial_state(self):
        """Test initial state of StateManager."""
        assert len(self.state_manager.conversation_history) == 0
        assert self.state_manager.current_turn is None
        assert self.state_manager.is_new_conversation is True
        assert isinstance(self.state_manager.app_state, dict)
        assert self.state_manager._lock is False
    
    def test_start_new_turn(self):
        """Test starting a new turn."""
        turn = self.state_manager.start_new_turn("Hello, world!")
        
        assert turn.turn_number == 1
        assert turn.user_message == "Hello, world!"
        assert turn.phase == TurnPhase.PROCESSING_USER_INPUT
        assert self.state_manager.current_turn is turn
        assert self.state_manager.is_new_conversation is False
    
    def test_start_multiple_turns(self):
        """Test starting multiple turns."""
        # Start first turn
        turn1 = self.state_manager.start_new_turn("First message")
        assert turn1.turn_number == 1
        
        # Complete first turn
        self.state_manager.complete_current_turn()
        assert len(self.state_manager.conversation_history) == 1
        assert self.state_manager.current_turn is None
        
        # Start second turn
        turn2 = self.state_manager.start_new_turn("Second message")
        assert turn2.turn_number == 2
        assert turn2.user_message == "Second message"
    
    def test_auto_complete_previous_turn(self):
        """Test automatic completion of previous turn when starting new one."""
        # Start first turn but don't complete it
        turn1 = self.state_manager.start_new_turn("First message")
        turn1.phase = TurnPhase.EXECUTING_TOOLS  # Simulate incomplete turn
        
        # Start second turn - should auto-complete first
        turn2 = self.state_manager.start_new_turn("Second message")
        
        assert len(self.state_manager.conversation_history) == 1
        assert self.state_manager.conversation_history[0] is turn1
        assert turn1.phase == TurnPhase.COMPLETED
        assert turn1.completed_at is not None
        assert turn2.turn_number == 2
    
    def test_update_current_turn(self):
        """Test updating current turn."""
        turn = self.state_manager.start_new_turn("Hello")
        
        self.state_manager.update_current_turn(
            agent_message="Hello back!",
            phase=TurnPhase.CALLING_LLM
        )
        
        assert turn.agent_message == "Hello back!"
        assert turn.phase == TurnPhase.CALLING_LLM
    
    def test_update_current_turn_no_turn(self):
        """Test updating current turn when no turn exists."""
        with pytest.raises(StateValidationError, match="No current turn to update"):
            self.state_manager.update_current_turn(agent_message="test")
    
    def test_add_tool_call(self):
        """Test adding tool calls."""
        turn = self.state_manager.start_new_turn("Hello")
        
        self.state_manager.add_tool_call("test_tool", {"arg1": "value1"})
        
        assert len(turn.tool_calls) == 1
        assert turn.tool_calls[0]["tool_name"] == "test_tool"
        assert turn.tool_calls[0]["args"] == {"arg1": "value1"}
        assert "timestamp" in turn.tool_calls[0]
    
    def test_add_tool_call_no_turn(self):
        """Test adding tool call when no current turn."""
        with pytest.raises(StateValidationError, match="No current turn to add tool call"):
            self.state_manager.add_tool_call("test_tool", {})
    
    def test_add_tool_result(self):
        """Test adding tool results."""
        turn = self.state_manager.start_new_turn("Hello")
        
        self.state_manager.add_tool_result("test_tool", {"result": "success"})
        
        assert len(turn.tool_results) == 1
        assert turn.tool_results[0]["tool_name"] == "test_tool"
        assert turn.tool_results[0]["result"] == {"result": "success"}
        assert "timestamp" in turn.tool_results[0]
    
    def test_add_tool_result_no_turn(self):
        """Test adding tool result when no current turn."""
        with pytest.raises(StateValidationError, match="No current turn to add tool result"):
            self.state_manager.add_tool_result("test_tool", {})
    
    def test_complete_current_turn(self):
        """Test completing current turn."""
        turn = self.state_manager.start_new_turn("Hello")
        turn.agent_message = "Hello back!"
        
        self.state_manager.complete_current_turn()
        
        assert turn.phase == TurnPhase.COMPLETED
        assert turn.completed_at is not None
        assert len(self.state_manager.conversation_history) == 1
        assert self.state_manager.conversation_history[0] is turn
        assert self.state_manager.current_turn is None
    
    def test_complete_current_turn_no_turn(self):
        """Test completing turn when no current turn."""
        # Should not raise an error, just log a warning
        self.state_manager.complete_current_turn()
        assert len(self.state_manager.conversation_history) == 0
    
    def test_get_state_for_context(self):
        """Test getting state in legacy format."""
        # Create some conversation history
        turn1 = self.state_manager.start_new_turn("First message")
        turn1.agent_message = "First response"
        self.state_manager.add_tool_call("tool1", {"arg": "value"})
        self.state_manager.add_tool_result("tool1", {"result": "success"})
        self.state_manager.complete_current_turn()
        
        turn2 = self.state_manager.start_new_turn("Second message")
        turn2.agent_message = "Second response"
        
        # Get legacy state format
        state = self.state_manager.get_state_for_context()
        
        assert "user:conversation_history" in state
        assert "temp:is_new_conversation" in state
        assert "temp:current_turn" in state
        assert "temp:tool_calls_current_turn" in state
        assert "temp:tool_results_current_turn" in state
        
        history = state["user:conversation_history"]
        assert len(history) == 2  # One completed turn + current turn
        
        # Check first turn in history
        assert history[0]["user_message"] == "First message"
        assert history[0]["agent_message"] == "First response"
        assert len(history[0]["tool_calls"]) == 1
        assert len(history[0]["tool_results"]) == 1
        
        # Check current turn in history
        assert history[1]["user_message"] == "Second message"
        assert history[1]["agent_message"] == "Second response"
    
    def test_sync_from_legacy_state(self):
        """Test syncing from legacy state format."""
        legacy_state = {
            "user:conversation_history": [
                {
                    "user_message": "Hello",
                    "agent_message": "Hi there",
                    "tool_calls": [{"tool_name": "test", "args": {}}],
                    "tool_results": [{"tool_name": "test", "result": "ok"}]
                }
            ],
            "temp:current_turn": {
                "user_message": "Current message",
                "agent_message": "Current response",
                "tool_calls": [],
                "tool_results": []
            },
            "temp:is_new_conversation": False,
            "app:core_goal": "Test goal",
            "app:code_snippets": []
        }
        
        self.state_manager.sync_from_legacy_state(legacy_state)
        
        # Check conversation history
        assert len(self.state_manager.conversation_history) == 1
        turn = self.state_manager.conversation_history[0]
        assert turn.user_message == "Hello"
        assert turn.agent_message == "Hi there"
        assert len(turn.tool_calls) == 1
        assert len(turn.tool_results) == 1
        assert turn.phase == TurnPhase.COMPLETED
        
        # Check current turn
        assert self.state_manager.current_turn is not None
        current = self.state_manager.current_turn
        assert current.user_message == "Current message"
        assert current.agent_message == "Current response"
        assert current.turn_number == 2
        
        # Check app state
        assert self.state_manager.app_state["core_goal"] == "Test goal"
        assert self.state_manager.is_new_conversation is False


class TestConcurrentAccess:
    """Test cases for concurrent access protection."""
    
    def setup_method(self):
        """Set up a fresh StateManager for each test."""
        self.state_manager = StateManager()
    
    def test_lock_protection(self):
        """Test that lock prevents concurrent modifications."""
        # Manually acquire lock
        self.state_manager._acquire_lock()
        
        # Try to start a new turn - should fail
        with pytest.raises(StateValidationError, match="locked"):
            self.state_manager.start_new_turn("test")
        
        # Release lock and try again - should succeed
        self.state_manager._release_lock()
        turn = self.state_manager.start_new_turn("test")
        assert turn is not None
    
    def test_lock_release_in_finally(self):
        """Test that locks are properly released even on exceptions."""
        # Start a turn to have a current turn
        self.state_manager.start_new_turn("test")
        
        # Mock an exception during update
        with patch.object(self.state_manager.current_turn, '__setattr__', side_effect=Exception("test error")):
            with pytest.raises(Exception, match="test error"):
                self.state_manager.update_current_turn(agent_message="test")
        
        # Lock should be released even after exception
        assert self.state_manager._lock is False
        
        # Should be able to perform operations
        self.state_manager.update_current_turn(agent_message="test after error")
        assert self.state_manager.current_turn.agent_message == "test after error"


def test_basic_functionality():
    """Test basic state management functionality."""
    print("Testing basic functionality...")
    
    state_manager = StateManager()
    
    # Test starting a new turn
    turn1 = state_manager.start_new_turn("Hello, world!")
    assert turn1.turn_number == 1
    assert turn1.user_message == "Hello, world!"
    assert turn1.phase == TurnPhase.PROCESSING_USER_INPUT
    
    # Test adding tool calls and results
    state_manager.add_tool_call("test_tool", {"arg1": "value1"})
    state_manager.add_tool_result("test_tool", {"result": "success"})
    
    assert len(turn1.tool_calls) == 1
    assert len(turn1.tool_results) == 1
    
    # Test updating turn
    state_manager.update_current_turn(agent_message="Hello back!")
    assert turn1.agent_message == "Hello back!"
    
    # Test completing turn
    state_manager.complete_current_turn()
    assert turn1.phase == TurnPhase.COMPLETED
    assert turn1.completed_at is not None
    assert len(state_manager.conversation_history) == 1
    assert state_manager.current_turn is None
    
    print("✓ Basic functionality tests passed")


def test_error_handling():
    """Test error handling."""
    print("Testing error handling...")
    
    state_manager = StateManager()
    
    # Test adding tool call without current turn
    try:
        state_manager.add_tool_call("test_tool", {})
        assert False, "Should have raised StateValidationError"
    except StateValidationError:
        pass  # Expected
    
    # Test adding tool result without current turn
    try:
        state_manager.add_tool_result("test_tool", {})
        assert False, "Should have raised StateValidationError"
    except StateValidationError:
        pass  # Expected
    
    # Test updating turn without current turn
    try:
        state_manager.update_current_turn(agent_message="test")
        assert False, "Should have raised StateValidationError"
    except StateValidationError:
        pass  # Expected
    
    print("✓ Error handling tests passed")


def test_concurrent_protection():
    """Test concurrent access protection."""
    print("Testing concurrent access protection...")
    
    state_manager = StateManager()
    
    # Simulate concurrent access by manually acquiring lock
    state_manager._acquire_lock()
    
    try:
        state_manager.start_new_turn("test")
        assert False, "Should have raised StateValidationError due to lock"
    except StateValidationError as e:
        assert "locked" in str(e).lower()
    
    # Release lock and try again
    state_manager._release_lock()
    turn = state_manager.start_new_turn("test")
    assert turn is not None
    
    print("✓ Concurrent access protection tests passed")


def main():
    """Run all tests."""
    print("Running StateManager tests...\n")
    
    try:
        test_basic_functionality()
        test_error_handling()
        test_concurrent_protection()
        
        print("\n🎉 All tests passed! StateManager core functionality is working correctly.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main()) 