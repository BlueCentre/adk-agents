"""Integration tests for real-time syntax and style feedback system (Milestone 4.1).

These tests verify that the real-time feedback system correctly identifies syntax
errors, provides appropriate suggestions, and integrates properly with the file
editing workflow.
"""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from google.adk.tools import ToolContext
import pytest

# Import the modules to test
from agents.software_engineer.shared_libraries.realtime_feedback import (
    RealtimeFeedbackEngine,
    handle_critical_issues_feedback,
    validate_code_before_approval,
)
from agents.software_engineer.tools.filesystem import edit_file_content
from agents.software_engineer.tools.realtime_feedback_handler import (
    configure_realtime_feedback,
    get_feedback_options,
)


class TestRealtimeFeedbackEngineUnit:
    """Unit tests for the RealtimeFeedbackEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = RealtimeFeedbackEngine()

    def test_detect_language(self):
        """Test language detection from file extensions."""
        assert self.engine.detect_language("test.py") == "python"
        assert self.engine.detect_language("test.js") == "javascript"
        assert self.engine.detect_language("test.ts") == "typescript"
        assert self.engine.detect_language("test.jsx") == "javascript"
        assert self.engine.detect_language("test.tsx") == "typescript"
        assert self.engine.detect_language("test.txt") == "unknown"

    def test_python_syntax_validation_valid_code(self):
        """Test Python syntax validation with valid code."""
        valid_python = """
def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
"""
        issues = self.engine.validate_python_syntax(valid_python, "test.py")
        # Should have no critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        assert len(critical_issues) == 0

    def test_python_syntax_validation_syntax_error(self):
        """Test Python syntax validation with syntax errors."""
        invalid_python = """
def hello_world()  # Missing colon
    print("Hello, World!")
    return True
"""
        issues = self.engine.validate_python_syntax(invalid_python, "test.py")

        # Should have at least one critical issue
        critical_issues = [i for i in issues if i.severity == "critical"]
        assert len(critical_issues) > 0
        assert "Syntax Error" in critical_issues[0].message
        assert critical_issues[0].suggestion is not None

    def test_python_syntax_validation_indentation_error(self):
        """Test Python syntax validation with indentation errors."""
        invalid_python = """
def hello_world():
print("Hello, World!")  # Wrong indentation
    return True
"""
        issues = self.engine.validate_python_syntax(invalid_python, "test.py")
        critical_issues = [i for i in issues if i.severity == "critical"]
        assert len(critical_issues) > 0

    def test_python_style_checks(self):
        """Test basic Python style checks."""
        # Construct code with trailing whitespace programmatically to avoid linter removal
        style_issues_code = """
def hello_world():
    x = 1    # Trailing spaces{}
    very_long_line_that_exceeds_the_hundred_character_limit_and_should_definitely_trigger_a_warning_message = "test"
    print("Hello, World!")
""".format("   ")  # noqa: E501 Add trailing spaces
        issues = self.engine.validate_python_syntax(style_issues_code, "test.py")

        # Should find trailing whitespace and long line
        trailing_ws = [i for i in issues if "Trailing whitespace" in i.message]
        long_line = [i for i in issues if "Line too long" in i.message]

        assert len(trailing_ws) > 0
        assert len(long_line) > 0
        assert trailing_ws[0].fix_type == "automatic"

    def test_javascript_validation(self):
        """Test JavaScript syntax validation."""
        js_code = """
function hello() {
    let x = 5
    console.log("Hello")
    return x
}
"""
        issues = self.engine.validate_javascript_syntax(js_code, "test.js")

        # Should find missing semicolons and console.log
        semicolon_issues = [i for i in issues if "Missing semicolon" in i.message]
        console_issues = [i for i in issues if "Console.log" in i.message]

        assert len(semicolon_issues) > 0
        assert len(console_issues) > 0

    def test_automatic_fixes(self):
        """Test automatic fix functionality."""
        code_with_fixable_issues = """
function test() {{
    let x = 5{}
    return x
}}
""".format("   ")  # Add trailing spaces
        issues = self.engine.validate_javascript_syntax(code_with_fixable_issues, "test.js")
        fixed_code = self.engine.get_automatic_fixes(code_with_fixable_issues, issues)

        # Should have removed trailing whitespace and added semicolons
        assert "   \n" not in fixed_code  # No trailing spaces
        assert "return x;" in fixed_code  # Semicolon added


class TestRealtimeFeedbackIntegration:
    """Integration tests for real-time feedback with file operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool_context = MagicMock(spec=ToolContext)
        self.tool_context.state = {}

    def test_validate_code_before_approval_valid_code(self):
        """Test validation of valid code."""
        valid_python = """
def calculate_sum(a, b):
    return a + b

result = calculate_sum(1, 2)
print(result)
"""
        result = validate_code_before_approval(valid_python, "test.py", self.tool_context)

        assert result["has_critical_issues"] is False
        assert len(result["issues"]) >= 0  # May have style suggestions
        assert "✅" in result["formatted_feedback"]

    def test_validate_code_before_approval_critical_issues(self):
        """Test validation of code with critical syntax errors."""
        invalid_python = """
def calculate_sum(a, b)  # Missing colon
    return a + b

result = calculate_sum(1, 2
print(result)  # Missing closing parenthesis
"""
        result = validate_code_before_approval(invalid_python, "test.py", self.tool_context)

        assert result["has_critical_issues"] is True
        assert len(result["issues"]) > 0
        assert "🚨" in result["formatted_feedback"]
        assert result["can_auto_fix"] is False  # Syntax errors can't be auto-fixed

    def test_validate_code_before_approval_auto_fixable(self):
        """Test validation of code with auto-fixable issues."""
        fixable_code = """
def test():
    x = 5{}
    return x
""".format("   ")  # Add trailing spaces
        result = validate_code_before_approval(fixable_code, "test.py", self.tool_context)

        assert result["has_critical_issues"] is False
        assert result["can_auto_fix"] is True
        assert result["auto_fixed_code"] is not None
        assert "   \n" not in result["auto_fixed_code"]  # Trailing spaces removed


class TestEditFileContentIntegration:
    """Integration tests for edit_file_content with real-time feedback."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool_context = MagicMock(spec=ToolContext)
        self.tool_context.state = {
            "require_edit_approval": False,  # Skip approval for testing
            "realtime_feedback_enabled": True,
        }
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_edit_file_valid_code_no_approval(self):
        """Test editing a file with valid code (no approval required)."""
        valid_python = """
def hello():
    print("Hello, World!")
    return True
"""
        test_file = Path(self.temp_dir) / "test.py"

        result = edit_file_content(str(test_file), valid_python, self.tool_context)

        assert result["status"] == "success"
        assert test_file.exists()
        assert test_file.read_text() == valid_python

    def test_edit_file_critical_issues_blocks_write(self):
        """Test that critical syntax issues block file writing."""
        invalid_python = """
def hello()  # Missing colon
    print("Hello, World!")
    return True
"""
        test_file = Path(self.temp_dir) / "test.py"

        result = edit_file_content(str(test_file), invalid_python, self.tool_context)

        assert result["status"] == "critical_issues"
        assert "feedback" in result
        assert "🚨" in result["feedback"]
        assert not test_file.exists()  # File should not be created

    def test_edit_file_with_approval_includes_feedback(self):
        """Test that approval requests include real-time feedback."""
        self.tool_context.state["require_edit_approval"] = True

        code_with_warnings = """
def test():
    x = 5    # Trailing spaces{}
    very_long_line_that_exceeds_the_hundred_character_limit_and_should_trigger_a_warning = "test"
    return x
""".format("   ")  # Add trailing spaces
        test_file = Path(self.temp_dir) / "test.py"

        result = edit_file_content(str(test_file), code_with_warnings, self.tool_context)

        assert result["status"] == "pending_approval"
        assert "realtime_feedback" in result
        assert "💡" in result["message"]  # Should include style suggestions in approval message

    def test_edit_file_feedback_disabled(self):
        """Test that feedback can be disabled."""
        self.tool_context.state["realtime_feedback_enabled"] = False

        invalid_python = """
def hello()  # Missing colon - should not be caught
    print("Hello, World!")
"""
        test_file = Path(self.temp_dir) / "test.py"

        result = edit_file_content(str(test_file), invalid_python, self.tool_context)

        # Should succeed despite syntax error because feedback is disabled
        assert result["status"] == "success"
        assert test_file.exists()


class TestCriticalIssuesHandler:
    """Integration tests for critical issues handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool_context = MagicMock(spec=ToolContext)
        self.tool_context.state = {}

        self.critical_response = {
            "status": "critical_issues",
            "feedback": (
                "🚨 **Critical Issues (must fix):**\n"
                "   Line 1, Col 18: Syntax Error: invalid syntax"
            ),
            "can_auto_fix": False,
            "auto_fixed_code": None,
            "proposed_filepath": "test.py",
            "proposed_content": "def test()  # Missing colon",
            "message": "Critical syntax issues must be resolved before proceeding",
        }

    def test_handle_critical_issues_get_options(self):
        """Test getting options for handling critical issues."""
        result = handle_critical_issues_feedback(self.critical_response, self.tool_context, None)

        assert result["status"] == "awaiting_user_choice"
        assert "options" in result
        assert "manual" in result["options"]
        assert result["can_auto_fix"] is False

    def test_handle_critical_issues_manual_choice(self):
        """Test choosing manual fix for critical issues."""
        result = handle_critical_issues_feedback(
            self.critical_response, self.tool_context, "manual"
        )

        assert result["status"] == "manual_fix_requested"
        assert "suggested_actions" in result
        assert "Fix the syntax errors" in result["suggested_actions"][0]

    def test_handle_critical_issues_auto_fix_when_available(self):
        """Test auto-fix when available."""
        auto_fixable_response = self.critical_response.copy()
        auto_fixable_response.update(
            {"can_auto_fix": True, "auto_fixed_code": "def test():  # Fixed colon"}
        )

        with patch("agents.software_engineer.tools.filesystem.edit_file_content") as mock_edit:
            mock_edit.return_value = {"status": "success", "message": "File written"}

            result = handle_critical_issues_feedback(
                auto_fixable_response, self.tool_context, "auto_fix"
            )

            assert result["status"] == "auto_fixed_and_applied"
            assert "✅" in result["message"]
            mock_edit.assert_called_once()

    def test_configure_realtime_feedback_tool(self):
        """Test the configuration tool for real-time feedback."""
        result = configure_realtime_feedback(
            enabled=True, allow_ignore_critical=True, tool_context=self.tool_context
        )

        assert result["status"] == "configured"
        assert self.tool_context.state["realtime_feedback_enabled"] is True
        assert self.tool_context.state["allow_ignore_critical_issues"] is True

    def test_feedback_options_tool(self):
        """Test the get_feedback_options tool."""
        result = get_feedback_options(self.critical_response, self.tool_context)

        assert result["status"] == "awaiting_user_choice"
        assert "options" in result


class TestEndToEndWorkflow:
    """End-to-end integration tests for the complete workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool_context = MagicMock(spec=ToolContext)
        self.tool_context.state = {
            "require_edit_approval": False,
            "realtime_feedback_enabled": True,
        }
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_workflow_syntax_error_to_fix(self):
        """Test complete workflow from syntax error detection to resolution."""
        # Step 1: Try to write invalid code
        invalid_code = """
def calculate(a, b)  # Missing colon
    return a + b
"""
        test_file = Path(self.temp_dir) / "calc.py"

        result1 = edit_file_content(str(test_file), invalid_code, self.tool_context)
        assert result1["status"] == "critical_issues"

        # Step 2: Get options for handling
        options_result = get_feedback_options(result1, self.tool_context)
        assert options_result["status"] == "awaiting_user_choice"
        assert "manual" in options_result["options"]

        # Step 3: Choose manual fix and provide corrected code
        fixed_code = """
def calculate(a, b):  # Fixed colon
    return a + b
"""
        result2 = edit_file_content(str(test_file), fixed_code, self.tool_context)
        assert result2["status"] == "success"
        assert test_file.exists()
        assert "def calculate(a, b):" in test_file.read_text()

    def test_workflow_with_auto_fixable_issues(self):
        """Test workflow with automatically fixable issues."""
        # Code with trailing whitespace (auto-fixable)
        fixable_code = """
def test():
    x = 5{}
    return x
""".format("   ")  # Add trailing spaces
        test_file = Path(self.temp_dir) / "test.py"

        # This should succeed because trailing whitespace is not critical
        result = edit_file_content(str(test_file), fixable_code, self.tool_context)
        assert result["status"] == "success"

        # Verify the file was created
        assert test_file.exists()
        file_content = test_file.read_text()

        # The trailing spaces should still be there since it's not critical
        # Real-time feedback only blocks critical issues
        assert "   " in file_content  # Check for trailing spaces somewhere in content


# Test fixtures and utilities
@pytest.fixture
def sample_python_files():
    """Provide sample Python files for testing."""
    return {
        "valid": """
def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
""",
        "syntax_error": """
def hello_world()  # Missing colon
    print("Hello, World!")
    return True
""",
        "style_issues": """
def test():
    x = 5   # Trailing spaces
    very_long_line_that_exceeds_the_hundred_character_limit_and_should_trigger_a_warning = "test"
    return x
""",
        "auto_fixable": """
function test() {
    let x = 5
    return x
}
""",
    }


class TestRealtimeFeedbackUserVerification:
    """Tests that simulate user verification scenarios from the milestone."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool_context = MagicMock(spec=ToolContext)
        self.tool_context.state = {
            "require_edit_approval": False,
            "realtime_feedback_enabled": True,
        }
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_user_verification_syntax_error_detection(self):
        """
        User Verification Step 1: Execute a command that results in syntactically
        incorrect code and verify the agent catches the error.
        """
        # Simulate asking agent to write syntactically incorrect code
        test_file = Path(self.temp_dir) / "test.py"

        # Even though this code is technically valid Python, let's test with clearly invalid syntax
        clearly_invalid = """
def my_func()  # Missing colon
    x = 1
    return 2
"""

        result = edit_file_content(str(test_file), clearly_invalid, self.tool_context)

        # Verify the agent catches the syntax error
        assert result["status"] == "critical_issues"
        assert "Syntax Error" in result["feedback"]
        assert not test_file.exists()  # File should not be created

        print("✅ User Verification 1: Agent correctly detects syntax errors")

    def test_user_verification_style_violation_detection(self):
        """
        User Verification Step 2: Create code with style violations and verify
        the agent provides feedback.
        """
        style_violation_code = """
def foo():
    x = 1    # Trailing spaces{}
    very_long_line_that_definitely_exceeds_the_hundred_character_limit = True
    return x
""".format("   ")  # Add trailing spaces
        test_file = Path(self.temp_dir) / "style_test.py"

        # With approval enabled to see the feedback
        self.tool_context.state["require_edit_approval"] = True

        result = edit_file_content(str(test_file), style_violation_code, self.tool_context)

        assert result["status"] == "pending_approval"
        assert "realtime_feedback" in result
        feedback = result["realtime_feedback"]

        # Should detect style issues
        assert "Trailing whitespace" in feedback or "Line too long" in feedback or "⚠️" in feedback

        print("✅ User Verification 2: Agent correctly detects style violations")

    def test_user_verification_immediate_feedback_loop(self):
        """
        User Verification Step 3: Verify the agent provides immediate feedback
        and correction suggestions.
        """
        # Test with code that has a clear syntax error with a suggested fix
        syntax_error_code = """
if True  # Missing colon
    print("Hello")
"""
        test_file = Path(self.temp_dir) / "feedback_test.py"

        result = edit_file_content(str(test_file), syntax_error_code, self.tool_context)

        assert result["status"] == "critical_issues"
        assert "feedback" in result

        # Should provide suggestion
        feedback = result["feedback"]
        assert "💡 Suggestion:" in feedback or "Add ':'" in feedback

        print("✅ User Verification 3: Agent provides immediate feedback and suggestions")


if __name__ == "__main__":
    # Run a quick smoke test
    engine = RealtimeFeedbackEngine()

    # Test basic functionality
    valid_code = "def test():\n    return True"
    invalid_code = "def test()\n    return True"  # Missing colon

    valid_issues = engine.validate_python_syntax(valid_code, "test.py")
    invalid_issues = engine.validate_python_syntax(invalid_code, "test.py")

    print(f"Valid code issues: {len(valid_issues)}")
    print(f"Invalid code issues: {len(invalid_issues)}")
    critical_count = len([i for i in invalid_issues if i.severity == "critical"])
    print(f"Critical issues in invalid code: {critical_count}")

    if len([i for i in invalid_issues if i.severity == "critical"]) > 0:
        print("✅ Smoke test passed: Real-time feedback system is working")
    else:
        print("❌ Smoke test failed: Critical issues not detected")
