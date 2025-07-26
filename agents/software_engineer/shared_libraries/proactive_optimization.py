"""Proactive Optimization Suggestions System.

This module implements Milestone 2.2: Proactive Optimization Suggestions
by automatically triggering code analysis on file modifications and presenting
intelligent suggestions for code quality improvements.
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path
import re
from typing import Any, Optional

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# Configuration constants
MAX_SUGGESTIONS_TO_DISPLAY = 5
MAX_RECENT_SUGGESTIONS = 3
ANALYSIS_COOLDOWN_MINUTES = 2  # Prevent too frequent analysis
MAX_ANALYSIS_HISTORY_SIZE = 50  # Limit analysis history to prevent memory bloat


class ProactiveOptimizer:
    """Automatically analyzes code on modifications and suggests improvements."""

    def __init__(self):
        """Initialize the proactive optimizer."""
        self.supported_languages = {".py", ".js", ".ts", ".jsx", ".tsx"}
        self.analysis_severity_priority = ["critical", "error", "warning", "info"]

    def should_analyze_file(self, file_path: str, session_state: dict) -> bool:
        """
        Determine if a file should be analyzed for optimization suggestions.

        Args:
            file_path: Path to the modified file
            session_state: Current session state

        Returns:
            True if file should be analyzed, False otherwise
        """
        try:
            # Check if file extension is supported
            if not self._is_supported_file(file_path):
                return False

            # Check if analysis is enabled (default: True)
            if not session_state.get("proactive_optimization_enabled", True):
                return False

            # Check cooldown to prevent too frequent analysis
            if self._is_in_cooldown(file_path, session_state):
                return False

            # Check if file exists and is readable
            if not Path(file_path).exists():
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking if file should be analyzed: {e}")
            return False

    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file type is supported for analysis."""
        return Path(file_path).suffix.lower() in self.supported_languages

    def _is_in_cooldown(self, file_path: str, session_state: dict) -> bool:
        """Check if file analysis is in cooldown period."""
        try:
            analysis_history = session_state.get("file_analysis_history", {})
            last_analysis = analysis_history.get(file_path)

            if not last_analysis:
                return False

            last_time = datetime.fromisoformat(last_analysis)
            # Read cooldown from session state, fallback to default
            cooldown_minutes = session_state.get(
                "optimization_cooldown_minutes", ANALYSIS_COOLDOWN_MINUTES
            )
            cooldown_threshold = datetime.now() - timedelta(minutes=cooldown_minutes)

            # Fixed: Return True if last analysis was AFTER the threshold (within cooldown)
            return last_time > cooldown_threshold

        except (ValueError, KeyError) as e:
            logger.debug(f"Error checking analysis cooldown: {e}")
            return False

    def analyze_and_suggest(
        self, file_path: str, tool_context: ToolContext
    ) -> Optional[dict[str, Any]]:
        """
        Analyze a file and generate optimization suggestions.

        Args:
            file_path: Path to the file to analyze
            tool_context: ADK tool context

        Returns:
            Dict with analysis results and suggestions, or None if no suggestions
        """
        try:
            # Import the existing analysis functions
            from ..tools.code_analysis import _analyze_code

            # Run code analysis
            analysis_result = _analyze_code(file_path, tool_context)

            if analysis_result.get("status") == "Failed":
                logger.debug(f"Analysis failed for {file_path}: {analysis_result.get('error')}")
                return None

            # Update analysis history
            self._update_analysis_history(file_path, tool_context.state)

            # Get prioritized issues
            suggestions = self._generate_prioritized_suggestions(tool_context)

            if not suggestions:
                return None

            return {
                "file_path": file_path,
                "suggestions": suggestions,
                "analysis_timestamp": datetime.now().isoformat(),
                "language": analysis_result.get("language", "unknown"),
                "total_issues": len(tool_context.state.get("analysis_issues", [])),
            }

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None

    def _update_analysis_history(self, file_path: str, session_state: dict) -> None:
        """Update the analysis history for the file."""
        try:
            if "file_analysis_history" not in session_state:
                session_state["file_analysis_history"] = {}

            session_state["file_analysis_history"][file_path] = datetime.now().isoformat()

            # Limit history size
            history = session_state["file_analysis_history"]
            if len(history) > MAX_ANALYSIS_HISTORY_SIZE:  # Keep only last N analyzed files
                # Remove oldest entries
                sorted_items = sorted(history.items(), key=lambda x: x[1])
                for old_file, _ in sorted_items[:-MAX_ANALYSIS_HISTORY_SIZE]:
                    del history[old_file]

        except Exception as e:
            logger.error(f"Error updating analysis history: {e}")

    def _generate_prioritized_suggestions(self, tool_context: ToolContext) -> list[dict[str, Any]]:
        """
        Generate prioritized optimization suggestions from analysis results.

        Args:
            tool_context: ADK tool context with analysis results

        Returns:
            List of prioritized suggestions
        """
        try:
            from ..tools.code_analysis import get_issues_by_severity, suggest_fixes

            prioritized_suggestions = []

            # Get all fix suggestions once to avoid repeated calls in the loop.
            fixes_result = suggest_fixes(tool_context)
            suggested_fixes = fixes_result.get("suggested_fixes", [])

            # Process issues by severity priority
            for severity in self.analysis_severity_priority:
                severity_result = get_issues_by_severity(tool_context, severity)
                issues = severity_result.get("issues", [])

                if not issues:
                    continue

                # Match issues with their fixes
                for issue in issues[:MAX_SUGGESTIONS_TO_DISPLAY]:  # Limit per severity
                    suggestion_entry = {
                        "issue": issue,
                        "severity": severity,
                        "line": issue.get("line"),
                        "message": issue.get("message", ""),
                        "source": issue.get("source", "analyzer"),
                    }

                    # Find corresponding fix suggestion
                    fix_suggestion = self._find_fix_for_issue(issue, suggested_fixes)
                    if fix_suggestion:
                        suggestion_entry["suggested_fix"] = fix_suggestion["suggestion"]
                    else:
                        suggestion_entry["suggested_fix"] = self._generate_generic_fix_suggestion(
                            issue
                        )

                    prioritized_suggestions.append(suggestion_entry)

                    # Stop if we have enough suggestions
                    if len(prioritized_suggestions) >= MAX_SUGGESTIONS_TO_DISPLAY:
                        break

                if len(prioritized_suggestions) >= MAX_SUGGESTIONS_TO_DISPLAY:
                    break

            return prioritized_suggestions

        except Exception as e:
            logger.error(f"Error generating prioritized suggestions: {e}")
            return []

    def _find_fix_for_issue(
        self, issue: dict[str, Any], suggested_fixes: list[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Find a fix suggestion that matches the given issue."""
        try:
            issue_line = issue.get("line")
            issue_code = issue.get("code", "")

            for fix in suggested_fixes:
                fix_issue = fix.get("issue", {})
                if fix_issue.get("line") == issue_line and fix_issue.get("code") == issue_code:
                    return fix

        except Exception as e:
            logger.debug(f"Error finding fix for issue: {e}")

        return None

    def _generate_generic_fix_suggestion(self, issue: dict[str, Any]) -> str:
        """Generate a generic fix suggestion for an issue without a specific fix."""
        severity = issue.get("severity", "").lower()
        message = issue.get("message", "")
        line = issue.get("line", "")
        code = issue.get("code", "")

        # Enhanced specific suggestions for common patterns
        message_lower = message.lower()

        # Unused import patterns - provide exact removal suggestion
        if "unused import" in message_lower:
            # Try to extract the import name from the message
            import_match = re.search(r"unused import ['\"]([^'\"]+)['\"]", message, re.IGNORECASE)
            if import_match:
                import_name = import_match.group(1)
                return f"Remove the unused import '{import_name}' on line {line}"
            return f"Remove the unused import statement on line {line}"

        # Unused variable patterns - provide exact removal suggestion
        if "unused variable" in message_lower:
            var_match = re.search(r"unused variable ['\"]([^'\"]+)['\"]", message, re.IGNORECASE)
            if var_match:
                var_name = var_match.group(1)
                return (
                    f"Remove the unused variable '{var_name}' on line {line} or use it in your code"
                )
            return f"Remove the unused variable on line {line} or use it in your code"

        # Undefined variable patterns - provide specific guidance
        if "undefined variable" in message_lower or "undefined name" in message_lower:
            var_match = re.search(
                r"undefined (?:variable|name) ['\"]([^'\"]+)['\"]", message, re.IGNORECASE
            )
            if var_match:
                var_name = var_match.group(1)
                return (
                    f"Define variable '{var_name}' before line {line} "
                    f"or check for typos in the name"
                )
            return f"Define the variable before use on line {line} or check for typos"

        # Line too long - provide specific guidance
        if "line too long" in message_lower or code == "E501":
            length_match = re.search(r"line too long \((\d+)/(\d+)\)", message, re.IGNORECASE)
            if length_match:
                current_len, max_len = length_match.groups()
                chars_over = int(current_len) - int(max_len)
                return (
                    f"Shorten line {line} by {chars_over} characters "
                    f"(currently {current_len}, max {max_len}). "
                    f"Consider breaking it into multiple lines or variables."
                )
            return f"Break the long line at line {line} into multiple shorter lines"

        # Import errors - provide specific guidance
        if (
            "import" in message_lower
            and ("cannot import" in message_lower or "no module" in message_lower)
        ) or ("no module named" in message_lower):
            module_match = re.search(r"no module named ['\"]([^'\"]+)['\"]", message, re.IGNORECASE)
            if module_match:
                module_name = module_match.group(1)
                return (
                    f"Install the missing module '{module_name}' using pip or check the import path"
                )
            return (
                f"Check the import statement on line {line} - the module may not be "
                f"installed or the path may be incorrect"
            )

        # Indentation errors - provide specific guidance
        if "indentation" in message_lower:
            return (
                f"Fix the indentation on line {line} to match the expected Python indentation level"
            )

        # Syntax errors - provide specific guidance
        if "syntax error" in message_lower or "invalid syntax" in message_lower:
            return (
                f"Fix the syntax error on line {line} - check for missing colons, "
                f"parentheses, or quotes"
            )

        # Complexity suggestions - enhanced guidance
        if "complexity" in message_lower:
            return (
                f"Refactor the complex function at line {line} into smaller, more focused "
                f"functions. Consider extracting logic into helper methods."
            )

        # Style issues - enhanced guidance
        if "style" in message_lower or "format" in message_lower:
            if "whitespace" in message_lower:
                return f"Remove trailing whitespace on line {line}"
            if "blank line" in message_lower:
                return f"Adjust blank line spacing around line {line} according to PEP 8 guidelines"
            return f"Fix the code style issue on line {line} to follow PEP 8 conventions"

        # Security issues - enhanced guidance
        if severity in ["critical", "error"] and any(
            word in message_lower for word in ["security", "vulnerable", "unsafe"]
        ):
            return (
                f"Address the security issue on line {line}: "
                f"{message[:100]}{'...' if len(message) > 100 else ''}"
            )

        # Generic fallbacks based on severity
        if severity == "critical":
            return (
                f"Critical issue on line {line}: "
                f"{message[:60]}{'...' if len(message) > 60 else ''} "
                f"- immediate attention required"
            )
        if severity == "error":
            return (
                f"Fix the error on line {line}: {message[:60]}{'...' if len(message) > 60 else ''}"
            )
        if severity == "warning":
            return (
                f"Address the warning on line {line}: "
                f"{message[:60]}{'...' if len(message) > 60 else ''}"
            )
        return (
            f"Consider addressing the issue on line {line}: "
            f"{message[:60]}{'...' if len(message) > 60 else ''}"
        )

    def format_optimization_suggestions(self, analysis_result: dict[str, Any]) -> str:
        """
        Format optimization suggestions for display to user.

        Args:
            analysis_result: Analysis results with suggestions

        Returns:
            Formatted string with suggestions
        """
        if not analysis_result or not analysis_result.get("suggestions"):
            return ""

        suggestions = analysis_result["suggestions"]
        file_path = analysis_result["file_path"]
        total_issues = analysis_result.get("total_issues", 0)

        output = ["🔧 **Proactive Code Optimization:**"]
        output.append(f"I analyzed `{file_path}` and found {total_issues} potential improvements:")
        output.append("")

        for i, suggestion in enumerate(suggestions, 1):
            severity = suggestion["severity"].upper()
            line = suggestion.get("line", "?")
            message = suggestion.get("message", "").strip()
            fix = suggestion.get("suggested_fix", "")

            # Format severity with emoji
            severity_icon = {"CRITICAL": "🚨", "ERROR": "❌", "WARNING": "⚠️", "INFO": "💡"}.get(
                severity, "•"
            )

            output.append(f"**{i}. {severity_icon} {severity}** (Line {line})")
            output.append(f"   **Issue:** {message[:80]}{'...' if len(message) > 80 else ''}")
            output.append(f"   **Suggestion:** {fix}")
            output.append("")

        output.append("💡 Would you like me to help you fix any of these issues?")
        output.append(
            "You can also disable these suggestions by saying 'disable optimization suggestions'."
        )

        return "\n".join(output)

    def configure_optimization_settings(
        self,
        session_state: dict,
        enabled: Optional[bool] = None,
        cooldown_minutes: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Configure proactive optimization settings.

        Args:
            session_state: Current session state
            enabled: Whether to enable/disable proactive optimization
            cooldown_minutes: Analysis cooldown period in minutes

        Returns:
            Dict with configuration status
        """
        try:
            changes = []

            if enabled is not None:
                session_state["proactive_optimization_enabled"] = enabled
                status = "enabled" if enabled else "disabled"
                changes.append(f"Proactive optimization {status}")

            if cooldown_minutes is not None:
                session_state["optimization_cooldown_minutes"] = cooldown_minutes
                changes.append(f"Analysis cooldown set to {cooldown_minutes} minutes")

            return {
                "status": "success",
                "changes": changes,
                "current_settings": {
                    "enabled": session_state.get("proactive_optimization_enabled", True),
                    "cooldown_minutes": session_state.get(
                        "optimization_cooldown_minutes", ANALYSIS_COOLDOWN_MINUTES
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error configuring optimization settings: {e}")
            return {"status": "error", "message": str(e)}


# Global instance for use in callbacks
_optimizer = ProactiveOptimizer()


def detect_and_suggest_optimizations(file_path: str, tool_context: ToolContext) -> Optional[str]:
    """
    Main function to detect code issues and generate optimization suggestions.

    Args:
        file_path: Path to the file that was modified
        tool_context: ADK tool context

    Returns:
        Formatted suggestion string or None
    """
    try:
        if not _optimizer.should_analyze_file(file_path, tool_context.state):
            return None

        analysis_result = _optimizer.analyze_and_suggest(file_path, tool_context)

        if analysis_result and analysis_result.get("suggestions"):
            return _optimizer.format_optimization_suggestions(analysis_result)

        return None

    except Exception as e:
        logger.error(f"Error in proactive optimization detection: {e}")
        return None


def configure_proactive_optimization(
    session_state: dict, enabled: Optional[bool] = None, cooldown_minutes: Optional[int] = None
) -> dict[str, Any]:
    """
    Configure proactive optimization settings.

    Args:
        session_state: Current session state
        enabled: Whether to enable/disable proactive optimization
        cooldown_minutes: Analysis cooldown period in minutes

    Returns:
        Dict with configuration status
    """
    return _optimizer.configure_optimization_settings(session_state, enabled, cooldown_minutes)


def get_optimization_statistics(session_state: dict) -> dict[str, Any]:
    """
    Get statistics about file analysis history.

    Args:
        session_state: Current session state

    Returns:
        Dictionary with optimization statistics
    """
    try:
        analysis_history = session_state.get("file_analysis_history", {})

        return {
            "total_files_analyzed": len(analysis_history),
            "optimization_enabled": session_state.get("proactive_optimization_enabled", True),
            "cooldown_minutes": session_state.get(
                "optimization_cooldown_minutes", ANALYSIS_COOLDOWN_MINUTES
            ),
            "recently_analyzed_files": list(analysis_history.keys())[-10:],  # Last 10 files
        }

    except Exception as e:
        logger.error(f"Error getting optimization statistics: {e}")
        return {
            "total_files_analyzed": 0,
            "optimization_enabled": True,
            "cooldown_minutes": ANALYSIS_COOLDOWN_MINUTES,
            "recently_analyzed_files": [],
        }
