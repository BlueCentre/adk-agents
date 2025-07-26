import logging
from pathlib import Path
import re

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def _extract_target(match: re.Match) -> str:
    """Extract the target (directory/file) from regex match groups"""
    groups = match.groups()
    if len(groups) >= 2:
        # If we have quote/backtick in group 1 and target in group 2
        return groups[1] if groups[1] else groups[0]
    return groups[0] if groups else ""


def _check_command_history_context(tool_context: ToolContext, query_lower: str) -> str:
    """Check command history and errors for relevant context"""
    context_info = ""

    if not tool_context or not tool_context.state:
        return context_info

    # Check for queries referencing previous commands/errors
    reference_patterns = [
        r"why did (that|it) fail",
        r"what(?:'s| is) wrong with (?:the )?(?:last|previous) command",
        r"what happened",
        r"(?:last|previous|recent) (?:command|error)",
        r"that (?:didn't work|failed)",
        r"fix (?:the|that) (?:error|problem)",
        r"what was the output of",
        r"(?:last|previous) (?:result|output)",
    ]

    query_references_history = any(
        re.search(pattern, query_lower) for pattern in reference_patterns
    )

    if query_references_history:
        # Get recent command history
        command_history = tool_context.state.get("command_history", [])
        recent_errors = tool_context.state.get("recent_errors", [])

        if recent_errors:
            # Add most recent error context
            latest_error = recent_errors[-1]
            context_info += "\n\nRecent Error Context:\n"
            context_info += f"Command: {latest_error.get('command', 'Unknown')}\n"
            context_info += f"Error Type: {latest_error['error_type']}\n"
            context_info += f"Error Output: {latest_error.get('stderr', '')[:200]}...\n"

        if command_history:
            # Add recent command context (last 3 commands)
            recent_commands = command_history[-3:]
            context_info += "\n\nRecent Command History:\n"
            for _i, cmd in enumerate(recent_commands, 1):
                status = "✓" if cmd.get("success") else "✗"
                context_info += f"{status} {cmd.get('command', 'Unknown')}\n"

    return context_info


def _execute_contextual_actions(tool_context: ToolContext, actions: list[dict]) -> list[dict]:
    """Execute contextual actions and return results"""
    results = []
    # Get current directory from tool_context.state (or fallback to Path.cwd())
    current_dir_str = tool_context.state.get("current_directory", str(Path.cwd()))
    current_dir = Path(current_dir_str)

    for action in actions:
        try:
            if action["type"] == "list_directory":
                target_path = Path(action["target"])
                if not target_path.is_absolute():
                    target_path = current_dir / target_path

                if target_path.exists():
                    try:
                        from ..tools.filesystem import list_directory_contents

                        tool_result = list_directory_contents(str(target_path))
                        if tool_result.get("status") == "success":
                            # Convert tool format to expected format
                            all_items = tool_result["contents"]
                            files = []
                            directories = []
                            for item_name in all_items:
                                item_path = target_path / item_name
                                if item_path.is_file():
                                    files.append(item_name)
                                elif item_path.is_dir():
                                    directories.append(item_name)
                            result = {"files": files, "directories": directories}
                        else:
                            msg = tool_result.get("message", "Unknown error")
                            result = f"Error listing directory: {msg}"
                            results.append({"action": action, "result": result, "status": "error"})
                            continue
                    except ImportError:
                        files = []
                        directories = []
                        for item in target_path.iterdir():
                            if item.is_file():
                                files.append(item.name)
                            elif item.is_dir():
                                directories.append(item.name)
                        result = {"files": files, "directories": directories}

                    results.append({"action": action, "result": result, "status": "success"})
                else:
                    results.append(
                        {
                            "action": action,
                            "result": f"Directory '{target_path}' not found",
                            "status": "error",
                        }
                    )

            elif action["type"] == "read_file":
                target_path = Path(action["target"])
                if not target_path.is_absolute():
                    target_path = current_dir / target_path

                if target_path.exists():
                    try:
                        from ..tools.filesystem import read_file_content

                        tool_result = read_file_content(str(target_path))
                        if tool_result.get("status") == "success":
                            result = tool_result["content"]  # Extract content from tool format
                        else:
                            result = (
                                f"Error reading file: {tool_result.get('message', 'Unknown error')}"
                            )
                            results.append({"action": action, "result": result, "status": "error"})
                            continue
                    except ImportError:
                        result = target_path.read_text(encoding="utf-8")

                    results.append({"action": action, "result": result, "status": "success"})
                else:
                    results.append(
                        {
                            "action": action,
                            "result": f"File '{target_path}' not found",
                            "status": "error",
                        }
                    )

        except Exception as e:
            results.append(
                {
                    "action": action,
                    "result": f"Error executing {action['type']}: {e!s}",
                    "status": "error",
                }
            )

    return results


def _preprocess_and_add_context_to_agent_prompt(callback_context: CallbackContext = None):
    """
    Callback to preprocess user input and inject relevant contextual information
    (file system, command history, error logs) into the agent's session state.
    This function is intended to be used as a before_agent_callback.

    Note: This callback initializes contextual state but doesn't directly modify
    user messages. The agent's prompt instructions will guide the LLM to check
    session state for contextual information.
    """
    if not callback_context:
        logger.warning(
            "[_preprocess_and_add_context_to_agent_prompt] No callback context available."
        )
        return

    # Ensure current_directory is always up-to-date in session state
    # Access state via callback_context.state (the correct ADK pattern)
    if hasattr(callback_context, "state") and callback_context.state is not None:
        session_state = callback_context.state
        if "current_directory" not in session_state:
            session_state["current_directory"] = str(Path.cwd())

        # Initialize empty command history and errors if not present
        if "command_history" not in session_state:
            session_state["command_history"] = []
        if "recent_errors" not in session_state:
            session_state["recent_errors"] = []

        logger.info(
            "[_preprocess_and_add_context_to_agent_prompt] "
            "Initialized contextual state for agent session."
        )
    else:
        logger.warning(
            "[_preprocess_and_add_context_to_agent_prompt] "
            "No session state available in callback context."
        )
