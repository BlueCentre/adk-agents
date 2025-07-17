"""Code review agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...shared_libraries.callbacks import create_telemetry_callbacks

# from software_engineer.sub_agents.code_review.shared_libraries.types import CodeReviewResponse
# from ...tools.code_analysis import analyze_code_tool
# from ...tools.filesystem import list_dir_tool, read_file_tool
from ...tools.code_search import codebase_search_tool
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
from ...tools.shell_command import execute_shell_command_tool
from . import prompt

# Create telemetry callbacks for observability
callbacks = create_telemetry_callbacks("code_review_agent")

code_review_agent = Agent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="code_review_agent",
    description="Analyzes code for issues and suggests improvements",
    instruction=prompt.CODE_REVIEW_AGENT_INSTR,
    generate_content_config=GenerateContentConfig(
        temperature=0.1,
        top_p=0.95,
        max_output_tokens=1000,
    ),
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        codebase_search_tool,
        execute_shell_command_tool,
    ],
    # Add telemetry callbacks for observability
    before_agent_callback=callbacks["before_agent"],
    after_agent_callback=callbacks["after_agent"],
    before_model_callback=callbacks["before_model"],
    after_model_callback=callbacks["after_model"],
    before_tool_callback=callbacks["before_tool"],
    after_tool_callback=callbacks["after_tool"],
)
