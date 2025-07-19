"""Tools for executing shell commands."""

import logging
import shlex
import shutil
import subprocess
from typing import Any, Dict, List, Literal, Optional

# Import ToolContext for state management
from google.adk.tools import (
    FunctionTool,  # Ensure FunctionTool is imported if not already
    ToolContext,
)
from pydantic import BaseModel, Field

from .. import config as agent_config
from ..components.learning_system import learning_system  # Import the learning system

logger = logging.getLogger(__name__)

# --- Configuration Tool --- #


class ConfigureShellApprovalInput(BaseModel):
    """Input model for configuring shell command approval."""

    require_approval: bool = Field(
        ..., description="Set to true to require approval, false to disable."
    )


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
    return ConfigureShellApprovalOutput(
        status=f"Shell command approval requirement is now {status}."
    )


# --- Whitelist Configuration Tool --- #


class ConfigureShellWhitelistInput(BaseModel):
    """Input model for configuring the shell command whitelist."""

    action: Literal["add", "remove", "list", "clear"] = Field(
        ..., description="Action to perform: add, remove, list, or clear."
    )
    command: Optional[str] = Field(
        None, description="The command to add or remove (required for 'add' and 'remove' actions)."
    )


class ConfigureShellWhitelistOutput(BaseModel):
    """Output model for configuring the shell command whitelist."""

    status: str
    whitelist: Optional[list[str]] = Field(
        None, description="The current whitelist (only for 'list' action)."
    )


def configure_shell_whitelist(
    args: dict, tool_context: ToolContext
) -> ConfigureShellWhitelistOutput:
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

    # Initialize whitelist in state if it doesn't exist
    if "shell_command_whitelist" not in tool_context.state:
        # Initialize with default safe commands
        tool_context.state["shell_command_whitelist"] = agent_config.DEFAULT_SAFE_COMMANDS[:]
        logger.info(
            f"Initialized shell command whitelist with defaults: {agent_config.DEFAULT_SAFE_COMMANDS}"
        )

    whitelist: list[str] = tool_context.state["shell_command_whitelist"]

    if action == "add":
        if not command:
            return ConfigureShellWhitelistOutput(
                status="Error: 'command' is required for 'add' action."
            )
        if command not in whitelist:
            whitelist.append(command)
            tool_context.state["shell_command_whitelist"] = whitelist  # Update state
            logger.info(f"Added command '{command}' to shell whitelist.")
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' added to whitelist.")
        return ConfigureShellWhitelistOutput(
            status=f"Command '{command}' is already in the whitelist."
        )
    if action == "remove":
        if not command:
            return ConfigureShellWhitelistOutput(
                status="Error: 'command' is required for 'remove' action."
            )
        if command in whitelist:
            whitelist.remove(command)
            tool_context.state["shell_command_whitelist"] = whitelist  # Update state
            logger.info(f"Removed command '{command}' from shell whitelist.")
            return ConfigureShellWhitelistOutput(
                status=f"Command '{command}' removed from whitelist."
            )
        return ConfigureShellWhitelistOutput(status=f"Command '{command}' not found in whitelist.")
    if action == "list":
        return ConfigureShellWhitelistOutput(
            status="Current whitelist retrieved.", whitelist=list(whitelist)
        )  # Return a copy
    if action == "clear":
        tool_context.state["shell_command_whitelist"] = []
        logger.info("Cleared shell command whitelist.")
        return ConfigureShellWhitelistOutput(status="Shell command whitelist cleared.")
    return ConfigureShellWhitelistOutput(
        status=f"Error: Invalid action '{action}'. Valid actions are: add, remove, list, clear."
    )


# --- Check Command Existence Tool --- # <--- Added section start


class CheckCommandExistsInput(BaseModel):
    """Input model for checking command existence."""

    command: str = Field(
        ..., description="The command name (e.g., 'git', 'ls') to check for existence."
    )


class CheckCommandExistsOutput(BaseModel):
    """Output model for checking command existence."""

    exists: bool
    command_checked: str
    message: str


def check_command_exists(args: dict, tool_context: ToolContext) -> CheckCommandExistsOutput:
    """Checks if a command exists in the system's PATH. Extracts the base command."""
    # Handle potential nested args structure from LLM function calls
    # Try to get 'command' directly, then check for nested 'args.command_name'
    command_name = args.get("command")
    if command_name is None or not isinstance(command_name, str):
        nested_args = args.get("args", {})
        command_name = nested_args.get("command_name")

    base_command = None
    message = ""

    if not command_name or not isinstance(command_name, str):
        message = "Error: 'command' argument is missing or not a string in expected formats."
        logger.error(message)
        return CheckCommandExistsOutput(
            exists=False,
            command_checked=str(command_name) if command_name is not None else "",
            message=message,
        )

    try:
        # Extract base command if it includes arguments (shutil.which needs the command name only)
        parts = shlex.split(command_name)
        if parts:
            base_command = parts[0]
        else:
            message = f"Could not parse base command from input: '{command_name}'"
            logger.warning(message)
            return CheckCommandExistsOutput(
                exists=False, command_checked=command_name, message=message
            )

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

    status: Literal["whitelisted", "approval_disabled", "approval_required"] = Field(
        ..., description="The safety status of the command."
    )
    command: str = Field(..., description="The command that was checked.")
    message: str = Field(..., description="Explanation of the status.")


def check_shell_command_safety(
    args: dict, tool_context: ToolContext
) -> CheckShellCommandSafetyOutput:
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
        return CheckShellCommandSafetyOutput(
            status="whitelisted",
            command=command,
            message="Command is in the configured whitelist and can be run directly.",
        )
    if not require_approval:
        logger.info(f"Command '{command}' is not whitelisted, but shell approval is disabled.")
        return CheckShellCommandSafetyOutput(
            status="approval_disabled",
            command=command,
            message="Command is not whitelisted, but approval is disabled for this session.",
        )
    logger.warning(f"Command '{command}' requires approval (not whitelisted and approval enabled).")
    return CheckShellCommandSafetyOutput(
        status="approval_required",
        command=command,
        message="Command requires user approval as it is not whitelisted and approval is enabled.",
    )


# --- Vetted Shell Command Execution Tool --- #


class ExecuteVettedShellCommandInput(BaseModel):
    """Input model for the execute_vetted_shell_command tool."""

    command: str = Field(
        ..., description="The shell command to execute. Should have been vetted first."
    )
    working_directory: Optional[str] = Field(
        None, description="Optional working directory to run the command in."
    )
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
TRUNCATE_HEAD_TAIL_LENGTH = 1024 * 2  # Show first/last 2KB if truncating


def _truncate_output(output: str, max_len: int, head_tail_len: int) -> str:
    if output is None or len(output) <= max_len:
        return output

    truncated_msg = f"[Output truncated. Original length: {len(output)} chars. Showing first and last {head_tail_len} chars]\\n"
    head = output[:head_tail_len]
    tail = output[-head_tail_len:]
    return truncated_msg + head + "\\n...\\n" + tail


def execute_vetted_shell_command(
    args: dict,
    tool_context: ToolContext,  # noqa: ARG001
) -> ExecuteVettedShellCommandOutput:
    """Executes a shell command that has ALREADY BEEN VETTED or explicitly approved.

    ***WARNING:*** DO NOT CALL THIS TOOL directly unless you have either:
    1. Called `check_shell_command_safety` and received a status of 'whitelisted' or
       'approval_disabled'.
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
        return ExecuteVettedShellCommandOutput(
            status="error",
            command_executed=command,
            message="Error: 'command' argument is missing.",
        )

    try:
        timeout_sec = int(timeout)
    except (ValueError, TypeError):
        return ExecuteVettedShellCommandOutput(
            status="error",
            command_executed=command,
            message=f"Error: Invalid timeout value '{timeout}'. Must be an integer.",
        )

    logger.info(
        f"Executing vetted shell command: '{command}' in directory '{working_directory or '.'}'"
    )

    # Try multiple command parsing strategies if the first one fails
    parsing_strategies = [
        ("shlex_split", lambda cmd: shlex.split(cmd)),
        ("shell_true", lambda cmd: cmd),  # Execute as shell string
        ("simple_split", lambda cmd: cmd.split()),  # Simple whitespace split as fallback
    ]

    last_error = None

    for strategy_name, parser in parsing_strategies:
        try:
            if strategy_name == "shlex_split":
                command_parts = parser(command)
                shell_mode = False
            elif strategy_name == "shell_true":
                command_parts = command
                shell_mode = True
            else:  # simple_split
                command_parts = parser(command)
                shell_mode = False

            logger.info(f"Trying command execution with strategy '{strategy_name}'")

            process = subprocess.run(
                command_parts,
                capture_output=True,
                text=True,
                cwd=working_directory,
                timeout=timeout_sec,
                check=False,  # Don't raise exception on non-zero exit
                shell=shell_mode,  # Use shell mode for complex commands
            )

            logger.info(
                f"Vetted command '{command}' finished with return code "
                f"{process.returncode} using strategy '{strategy_name}'"
            )

            stdout_processed = _truncate_output(
                process.stdout.strip(), MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH
            )
            stderr_processed = _truncate_output(
                process.stderr.strip(), MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH
            )

            # Add strategy info to success message for debugging
            success_msg = (
                "Command executed successfully."
                if process.returncode == 0
                else "Command executed with non-zero exit code."
            )
            if strategy_name != "shlex_split":
                success_msg += f" (Used fallback strategy: {strategy_name})"

            return ExecuteVettedShellCommandOutput(
                stdout=stdout_processed,
                stderr=stderr_processed,
                return_code=process.returncode,
                command_executed=command,
                status="executed",
                message=success_msg,
            )

        except ValueError as ve:
            # This is likely a shlex parsing error (like "No closing quotation")
            logger.warning(f"Command parsing failed with strategy '{strategy_name}': {ve}")
            last_error = ve
            if strategy_name == "shlex_split":
                # Continue to try other strategies
                continue
            # If even simple strategies fail, this is a more serious error
            break

        except FileNotFoundError:
            logger.error(f"Command not found during execution: {command}")
            return ExecuteVettedShellCommandOutput(
                stdout=None,
                stderr=_truncate_output(
                    f"Error: Command not found: {command}",
                    MAX_OUTPUT_CAPTURE_LENGTH,
                    TRUNCATE_HEAD_TAIL_LENGTH,
                ),
                return_code=-1,
                command_executed=command,
                status="error",
                message=f"Command not found: {command}",
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Vetted command '{command}' timed out after {timeout_sec} seconds.")
            return ExecuteVettedShellCommandOutput(
                stdout=None,
                stderr=_truncate_output(
                    f"Error: Command timed out after {timeout_sec} seconds.",
                    MAX_OUTPUT_CAPTURE_LENGTH,
                    TRUNCATE_HEAD_TAIL_LENGTH,
                ),
                return_code=-2,
                command_executed=command,
                status="error",
                message=f"Command timed out after {timeout_sec} seconds.",
            )
        except Exception as e:
            logger.warning(f"Command execution failed with strategy '{strategy_name}': {e}")
            last_error = e
            continue

    # If we get here, all strategies failed
    error_msg = f"All command execution strategies failed. Last error: {last_error}"
    logger.error(f"An error occurred while running vetted command '{command}': {error_msg}")
    return ExecuteVettedShellCommandOutput(
        stdout=None,
        stderr=_truncate_output(error_msg, MAX_OUTPUT_CAPTURE_LENGTH, TRUNCATE_HEAD_TAIL_LENGTH),
        return_code=-3,
        command_executed=command,
        status="error",
        message=error_msg,
    )


# --- Command Reconstruction Utilities --- #


def suggest_command_alternatives(
    original_command: str,
    error_type: str = "parsing_error",
    context_keywords: Optional[list[str]] = None,
) -> list[str]:
    """Suggests alternative command formulations for commands that failed due to parsing issues.

    This is particularly useful for git commit commands with complex messages.

    Args:
        original_command (str): The original command that failed
        error_type (str): The type of error encountered (e.g., "parsing_error").
        context_keywords (list[str]): Keywords from the command context for better suggestions.

    Returns:
        List[str]: List of alternative command formulations
    """
    if context_keywords is None:
        context_keywords = []

    # Get suggestions from the learning system first
    learned_suggestions = learning_system.get_suggestions(
        original_command, error_type, context_keywords
    )
    alternatives = list(learned_suggestions)

    # Handle git commit commands specifically
    if original_command.startswith("git commit"):
        try:
            # Extract the commit message from various patterns
            import re

            # Pattern 1: git commit -m "message" -m "description"
            if "-m " in original_command:
                # Try to extract and properly escape commit messages
                msg_pattern = r'-m\s+["\']([^"\']*)["\']'
                messages = re.findall(msg_pattern, original_command)

                if messages:
                    # Suggest using a simpler approach with escaped quotes
                    if len(messages) == 1:
                        # Single message
                        escaped_msg = messages[0].replace('"', '\\"').replace("'", "\\'")
                        alternatives.append(f'git commit -m "{escaped_msg}"')
                    else:
                        # Multiple messages - suggest combining them
                        combined_msg = "\\n\\n".join(messages)
                        escaped_msg = combined_msg.replace('"', '\\"').replace("'", "\\'")
                        alternatives.append(f'git commit -m "{escaped_msg}"')

                # Suggest using heredoc approach for complex messages
                alternatives.append("git commit -F -")  # Read from stdin
                alternatives.append("git commit")  # Open editor

            # Always suggest the basic commit without message as fallback
            if "git commit -m" in original_command:
                alternatives.append("git commit")  # Let git open the editor

        except Exception as e:
            logger.warning(f"Failed to parse git commit command for alternatives: {e}")

    # For any command with quotes, suggest shell-escaped version
    if '"' in original_command or "'" in original_command:
        # Simple escape strategy - replace quotes with escaped versions
        escaped_cmd = original_command.replace('"', '\\"').replace("'", "\\'")
        if escaped_cmd != original_command:
            alternatives.append(escaped_cmd)

    # Add a generic suggestion for complex commands
    if len(original_command) > 100 or original_command.count('"') > 2:
        alternatives.append("# Consider breaking this into multiple simpler commands")
        alternatives.append("# Or use a shell script file for complex operations")

    return alternatives


class ExecuteVettedShellCommandWithRetryInput(BaseModel):
    """Input model for the enhanced shell command execution with built-in retry logic."""

    command: str = Field(..., description="The shell command to execute.")
    working_directory: Optional[str] = Field(
        None, description="Optional working directory to run the command in."
    )
    timeout: int = Field(60, description="Timeout in seconds for the command execution.")
    auto_retry: bool = Field(
        True,
        description="Whether to automatically try alternative command formats on parsing failures.",
    )


class ExecuteVettedShellCommandWithRetryOutput(BaseModel):
    """Output model for the enhanced shell command execution."""

    stdout: str | None = Field(None, description="The standard output of the command.")
    stderr: str | None = Field(None, description="The standard error of the command.")
    return_code: int | None = Field(None, description="The return code of the command.")
    command_executed: str | None = Field(None, description="The actual command that was executed.")
    strategy_used: str | None = Field(None, description="The execution strategy that succeeded.")
    alternatives_tried: list[str] = Field(
        default_factory=list, description="Alternative commands that were attempted."
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggested alternative commands for manual retry."
    )
    status: str = Field(description="Status: 'executed', 'error', or 'failed_with_suggestions'.")
    message: str = Field(description="Additional information about the status.")


def execute_vetted_shell_command_with_retry(
    args: dict, tool_context: ToolContext
) -> ExecuteVettedShellCommandWithRetryOutput:
    """Enhanced shell command execution with automatic retry and alternative suggestions.

    This function provides better error handling for complex commands, especially git commits
    with multi-line messages that may have quote parsing issues.

    Args:
        args (dict): A dictionary containing:
            command (str): The shell command to execute.
            working_directory (Optional[str]): Optional working directory.
            timeout (Optional[int]): Optional timeout in seconds (default: 60).
            auto_retry (Optional[bool]): Whether to auto-retry with alternatives (default: True).
        tool_context (ToolContext): The context for state management.

    Returns:
        ExecuteVettedShellCommandWithRetryOutput: Enhanced result with retry information.
    """
    command = args.get("command")
    args.get("working_directory")
    args.get("timeout", 60)
    auto_retry = args.get("auto_retry", True)

    if not command:
        return ExecuteVettedShellCommandWithRetryOutput(
            status="error",
            command_executed=command,
            message="Error: 'command' argument is missing.",
        )

    # First, try the standard execution
    standard_result = execute_vetted_shell_command(args, tool_context)

    # If it succeeded, return the result with additional metadata
    if standard_result.status == "executed":
        return ExecuteVettedShellCommandWithRetryOutput(
            stdout=standard_result.stdout,
            stderr=standard_result.stderr,
            return_code=standard_result.return_code,
            command_executed=standard_result.command_executed,
            strategy_used="standard",
            status="executed",
            message=standard_result.message,
        )

    # If it failed and auto_retry is disabled, return with suggestions
    if not auto_retry:
        suggestions = suggest_command_alternatives(command, error_type="unknown_error")
        return ExecuteVettedShellCommandWithRetryOutput(
            status="failed_with_suggestions",
            command_executed=command,
            suggestions=suggestions,
            message=(
                f"Command failed: {standard_result.message}. Auto-retry disabled. See "
                "suggestions for alternatives."
            ),
        )

    # If it failed due to parsing issues, try alternatives
    if (
        "parsing" in standard_result.message.lower()
        or "quotation" in standard_result.message.lower()
    ):
        logger.info(f"Command failed with parsing error, trying alternative approaches: {command}")

        alternatives = suggest_command_alternatives(command, error_type="parsing_error")
        alternatives_tried = []

        for alternative in alternatives:
            if alternative.startswith("#"):  # Skip comment suggestions
                continue

            logger.info(f"Trying alternative command: {alternative}")
            alternatives_tried.append(alternative)

            alt_args = args.copy()
            alt_args["command"] = alternative

            alt_result = execute_vetted_shell_command(alt_args, tool_context)

            if alt_result.status == "executed":
                # Record the successful alternative
                learning_system.record_success(
                    original_command=command,
                    error_type="parsing_error",  # Assuming parsing error for now
                    successful_alternative=alternative,
                    context_keywords=[],  # Can add more context later if needed
                )
                return ExecuteVettedShellCommandWithRetryOutput(
                    stdout=alt_result.stdout,
                    stderr=alt_result.stderr,
                    return_code=alt_result.return_code,
                    command_executed=alt_result.command_executed,
                    strategy_used="alternative",
                    alternatives_tried=alternatives_tried,
                    status="executed",
                    message=(
                        f"Original command failed, but alternative succeeded: {alt_result.message}"
                    ),
                )

        # All alternatives failed
        return ExecuteVettedShellCommandWithRetryOutput(
            status="failed_with_suggestions",
            command_executed=command,
            alternatives_tried=alternatives_tried,
            suggestions=[
                alt for alt in alternatives if alt.startswith("#") or alt not in alternatives_tried
            ],
            message=f"Original command and {len(alternatives_tried)} alternatives failed. Original "
            f"error: {standard_result.message}",
        )

    # For non-parsing errors, return the original error with suggestions
    suggestions = suggest_command_alternatives(command)
    return ExecuteVettedShellCommandWithRetryOutput(
        status="error",
        stdout=standard_result.stdout,
        stderr=standard_result.stderr,
        return_code=standard_result.return_code,
        command_executed=standard_result.command_executed,
        suggestions=suggestions,
        message=standard_result.message,
    )


# --- Tool Registrations --- # <-- Added section (optional but good practice)

# Wrap functions with FunctionTool
# Note: This assumes FunctionTool is imported or available in the scope

configure_shell_approval_tool = FunctionTool(configure_shell_approval)
configure_shell_whitelist_tool = FunctionTool(configure_shell_whitelist)
check_command_exists_tool = FunctionTool(check_command_exists)
check_shell_command_safety_tool = FunctionTool(check_shell_command_safety)
execute_vetted_shell_command_tool = FunctionTool(execute_vetted_shell_command)
execute_vetted_shell_command_with_retry_tool = FunctionTool(execute_vetted_shell_command_with_retry)
