"""Testing Agent Implementation."""

from google.adk.agents import LlmAgent

# Import codebase search tool from the tools module
from ...tools import codebase_search_tool
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
from ...tools.search import google_search_grounding
from ...tools.shell_command import execute_vetted_shell_command_tool
from . import prompt

testing_agent = LlmAgent(
    model="gemini-1.5-pro-001",
    name="testing_agent",
    description="Agent specialized in writing and running tests",
    instruction=prompt.TESTING_AGENT_INSTR,
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        codebase_search_tool,
        execute_vetted_shell_command_tool,
        google_search_grounding,
    ],
    output_key="testing",
)

# Placeholder for actual tool implementation
