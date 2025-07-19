"""Ollama Agent Implementation."""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# Import tools from the parent tools module
from ...tools.filesystem import edit_file_tool, list_dir_tool, read_file_tool
from ...tools.shell_command import execute_shell_command_tool
from . import prompt

# from ...tools.code_search import codebase_search_tool


def create_ollama_agent(name_suffix=""):
    """Factory function to create ollama agent instances.

    Args:
        name_suffix: Optional suffix to append to agent name (e.g., "enhanced_")

    Returns:
        Agent: Configured ollama agent instance
    """
    agent_name = f"{name_suffix}ollama_agent" if name_suffix else "ollama_agent"

    # REF: https://google.github.io/adk-docs/agents/models/#ollama-integration
    return Agent(
        # model=LiteLlm(model="ollama_chat/llama3.2"),  # Use ollama_chat provider with LiteLlm
        # model=LiteLlm(model="hosted_vllm/llama3.2"),  # Use ollama_chat provider with LiteLlm
        model=LiteLlm(
            model="hosted_vllm/llama3.2",
        ),
        # generate_content_config=types.GenerateContentConfig(
        #     temperature=0.2, # More deterministic output
        #     max_output_tokens=250
        # ),
        name=agent_name,
        description="Agent that runs local ollama models in sandboxed environment",
        instruction=prompt.OLLAMA_AGENT_INSTR,
        tools=[
            read_file_tool,
            list_dir_tool,
            edit_file_tool,
            # codebase_search_tool,
            execute_shell_command_tool,
        ],
        output_key="ollama",
    )


# Create the default instance for backward compatibility
ollama_agent = create_ollama_agent()
