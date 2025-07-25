"""Project context tool for the software engineer agent."""

import json
from pathlib import Path

from google.adk.agents.callback_context import CallbackContext

# Import agent configuration
from ..config import SOFTWARE_ENGINEER_CONTEXT

# Define constants
PROJECT_CONTEXT_KEY = "project_context"
USER_PROFILE_KEY = "user_profile"
DEFAULT_CONTEXT_PATH = SOFTWARE_ENGINEER_CONTEXT


def load_project_context(callback_context: CallbackContext):
    """
    Load the project context and user profile from a JSON file.

    Args:
        callback_context: The callback context from ADK.
    """
    # Initialize empty context
    project_context = {}
    user_profile = {}

    try:
        if Path(DEFAULT_CONTEXT_PATH).exists():
            with Path.open(DEFAULT_CONTEXT_PATH) as file:
                data = json.load(file)
                project_context = data.get("project_context", {})
                user_profile = data.get("user_profile", {})
                print(f"\nLoaded project context: {project_context}\n")
                print(f"\nLoaded user profile: {user_profile}\n")
    except Exception as e:
        print(f"Error loading project context: {e}")

    # Set the context in the state
    callback_context.state[PROJECT_CONTEXT_KEY] = json.dumps(project_context, indent=2)
    callback_context.state[USER_PROFILE_KEY] = json.dumps(user_profile, indent=2)


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
