"""DevOps Agent Implementation."""

import logging

from .devops_agent import MyDevopsAgent
from .tools.setup import load_all_tools_and_toolsets

from . import config as agent_config
from . import prompts as agent_prompts

logger = logging.getLogger(__name__)


# Create agent instance using the MyDevopsAgent abstraction
devops_agent_instance = MyDevopsAgent(
    model=agent_config.GEMINI_MODEL_NAME,
    name="devops_agent",
    description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
    instruction=agent_prompts.DEVOPS_AGENT_INSTR,
    generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
    tools=load_all_tools_and_toolsets(),
    output_key="devops",
)

# Comment out if this will be used as a sub-agent
root_agent = devops_agent_instance
