"""Debugging Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

# from ...tools.system_info import get_os_info
from ... import config as agent_config
from ...shared_libraries.callbacks import create_telemetry_callbacks

# Import codebase search tool from the tools module
from ...tools.code_search import codebase_search_tool
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool

# from ...tools.search import google_search_grounding
from ...tools.shell_command import execute_shell_command_tool
from . import prompt

# Create telemetry callbacks for observability
callbacks = create_telemetry_callbacks("debugging_agent")

debugging_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="debugging_agent",
    description="Agent specialized in debugging code and fixing issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    generate_content_config=GenerateContentConfig(
        temperature=0.8,
        top_p=0.95,
        max_output_tokens=4096,
    ),
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        codebase_search_tool,  # Critical for understanding code context
        execute_shell_command_tool,
        # get_os_info,
        # google_search_grounding,
    ],
    # Add telemetry callbacks for observability
    before_agent_callback=callbacks["before_agent"],
    after_agent_callback=callbacks["after_agent"],
    before_model_callback=callbacks["before_model"],
    after_model_callback=callbacks["after_model"],
    before_tool_callback=callbacks["before_tool"],
    after_tool_callback=callbacks["after_tool"],
    output_key="debugging",
)
