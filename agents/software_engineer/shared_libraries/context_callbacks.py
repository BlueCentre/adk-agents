"""Context-aware callback functions for software engineer agents.

This module implements callback functions that provide contextual information
to agents before they process user queries, enabling more intelligent responses.
"""

import logging
from pathlib import Path
import re
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext

from .constants import DEPENDENCY_FILES
from .proactive_error_detection import detect_and_suggest_error_fixes
from .proactive_optimization import configure_proactive_optimization

logger = logging.getLogger(__name__)


def _extract_target(match: re.Match) -> str:
    """Extract the target (directory/file) from regex match groups"""
    groups = match.groups()
    if len(groups) >= 2:
        # If we have quote/backtick in group 1 and target in group 2
        return groups[1] if groups[1] else groups[0]
    return groups[0] if groups else ""


def _check_command_history_context(tool_context: ToolContext, query_lower: str) -> Optional[str]:
    """Check if the query refers to command history or recent errors"""
    try:
        session_state = tool_context.state

        # Patterns that indicate references to previous commands/errors
        history_patterns = [
            r"why.*fail",
            r"what.*wrong",
            r"that.*error",
            r"last.*command",
            r"previous.*command",
            r"recent.*error",
            r"what.*happened",
            r"error.*message",
        ]

        # Check if query matches any pattern
        for pattern in history_patterns:
            if re.search(pattern, query_lower):
                # Get recent command history
                command_history = session_state.get("command_history", [])
                recent_errors = session_state.get("recent_errors", [])

                context_parts = []

                # Add recent failed commands
                if recent_errors:
                    context_parts.append(f"Recent errors: {recent_errors[-3:]}")

                # Add recent commands
                if command_history:
                    recent_commands = command_history[-5:]  # Last 5 commands
                    context_parts.append(f"Recent commands: {recent_commands}")

                if context_parts:
                    return " | ".join(context_parts)

        return None

    except Exception as e:
        logger.error(f"Error checking command history context: {e}")
        return None


def _analyze_user_query_for_context(user_message: str) -> tuple[list[dict[str, Any]], str]:
    """
    Analyze user query to determine if contextual actions should be triggered.
    Returns tuple of (actions_to_execute, query_lower)
    """
    query_lower = user_message.lower()
    actions = []

    try:
        # Directory listing patterns
        dir_patterns = [
            (r"what.*in.*?([a-zA-Z_][a-zA-Z0-9_./\-]*)", "directory_reference"),
            (r"list.*?([a-zA-Z_][a-zA-Z0-9_./\-]*)", "directory_reference"),
            (
                r"show.*?([a-zA-Z_][a-zA-Z0-9_./\-]*)\s+(?:dir|directory|folder)",
                "directory_reference",
            ),
            (r"contents.*?of.*?([a-zA-Z_][a-zA-Z0-9_./\-]*)", "directory_reference"),
            (r"files.*?in.*?([a-zA-Z_][a-zA-Z0-9_./\-]*)", "directory_reference"),
        ]

        # File reading patterns
        file_patterns = [
            (r"show.*?([a-zA-Z_][a-zA-Z0-9_./\-]*\.[\w]+)", "file_reference"),
            (r"read.*?([a-zA-Z_][a-zA-Z0-9_./\-]*\.[\w]+)", "file_reference"),
            (r"content.*?of.*?([a-zA-Z_][a-zA-Z0-9_./\-]*\.[\w]+)", "file_reference"),
            (r"open.*?([a-zA-Z_][a-zA-Z0-9_./\-]*\.[\w]+)", "file_reference"),
            (r"display.*?([a-zA-Z_][a-zA-Z0-9_./\-]*\.[\w]+)", "file_reference"),
        ]

        # Check for directory references
        for pattern, _action_type in dir_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                target = match.strip() if isinstance(match, str) else match[0].strip()
                if target and not target.startswith("http"):  # Avoid URLs
                    actions.append({"type": "list_directory", "target": target})

        # Check for file references
        for pattern, _action_type in file_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                target = match.strip() if isinstance(match, str) else match[0].strip()
                if target and not target.startswith("http"):  # Avoid URLs
                    actions.append({"type": "read_file", "target": target})

        # Remove duplicates
        unique_actions = []
        seen = set()
        for action in actions:
            key = (action["type"], action["target"])
            if key not in seen:
                unique_actions.append(action)
                seen.add(key)

        return unique_actions, query_lower

    except Exception as e:
        logger.error(f"Error analyzing user query for context: {e}")
        return [], query_lower


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
                        # Fallback implementation
                        try:
                            all_items = [p.name for p in target_path.iterdir()]
                            files = [p.name for p in target_path.iterdir() if p.is_file()]
                            directories = [p.name for p in target_path.iterdir() if p.is_dir()]
                            result = {"files": files, "directories": directories}
                        except Exception as fallback_e:
                            result = f"Error listing directory: {fallback_e}"
                            results.append({"action": action, "result": result, "status": "error"})
                            continue
                else:
                    result = f"Directory not found: {target_path}"
                    results.append({"action": action, "result": result, "status": "error"})
                    continue

                results.append({"action": action, "result": result, "status": "success"})

            elif action["type"] == "read_file":
                target_path = Path(action["target"])
                if not target_path.is_absolute():
                    target_path = current_dir / target_path

                if target_path.exists() and target_path.is_file():
                    try:
                        from ..tools.filesystem import read_file_content

                        tool_result = read_file_content(str(target_path))
                        if tool_result.get("status") == "success":
                            result = tool_result["content"]
                        else:
                            msg = tool_result.get("message", "Unknown error")
                            result = f"Error reading file: {msg}"
                            results.append({"action": action, "result": result, "status": "error"})
                            continue
                    except ImportError:
                        # Fallback implementation
                        try:
                            result = target_path.read_text(encoding="utf-8")
                        except Exception as fallback_e:
                            result = f"Error reading file: {fallback_e}"
                            results.append({"action": action, "result": result, "status": "error"})
                            continue
                else:
                    result = f"File not found: {target_path}"
                    results.append({"action": action, "result": result, "status": "error"})
                    continue

                results.append({"action": action, "result": result, "status": "success"})

        except Exception as e:
            logger.error(f"Error executing contextual action {action}: {e}")
            results.append({"action": action, "result": f"Error: {e}", "status": "error"})

    return results


def _should_update_project_context(session_state: dict) -> bool:
    """
    Determine if project context should be updated based on various criteria.

    Args:
        session_state: The current session state

    Returns:
        True if project context should be updated
    """
    try:
        # Always update if never done before
        if "project_structure" not in session_state:
            return True

        # Check if current directory changed
        current_dir = session_state.get("current_directory", str(Path.cwd()))
        last_updated_dir = session_state.get("project_context_updated")
        if last_updated_dir != current_dir:
            return True

        # Check if we have no dependencies but dependency files might exist
        dependencies = session_state.get("project_dependencies", {})
        if not dependencies.get("dependency_files_found"):
            # Check if any dependency files exist in current directory
            current_path = Path(current_dir)
            for dep_file in DEPENDENCY_FILES:
                if (current_path / dep_file).exists():
                    return True

        return False

    except Exception as e:
        logger.debug(f"Error checking if project context should update: {e}")
        return False


def _update_project_context_if_needed(session_state: dict) -> None:
    """
    Update project context in session state if needed.

    Args:
        session_state: The session state to update
    """
    try:
        if _should_update_project_context(session_state):
            from ..tools.project_context import update_project_context_in_session

            current_dir = session_state.get("current_directory", str(Path.cwd()))
            summary = update_project_context_in_session(session_state, current_dir)

            logger.info(f"Updated project context: {summary}")

    except Exception as e:
        logger.error(f"Error updating project context: {e}")


def _preprocess_and_add_context_to_agent_prompt(callback_context: CallbackContext = None):
    """
    Callback to preprocess user input and inject relevant contextual information
    (file system, command history, error logs) into the agent's session state.
    This function is intended to be used as a before_agent_callback.

    This callback now actively analyzes recent user messages and executes contextual
    actions like directory listing and file reading when appropriate.

    Enhanced with project structure mapping and dependency inference capabilities.
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

        # NEW: Update project context if needed (Task 1.3.1 & 1.3.2)
        _update_project_context_if_needed(session_state)

        # NEW: Try to analyze recent user messages for contextual actions
        try:
            # Look for recent user messages in conversation history or state
            recent_user_message = None

            # Check various possible locations for the current user message
            if "current_user_message" in session_state:
                recent_user_message = session_state["current_user_message"]
            elif session_state.get("conversation_context"):
                # Get the most recent message if available
                recent_entry = session_state["conversation_context"][-1]
                if isinstance(recent_entry, dict) and "user_message" in recent_entry:
                    recent_user_message = recent_entry["user_message"]
            elif "temp:current_turn" in session_state:
                current_turn = session_state["temp:current_turn"]
                if isinstance(current_turn, dict) and "user_message" in current_turn:
                    recent_user_message = current_turn["user_message"]

            if recent_user_message and isinstance(recent_user_message, str):
                logger.info(
                    "[_preprocess_and_add_context_to_agent_prompt] "
                    f"Analyzing user query: {recent_user_message[:100]}..."
                )

                # Analyze the user query for contextual actions
                actions, query_lower = _analyze_user_query_for_context(recent_user_message)

                # Check for project-related queries that might need updated context
                project_query_patterns = [
                    "project structure",
                    "dependencies",
                    "what.*dependencies",
                    "project.*files",
                    "architecture",
                    "codebase structure",
                ]

                force_project_update = any(
                    re.search(pattern, query_lower) for pattern in project_query_patterns
                )

                if force_project_update:
                    logger.info("Detected project-related query, forcing context update")
                    _update_project_context_if_needed(session_state)

                # VCS assistance is now handled centrally in enhanced_agent.py to avoid duplication

                if actions:
                    logger.info(
                        "[_preprocess_and_add_context_to_agent_prompt] "
                        f"Found {len(actions)} contextual actions to execute"
                    )

                    # Create a mock ToolContext to execute actions
                    from types import SimpleNamespace

                    mock_tool_context = SimpleNamespace()
                    mock_tool_context.state = session_state

                    # Execute contextual actions
                    results = _execute_contextual_actions(mock_tool_context, actions)

                    # Check for command history context
                    history_context = _check_command_history_context(mock_tool_context, query_lower)

                    # Store results in session state for LLM access
                    contextual_info = {
                        "actions_executed": len(actions),
                        "results": results,
                        "command_history_context": history_context,
                        "timestamp": str(Path.cwd()),  # Use a timestamp-like field
                    }

                    session_state["__preprocessed_context_for_llm"] = contextual_info

                    logger.info(
                        "[_preprocess_and_add_context_to_agent_prompt] "
                        f"Executed {len(actions)} contextual actions with {len(results)} results"
                    )

        except Exception as e:
            logger.error(f"Error in contextual preprocessing: {e}")

        # NEW: Always check for proactive error suggestions, even without contextual actions
        # This ensures we catch recent errors regardless of the user's query
        try:
            proactive_suggestions = detect_and_suggest_error_fixes(session_state)
            if proactive_suggestions:
                # Add or update proactive suggestions in existing context
                if "__preprocessed_context_for_llm" not in session_state:
                    session_state["__preprocessed_context_for_llm"] = {}

                session_state["__preprocessed_context_for_llm"]["proactive_error_suggestions"] = (
                    proactive_suggestions
                )

                logger.info(
                    "[_preprocess_and_add_context_to_agent_prompt] "
                    "Added proactive error suggestions to context"
                )
        except Exception as e:
            logger.error(f"Error in proactive error detection: {e}")

        # NEW: Check for configuration commands for proactive optimization (Milestone 2.2.3)
        try:
            if recent_user_message and isinstance(recent_user_message, str):
                # Handle optimization configuration commands with refined patterns for actual
                #  commands
                # Match patterns like "disable optimization", "turn off optimization suggestions",
                #  etc.
                # but exclude questions like "How do I disable..." or "Can you disable..."
                disable_patterns = [
                    r"^(please\s+)?(disable|turn\s+off)\s+optimization",  # Direct commands
                    r"\b(disable|turn\s+off)\s+optimization\s+(suggestions?|features?)\b",  # With "suggestions"  # noqa: E501
                ]

                enable_patterns = [
                    r"^(please\s+)?(enable|turn\s+on)\s+optimization",  # Direct commands
                    r"\b(enable|turn\s+on)\s+optimization\s+(suggestions?|features?)\b",  # With "suggestions"  # noqa: E501
                ]

                # Check for disable commands (but not questions)
                is_disable_command = False
                for pattern in disable_patterns:
                    if re.search(pattern, recent_user_message, re.IGNORECASE):
                        # Additional check: exclude questions
                        if not re.search(
                            r"^(how|can|what|why|when|where)\b", recent_user_message, re.IGNORECASE
                        ):
                            is_disable_command = True
                            break

                # Check for enable commands (but not questions)
                is_enable_command = False
                for pattern in enable_patterns:
                    if re.search(pattern, recent_user_message, re.IGNORECASE):
                        # Additional check: exclude questions
                        if not re.search(
                            r"^(how|can|what|why|when|where)\b", recent_user_message, re.IGNORECASE
                        ):
                            is_enable_command = True
                            break

                if is_disable_command:
                    result = configure_proactive_optimization(session_state, enabled=False)
                    if result.get("status") == "success":
                        if "__preprocessed_context_for_llm" not in session_state:
                            session_state["__preprocessed_context_for_llm"] = {}
                        session_state["__preprocessed_context_for_llm"][
                            "optimization_config_change"
                        ] = (
                            "✅ Proactive optimization suggestions have been disabled. "
                            "You can re-enable them by saying 'enable optimization suggestions'."
                        )

                elif is_enable_command:
                    result = configure_proactive_optimization(session_state, enabled=True)
                    if result.get("status") == "success":
                        if "__preprocessed_context_for_llm" not in session_state:
                            session_state["__preprocessed_context_for_llm"] = {}
                        session_state["__preprocessed_context_for_llm"][
                            "optimization_config_change"
                        ] = (
                            "✅ Proactive optimization suggestions have been enabled. "
                            "I'll analyze your code files when you edit them "
                            "and suggest improvements."
                        )

        except Exception as e:
            logger.error(f"Error in optimization configuration handling: {e}")
