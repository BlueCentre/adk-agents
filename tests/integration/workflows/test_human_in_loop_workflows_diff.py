import unittest
from unittest.mock import MagicMock

from agents.software_engineer.workflows.human_in_loop_workflows import (
    _present_file_edit_proposal,
    human_in_the_loop_approval,
)


class TestHumanInTheLoopWorkflowsDiff(unittest.TestCase):
    def test_file_edit_proposal_with_diff(self):
        # Arrange
        tool_context = MagicMock()
        tool_context.state = {}
        old_content = "Hello, world!"
        new_content = "Hello, beautiful world!"
        proposal = {
            "type": "file_edit",
            "proposed_filepath": "hello.txt",
            "old_content": old_content,
            "proposed_content": new_content,
        }
        user_input_handler = MagicMock(return_value="yes")
        display_handler = MagicMock()

        # Act
        human_in_the_loop_approval(tool_context, proposal, user_input_handler, display_handler)
        presentation = _present_file_edit_proposal(proposal)

        # Assert
        self.assertIn("```diff", presentation)
        self.assertIn("-Hello, world!", presentation)
        self.assertIn("+Hello, beautiful world!", presentation)

    def test_file_edit_proposal_without_diff(self):
        # Arrange
        proposal = {
            "type": "file_edit",
            "proposed_filepath": "hello.txt",
            "proposed_content": "Hello, world!",
        }

        # Act
        presentation = _present_file_edit_proposal(proposal)

        # Assert
        self.assertNotIn("```diff", presentation)
        self.assertIn("```", presentation)


if __name__ == "__main__":
    unittest.main()
