"""Enhanced shell command execution tool with command history and error tracking."""

from datetime import datetime
import logging
import os
import re
import subprocess
from typing import Optional

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Maximum number of commands to keep in history
MAX_COMMAND_HISTORY = 50
MAX_ERROR_HISTORY = 20


class ExecuteShellCommandInput(BaseModel):
    """Input model for executing shell commands."""

    command: str = Field(..., description="The shell command to execute")
    working_directory: Optional[str] = Field(
        None, description="Optional working directory to run the command in"
    )


class ExecuteShellCommandOutput(BaseModel):
    """Output model for shell command execution."""

    command: str = Field(..., description="The command that was executed")
    exit_code: int = Field(..., description="The exit code of the command")
    stdout: str = Field(..., description="Standard output from the command")
    stderr: str = Field(..., description="Standard error from the command")
    success: bool = Field(..., description="Whether the command executed successfully")
    working_directory: Optional[str] = Field(None, description="The working directory used")


def _detect_error_patterns(stderr: str, stdout: str, exit_code: int) -> Optional[dict]:
    """
    Detect common error patterns in command output.

    Args:
        stderr: Standard error output
        stdout: Standard output
        exit_code: Command exit code

    Returns:
        Dict with error information if error detected, None otherwise
    """
    if exit_code == 0:
        return None

    # Common error patterns to detect
    error_patterns = [
        (r"No such file or directory", "file_not_found"),
        (r"Permission denied", "permission_denied"),
        (r"command not found", "command_not_found"),
        (r"Connection refused", "connection_refused"),
        (r"Syntax error", "syntax_error"),
        (r"ImportError|ModuleNotFoundError", "python_import_error"),
        (r"ENOENT", "file_not_found"),
        (r"EACCES", "permission_denied"),
        (r"timeout|timed out", "timeout"),
        (r"killed", "process_killed"),
    ]

    combined_output = f"{stderr}\n{stdout}".lower()

    for pattern, error_type in error_patterns:
        if re.search(pattern, combined_output, re.IGNORECASE):
            return {
                "error_type": error_type,
                "pattern_matched": pattern,
                "stderr": stderr,
                "stdout": stdout,
                "exit_code": exit_code,
            }

    # Generic error if no specific pattern matched
    return {
        "error_type": "generic_error",
        "pattern_matched": "non_zero_exit_code",
        "stderr": stderr,
        "stdout": stdout,
        "exit_code": exit_code,
    }


def _store_command_history(tool_context: ToolContext, command_info: dict):
    """
    Store command execution information in session state.

    Args:
        tool_context: ADK tool context
        command_info: Command execution details
    """
    if not tool_context or not tool_context.state:
        return

    try:
        # Get existing command history or initialize empty list
        command_history = tool_context.state.get("command_history", [])

        # Add current command with timestamp
        command_entry = {
            **command_info,
            "timestamp": datetime.now().isoformat(),
        }

        command_history.append(command_entry)

        # Limit history size to prevent memory bloat
        if len(command_history) > MAX_COMMAND_HISTORY:
            command_history = command_history[-MAX_COMMAND_HISTORY:]

        # Store back in session state
        tool_context.state["command_history"] = command_history

        logger.debug(f"Stored command in history: {command_info['command'][:50]}...")

    except Exception as e:
        logger.error(f"Failed to store command history: {e!s}")


def _store_error_context(tool_context: ToolContext, error_info: dict):
    """
    Store error information in session state for later analysis.

    Args:
        tool_context: ADK tool context
        error_info: Error details including type and context
    """
    if not tool_context or not tool_context.state:
        return

    try:
        # Get existing error history or initialize empty list
        recent_errors = tool_context.state.get("recent_errors", [])

        # Add current error with timestamp
        error_entry = {
            **error_info,
            "timestamp": datetime.now().isoformat(),
        }

        recent_errors.append(error_entry)

        # Limit error history size
        if len(recent_errors) > MAX_ERROR_HISTORY:
            recent_errors = recent_errors[-MAX_ERROR_HISTORY:]

        # Store back in session state
        tool_context.state["recent_errors"] = recent_errors

        logger.debug(f"Stored error in history: {error_info['error_type']}")

    except Exception as e:
        logger.error(f"Failed to store error context: {e!s}")


def execute_shell_command(args: dict, tool_context: ToolContext) -> ExecuteShellCommandOutput:
    """
    Execute a shell command and return the result with enhanced history tracking.

    Args:
        args: Dictionary containing command and working_directory
        tool_context: The ADK tool context (provides access to session state)

    Returns:
        ExecuteShellCommandOutput containing command results
    """
    command = args.get("command")
    working_directory = args.get("working_directory")

    if not command:
        output = ExecuteShellCommandOutput(
            command="",
            exit_code=-1,
            stdout="",
            stderr="Error: No command provided",
            success=False,
            working_directory=working_directory,
        )

        # Store command history even for invalid commands
        command_info = {
            "command": "",
            "working_directory": working_directory,
            "exit_code": -1,
            "success": False,
            "error_reason": "no_command_provided",
        }
        _store_command_history(tool_context, command_info)

        return output

    try:
        logger.info(f"Executing command: {command}")
        if working_directory:
            logger.info(f"Working directory: {working_directory}")

        # Sanitize Git-related env so commands (especially git) operate within the provided
        # working_directory rather than any inherited repository from the parent process
        # (e.g., pre-commit hooks setting GIT_* vars).
        env = os.environ.copy()
        for var in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        ):
            env.pop(var, None)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=60,  # 60 second timeout
            env=env,
        )

        output = ExecuteShellCommandOutput(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            success=result.returncode == 0,
            working_directory=working_directory,
        )

        # Store command execution in history
        command_info = {
            "command": command,
            "working_directory": working_directory,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "stdout_length": len(result.stdout),
            "stderr_length": len(result.stderr),
        }
        _store_command_history(tool_context, command_info)

        # Detect and store error information if command failed
        if result.returncode != 0:
            error_info = _detect_error_patterns(result.stderr, result.stdout, result.returncode)
            if error_info:
                error_info["command"] = command
                error_info["working_directory"] = working_directory
                _store_error_context(tool_context, error_info)

        return output

    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after 60 seconds: {command}"
        logger.error(error_msg)

        output = ExecuteShellCommandOutput(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=error_msg,
            success=False,
            working_directory=working_directory,
        )

        # Store timeout error in history and error context
        command_info = {
            "command": command,
            "working_directory": working_directory,
            "exit_code": -1,
            "success": False,
            "error_reason": "timeout",
        }
        _store_command_history(tool_context, command_info)

        error_info = {
            "error_type": "timeout",
            "pattern_matched": "subprocess_timeout",
            "command": command,
            "working_directory": working_directory,
            "stderr": error_msg,
            "stdout": "",
            "exit_code": -1,
        }
        _store_error_context(tool_context, error_info)

        return output

    except Exception as e:
        error_msg = f"Error executing command '{command}': {e!s}"
        logger.error(error_msg)

        output = ExecuteShellCommandOutput(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=error_msg,
            success=False,
            working_directory=working_directory,
        )

        # Store exception error in history and error context
        command_info = {
            "command": command,
            "working_directory": working_directory,
            "exit_code": -1,
            "success": False,
            "error_reason": "exception",
        }
        _store_command_history(tool_context, command_info)

        error_info = {
            "error_type": "exception",
            "pattern_matched": "python_exception",
            "command": command,
            "working_directory": working_directory,
            "stderr": error_msg,
            "stdout": "",
            "exit_code": -1,
        }
        _store_error_context(tool_context, error_info)

        return output


# Create the tool using FunctionTool wrapper
execute_shell_command_tool = FunctionTool(execute_shell_command)
