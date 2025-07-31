"""Code improver agent for iterative code refinement workflows."""

from collections.abc import AsyncGenerator
import logging

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from ... import config as agent_config

logger = logging.getLogger(__name__)


class CodeImprover(LlmAgent):
    """Agent that improves code based on feedback from quality checks."""

    def __init__(self, name: str = "code_improver"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Improves code based on quality feedback",
            instruction="Improve code based on quality feedback",
            output_key="code_improver",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Improve code based on previous iteration feedback."""

        # Get feedback from previous iteration
        code_quality_issues = ctx.session.state.get("code_quality", {}).get("issues", [])
        code_review_issues = ctx.session.state.get("code_review", {}).get("issues", [])
        testing_issues = ctx.session.state.get("testing", {}).get("issues", [])

        # Aggregate improvement suggestions
        improvements = []

        # Process quality issues
        for issue in code_quality_issues[:3]:  # Top 3 issues
            improvements.append(
                {
                    "type": "quality",
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                    "suggestion": issue.get("suggestion", ""),
                }
            )

        # Process review issues
        for issue in code_review_issues[:3]:  # Top 3 issues
            improvements.append(
                {
                    "type": "review",
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                    "suggestion": issue.get("suggestion", ""),
                }
            )

        # Process testing issues
        for issue in testing_issues[:3]:  # Top 3 issues
            improvements.append(
                {
                    "type": "testing",
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                    "suggestion": issue.get("suggestion", ""),
                }
            )

        # Store improvement plan
        ctx.session.state["improvement_plan"] = {
            "improvements": improvements,
            "total_improvements": len(improvements),
            "iteration": ctx.session.state.get("iteration_state", {}).get("current_iteration", 0),
        }

        # Generate improvement event
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=f"Code improvement plan created with {len(improvements)} improvements"
                    )
                ]
            ),
            actions=EventActions(),
        )
