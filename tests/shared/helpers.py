"""
Test helper utilities and common functions for DevOps agent tests.

This module provides common utilities, fixtures, and helper functions
used across the test suite.
"""

import asyncio
from dataclasses import dataclass, field

# Note: These imports would normally be from devops_agent
# For testing purposes, we'll define minimal versions here
from enum import Enum
from pathlib import Path
import tempfile
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, Mock


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
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
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
            raise StateValidationError(
                f"Turn {self.turn_number} marked completed but no completion time"
            )

        return True


class StateValidationError(Exception):
    """Raised when state validation fails."""


class StateManager:
    """Minimal StateManager for testing."""

    def __init__(self):
        self.conversation_history = []
        self.current_turn = None
        self.is_new_conversation = True
        self.app_state = {
            "code_snippets": [],
            "core_goal": "",
            "current_phase": "",
            "key_decisions": [],
            "last_modified_files": [],
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
                print(
                    f"Previous turn {self.current_turn.turn_number} was not properly"
                    " completed. Completing now."
                )
                self.current_turn.mark_completed()
                self.conversation_history.append(self.current_turn)

            # Create new turn
            turn_number = len(self.conversation_history) + 1
            self.current_turn = TurnState(
                turn_number=turn_number,
                user_message=user_message,
                phase=TurnPhase.PROCESSING_USER_INPUT,
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

    def add_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """Add a tool call to the current turn."""
        if not self.current_turn:
            raise StateValidationError("No current turn to add tool call to")

        tool_call = {"tool_name": tool_name, "args": args, "timestamp": time.time()}
        self.current_turn.tool_calls.append(tool_call)
        print(f"Added tool call {tool_name} to turn {self.current_turn.turn_number}")

    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add a tool result to the current turn."""
        if not self.current_turn:
            raise StateValidationError("No current turn to add tool result to")

        tool_result = {
            "tool_name": tool_name,
            "result": result,
            "timestamp": time.time(),
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

    def get_state_for_context(self) -> dict[str, Any]:
        """Get state in legacy format for compatibility."""
        # Convert conversation history to legacy format
        history = []
        for turn in self.conversation_history:
            history.append(
                {
                    "user_message": turn.user_message,
                    "agent_message": turn.agent_message,
                    "tool_calls": turn.tool_calls,
                    "tool_results": turn.tool_results,
                }
            )

        # Add current turn if it exists
        if self.current_turn:
            history.append(
                {
                    "user_message": self.current_turn.user_message,
                    "agent_message": self.current_turn.agent_message,
                    "tool_calls": self.current_turn.tool_calls,
                    "tool_results": self.current_turn.tool_results,
                }
            )

        state = {
            "user:conversation_history": history,
            "temp:is_new_conversation": self.is_new_conversation,
            "temp:current_turn": {
                "user_message": (self.current_turn.user_message if self.current_turn else None),
                "agent_message": (self.current_turn.agent_message if self.current_turn else None),
                "tool_calls": (self.current_turn.tool_calls if self.current_turn else []),
                "tool_results": (self.current_turn.tool_results if self.current_turn else []),
            },
            "temp:tool_calls_current_turn": (
                self.current_turn.tool_calls if self.current_turn else []
            ),
            "temp:tool_results_current_turn": (
                self.current_turn.tool_results if self.current_turn else []
            ),
        }

        # Add app state with proper prefixes
        for key, value in self.app_state.items():
            state[f"app:{key}"] = value

        return state

    def sync_from_legacy_state(self, legacy_state: dict[str, Any]) -> None:
        """Sync from legacy state format."""
        # Extract conversation history
        history = legacy_state.get("user:conversation_history", [])
        self.conversation_history = []

        for i, turn_data in enumerate(history):  # All turns in history
            turn = TurnState(
                turn_number=i + 1,
                user_message=turn_data.get("user_message"),
                agent_message=turn_data.get("agent_message"),
                tool_calls=turn_data.get("tool_calls", []),
                tool_results=turn_data.get("tool_results", []),
                phase=TurnPhase.COMPLETED,
            )
            turn.completed_at = time.time()
            self.conversation_history.append(turn)

        # Handle current turn
        current_turn_data = legacy_state.get("temp:current_turn", {})
        if current_turn_data.get("user_message") or current_turn_data.get("agent_message"):
            self.current_turn = TurnState(
                turn_number=len(self.conversation_history) + 1,
                user_message=current_turn_data.get("user_message"),
                agent_message=current_turn_data.get("agent_message"),
                tool_calls=current_turn_data.get("tool_calls", []),
                tool_results=current_turn_data.get("tool_results", []),
            )

        # Extract app state
        for key, value in legacy_state.items():
            if key.startswith("app:"):
                app_key = key[4:]  # Remove 'app:' prefix
                self.app_state[app_key] = value

        self.is_new_conversation = legacy_state.get("temp:is_new_conversation", False)


@dataclass
class MockEvent:
    """Mock event for testing agent responses."""

    author: str
    content: Any
    actions: Any = None


class MockInvocationContext:
    """Mock invocation context for testing."""

    def __init__(
        self,
        state: Optional[dict[str, Any]] = None,
        invocation_id: str = "mock_inv_123",
        trace_id: str = "mock_trace_456",
        session_state: Optional[dict[str, Any]] = None,
    ):
        self.state = state or {}
        self.invocation_id = invocation_id
        self.trace_id = trace_id
        self.session_state = session_state or {}
        self.end_invocation = False


class MockCallbackContext:
    """Mock callback context for testing."""

    def __init__(self, state: Optional[dict[str, Any]] = None):
        self.state = state or {}


class MockLlmRequest:
    """Mock LLM request for testing."""

    def __init__(
        self,
        messages: Optional[list[Any]] = None,
        tools: Optional[list[Any]] = None,
        model: str = "test_model",
        contents: Optional[list[Any]] = None,
    ):
        self.messages = messages or []
        self.tools = tools or []
        self.model = model
        self.contents = contents or []
        self.system_instruction = None


class MockLlmResponse:
    """Mock LLM response for testing."""

    def __init__(
        self,
        text: str = "",
        usage_metadata: Any = None,
        content: Any = None,
        parts: Optional[list[Any]] = None,
    ):
        self.text = text
        self.usage_metadata = usage_metadata
        self.content = content
        self.parts = parts or []


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str, args: Optional[dict[str, Any]] = None):
        self.name = name
        self.args = args or {}


class MockToolContext:
    """Mock tool context for testing."""

    def __init__(
        self,
        state: Optional[dict[str, Any]] = None,
        invocation_id: str = "mock_tool_inv_789",
        trace_id: str = "mock_trace_456",
        tool_input: Optional[dict[str, Any]] = None,
    ):
        self.state = state or {}
        self.invocation_id = invocation_id
        self.trace_id = trace_id
        self.tool_input = tool_input or {}


def create_sample_conversation_history(
    num_turns: int = 3,
) -> list[dict[str, Any]]:
    """Create sample conversation history for testing."""
    history = []
    for i in range(num_turns):
        turn = {
            "user_message": f"User message {i + 1}",
            "agent_message": f"Agent response {i + 1}",
            "tool_calls": (
                [
                    {
                        "tool_name": f"tool_{i}",
                        "args": {"arg1": f"value_{i}"},
                        "timestamp": time.time() - (num_turns - i) * 60,
                    }
                ]
                if i % 2 == 0
                else []
            ),
            "tool_results": (
                [
                    {
                        "tool_name": f"tool_{i}",
                        "result": f"result_{i}",
                        "timestamp": time.time() - (num_turns - i) * 60 + 30,
                    }
                ]
                if i % 2 == 0
                else []
            ),
        }
        history.append(turn)
    return history


def create_sample_code_snippets(num_snippets: int = 5) -> list[dict[str, Any]]:
    """Create sample code snippets for testing."""
    snippets = []
    for i in range(num_snippets):
        snippet = {
            "file_path": f"src/module_{i}.py",
            "code": (f'def function_{i}():\n    """Sample function {i}."""\n    return {i}'),
            "start_line": i * 10 + 1,
            "end_line": i * 10 + 3,
            "last_accessed": i + 1,
            "relevance_score": 1.0 - (i * 0.1),
        }
        snippets.append(snippet)
    return snippets


def create_sample_app_state() -> dict[str, Any]:
    """Create sample app state for testing."""
    return {
        "code_snippets": create_sample_code_snippets(),
        "core_goal": "Implement a robust DevOps automation system",
        "current_phase": "Implementation",
        "key_decisions": [
            "Use Python for automation scripts",
            "Implement retry logic for API calls",
            "Add comprehensive logging",
        ],
        "last_modified_files": [
            "src/agent.py",
            "src/retry_logic.py",
            "tests/test_agent.py",
        ],
    }


def create_sample_legacy_state(
    include_current_turn: bool = True,
) -> dict[str, Any]:
    """Create sample legacy state format for testing."""
    state = {
        "user:conversation_history": create_sample_conversation_history(),
        "temp:is_new_conversation": False,
        "temp:tool_calls_current_turn": [],
        "temp:tool_results_current_turn": [],
    }

    # Add app state with proper prefixes
    app_state = create_sample_app_state()
    for key, value in app_state.items():
        state[f"app:{key}"] = value

    if include_current_turn:
        state["temp:current_turn"] = {
            "user_message": "Current user message",
            "agent_message": "Current agent response",
            "tool_calls": [],
            "tool_results": [],
            "system_messages": [],
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

    def __init__(self, items: list[Any]):
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


def assert_legacy_state_format(state: dict[str, Any]):
    """Assert that a state dictionary follows the legacy format."""
    required_keys = [
        "user:conversation_history",
        "temp:is_new_conversation",
        "temp:current_turn",
        "temp:tool_calls_current_turn",
        "temp:tool_results_current_turn",
    ]

    for key in required_keys:
        assert key in state, f"Missing required key: {key}"

    # Validate conversation history format
    history = state["user:conversation_history"]
    assert isinstance(history, list)

    for turn in history:
        assert isinstance(turn, dict)
        # These keys are optional but should be present in most cases
        expected_keys = [
            "user_message",
            "agent_message",
            "tool_calls",
            "tool_results",
        ]
        for key in expected_keys:
            if key in turn:
                if key in ["tool_calls", "tool_results"]:
                    assert isinstance(turn[key], list)
                else:
                    assert isinstance(turn[key], (str, type(None)))


async def run_with_timeout(coro, timeout: float = 5.0):
    """Run a coroutine with a timeout for testing."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as e:
        raise AssertionError(f"Operation timed out after {timeout} seconds") from e


def create_error_scenarios() -> list[tuple]:
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
        ("unknown error", "UnknownError", False),
    ]


class MetricsCollector:
    """Helper class for collecting test metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.operations = []
        self.errors = []

    def record_operation(self, operation: str, duration: float):
        """Record an operation with its duration."""
        self.operations.append(
            {"operation": operation, "duration": duration, "timestamp": time.time()}
        )

    def record_error(self, error: str, error_type: str):
        """Record an error."""
        self.errors.append({"error": error, "error_type": error_type, "timestamp": time.time()})

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of collected metrics."""
        total_duration = time.time() - self.start_time
        return {
            "total_duration": total_duration,
            "total_operations": len(self.operations),
            "total_errors": len(self.errors),
            "avg_operation_duration": (
                sum(op["duration"] for op in self.operations) / len(self.operations)
                if self.operations
                else 0
            ),
            "error_rate": (len(self.errors) / len(self.operations) if self.operations else 0),
        }


# ADD MISSING UTILITY FUNCTIONS AT THE END OF THE FILE


def create_mock_llm_client():
    """Create a mock LLM client for testing with realistic behavior."""
    client = AsyncMock()

    # Mock generate_content method
    async def mock_generate_content(*_, **__):
        response = AsyncMock()
        response.text = "Mock LLM response for testing"
        response.usage_metadata = Mock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        response.usage_metadata.total_token_count = 150
        return response

    client.generate_content = mock_generate_content

    # Mock count_tokens method
    async def mock_count_tokens(content):
        # Simple token counting approximation
        text = str(content) if content else ""
        return Mock(total_tokens=len(text.split()) * 1.3)  # ~1.3 tokens per word

    client.count_tokens = mock_count_tokens

    return client


def create_mock_session_state():
    """Create a comprehensive mock session state for testing."""
    return {
        # Workflow coordination state
        "workflow_state": {
            "current_step": 0,
            "total_steps": 5,
            "status": "in_progress",
            "workflow_type": "sequential",
            "last_updated": time.time(),
        },
        # Context management state
        "context_state": {
            "priority_queue": [],
            "token_budget": 100000,
            "optimization_level": "normal",
            "emergency_mode": False,
        },
        # Agent coordination state
        "agent_coordination": {
            "active_agents": [],
            "shared_state": {},
            "handoff_queue": [],
            "coordination_mode": "sequential",
        },
        # Feature development state
        "feature_plan": {
            "complexity": "medium",
            "estimated_hours": 8,
            "requirements": ["authentication", "authorization", "testing"],
            "architecture_decisions": [],
        },
        # Code review state
        "code_review": {
            "issues": [],
            "suggestions": [],
            "approval_status": "pending",
            "reviewer_feedback": [],
        },
        # Testing state
        "testing": {
            "coverage": 85,
            "tests_added": 5,
            "tests_passing": 12,
            "tests_failing": 0,
            "test_strategy": "comprehensive",
        },
        # Deployment state
        "deployment": {
            "ready": False,
            "environment": "staging",
            "checklist": [],
            "approval_required": True,
        },
        # Memory and conversation state
        "conversation_history": [],
        "tool_results": [],
        "code_snippets": [],
        "key_decisions": [],
        "current_phase": "initialization",
        "core_goal": "",
        "last_modified_files": [],
    }


def create_test_workspace():
    """Create a temporary test workspace with sample files."""

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="agent_test_")
    workspace_path = Path(temp_dir)

    # Create sample project structure
    sample_files = {
        "README.md": """# Test Project
This is a test project for agent integration testing.

## Authentication System
The authentication system handles user login and security.
""",
        "src/auth.py": """\"\"\"Authentication module for user management.\"\"\"
import hashlib
import jwt
from typing import Optional, Dict, Any

SECRET_KEY = "your-secret-key-here"  # Security issue for testing

class AuthManager:
    \"\"\"Handles user authentication and authorization.\"\"\"

    def __init__(self):
        self.users = {}
        self.sessions = {}

    def authenticate(self, username: str, password: str) -> Optional[str]:
        \"\"\"Authenticate user and return token.\"\"\"
        # Simple password hashing - needs improvement
        password_hash = hashlib.md5(password.encode()).hexdigest()

        if username in self.users and self.users[username] == password_hash:
            token = jwt.encode({"user": username}, SECRET_KEY, algorithm="HS256")
            return token
        return None

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        \"\"\"Validate JWT token.\"\"\"
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError:
            return None
""",
        "src/user_management.py": """\"\"\"User management functionality.\"\"\"
from typing import List, Dict, Any
from .auth import AuthManager

class UserManager:
    \"\"\"Manages user accounts and profiles.\"\"\"

    def __init__(self):
        self.auth_manager = AuthManager()
        self.user_profiles = {}

    def create_user(self, username: str, password: str, email: str) -> bool:
        \"\"\"Create a new user account.\"\"\"
        if username in self.auth_manager.users:
            return False

        # Store user credentials
        password_hash = hashlib.md5(password.encode()).hexdigest()
        self.auth_manager.users[username] = password_hash

        # Create user profile
        self.user_profiles[username] = {
            "email": email,
            "created_at": time.time(),
            "last_login": None,
            "active": True
        }
        return True

    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        \"\"\"Get user profile information.\"\"\"
        return self.user_profiles.get(username)
""",
        "tests/test_auth.py": """\"\"\"Tests for authentication module.\"\"\"
import pytest
from src.auth import AuthManager

class TestAuthManager:
    def setup_method(self):
        self.auth_manager = AuthManager()

    def test_authenticate_valid_user(self):
        # Setup user
        self.auth_manager.users["testuser"] = "5d41402abc4b2a76b9719d911017c592"  # "hello"

        # Test authentication
        token = self.auth_manager.authenticate("testuser", "hello")
        assert token is not None

    def test_authenticate_invalid_user(self):
        token = self.auth_manager.authenticate("nonexistent", "password")
        assert token is None

    def test_validate_token(self):
        # Setup user and get token
        self.auth_manager.users["testuser"] = "5d41402abc4b2a76b9719d911017c592"
        token = self.auth_manager.authenticate("testuser", "hello")

        # Validate token
        payload = self.auth_manager.validate_token(token)
        assert payload is not None
        assert payload["user"] == "testuser"
""",
        "requirements.txt": """fastapi==0.104.1
uvicorn==0.24.0
pyjwt==2.8.0
bcrypt==4.0.1
pytest==7.4.3
pytest-asyncio==0.21.1
""",
        "pyproject.toml": """[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --tb=short"
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "setup.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
""",
        ".gitignore": """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

.coverage
htmlcov/
.tox/
.pytest_cache/
""",
        "config.json": """{
    "app_name": "test_auth_system",
    "debug": true,
    "secret_key": "test-secret-key-change-in-production",
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "test_db",
        "user": "test_user"
    },
    "auth": {
        "token_expiry": 3600,
        "max_login_attempts": 5,
        "password_min_length": 8
    },
    "logging": {
        "level": "INFO",
        "file": "app.log"
    }
}""",
    }

    # Write sample files
    for file_path, content in sample_files.items():
        full_path = workspace_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    # Create some empty directories
    (workspace_path / "src" / "utils").mkdir(parents=True, exist_ok=True)
    (workspace_path / "tests" / "integration").mkdir(parents=True, exist_ok=True)
    (workspace_path / "docs").mkdir(parents=True, exist_ok=True)
    (workspace_path / "scripts").mkdir(parents=True, exist_ok=True)

    return str(workspace_path)


def create_mock_agent_with_tools():
    """Create a mock agent with simulated tool execution capabilities."""
    agent = Mock()
    agent.name = "test_agent"
    agent.tools = []

    # Mock tool execution
    async def mock_execute_with_tools(tool_requests):
        results = []
        for request in tool_requests:
            if isinstance(request, str):
                tool_name = request.split()[0]
                args = request.split()[1:] if len(request.split()) > 1 else []
            else:
                tool_name = request.get("tool_name", "unknown")
                args = request.get("args", [])

            # Simulate tool execution
            if tool_name == "read_file":
                result = {"content": "Mock file content", "lines": 50}
            elif tool_name == "analyze_code":
                result = {
                    "issues": ["security_issue", "performance_issue"],
                    "score": 75,
                }
            elif tool_name == "suggest_fixes":
                result = {"suggestions": ["Use bcrypt for passwords", "Add input validation"]}
            else:
                result = {"status": "success", "output": f"Mock result for {tool_name}"}

            results.append(
                {
                    "tool_name": tool_name,
                    "args": args,
                    "result": result,
                    "success": True,
                }
            )

        return Mock(
            tools_executed=len(tool_requests),
            results=results,
            context_state={"tools_executed": len(tool_requests)},
        )

    agent.execute_with_tools = mock_execute_with_tools
    return agent


def create_mock_context_manager_with_sample_data():
    """Create a mock context manager with realistic sample data."""
    from agents.devops.components.context_management import ContextManager

    # Create with mock LLM client
    mock_client = create_mock_llm_client()
    context_manager = ContextManager(
        model_name="gemini-2.0-flash-thinking-experimental",
        max_llm_token_limit=100000,
        llm_client=mock_client,
        target_recent_turns=5,
        target_code_snippets=10,
        target_tool_results=10,
    )

    # Add sample conversation history
    context_manager.start_new_turn("Review the authentication system")
    context_manager.update_phase("Code Review")
    context_manager.add_code_snippet("src/auth.py", "class AuthManager:", 1, 50)
    context_manager.add_tool_result(
        "code_analysis", {"issues": ["hardcoded_secret"], "severity": "high"}
    )
    context_manager.update_agent_response(1, "Found security issues in authentication")

    context_manager.start_new_turn("Fix the security issues")
    context_manager.update_phase("Implementation")
    context_manager.add_key_decision("Use bcrypt for password hashing")
    context_manager.add_tool_result("test_runner", {"passed": 5, "failed": 1})
    context_manager.update_agent_response(2, "Implemented bcrypt, one test still failing")

    return context_manager


def create_mock_workflow_agents():
    """Create mock agents for workflow testing."""
    agents = {}

    # Create different types of agents
    agent_types = [
        "design_pattern_agent",
        "code_review_agent",
        "code_quality_agent",
        "testing_agent",
        "debugging_agent",
        "documentation_agent",
        "devops_agent",
    ]

    for agent_type in agent_types:
        agent = AsyncMock()
        agent.name = agent_type
        agent.description = f"Mock {agent_type} for testing"

        # Mock execution behavior
        async def mock_execute(*_, agent_type=agent_type, **__):
            return Mock(
                success=True,
                result=f"Mock result from {agent_type}",
                state_updates={f"{agent_type}_completed": True},
                execution_time=0.1,
            )

        agent.execute = mock_execute
        agents[agent_type] = agent

    return agents


def patch_human_approval_responses(responses):
    """Context manager to patch human approval responses for testing."""

    class MockHumanApprovalPatcher:
        def __init__(self, responses):
            self.responses = responses
            self.response_index = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def get_next_response(self):
            if self.response_index < len(self.responses):
                response = self.responses[self.response_index]
                self.response_index += 1
                return response
            return {"approved": True, "feedback": "Default approval"}

    return MockHumanApprovalPatcher(responses)


def create_performance_test_data():
    """Create test data for performance validation tests."""
    return {
        "large_codebase": {"files": 50, "lines_per_file": 500, "total_lines": 25000},
        "conversation_history": {
            "turns": 20,
            "avg_tokens_per_turn": 500,
            "total_tokens": 10000,
        },
        "tool_results": {"count": 30, "avg_size": 1000, "total_size": 30000},
        "expected_performance": {
            "max_context_assembly_time": 2.0,  # seconds
            "max_parallel_speedup": 0.7,  # 30% faster than sequential
            "token_optimization_ratio": 0.8,  # 20% token reduction
        },
    }
