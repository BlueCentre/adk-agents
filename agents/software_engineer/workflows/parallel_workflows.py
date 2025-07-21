"""Parallel workflow patterns for the Software Engineer Agent."""

from collections.abc import AsyncGenerator

from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from .. import config as agent_config
from ..sub_agents.code_quality.agent import code_quality_agent
from ..sub_agents.code_review.agent import code_review_agent
from ..sub_agents.design_pattern.agent import design_pattern_agent
from ..sub_agents.testing.agent import testing_agent


class StateAggregatorAgent(LlmAgent):
    """Agent that aggregates results from parallel sub-agents into shared state."""

    def __init__(self, name: str = "state_aggregator"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Aggregates results from parallel agents into shared state",
            instruction="Aggregate parallel agent results into shared state",
            output_key="state_aggregator",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Aggregate results from parallel agents."""

        # Get results from parallel agents
        code_review_result = ctx.session.state.get("code_review", {})
        code_quality_result = ctx.session.state.get("code_quality", {})
        testing_result = ctx.session.state.get("testing", {})
        design_pattern_result = ctx.session.state.get("design_pattern", {})

        # Aggregate into a comprehensive analysis
        aggregated_analysis = {
            "code_review": code_review_result,
            "code_quality": code_quality_result,
            "testing": testing_result,
            "design_patterns": design_pattern_result,
            "analysis_complete": True,
            "timestamp": ctx.session.created_at.isoformat() if ctx.session.created_at else None,
        }

        # Store in session state
        ctx.session.state["parallel_analysis"] = aggregated_analysis

        # Generate completion event
        yield Event(
            author=self.name,
            text=(
                f"Parallel analysis complete. Aggregated results from "
                f"{len([r for r in [code_review_result, code_quality_result, testing_result, design_pattern_result] if r])} agents."  # noqa: E501
            ),
            actions=EventActions(),
        )


def create_parallel_analysis_workflow() -> ParallelAgent:
    """
    Creates a parallel workflow that runs code review, quality analysis,
    testing analysis, and design pattern analysis concurrently.

    This implements the ADK Parallel Fan-Out/Gather Pattern.
    """

    # Create state aggregator
    aggregator = StateAggregatorAgent()

    # Create parallel workflow
    return ParallelAgent(
        name="parallel_analysis_workflow",
        description="Runs code analysis tasks in parallel for faster feedback",
        sub_agents=[
            code_review_agent,  # Analyzes code for issues
            code_quality_agent,  # Runs static analysis
            testing_agent,  # Analyzes test coverage and strategy
            design_pattern_agent,  # Reviews architectural patterns
            aggregator,  # Aggregates results
        ],
    )


def create_parallel_implementation_workflow() -> ParallelAgent:
    """
    Creates a parallel workflow for implementation tasks that can run independently.

    This is useful for tasks like:
    - Writing tests while implementing features
    - Generating documentation while coding
    - Setting up CI/CD while developing
    """

    # Create specialized agents for parallel implementation
    parallel_implementation_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="parallel_implementation_agent",
        description="Coordinates parallel implementation tasks",
        instruction="""
        You coordinate parallel implementation tasks. Your role is to:
        1. Analyze the requirements and break them into parallel tasks
        2. Ensure each task has the necessary context from session state
        3. Coordinate between parallel agents to avoid conflicts
        4. Aggregate results and ensure consistency

        Use session.state to share context between parallel tasks.
        """,
        output_key="parallel_implementation",
    )

    # Create a separate testing agent instance for this workflow
    parallel_testing_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="parallel_testing_agent",
        description="Testing agent for parallel implementation workflow",
        instruction="""
        You are a testing agent specialized in writing tests during parallel implementation.

        Your tasks:
        1. Write unit tests for implemented features
        2. Create integration tests for component interactions
        3. Generate test data and fixtures as needed
        4. Validate test coverage and quality

        Work in coordination with the implementation agent using session.state.
        """,
        output_key="parallel_testing",
    )

    return ParallelAgent(
        name="parallel_implementation_workflow",
        description="Runs implementation tasks in parallel",
        sub_agents=[
            parallel_implementation_agent,
            parallel_testing_agent,  # Separate testing agent instance
            # Additional agents can be added as needed
        ],
    )


def create_parallel_validation_workflow() -> ParallelAgent:
    """
    Creates a parallel workflow for validation tasks that can run independently.

    This runs multiple validation checks concurrently:
    - Code review
    - Quality analysis
    - Security analysis
    - Performance testing
    """

    # Create separate agent instances for validation workflow
    validation_review_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="validation_review_agent",
        description="Code review agent for validation workflow",
        instruction="""
        You are a code review agent specialized in validation workflows.

        Your tasks:
        1. Perform thorough code review for validation
        2. Check for security vulnerabilities
        3. Validate code quality and standards
        4. Ensure compliance with best practices

        Focus on validation-specific concerns and store results in session.state.
        """,
        output_key="validation_review",
    )

    validation_quality_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="validation_quality_agent",
        description="Quality analysis agent for validation workflow",
        instruction="""
        You are a quality analysis agent specialized in validation workflows.

        Your tasks:
        1. Perform static code analysis
        2. Check code metrics and complexity
        3. Validate coding standards compliance
        4. Identify technical debt and improvements

        Focus on quality validation and store results in session.state.
        """,
        output_key="validation_quality",
    )

    return ParallelAgent(
        name="parallel_validation_workflow",
        description="Runs validation checks in parallel",
        sub_agents=[
            validation_review_agent,  # Separate review agent instance
            validation_quality_agent,  # Separate quality agent instance
            # Additional validation agents can be added
        ],
    )
