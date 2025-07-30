# code_agent/agent/software_engineer/software_engineer/tools/filesystem_tools.py
import logging
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from agents.software_engineer.shared_libraries.workflow_guidance import ActionType

logger = logging.getLogger(__name__)

# Consider adding a WORKSPACE_ROOT validation here for security
# WORKSPACE_ROOT = os.path.abspath(".") # Example: Use current working directory


def read_file_content(filepath: str) -> dict[str, Any]:
    """
    Reads the content of a file from the local filesystem.

    Args:
        filepath: The relative or absolute path to the file.
                  Relative paths are resolved from the agent's current working directory.
                  (Security Note: Path validation should be implemented to restrict access).

    Returns:
        A dictionary with:
        - {'status': 'success', 'content': 'file_content_string'} on success.
        - {'status': 'error', 'error_type': str, 'message': str} on failure.
          Possible error_types: 'FileNotFound', 'PermissionDenied', 'IOError', 'SecurityViolation'
            (if implemented).
    """
    logger.info(f"Attempting to read file: {filepath}")
    # Add path validation/sandboxing here before opening
    # Example:
    # abs_path = os.path.abspath(filepath)
    # if not abs_path.startswith(WORKSPACE_ROOT):
    #     message = f"Access denied: Path '{filepath}' is outside the allowed workspace."
    #     logger.error(message)
    #     return {"status": "error", "error_type": "SecurityViolation", "message": message}
    try:
        with Path(filepath).open(encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Successfully read file: {filepath}")
        return {"status": "success", "content": content}
    except FileNotFoundError:
        message = f"File not found at path '{filepath}'."
        logger.error(message)
        return {"status": "error", "error_type": "FileNotFound", "message": message}
    except PermissionError:
        message = f"Permission denied when trying to read file '{filepath}'."
        logger.error(message)
        return {"status": "error", "error_type": "PermissionDenied", "message": message}
    except Exception as e:
        message = f"An unexpected error occurred while reading file '{filepath}': {e}"
        logger.error(message, exc_info=True)
        return {"status": "error", "error_type": "IOError", "message": message}


def list_directory_contents(directory_path: str) -> dict[str, Any]:
    """
    Lists the contents (files and directories) of a directory on the local filesystem.

    Args:
        directory_path: The relative or absolute path to the directory.
                        Relative paths are resolved from the agent's current working directory.
                        (Security Note: Path validation should be implemented to restrict access).

    Returns:
        A dictionary with:
        - {'status': 'success', 'contents': ['item1', 'item2', ...]} on success.
        - {'status': 'error', 'error_type': str, 'message': str} on failure.
          Possible error_types: 'NotADirectory', 'FileNotFound', 'PermissionDenied', 'IOError',
            'SecurityViolation' (if implemented).
    """
    logger.info(f"Attempting to list directory: {directory_path}")
    # Add path validation/sandboxing here before listing
    # Example:
    # abs_path = os.path.abspath(directory_path)
    # if not abs_path.startswith(WORKSPACE_ROOT):
    #     message = f"Access denied: Path '{directory_path}' is outside the allowed workspace."
    #     logger.error(message)
    #     return {"status": "error", "error_type": "SecurityViolation", "message": message}
    try:
        dir_path = Path(directory_path)
        if not dir_path.exists():
            message = f"Directory not found at path '{directory_path}'."
            logger.error(message)
            return {"status": "error", "error_type": "FileNotFound", "message": message}
        if not dir_path.is_dir():
            message = f"Path '{directory_path}' exists but is not a directory."
            logger.error(message)
            return {"status": "error", "error_type": "NotADirectory", "message": message}

        contents = [item.name for item in dir_path.iterdir()]
        logger.info(f"Successfully listed directory: {directory_path}")
        return {"status": "success", "contents": contents}
    except PermissionError:
        message = f"Permission denied when trying to list directory '{directory_path}'."
        logger.error(message)
        return {"status": "error", "error_type": "PermissionDenied", "message": message}
    except Exception as e:
        message = f"An unexpected error occurred while listing directory '{directory_path}': {e}"
        logger.error(message, exc_info=True)
        return {"status": "error", "error_type": "IOError", "message": message}


def edit_file_content(
    filepath: str,
    content: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Writes content to a file or proposes the write, requiring user approval based on session state.
    Creates the file if it does not exist (including parent directories).
    Overwrites the file if it already exists (only if approval is not required or already granted).

    Implements Milestone 4.1: Real-time Syntax and Basic Style Feedback by validating code
    before approval and providing immediate feedback on issues.

    Checks the 'require_edit_approval' flag in session state (defaults to True).
    If True, returns a 'pending_approval' status without writing.
    If False, writes the file and returns 'success' or 'error'.

    Args:
        filepath: The relative or absolute path to the file.
                  Relative paths are resolved from the agent's current working directory.
                  (Security Note: Path validation should be implemented to restrict access).
        content: The new content to write to the file.

    Returns:
        A dictionary with:
        - {'status': 'pending_approval', 'proposed_filepath': str, 'proposed_content': str,
          'message': str, 'realtime_feedback': str} if approval is required.
        - {'status': 'critical_issues', 'feedback': str, 'can_auto_fix': bool,
          'auto_fixed_code': str} if critical syntax errors are found.
        - {'status': 'success', 'message': 'Success message'} on successful write
          (when approval not required).
        - {'status': 'error', 'error_type': str, 'message': str} on failure during write
          or validation.
          Possible error_types: 'PermissionDenied', 'IOError', 'SecurityViolation' (if implemented).
    """
    logger.info(f"Checking approval requirement for writing to file: {filepath}")

    # Add path validation/sandboxing here FIRST
    # Example:
    # abs_path = os.path.abspath(filepath)
    # if not abs_path.startswith(WORKSPACE_ROOT):
    #     message = f"Access denied: Path '{filepath}' is outside the allowed workspace."
    #     logger.error(message)
    #     return {"status": "error", "error_type": "SecurityViolation", "message": message}

    # Milestone 4.1: Real-time Syntax and Style Feedback
    # Run real-time validation before approval (unless disabled or internal operations)
    realtime_feedback_enabled = tool_context.state.get("realtime_feedback_enabled", True)
    skip_validation = tool_context.state.get("skip_realtime_validation", False)

    if realtime_feedback_enabled and not skip_validation:
        logger.info(f"Running real-time validation for: {filepath}")
        try:
            from ..shared_libraries.realtime_feedback import validate_code_before_approval

            validation_result = validate_code_before_approval(content, filepath, tool_context)

            # If there are critical issues, return feedback immediately
            if validation_result.get("has_critical_issues", False):
                logger.info(f"Critical syntax issues found in {filepath}, blocking edit")
                return {
                    "status": "critical_issues",
                    "feedback": validation_result.get(
                        "formatted_feedback", "Critical issues found"
                    ),
                    "can_auto_fix": validation_result.get("can_auto_fix", False),
                    "auto_fixed_code": validation_result.get("auto_fixed_code"),
                    "proposed_filepath": filepath,
                    "proposed_content": content,
                    "message": "Critical syntax issues must be resolved before proceeding",
                }

        except Exception as e:
            logger.warning(f"Real-time validation failed for {filepath}: {e}")
            # Continue with normal flow if validation fails

    # Default to requiring approval unless explicitly told otherwise.
    # The 'force_edit' flag can be used for internal, non-user-facing automation
    # where pre-approval is implicitly granted.
    require_approval = tool_context.state.get("require_edit_approval", True)
    force_edit = tool_context.state.get("force_edit", False)

    if require_approval and not force_edit:
        logger.info(f"Approval required for file edit: {filepath}. Returning pending status.")

        # Include real-time feedback in approval request if available
        realtime_feedback = ""
        if realtime_feedback_enabled and not skip_validation:
            try:
                from ..shared_libraries.realtime_feedback import validate_code_before_approval

                validation_result = validate_code_before_approval(content, filepath, tool_context)
                realtime_feedback = validation_result.get("formatted_feedback", "")
            except Exception as e:
                logger.debug(f"Failed to get real-time feedback for approval: {e}")

        approval_response = {
            "status": "pending_approval",
            "proposed_filepath": filepath,
            "proposed_content": content,
            "message": f"Approval required to write to '{filepath}'. User confirmation needed.",
        }

        # Add real-time feedback if available
        if realtime_feedback:
            approval_response["realtime_feedback"] = realtime_feedback
            approval_response["message"] += f"\n\n{realtime_feedback}"

        return approval_response

    # Proceed with write if approval is not required or has been forced
    if force_edit:
        logger.info(
            f"Approval bypassed due to 'force_edit' flag. Proceeding with write to file: {filepath}"
        )
    else:
        logger.info(f"Approval not required. Proceeding with write to file: {filepath}")
    try:
        # Ensure the directory exists
        dir_path = Path(filepath).parent
        if dir_path:  # Ensure dir_path is not empty (happens for root-level files)
            dir_path.mkdir(parents=True, exist_ok=True)  # Creates parent dirs if needed

        # Consider atomic write here: write to temp file, then os.replace()
        with Path(filepath).open("w", encoding="utf-8") as f:
            f.write(content)
        message = f"Successfully wrote content to '{filepath}'."
        logger.info(message)

        # Set last_action for workflow guidance (Milestone 2.3)
        tool_context.state["last_action"] = ActionType.EDIT_FILE.value
        logger.debug(f"Set last_action={ActionType.EDIT_FILE.value} for workflow guidance")

        # Return simple success result - optimization analysis will be handled by callback system
        return {"status": "success", "message": message}
    except PermissionError:
        message = f"Permission denied when trying to write to file '{filepath}'."
        logger.error(message)
        return {"status": "error", "error_type": "PermissionDenied", "message": message}
    except Exception as e:
        message = f"An unexpected error occurred while writing to file '{filepath}': {e}"
        logger.error(message, exc_info=True)
        return {"status": "error", "error_type": "IOError", "message": message}


def configure_edit_approval(require_approval: bool, tool_context: ToolContext) -> dict[str, Any]:
    """
    Configures whether file edits require user approval for the current session.
    Sets the 'require_edit_approval' flag in the session state.

    Args:
        require_approval: Set to True to require approval (default), False to allow direct edits.

    Returns:
        dict: Configuration status and current setting.
    """
    try:
        tool_context.state["require_edit_approval"] = require_approval
        status = "enabled" if require_approval else "disabled"
        message = f"File edit approval has been {status} for this session."

        logger.info(f"Edit approval setting changed: require_approval={require_approval}")

        return {
            "status": "success",
            "message": message,
            "require_approval": require_approval,
            "session_setting": tool_context.state.get("require_edit_approval", True),
        }
    except Exception as e:
        error_message = f"Failed to configure edit approval: {e}"
        logger.error(error_message)
        return {
            "status": "error",
            "message": error_message,
            "require_approval": tool_context.state.get("require_edit_approval", True),
        }


def enable_smooth_testing_mode(tool_context: ToolContext) -> dict[str, Any]:
    """
    Enable smooth testing mode by disabling approval requirements and optimizing settings.
    This makes the agent more proactive and reduces friction for testing scenarios.

    Args:
        tool_context: ADK tool context

    Returns:
        dict: Configuration status
    """
    try:
        # Disable approval requirements for smoother testing
        tool_context.state["require_edit_approval"] = False

        # Enable smooth testing mode flag
        tool_context.state["smooth_testing_enabled"] = True

        # Ensure proactive optimization is enabled
        tool_context.state["proactive_optimization_enabled"] = True
        tool_context.state["proactive_suggestions_enabled"] = True

        # Reduce cooldown for more responsive suggestions
        tool_context.state["optimization_cooldown_minutes"] = 0

        logger.info("Enabled smooth testing mode - approvals disabled, proactive analysis enabled")

        return {
            "status": "success",
            "message": (
                "Smooth testing mode enabled. I'll be more proactive and "
                "won't require approvals for file operations."
            ),
            "settings": {
                "require_edit_approval": False,
                "smooth_testing_enabled": True,
                "proactive_optimization_enabled": True,
                "optimization_cooldown_minutes": 0,
            },
        }
    except Exception as e:
        error_message = f"Failed to enable smooth testing mode: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}


# FunctionTool definitions
read_file_content_tool = FunctionTool(read_file_content)
list_directory_contents_tool = FunctionTool(list_directory_contents)
edit_file_content_tool = FunctionTool(edit_file_content)
configure_edit_approval_tool = FunctionTool(configure_edit_approval)
enable_smooth_testing_mode_tool = FunctionTool(enable_smooth_testing_mode)

# Export the tools
__all__ = [
    "configure_edit_approval_tool",
    "edit_file_content_tool",
    "enable_smooth_testing_mode_tool",
    "list_directory_contents_tool",
    "read_file_content_tool",
]
