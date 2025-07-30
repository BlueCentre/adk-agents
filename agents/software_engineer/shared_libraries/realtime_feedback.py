"""Real-time Syntax and Style Feedback System.

This module implements Milestone 4.1: Real-time Syntax and Basic Style Feedback
by providing immediate feedback on syntax errors and style violations before
code is proposed for approval.
"""

import ast
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Optional

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


class SyntaxIssue:
    """Represents a syntax or style issue found in code."""

    def __init__(
        self,
        line: int,
        column: int,
        severity: str,
        message: str,
        suggestion: Optional[str] = None,
        fix_type: str = "manual",
    ):
        self.line = line
        self.column = column
        self.severity = severity  # "critical", "error", "warning", "info"
        self.message = message
        self.suggestion = suggestion
        self.fix_type = fix_type  # "automatic", "manual", "suggestion"


class RealtimeFeedbackEngine:
    """Provides real-time syntax and style feedback for code."""

    def __init__(self):
        """Initialize the real-time feedback engine."""
        self.supported_languages = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
        }

    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        suffix = Path(file_path).suffix.lower()
        return self.supported_languages.get(suffix, "unknown")

    def validate_python_syntax(self, code: str, _file_path: str) -> list[SyntaxIssue]:
        """Validate Python syntax and detect basic issues."""
        issues = []

        try:
            # Basic syntax check using AST
            ast.parse(code)
        except SyntaxError as e:
            # Create detailed syntax error message
            suggestion = self._suggest_python_syntax_fix(e, code)
            issues.append(
                SyntaxIssue(
                    line=e.lineno or 1,
                    column=e.offset or 1,
                    severity="critical",
                    message=f"Syntax Error: {e.msg}",
                    suggestion=suggestion,
                    fix_type="manual",
                )
            )
            return issues  # Return early for syntax errors

        # Additional lightweight checks if syntax is valid
        issues.extend(self._check_python_style_basics(code))

        return issues

    def _suggest_python_syntax_fix(self, syntax_error: SyntaxError, code: str) -> Optional[str]:
        """Suggest fixes for common Python syntax errors."""
        msg = syntax_error.msg.lower()

        if "expected ':'" in msg:
            return f"Add ':' at the end of line {syntax_error.lineno}"
        if "invalid syntax" in msg:
            lines = code.split("\n")
            error_line_idx = (syntax_error.lineno or 1) - 1

            if error_line_idx < len(lines):
                line = lines[error_line_idx]

                # Check for missing colons
                if any(
                    keyword in line
                    for keyword in [
                        "if ",
                        "else:",
                        "for ",
                        "while ",
                        "def ",
                        "class ",
                        "try:",
                        "except:",
                        "finally:",
                    ]
                ):
                    if not line.rstrip().endswith(":"):
                        return f"Add ':' at the end of line {syntax_error.lineno}"

                # Check for unmatched parentheses/brackets
                if line.count("(") != line.count(")"):
                    return f"Check parentheses matching on line {syntax_error.lineno}"
                if line.count("[") != line.count("]"):
                    return f"Check bracket matching on line {syntax_error.lineno}"
                if line.count("{") != line.count("}"):
                    return f"Check brace matching on line {syntax_error.lineno}"

        elif "unexpected eof" in msg:
            return "Check for unclosed parentheses, brackets, or quotes"

        elif "unexpected indent" in msg:
            return f"Fix indentation on line {syntax_error.lineno}"

        return None

    def _check_python_style_basics(self, code: str) -> list[SyntaxIssue]:
        """Check basic Python style issues."""
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for lines too long (basic check)
            if len(line) > 100:
                issues.append(
                    SyntaxIssue(
                        line=i,
                        column=100,
                        severity="warning",
                        message=f"Line too long ({len(line)} characters)",
                        suggestion="Consider breaking the line",
                        fix_type="manual",
                    )
                )

            # Check for trailing whitespace
            if line.endswith((" ", "\t")):
                issues.append(
                    SyntaxIssue(
                        line=i,
                        column=len(line),
                        severity="info",
                        message="Trailing whitespace",
                        suggestion="Remove trailing whitespace",
                        fix_type="automatic",
                    )
                )

            # Check for mixed tabs and spaces (basic)
            if "\t" in line and "    " in line:
                issues.append(
                    SyntaxIssue(
                        line=i,
                        column=1,
                        severity="warning",
                        message="Mixed tabs and spaces",
                        suggestion="Use consistent indentation (spaces recommended)",
                        fix_type="manual",
                    )
                )

        return issues

    def validate_javascript_syntax(self, code: str, _file_path: str) -> list[SyntaxIssue]:
        """Validate JavaScript/TypeScript syntax using lightweight checks."""
        issues = []
        lines = code.split("\n")

        # Basic syntax checks
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for missing semicolons (basic heuristic)
            if (
                stripped
                and not stripped.endswith((";", "{", "}", ":", ",", ")", "\\"))
                and not stripped.startswith(("if", "else", "for", "while", "function", "class"))
                and (
                    "return " in stripped
                    or stripped.startswith(("let ", "const ", "var "))
                    or "=" in stripped
                    or "console." in stripped
                )
            ):
                issues.append(
                    SyntaxIssue(
                        line=i,
                        column=len(line),
                        severity="warning",
                        message="Missing semicolon",
                        suggestion="Add semicolon at end of statement",
                        fix_type="automatic",
                    )
                )

            # Check for console.log statements (should be removed in production)
            if "console.log" in stripped.lower():
                issues.append(
                    SyntaxIssue(
                        line=i,
                        column=line.lower().find("console.log") + 1,
                        severity="info",
                        message="Console.log statement found",
                        suggestion="Remove console.log statements in production code",
                        fix_type="manual",
                    )
                )

        return issues

    def run_lightweight_ruff_check(self, code: str, _file_path: str) -> list[SyntaxIssue]:
        """Run lightweight ruff check if available."""
        issues = []

        try:
            # Create temporary file for ruff analysis
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name

            # Run ruff with minimal rule set for quick feedback
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "ruff",
                    "check",
                    temp_path,
                    "--select",
                    "E9,F63,F7,F82",  # Only syntax errors and undefined names
                    "--output-format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # No issues found
                pass
            else:
                # Parse ruff output if it's JSON
                try:
                    import json

                    ruff_issues = json.loads(result.stdout)
                    for issue in ruff_issues:
                        issues.append(
                            SyntaxIssue(
                                line=issue.get("location", {}).get("row", 1),
                                column=issue.get("location", {}).get("column", 1),
                                severity="error"
                                if issue.get("code", "").startswith("E9")
                                else "warning",
                                message=f"Ruff {issue.get('code', '')}: {issue.get('message', '')}",
                                fix_type="manual",
                            )
                        )
                except (json.JSONDecodeError, KeyError):
                    # Fallback to text parsing or ignore
                    pass

            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"Ruff check failed or unavailable: {e}")

        return issues

    def validate_code_realtime(self, code: str, file_path: str) -> tuple[bool, list[SyntaxIssue]]:
        """
        Validate code in real-time before approval.

        Args:
            code: The code content to validate
            file_path: Path to the file being edited

        Returns:
            Tuple of (has_critical_issues, list_of_issues)
        """
        language = self.detect_language(file_path)
        issues = []

        if language == "python":
            # Check syntax first
            issues.extend(self.validate_python_syntax(code, file_path))

            # Run lightweight ruff if no critical syntax errors
            critical_issues = [i for i in issues if i.severity == "critical"]
            if not critical_issues:
                issues.extend(self.run_lightweight_ruff_check(code, file_path))

        elif language in ["javascript", "typescript"]:
            issues.extend(self.validate_javascript_syntax(code, file_path))

        # Check if there are critical issues that should block approval
        has_critical_issues = any(issue.severity == "critical" for issue in issues)

        return has_critical_issues, issues

    def format_issues_for_user(self, issues: list[SyntaxIssue]) -> str:
        """Format issues for user-friendly display."""
        if not issues:
            return "✅ No syntax or style issues found."

        formatted = ["🔍 **Real-time Code Analysis Results:**\n"]

        # Group by severity
        critical = [i for i in issues if i.severity == "critical"]
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        info = [i for i in issues if i.severity == "info"]

        if critical:
            formatted.append("🚨 **Critical Issues (must fix):**")
            for issue in critical:
                formatted.append(f"   Line {issue.line}, Col {issue.column}: {issue.message}")
                if issue.suggestion:
                    formatted.append(f"   💡 Suggestion: {issue.suggestion}")
            formatted.append("")

        if errors:
            formatted.append("❌ **Errors:**")
            for issue in errors:
                formatted.append(f"   Line {issue.line}, Col {issue.column}: {issue.message}")
                if issue.suggestion:
                    formatted.append(f"   💡 Suggestion: {issue.suggestion}")
            formatted.append("")

        if warnings:
            formatted.append("⚠️ **Warnings:**")
            for issue in warnings[:3]:  # Limit to 3 warnings for brevity
                formatted.append(f"   Line {issue.line}, Col {issue.column}: {issue.message}")
                if issue.suggestion:
                    formatted.append(f"   💡 Suggestion: {issue.suggestion}")
            if len(warnings) > 3:
                formatted.append(f"   ... and {len(warnings) - 3} more warnings")
            formatted.append("")

        if info:
            formatted.append("💡 **Style Suggestions:**")
            for issue in info[:2]:  # Limit to 2 info items for brevity
                formatted.append(f"   Line {issue.line}, Col {issue.column}: {issue.message}")
            if len(info) > 2:
                formatted.append(f"   ... and {len(info) - 2} more style suggestions")

        return "\n".join(formatted)

    def get_automatic_fixes(self, code: str, issues: list[SyntaxIssue]) -> str:
        """Apply automatic fixes where possible."""
        lines = code.split("\n")

        for issue in issues:
            if issue.fix_type == "automatic":
                if issue.message == "Trailing whitespace":
                    # Fix trailing whitespace
                    if issue.line <= len(lines):
                        lines[issue.line - 1] = lines[issue.line - 1].rstrip()
                elif issue.message == "Missing semicolon":
                    # Add semicolon for JavaScript
                    if issue.line <= len(lines):
                        lines[issue.line - 1] = lines[issue.line - 1].rstrip() + ";"

        return "\n".join(lines)


# Global instance for reuse
_feedback_engine = RealtimeFeedbackEngine()


def handle_critical_issues_feedback(
    critical_issues_response: dict[str, Any],
    tool_context: ToolContext,
    user_choice: Optional[str] = None,
) -> dict[str, Any]:
    """
    Handle critical issues feedback and provide options for resolution.

    Args:
        critical_issues_response: The response from edit_file_content with critical issues
        tool_context: Tool context for state management
        user_choice: Optional user choice for handling issues
            ("auto_fix", "manual", "ignore", "retry")

    Returns:
        Dict with next steps or final resolution
    """
    try:
        filepath = critical_issues_response.get("proposed_filepath", "")
        content = critical_issues_response.get("proposed_content", "")
        can_auto_fix = critical_issues_response.get("can_auto_fix", False)
        auto_fixed_code = critical_issues_response.get("auto_fixed_code")

        # If user hasn't provided a choice, present options
        if user_choice is None:
            options = ["manual"]  # Always offer manual fix option

            if can_auto_fix and auto_fixed_code:
                options.insert(0, "auto_fix")  # Prioritize auto-fix if available

            # For testing or non-critical workflows, allow ignore option
            if tool_context.state.get("allow_ignore_critical_issues", False):
                options.append("ignore")

            return {
                "status": "awaiting_user_choice",
                "message": "Critical syntax issues found. How would you like to proceed?",
                "options": options,
                "feedback": critical_issues_response.get("feedback", ""),
                "can_auto_fix": can_auto_fix,
                "auto_fix_preview": auto_fixed_code if can_auto_fix else None,
                "filepath": filepath,
                "original_content": content,
            }

        # Process user choice
        if user_choice == "auto_fix" and can_auto_fix and auto_fixed_code:
            logger.info(f"Applying automatic fixes to {filepath}")

            # Recursively call edit_file_content with fixed code (skip validation this time)
            tool_context.state["skip_realtime_validation"] = True
            try:
                from ..tools.filesystem import edit_file_content

                result = edit_file_content(filepath, auto_fixed_code, tool_context)

                if result.get("status") == "success":
                    return {
                        "status": "auto_fixed_and_applied",
                        "message": (
                            f"✅ Automatically fixed issues and applied changes to '{filepath}'"
                        ),
                        "applied_fixes": "Trailing whitespace removed, semicolons added, etc.",
                        "final_content": auto_fixed_code,
                    }
                return {
                    "status": "auto_fix_failed",
                    "message": (
                        f"❌ Auto-fix succeeded but file write failed: "
                        f"{result.get('message', 'Unknown error')}"
                    ),
                    "original_issue": critical_issues_response.get("feedback", ""),
                    "write_error": result,
                }
            finally:
                # Re-enable validation for future operations
                tool_context.state.pop("skip_realtime_validation", None)

        elif user_choice == "manual":
            return {
                "status": "manual_fix_requested",
                "message": "Please manually fix the issues and try again:",
                "feedback": critical_issues_response.get("feedback", ""),
                "filepath": filepath,
                "suggested_actions": [
                    "Fix the syntax errors mentioned above",
                    "Re-run the edit command with corrected code",
                    "Use 'auto_fix' option if automatic fixes are available",
                ],
            }

        elif user_choice == "ignore" and tool_context.state.get(
            "allow_ignore_critical_issues", False
        ):
            logger.warning(f"User chose to ignore critical issues in {filepath}")

            # Force the edit despite critical issues
            tool_context.state["skip_realtime_validation"] = True
            try:
                from ..tools.filesystem import edit_file_content

                result = edit_file_content(filepath, content, tool_context)
                return {
                    "status": "critical_issues_ignored",
                    "message": (
                        f"⚠️ File written despite critical issues: {result.get('message', '')}"
                    ),
                    "warning": "Code may not function correctly due to syntax errors",
                    "ignored_feedback": critical_issues_response.get("feedback", ""),
                }
            finally:
                tool_context.state.pop("skip_realtime_validation", None)

        elif user_choice == "retry":
            return {
                "status": "retry_requested",
                "message": "Please provide the corrected code and try again.",
                "feedback": critical_issues_response.get("feedback", ""),
                "filepath": filepath,
            }

        else:
            return {
                "status": "invalid_choice",
                "message": (
                    f"Invalid choice '{user_choice}'. Available options: auto_fix, manual, retry"
                ),
                "feedback": critical_issues_response.get("feedback", ""),
            }

    except Exception as e:
        logger.error(f"Error handling critical issues feedback: {e}")
        return {
            "status": "feedback_handler_error",
            "message": f"Error processing feedback: {e}",
            "original_feedback": critical_issues_response.get("feedback", ""),
        }


def validate_code_before_approval(
    code: str, file_path: str, tool_context: ToolContext
) -> dict[str, Any]:
    """
    Main entry point for real-time code validation.

    Args:
        code: Code content to validate
        file_path: Path to the file
        tool_context: Tool context for state management

    Returns:
        Dict with validation results
    """
    try:
        has_critical_issues, issues = _feedback_engine.validate_code_realtime(code, file_path)

        # Store issues in session state for potential later reference
        if "realtime_feedback_issues" not in tool_context.state:
            tool_context.state["realtime_feedback_issues"] = {}

        tool_context.state["realtime_feedback_issues"][file_path] = [
            {
                "line": issue.line,
                "column": issue.column,
                "severity": issue.severity,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "fix_type": issue.fix_type,
            }
            for issue in issues
        ]

        return {
            "has_critical_issues": has_critical_issues,
            "issues": issues,
            "formatted_feedback": _feedback_engine.format_issues_for_user(issues),
            "can_auto_fix": any(issue.fix_type == "automatic" for issue in issues),
            "auto_fixed_code": _feedback_engine.get_automatic_fixes(code, issues)
            if any(issue.fix_type == "automatic" for issue in issues)
            else None,
        }

    except Exception as e:
        logger.error(f"Error in real-time code validation: {e}")
        return {
            "has_critical_issues": False,
            "issues": [],
            "formatted_feedback": f"⚠️ Validation error: {e}",
            "can_auto_fix": False,
            "auto_fixed_code": None,
        }
