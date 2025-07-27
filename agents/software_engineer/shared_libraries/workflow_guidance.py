"""Workflow Guidance and Next Step Suggestion System.

This module implements Milestone 2.3: Workflow Guidance and Next Step Suggestions
by anticipating logical next steps in common development workflows and offering guidance.
"""

from enum import Enum
import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enumeration of action types for workflow guidance."""

    EDIT_FILE = "edit_file"
    CREATE_FEATURE = "create_feature"


class WorkflowGuidance:
    """Anticipates and suggests next steps in development workflows."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the workflow guidance system.

        Args:
            config_path: Path to the workflow patterns configuration file.
                        If None, uses the default config file in the same directory.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "workflow_patterns.yaml"

        self.workflow_patterns = self._load_workflow_patterns(config_path)

    def _load_workflow_patterns(self, config_path: Path) -> dict:
        """Load workflow patterns from the configuration file.

        Args:
            config_path: Path to the configuration file.

        Returns:
            Dictionary containing workflow patterns.
        """
        try:
            with config_path.open(encoding="utf-8") as file:
                patterns = yaml.safe_load(file)
                return patterns or {}
        except FileNotFoundError:
            logger.warning(f"Workflow patterns config file not found: {config_path}")
            return self._get_default_patterns()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing workflow patterns config: {e}")
            return self._get_default_patterns()

    def _get_default_patterns(self) -> dict:
        """Get default workflow patterns as fallback.

        Returns:
            Dictionary containing default workflow patterns.
        """
        return {
            "code_change": {
                "next_step": "run_tests",
                "suggestion": (
                    "It looks like you've modified a file. Would you like to run the tests?"
                ),
            },
            "new_feature": {
                "next_step": "create_documentation",
                "suggestion": (
                    "You've created a new feature. Would you like to create documentation for it?"
                ),
            },
        }

    def suggest_next_step(self, session_state: dict) -> Optional[dict]:
        """
        Suggest the next logical action based on the current state.

        Args:
            session_state: Current session state.

        Returns:
            A dictionary with the suggestion, or None if no suggestion.
        """
        if not session_state or not session_state.get("proactive_suggestions_enabled", True):
            return None

        last_action = session_state.get("last_action")
        if not last_action:
            return None

        if last_action == ActionType.EDIT_FILE.value:
            return self.workflow_patterns.get("code_change")
        if last_action == ActionType.CREATE_FEATURE.value:
            return self.workflow_patterns.get("new_feature")

        return None

    def format_suggestion(self, suggestion: dict) -> str:
        """
        Format the suggestion for display to the user.

        Args:
            suggestion: The suggestion to format.

        Returns:
            A formatted string.
        """
        return f"💡 **Next Step Suggestion:** {suggestion['suggestion']}"


_workflow_guidance = WorkflowGuidance()


def suggest_next_step(session_state: Optional[dict]) -> Optional[str]:
    """
    Suggest the next logical action based on the current state.

    Args:
        session_state: Current session state.

    Returns:
        A formatted string with the suggestion, or None if no suggestion.
    """
    suggestion = _workflow_guidance.suggest_next_step(session_state)
    if suggestion:
        return _workflow_guidance.format_suggestion(suggestion)
    return None
