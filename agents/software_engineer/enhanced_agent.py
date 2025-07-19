"""Enhanced Software Engineer Agent with ADK Workflow Patterns."""

import logging
from typing import Any, Dict

from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool, ToolContext, load_memory
from google.genai.types import GenerateContentConfig

from . import config as agent_config
from . import prompt
from .shared_libraries.callbacks import create_enhanced_telemetry_callbacks

# Import sub-agent prompts and tools to create separate instances
from .tools.setup import load_all_tools_and_toolsets

# Import workflow patterns

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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


def workflow_selector_tool(
    task_type: str,
    complexity: str = "medium",
    requires_approval: bool = False,
    parallel_capable: bool = False,
    iterative: bool = False,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
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
        "recommendation_reason": f"Selected {selected_workflow} based on task complexity and requirements",
    }


def state_manager_tool(
    action: str, key: str = "", value: str = "", tool_context: ToolContext = None
) -> Dict[str, Any]:
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

        elif action == "set":
            tool_context.state[key] = value
            return {"status": "success", "message": f"Set {key} = {value}"}

        elif action == "update":
            # For simplicity, treat update as set for string values
            tool_context.state[key] = value
            return {"status": "success", "message": f"Updated {key}"}

        elif action == "delete":
            if key in tool_context.state:
                del tool_context.state[key]
                return {"status": "success", "message": f"Deleted {key}"}
            else:
                return {"status": "warning", "message": f"Key {key} not found"}

        elif action == "list_keys":
            keys = list(tool_context.state.keys())
            return {"status": "success", "keys": keys}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    except Exception as e:
        return {"status": "error", "message": f"State operation failed: {str(e)}"}


# Create tool instances
workflow_selector_function_tool = FunctionTool(workflow_selector_tool)
state_manager_function_tool = FunctionTool(state_manager_tool)


def create_enhanced_software_engineer_agent() -> Agent:
    """
    Creates an enhanced software engineer agent with intelligent workflow orchestration.

    This agent provides:
    1. Traditional sub-agent delegation for simple tasks
    2. Workflow orchestration tools for complex tasks
    3. Shared state management
    4. Intelligent task routing and coordination
    """

    # Load all tools
    tools = load_all_tools_and_toolsets()

    # Add workflow and state management tools
    tools.extend(
        [workflow_selector_function_tool, state_manager_function_tool, load_memory]
    )

    # Create telemetry callbacks for observability
    callbacks = create_enhanced_telemetry_callbacks("enhanced_software_engineer")

    # Note: Workflows are created on-demand to avoid agent parent conflicts
    # This allows dynamic workflow creation without pre-instantiating all workflows

    # Create the enhanced agent
    enhanced_agent = Agent(
        model=LiteLlm(model=f"gemini/{agent_config.DEFAULT_AGENT_MODEL}"),
        name="enhanced_software_engineer",
        description="Advanced software engineer with ADK workflow orchestration capabilities",
        instruction=prompt.SOFTWARE_ENGINEER_ENHANCED_INSTR,
        generate_content_config=GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            # max_output_tokens=4096,
        ),
        sub_agents=create_enhanced_sub_agents(),  # Create separate instances to avoid parent conflicts
        tools=tools,
        # Add telemetry callbacks for observability
        before_agent_callback=callbacks["before_agent"],
        after_agent_callback=callbacks["after_agent"],
        before_model_callback=callbacks["before_model"],
        after_model_callback=callbacks["after_model"],
        before_tool_callback=callbacks["before_tool"],
        after_tool_callback=callbacks["after_tool"],
        output_key="enhanced_software_engineer",
    )

    return enhanced_agent


# Create the enhanced agent instance
enhanced_root_agent = create_enhanced_software_engineer_agent()

# Export as root_agent for ADK compatibility
# This allows the enhanced agent to be loaded as the default agent
root_agent = enhanced_root_agent
