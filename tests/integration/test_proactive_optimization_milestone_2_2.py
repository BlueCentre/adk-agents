"""
Integration Tests for Milestone 2.2: Proactive Optimization Suggestions

This test suite verifies that the proactive optimization system correctly:
1. Automatically triggers code analysis on file modifications
2. Filters and prioritizes suggestions by severity
3. Presents optimization suggestions non-intrusively
4. Integrates with the callback system for user control

Tests cover the full workflow from file modification to optimization suggestions.
"""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

from agents.software_engineer.shared_libraries.context_callbacks import (
    _preprocess_and_add_context_to_agent_prompt,
)
from agents.software_engineer.shared_libraries.proactive_optimization import (
    ProactiveOptimizer,
    configure_proactive_optimization,
    detect_and_suggest_optimizations,
    get_optimization_statistics,
)
from agents.software_engineer.tools.filesystem import edit_file_content


class TestProactiveOptimizerUnit:
    """Unit tests for the ProactiveOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create a ProactiveOptimizer instance."""
        return ProactiveOptimizer()

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context with session state."""
        context = Mock()
        context.state = {
            "proactive_optimization_enabled": True,
            "file_analysis_history": {},
            "analysis_issues": [],
        }
        return context

    def test_should_analyze_file_supported_python(self, optimizer):
        """Test that Python files are supported for analysis."""
        session_state = {"proactive_optimization_enabled": True}

        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
            temp_file.write(b"print('hello')")
            temp_path = temp_file.name

        try:
            result = optimizer.should_analyze_file(temp_path, session_state)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_should_analyze_file_supported_javascript(self, optimizer):
        """Test that JavaScript files are supported for analysis."""
        session_state = {"proactive_optimization_enabled": True}

        with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as temp_file:
            temp_file.write(b"console.log('hello');")
            temp_path = temp_file.name

        try:
            result = optimizer.should_analyze_file(temp_path, session_state)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_should_analyze_file_unsupported_extension(self, optimizer):
        """Test that unsupported file types are rejected."""
        session_state = {"proactive_optimization_enabled": True}

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Hello world")
            temp_path = temp_file.name

        try:
            result = optimizer.should_analyze_file(temp_path, session_state)
            assert result is False
        finally:
            Path(temp_path).unlink()

    def test_should_analyze_file_disabled(self, optimizer):
        """Test that analysis is skipped when disabled."""
        session_state = {"proactive_optimization_enabled": False}

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
            temp_file.write(b"print('hello')")
            temp_path = temp_file.name

        try:
            result = optimizer.should_analyze_file(temp_path, session_state)
            assert result is False
        finally:
            Path(temp_path).unlink()

    def test_should_analyze_file_cooldown_active(self, optimizer):
        """Test that files in cooldown period are not re-analyzed."""
        current_time = datetime.now()
        recent_time = current_time - timedelta(minutes=1)  # Within 2-minute cooldown

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
            temp_file.write(b"print('hello')")
            temp_path = temp_file.name

        session_state = {
            "proactive_optimization_enabled": True,
            "file_analysis_history": {
                temp_path: recent_time.isoformat()  # Use actual temp path
            },
        }

        try:
            result = optimizer.should_analyze_file(temp_path, session_state)
            assert result is False
        finally:
            Path(temp_path).unlink()

    def test_should_analyze_file_cooldown_expired(self, optimizer):
        """Test that files with expired cooldown can be re-analyzed."""
        current_time = datetime.now()
        old_time = current_time - timedelta(minutes=5)  # Beyond 2-minute cooldown

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
            temp_file.write(b"print('hello')")
            temp_path = temp_file.name

        session_state = {
            "proactive_optimization_enabled": True,
            "file_analysis_history": {
                temp_path: old_time.isoformat()  # Use actual temp path
            },
        }

        try:
            result = optimizer.should_analyze_file(temp_path, session_state)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_generate_prioritized_suggestions(self, optimizer, mock_tool_context):
        """Test generation of prioritized suggestions."""
        # Mock analysis issues with different severities
        mock_tool_context.state["analysis_issues"] = [
            {
                "line": 10,
                "severity": "error",
                "message": "Undefined variable 'x'",
                "code": "E0602",
                "source": "pylint",
            },
            {
                "line": 15,
                "severity": "warning",
                "message": "Line too long (85/79)",
                "code": "E501",
                "source": "flake8",
            },
            {
                "line": 5,
                "severity": "info",
                "message": "Consider using enumerate",
                "code": "C0200",
                "source": "pylint",
            },
        ]

        with patch.object(
            optimizer, "_find_fix_for_issue", return_value={"suggestion": "Mock fix suggestion"}
        ):
            suggestions = optimizer._generate_prioritized_suggestions(mock_tool_context)

        assert len(suggestions) > 0
        # Should prioritize error severity first
        assert suggestions[0]["severity"] == "error"
        assert "Undefined variable" in suggestions[0]["message"]

    def test_format_optimization_suggestions(self, optimizer):
        """Test formatting of optimization suggestions for display."""
        analysis_result = {
            "file_path": "test.py",
            "total_issues": 3,
            "suggestions": [
                {
                    "severity": "error",
                    "line": 10,
                    "message": "Undefined variable 'x'",
                    "suggested_fix": "Define variable 'x' before use",
                },
                {
                    "severity": "warning",
                    "line": 15,
                    "message": "Line too long",
                    "suggested_fix": "Break line into multiple lines",
                },
            ],
        }

        formatted = optimizer.format_optimization_suggestions(analysis_result)

        assert "🔧 **Proactive Code Optimization:**" in formatted
        assert "test.py" in formatted
        assert "3 potential improvements" in formatted
        assert "❌ ERROR" in formatted
        assert "⚠️ WARNING" in formatted
        assert "Undefined variable" in formatted
        assert "Define variable 'x' before use" in formatted

    def test_configure_optimization_settings(self, optimizer):
        """Test configuration of optimization settings."""
        session_state = {}

        result = optimizer.configure_optimization_settings(
            session_state, enabled=False, cooldown_minutes=5
        )

        assert result["status"] == "success"
        assert "Proactive optimization disabled" in result["changes"]
        assert "Analysis cooldown set to 5 minutes" in result["changes"]
        assert session_state["proactive_optimization_enabled"] is False
        assert session_state["optimization_cooldown_minutes"] == 5


class TestProactiveOptimizationIntegration:
    """Integration tests for proactive optimization with real components."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context with realistic session state."""
        context = Mock()
        context.state = {
            "proactive_optimization_enabled": True,
            "file_analysis_history": {},
            "analysis_issues": [],
            "analyzed_file": None,
            "analyzed_code": None,
        }
        return context

    def test_detect_and_suggest_optimizations_function(self, mock_tool_context):
        """Test the main optimization detection function."""
        # Create a temporary Python file with issues
        test_code = """
def unused_function():
    x = 1  # unused variable
    pass

print("test")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(test_code)
            temp_path = temp_file.name

        try:
            # Mock the analysis functions that are imported dynamically
            with patch(
                "agents.software_engineer.tools.code_analysis._analyze_code"
            ) as mock_analyze:
                mock_analyze.return_value = {"status": "Analysis complete", "language": "python"}

                # Mock issues in tool context after analysis
                mock_tool_context.state["analysis_issues"] = [
                    {
                        "line": 3,
                        "severity": "warning",
                        "message": "Unused variable 'x'",
                        "code": "W0612",
                        "source": "pylint",
                    }
                ]

                with patch(
                    "agents.software_engineer.tools.code_analysis.get_issues_by_severity"
                ) as mock_get_issues:
                    mock_get_issues.return_value = {
                        "issues": [mock_tool_context.state["analysis_issues"][0]],
                        "count": 1,
                    }

                    with patch(
                        "agents.software_engineer.tools.code_analysis.suggest_fixes"
                    ) as mock_suggest:
                        mock_suggest.return_value = {
                            "suggested_fixes": [
                                {
                                    "issue": mock_tool_context.state["analysis_issues"][0],
                                    "suggestion": "Remove the unused variable at line 3",
                                }
                            ]
                        }

                        suggestions = detect_and_suggest_optimizations(temp_path, mock_tool_context)

            assert suggestions is not None
            assert "🔧 **Proactive Code Optimization:**" in suggestions
            assert "Unused variable" in suggestions

        finally:
            Path(temp_path).unlink()

    def test_detect_and_suggest_optimizations_disabled(self, mock_tool_context):
        """Test that optimization detection respects disabled setting."""
        mock_tool_context.state["proactive_optimization_enabled"] = False

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
            temp_file.write(b"print('test')")
            temp_path = temp_file.name

        try:
            suggestions = detect_and_suggest_optimizations(temp_path, mock_tool_context)
            assert suggestions is None
        finally:
            Path(temp_path).unlink()

    def test_configure_proactive_optimization_function(self):
        """Test the configuration function."""
        session_state = {}

        result = configure_proactive_optimization(session_state, enabled=True)

        assert result["status"] == "success"
        assert session_state["proactive_optimization_enabled"] is True

    def test_get_optimization_statistics(self):
        """Test getting optimization statistics."""
        session_state = {
            "file_analysis_history": {
                "file1.py": "2025-01-01T10:00:00",
                "file2.js": "2025-01-01T11:00:00",
            },
            "proactive_optimization_enabled": True,
        }

        stats = get_optimization_statistics(session_state)

        assert stats["total_files_analyzed"] == 2
        assert stats["optimization_enabled"] is True
        assert "file1.py" in stats["recently_analyzed_files"]
        assert "file2.js" in stats["recently_analyzed_files"]


class TestFileSystemIntegration:
    """Test integration with the file system for automatic analysis triggering."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context."""
        context = Mock()
        context.state = {
            "require_edit_approval": False,  # Allow direct edits for testing
            "proactive_optimization_enabled": True,
            "file_analysis_history": {},
        }
        return context

    def test_edit_file_triggers_optimization(self, mock_tool_context):
        """Test that editing a file triggers optimization analysis."""
        test_code = """
def example_function():
    unused_var = 42  # This should trigger a warning
    return "hello"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Mock the optimization detection to return suggestions
            with patch(
                "agents.software_engineer.shared_libraries.proactive_optimization.detect_and_suggest_optimizations"
            ) as mock_detect:
                mock_detect.return_value = "🔧 **Proactive Code Optimization:** Found 1 issue"

                result = edit_file_content(temp_path, test_code, mock_tool_context)

                assert result["status"] == "success"
                assert "optimization_suggestions" in result
                assert "🔧 **Proactive Code Optimization:**" in result["optimization_suggestions"]
                mock_detect.assert_called_once_with(temp_path, mock_tool_context)

        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink()

    def test_edit_file_optimization_failure_doesnt_break_edit(self, mock_tool_context):
        """Test that optimization failure doesn't prevent successful file edits."""
        test_code = "print('hello world')"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Mock optimization to raise an exception
            with patch(
                "agents.software_engineer.shared_libraries.proactive_optimization.detect_and_suggest_optimizations"
            ) as mock_detect:
                mock_detect.side_effect = Exception("Analysis failed")

                result = edit_file_content(temp_path, test_code, mock_tool_context)

                # File edit should still succeed even if optimization fails
                assert result["status"] == "success"
                assert "optimization_suggestions" not in result

        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink()


class TestCallbackSystemIntegration:
    """Test integration with the callback system for user configuration."""

    @pytest.fixture
    def mock_callback_context(self):
        """Create a mock callback context."""
        context = Mock()
        context.state = {
            "current_user_message": "",
            "proactive_optimization_enabled": True,
        }
        return context

    def test_callback_disable_optimization_command(self, mock_callback_context):
        """Test that disable optimization command is handled in callbacks."""
        mock_callback_context.state["current_user_message"] = "disable optimization suggestions"

        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        assert context_info is not None
        assert "optimization_config_change" in context_info
        assert "have been disabled" in context_info["optimization_config_change"]
        assert mock_callback_context.state["proactive_optimization_enabled"] is False

    def test_callback_enable_optimization_command(self, mock_callback_context):
        """Test that enable optimization command is handled in callbacks."""
        mock_callback_context.state["proactive_optimization_enabled"] = False
        mock_callback_context.state["current_user_message"] = "enable optimization suggestions"

        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        assert context_info is not None
        assert "optimization_config_change" in context_info
        assert "have been enabled" in context_info["optimization_config_change"]
        assert mock_callback_context.state["proactive_optimization_enabled"] is True

    def test_callback_no_optimization_command(self, mock_callback_context):
        """Test that non-optimization commands don't trigger configuration changes."""
        mock_callback_context.state["current_user_message"] = "Hello, how are you?"

        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        # Should not have optimization config changes for regular messages
        if context_info:
            assert "optimization_config_change" not in context_info


class TestEndToEndOptimizationFlow:
    """End-to-end tests for the complete optimization suggestion workflow."""

    def test_complete_optimization_flow(self):
        """Test the complete flow from code analysis to formatted suggestions."""
        # Create a Python file with known issues
        problematic_code = """
import os  # unused import
import sys

def test_function():
    unused_variable = 42
    very_long_line_that_should_trigger_a_line_length_warning_in_most_linters_and_code_analysis_tools = (
        True
    )
    return "hello"

print("test")
"""  # noqa: E501

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(problematic_code)
            temp_path = temp_file.name

        try:
            # Create tool context
            tool_context = Mock()
            tool_context.state = {
                "proactive_optimization_enabled": True,
                "file_analysis_history": {},
                "analysis_issues": [],
            }

            # Mock analysis results
            mock_issues = [
                {
                    "line": 1,
                    "severity": "warning",
                    "message": "Unused import 'os'",
                    "code": "W0611",
                    "source": "pylint",
                },
                {
                    "line": 5,
                    "severity": "warning",
                    "message": "Unused variable 'unused_variable'",
                    "code": "W0612",
                    "source": "pylint",
                },
                {
                    "line": 6,
                    "severity": "error",
                    "message": "Line too long (89/79)",
                    "code": "E501",
                    "source": "flake8",
                },
            ]

            with patch(
                "agents.software_engineer.tools.code_analysis._analyze_code"
            ) as mock_analyze:
                mock_analyze.return_value = {"status": "Analysis complete", "language": "python"}

                tool_context.state["analysis_issues"] = mock_issues

                with patch(
                    "agents.software_engineer.tools.code_analysis.get_issues_by_severity"
                ) as mock_get_issues:

                    def mock_get_issues_side_effect(_tool_context, severity):
                        filtered = [issue for issue in mock_issues if issue["severity"] == severity]
                        return {"issues": filtered, "count": len(filtered)}

                    mock_get_issues.side_effect = mock_get_issues_side_effect

                    with patch(
                        "agents.software_engineer.tools.code_analysis.suggest_fixes"
                    ) as mock_suggest:
                        mock_suggest.return_value = {
                            "suggested_fixes": [
                                {
                                    "issue": mock_issues[0],
                                    "suggestion": "Remove the unused import at line 1",
                                }
                            ]
                        }

                        suggestions = detect_and_suggest_optimizations(temp_path, tool_context)

                        assert suggestions is not None
                        assert "🔧 **Proactive Code Optimization:**" in suggestions
                        assert "Line too long" in suggestions  # Should prioritize error severity
                        assert (
                            "💡 Would you like me to help you fix any of these issues?"
                            in suggestions
                        )

        finally:
            Path(temp_path).unlink()

    def test_optimization_statistics_tracking(self):
        """Test that optimization statistics are properly tracked."""
        session_state = {
            "file_analysis_history": {},
            "proactive_optimization_enabled": True,
        }

        # Simulate analyzing multiple files
        current_time = datetime.now()

        files = ["file1.py", "file2.js", "file3.ts"]
        for i, file_path in enumerate(files):
            session_state["file_analysis_history"][file_path] = (
                current_time - timedelta(minutes=i)
            ).isoformat()

        stats = get_optimization_statistics(session_state)

        assert stats["total_files_analyzed"] == 3
        assert stats["optimization_enabled"] is True
        assert len(stats["recently_analyzed_files"]) == 3
        assert "file1.py" in stats["recently_analyzed_files"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
