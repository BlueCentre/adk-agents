import unittest

from agents.software_engineer.workflows.human_in_loop_workflows import (
    _present_file_edit_proposal,
    generate_diff_for_proposal,
)


def test_file_edit_proposal_with_diff():
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
    assert "```diff" in presentation
    assert "-Hello, world!" in presentation
    assert "+Hello, beautiful world!" in presentation


def test_file_edit_proposal_without_diff():
    # Arrange
    proposal = {
        "type": "file_edit",
        "proposed_filepath": "hello.txt",
        "proposed_content": "Hello, world!",
    }

    # Act
    presentation = _present_file_edit_proposal(proposal)

    # Assert
    assert "```diff" not in presentation
    assert "```" in presentation


if __name__ == "__main__":
    unittest.main()
