"""Documentation Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...tools import load_tools_for_sub_agent
from . import prompt


def create_documentation_agent(name_suffix=""):
    """Factory function to create documentation agent instances.

    Args:
        name_suffix: Optional suffix to append to agent name (e.g., "enhanced_")

    Returns:
        LlmAgent: Configured documentation agent instance
    """
    agent_name = (
        f"{name_suffix}documentation_agent" if name_suffix else "documentation_agent"
    )

    # Load tools using the profile-based loading with per-sub-agent MCP configuration
    # This uses the new per-sub-agent MCP tool loading system
    tools = load_tools_for_sub_agent("documentation", sub_agent_name=agent_name)

    return LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name=agent_name,
        description="Agent specialized in writing and updating documentation",
        instruction=prompt.DOCUMENTATION_AGENT_INSTR,
        generate_content_config=GenerateContentConfig(
            temperature=0.3,
            top_p=0.95,
            # max_output_tokens=4096,
        ),
        tools=tools,
        output_key="documentation",
    )


# Create the default instance for backward compatibility
documentation_agent = create_documentation_agent()
