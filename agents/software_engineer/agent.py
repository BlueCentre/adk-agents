"""Software Engineer Agent Implementation using Ollama and Llama 3.2."""

import logging

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import load_memory

from . import prompt
from .sub_agents.code_quality.agent import code_quality_agent

# from .sub_agents.code_review.agent import code_review_agent
# from .sub_agents.debugging.agent import debugging_agent
# from .sub_agents.design_pattern.agent import design_pattern_agent
# from .sub_agents.devops.agent import devops_agent
# from .sub_agents.documentation.agent import documentation_agent
# from .sub_agents.testing.agent import testing_agent
from .tools import (
    codebase_search_tool,
    edit_file_tool,
    execute_shell_command_tool,
    get_os_info_tool,
    list_dir_tool,
    read_file_tool,
)

# from typing import Optional, Any, Dict, List


# from .tools.memory_tools import add_memory_fact, search_memory_facts
# from .tools.project_context import load_project_context

logger = logging.getLogger(__name__)


# def initialize_session_memory(tool_context):
#     """Initialize session memory in tool_context if it doesn't exist."""
#     if not hasattr(tool_context, "session_state"):
#         logger.warning("Tool context does not have session_state. Cannot initialize memory.")
#         return

#     if "memory" not in tool_context.session_state:
#         logger.info("Initializing agent session memory.")
#         tool_context.session_state["memory"] = {
#             "context": {
#                 "project_path": None,
#                 "current_file": None,
#             },
#             "tasks": {
#                 "active_task": None,
#                 "completed_tasks": [],
#             },
#             "history": {
#                 "last_read_file": None,
#                 "last_search_query": None,
#                 "last_error": None,
#             },
#             "user_preferences": {},
#         }


# REF: https://google.github.io/adk-docs/agents/models/#ollama-integration
# Create the agent using LiteLlm wrapper for Ollama integration
root_agent = Agent(
    model=LiteLlm(model="ollama_chat/llama3.2"),  # Use ollama_chat provider with LiteLlm
    name="software_engineer",
    description="An AI software engineer assistant that helps with various software development tasks",
    instruction=prompt.SOFTWARE_ENGINEER_INSTR,
    sub_agents=[
        # design_pattern_agent,
        # documentation_agent,
        # code_review_agent,
        code_quality_agent,
        # testing_agent,
        # debugging_agent,
        # devops_agent,  # TODO: Move command tools to devops_agent with more guardrails
    ],
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        execute_shell_command_tool,
        codebase_search_tool,
        get_os_info_tool,
        # Memory Tools
        load_memory,
        # add_memory_fact,
        # search_memory_facts,
    ],
    # before_agent_callback=load_project_context,
    output_key="software_engineer",
)
