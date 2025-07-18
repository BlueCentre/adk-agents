"""Testing Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...tools import load_tools_for_sub_agent
from . import prompt

# Load tools using the selective loading approach with custom configuration
# This demonstrates how to customize the predefined profile
custom_testing_config = {
    "included_tools": [
        "google_search_grounding"
    ],  # Add search capability for testing frameworks
    "excluded_categories": [],  # Override profile to allow search tools
}

tools = load_tools_for_sub_agent(
    "testing", custom_testing_config, sub_agent_name="testing_agent"
)

testing_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="testing_agent",
    description="Agent specialized in writing and running tests",
    instruction=prompt.TESTING_AGENT_INSTR,
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        # max_output_tokens=4096,
    ),
    tools=tools,
    output_key="testing",
)
