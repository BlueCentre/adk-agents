from collections.abc import AsyncGenerator
import logging
import time
from typing import Any, Callable, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext
from google.genai import types as genai_types

from .. import config as agent_config
from ..shared_libraries.diff_utils import generate_unified_diff

logger = logging.getLogger(__name__)


class HumanApprovalWorkflow(LlmAgent):
    """
    A general purpose workflow agent for handling human approval of diverse action types.

    This workflow can handle various types of proposals including:
    - File edits and code changes
    - Deployment plans
    - Architecture decisions
    - Multi-step plans
    - Security-critical operations
    """

    def __init__(self, name: str = "human_approval_workflow"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Handles human approval workflow for critical actions",
            instruction="""
            You are a Human Approval Workflow agent. Your role is to:

            1. Parse and understand the proposed action from the context
            2. Generate a clear, comprehensive presentation of the proposal
            3. Identify potential risks and impacts
            4. Present the proposal to the user for approval
            5. Handle the approval/rejection response
            6. Update audit trails and proceed accordingly

            For different proposal types, adapt your presentation:
            - Code changes: Show diffs, affected files, potential impacts
            - Deployment plans: Show deployment steps, environments, rollback plans
            - Architecture decisions: Show design changes, trade-offs, dependencies
            - Security operations: Highlight security implications and access changes

            Always be thorough but concise. Present information in a user-friendly format.
            """,
            output_key="approval_workflow",
        )

    async def run(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
        """Execute the human approval workflow."""
        logger.info("Starting Human Approval Workflow")

        # Extract proposal from context
        proposal = context.state.get("pending_proposal", {})
        if not proposal:
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text="No proposal found in context for approval")]
                ),
                actions=EventActions(),
            )
            return

        # Generate standardized presentation
        presentation = self._generate_proposal_presentation(proposal)

        # Present to user and get approval
        approved = self._handle_user_approval(context, proposal, presentation)

        # Update state and audit trail
        self._update_approval_state(context, proposal, approved)

        # Yield result
        approval_status = "approved" if approved else "rejected"
        proposal_type = proposal.get("type", "unknown")
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=f"Approval workflow completed: {approval_status} "
                        f"({proposal_type} proposal)"
                    )
                ]
            ),
            actions=EventActions(),
        )

    def _generate_proposal_presentation(self, proposal: dict[str, Any]) -> str:
        """Generate a standardized presentation for the proposal."""
        return generate_proposal_presentation(proposal)

    def _handle_user_approval(
        self, context: InvocationContext, proposal: dict[str, Any], presentation: str
    ) -> bool:
        """Handle the user approval process using the generic approval function."""

        # Use default display and input handlers if not provided
        def default_display_handler(message: str) -> None:
            print(message)

        def default_input_handler(prompt: str) -> str:
            return input(prompt)

        # Get custom handlers from proposal if available
        display_handler = proposal.get("display_handler", default_display_handler)
        input_handler = proposal.get("user_input_handler", default_input_handler)

        # Display the formatted presentation
        display_handler(presentation)

        # Create a formatted proposal for the approval function
        formatted_proposal = {
            "message": f"Please review the {proposal.get('type', 'action')} proposal above.",
            "proposal_type": proposal.get("type", "unknown"),
            "presentation": presentation,
        }

        # Use the generic approval function that works with any state dictionary
        return approve_proposal_with_user_input(
            state_dict=context.state,
            proposal=formatted_proposal,
            user_input_handler=input_handler,
            display_handler=display_handler,
        )

    def _update_approval_state(
        self, context: InvocationContext, proposal: dict[str, Any], approved: bool
    ) -> None:
        """Update the approval state and workflow context."""
        # Update workflow state
        context.state["last_approval_outcome"] = "approved" if approved else "rejected"
        context.state["last_proposal_type"] = proposal.get("type", "unknown")

        # Clear the pending proposal
        if "pending_proposal" in context.state:
            del context.state["pending_proposal"]

        # Set next action based on approval
        if approved:
            context.state["approved_action"] = proposal
            context.state["workflow_next_step"] = "execute_approved_action"
        else:
            context.state["workflow_next_step"] = "handle_rejection"

        logger.info(f"Approval workflow completed: {'Approved' if approved else 'Rejected'}")


def _present_architecture_proposal(proposal: dict[str, Any]) -> str:
    """Present an architecture change proposal."""
    presentation = ["# 🏗️ Architecture Change Proposal", ""]

    if "change_description" in proposal:
        presentation.extend(["**Proposed Change:**", proposal["change_description"], ""])

    if "affected_components" in proposal:
        presentation.extend(["**Affected Components:**", ""])
        for component in proposal["affected_components"]:
            presentation.append(f"- {component}")
        presentation.append("")

    if "trade_offs" in proposal:
        presentation.extend(["**Trade-offs:**", proposal["trade_offs"], ""])

    return "\n".join(presentation)


def _present_deployment_proposal(proposal: dict[str, Any]) -> str:
    """Present a deployment proposal with steps and rollback plan."""
    presentation = ["# 🚀 Deployment Proposal", ""]

    if "environment" in proposal:
        presentation.extend([f"**Target Environment:** {proposal['environment']}", ""])

    if "deployment_steps" in proposal:
        presentation.extend(["**Deployment Steps:**", ""])
        for i, step in enumerate(proposal["deployment_steps"], 1):
            presentation.append(f"{i}. {step}")
        presentation.append("")

    if "rollback_plan" in proposal:
        presentation.extend(["**Rollback Plan:**", proposal["rollback_plan"], ""])

    if "risks" in proposal:
        presentation.extend(["**⚠️ Identified Risks:**", ""])
        for risk in proposal["risks"]:
            presentation.append(f"- {risk}")
        presentation.append("")

    return "\n".join(presentation)


def _present_file_edit_proposal(proposal: dict[str, Any]) -> str:
    """Present a file edit proposal with diff and impact analysis."""
    presentation = ["# 📝 File Edit Proposal", ""]

    if "proposed_filepath" in proposal:
        presentation.extend([f"**File:** `{proposal['proposed_filepath']}`", ""])

    if "diff" in proposal:
        presentation.extend(["**Proposed Changes:**", "```diff", proposal["diff"], "```", ""])
    elif "proposed_content" in proposal:
        presentation.extend(
            [
                "**New Content:**",
                "```",
                proposal["proposed_content"][:500]
                + ("..." if len(proposal["proposed_content"]) > 500 else ""),
                "```",
                "",
            ]
        )

    if "impact_analysis" in proposal:
        presentation.extend(["**Impact Analysis:**", proposal["impact_analysis"], ""])

    return "\n".join(presentation)


def _present_generic_proposal(proposal: dict[str, Any]) -> str:
    """Present a generic proposal format."""
    presentation = ["# 📄 Action Proposal", ""]

    if "title" in proposal:
        presentation.extend([f"**Title:** {proposal['title']}", ""])

    if "description" in proposal:
        presentation.extend(["**Description:**", proposal["description"], ""])

    if "details" in proposal:
        presentation.extend(["**Details:**", proposal["details"], ""])

    return "\n".join(presentation)


def _present_multi_step_proposal(proposal: dict[str, Any]) -> str:
    """Present a multi-step plan proposal."""
    presentation = ["# 📋 Multi-Step Plan Proposal", ""]

    if "plan_description" in proposal:
        presentation.extend(["**Plan Overview:**", proposal["plan_description"], ""])

    if "steps" in proposal:
        presentation.extend(["**Execution Steps:**", ""])
        for i, step in enumerate(proposal["steps"], 1):
            presentation.append(f"{i}. {step}")
        presentation.append("")

    if "estimated_duration" in proposal:
        presentation.extend([f"**Estimated Duration:** {proposal['estimated_duration']}", ""])

    return "\n".join(presentation)


def _present_security_proposal(proposal: dict[str, Any]) -> str:
    """Present a security operation proposal."""
    presentation = ["# 🔒 Security Operation Proposal", ""]

    if "operation_type" in proposal:
        presentation.extend([f"**Operation Type:** {proposal['operation_type']}", ""])

    if "security_implications" in proposal:
        presentation.extend(
            ["**🚨 Security Implications:**", proposal["security_implications"], ""]
        )

    if "access_changes" in proposal:
        presentation.extend(["**Access Changes:**", ""])
        for change in proposal["access_changes"]:
            presentation.append(f"- {change}")
        presentation.append("")

    return "\n".join(presentation)


def approve_proposal_with_user_input(
    state_dict: dict[str, Any],
    proposal: dict[str, Any],
    user_input_handler: Callable[[str], str],
    display_handler: Callable[[str], None],
) -> bool:
    """
    Generic approval function that works with any state dictionary.

    This function presents a proposal to the user, asks for their approval,
    and records the outcome in the provided state dictionary.

    Args:
        state_dict: Dictionary for storing state (can be from ToolContext or InvocationContext)
        proposal: Dictionary containing the details of the proposed action
        user_input_handler: Function to get user input
        display_handler: Function to display messages to user

    Returns:
        bool: True if approved, False if rejected
    """
    logger.info(f"Initiating approval workflow for proposal: {proposal}")

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
    audit_log = state_dict.get("approval_audit_trail", [])
    audit_entry = {
        "timestamp": time.time(),
        "proposal": proposal,
        "outcome": "approved" if approved else "rejected",
    }
    audit_log.append(audit_entry)
    state_dict["approval_audit_trail"] = audit_log

    logger.info(f"Approval workflow completed. Outcome: {'Approved' if approved else 'Rejected'}")

    return approved


def create_file_edit_proposal(
    filepath: str,
    content: str,
    diff: Optional[str] = None,
    impact_analysis: Optional[str] = None,
    display_handler: Optional[Callable[[str], None]] = None,
    user_input_handler: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """
    Create a standardized file edit proposal.

    Args:
        filepath: Path to the file being edited
        content: New content for the file
        diff: Optional diff showing changes
        impact_analysis: Optional analysis of the impact
        display_handler: Optional custom display handler
        user_input_handler: Optional custom input handler

    Returns:
        dict: Standardized proposal dictionary
    """
    proposal = {
        "type": "file_edit",
        "proposed_filepath": filepath,
        "proposed_content": content,
    }

    if diff:
        proposal["diff"] = diff
    if impact_analysis:
        proposal["impact_analysis"] = impact_analysis
    if display_handler:
        proposal["display_handler"] = display_handler
    if user_input_handler:
        proposal["user_input_handler"] = user_input_handler

    return proposal


def create_deployment_proposal(
    environment: str,
    deployment_steps: list[str],
    rollback_plan: Optional[str] = None,
    risks: Optional[list[str]] = None,
    display_handler: Optional[Callable[[str], None]] = None,
    user_input_handler: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """
    Create a standardized deployment proposal.

    Args:
        environment: Target deployment environment
        deployment_steps: List of deployment steps
        rollback_plan: Optional rollback plan description
        risks: Optional list of identified risks
        display_handler: Optional custom display handler
        user_input_handler: Optional custom input handler

    Returns:
        dict: Standardized proposal dictionary
    """
    proposal = {
        "type": "deployment",
        "environment": environment,
        "deployment_steps": deployment_steps,
    }

    if rollback_plan:
        proposal["rollback_plan"] = rollback_plan
    if risks:
        proposal["risks"] = risks
    if display_handler:
        proposal["display_handler"] = display_handler
    if user_input_handler:
        proposal["user_input_handler"] = user_input_handler

    return proposal


def create_architecture_proposal(
    change_description: str,
    affected_components: Optional[list[str]] = None,
    trade_offs: Optional[str] = None,
    display_handler: Optional[Callable[[str], None]] = None,
    user_input_handler: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """
    Create a standardized architecture change proposal.

    Args:
        change_description: Description of the proposed change
        affected_components: Optional list of affected components
        trade_offs: Optional description of trade-offs
        display_handler: Optional custom display handler
        user_input_handler: Optional custom input handler

    Returns:
        dict: Standardized proposal dictionary
    """
    proposal = {
        "type": "architecture_change",
        "change_description": change_description,
    }

    if affected_components:
        proposal["affected_components"] = affected_components
    if trade_offs:
        proposal["trade_offs"] = trade_offs
    if display_handler:
        proposal["display_handler"] = display_handler
    if user_input_handler:
        proposal["user_input_handler"] = user_input_handler

    return proposal


def create_security_proposal(
    operation_type: str,
    security_implications: str,
    access_changes: Optional[list[str]] = None,
    display_handler: Optional[Callable[[str], None]] = None,
    user_input_handler: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """
    Create a standardized security operation proposal.

    Args:
        operation_type: Type of security operation
        security_implications: Description of security implications
        access_changes: Optional list of access changes
        display_handler: Optional custom display handler
        user_input_handler: Optional custom input handler

    Returns:
        dict: Standardized proposal dictionary
    """
    proposal = {
        "type": "security_operation",
        "operation_type": operation_type,
        "security_implications": security_implications,
    }

    if access_changes:
        proposal["access_changes"] = access_changes
    if display_handler:
        proposal["display_handler"] = display_handler
    if user_input_handler:
        proposal["user_input_handler"] = user_input_handler

    return proposal


def create_multi_step_proposal(
    plan_description: str,
    steps: list[str],
    estimated_duration: Optional[str] = None,
    display_handler: Optional[Callable[[str], None]] = None,
    user_input_handler: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """
    Create a standardized multi-step plan proposal.

    Args:
        plan_description: Overview of the plan
        steps: List of execution steps
        estimated_duration: Optional estimated duration
        display_handler: Optional custom display handler
        user_input_handler: Optional custom input handler

    Returns:
        dict: Standardized proposal dictionary
    """
    proposal = {
        "type": "multi_step_plan",
        "plan_description": plan_description,
        "steps": steps,
    }

    if estimated_duration:
        proposal["estimated_duration"] = estimated_duration
    if display_handler:
        proposal["display_handler"] = display_handler
    if user_input_handler:
        proposal["user_input_handler"] = user_input_handler

    return proposal


def create_generic_proposal(
    title: str,
    description: str,
    details: Optional[str] = None,
    display_handler: Optional[Callable[[str], None]] = None,
    user_input_handler: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """
    Create a generic proposal for actions that don't fit other categories.

    Args:
        title: Title of the proposal
        description: Description of the proposed action
        details: Optional additional details
        display_handler: Optional custom display handler
        user_input_handler: Optional custom input handler

    Returns:
        dict: Standardized proposal dictionary
    """
    proposal = {
        "type": "generic",
        "title": title,
        "description": description,
    }

    if details:
        proposal["details"] = details
    if display_handler:
        proposal["display_handler"] = display_handler
    if user_input_handler:
        proposal["user_input_handler"] = user_input_handler

    return proposal


def create_human_approval_workflow() -> HumanApprovalWorkflow:
    """
    Create a human approval workflow instance.

    This function creates a configured HumanApprovalWorkflow agent that can be used
    by the workflow_selector_tool when requires_approval=True is detected.

    Returns:
        HumanApprovalWorkflow: Configured workflow instance
    """
    return HumanApprovalWorkflow(name="human_approval_workflow")


def generate_diff_for_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a diff for a file edit proposal and add it to the proposal.

    Args:
        proposal: The proposal dictionary.

    Returns:
        The proposal dictionary with the diff added.
    """
    if proposal.get("type") == "file_edit":
        old_content = proposal.get("old_content", "")
        new_content = proposal.get("proposed_content", "")
        filepath = proposal.get("proposed_filepath", "file")
        diff = generate_unified_diff(old_content, new_content, filepath, filepath)
        proposal["diff"] = diff
    return proposal


def generate_proposal_presentation(proposal: dict[str, Any]) -> str:
    """
    Generate a standardized presentation for a proposal.

    This is a stateless utility function that can be used by both workflows
    and tools to generate consistent proposal presentations.

    Args:
        proposal: Dictionary containing proposal details

    Returns:
        str: Formatted presentation string
    """
    proposal_type = proposal.get("type", "unknown")

    if proposal_type == "file_edit":
        return _present_file_edit_proposal(proposal)
    if proposal_type == "deployment":
        return _present_deployment_proposal(proposal)
    if proposal_type == "architecture_change":
        return _present_architecture_proposal(proposal)
    if proposal_type == "security_operation":
        return _present_security_proposal(proposal)
    if proposal_type == "multi_step_plan":
        return _present_multi_step_proposal(proposal)
    return _present_generic_proposal(proposal)


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
    return approve_proposal_with_user_input(
        state_dict=tool_context.state,
        proposal=proposal,
        user_input_handler=user_input_handler,
        display_handler=display_handler,
    )


def setup_approval_proposal(
    proposal_data: dict[str, Any],
    context: InvocationContext,
) -> None:
    """
    Set up a proposal in the session state for approval workflow processing.

    Args:
        proposal_data: The proposal data dictionary
        context: The invocation context to store the proposal in
    """
    context.state["pending_proposal"] = proposal_data
    context.state["workflow_state"] = "awaiting_approval"
