"""Iterative workflow patterns for the Software Engineer Agent."""

from collections.abc import AsyncGenerator
import logging

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from .. import config as agent_config
from ..sub_agents.code_quality.agent import code_quality_agent
from ..sub_agents.code_review.agent import code_review_agent
from ..sub_agents.debugging.agent import debugging_agent
from ..sub_agents.testing.agent import testing_agent
from .code_refinement import (
    CodeImprover,
    CodeQualityAndTestingIntegrator,
    CodeRefinementFeedbackCollector,
    CodeRefinementReviser,
    IterativeQualityChecker,
)

logger = logging.getLogger(__name__)


class CodeRefinementSatisfactionChecker(BaseAgent):
    """Checks if the user is satisfied with the code refinement."""

    def __init__(self, name: str = "code_refinement_satisfaction_checker"):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Check if user is satisfied or if we should continue refining."""

        # Get feedback and iteration state
        feedback_list = ctx.session.state.get("refinement_feedback", [])
        iteration_state = ctx.session.state.get("iteration_state", {})
        current_iteration = iteration_state.get("current_iteration", 0)
        max_iterations = iteration_state.get("max_iterations", 5)

        should_stop = False
        reason = ""

        if feedback_list:
            latest_feedback = feedback_list[-1]
            user_satisfied = latest_feedback.get("user_satisfied", False)

            if user_satisfied:
                should_stop = True
                reason = "User is satisfied with the code"
            elif current_iteration >= max_iterations:
                should_stop = True
                reason = f"Maximum iterations reached ({max_iterations})"
            else:
                reason = f"Continuing refinement - iteration {current_iteration + 1}"
        else:
            # No feedback yet, continue to collect it
            reason = "Waiting for initial user feedback"

        # Update iteration state
        iteration_state.update(
            {
                "current_iteration": current_iteration + 1,
                "should_stop": should_stop,
                "reason": reason,
            }
        )
        ctx.session.state["iteration_state"] = iteration_state

        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[genai_types.Part(text=f"Refinement check: {reason}")]
            ),
            actions=EventActions(escalate=should_stop),
        )


def create_code_refinement_loop() -> LoopAgent:
    """
    Creates a code refinement loop workflow for iterative code improvement based on user feedback.

    This implements the ADK Iterative Refinement Pattern for user-driven code improvement:
    1. Present code → 2. Collect feedback → 3. Revise code → 4. Run integrated
    quality/testing checks → 5. Repeat until user satisfied

    The workflow creates a mini "red-green-refactor" cycle:
    - RED: Identify quality issues and testing gaps
    - GREEN: Ensure code meets basic standards
    - REFACTOR: Apply user feedback for continuous improvement
    """

    # Create feedback collector
    feedback_collector = CodeRefinementFeedbackCollector()

    # Create code reviser
    code_reviser = CodeRefinementReviser()

    # Create integrated quality and testing analyzer
    quality_testing_integrator = CodeQualityAndTestingIntegrator()

    # Create satisfaction checker
    satisfaction_checker = CodeRefinementSatisfactionChecker()

    # Create initialization agent
    init_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="code_refinement_init_agent",
        description="Initializes code refinement process",
        instruction="""
        You initialize the code refinement process.

        Your tasks:
        1. Set up iteration_state in session.state
        2. Ensure initial code is available in session.state['current_code']
        3. Initialize refinement_feedback list
        4. Set up revision_history tracking
        5. Initialize quality and testing tracking
        6. Prepare context for iterative user-driven improvement

        If no initial code is provided, you should generate a basic implementation
        based on the task description.

        The refinement process integrates:
        - User feedback collection and processing
        - Contextual code revision based on feedback
        - Integrated code quality analysis and testing
        - Mini red-green-refactor cycles for continuous improvement
        """,
        output_key="refinement_init",
    )

    # Create iterative code refinement loop with integrated quality & testing
    return LoopAgent(
        name="code_refinement_loop",
        description="Iteratively refines code based on user feedback with integrated "
        "quality analysis and testing",
        max_iterations=agent_config.CODE_REFINEMENT_MAX_ITERATIONS,
        sub_agents=[
            init_agent,  # Initialize (runs once)
            feedback_collector,  # Collect user feedback
            code_reviser,  # Revise code based on feedback
            quality_testing_integrator,  # Integrated quality analysis and testing
            # (RED-GREEN-REFACTOR)
            satisfaction_checker,  # Check if user is satisfied
        ],
    )


def create_iterative_refinement_workflow() -> LoopAgent:
    """
    Creates an iterative refinement workflow that continuously improves code quality.

    This implements the ADK Iterative Refinement Pattern:
    1. Analyze code → 2. Improve → 3. Test → 4. Check quality → 5. Repeat until satisfied
    """

    # Create code improver
    code_improver = CodeImprover()

    # Create quality checker
    quality_checker = IterativeQualityChecker()

    # Create initialization agent
    init_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="refinement_init_agent",
        description="Initializes iterative refinement process",
        instruction="""
        You initialize the iterative refinement process.

        Your tasks:
        1. Set up iteration_state in session.state
        2. Analyze initial code quality
        3. Set quality targets and thresholds
        4. Prepare context for iterative improvement
        """,
        output_key="refinement_init",
    )

    # Create iterative refinement loop
    return LoopAgent(
        name="iterative_refinement_loop",
        description="Iteratively refines code until quality standards are met",
        max_iterations=5,
        sub_agents=[
            init_agent,  # Initialize (runs once)
            code_improver,  # Improve code based on feedback
            code_quality_agent,  # Check code quality
            code_review_agent,  # Review improvements
            testing_agent,  # Test improvements
            quality_checker,  # Check if we should stop
        ],
    )


def create_iterative_debug_workflow() -> LoopAgent:
    """
    Creates an iterative debugging workflow that keeps trying until the bug is fixed.

    This implements iterative debugging:
    1. Analyze → 2. Fix → 3. Test → 4. Verify → 5. Repeat until fixed
    """

    # Create debug verification agent
    debug_verification_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="debug_verification_agent",
        description="Verifies if debugging was successful",
        instruction="""
        You verify if debugging was successful.

        Your tasks:
        1. Check if the original issue is resolved
        2. Verify no new issues were introduced
        3. Test edge cases related to the bug
        4. Store verification results in session.state['debug_verification']
        5. Set escalate=True if bug is fixed, False if more debugging needed
        """,
        output_key="debug_verification",
    )

    class DebugSuccessChecker(BaseAgent):
        """Checks if debugging was successful."""

        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            debug_result = ctx.session.state.get("debug_verification", {})
            bug_fixed = debug_result.get("bug_fixed", False)

            # Check maximum iterations
            iteration_state = ctx.session.state.get("iteration_state", {})
            current_iteration = iteration_state.get("current_iteration", 0)
            max_iterations = iteration_state.get("max_iterations", 3)

            should_stop = bug_fixed or current_iteration >= max_iterations
            reason = "Bug fixed" if bug_fixed else f"Max iterations reached ({max_iterations})"

            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text=f"Debug check: {reason}")]
                ),
                actions=EventActions(escalate=should_stop),
            )

    debug_success_checker = DebugSuccessChecker(name="debug_success_checker")

    # Create iterative debug loop
    return LoopAgent(
        name="iterative_debug_loop",
        description="Iteratively debugs until issue is resolved",
        max_iterations=3,
        sub_agents=[
            debugging_agent,  # Debug the issue
            testing_agent,  # Test the fix
            debug_verification_agent,  # Verify fix works
            debug_success_checker,  # Check if we should stop
        ],
    )


def create_iterative_test_improvement_workflow() -> LoopAgent:
    """
    Creates an iterative workflow for improving test coverage and quality.

    This keeps adding tests until coverage targets are met:
    1. Analyze coverage → 2. Add tests → 3. Run tests → 4. Check coverage → 5. Repeat
    """

    # Create test coverage analyzer
    coverage_analyzer = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="coverage_analyzer",
        description="Analyzes test coverage and identifies gaps",
        instruction="""
        You analyze test coverage and identify gaps.

        Your tasks:
        1. Analyze current test coverage
        2. Identify uncovered code paths
        3. Prioritize missing tests by importance
        4. Store analysis in session.state['coverage_analysis']
        """,
        output_key="coverage_analysis",
    )

    class CoverageChecker(BaseAgent):
        """Checks if coverage targets are met."""

        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            testing_result = ctx.session.state.get("testing", {})
            coverage = testing_result.get("coverage", 0)
            target_coverage = 85  # 85% coverage target

            # Check maximum iterations
            iteration_state = ctx.session.state.get("iteration_state", {})
            current_iteration = iteration_state.get("current_iteration", 0)
            max_iterations = iteration_state.get("max_iterations", 4)

            should_stop = coverage >= target_coverage or current_iteration >= max_iterations
            reason = (
                f"Coverage target met ({coverage}%)"
                if coverage >= target_coverage
                else f"Max iterations reached ({max_iterations})"
            )

            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text=f"Coverage check: {reason}")]
                ),
                actions=EventActions(escalate=should_stop),
            )

    coverage_checker = CoverageChecker(name="coverage_checker")

    # Create iterative test improvement loop
    return LoopAgent(
        name="iterative_test_improvement_loop",
        description="Iteratively improves test coverage until targets are met",
        max_iterations=4,
        sub_agents=[
            coverage_analyzer,  # Analyze coverage gaps
            testing_agent,  # Add more tests
            coverage_checker,  # Check if target is met
        ],
    )


def create_iterative_code_generation_workflow() -> LoopAgent:
    """
    Creates an iterative code generation workflow that refines generated code.

    This implements the Generator-Critic pattern:
    1. Generate code → 2. Review → 3. Refine → 4. Test → 5. Repeat until satisfactory
    """

    # Create code generator
    code_generator = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="iterative_code_generator",
        description="Generates code iteratively based on feedback",
        instruction="""
        You generate code iteratively based on feedback.

        Your tasks:
        1. Generate initial code or refine existing code
        2. Incorporate feedback from previous iterations
        3. Store generated code in session.state['generated_code']
        4. Include explanations for design decisions
        """,
        output_key="generated_code",
    )

    class GenerationQualityChecker(BaseAgent):
        """Checks if generated code meets quality standards."""

        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            # Get feedback from review agents
            review_result = ctx.session.state.get("code_review", {})
            quality_result = ctx.session.state.get("code_quality", {})

            # Simple quality scoring
            review_score = 5 - len(review_result.get("issues", []))  # Fewer issues = better
            quality_score = 5 if quality_result.get("status") == "pass" else 2

            total_score = (review_score + quality_score) / 2

            # Check iterations
            iteration_state = ctx.session.state.get("iteration_state", {})
            current_iteration = iteration_state.get("current_iteration", 0)
            max_iterations = iteration_state.get("max_iterations", 3)

            should_stop = total_score >= 4.0 or current_iteration >= max_iterations
            reason = (
                f"Quality score: {total_score:.1f}/5"
                if total_score >= 4.0
                else f"Max iterations reached ({max_iterations})"
            )

            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text=f"Generation quality check: {reason}")]
                ),
                actions=EventActions(escalate=should_stop),
            )

    generation_quality_checker = GenerationQualityChecker(name="generation_quality_checker")

    # Create iterative code generation loop
    return LoopAgent(
        name="iterative_code_generation_loop",
        description="Iteratively generates and refines code based on feedback",
        max_iterations=3,
        sub_agents=[
            code_generator,  # Generate/refine code
            code_review_agent,  # Review generated code
            code_quality_agent,  # Check quality
            generation_quality_checker,  # Check if we should stop
        ],
    )
