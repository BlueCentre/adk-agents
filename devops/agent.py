"""DevOps Agent Implementation."""

import logging

from .devops_agent import MyDevopsAgent
from .tools.setup import load_core_tools_and_toolsets

from . import config as agent_config
from . import prompts as agent_prompts # Moved this import back

logger = logging.getLogger(__name__)


# devops_core_tools = load_core_tools_and_toolsets() # Moved this definition back

# Removed the MyDevopsAgent class definition
# class MyDevopsAgent(LlmAgent):
#    ...

# Create agent instance and assign to root_agent
devops_agent_instance = MyDevopsAgent(
    model=agent_config.GEMINI_MODEL_NAME,
    name="devops_agent",
    description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
    instruction=agent_prompts.DEVOPS_AGENT_INSTR,
    # tools=devops_core_tools,
    tools=load_core_tools_and_toolsets(),
    output_key="devops",
    generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
)

root_agent = devops_agent_instance
