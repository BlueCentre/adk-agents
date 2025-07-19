"""Code review agent implementation."""

from google.adk.agents import Agent

from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...shared_libraries.callbacks import create_telemetry_callbacks
from ...tools import load_tools_for_sub_agent
from . import prompt


def create_code_review_agent(name_suffix=""):
    """Factory function to create code review agent instances.

    Args:
        name_suffix: Optional suffix to append to agent name (e.g., "enhanced_")

    Returns:
        Agent: Configured code review agent instance
    """
    agent_name = f"{name_suffix}code_review_agent" if name_suffix else "code_review_agent"

    # Create telemetry callbacks for observability
    callbacks = create_telemetry_callbacks(agent_name)

    # Load tools using the profile-based loading with per-sub-agent MCP configuration
    # This uses the new per-sub-agent MCP tool loading system
    tools = load_tools_for_sub_agent("code_review", sub_agent_name=agent_name)

    return Agent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name=agent_name,
        description="Analyzes code for issues and suggests improvements",
        instruction=prompt.CODE_REVIEW_AGENT_INSTR,
        generate_content_config=GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            max_output_tokens=1000,
        ),
        tools=tools,
        # Add telemetry callbacks for observability
        before_agent_callback=callbacks["before_agent"],
        after_agent_callback=callbacks["after_agent"],
        before_model_callback=callbacks["before_model"],
        after_model_callback=callbacks["after_model"],
        before_tool_callback=callbacks["before_tool"],
        after_tool_callback=callbacks["after_tool"],
        output_key="code_review",
    )


# Create the default instance for backward compatibility
code_review_agent = create_code_review_agent()
