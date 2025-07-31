"""Iterative quality checker agent for code refinement workflows."""

from collections.abc import AsyncGenerator
import logging

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from ... import config as agent_config

logger = logging.getLogger(__name__)


class IterativeQualityChecker(LlmAgent):
    """Agent that checks if quality standards are met and decides whether to continue iterating."""

    def __init__(self, name: str = "iterative_quality_checker"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Checks if quality standards are met for iterative workflows",
            instruction="Check quality standards and decide whether to continue iterating",
            output_key="quality_checker",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Check quality and decide whether to escalate (stop) or continue."""

        # Get current iteration state
        iteration_state = ctx.session.state.get("iteration_state", {})
        current_iteration = iteration_state.get("current_iteration", 0)
        max_iterations = iteration_state.get("max_iterations", 5)

        # Get quality metrics from various agents
        code_quality_result = ctx.session.state.get("code_quality", {})
        code_review_result = ctx.session.state.get("code_review", {})
        testing_result = ctx.session.state.get("testing", {})

        # Simple quality check logic (can be enhanced with more sophisticated criteria)
        quality_score = 0

        # Check code quality
        if code_quality_result.get("status") == "pass":
            quality_score += 1

        # Check code review
        if code_review_result.get("issues_count", 0) == 0:
            quality_score += 1

        # Check testing
        if testing_result.get("coverage", 0) >= 80:  # 80% coverage threshold
            quality_score += 1

        # Decision logic
        should_stop = False
        reason = ""

        if quality_score >= 2:  # At least 2 out of 3 quality checks pass
            should_stop = True
            reason = f"Quality standards met (score: {quality_score}/3)"
        elif current_iteration >= max_iterations:
            should_stop = True
            reason = f"Maximum iterations reached ({max_iterations})"
        else:
            reason = (
                f"Quality needs improvement (score: {quality_score}/3), "
                f"continuing iteration {current_iteration + 1}"
            )

        # Update iteration state
        iteration_state.update(
            {
                "current_iteration": current_iteration + 1,
                "quality_score": quality_score,
                "should_stop": should_stop,
                "reason": reason,
            }
        )
        ctx.session.state["iteration_state"] = iteration_state

        # Generate event with escalation decision
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[genai_types.Part(text=f"Quality check complete: {reason}")]
            ),
            actions=EventActions(escalate=should_stop),
        )
