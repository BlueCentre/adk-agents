"""Enhanced Software Engineer Agent with ADK Workflow Patterns."""

import logging
from typing import Any
import warnings

from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.adk.tools import FunctionTool, ToolContext, load_memory
from google.genai import types

from . import config as agent_config, prompt
from .shared_libraries.callbacks import (
    create_enhanced_telemetry_callbacks,
    create_model_config_callbacks,
    create_retry_callbacks,
    create_token_optimization_callbacks,
)

# Import sub-agent prompts and tools to create separate instances
from .tools.setup import load_all_tools_and_toolsets

# Ignore all warnings
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR)

# logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def add_retry_capabilities_to_agent(agent, retry_handler):
    """Add retry capabilities to an agent by wrapping the model's generate_content_async method."""
    if not retry_handler:
        logger.warning(f"[{agent.name}] No retry handler provided, skipping retry setup")
        return agent

    # Get the agent's model
    model = agent.model if hasattr(agent, "model") else None
    if not model:
        logger.warning(f"[{agent.name}] No model found on agent, skipping retry setup")
        return agent

    # Store the original generate_content_async method
    original_generate_content_async = model.generate_content_async

    # Create the retry-enabled version
    async def generate_content_async_with_retry(llm_request, stream=False):
        """Wrap generate_content_async with retry logic."""

        async def model_call():
            # Call the original method and collect all responses
            responses = []
            async for response in original_generate_content_async(llm_request, stream):
                responses.append(response)
            return responses

        # Use retry handler to wrap the model call
        responses = await retry_handler(model_call)

        # Yield the responses (to maintain the async generator interface)
        for response in responses:
            yield response

    # Replace the model's method with the retry-enabled version
    # Use object.__setattr__ to bypass Pydantic validation
    try:
        object.__setattr__(model, "generate_content_async", generate_content_async_with_retry)
        logger.debug(f"[{agent.name}] Successfully replaced generate_content_async method")
    except Exception as e:
        logger.warning(f"[{agent.name}] Failed to replace generate_content_async method: {e}")
        # Fallback: try direct assignment (might work for some model types)
        try:
            model.generate_content_async = generate_content_async_with_retry
            logger.debug(f"[{agent.name}] Fallback method replacement successful")
        except Exception as e2:
            logger.error(f"[{agent.name}] Both method replacement attempts failed: {e2}")
            return agent

    # Store references for debugging/testing
    agent._retry_handler = retry_handler
    agent._original_generate_content_async = original_generate_content_async

    logger.info(
        f"[{agent.name}] Retry capabilities integrated - model calls now include "
        "automatic retry with exponential backoff"
    )
    return agent


def create_enhanced_sub_agents():
    """Create separate sub-agent instances for the enhanced agent to avoid parent conflicts.

    Uses factory functions from each sub-agent module to eliminate code duplication
    while maintaining full feature parity with sophisticated tool loading and callbacks.
    """
    # Import factory functions from each sub-agent module
    from .sub_agents.code_quality.agent import create_code_quality_agent
    from .sub_agents.code_review.agent import create_code_review_agent
    from .sub_agents.debugging.agent import create_debugging_agent
    from .sub_agents.design_pattern.agent import (  # Static tools, no factory needed
        design_pattern_agent,
    )
    from .sub_agents.devops.agent import create_devops_agent
    from .sub_agents.documentation.agent import create_documentation_agent
    from .sub_agents.ollama.agent import create_ollama_agent
    from .sub_agents.testing.agent import create_testing_agent

    # Create enhanced instances using factory functions
    enhanced_sub_agents = []

    # 1. Design Pattern Agent - Create new instance with different name (uses static tools)
    enhanced_design_pattern_agent = LlmAgent(
        model=design_pattern_agent.model,
        name="enhanced_design_pattern_agent",
        description=design_pattern_agent.description,
        instruction=design_pattern_agent.instruction,
        tools=design_pattern_agent.tools,  # Reuse same static tools
        output_key="design_pattern",
    )
    enhanced_sub_agents.append(enhanced_design_pattern_agent)

    # 2-8. All other agents - Use factory functions (eliminates all duplication!)
    enhanced_sub_agents.append(create_code_review_agent("enhanced_"))
    enhanced_sub_agents.append(create_testing_agent("enhanced_"))
    enhanced_sub_agents.append(create_code_quality_agent("enhanced_"))
    enhanced_sub_agents.append(create_debugging_agent("enhanced_"))
    enhanced_sub_agents.append(create_documentation_agent("enhanced_"))
    enhanced_sub_agents.append(create_devops_agent("enhanced_"))
    enhanced_sub_agents.append(create_ollama_agent("enhanced_"))

    return enhanced_sub_agents


def state_manager_tool(
    action: str, key: str = "", value: str = "", tool_context: ToolContext = None
) -> dict[str, Any]:
    """
    Tool for managing shared state between agents in workflows.

    Args:
        action: Action to perform (get, set, update, delete, list_keys)
        key: State key to operate on
        value: String value to set (for set/update actions)
        tool_context: ADK tool context

    Returns:
        Dict containing operation result
    """

    if not tool_context or not tool_context.state:
        return {"status": "error", "message": "No session state available"}

    try:
        if action == "get":
            result = tool_context.state.get(key)
            return {"status": "success", "key": key, "value": result}

        if action == "set":
            tool_context.state[key] = value
            return {"status": "success", "message": f"Set {key} = {value}"}

        if action == "update":
            # For simplicity, treat update as set for string values
            tool_context.state[key] = value
            return {"status": "success", "message": f"Updated {key}"}

        if action == "delete":
            if key in tool_context.state:
                del tool_context.state[key]
                return {"status": "success", "message": f"Deleted {key}"}
            return {"status": "warning", "message": f"Key {key} not found"}

        if action == "list_keys":
            keys = list(tool_context.state.keys())
            return {"status": "success", "keys": keys}

        return {"status": "error", "message": f"Unknown action: {action}"}

    except Exception as e:
        return {"status": "error", "message": f"State operation failed: {e!s}"}


def workflow_selector_tool(
    task_type: str,
    complexity: str = "medium",
    requires_approval: bool = False,
    parallel_capable: bool = False,
    iterative: bool = False,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """
    Tool that selects the appropriate workflow pattern based on task characteristics.

    Args:
        task_type: Type of task (e.g., "feature_development", "bug_fix", "code_review")
        complexity: Complexity level (low, medium, high)
        requires_approval: Whether human approval is needed
        parallel_capable: Whether task can benefit from parallel processing
        iterative: Whether task needs iterative refinement
        tool_context: ADK tool context

    Returns:
        Dict containing selected workflow and configuration
    """

    workflows = {
        # Sequential workflows
        "feature_development": "feature_development_workflow",
        "bug_fix": "bug_fix_workflow",
        "code_review": "code_review_workflow",
        "refactoring": "refactoring_workflow",
        # Parallel workflows
        "analysis": "parallel_analysis_workflow",
        "implementation": "parallel_implementation_workflow",
        "validation": "parallel_validation_workflow",
        # Iterative workflows
        "refinement": "iterative_refinement_workflow",
        "debug": "iterative_debug_workflow",
        "test_improvement": "iterative_test_improvement_workflow",
        "code_generation": "iterative_code_generation_workflow",
        # Human-in-the-loop workflows
        "approval": "approval_workflow",
        "collaborative_review": "collaborative_review_workflow",
        "architecture_decision": "architecture_decision_workflow",
        "deployment": "deployment_approval_workflow",
    }

    selected_workflow = workflows.get(task_type, "feature_development_workflow")

    # Modify selection based on characteristics
    if requires_approval:
        if task_type == "code_review":
            selected_workflow = "collaborative_review_workflow"
        elif task_type in ["architecture", "deployment"]:
            selected_workflow = f"{task_type}_workflow"
        else:
            selected_workflow = "approval_workflow"

    if parallel_capable and complexity in ["medium", "high"]:
        if task_type in ["analysis", "implementation", "validation"]:
            selected_workflow = f"parallel_{task_type}_workflow"

    if iterative and complexity == "high":
        if task_type in ["refinement", "debug", "test_improvement", "code_generation"]:
            selected_workflow = f"iterative_{task_type}_workflow"

    # Store workflow selection in session state
    if tool_context and tool_context.state:
        tool_context.state["selected_workflow"] = {
            "workflow": selected_workflow,
            "task_type": task_type,
            "complexity": complexity,
            "requires_approval": requires_approval,
            "parallel_capable": parallel_capable,
            "iterative": iterative,
        }

    return {
        "selected_workflow": selected_workflow,
        "task_characteristics": {
            "task_type": task_type,
            "complexity": complexity,
            "requires_approval": requires_approval,
            "parallel_capable": parallel_capable,
            "iterative": iterative,
        },
        "recommendation_reason": (
            f"Selected {selected_workflow} based on task complexity and requirements",
        ),
    }


# Create tool instances
state_manager_function_tool = FunctionTool(state_manager_tool)
workflow_selector_function_tool = FunctionTool(workflow_selector_tool)


def create_enhanced_software_engineer_agent() -> Agent:
    """
    Create an enhanced software engineer agent with retry capabilities.

    Returns:
        RetryEnabledAgent: Configured agent instance with workflow orchestration
    """
    try:
        logger.info("Creating enhanced software engineer agent...")

        # Initialize model
        model = LiteLlm(model=f"gemini/{agent_config.DEFAULT_AGENT_MODEL}")

        # Load all available tools and toolsets from enhanced tool setup
        tools = load_all_tools_and_toolsets()  # This returns a flat list of tools
        # This allows dynamic workflow creation without pre-instantiating all workflows

        # Add workflow and state management tools
        tools.extend(
            [
                state_manager_function_tool,
                workflow_selector_function_tool,
                load_memory,
            ]
        )

        # Create focused single-purpose callbacks
        telemetry_callbacks = create_enhanced_telemetry_callbacks("enhanced_software_engineer")
        model_config_callbacks = create_model_config_callbacks(model.model)
        optimization_callbacks = create_token_optimization_callbacks("enhanced_software_engineer")
        retry_callbacks = create_retry_callbacks("enhanced_software_engineer")

        # Create the enhanced agent
        agent = Agent(
            model=model,
            name="enhanced_software_engineer",
            description="Advanced software engineer with ADK workflow orchestration capabilities",
            instruction=prompt.SOFTWARE_ENGINEER_ENHANCED_INSTR,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=agent_config.GEMINI_THINKING_INCLUDE_THOUGHTS,
                    thinking_budget=agent_config.GEMINI_THINKING_BUDGET,
                ),
            )
            if agent_config.GEMINI_THINKING_ENABLE
            and agent_config.is_thinking_supported(agent_config.DEFAULT_AGENT_MODEL)
            else None,
            generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
            sub_agents=create_enhanced_sub_agents(),  # Separate instances to avoid parent conflicts
            tools=tools,
            # Add focused single-purpose callbacks (Telemetry → Config → Optimization)
            before_agent_callback=[
                telemetry_callbacks["before_agent"],
                optimization_callbacks["before_agent"],
            ],
            after_agent_callback=[
                telemetry_callbacks["after_agent"],
                optimization_callbacks["after_agent"],
            ],
            before_model_callback=[
                retry_callbacks["before_model"],  # Retry setup first
                telemetry_callbacks["before_model"],
                model_config_callbacks["before_model"],
                optimization_callbacks["before_model"],
            ],
            after_model_callback=[
                retry_callbacks["after_model"],  # Retry cleanup first
                telemetry_callbacks["after_model"],
                optimization_callbacks["after_model"],
            ],
            before_tool_callback=[
                telemetry_callbacks["before_tool"],
                optimization_callbacks["before_tool"],
            ],
            after_tool_callback=[
                telemetry_callbacks["after_tool"],
                optimization_callbacks["after_tool"],
            ],
            output_key="enhanced_software_engineer",
        )

        # Add retry capabilities to the agent
        return add_retry_capabilities_to_agent(agent, retry_callbacks["retry_handler"])

    except Exception as e:
        logger.error(f"Failed to create enhanced software engineer agent: {e!s}")
        raise


# Create the enhanced agent instance
enhanced_root_agent = create_enhanced_software_engineer_agent()

# Export as root_agent for ADK compatibility
# This allows the enhanced agent to be loaded as the default agent
root_agent = enhanced_root_agent
