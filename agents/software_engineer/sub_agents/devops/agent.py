"""DevOps Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...tools import load_tools_for_sub_agent
from . import prompt

# Load tools using the profile-based loading with per-sub-agent MCP configuration
# This uses the new per-sub-agent MCP tool loading system
custom_devops_config = {
    "included_categories": ["filesystem", "shell_command", "system_info"],
    "included_tools": ["codebase_search_tool"],
    "excluded_tools": ["analyze_code_tool"],  # DevOps agent doesn't need code analysis
    "include_mcp_tools": True,
    "mcp_server_filter": [
        "filesystem",
        "docker",
        "kubernetes",
    ],  # Only specific MCP tools
}

tools = load_tools_for_sub_agent(
    "devops", custom_devops_config, sub_agent_name="devops_agent"
)

devops_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="devops_agent",
    description="Agent specialized in DevOps, CI/CD, deployment, and infrastructure",
    instruction=prompt.DEVOPS_AGENT_INSTR,
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=4096,
    ),
    tools=tools,
    output_key="devops",
)
