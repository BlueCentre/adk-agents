"""Code review agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

# from software_engineer.sub_agents.code_review.shared_libraries.types import CodeReviewResponse
from ...tools.code_analysis import analyze_code_tool
from ...tools.filesystem import list_dir_tool, read_file_tool
from . import prompt

code_review_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",  # "gemini-2.5-pro-exp-03-25", #"gemini-2.0-flash-001",
    name="code_review_agent",
    description="Analyzes code for issues and suggests improvements",
    instruction=prompt.CODE_REVIEW_AGENT_INSTR,
    tools=[analyze_code_tool, read_file_tool, list_dir_tool],
    generate_content_config=GenerateContentConfig(
        temperature=0.1,
        top_p=0.95,
        max_output_tokens=1000,
    ),
)
