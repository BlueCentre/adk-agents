"""Integration tests for Milestone 2.3: Workflow Guidance and Next Step Suggestions."""

from agents.software_engineer.shared_libraries.workflow_guidance import (
    ActionType,
    suggest_next_step,
)


def test_suggest_next_step_after_code_change():
    """Verify that the agent suggests running tests after a code change."""
    session_state = {
        "last_action": ActionType.EDIT_FILE.value,
        "proactive_suggestions_enabled": True,
    }
    suggestion = suggest_next_step(session_state)
    assert suggestion is not None
    assert "Would you like to run the tests?" in suggestion


def test_suggest_next_step_after_new_feature():
    """Verify that the agent suggests creating documentation after a new feature."""
    session_state = {
        "last_action": "create_feature",
        "proactive_suggestions_enabled": True,
    }
    suggestion = suggest_next_step(session_state)
    assert suggestion is not None
    assert "Would you like to create documentation for it?" in suggestion


def test_no_suggestion_when_disabled():
    """Verify that the agent does not suggest a next step when disabled."""
    session_state = {
        "last_action": ActionType.EDIT_FILE.value,
        "proactive_suggestions_enabled": False,
    }
    suggestion = suggest_next_step(session_state)
    assert suggestion is None


def test_no_suggestion_when_no_last_action():
    """Verify that the agent does not suggest a next step when there is no last action."""
    session_state = {
        "proactive_suggestions_enabled": True,
    }
    suggestion = suggest_next_step(session_state)
    assert suggestion is None
