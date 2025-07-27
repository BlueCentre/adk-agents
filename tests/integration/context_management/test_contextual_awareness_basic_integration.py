"""Integration tests for Milestone 1.1: Basic Contextual Awareness (File System & Open Files)"""

from pathlib import Path
import tempfile
from unittest.mock import Mock

from google.adk.agents.callback_context import CallbackContext
import pytest

from agents.software_engineer.shared_libraries.context_callbacks import (
    _execute_contextual_actions,
    _preprocess_and_add_context_to_agent_prompt,
)


@pytest.fixture
def mock_tool_context():
    """Create a mock tool context with session state"""
    context = Mock()
    context.state = {"_initialized": True}  # Make state truthy
    context.__bool__ = lambda _self: True
    return context


@pytest.fixture
def mock_callback_context():
    """Create a mock callback context with session state"""
    context = Mock(spec=CallbackContext)
    context.state = {"_initialized": True}  # Make state truthy
    return context


@pytest.fixture
def temp_project_structure():
    """Create a temporary project structure for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create directories
        (temp_path / "src").mkdir()
        (temp_path / "tests").mkdir()
        (temp_path / "docs").mkdir()

        # Create files
        (temp_path / "src" / "main.py").write_text("print('Hello World')")
        (temp_path / "src" / "utils.py").write_text("def helper(): pass")
        (temp_path / "README.md").write_text("# Test Project")
        (temp_path / "tests" / "test_main.py").write_text("def test_main(): pass")

        yield temp_path


class TestContextualAwarenessCallback:
    """Test the contextual awareness callback functionality"""

    def test_callback_initializes_current_directory(self, mock_callback_context):
        """Test that the callback initializes current_directory in session state"""
        # Act
        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        # Assert
        assert "current_directory" in mock_callback_context.state
        assert mock_callback_context.state["current_directory"] == str(Path.cwd())

    def test_callback_initializes_command_history(self, mock_callback_context):
        """Test that the callback initializes command_history in session state"""
        # Act
        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        # Assert
        assert "command_history" in mock_callback_context.state
        assert mock_callback_context.state["command_history"] == []

    def test_callback_initializes_recent_errors(self, mock_callback_context):
        """Test that the callback initializes recent_errors in session state"""
        # Act
        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        # Assert
        assert "recent_errors" in mock_callback_context.state
        assert mock_callback_context.state["recent_errors"] == []

    def test_callback_handles_no_context_gracefully(self):
        """Test that the callback handles missing callback context gracefully"""
        # Act - should not raise an exception
        _preprocess_and_add_context_to_agent_prompt(None)

        # Assert - function completes without error

    def test_callback_handles_no_session_state_gracefully(self):
        """Test that the callback handles missing session state gracefully"""
        context = Mock(spec=CallbackContext)
        context.state = None

        # Act - should not raise an exception
        _preprocess_and_add_context_to_agent_prompt(context)

        # Assert - function completes without error

    def test_callback_preserves_existing_state(self, mock_callback_context):
        """Test that the callback preserves existing state values"""
        # Arrange - pre-populate some state
        mock_callback_context.state["current_directory"] = "/existing/path"
        mock_callback_context.state["command_history"] = [{"command": "existing"}]

        # Act
        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        # Assert - existing values are preserved
        assert mock_callback_context.state["current_directory"] == "/existing/path"
        assert mock_callback_context.state["command_history"] == [{"command": "existing"}]
        # But missing values are initialized
        assert "recent_errors" in mock_callback_context.state


class TestContextualActions:
    """Test the contextual action execution helpers"""

    def test_execute_contextual_actions_list_directory(
        self, mock_tool_context, temp_project_structure
    ):
        """Test executing list directory actions"""
        # Arrange
        mock_tool_context.state["current_directory"] = str(temp_project_structure)
        actions = [{"type": "list_directory", "target": "src"}]

        # Act
        results = _execute_contextual_actions(mock_tool_context, actions)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result["status"] == "success"
        assert "main.py" in result["result"]["files"]
        assert "utils.py" in result["result"]["files"]

    def test_execute_contextual_actions_read_file(self, mock_tool_context, temp_project_structure):
        """Test executing read file actions"""
        # Arrange
        mock_tool_context.state["current_directory"] = str(temp_project_structure)
        actions = [{"type": "read_file", "target": "src/main.py"}]

        # Act
        results = _execute_contextual_actions(mock_tool_context, actions)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result["status"] == "success"
        assert "print('Hello World')" in result["result"]

    def test_execute_contextual_actions_handles_errors(
        self, mock_tool_context, temp_project_structure
    ):
        """Test error handling in contextual actions"""
        # Arrange
        mock_tool_context.state["current_directory"] = str(temp_project_structure)
        actions = [
            {"type": "list_directory", "target": "nonexistent"},
            {"type": "read_file", "target": "nonexistent.py"},
        ]

        # Act
        results = _execute_contextual_actions(mock_tool_context, actions)

        # Assert
        assert len(results) == 2
        assert all(result["status"] == "error" for result in results)
        assert "not found" in results[0]["result"]
        assert "not found" in results[1]["result"]
