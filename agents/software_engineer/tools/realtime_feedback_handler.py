"""Real-time Feedback Handler Tool.

This tool provides interface for handling critical issues responses from the
real-time feedback system (Milestone 4.1).
"""

import logging
from typing import Any

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeedbackHandlerRequest(BaseModel):
    """Request model for handling feedback responses."""

    critical_issues_response: dict[str, Any] = Field(
        description="The critical issues response from edit_file_content"
    )
    user_choice: str = Field(
        description="User's choice for handling issues: 'auto_fix', 'manual', 'ignore', or 'retry'"
    )


def handle_critical_issues(
    critical_issues_response: dict[str, Any],
    user_choice: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Handle critical syntax issues found during real-time validation.

    This tool processes critical issues responses from edit_file_content and provides
    options for automatic fixing, manual correction, or other resolution strategies.

    Args:
        critical_issues_response: The response from edit_file_content with status 'critical_issues'
        user_choice: How to handle the issues ('auto_fix', 'manual', 'ignore', 'retry')
        tool_context: Tool context for state management

    Returns:
        Dict with resolution status and next steps
    """
    try:
        from ..shared_libraries.realtime_feedback import handle_critical_issues_feedback

        result = handle_critical_issues_feedback(
            critical_issues_response, tool_context, user_choice
        )

        # Handle new action-based returns that require follow-up file operations
        if result.get("status") == "auto_fix_ready":
            # Apply the automatic fix by calling edit_file_content
            filepath = result.get("filepath")
            fixed_content = result.get("fixed_content")

            if filepath and fixed_content:
                # Set skip validation flag to avoid circular validation
                tool_context.state["skip_realtime_validation"] = True
                try:
                    from ..tools.filesystem import edit_file_content

                    edit_result = edit_file_content(filepath, fixed_content, tool_context)

                    if edit_result.get("status") == "success":
                        return {
                            "status": "auto_fixed_and_applied",
                            "message": (
                                f"✅ Automatically fixed issues and applied changes to '{filepath}'"
                            ),
                            "applied_fixes": result.get("applied_fixes", ""),
                            "final_content": fixed_content,
                        }
                    return {
                        "status": "auto_fix_failed",
                        "message": (
                            f"❌ Auto-fix succeeded but file write failed: "
                            f"{edit_result.get('message', 'Unknown error')}"
                        ),
                        "original_issue": critical_issues_response.get("feedback", ""),
                        "write_error": edit_result,
                    }
                finally:
                    # Re-enable validation for future operations
                    tool_context.state.pop("skip_realtime_validation", None)

        elif result.get("status") == "ignore_issues_ready":
            # Force the edit despite critical issues
            filepath = result.get("filepath")
            content = result.get("content")

            if filepath and content:
                # Set skip validation flag to avoid validation during forced edit
                tool_context.state["skip_realtime_validation"] = True
                try:
                    from ..tools.filesystem import edit_file_content

                    edit_result = edit_file_content(filepath, content, tool_context)
                    return {
                        "status": "critical_issues_ignored",
                        "message": (
                            f"⚠️ File written despite critical issues: "
                            f"{edit_result.get('message', '')}"
                        ),
                        "warning": result.get("warning", ""),
                        "ignored_feedback": result.get("ignored_feedback", ""),
                    }
                finally:
                    tool_context.state.pop("skip_realtime_validation", None)

        logger.info(
            f"Handled critical issues with choice '{user_choice}': "
            f"{result.get('status', 'unknown')}"
        )
        return result

    except Exception as e:
        logger.error(f"Error in handle_critical_issues tool: {e}")
        return {
            "status": "tool_error",
            "message": f"Error handling critical issues: {e}",
            "error_type": "ToolExecutionError",
        }


def get_feedback_options(
    critical_issues_response: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Get available options for handling critical syntax issues.

    Args:
        critical_issues_response: The response from edit_file_content with status 'critical_issues'
        tool_context: Tool context for state management

    Returns:
        Dict with available options and preview information
    """
    try:
        from ..shared_libraries.realtime_feedback import handle_critical_issues_feedback

        # Call with no user_choice to get options
        result = handle_critical_issues_feedback(
            critical_issues_response, tool_context, user_choice=None
        )

        logger.info("Retrieved feedback options for critical issues")
        return result

    except Exception as e:
        logger.error(f"Error in get_feedback_options tool: {e}")
        return {
            "status": "tool_error",
            "message": f"Error getting feedback options: {e}",
            "error_type": "ToolExecutionError",
        }


def configure_realtime_feedback(
    enabled: bool,
    allow_ignore_critical: bool = False,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """
    Configure real-time feedback settings.

    Args:
        enabled: Whether to enable real-time feedback validation
        allow_ignore_critical: Whether to allow ignoring critical issues
        tool_context: Tool context for state management

    Returns:
        Dict with configuration status
    """
    try:
        if tool_context is None:
            return {
                "status": "error",
                "message": "Tool context is required",
                "error_type": "MissingParameter",
            }

        tool_context.state["realtime_feedback_enabled"] = enabled
        tool_context.state["allow_ignore_critical_issues"] = allow_ignore_critical

        logger.info(
            f"Configured real-time feedback: enabled={enabled}, "
            f"allow_ignore={allow_ignore_critical}"
        )

        return {
            "status": "configured",
            "message": f"Real-time feedback {'enabled' if enabled else 'disabled'}",
            "settings": {
                "realtime_feedback_enabled": enabled,
                "allow_ignore_critical_issues": allow_ignore_critical,
            },
        }

    except Exception as e:
        logger.error(f"Error configuring real-time feedback: {e}")
        return {
            "status": "error",
            "message": f"Configuration error: {e}",
            "error_type": "ConfigurationError",
        }


# Define the tools using FunctionTool
handle_critical_issues_tool = FunctionTool(func=handle_critical_issues)
get_feedback_options_tool = FunctionTool(func=get_feedback_options)
configure_realtime_feedback_tool = FunctionTool(func=configure_realtime_feedback)
