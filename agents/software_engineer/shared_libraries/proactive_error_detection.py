"""Proactive Error Detection and Fix Suggestion System.

This module implements Milestone 2.1: Basic Proactive Error Detection
by automatically detecting common errors and suggesting initial debugging steps.
"""

from datetime import datetime, timedelta
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ProactiveErrorDetector:
    """Detects common errors and suggests initial debugging steps."""

    def __init__(self):
        """Initialize the error detector with predefined fix suggestions."""
        self.error_fix_mappings = {
            "file_not_found": {
                "patterns": ["No such file or directory", "ENOENT"],
                "suggestions": [
                    "Check if the file exists using `ls -la <filename>`",
                    "Verify the file path is correct - use `pwd` to check current directory",
                    "If creating a new file, ensure the parent directory exists",
                    "Check file permissions with `ls -la` in the containing directory",
                ],
                "priority": "high",
            },
            "permission_denied": {
                "patterns": ["Permission denied", "EACCES"],
                "suggestions": [
                    "Check file permissions with `ls -la <filename>`",
                    "Use `chmod` to modify permissions if needed (e.g., `chmod 755 <filename>`)",
                    "Verify you have write permissions to the directory",
                    "Try running with `sudo` if appropriate (use cautiously)",
                ],
                "priority": "high",
            },
            "command_not_found": {
                "patterns": [
                    "command not found",
                    "not recognized as an internal or external command",
                ],
                "suggestions": [
                    "Check if the command is installed using `which <command>` or `type <command>`",
                    "Install the package (e.g., `apt install <pkg>` or `brew install <pkg>`)",
                    "Check if the command is in your PATH: `echo $PATH`",
                    "Verify the command spelling and syntax",
                ],
                "priority": "medium",
            },
            "connection_refused": {
                "patterns": ["Connection refused", "connection refused"],
                "suggestions": [
                    "Check if the target service is running",
                    "Verify the correct host and port are being used",
                    "Check firewall settings that might be blocking the connection",
                    "Test connectivity with `ping` or `telnet` to the target host",
                ],
                "priority": "medium",
            },
            "syntax_error": {
                "patterns": ["Syntax error", "SyntaxError", "syntax error"],
                "suggestions": [
                    "Check for missing brackets, parentheses, or quotes",
                    "Verify proper indentation (especially in Python)",
                    "Look for missing semicolons or commas where required",
                    "Use a linter or IDE to identify syntax issues",
                ],
                "priority": "high",
            },
            "python_import_error": {
                "patterns": ["ImportError", "ModuleNotFoundError"],
                "suggestions": [
                    "Install the missing module: `pip install <module_name>`",
                    "Check if you're in the correct virtual environment",
                    "Verify the module name spelling and case sensitivity",
                    "Check if the module is in your PYTHONPATH",
                ],
                "priority": "medium",
            },
            "timeout": {
                "patterns": ["timeout", "timed out", "TimeoutError"],
                "suggestions": [
                    "Check network connectivity if it's a network operation",
                    "Increase timeout value if appropriate",
                    "Verify the target service is responsive",
                    "Consider breaking down large operations into smaller chunks",
                ],
                "priority": "medium",
            },
            "process_killed": {
                "patterns": ["killed", "Killed", "SIGKILL"],
                "suggestions": [
                    "Check system memory usage: `free -h` or `top`",
                    "Look for out-of-memory issues in system logs: `dmesg | grep -i memory`",
                    "Consider reducing memory usage or adding more RAM",
                    "Check if the process was manually terminated",
                ],
                "priority": "high",
            },
            "generic_error": {
                "patterns": ["error", "Error", "failed", "Failed"],
                "suggestions": [
                    "Check the full error message for specific details",
                    "Look at system logs for more context: `journalctl -xe`",
                    "Try running the command with verbose output (-v or --verbose)",
                    "Search for the specific error message in documentation or online",
                ],
                "priority": "low",
            },
        }

    def analyze_recent_errors(self, session_state: dict) -> Optional[dict]:
        """
        Analyze recent errors and generate proactive suggestions.

        Args:
            session_state: Current session state containing recent_errors

        Returns:
            Dict with error analysis and suggestions, or None if no actionable errors
        """
        try:
            recent_errors = session_state.get("recent_errors", [])
            if not recent_errors:
                return None

            # Get the most recent error (within last 5 minutes for proactive detection)
            current_time = datetime.now()
            recent_threshold = current_time - timedelta(minutes=5)

            actionable_errors = []

            for error in reversed(recent_errors):  # Most recent first
                try:
                    error_time = datetime.fromisoformat(error.get("timestamp", ""))
                    if error_time < recent_threshold:
                        continue  # Skip older errors

                    suggestion = self._generate_error_suggestion(error)
                    if suggestion:
                        actionable_errors.append(
                            {
                                "error": error,
                                "suggestion": suggestion,
                                "timestamp": error.get("timestamp"),
                                "command": error.get("command", "unknown"),
                            }
                        )

                except (ValueError, KeyError) as e:
                    logger.debug(f"Error parsing timestamp for error entry: {e}")
                    continue

            if actionable_errors:
                return {
                    "has_proactive_suggestions": True,
                    "error_count": len(actionable_errors),
                    "suggestions": actionable_errors[:3],  # Limit to top 3 most recent
                    "generated_at": current_time.isoformat(),
                }

            return None

        except Exception as e:
            logger.error(f"Error analyzing recent errors for proactive suggestions: {e}")
            return None

    def _generate_error_suggestion(self, error: dict) -> Optional[dict]:
        """
        Generate a specific suggestion for an error.

        Args:
            error: Error information dictionary

        Returns:
            Dict with suggestion details or None
        """
        error_type = error.get("error_type", "unknown")
        error_details = error.get("details", "")
        stderr = error.get("stderr", "")

        suggestion_info = None
        matched_error_type = error_type

        # Always try pattern matching first for more accurate error classification
        # Try to match specific patterns first (excluding generic_error)
        for err_type, info in self.error_fix_mappings.items():
            if err_type == "generic_error":  # Skip generic patterns in first pass
                continue
            for pattern in info["patterns"]:
                if re.search(pattern, f"{error_details} {stderr}", re.IGNORECASE):
                    suggestion_info = info
                    matched_error_type = err_type
                    break
            if suggestion_info:
                break

        # If no specific pattern matched, try direct error type mapping (excluding generic)
        if not suggestion_info and error_type != "generic_error":
            suggestion_info = self.error_fix_mappings.get(error_type)
            if suggestion_info:
                matched_error_type = error_type

        # If still no match, try generic patterns as last resort
        # But only for actual error conditions
        if not suggestion_info:
            combined_text = f"{error_details} {stderr}".lower()
            # Only use generic error suggestions for actual error conditions
            if any(keyword in combined_text for keyword in ["error", "failed", "exception"]):
                generic_info = self.error_fix_mappings.get("generic_error")
                if generic_info:
                    suggestion_info = generic_info
                    matched_error_type = "generic_error"

        if not suggestion_info:
            return None

        return {
            "error_type": matched_error_type,
            "priority": suggestion_info["priority"],
            "suggestions": suggestion_info["suggestions"],
            "context": {
                "stderr": stderr[:200] if stderr else "",  # Truncate for readability
                "details": error_details[:200] if error_details else "",
            },
        }

    def format_proactive_suggestions(self, analysis: dict) -> str:
        """
        Format proactive suggestions for display to user.

        Args:
            analysis: Analysis results from analyze_recent_errors

        Returns:
            Formatted string with suggestions
        """
        if not analysis or not analysis.get("has_proactive_suggestions"):
            return ""

        suggestions = analysis.get("suggestions", [])
        if not suggestions:
            return ""

        output = ["🔍 **Proactive Error Detection:**"]
        output.append(f"I noticed {analysis['error_count']} recent error(s) that I can help with:")
        output.append("")

        for i, item in enumerate(suggestions, 1):
            suggestion = item["suggestion"]
            command = item["command"]

            output.append(f"**{i}. Error in command:** `{command}`")
            output.append(f"   **Type:** {suggestion['error_type'].replace('_', ' ').title()}")

            if suggestion.get("context", {}).get("stderr"):
                stderr_preview = suggestion["context"]["stderr"]
                output.append(f"   **Details:** {stderr_preview}...")

            output.append("   **Suggested fixes:**")
            for fix in suggestion["suggestions"][:3]:  # Limit to top 3 suggestions
                output.append(f"   • {fix}")
            output.append("")

        output.append("💡 Would you like me to help you investigate any of these issues?")

        return "\n".join(output)


# Global instance for use in callbacks
_error_detector = ProactiveErrorDetector()


def detect_and_suggest_error_fixes(session_state: dict) -> Optional[str]:
    """
    Main function to detect errors and generate suggestions.

    Args:
        session_state: Current session state

    Returns:
        Formatted suggestion string or None
    """
    try:
        analysis = _error_detector.analyze_recent_errors(session_state)
        if analysis:
            return _error_detector.format_proactive_suggestions(analysis)
        return None
    except Exception as e:
        logger.error(f"Error in proactive error detection: {e}")
        return None


def get_error_statistics(session_state: dict) -> dict:
    """
    Get statistics about recent errors for debugging/monitoring.

    Args:
        session_state: Current session state

    Returns:
        Dictionary with error statistics
    """
    try:
        recent_errors = session_state.get("recent_errors", [])

        error_types = {}
        total_errors = len(recent_errors)

        for error in recent_errors:
            error_type = error.get("error_type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": total_errors,
            "error_types": error_types,
            "has_recent_errors": total_errors > 0,
        }
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        return {"total_errors": 0, "error_types": {}, "has_recent_errors": False}
