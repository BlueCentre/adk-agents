"""Simple shell command execution tool for the Software Engineer Agent."""

import logging
import subprocess
from typing import Optional

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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


def execute_shell_command(args: dict, tool_context: ToolContext) -> ExecuteShellCommandOutput:  # noqa: ARG001
    """
    Execute a shell command and return the result.

    Args:
        args: Dictionary containing command and working_directory
        tool_context: The ADK tool context

    Returns:
        ExecuteShellCommandOutput containing command results
    """
    command = args.get("command")
    working_directory = args.get("working_directory")

    if not command:
        return ExecuteShellCommandOutput(
            command="",
            exit_code=-1,
            stdout="",
            stderr="Error: No command provided",
            success=False,
            working_directory=working_directory,
        )

    try:
        logger.info(f"Executing command: {command}")
        if working_directory:
            logger.info(f"Working directory: {working_directory}")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=60,  # 60 second timeout
        )

        return ExecuteShellCommandOutput(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            success=result.returncode == 0,
            working_directory=working_directory,
        )

    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after 60 seconds: {command}"
        logger.error(error_msg)
        return ExecuteShellCommandOutput(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=error_msg,
            success=False,
            working_directory=working_directory,
        )

    except Exception as e:
        error_msg = f"Error executing command '{command}': {e!s}"
        logger.error(error_msg)
        return ExecuteShellCommandOutput(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=error_msg,
            success=False,
            working_directory=working_directory,
        )


# Create the tool using FunctionTool wrapper
execute_shell_command_tool = FunctionTool(execute_shell_command)
