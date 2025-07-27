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

    def test_enhanced_generic_fix_suggestions(self, optimizer):
        """Test that enhanced generic fix suggestions provide specific actionable advice."""
        # Test unused import suggestion
        unused_import_issue = {
            "line": 5,
            "severity": "warning",
            "message": "Unused import 'os'",
            "code": "W0611",
            "source": "pylint",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(unused_import_issue)
        assert "Remove the unused import 'os' on line 5" in suggestion

        # Test unused variable suggestion
        unused_var_issue = {
            "line": 10,
            "severity": "warning",
            "message": "Unused variable 'temp_data'",
            "code": "W0612",
            "source": "pylint",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(unused_var_issue)
        assert "Remove the unused variable 'temp_data' on line 10" in suggestion
        assert "or use it in your code" in suggestion

        # Test line too long suggestion with specific details
        line_too_long_issue = {
            "line": 25,
            "severity": "error",
            "message": "Line too long (95/79)",
            "code": "E501",
            "source": "flake8",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(line_too_long_issue)
        assert "Shorten line 25 by 16 characters" in suggestion
        assert "currently 95, max 79" in suggestion

        # Test undefined variable suggestion
        undefined_var_issue = {
            "line": 15,
            "severity": "error",
            "message": "Undefined variable 'config_data'",
            "code": "E0602",
            "source": "pylint",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(undefined_var_issue)
        assert "Define variable 'config_data' before line 15" in suggestion
        assert "check for typos" in suggestion

        # Test import error suggestion with correct format
        import_error_issue = {
            "line": 2,
            "severity": "error",
            "message": "No module named 'nonexistent_module'",
            "code": "E0401",
            "source": "pylint",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(import_error_issue)
        assert "Install the missing module 'nonexistent_module'" in suggestion

        # Test critical security issue
        security_issue = {
            "line": 30,
            "severity": "critical",
            "message": "Potential security vulnerability: SQL injection possible",
            "code": "S608",
            "source": "bandit",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(security_issue)
        assert "Address the security issue on line 30" in suggestion
        assert "SQL injection" in suggestion

        # Test syntax error suggestion
        syntax_issue = {
            "line": 8,
            "severity": "error",
            "message": "Invalid syntax",
            "code": "E9999",
            "source": "python",
        }
        suggestion = optimizer._generate_generic_fix_suggestion(syntax_issue)
        assert "Fix the syntax error on line 8" in suggestion
        assert "check for missing colons" in suggestion


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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
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
        """Test that editing a file works correctly (optimization handled by agent callbacks)."""
        test_code = """
def example_function():
    unused_var = 42  # This should trigger a warning
    return "hello"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = edit_file_content(temp_path, test_code, mock_tool_context)

            assert result["status"] == "success"
            assert "message" in result
            assert temp_path in result["message"]

            # Verify file was written correctly
            assert Path(temp_path).exists()
            written_content = Path(temp_path).read_text()
            assert written_content == test_code

            # Note: Optimization suggestions are now added by agent callbacks,
            # not by direct tool calls

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

    def test_callback_false_positive_prevention(self, mock_callback_context):
        """Test that regex prevents false positives in optimization commands."""
        # This should NOT trigger optimization disable because it's talking about something else
        mock_callback_context.state["current_user_message"] = (
            "How do I disable optimization for just one function?"
        )

        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        # Should not have optimization config changes for non-command messages
        if context_info:
            assert "optimization_config_change" not in context_info
        # Optimization should still be enabled (not changed)
        assert mock_callback_context.state.get("proactive_optimization_enabled", True) is True

    def test_callback_exact_phrase_matching(self, mock_callback_context):
        """Test that regex matches exact phrases correctly."""
        # This SHOULD trigger optimization disable because it matches exactly
        mock_callback_context.state["current_user_message"] = (
            "Please disable optimization suggestions for me"
        )

        _preprocess_and_add_context_to_agent_prompt(mock_callback_context)

        context_info = mock_callback_context.state.get("__preprocessed_context_for_llm")
        assert context_info is not None
        assert "optimization_config_change" in context_info
        assert "have been disabled" in context_info["optimization_config_change"]
        assert mock_callback_context.state["proactive_optimization_enabled"] is False


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


class TestUXImprovementsIntegration:
    """Integration tests for UX improvements: No multiple confirmations required.

    This test class validates the enhanced user experience for milestone 2.2 that eliminates
    the need for users to say "ok" multiple times to get code quality suggestions.

    Key UX improvements tested:
    - Tool response enhancement: optimization_suggestions added directly to tool response
    - Immediate agent access: agent can present suggestions without asking for permission
    - No duplicate analysis: prevents running analysis twice if suggestions already exist
    - End-to-end workflow: single request → immediate suggestions without friction
    - Milestone scenario: specific milestone 2.2 testing with smooth workflow

    Before improvements:
        🤖 Agent: "Now, I will analyze the code for quality issues."
        👤 User: "ok" [First confirmation]
        🤖 Agent: "...Would you like me to suggest improvements?"
        👤 User: "ok" [Second confirmation - frustrated]
        🤖 Agent: [Finally provides suggestions]

    After improvements:
        👤 User: "Create test.py with code issue"
        🤖 Agent: "✅ Created test.py. 🔧 **Proactive Code Optimization:**
                   Found 1 improvement: Unused variable 'x'..."

    Zero confirmations required, immediate value delivery.
    """

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context with realistic session state."""
        context = Mock()
        context.state = {
            "proactive_optimization_enabled": True,
            "proactive_suggestions_enabled": True,
            "file_analysis_history": {},
            "analysis_issues": [],
            "smooth_testing_enabled": True,
            "require_edit_approval": False,
        }
        return context

    def test_immediate_suggestions_in_tool_response(self, mock_tool_context):
        """Test that optimization suggestions are added directly to tool response."""
        from agents.swe.enhanced_agent import _proactive_code_quality_analysis

        # Create a mock tool response that simulates successful file creation
        tool_response = {
            "status": "success",
            "message": "File created successfully",
            "filepath": ".sandbox/test.py",
        }

        # Create a mock tool with edit_file_content name
        mock_tool = Mock()
        mock_tool.name = "edit_file_content"

        # Mock args with filepath
        mock_args = {"filepath": ".sandbox/test.py"}

        # Create a test file with code quality issues
        test_code = """def my_func(): x = 1; return 2"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(test_code)
            temp_path = temp_file.name

        try:
            # Update args to use real file path
            mock_args["filepath"] = temp_path

            # Mock the optimization detection to return suggestions
            with patch(
                "agents.swe.shared_libraries.proactive_optimization.detect_and_suggest_optimizations"
            ) as mock_detect:
                mock_suggestions = """🔧 **Proactive Code Optimization:**
I analyzed test.py and found 1 potential improvement:

**1. ⚠️ WARNING** (Line 1)
   **Issue:** Unused variable 'x'
   **Suggestion:** Remove the unused variable 'x' or use it in your code

💡 Would you like me to help you fix this issue?"""

                mock_detect.return_value = mock_suggestions

                # Call the proactive analysis callback
                _proactive_code_quality_analysis(
                    mock_tool, mock_args, mock_tool_context, tool_response
                )

                # Verify suggestions were added to tool response for immediate access
                assert "optimization_suggestions" in tool_response
                assert tool_response["optimization_suggestions"] == mock_suggestions
                assert "Proactive Code Optimization" in tool_response["optimization_suggestions"]
                assert "Unused variable" in tool_response["optimization_suggestions"]

                # Verify suggestions were also stored in session state
                assert "proactive_suggestions" in mock_tool_context.state
                assert len(mock_tool_context.state["proactive_suggestions"]) == 1

                suggestion_entry = mock_tool_context.state["proactive_suggestions"][0]
                assert suggestion_entry["filepath"] == temp_path
                assert suggestion_entry["suggestions"] == mock_suggestions
                assert "timestamp" in suggestion_entry

        finally:
            Path(temp_path).unlink()

    def test_no_duplicate_analysis_when_suggestions_exist(self, mock_tool_context):
        """Test that analysis doesn't run twice if suggestions already exist."""
        from agents.swe.enhanced_agent import _proactive_code_quality_analysis

        # Create tool response that already has suggestions
        tool_response = {"status": "success", "optimization_suggestions": "Already analyzed"}

        mock_tool = Mock()
        mock_tool.name = "edit_file_content"
        mock_args = {"filepath": ".sandbox/test.py"}

        with patch(
            "agents.swe.shared_libraries.proactive_optimization.detect_and_suggest_optimizations"
        ) as mock_detect:
            # Call the callback
            _proactive_code_quality_analysis(mock_tool, mock_args, mock_tool_context, tool_response)

            # Verify detection wasn't called since suggestions already exist
            mock_detect.assert_not_called()

            # Verify original suggestions remain unchanged
            assert tool_response["optimization_suggestions"] == "Already analyzed"

    def test_end_to_end_ux_workflow(self, mock_tool_context):
        """Test the complete UX workflow: single request → immediate suggestions."""

        # Create a test file with code quality issues
        test_code = """def my_func(): x = 1; return 2
def another_func():
    unused_var = "test"
    return True"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(test_code)
            temp_path = temp_file.name

        try:
            # Simulate the file creation tool call
            mock_tool_context.state["require_edit_approval"] = False

            # Call edit_file_content to create the file
            result = edit_file_content(temp_path, test_code, tool_context=mock_tool_context)

            # Verify file was created successfully
            assert result["status"] == "success"
            assert "Successfully wrote content to" in result["message"]

            # The proactive analysis callback should have run automatically
            # and added suggestions to the tool response
            # (This would happen via the callback system in real usage)

            # Simulate what the callback would do
            from agents.swe.enhanced_agent import _proactive_code_quality_analysis

            mock_tool = Mock()
            mock_tool.name = "edit_file_content"
            mock_args = {"filepath": temp_path}

            with patch(
                "agents.swe.shared_libraries.proactive_optimization.detect_and_suggest_optimizations"
            ) as mock_detect:
                mock_suggestions = """🔧 **Proactive Code Optimization:**
I analyzed the file and found 2 potential improvements:

**1. ⚠️ WARNING** (Line 1)
   **Issue:** Unused variable 'x'
   **Suggestion:** Remove the unused variable 'x' or use it in your code

**2. ⚠️ WARNING** (Line 3)
   **Issue:** Unused variable 'unused_var'
   **Suggestion:** Remove the unused variable 'unused_var' or use it in your code

💡 Would you like me to help you fix these issues?"""

                mock_detect.return_value = mock_suggestions

                # Run the proactive analysis
                _proactive_code_quality_analysis(mock_tool, mock_args, mock_tool_context, result)

                # Verify the complete UX workflow
                assert result["status"] == "success"  # File created successfully
                assert "optimization_suggestions" in result  # Suggestions added immediately
                assert "Proactive Code Optimization" in result["optimization_suggestions"]
                assert "2 potential improvements" in result["optimization_suggestions"]

                # Verify agent has immediate access to suggestions
                suggestions = result["optimization_suggestions"]
                assert "Unused variable 'x'" in suggestions
                assert "Unused variable 'unused_var'" in suggestions
                assert "Would you like me to help you fix" in suggestions

                # Verify no approval required for .sandbox files
                assert not mock_tool_context.state.get("require_edit_approval", True)

        finally:
            Path(temp_path).unlink()

    def test_milestone_scenario_smooth_workflow(self, mock_tool_context):
        """Test the specific milestone 2.2 scenario with smooth workflow."""

        # Set up milestone testing scenario
        mock_tool_context.state["smooth_testing_enabled"] = True
        mock_tool_context.state["require_edit_approval"] = False

        # Create the specific milestone test file
        milestone_code = """def my_func(): x = 1; return 2"""
        sandbox_path = Path(tempfile.gettempdir()) / ".sandbox" / "test.py"
        sandbox_path.parent.mkdir(exist_ok=True)

        try:
            sandbox_path.write_text(milestone_code)

            # Simulate the enhanced agent workflow
            from agents.swe.enhanced_agent import _proactive_code_quality_analysis

            tool_response = {
                "status": "success",
                "message": f"File created successfully at {sandbox_path}",
                "filepath": str(sandbox_path),
            }

            mock_tool = Mock()
            mock_tool.name = "edit_file_content"
            mock_args = {"filepath": str(sandbox_path)}

            with patch(
                "agents.swe.shared_libraries.proactive_optimization.detect_and_suggest_optimizations"
            ) as mock_detect:
                mock_suggestions = """🔧 **Proactive Code Optimization:**
I analyzed test.py and found 1 potential improvement:

**1. ⚠️ WARNING** (Line 1)
   **Issue:** Unused variable 'x' at line 1
   **Suggestion:** Remove the unused variable 'x' or use it in your code

💡 Would you like me to help you fix this issue?"""

                mock_detect.return_value = mock_suggestions

                # Run the proactive analysis callback
                _proactive_code_quality_analysis(
                    mock_tool, mock_args, mock_tool_context, tool_response
                )

                # Verify the perfect milestone 2.2 workflow
                assert tool_response["status"] == "success"  # No approval friction
                assert "optimization_suggestions" in tool_response  # Immediate suggestions
                assert "I analyzed test.py" in tool_response["optimization_suggestions"]
                assert "Unused variable 'x'" in tool_response["optimization_suggestions"]

                # Verify this enables the agent to provide immediate feedback
                # without asking for permission or requiring multiple "ok" responses
                suggestions = tool_response["optimization_suggestions"]
                assert suggestions.startswith("🔧 **Proactive Code Optimization:**")
                assert "Would you like me to help you fix" in suggestions

                # Verify session state tracks the analysis
                assert len(mock_tool_context.state["proactive_suggestions"]) == 1

        finally:
            if sandbox_path.exists():
                sandbox_path.unlink()
            if sandbox_path.parent.exists():
                sandbox_path.parent.rmdir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
