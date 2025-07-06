"""DevOps Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

# Import from the prompt module in the current directory
from ... import config as agent_config

# Import codebase search tool from the tools module
from ...tools.code_search import codebase_search_tool
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool

# from ...tools.search import google_search_grounding
from ...tools.shell_command import execute_shell_command_tool
from . import prompt

devops_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="devops_agent",
    description="Agent specialized in DevOps, CI/CD, deployment, and infrastructure",
    instruction=prompt.DEVOPS_AGENT_INSTR,
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        codebase_search_tool,
        execute_shell_command_tool,
        # google_search_grounding,
    ],
    output_key="devops",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)

# Placeholder for actual tool implementation
