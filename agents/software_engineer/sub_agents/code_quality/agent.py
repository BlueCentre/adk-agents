"""Code quality agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...tools import load_tools_for_sub_agent
from . import prompt


def create_code_quality_agent(name_suffix=""):
    """Factory function to create code quality agent instances.

    Args:
        name_suffix: Optional suffix to append to agent name (e.g., "enhanced_")

    Returns:
        Agent: Configured code quality agent instance
    """
    agent_name = f"{name_suffix}code_quality_agent" if name_suffix else "code_quality_agent"

    # Load tools using the profile-based loading with per-sub-agent MCP configuration
    # This uses the new per-sub-agent MCP tool loading system
    tools = load_tools_for_sub_agent("code_quality", sub_agent_name=agent_name)

    return Agent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name=agent_name,
        description="Analyzes code for quality issues and suggests improvements",
        instruction=prompt.CODE_QUALITY_AGENT_INSTR,
        generate_content_config=GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            max_output_tokens=4096,
        ),
        tools=tools,
    )


# Create the default instance for backward compatibility
code_quality_agent = create_code_quality_agent()
