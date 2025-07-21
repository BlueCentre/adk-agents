"""Project context loading for the Software Engineer Agent."""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def load_project_context(callback_context) -> Optional[dict[str, Any]]:
    """
    Load project context information before agent execution.

    Args:
        callback_context: The ADK callback context

    Returns:
        None - context loading completed without adding extra event content
    """
    try:
        # Get current working directory
        current_dir = Path.cwd()

        # Log project information without returning it in the event
        logger.info("Project context loaded:")
        logger.info(f"  Working directory: {current_dir}")
        logger.info(f"  Project name: {Path(current_dir).name}")

        # Detect project type
        project_files = (
            [str(p.name) for p in Path(current_dir).iterdir()] if Path(current_dir).exists() else []
        )
        if "pyproject.toml" in project_files:
            project_type = "python"
        elif "package.json" in project_files:
            project_type = "javascript"
        elif "Cargo.toml" in project_files:
            project_type = "rust"
        elif "go.mod" in project_files:
            project_type = "go"
        else:
            project_type = "unknown"

        logger.info(f"  Project type: {project_type}")
        logger.info(f"  Files found: {project_files[:10]}...")  # Log first 10 files

        # Store context information in the callback context for tools to use
        if hasattr(callback_context, "user_data"):
            callback_context.user_data["project_context"] = {
                "working_directory": current_dir,
                "project_name": Path(current_dir).name,
                "project_type": project_type,
                "files_found": project_files,
            }

        # Return None to avoid validation errors with Event content
        return None

    except Exception as e:
        logger.error(f"Error loading project context: {e}")
        return None


def memorize_context(key: str, value: str, context: dict):
    """
    Store information in the project context.

    Args:
        key: The key to store the value under.
        value: The value to store.
        context: The context dictionary to update.

    Returns:
        A status message.
    """
    context[key] = value
    return {"status": f'Stored "{key}": "{value}" in project context'}
