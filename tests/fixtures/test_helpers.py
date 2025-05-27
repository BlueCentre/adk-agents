"""
Test helper utilities and common functions for DevOps agent tests.

This module provides common utilities, fixtures, and helper functions
used across the test suite.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass

# Note: These imports would normally be from devops_agent
# For testing purposes, we'll define minimal versions here
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import time

class TurnPhase(Enum):
    """Represents the current phase of a conversation turn."""
    INITIALIZING = "initializing"
    PROCESSING_USER_INPUT = "processing_user_input"
    CALLING_LLM = "calling_llm"
    PROCESSING_LLM_RESPONSE = "processing_llm_response"
    EXECUTING_TOOLS = "executing_tools"
    FINALIZING = "finalizing"
    COMPLETED = "completed"

@dataclass
class TurnState:
    """Minimal TurnState for testing."""
    turn_number: int
    phase: TurnPhase = TurnPhase.INITIALIZING
    user_message: Optional[str] = None
    agent_message: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def mark_completed(self):
        """Mark the turn as completed."""
        self.phase = TurnPhase.COMPLETED
        self.completed_at = time.time()

    def add_error(self, error: str):
        """Add an error to this turn."""
        self.errors.append(error)
        print(f"Turn {self.turn_number} error: {error}")

    def validate(self) -> bool:
        """Validate the turn state for consistency."""
        if self.turn_number < 1:
            raise StateValidationError(f"Invalid turn number: {self.turn_number}")
        
        if self.phase == TurnPhase.COMPLETED and self.completed_at is None:
            raise StateValidationError(f"Turn {self.turn_number} marked completed but no completion time")
        
        return True

class StateValidationError(Exception):
    """Raised when state validation fails."""
    pass

class StateManager:
    """Minimal StateManager for testing."""
    def __init__(self):
        self.conversation_history = []
        self.current_turn = None
        self.is_new_conversation = True
        self.app_state = {
            'code_snippets': [],
            'core_goal': '',
            'current_phase': '',
            'key_decisions': [],
            'last_modified_files': []
        }
        self._lock = False
    
    def _acquire_lock(self):
        """Acquire a simple lock for state modifications."""
        if self._lock:
            raise StateValidationError("State is currently locked for modification")
        self._lock = True
        
    def _release_lock(self):
        """Release the state lock."""
        self._lock = False
        
    def start_new_turn(self, user_message: Optional[str] = None) -> TurnState:
        """Start a new conversation turn with proper state management."""
        self._acquire_lock()
        try:
            # Complete the previous turn if it exists and isn't completed
            if self.current_turn and self.current_turn.phase != TurnPhase.COMPLETED:
                print(f"Previous turn {self.current_turn.turn_number} was not properly completed. Completing now.")
                self.current_turn.mark_completed()
                self.conversation_history.append(self.current_turn)
            
            # Create new turn
            turn_number = len(self.conversation_history) + 1
            self.current_turn = TurnState(
                turn_number=turn_number,
                user_message=user_message,
                phase=TurnPhase.PROCESSING_USER_INPUT
            )
            
            self.is_new_conversation = False
            print(f"Started new turn {turn_number}")
            return self.current_turn
            
        finally:
            self._release_lock()
    
    def update_current_turn(self, **kwargs) -> None:
        """Update the current turn with new data."""
        if not self.current_turn:
            raise StateValidationError("No current turn to update")
            
        self._acquire_lock()
        try:
            for key, value in kwargs.items():
                if hasattr(self.current_turn, key):
                    setattr(self.current_turn, key, value)
                else:
                    print(f"Attempted to set unknown attribute '{key}' on turn state")
        finally:
            self._release_lock()
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Add a tool call to the current turn."""
        if not self.current_turn:
            raise StateValidationError("No current turn to add tool call to")
            
        tool_call = {
            'tool_name': tool_name,
            'args': args,
            'timestamp': time.time()
        }
        self.current_turn.tool_calls.append(tool_call)
        print(f"Added tool call {tool_name} to turn {self.current_turn.turn_number}")
    
    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add a tool result to the current turn."""
        if not self.current_turn:
            raise StateValidationError("No current turn to add tool result to")
            
        tool_result = {
            'tool_name': tool_name,
            'result': result,
            'timestamp': time.time()
        }
        self.current_turn.tool_results.append(tool_result)
        print(f"Added tool result for {tool_name} to turn {self.current_turn.turn_number}")
    
    def complete_current_turn(self) -> None:
        """Complete the current turn and add it to history."""
        if not self.current_turn:
            print("No current turn to complete")
            return
            
        self._acquire_lock()
        try:
            self.current_turn.mark_completed()
            self.current_turn.validate()
            self.conversation_history.append(self.current_turn)
            print(f"Completed turn {self.current_turn.turn_number}")
            self.current_turn = None
        finally:
            self._release_lock()
    
    def get_state_for_context(self) -> Dict[str, Any]:
        """Get state in legacy format for compatibility."""
        # Convert conversation history to legacy format
        history = []
        for turn in self.conversation_history:
            history.append({
                'user_message': turn.user_message,
                'agent_message': turn.agent_message,
                'tool_calls': turn.tool_calls,
                'tool_results': turn.tool_results
            })
        
        # Add current turn if it exists
        if self.current_turn:
            history.append({
                'user_message': self.current_turn.user_message,
                'agent_message': self.current_turn.agent_message,
                'tool_calls': self.current_turn.tool_calls,
                'tool_results': self.current_turn.tool_results
            })
        
        state = {
            'user:conversation_history': history,
            'temp:is_new_conversation': self.is_new_conversation,
            'temp:current_turn': {
                'user_message': self.current_turn.user_message if self.current_turn else None,
                'agent_message': self.current_turn.agent_message if self.current_turn else None,
                'tool_calls': self.current_turn.tool_calls if self.current_turn else [],
                'tool_results': self.current_turn.tool_results if self.current_turn else []
            },
            'temp:tool_calls_current_turn': self.current_turn.tool_calls if self.current_turn else [],
            'temp:tool_results_current_turn': self.current_turn.tool_results if self.current_turn else []
        }
        
        # Add app state with proper prefixes
        for key, value in self.app_state.items():
            state[f'app:{key}'] = value
        
        return state
    
    def sync_from_legacy_state(self, legacy_state: Dict[str, Any]) -> None:
        """Sync from legacy state format."""
        # Extract conversation history
        history = legacy_state.get('user:conversation_history', [])
        self.conversation_history = []
        
        for i, turn_data in enumerate(history):  # All turns in history
            turn = TurnState(
                turn_number=i + 1,
                user_message=turn_data.get('user_message'),
                agent_message=turn_data.get('agent_message'),
                tool_calls=turn_data.get('tool_calls', []),
                tool_results=turn_data.get('tool_results', []),
                phase=TurnPhase.COMPLETED
            )
            turn.completed_at = time.time()
            self.conversation_history.append(turn)
        
        # Handle current turn
        current_turn_data = legacy_state.get('temp:current_turn', {})
        if current_turn_data.get('user_message') or current_turn_data.get('agent_message'):
            self.current_turn = TurnState(
                turn_number=len(self.conversation_history) + 1,
                user_message=current_turn_data.get('user_message'),
                agent_message=current_turn_data.get('agent_message'),
                tool_calls=current_turn_data.get('tool_calls', []),
                tool_results=current_turn_data.get('tool_results', [])
            )
        
        # Extract app state
        for key, value in legacy_state.items():
            if key.startswith('app:'):
                app_key = key[4:]  # Remove 'app:' prefix
                self.app_state[app_key] = value
        
        self.is_new_conversation = legacy_state.get('temp:is_new_conversation', False)


@dataclass
class MockEvent:
    """Mock event for testing agent responses."""
    author: str
    content: Any
    actions: Any = None


class MockInvocationContext:
    """Mock invocation context for testing."""
    
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or {}
        self.end_invocation = False


class MockCallbackContext:
    """Mock callback context for testing."""
    
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or {}


class MockLlmRequest:
    """Mock LLM request for testing."""
    
    def __init__(self, messages: List[Any] = None, tools: List[Any] = None, 
                 model: str = "test_model", contents: List[Any] = None):
        self.messages = messages or []
        self.tools = tools or []
        self.model = model
        self.contents = contents or []
        self.system_instruction = None


class MockLlmResponse:
    """Mock LLM response for testing."""
    
    def __init__(self, text: str = "", usage_metadata: Any = None, 
                 content: Any = None, parts: List[Any] = None):
        self.text = text
        self.usage_metadata = usage_metadata
        self.content = content
        self.parts = parts or []


class MockTool:
    """Mock tool for testing."""
    
    def __init__(self, name: str, args: Dict[str, Any] = None):
        self.name = name
        self.args = args or {}


class MockToolContext:
    """Mock tool context for testing."""
    
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or {}


def create_sample_conversation_history(num_turns: int = 3) -> List[Dict[str, Any]]:
    """Create sample conversation history for testing."""
    history = []
    for i in range(num_turns):
        turn = {
            'user_message': f'User message {i + 1}',
            'agent_message': f'Agent response {i + 1}',
            'tool_calls': [
                {
                    'tool_name': f'tool_{i}',
                    'args': {'arg1': f'value_{i}'},
                    'timestamp': time.time() - (num_turns - i) * 60
                }
            ] if i % 2 == 0 else [],
            'tool_results': [
                {
                    'tool_name': f'tool_{i}',
                    'result': f'result_{i}',
                    'timestamp': time.time() - (num_turns - i) * 60 + 30
                }
            ] if i % 2 == 0 else []
        }
        history.append(turn)
    return history


def create_sample_code_snippets(num_snippets: int = 5) -> List[Dict[str, Any]]:
    """Create sample code snippets for testing."""
    snippets = []
    for i in range(num_snippets):
        snippet = {
            'file_path': f'src/module_{i}.py',
            'code': f'def function_{i}():\n    """Sample function {i}."""\n    return {i}',
            'start_line': i * 10 + 1,
            'end_line': i * 10 + 3,
            'last_accessed': i + 1,
            'relevance_score': 1.0 - (i * 0.1)
        }
        snippets.append(snippet)
    return snippets


def create_sample_app_state() -> Dict[str, Any]:
    """Create sample app state for testing."""
    return {
        'code_snippets': create_sample_code_snippets(),
        'core_goal': 'Implement a robust DevOps automation system',
        'current_phase': 'Implementation',
        'key_decisions': [
            'Use Python for automation scripts',
            'Implement retry logic for API calls',
            'Add comprehensive logging'
        ],
        'last_modified_files': [
            'src/agent.py',
            'src/retry_logic.py',
            'tests/test_agent.py'
        ]
    }


def create_sample_legacy_state(include_current_turn: bool = True) -> Dict[str, Any]:
    """Create sample legacy state format for testing."""
    state = {
        'user:conversation_history': create_sample_conversation_history(),
        'temp:is_new_conversation': False,
        'temp:tool_calls_current_turn': [],
        'temp:tool_results_current_turn': []
    }
    
    # Add app state with proper prefixes
    app_state = create_sample_app_state()
    for key, value in app_state.items():
        state[f'app:{key}'] = value
    
    if include_current_turn:
        state['temp:current_turn'] = {
            'user_message': 'Current user message',
            'agent_message': 'Current agent response',
            'tool_calls': [],
            'tool_results': [],
            'system_messages': []
        }
    
    return state


def create_populated_state_manager() -> StateManager:
    """Create a StateManager with sample data for testing."""
    state_manager = StateManager()
    
    # Add conversation history
    for i in range(3):
        turn = state_manager.start_new_turn(f"Message {i + 1}")
        turn.agent_message = f"Response {i + 1}"
        if i % 2 == 0:
            state_manager.add_tool_call(f"tool_{i}", {"arg": f"value_{i}"})
            state_manager.add_tool_result(f"tool_{i}", {"result": f"success_{i}"})
        state_manager.complete_current_turn()
    
    # Add app state
    app_state = create_sample_app_state()
    state_manager.app_state.update(app_state)
    
    return state_manager


class AsyncIteratorMock:
    """Mock async iterator for testing async generators."""
    
    def __init__(self, items: List[Any]):
        self.items = items
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


def create_mock_agent(name: str = "test_agent", model: str = "test_model") -> Mock:
    """Create a mock agent with common attributes and methods."""
    agent = Mock()
    agent.name = name
    agent.model = model
    agent._state_manager = StateManager()
    agent._context_manager = Mock()
    agent._planning_manager = Mock()
    agent._console = Mock()
    agent._status_indicator = None
    agent._actual_llm_token_limit = 100000
    
    # Mock methods
    agent._is_retryable_error = Mock(return_value=True)
    agent._optimize_input_for_retry = AsyncMock(return_value=True)
    agent._count_tokens = Mock(return_value=100)
    agent._start_status = Mock()
    agent._stop_status = Mock()
    
    return agent


def assert_turn_state_valid(turn: TurnState):
    """Assert that a TurnState object is valid."""
    assert turn.turn_number >= 1
    assert isinstance(turn.phase, TurnPhase)
    assert isinstance(turn.tool_calls, list)
    assert isinstance(turn.tool_results, list)
    assert isinstance(turn.errors, list)
    assert isinstance(turn.created_at, float)
    
    if turn.phase == TurnPhase.COMPLETED:
        assert turn.completed_at is not None
        assert isinstance(turn.completed_at, float)
        assert turn.completed_at >= turn.created_at


def assert_state_manager_valid(state_manager: StateManager):
    """Assert that a StateManager object is in a valid state."""
    assert isinstance(state_manager.conversation_history, list)
    assert isinstance(state_manager.app_state, dict)
    assert isinstance(state_manager.is_new_conversation, bool)
    assert isinstance(state_manager._lock, bool)
    
    # Validate all turns in history
    for turn in state_manager.conversation_history:
        assert_turn_state_valid(turn)
        assert turn.phase == TurnPhase.COMPLETED
    
    # Validate current turn if it exists
    if state_manager.current_turn:
        assert_turn_state_valid(state_manager.current_turn)


def assert_legacy_state_format(state: Dict[str, Any]):
    """Assert that a state dictionary follows the legacy format."""
    required_keys = [
        'user:conversation_history',
        'temp:is_new_conversation',
        'temp:current_turn',
        'temp:tool_calls_current_turn',
        'temp:tool_results_current_turn'
    ]
    
    for key in required_keys:
        assert key in state, f"Missing required key: {key}"
    
    # Validate conversation history format
    history = state['user:conversation_history']
    assert isinstance(history, list)
    
    for turn in history:
        assert isinstance(turn, dict)
        # These keys are optional but should be present in most cases
        expected_keys = ['user_message', 'agent_message', 'tool_calls', 'tool_results']
        for key in expected_keys:
            if key in turn:
                if key in ['tool_calls', 'tool_results']:
                    assert isinstance(turn[key], list)
                else:
                    assert isinstance(turn[key], (str, type(None)))


async def run_with_timeout(coro, timeout: float = 5.0):
    """Run a coroutine with a timeout for testing."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise AssertionError(f"Operation timed out after {timeout} seconds")


def create_error_scenarios() -> List[tuple]:
    """Create common error scenarios for testing."""
    return [
        # (error_message, error_type, should_retry)
        ("429 RESOURCE_EXHAUSTED", "RateLimitError", True),
        ("500 Internal Server Error", "ServerError", True),
        ("connection timeout", "TimeoutError", True),
        ("Invalid JSON response", "JSONDecodeError", True),
        ("token limit exceeded", "TokenLimitError", True),
        ("PERMISSION_DENIED", "AuthError", False),
        ("INVALID_ARGUMENT", "ValidationError", False),
        ("model not found", "ModelError", False),
        ("unknown error", "UnknownError", False)
    ]


class MetricsCollector:
    """Helper class for collecting test metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.operations = []
        self.errors = []
    
    def record_operation(self, operation: str, duration: float):
        """Record an operation with its duration."""
        self.operations.append({
            'operation': operation,
            'duration': duration,
            'timestamp': time.time()
        })
    
    def record_error(self, error: str, error_type: str):
        """Record an error."""
        self.errors.append({
            'error': error,
            'error_type': error_type,
            'timestamp': time.time()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics."""
        total_duration = time.time() - self.start_time
        return {
            'total_duration': total_duration,
            'total_operations': len(self.operations),
            'total_errors': len(self.errors),
            'avg_operation_duration': sum(op['duration'] for op in self.operations) / len(self.operations) if self.operations else 0,
            'error_rate': len(self.errors) / len(self.operations) if self.operations else 0
        } 