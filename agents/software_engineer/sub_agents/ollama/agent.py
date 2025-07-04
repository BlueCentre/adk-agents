"""Ollama Agent Implementation."""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# Import tools from the parent tools module
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
from ...tools.shell_command import execute_shell_command_tool

# from ...tools.code_search import codebase_search_tool


# REF: https://google.github.io/adk-docs/agents/models/#ollama-integration
ollama_agent = Agent(
    # model=LiteLlm(model="ollama_chat/llama3.2"),  # Use ollama_chat provider with LiteLlm
    # model=LiteLlm(model="hosted_vllm/llama3.2"),  # Use ollama_chat provider with LiteLlm
    model=LiteLlm(
        model="hosted_vllm/llama3.2",
    ),
    # generate_content_config=types.GenerateContentConfig(
    #     temperature=0.2, # More deterministic output
    #     max_output_tokens=250
    # ),
    name="ollama_agent",
    description="Agent that runs local ollama models in sandboxed environment",
    instruction="""You are a helpful development assistant. 

For general questions, conversations, or when providing information, respond directly in clear, readable text using markdown formatting when helpful.

Only use function calls when you need to:
- Read or edit files
- Search through code
- Execute shell commands
- Perform specific actions that require tools

When you do need to call a function, respond with the appropriate JSON format for the function call.

Be helpful, concise, and focus on providing practical development assistance.""",
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        # codebase_search_tool,
        execute_shell_command_tool,
    ],
    output_key="ollama",
)
