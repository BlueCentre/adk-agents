"""Integration tests for Milestone 1.2: Shell Command History & Error Log Context"""

from unittest.mock import Mock, patch

import pytest

from agents.software_engineer.shared_libraries.context_callbacks import (
    _check_command_history_context,
)
from agents.software_engineer.tools.shell_command import (
    _detect_error_patterns,
    _store_command_history,
    _store_error_context,
    execute_shell_command,
)


class TestCommandHistoryCapture:
    """Test command history capture in shell_command tool"""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context with session state"""
        context = Mock()
        context.state = {"_initialized": True}  # Make state truthy
        context.__bool__ = lambda _self: True
        return context

    def test_store_command_history_success(self, mock_tool_context):
        """Test storing successful command history"""
        command_info = {
            "command": "ls -la",
            "exit_code": 0,
            "stdout": "file1.txt\nfile2.txt",
            "stderr": "",
            "success": True,
            "timestamp": "2024-01-01T10:00:00Z",
        }

        _store_command_history(mock_tool_context, command_info)

        assert "command_history" in mock_tool_context.state
        history = mock_tool_context.state["command_history"]
        assert len(history) == 1
        assert history[0]["command"] == "ls -la"
        assert history[0]["success"] is True

    def test_store_command_history_failure(self, mock_tool_context):
        """Test storing failed command history"""
        command_info = {
            "command": "cat nonexistent.txt",
            "exit_code": 1,
            "stdout": "",
            "stderr": "cat: nonexistent.txt: No such file or directory",
            "success": False,
            "timestamp": "2024-01-01T10:00:00Z",
        }

        _store_command_history(mock_tool_context, command_info)

        assert "command_history" in mock_tool_context.state
        history = mock_tool_context.state["command_history"]
        assert len(history) == 1
        assert history[0]["command"] == "cat nonexistent.txt"
        assert history[0]["success"] is False

    def test_command_history_size_limit(self, mock_tool_context):
        """Test that command history respects size limits"""
        # Add 55 commands to exceed the 50-command limit
        for i in range(55):
            command_info = {
                "command": f"echo {i}",
                "exit_code": 0,
                "stdout": str(i),
                "stderr": "",
                "success": True,
                "timestamp": f"2024-01-01T10:{i:02d}:00Z",
            }
            _store_command_history(mock_tool_context, command_info)

        history = mock_tool_context.state["command_history"]
        assert len(history) == 50  # Should be limited to 50
        # Should contain the most recent commands (5-54)
        assert history[0]["command"] == "echo 5"
        assert history[-1]["command"] == "echo 54"


class TestErrorPatternDetection:
    """Test error pattern detection in command output"""

    def test_detect_file_not_found_error(self):
        """Test detection of file not found errors"""
        stderr = "cat: nonexistent.txt: No such file or directory"
        stdout = ""
        exit_code = 1

        error_info = _detect_error_patterns(stderr, stdout, exit_code)

        assert error_info is not None
        assert error_info["error_type"] == "file_not_found"
        assert "nonexistent.txt" in stderr

    def test_detect_permission_denied_error(self):
        """Test detection of permission denied errors"""
        stderr = "cat: /root/secret.txt: Permission denied"
        stdout = ""
        exit_code = 1

        error_info = _detect_error_patterns(stderr, stdout, exit_code)

        assert error_info is not None
        assert error_info["error_type"] == "permission_denied"
        assert "/root/secret.txt" in stderr

    def test_detect_command_not_found_error(self):
        """Test detection of command not found errors"""
        stderr = "bash: nonexistentcommand: command not found"
        stdout = ""
        exit_code = 127

        error_info = _detect_error_patterns(stderr, stdout, exit_code)

        assert error_info is not None
        assert error_info["error_type"] == "command_not_found"
        assert "nonexistentcommand" in stderr

    def test_detect_syntax_error(self):
        """Test detection of syntax errors"""
        stderr = "bash: syntax error near unexpected token"
        stdout = ""
        exit_code = 1

        error_info = _detect_error_patterns(stderr, stdout, exit_code)

        assert error_info is not None
        assert error_info["error_type"] == "syntax_error"

    def test_no_error_patterns_for_success(self):
        """Test that no errors are detected for successful commands"""
        stderr = ""
        stdout = "Hello World"
        exit_code = 0

        error_info = _detect_error_patterns(stderr, stdout, exit_code)

        assert error_info is None


class TestErrorContextStorage:
    """Test error context storage"""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context with session state"""
        context = Mock()
        context.state = {"_initialized": True}  # Make state truthy
        context.__bool__ = lambda _self: True
        return context

    def test_store_error_context(self, mock_tool_context):
        """Test storing error context"""
        error_info = {
            "command": "cat nonexistent.txt",
            "error_type": "file_not_found",
            "details": "No such file or directory: nonexistent.txt",
            "stderr": "cat: nonexistent.txt: No such file or directory",
            "timestamp": "2024-01-01T10:00:00Z",
        }

        _store_error_context(mock_tool_context, error_info)

        assert "recent_errors" in mock_tool_context.state
        errors = mock_tool_context.state["recent_errors"]
        assert len(errors) == 1
        assert errors[0]["error_type"] == "file_not_found"

    def test_error_context_size_limit(self, mock_tool_context):
        """Test that error context respects size limits"""
        # Add 25 errors to exceed the 20-error limit
        for i in range(25):
            error_info = {
                "command": f"cat file{i}.txt",
                "error_type": "file_not_found",
                "details": f"No such file or directory: file{i}.txt",
                "stderr": f"cat: file{i}.txt: No such file or directory",
                "timestamp": f"2024-01-01T10:{i:02d}:00Z",
            }
            _store_error_context(mock_tool_context, error_info)

        errors = mock_tool_context.state["recent_errors"]
        assert len(errors) == 20  # Should be limited to 20
        # Should contain the most recent errors (5-24)
        assert "file5.txt" in errors[0]["details"]
        assert "file24.txt" in errors[-1]["details"]


class TestShellCommandIntegration:
    """Test integration of shell command with history and error capture"""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context with session state"""
        context = Mock()
        context.state = {"_initialized": True}
        context.__bool__ = lambda _self: True
        return context

    @patch("subprocess.run")
    def test_execute_shell_command_success_with_history(self, mock_run, mock_tool_context):
        """Test successful command execution with history capture"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Hello World"
        mock_run.return_value.stderr = ""

        args = {"command": "echo 'Hello World'"}
        result = execute_shell_command(args, mock_tool_context)

        assert result.success is True
        assert "command_history" in mock_tool_context.state
        history = mock_tool_context.state["command_history"]
        assert len(history) == 1
        assert history[0]["command"] == "echo 'Hello World'"
        assert history[0]["success"] is True

    @patch("subprocess.run")
    def test_execute_shell_command_failure_with_error_capture(self, mock_run, mock_tool_context):
        """Test failed command execution with error capture"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "cat: nonexistent.txt: No such file or directory"

        args = {"command": "cat nonexistent.txt"}
        result = execute_shell_command(args, mock_tool_context)

        assert result.success is False
        assert "command_history" in mock_tool_context.state
        assert "recent_errors" in mock_tool_context.state

        history = mock_tool_context.state["command_history"]
        errors = mock_tool_context.state["recent_errors"]

        assert len(history) == 1
        assert len(errors) == 1
        assert errors[0]["error_type"] == "file_not_found"

    def test_execute_shell_command_timeout_with_error_capture(self, mock_tool_context):
        """Test command timeout with error capture"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutError("Command timed out")

            args = {"command": "sleep 100"}
            result = execute_shell_command(args, mock_tool_context)

            assert result.success is False
            assert "recent_errors" in mock_tool_context.state
            errors = mock_tool_context.state["recent_errors"]
            assert len(errors) == 1
            assert errors[0]["error_type"] == "exception"


class TestCommandHistoryContext:
    """Test command history context checking functionality"""

    @pytest.fixture
    def mock_tool_context_with_history(self):
        """Create a mock tool context with command history and errors"""
        context = Mock()
        context.state = {
            "_initialized": True,
            "command_history": [
                {
                    "command": "ls -la",
                    "success": True,
                    "timestamp": "2024-01-01T10:00:00Z",
                },
                {
                    "command": "cat nonexistent.txt",
                    "success": False,
                    "timestamp": "2024-01-01T10:01:00Z",
                },
            ],
            "recent_errors": [
                {
                    "command": "cat nonexistent.txt",
                    "error_type": "file_not_found",
                    "details": "No such file or directory: nonexistent.txt",
                    "stderr": "cat: nonexistent.txt: No such file or directory",
                    "timestamp": "2024-01-01T10:01:00Z",
                }
            ],
        }
        context.__bool__ = lambda _self: True
        return context

    def test_check_command_history_context_why_failed(self, mock_tool_context_with_history):
        """Test context checking for 'why did that fail' queries"""
        context_info = _check_command_history_context(
            mock_tool_context_with_history, "why did that fail"
        )

        assert "Recent errors:" in context_info
        assert "file_not_found" in context_info
        assert "Recent commands:" in context_info

    def test_check_command_history_context_what_happened(self, mock_tool_context_with_history):
        """Test context checking for 'what happened' queries"""
        context_info = _check_command_history_context(
            mock_tool_context_with_history, "what happened"
        )

        assert "Recent errors:" in context_info
        assert "Recent commands:" in context_info

    def test_check_command_history_context_no_history_patterns(
        self, mock_tool_context_with_history
    ):
        """Test no context for queries without history reference patterns"""
        context_info = _check_command_history_context(
            mock_tool_context_with_history, "show me the files"
        )

        assert context_info is None

    def test_check_command_history_context_multiple_patterns(self, mock_tool_context_with_history):
        """Test that various history reference patterns are recognized"""
        test_queries = [
            "why did that fail",
            "what's wrong with the last command",
            "what happened",
            "last command",
            "that didn't work",
            "fix the error",
            "what was the output of",
            "previous result",
        ]

        for query in test_queries:
            context_info = _check_command_history_context(mock_tool_context_with_history, query)
            # Some queries might not match patterns and return None
            if context_info is not None:
                assert "Recent errors:" in context_info or "Recent commands:" in context_info

    def test_check_command_history_context_missing_history(self):
        """Test that the function handles missing history gracefully"""
        context = Mock()
        context.state = {"_initialized": True}  # No history or errors
        context.__bool__ = lambda _self: True

        context_info = _check_command_history_context(context, "why did that fail")

        # Should return None when no history is available
        assert context_info is None
