"""Integration tests for Milestone 2.3: Workflow Guidance and Next Step Suggestions."""

import unittest
from unittest.mock import MagicMock, patch

from agents.software_engineer.shared_libraries.workflow_guidance import suggest_next_step

class TestWorkflowGuidance(unittest.TestCase):
    """Test suite for workflow guidance and next step suggestions."""

    def test_suggest_next_step_after_code_change(self):
        """Verify that the agent suggests running tests after a code change."""
        session_state = {
            "last_action": "edit_file",
            "proactive_suggestions_enabled": True,
        }
        suggestion = suggest_next_step(session_state)
        self.assertIsNotNone(suggestion)
        self.assertIn("Would you like to run the tests?", suggestion)

    def test_suggest_next_step_after_new_feature(self):
        """Verify that the agent suggests creating documentation after a new feature."""
        session_state = {
            "last_action": "create_feature",
            "proactive_suggestions_enabled": True,
        }
        suggestion = suggest_next_step(session_state)
        self.assertIsNotNone(suggestion)
        self.assertIn("Would you like to create documentation for it?", suggestion)

    def test_no_suggestion_when_disabled(self):
        """Verify that the agent does not suggest a next step when disabled."""
        session_state = {
            "last_action": "edit_file",
            "proactive_suggestions_enabled": False,
        }
        suggestion = suggest_next_step(session_state)
        self.assertIsNone(suggestion)

    def test_no_suggestion_when_no_last_action(self):
        """Verify that the agent does not suggest a next step when there is no last action."""
        session_state = {
            "proactive_suggestions_enabled": True,
        }
        suggestion = suggest_next_step(session_state)
        self.assertIsNone(suggestion)

if __name__ == "__main__":
    unittest.main()
