"""Software Engineer Agent Implementation using Ollama and Llama 3.2."""

import logging

import litellm
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import load_memory

from . import config as agent_config
from . import prompt
from .shared_libraries.callbacks import create_enhanced_telemetry_callbacks
from .sub_agents.code_quality.agent import code_quality_agent
from .sub_agents.code_review.agent import code_review_agent
from .sub_agents.debugging.agent import debugging_agent
from .sub_agents.design_pattern.agent import design_pattern_agent
from .sub_agents.devops.agent import devops_agent
from .sub_agents.documentation.agent import documentation_agent
from .sub_agents.ollama.agent import ollama_agent
from .sub_agents.testing.agent import testing_agent
from .tools.setup import load_all_tools_and_toolsets

# from .tools import (
#     codebase_search_tool,
#     edit_file_tool,
#     execute_shell_command_tool,
#     get_os_info_tool,
#     list_dir_tool,
#     read_file_tool,
# )

# from typing import Optional, Any, Dict, List


# from .tools.memory_tools import add_memory_fact, search_memory_facts
# from .tools.project_context import load_project_context


# litellm.turn_off_message_logging()

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
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

# Load tools synchronously (MCP tools will be loaded later if in async context)
tools = load_all_tools_and_toolsets()

# Create telemetry callbacks for observability
callbacks = create_enhanced_telemetry_callbacks("software_engineer")

# REF: https://google.github.io/adk-docs/agents/models/#ollama-integration
# Create the agent using LiteLlm wrapper for Ollama integration
root_agent = Agent(
    # model=LiteLlm(model="ollama_chat/llama3.2"),  # Use ollama_chat provider with LiteLlm
    model=LiteLlm(
        model=f"gemini/{agent_config.DEFAULT_AGENT_MODEL}"
    ),  # Use ollama_chat provider with LiteLlm
    # model="gemini-2.5-flash-preview-05-20",  # Changed from Ollama to Gemini to match sub-agents
    name="software_engineer",
    description="An AI software engineer assistant that helps with various software development tasks",
    instruction=prompt.SOFTWARE_ENGINEER_INSTR,
    sub_agents=[
        # Ordered by typical workflow dependencies
        design_pattern_agent,  # 1. Architecture and design decisions
        code_review_agent,  # 2. Code analysis and implementation guidance
        code_quality_agent,  # 3. Quality validation and improvement suggestions
        testing_agent,  # 4. Test strategy and implementation
        debugging_agent,  # 5. Issue identification and resolution
        documentation_agent,  # 6. Documentation after code stabilization
        devops_agent,  # 7. Deployment and operational considerations
        ollama_agent,  # 8. Local model sandbox environment
    ],
    tools=tools,
    # tools=[
    #     read_file_tool,
    #     list_dir_tool,
    #     edit_file_tool,
    #     execute_shell_command_tool,
    #     codebase_search_tool,
    #     get_os_info_tool,
    #     # Memory Tools
    #     load_memory,
    #     # add_memory_fact,
    #     # search_memory_facts,
    # ],
    # Add telemetry callbacks for observability
    before_agent_callback=callbacks["before_agent"],
    after_agent_callback=callbacks["after_agent"],
    before_model_callback=callbacks["before_model"],
    after_model_callback=callbacks["after_model"],
    before_tool_callback=callbacks["before_tool"],
    after_tool_callback=callbacks["after_tool"],
    # before_agent_callback=load_project_context,
    output_key="software_engineer",
)
