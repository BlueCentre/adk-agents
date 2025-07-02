"""DevOps Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

# Import codebase search tool from the tools module
from ...tools import codebase_search_tool
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
from ...tools.search import google_search_grounding
from ...tools.shell_command import execute_vetted_shell_command_tool

# Import from the prompt module in the current directory
from . import prompt

devops_agent = LlmAgent(
    model="gemini-1.5-pro-001",
    name="devops_agent",
    description="Agent specialized in DevOps, CI/CD, deployment, and infrastructure",
    instruction=prompt.DEVOPS_AGENT_INSTR,
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        codebase_search_tool,
        execute_vetted_shell_command_tool,
        google_search_grounding,
    ],
    output_key="devops",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)

# Placeholder for actual tool implementation
