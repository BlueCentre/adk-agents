"""
Integration Tests for Milestone 2.1: Basic Proactive Error Detection

This test suite verifies that the proactive error detection system correctly:
1. Analyzes recent errors from session state
2. Generates appropriate fix suggestions
3. Integrates with the callback system
4. Provides suggestions to agents through context

Tests cover the full flow from error detection to agent response.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from agents.software_engineer.shared_libraries.context_callbacks import (
    _preprocess_and_add_context_to_agent_prompt,
)
from agents.software_engineer.shared_libraries.proactive_error_detection import (
    detect_and_suggest_error_fixes,
    get_error_statistics,
)


class TestProactiveErrorDetectionIntegration:
    """Integration tests for proactive error detection with agent callbacks."""

    @pytest.fixture
    def mock_callback_context(self):
        """Create a mock callback context with session state."""
        context = Mock()
        context.state = {
            "current_directory": "/test/dir",
            "command_history": [],
            "recent_errors": [],
        }
        return context

    def test_detect_and_suggest_error_fixes_function(self):
        """Test the main detection function."""
        current_time = datetime.now()
        session_state = {
            "recent_errors": [
                {
                    "command": "ls nonexistent",
                    "error_type": "file_not_found",
                    "details": "No such file or directory",
                    "stderr": "ls: cannot access 'nonexistent': No such file or directory",
                    "timestamp": (current_time - timedelta(minutes=1)).isoformat(),
                }
            ]
        }

        suggestions = detect_and_suggest_error_fixes(session_state)

        assert suggestions is not None
        assert "🔍 **Proactive Error Detection:**" in suggestions
        assert "ls nonexistent" in suggestions

    def test_detect_and_suggest_error_fixes_no_errors(self):
        """Test detection function with no errors."""
        session_state = {"recent_errors": []}
        suggestions = detect_and_suggest_error_fixes(session_state)
        assert suggestions is None

    def test_get_error_statistics(self):
        """Test getting error statistics."""
        session_state = {
            "recent_errors": [
                {"error_type": "file_not_found"},
                {"error_type": "file_not_found"},
                {"error_type": "permission_denied"},
            ]
        }

        stats = get_error_statistics(session_state)

        assert stats["total_errors"] == 3
        assert stats["error_types"]["file_not_found"] == 2
        assert stats["error_types"]["permission_denied"] == 1
        assert stats["has_recent_errors"] is True

    def test_callback_integration_with_errors(self, mock_callback_context):
        """Test that the callback system integrates proactive error detection."""
        # Add recent error to session state
        current_time = datetime.now()
        mock_callback_context.state["recent_errors"] = [
            {
                "command": "python broken.py",
                "error_type": "syntax_error",
                "details": "SyntaxError: invalid syntax",
                "stderr": "SyntaxError: invalid syntax",
                "timestamp": (current_time - timedelta(minutes=1)).isoformat(),
            }
        ]

        # Mock user message
        mock_callback_context.state["current_user_message"] = "help me debug this"

        # Call the callback
        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        # Check that proactive suggestions were added to context
        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        assert context_info is not None
        assert "proactive_error_suggestions" in context_info

        suggestions = context_info["proactive_error_suggestions"]
        assert suggestions is not None
        assert "🔍 **Proactive Error Detection:**" in suggestions

    def test_callback_integration_without_errors(self, mock_callback_context):
        """Test callback system when no recent errors exist."""
        # No recent errors in session state
        mock_callback_context.state["recent_errors"] = []
        mock_callback_context.state["current_user_message"] = "hello"

        # Call the callback
        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        # Check that no proactive suggestions were added if none exist
        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        if context_info:
            suggestions = context_info.get("proactive_error_suggestions")
            # Should be None or empty if no errors
            assert suggestions is None or suggestions == ""


class TestProactiveErrorDetectionEndToEnd:
    """End-to-end tests for the complete proactive error detection flow."""

    def test_complete_flow_file_not_found(self):
        """Test complete flow from error to suggestion for file not found."""
        # Simulate a recent file not found error
        current_time = datetime.now()
        session_state = {
            "recent_errors": [
                {
                    "command": "cat missing_file.txt",
                    "error_type": "file_not_found",
                    "details": "No such file or directory: missing_file.txt",
                    "stderr": "cat: missing_file.txt: No such file or directory",
                    "timestamp": (current_time - timedelta(minutes=2)).isoformat(),
                }
            ]
        }

        # Get suggestions
        suggestions = detect_and_suggest_error_fixes(session_state)

        # Verify suggestions are formatted correctly
        assert suggestions is not None
        assert "missing_file.txt" in suggestions
        assert "File Not Found" in suggestions
        assert "Check if the file exists using" in suggestions
        assert "ls -la" in suggestions

    def test_complete_flow_multiple_errors(self):
        """Test complete flow with multiple recent errors."""
        current_time = datetime.now()
        session_state = {
            "recent_errors": [
                {
                    "command": "python script.py",
                    "error_type": "python_import_error",
                    "details": "ImportError: No module named 'numpy'",
                    "stderr": "ImportError: No module named 'numpy'",
                    "timestamp": (current_time - timedelta(minutes=1)).isoformat(),
                },
                {
                    "command": "chmod +x script.sh",
                    "error_type": "permission_denied",
                    "details": "Permission denied",
                    "stderr": "chmod: changing permissions of 'script.sh': Permission denied",
                    "timestamp": (current_time - timedelta(minutes=3)).isoformat(),
                },
            ]
        }

        suggestions = detect_and_suggest_error_fixes(session_state)

        assert suggestions is not None
        assert "2 recent error(s)" in suggestions
        assert "Python Import Error" in suggestions
        assert "Permission Denied" in suggestions
        assert "pip install" in suggestions
        assert "chmod" in suggestions

    def test_complete_flow_no_recent_errors(self):
        """Test complete flow when no recent errors exist."""
        session_state = {"recent_errors": []}
        suggestions = detect_and_suggest_error_fixes(session_state)
        assert suggestions is None

    def test_error_statistics_comprehensive(self):
        """Test comprehensive error statistics."""
        session_state = {
            "recent_errors": [
                {"error_type": "file_not_found"},
                {"error_type": "file_not_found"},
                {"error_type": "permission_denied"},
                {"error_type": "python_import_error"},
                {"error_type": "timeout"},
            ]
        }

        stats = get_error_statistics(session_state)

        assert stats["total_errors"] == 5
        assert stats["error_types"]["file_not_found"] == 2
        assert stats["error_types"]["permission_denied"] == 1
        assert stats["error_types"]["python_import_error"] == 1
        assert stats["error_types"]["timeout"] == 1
        assert stats["has_recent_errors"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
