import logging
import time
from typing import Any, Callable

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def human_in_the_loop_approval(
    tool_context: ToolContext,
    proposal: dict[str, Any],
    user_input_handler: Callable[[str], str],
    display_handler: Callable[[str], None],
) -> bool:
    """
    Manages the human-in-the-loop approval workflow for a proposed action.

    This function presents a proposal to the user, asks for their approval,
    and records the outcome. It is designed to be a generic approval mechanism
    that can be used for various actions, such as file edits, command executions,
    or plan confirmations.

    Args:
        tool_context: The ADK ToolContext, providing access to session state.
        proposal: A dictionary containing the details of the proposed action.
                  Expected keys include 'proposed_filepath', 'proposed_content',
                  'message', etc.
        user_input_handler: A function that takes a prompt message (str) and
                            returns the user's input (str). This allows for
                            flexibility in how user input is captured (e.g.,
                            CLI input, UI button click).
        display_handler: A function that takes a message (str) and displays it
                         to the user. This allows for different presentation
                         formats (e.g., console print, UI message box).

    Returns:
        bool: True if the action is approved by the user, False otherwise.
    """
    logger.info(f"Initiating human approval workflow for proposal: {proposal}")

    # --- Present the proposal to the user ---
    display_handler("--- PROPOSED CHANGE ---")
    if "proposed_filepath" in proposal:
        display_handler(f"File: {proposal['proposed_filepath']}")
    if "proposed_content" in proposal:
        # For long content, consider showing a diff or a summary
        display_handler("Content:")
        display_handler(proposal["proposed_content"])
    if "message" in proposal:
        display_handler(f"Message: {proposal['message']}")
    display_handler("-----------------------")

    # --- Get user approval ---
    while True:
        response = user_input_handler("Approve this change? (yes/no): ").lower().strip()
        if response in ["yes", "y"]:
            approved = True
            break
        if response in ["no", "n"]:
            approved = False
            break
        display_handler("Invalid input. Please enter 'yes' or 'no'.")

    # --- Record the audit trail ---
    audit_log = tool_context.state.get("approval_audit_trail", [])
    audit_entry = {
        "timestamp": time.time(),
        "proposal": proposal,
        "outcome": "approved" if approved else "rejected",
    }
    audit_log.append(audit_entry)
    tool_context.state["approval_audit_trail"] = audit_log

    logger.info(f"Approval workflow completed. Outcome: {'Approved' if approved else 'Rejected'}")

    return approved
