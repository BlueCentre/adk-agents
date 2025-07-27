"""Workflow Guidance and Next Step Suggestion System.

This module implements Milestone 2.3: Workflow Guidance and Next Step Suggestions
by anticipating logical next steps in common development workflows and offering guidance.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class WorkflowGuidance:
    """Anticipates and suggests next steps in development workflows."""

    def __init__(self):
        """Initialize the workflow guidance system."""
        self.workflow_patterns = {
            "code_change": {
                "next_step": "run_tests",
                "suggestion": "It looks like you've modified a file. Would you like to run the tests?",
            },
            "new_feature": {
                "next_step": "create_documentation",
                "suggestion": "You've created a new feature. Would you like to create documentation for it?",
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
        if not session_state.get("proactive_suggestions_enabled", True):
            return None

        last_action = session_state.get("last_action")
        if not last_action:
            return None

        if last_action == "edit_file":
            return self.workflow_patterns.get("code_change")
        elif last_action == "create_feature":
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

def suggest_next_step(session_state: dict) -> Optional[str]:
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
