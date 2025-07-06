"""Sequential workflow patterns for the Software Engineer Agent."""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from .. import config as agent_config
from ..sub_agents.code_quality.agent import code_quality_agent
from ..sub_agents.code_review.agent import code_review_agent
from ..sub_agents.debugging.agent import debugging_agent
from ..sub_agents.design_pattern.agent import design_pattern_agent
from ..sub_agents.devops.agent import devops_agent
from ..sub_agents.documentation.agent import documentation_agent
from ..sub_agents.testing.agent import testing_agent


class WorkflowOrchestratorAgent(LlmAgent):
    """Agent that orchestrates workflow steps and manages state transitions."""
    
    def __init__(self, name: str = "workflow_orchestrator"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Orchestrates workflow steps and manages state transitions",
            instruction="Orchestrate workflow steps and manage state transitions",
            output_key="workflow_orchestrator"
        )
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Orchestrate workflow and manage state."""
        
        # Get current workflow state
        workflow_state = ctx.session.state.get("workflow_state", {})
        current_step = workflow_state.get("current_step", 0)
        total_steps = workflow_state.get("total_steps", 0)
        
        # Update workflow progress
        workflow_state.update({
            "current_step": current_step + 1,
            "status": "in_progress",
            "last_updated": ctx.session.created_at.isoformat() if ctx.session.created_at else None
        })
        
        ctx.session.state["workflow_state"] = workflow_state
        
        # Generate progress event
        yield Event(
            author=self.name,
            text=f"Workflow orchestration: Step {current_step + 1} of {total_steps}",
            actions=EventActions()
        )


def create_feature_development_workflow() -> SequentialAgent:
    """
    Creates a sequential workflow for complete feature development.
    
    This implements the ADK Sequential Pipeline Pattern following the natural
    software development lifecycle:
    1. Design & Architecture → 2. Implementation → 3. Testing → 4. Documentation → 5. Deployment
    """
    
    # Create workflow orchestrator
    orchestrator = WorkflowOrchestratorAgent()
    
    # Create planning agent that sets up the workflow
    planning_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="feature_planning_agent",
        description="Plans feature development workflow",
        instruction="""
        You are a feature planning agent. Your role is to:
        1. Analyze the feature requirements and break them down into tasks
        2. Set up the workflow state in session.state['workflow_state']
        3. Prepare context for subsequent agents
        4. Determine the scope and complexity of the feature
        
        Store your analysis in session.state['feature_plan'] for other agents to use.
        Set workflow_state with total_steps and current_step.
        """,
        output_key="feature_plan"
    )
    
    # Create sequential workflow
    feature_development = SequentialAgent(
        name="feature_development_workflow",
        description="Complete feature development pipeline",
        sub_agents=[
            planning_agent,          # 1. Plan the feature
            design_pattern_agent,    # 2. Design architecture
            code_review_agent,       # 3. Review implementation approach
            testing_agent,           # 4. Plan testing strategy
            debugging_agent,         # 5. Handle any issues
            documentation_agent,     # 6. Create documentation
            devops_agent,           # 7. Setup deployment
            orchestrator            # 8. Finalize workflow
        ]
    )
    
    return feature_development


def create_bug_fix_workflow() -> SequentialAgent:
    """
    Creates a sequential workflow for systematic bug fixing.
    
    This follows the debugging methodology:
    1. Reproduce → 2. Analyze → 3. Fix → 4. Test → 5. Document
    """
    
    # Create bug analysis agent
    bug_analysis_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="bug_analysis_agent",
        description="Analyzes bug reports and reproduction steps",
        instruction="""
        You analyze bug reports and prepare context for the debugging workflow.
        
        Your tasks:
        1. Understand the bug report and symptoms
        2. Gather relevant context from the codebase
        3. Prepare reproduction steps
        4. Store analysis in session.state['bug_analysis']
        5. Set up workflow state for debugging process
        """,
        output_key="bug_analysis"
    )
    
    # Create verification agent
    verification_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="fix_verification_agent",
        description="Verifies bug fixes and ensures no regressions",
        instruction="""
        You verify that bug fixes work correctly and don't introduce regressions.
        
        Your tasks:
        1. Check that the original issue is resolved
        2. Run tests to ensure no regressions
        3. Validate the fix against edge cases
        4. Store verification results in session.state['fix_verification']
        """,
        output_key="fix_verification"
    )
    
    bug_fix_workflow = SequentialAgent(
        name="bug_fix_workflow",
        description="Systematic bug fixing process",
        sub_agents=[
            bug_analysis_agent,     # 1. Analyze the bug
            debugging_agent,        # 2. Debug and fix
            testing_agent,          # 3. Test the fix
            verification_agent,     # 4. Verify fix works
            documentation_agent     # 5. Document the fix
        ]
    )
    
    return bug_fix_workflow


def create_code_review_workflow() -> SequentialAgent:
    """
    Creates a sequential workflow for comprehensive code review.
    
    This implements a thorough review process:
    1. Static Analysis → 2. Manual Review → 3. Testing Review → 4. Documentation Review
    """
    
    # Create review preparation agent
    review_prep_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="review_preparation_agent",
        description="Prepares code review context and scope",
        instruction="""
        You prepare the context for code review.
        
        Your tasks:
        1. Analyze the code changes and scope
        2. Identify files and components to review
        3. Set up review checklist based on change type
        4. Store review context in session.state['review_context']
        """,
        output_key="review_context"
    )
    
    # Create review summary agent
    review_summary_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="review_summary_agent",
        description="Summarizes code review findings",
        instruction="""
        You summarize code review findings from all review agents.
        
        Your tasks:
        1. Collect findings from code_quality, code_review, and testing agents
        2. Prioritize issues by severity and impact
        3. Create actionable recommendations
        4. Store summary in session.state['review_summary']
        """,
        output_key="review_summary"
    )
    
    code_review_workflow = SequentialAgent(
        name="code_review_workflow",
        description="Comprehensive code review process",
        sub_agents=[
            review_prep_agent,      # 1. Prepare review
            code_quality_agent,     # 2. Static analysis
            code_review_agent,      # 3. Manual review
            testing_agent,          # 4. Test review
            review_summary_agent    # 5. Summarize findings
        ]
    )
    
    return code_review_workflow


def create_refactoring_workflow() -> SequentialAgent:
    """
    Creates a sequential workflow for code refactoring.
    
    This ensures safe refactoring:
    1. Analyze → 2. Design → 3. Test → 4. Refactor → 5. Verify
    """
    
    # Create refactoring analysis agent
    refactoring_analysis_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="refactoring_analysis_agent",
        description="Analyzes code for refactoring opportunities",
        instruction="""
        You analyze code for refactoring opportunities.
        
        Your tasks:
        1. Identify code smells and improvement opportunities
        2. Analyze dependencies and impact of changes
        3. Prioritize refactoring tasks by value and risk
        4. Store analysis in session.state['refactoring_analysis']
        """,
        output_key="refactoring_analysis"
    )
    
    refactoring_workflow = SequentialAgent(
        name="refactoring_workflow",
        description="Safe code refactoring process",
        sub_agents=[
            refactoring_analysis_agent,  # 1. Analyze refactoring needs
            testing_agent,              # 2. Ensure good test coverage
            design_pattern_agent,       # 3. Design refactored structure
            code_quality_agent,         # 4. Apply refactoring
            testing_agent,              # 5. Verify refactoring works
            documentation_agent         # 6. Update documentation
        ]
    )
    
    return refactoring_workflow 