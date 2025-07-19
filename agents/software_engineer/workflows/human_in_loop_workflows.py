"""Human-in-the-loop workflow patterns for the Software Engineer Agent."""

import asyncio
import logging
from typing import Any, Dict

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool, ToolContext

from .. import config as agent_config
from ..sub_agents.code_quality.agent import code_quality_agent
from ..sub_agents.code_review.agent import code_review_agent
from ..sub_agents.testing.agent import testing_agent

logger = logging.getLogger(__name__)


def human_approval_tool(
    request_type: str,
    details: str,
    context: str = "",
    severity: str = "medium",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """
    Tool that requests human approval for various software engineering tasks.

    This is a conceptual implementation - in practice, this would integrate with
    external systems like Slack, email, or web interfaces for human interaction.

    Args:
        request_type: Type of approval needed (e.g., "code_deployment", "major_refactor")
        details: Detailed description of what needs approval
        context: Additional context about the request
        severity: Severity level (low, medium, high, critical)
        tool_context: ADK tool context

    Returns:
        Dict containing approval status and feedback
    """

    # In a real implementation, this would:
    # 1. Send notification to human reviewers (Slack, email, etc.)
    # 2. Present details in a user-friendly interface
    # 3. Wait for human response
    # 4. Return the decision and feedback

    logger.info(f"Human approval requested for {request_type}: {details}")

    # For demonstration, we'll simulate different approval scenarios
    # In practice, this would wait for actual human input

    if tool_context and tool_context.state:
        # Store approval request in session state
        approval_requests = tool_context.state.get("approval_requests", [])
        approval_requests.append(
            {
                "request_type": request_type,
                "details": details,
                "context": context,
                "severity": severity,
                "status": "pending",
                "timestamp": "2024-01-01T00:00:00Z",  # In practice, use actual timestamp
            }
        )
        tool_context.state["approval_requests"] = approval_requests

        # Check if there's already a response (simulating human response)
        existing_response = tool_context.state.get("human_response")
        if existing_response:
            return {
                "status": "approved" if existing_response.get("approved", False) else "rejected",
                "feedback": existing_response.get("feedback", ""),
                "reviewer": existing_response.get("reviewer", "human_reviewer"),
                "timestamp": existing_response.get("timestamp", "2024-01-01T00:00:00Z"),
            }

    # Simulate approval based on severity and type
    if severity == "low":
        return {
            "status": "approved",
            "feedback": "Approved automatically for low severity changes",
            "reviewer": "automated_approval",
            "timestamp": "2024-01-01T00:00:00Z",
        }
    return {
        "status": "pending",
        "feedback": "Human approval required - request sent to reviewers",
        "reviewer": "pending",
        "timestamp": "2024-01-01T00:00:00Z",
        "message": f"Please review and approve: {request_type} - {details}",
    }


def human_feedback_tool(
    feedback_type: str, request: str, context: str = "", tool_context: ToolContext = None
) -> dict[str, Any]:
    """
    Tool that requests human feedback on various software engineering decisions.

    Args:
        feedback_type: Type of feedback needed (e.g., "architecture_review", "code_style")
        request: Specific feedback request
        context: Additional context
        tool_context: ADK tool context

    Returns:
        Dict containing feedback and suggestions
    """

    logger.info(f"Human feedback requested for {feedback_type}: {request}")

    # In practice, this would integrate with collaboration tools
    # For demonstration, we'll provide simulated feedback

    if tool_context and tool_context.state:
        # Store feedback request in session state
        feedback_requests = tool_context.state.get("feedback_requests", [])
        feedback_requests.append(
            {
                "feedback_type": feedback_type,
                "request": request,
                "context": context,
                "status": "pending",
                "timestamp": "2024-01-01T00:00:00Z",
            }
        )
        tool_context.state["feedback_requests"] = feedback_requests

    # Simulate human feedback
    return {
        "status": "received",
        "feedback": f"Human feedback for {feedback_type}: Please consider best practices and team conventions",
        "suggestions": [
            "Review code style guidelines",
            "Consider performance implications",
            "Ensure adequate test coverage",
        ],
        "reviewer": "senior_developer",
        "timestamp": "2024-01-01T00:00:00Z",
    }


# Create tool instances
human_approval_function_tool = FunctionTool(human_approval_tool)
human_feedback_function_tool = FunctionTool(human_feedback_tool)


def create_approval_workflow() -> SequentialAgent:
    """
    Creates a human-in-the-loop approval workflow for critical changes.

    This implements the ADK Human-in-the-Loop Pattern for:
    1. Code changes requiring approval
    2. Architecture decisions
    3. Production deployments
    4. Security-related changes
    """

    # Create approval preparation agent
    approval_prep_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="approval_preparation_agent",
        description="Prepares requests for human approval",
        instruction="""
        You prepare requests for human approval.

        Your tasks:
        1. Analyze the change/decision requiring approval
        2. Gather relevant context and impact analysis
        3. Prepare clear, concise approval requests
        4. Use human_approval_tool to request approval
        5. Store approval context in session.state['approval_context']
        """,
        tools=[human_approval_function_tool],
        output_key="approval_context",
    )

    # Create approval processing agent
    approval_processor = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="approval_processor",
        description="Processes human approval responses",
        instruction="""
        You process human approval responses.

        Your tasks:
        1. Check approval status from session.state
        2. Process feedback from human reviewers
        3. Determine next steps based on approval/rejection
        4. Store processing results in session.state['approval_result']
        """,
        output_key="approval_result",
    )

    # Create approval workflow
    return SequentialAgent(
        name="human_approval_workflow",
        description="Manages human approval for critical changes",
        sub_agents=[
            approval_prep_agent,  # Prepare approval request
            approval_processor,  # Process approval response
        ],
    )


def create_collaborative_review_workflow() -> SequentialAgent:
    """
    Creates a collaborative review workflow that includes human feedback.

    This combines automated analysis with human review:
    1. Automated analysis → 2. Human review → 3. Incorporate feedback → 4. Finalize
    """

    # Create human review coordinator
    human_review_coordinator = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="human_review_coordinator",
        description="Coordinates human review process",
        instruction="""
        You coordinate the human review process.

        Your tasks:
        1. Gather automated analysis results
        2. Prepare human-readable review summaries
        3. Use human_feedback_tool to request human review
        4. Coordinate between automated and human feedback
        5. Store coordination results in session.state['review_coordination']
        """,
        tools=[human_feedback_function_tool],
        output_key="review_coordination",
    )

    # Create feedback integrator
    feedback_integrator = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="feedback_integrator",
        description="Integrates human and automated feedback",
        instruction="""
        You integrate human and automated feedback.

        Your tasks:
        1. Collect automated analysis results
        2. Collect human feedback and suggestions
        3. Reconcile conflicts between automated and human feedback
        4. Prioritize actions based on combined feedback
        5. Store integrated feedback in session.state['integrated_feedback']
        """,
        output_key="integrated_feedback",
    )

    # Create collaborative review workflow
    return SequentialAgent(
        name="collaborative_review_workflow",
        description="Combines automated analysis with human review",
        sub_agents=[
            code_review_agent,  # Automated code review
            code_quality_agent,  # Automated quality analysis
            testing_agent,  # Automated testing analysis
            human_review_coordinator,  # Request human review
            feedback_integrator,  # Integrate all feedback
        ],
    )


def create_architecture_decision_workflow() -> SequentialAgent:
    """
    Creates a workflow for architecture decisions that require human input.

    This ensures important architectural decisions get human oversight:
    1. Analyze → 2. Propose → 3. Human review → 4. Finalize → 5. Document
    """

    # Create architecture proposal agent
    architecture_proposer = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="architecture_proposer",
        description="Proposes architecture solutions",
        instruction="""
        You propose architecture solutions.

        Your tasks:
        1. Analyze architecture requirements
        2. Research and propose solutions
        3. Consider trade-offs and alternatives
        4. Prepare detailed architecture proposals
        5. Store proposals in session.state['architecture_proposal']
        """,
        output_key="architecture_proposal",
    )

    # Create architecture review coordinator
    architecture_review_coordinator = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="architecture_review_coordinator",
        description="Coordinates architecture review with humans",
        instruction="""
        You coordinate architecture review with human experts.

        Your tasks:
        1. Prepare architecture review materials
        2. Use human_feedback_tool to request expert review
        3. Facilitate discussion of alternatives
        4. Coordinate decision-making process
        5. Store review results in session.state['architecture_review']
        """,
        tools=[human_feedback_function_tool],
        output_key="architecture_review",
    )

    # Create architecture finalizer
    architecture_finalizer = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="architecture_finalizer",
        description="Finalizes architecture decisions",
        instruction="""
        You finalize architecture decisions.

        Your tasks:
        1. Incorporate human feedback into architecture
        2. Resolve any remaining issues or concerns
        3. Finalize architecture documentation
        4. Plan implementation approach
        5. Store final architecture in session.state['final_architecture']
        """,
        output_key="final_architecture",
    )

    # Create architecture decision workflow
    return SequentialAgent(
        name="architecture_decision_workflow",
        description="Manages architecture decisions with human oversight",
        sub_agents=[
            architecture_proposer,  # Propose architecture
            architecture_review_coordinator,  # Human review
            architecture_finalizer,  # Finalize decision
        ],
    )


def create_deployment_approval_workflow() -> SequentialAgent:
    """
    Creates a deployment approval workflow with human oversight.

    This ensures deployments get proper approval:
    1. Pre-deployment checks → 2. Human approval → 3. Deployment → 4. Post-deployment verification
    """

    # Create deployment preparation agent
    deployment_prep_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="deployment_preparation_agent",
        description="Prepares deployment for approval",
        instruction="""
        You prepare deployment for human approval.

        Your tasks:
        1. Run pre-deployment checks
        2. Prepare deployment summary
        3. Assess deployment risks
        4. Use human_approval_tool to request deployment approval
        5. Store preparation results in session.state['deployment_prep']
        """,
        tools=[human_approval_function_tool],
        output_key="deployment_prep",
    )

    # Create deployment executor
    deployment_executor = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="deployment_executor",
        description="Executes deployment after approval",
        instruction="""
        You execute deployment after human approval.

        Your tasks:
        1. Verify approval was granted
        2. Execute deployment steps
        3. Monitor deployment progress
        4. Handle any deployment issues
        5. Store execution results in session.state['deployment_execution']
        """,
        output_key="deployment_execution",
    )

    # Create deployment verification agent
    deployment_verifier = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="deployment_verifier",
        description="Verifies deployment success",
        instruction="""
        You verify deployment success.

        Your tasks:
        1. Run post-deployment verification
        2. Check system health and functionality
        3. Validate deployment objectives were met
        4. Report deployment status to stakeholders
        5. Store verification results in session.state['deployment_verification']
        """,
        output_key="deployment_verification",
    )

    # Create deployment approval workflow
    return SequentialAgent(
        name="deployment_approval_workflow",
        description="Manages deployment with human approval",
        sub_agents=[
            deployment_prep_agent,  # Prepare for deployment
            deployment_executor,  # Execute deployment
            deployment_verifier,  # Verify deployment
        ],
    )
