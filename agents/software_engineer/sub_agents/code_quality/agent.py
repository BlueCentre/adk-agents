"""Code quality agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...tools.code_analysis import (
    analyze_code_tool,
    get_analysis_issues_by_severity_tool,
    suggest_code_fixes_tool,
)
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
from . import prompt

code_quality_agent = Agent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="code_quality_agent",
    description="Analyzes code for quality issues and suggests improvements",
    instruction=prompt.CODE_QUALITY_AGENT_INSTR,
    tools=[
        analyze_code_tool,
        get_analysis_issues_by_severity_tool,
        suggest_code_fixes_tool,
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.1,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)
