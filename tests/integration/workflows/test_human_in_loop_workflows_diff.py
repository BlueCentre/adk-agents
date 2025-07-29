import unittest

from agents.software_engineer.workflows.human_in_loop_workflows import (
    _present_file_edit_proposal,
    generate_diff_for_proposal,
)


class TestHumanInTheLoopWorkflowsDiff(unittest.TestCase):
    def test_file_edit_proposal_with_diff(self):
        # Arrange
        old_content = "Hello, world!"
        new_content = "Hello, beautiful world!"
        proposal = {
            "type": "file_edit",
            "proposed_filepath": "hello.txt",
            "old_content": old_content,
            "proposed_content": new_content,
        }

        # Act
        proposal_with_diff = generate_diff_for_proposal(proposal)
        presentation = _present_file_edit_proposal(proposal_with_diff)

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
