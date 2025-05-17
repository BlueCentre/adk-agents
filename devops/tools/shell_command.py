"""Tools for executing shell commands."""

import logging
import shlex
import shutil  # <-- Added import
import subprocess
from typing import Literal, Optional, Dict, Any

# Import ToolContext for state management
from google.adk.tools import (
    FunctionTool,  # Ensure FunctionTool is imported if not already
    ToolContext,
)
from pydantic import BaseModel, Field

from .. import config as agent_config

logger = logging.getLogger(__name__)

# --- Configuration Tool --- #


class ConfigureShellApprovalInput(BaseModel):
    """Input model for configuring shell command approval."""

    require_approval: bool = Field(..., description="Set to true to require approval, false to disable.")


class ConfigureShellApprovalOutput(BaseModel):
    """Output model for configuring shell command approval."""

    status: str


def configure_shell_approval(args: dict, tool_context: ToolContext) -> ConfigureShellApprovalOutput:
    """Configures whether running shell commands requires user approval for the current session.

    Args:
        args (dict): A dictionary containing:
            require_approval (bool): Set to true to require approval, false to disable.
        tool_context (ToolContext): The context for accessing session state.
    """
    require_approval = args.get("require_approval")

    # Add validation for the boolean argument
    if require_approval is None or not isinstance(require_approval, bool):
        message = "Error: 'require_approval' argument is missing or not a boolean (true/false)."
        logger.error(message)
        return ConfigureShellApprovalOutput(status=message)

    tool_context.state["require_shell_approval"] = require_approval
    status = "enabled" if require_approval else "disabled"
    logger.info(f"Shell command approval requirement set to: {status}")
    return ConfigureShellApprovalOutput(status=f"Shell command approval requirement is now {status}.")


# --- Whitelist Configuration Tool --- #


class ConfigureShellWhitelistInput(BaseModel):
    """Input model for configuring the shell command whitelist."""

    action: Literal["add", "remove", "list", "clear"] = Field(..., description="Action to perform: add, remove, list, or clear.")
    command: Optional[str] = Field(None, description="The command to add or remove (required for 'add' and 'remove' actions).")


class ConfigureShellWhitelistOutput(BaseModel):
    """Output model for configuring the shell command whitelist."""

    status: str
    whitelist: Optional[list[str]] = Field(None, description="The current whitelist (only for 'list' action).")


def configure_shell_whitelist(args: dict, tool_context: ToolContext) -> ConfigureShellWhitelistOutput:
    """Manages the whitelist of shell commands that bypass approval.

    Args:
        args (dict): A dictionary containing:
            action (Literal["add", "remove", "list", "clear"]): The action.
            command (Optional[str]): The command for add/remove.
        tool_context (ToolContext): The context for accessing session state.
    """
    action = args.get("action")
    command = args.get("command")

    # Default safe commands (adjust as needed)
    DEFAULT_SAFE_COMMANDS = [
        "ls",
        "grep",
        "find",
        "cat",
        "pwd",
        "echo",
        "git status",
        "head",
        "tail",
        "wc",
        "git diff",
        "git log",
        "which",
        "ping",
        "host",
        "dig",
        "nslookup",
        "ss",
        "uname",
        "uptime",
        "date",
        "df",
        "du",
        "free",
        "stat",
        "ps",
        "pgrep",
        "ip addr",
        "ip route",
        "traceroute",
        "git grep",
        "git branch",
        "git branch --show-current",  # Specific safe variant
        "git tag",
        "git remote -v",
        "git config --list",
        "docker ps",
        "docker images",
        "kubectl get",
        "kubectl describe",
        "kubectl logs",
        "kubectl cluster-info",
        "kubectl config view",
        "kubectl version",
        "kubectl api-resources",
        "kubectl api-versions",
        "kubectl top",
    ]

    # Initialize whitelist in state if it doesn't exist
    if "shell_command_whitelist" not in tool_context.state:
        # Initialize with default safe commands
        tool_context.state["shell_command_whitelist"] = agent_config.DEFAULT_SAFE_COMMANDS[:]
        logger.info(f"Initialized shell command whitelist with defaults: {agent_config.DEFAULT_SAFE_COMMANDS}")

    whitelist: list[str] = tool_context.state["shell_command_whitelist"]

    if action == "add":
        if not command:
            return ConfigureShellWhitelistOutput(status="Error: 'command' is required for 'add' action.")
        if command not in whitelist:
            whitelist.append(command)
            tool_context.state["shell_command_whitelist"] = whitelist  # Update state
            logger.info(f"Added command '{command}' to shell whitelist.")
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' added to whitelist.")
        else:
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' is already in the whitelist.")
    elif action == "remove":
        if not command:
            return ConfigureShellWhitelistOutput(status="Error: 'command' is required for 'remove' action.")
        if command in whitelist:
            whitelist.remove(command)
            tool_context.state["shell_command_whitelist"] = whitelist  # Update state
            logger.info(f"Removed command '{command}' from shell whitelist.")
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' removed from whitelist.")
        else:
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' not found in whitelist.")
    elif action == "list":
        return ConfigureShellWhitelistOutput(status="Current whitelist retrieved.", whitelist=list(whitelist))  # Return a copy
    elif action == "clear":
        tool_context.state["shell_command_whitelist"] = []
        logger.info("Cleared shell command whitelist.")
        return ConfigureShellWhitelistOutput(status="Shell command whitelist cleared.")
    else:
        return ConfigureShellWhitelistOutput(status=f"Error: Invalid action '{action}'. Valid actions are: add, remove, list, clear.")


# --- Check Command Existence Tool --- # <--- Added section start


class CheckCommandExistsInput(BaseModel):
    """Input model for checking command existence."""

    command: str = Field(..., description="The command name (e.g., 'git', 'ls') to check for existence.")


class CheckCommandExistsOutput(BaseModel):
    """Output model for checking command existence."""

    exists: bool
    command_checked: str
    message: str


def check_command_exists(args: dict, tool_context: ToolContext) -> CheckCommandExistsOutput:
    """Checks if a command exists in the system's PATH. Extracts the base command."""
    # Handle potential nested args structure from LLM function calls
    command_name = args.get("command")
    base_command = None
    message = ""

    if not command_name or not isinstance(command_name, str):
        message = "Error: 'command' argument is missing or not a string."
        logger.error(message)
        return CheckCommandExistsOutput(exists=False, command_checked=str(command_name) if command_name is not None else "", message=message)

    try:
        # Extract base command if it includes arguments (shutil.which needs the command name only)
        parts = shlex.split(command_name)
        if parts:
            base_command = parts[0]
        else:
            message = f"Could not parse base command from input: '{command_name}'"
            logger.warning(message)
            return CheckCommandExistsOutput(exists=False, command_checked=command_name, message=message)

    except ValueError as e:
        message = f"Error parsing command '{command_name}': {e}"
        logger.error(message)
        return CheckCommandExistsOutput(exists=False, command_checked=command_name, message=message)

    if not base_command:  # Should not happen if parsing worked, but check anyway
        message = "Error: Could not determine base command."
        logger.error(message)
        return CheckCommandExistsOutput(exists=False, command_checked=command_name, message=message)

    exists = shutil.which(base_command) is not None
    status_msg = "exists" if exists else "does not exist"
    message = f"Command '{base_command}' {status_msg} in system PATH."
    logger.info(f"Checked existence for command '{base_command}': {exists}")
    return CheckCommandExistsOutput(exists=exists, command_checked=base_command, message=message)


# <--- Added section end


# --- Shell Command Safety Check Tool --- #


class CheckShellCommandSafetyInput(BaseModel):
    """Input model for checking shell command safety."""

    command: str = Field(..., description="The shell command to check.")


class CheckShellCommandSafetyOutput(BaseModel):
    """Output model for checking shell command safety."""

    status: Literal["whitelisted", "approval_disabled", "approval_required"] = Field(..., description="The safety status of the command.")
    command: str = Field(..., description="The command that was checked.")
    message: str = Field(..., description="Explanation of the status.")


def check_shell_command_safety(args: dict, tool_context: ToolContext) -> CheckShellCommandSafetyOutput:
    """Checks if a shell command is safe to run without explicit user approval.

    Checks against the configured whitelist and the session's approval requirement.
    Does NOT execute the command.

    Args:
        args (dict): A dictionary containing:
            command (str): The shell command to check.
        tool_context (ToolContext): The context for accessing session state.

    Returns:
        CheckShellCommandSafetyOutput: An object indicating the safety status.
    """
    command = args.get("command")
    if not command:
        # Technically this shouldn't happen with Pydantic validation, but belt-and-suspenders
        return CheckShellCommandSafetyOutput(
            status="approval_required",  # Default to safest option on error
            command=command or "",
            message="Error: Command argument missing in input.",
        )

    require_approval = tool_context.state.get("require_shell_approval", True)
    # Ensure whitelist is initialized if needed (accessing it via configure_shell_whitelist initializes)
    if "shell_command_whitelist" not in tool_context.state:
        # Temporarily call configure_shell_whitelist with 'list' action to initialize state
        # This is a slight workaround to ensure initialization happens if only check/execute are called.
        # A cleaner approach might involve a dedicated initialization step or context manager.
        _ = configure_shell_whitelist({"action": "list"}, tool_context)

    shell_whitelist = tool_context.state.get("shell_command_whitelist", [])
    is_whitelisted = command in shell_whitelist

    if is_whitelisted:
        logger.info(f"Command '{command}' is whitelisted.")
        return CheckShellCommandSafetyOutput(status="whitelisted", command=command, message="Command is in the configured whitelist and can be run directly.")
    elif not require_approval:
        logger.info(f"Command '{command}' is not whitelisted, but shell approval is disabled.")
        return CheckShellCommandSafetyOutput(
            status="approval_disabled", command=command, message="Command is not whitelisted, but approval is disabled for this session."
        )
    else:
        logger.warning(f"Command '{command}' requires approval (not whitelisted and approval enabled).")
        return CheckShellCommandSafetyOutput(
            status="approval_required", command=command, message="Command requires user approval as it is not whitelisted and approval is enabled."
        )


# --- Vetted Shell Command Execution Tool --- #


class ExecuteVettedShellCommandInput(BaseModel):
    """Input model for the execute_vetted_shell_command tool."""

    command: str = Field(..., description="The shell command to execute. Should have been vetted first.")
    working_directory: Optional[str] = Field(None, description="Optional working directory to run the command in.")
    timeout: int = Field(60, description="Timeout in seconds for the command execution.")


class ExecuteVettedShellCommandOutput(BaseModel):
    """Output model for the execute_vetted_shell_command tool."""

    stdout: str | None = Field(None, description="The standard output of the command.")
    stderr: str | None = Field(None, description="The standard error of the command.")
    return_code: int | None = Field(None, description="The return code of the command.")
    command_executed: str | None = Field(None, description="The command that was executed.")
    status: str = Field(description="Status: 'executed' or 'error'.")
    message: str = Field(description="Additional information about the status.")


MAX_OUTPUT_CAPTURE_LENGTH = 1024 * 10  # Max 10KB for stdout/stderr to keep in full
TRUNCATE_HEAD_TAIL_LENGTH = 1024 * 2 # Show first/last 2KB if truncating

def _truncate_output(output: str, max_len: int, head_tail_len: int) -> str:
    if output is None or len(output) <= max_len:
        return output
    
    truncated_msg = f"[Output truncated. Original length: {len(output)} chars. Showing first and last {head_tail_len} chars]\\n"
    head = output[:head_tail_len]
    tail = output[-head_tail_len:]
    return truncated_msg + head + "\\n...\\n" + tail

def execute_vetted_shell_command(args: dict, tool_context: ToolContext) -> ExecuteVettedShellCommandOutput:
    """Executes a shell command that has ALREADY BEEN VETTED or explicitly approved.

    ***WARNING:*** DO NOT CALL THIS TOOL directly unless you have either:
    1. Called `check_shell_command_safety` and received a status of 'whitelisted' or 'approval_disabled'.
    2. Received explicit user confirmation to run this specific command.

    This tool performs NO safety checks itself.

    Args:
        args (dict): A dictionary containing:
            command (str): The shell command to execute.
            working_directory (Optional[str]): Optional working directory.
            timeout (Optional[int]): Optional timeout in seconds (default: 60).
        tool_context (ToolContext): The context (unused here, but required by ADK).

    Returns:
        ExecuteVettedShellCommandOutput: The result of the command execution.
    """
    command = args.get("command")
    working_directory = args.get("working_directory")
    timeout = args.get("timeout", 60)

    if not command:
        return ExecuteVettedShellCommandOutput(status="error", command_executed=command, message="Error: 'command' argument is missing.")

    try:
        timeout_sec = int(timeout)
    except (ValueError, TypeError):
        return ExecuteVettedShellCommandOutput(
            status="error", command_executed=command, message=f"Error: Invalid timeout value '{timeout}'. Must be an integer."
        )

    command_parts = shlex.split(command)
    logger.info(f"Executing vetted shell command: '{command}' in directory '{working_directory or '.'}'")

    try:
        process = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=timeout_sec,
            check=False,  # Don't raise exception on non-zero exit
        )
        logger.info(f"Vetted command '{command}' finished with return code {process.returncode}")
        
        stdout_processed = _truncate_output(process.stdout.strip(), MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH)
        stderr_processed = _truncate_output(process.stderr.strip(), MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH)
        
        return ExecuteVettedShellCommandOutput(
            stdout=stdout_processed,
            stderr=stderr_processed,
            return_code=process.returncode,
            command_executed=command,
            status="executed",
            message="Command executed successfully." if process.returncode == 0 else "Command executed with non-zero exit code.",
        )
    except FileNotFoundError:
        logger.error(f"Command not found during execution: {command_parts[0]}")
        return ExecuteVettedShellCommandOutput(
            stdout=None,
            stderr=_truncate_output(f"Error: Command not found: {command_parts[0]}", MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH),
            return_code=-1,  # Using distinct negative codes for different errors
            command_executed=command,
            status="error",
            message=f"Command not found: {command_parts[0]}",
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Vetted command '{command}' timed out after {timeout_sec} seconds.")
        return ExecuteVettedShellCommandOutput(
            stdout=None,
            stderr=_truncate_output(f"Error: Command timed out after {timeout_sec} seconds.", MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH),
            return_code=-2,
            command_executed=command,
            status="error",
            message=f"Command timed out after {timeout_sec} seconds.",
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred while running vetted command '{command}': {e}")
        return ExecuteVettedShellCommandOutput(
            stdout=None,
            stderr=_truncate_output(f"An unexpected error occurred: {e}", MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH),
            return_code=-3,
            command_executed=command,
            status="error",
            message=f"An unexpected error occurred: {e}"
        )


# --- Tool Registrations --- # <-- Added section (optional but good practice)

# Wrap functions with FunctionTool
# Note: This assumes FunctionTool is imported or available in the scope

configure_shell_approval_tool = FunctionTool(configure_shell_approval)
configure_shell_whitelist_tool = FunctionTool(configure_shell_whitelist)
check_command_exists_tool = FunctionTool(check_command_exists)
check_shell_command_safety_tool = FunctionTool(check_shell_command_safety)
execute_vetted_shell_command_tool = FunctionTool(execute_vetted_shell_command)
