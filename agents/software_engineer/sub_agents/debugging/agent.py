"""Debugging Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

# from ...tools.system_info import get_os_info
from ... import config as agent_config

# Import codebase search tool from the tools module
from ...tools.code_search import codebase_search_tool
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool

# from ...tools.search import google_search_grounding
from ...tools.shell_command import execute_shell_command_tool
from . import prompt

debugging_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="debugging_agent",
    description="Agent specialized in debugging code and fixing issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        codebase_search_tool,  # Critical for understanding code context
        execute_shell_command_tool,
        # get_os_info,
        # google_search_grounding,
    ],
    output_key="debugging",
    generate_content_config=GenerateContentConfig(
        temperature=0.8,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)

# Placeholder for actual tool implementation
