"""Ollama Agent Implementation."""

from google.adk.agents import Agent

# from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# from google.adk.tools import google_search

# Import codebase search tool from the tools module
# from ...tools import codebase_search_tool
# from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
# from ...tools.search import google_search_grounding
# from ...tools.shell_command import execute_vetted_shell_command_tool
# from . import prompt

# Input schema used by both agents
# class AgentInput(BaseModel):
#     country: str = Field(description="The country to get information about.")

# Output schema ONLY for the second agent
# class CapitalInfoOutput(BaseModel):
#     capital: str = Field(description="The capital city of the country.")
#     # Note: Population is illustrative; the LLM will infer or estimate this
#     # as it cannot use tools when output_schema is set.
#     population_estimate: str = Field(description="An estimated population of the capital city.")

# REF: https://google.github.io/adk-docs/agents/models/#ollama-integration
ollama_agent = Agent(
    # model=LiteLlm(model="ollama_chat/llama3.2"),  # Use ollama_chat provider with LiteLlm
    # model=LiteLlm(model="hosted_vllm/llama3.2"),  # Use ollama_chat provider with LiteLlm
    model=LiteLlm(
        model="hosted_vllm/llama3.2",
        # messages=[
        #     {
        #     "role": "user",
        #     "content": "You are a helpful assistant. Respond in JSON format."
        #     }
        # ]
    ),
    # generate_content_config=types.GenerateContentConfig(
    #     temperature=0.2, # More deterministic output
    #     max_output_tokens=250
    # ),
    name="ollama_agent",
    description="Agent specialized in writing and running tests",
    # instruction="You are a helpful assistant. Respond in JSON format.",
    instruction="""
    Review the user's prompt and the available functions listed below.
    First, determine if calling one of these functions is the most appropriate
    way to respond. A function call is likely needed if the prompt asks for a
    specific action, requires external data lookup, or involves calculations
    handled by the functions. If the prompt is a general question or can be
    answered directly, a function call is likely NOT needed.

    If you determine a function call IS required: Respond ONLY with a JSON
    object in the format {"name": "function_name", "parameters": {"argument_name": "value"}}.
    Ensure parameter values are concrete, not variables.

    If you determine a function call IS NOT required: Respond directly to the
    user's prompt in plain text, providing the answer or information requested.
    Do not output any JSON.
    """,
    # input_schema=AgentInput,
    # output_schema=CapitalInfoOutput, # Enforce JSON output structure
    tools=[
        # google_search,
        # read_file_tool,
        # list_dir_tool,
        # edit_file_tool,
        # codebase_search_tool,
        # execute_vetted_shell_command_tool,
        # google_search_grounding,
    ],
    output_key="ollama",
)
