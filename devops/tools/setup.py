"""
This file is used to load the core tools and toolsets for the devops agent.
It is used in the devops_agent.py file to load the core tools and toolsets.
"""

import logging
import json
import os
import asyncio

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .. import config as agent_config
from .. import prompts

if agent_config.ENABLE_CODE_EXECUTION:
    from google.adk.code_executors import BuiltInCodeExecutor

# Import specific tools from the current package (tools/)
from . import (
    index_directory_tool,
    retrieve_code_context_tool,
    purge_rag_index_tool,
    read_file_tool,
    list_dir_tool,
    edit_file_tool,
    codebase_search_tool,
    execute_vetted_shell_command_tool,
    check_command_exists_tool,
)
from .file_summarizer_tool import FileSummarizerTool

logger = logging.getLogger(__name__)

# Global registry for loaded MCP toolsets to prevent re-initialization
_loaded_mcp_toolsets = {
    # "datadog": None,
    # "filesystem": None,
    "playwright": None,
    # User-defined MCP servers will be added here with their names as keys
}

def load_core_tools_and_toolsets():
    """Loads and initializes all core tools, sub-agents, and MCP toolsets.
    Ensures MCP toolsets are initialized only once.
    """
    global _loaded_mcp_toolsets

    file_summarizer_tool_instance = FileSummarizerTool()

    _search_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="google_search_grounding",
        description="An agent providing Google-search grounding capability",
        instruction=prompts.SEARCH_AGENT_INSTR,
        tools=[google_search],
    )

    # A code executor that uses the Model's built-in code executor.
    # Currently only supports Gemini 2.0+ models, but will be expanded to
    # other models.
    if agent_config.ENABLE_CODE_EXECUTION:
        _code_execution_agent = LlmAgent(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name="code_execution",
            description="An agent specialized in code execution",
            instruction=prompts.CODE_EXECUTION_AGENT_INSTR,
            code_executor=[BuiltInCodeExecutor],
        )

    # devops_observability_tools = []
    # if not _loaded_mcp_toolsets["datadog"]:
    #     try:
    #         if agent_config.DATADOG_API_KEY and agent_config.DATADOG_APP_KEY:
    #             mcp_datadog_toolset = MCPToolset(
    #                 connection_params=StdioServerParameters(
    #                     command="npx",
    #                     args=["-y", "@winor30/mcp-server-datadog"],
    #                     env={
    #                         "DATADOG_API_KEY": agent_config.DATADOG_API_KEY,
    #                         "DATADOG_APP_KEY": agent_config.DATADOG_APP_KEY,
    #                     },
    #                 ),
    #             )
    #             _loaded_mcp_toolsets["datadog"] = mcp_datadog_toolset
    #             logger.info("MCP Datadog Toolset initialized successfully by setup.py.")
    #         else:
    #             logger.warning("DATADOG_API_KEY or DATADOG_APP_KEY not set in config. MCP Datadog Toolset will not be loaded.")
    #     except Exception as e:
    #         logger.warning(f"Failed to load MCP Datadog Toolset in setup.py: {e}. The Datadog tools will be unavailable.")
    
    # if _loaded_mcp_toolsets["datadog"]:
    #     devops_observability_tools.append(_loaded_mcp_toolsets["datadog"])
    # else:
    #     logger.info("MCP Datadog Toolset was not loaded or already loaded, not adding to observability tools again unless it's the first load.")


    # _observability_agent = LlmAgent(
    #     model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    #     name="observability",
    #     description="Agent specialized in Observability",
    #     instruction=prompts.OBSERVABILITY_AGENT_INSTR,
    #     tools=devops_observability_tools, # tools list will be empty if datadog isn't loaded
    # )

    devops_core_tools_list = [
        index_directory_tool,
        retrieve_code_context_tool,
        purge_rag_index_tool,
        list_dir_tool,
        read_file_tool,
        edit_file_tool,
        file_summarizer_tool_instance,
        codebase_search_tool,
        check_command_exists_tool,
        execute_vetted_shell_command_tool,
        AgentTool(agent=_search_agent),
        # AgentTool(agent=_observability_agent),
    ]

    if agent_config.ENABLE_CODE_EXECUTION:
        devops_core_tools_list.append(AgentTool(agent=_code_execution_agent))

    # if not _loaded_mcp_toolsets["filesystem"]:
    #     try:
    #         mcp_filesystem_toolset = MCPToolset(
    #             connection_params=StdioServerParameters(
    #                 command="rust-mcp-filesystem",
    #                 args=["--allow-write", *agent_config.MCP_ALLOWED_DIRECTORIES],
    #             ),
    #         )
    #         _loaded_mcp_toolsets["filesystem"] = mcp_filesystem_toolset
    #         logger.info("MCP Filesystem Toolset initialized successfully by setup.py.")
    #     except Exception as e:
    #         logger.warning(
    #             f"Failed to load MCP Filesystem Toolset in setup.py: {e}. "
    #             "DevOps agent will fallback to using the built-in file system tools."
    #         )
    
    # if _loaded_mcp_toolsets["filesystem"]:
    #     devops_core_tools_list.append(_loaded_mcp_toolsets["filesystem"])
    # else:
    #     logger.info("MCP Filesystem Toolset was not loaded or already loaded, not adding to core tools list again unless it's the first load.")

    if agent_config.MCP_PLAYWRIGHT_ENABLED:
        if not _loaded_mcp_toolsets["playwright"]:
            try:
                mcp_playwright_toolset = MCPToolset(
                    connection_params=StdioServerParameters(
                        command="npx",
                        args=[
                            "@playwright/mcp@latest",
                            # To use a specific Chrome profile, add:
                            # "--user-data-dir=/path/to/your/chrome/profile",
                            # Or for Firefox:
                            # "--browser=firefox", 
                            # "--user-data-dir=/path/to/your/firefox/profile",
                            # Ensure the path is correct and the Playwright server has permissions.
                            # Persistent profiles are default. For isolated sessions, add "--isolated".
                            # See https://github.com/microsoft/playwright-mcp for more options.
                        ],
                    ),
                )
                _loaded_mcp_toolsets["playwright"] = mcp_playwright_toolset
                logger.info("MCP Playwright Toolset initialized successfully by setup.py.")
            except Exception as e:
                logger.warning(
                    f"Failed to load MCP Playwright Toolset in setup.py: {e}. "
                    "Playwright tools will be unavailable."
                )

        if _loaded_mcp_toolsets["playwright"]:
            devops_core_tools_list.append(_loaded_mcp_toolsets["playwright"])
        else:
            # This case (Playwright enabled but not loaded due to an error, or already loaded)
            logger.info("MCP Playwright Toolset is enabled but was not loaded (possibly due to an error on first attempt or already loaded).")
    else:
        logger.info("MCP Playwright Toolset is disabled via config in setup.py.")
    return devops_core_tools_list

# Example from:
# - https://www.marktechpost.com/2025/04/29/how-to-create-a-custom-model-context-protocol-mcp-client-using-gemini/
# - https://github.com/mohd-arham-islam/geminiClient/blob/main/client.py
# def clean_schema(schema):
#     """Cleans the schema by keeping only allowed keys"""
#     allowed_keys = {"type", "properties", "required", "description", "title", "default", "enum"}
#     return {k: v for k, v in schema.items() if k in allowed_keys}

def load_user_tools_and_toolsets():
    """Loads and initializes all user tools, sub-agents, and MCP toolsets.
    Ensures MCP toolsets are initialized only once. Use MCP to load user tools,
    by adding the mcpServers section to the mcp.json file.
    Example mcp.json file:
    {
        "mcpServers": {
            "sonarqube": {
                "command": "npx",
                "args": [
                    "-y",
                    "sonarqube-mcp-server@1.0.0"
                ],
                "env": {
                    "SONARQUBE_URL": "https://sonarcloud.io",
                    "SONARQUBE_TOKEN": "{{env.SONAR_TOKEN}}",
                    "SONARQUBE_ORGANIZATION": "{{env.SONAR_ORGANIZATION}}"
                }
            },
            "gitmcp-adk": {
                "url": "https://gitmcp.io/BlueCentre/adk-agents"
            }
        }
    }
    """
    global _loaded_mcp_toolsets

    def _substitute_env_vars(value):
        """Recursively substitutes {{env.VAR_NAME}} placeholders with environment variable values."""
        if isinstance(value, str):
            import re
            match = re.search(r"{{env\.([^}]+)}}", value)
            if match:
                var_name = match.group(1)
                env_value = os.environ.get(var_name)
                if env_value is not None:
                    # Simple substitution for now, assumes the whole string is the placeholder
                    if value == f"{{{{env.{var_name}}}}}":
                        return env_value
                    # More complex substitution (e.g., part of a string)
                    # This requires more sophisticated regex and handling, skipping for simplicity now.
                    # return value.replace(f'{{{{env.{var_name}}}}}', env_value)
                    else:
                        logger.warning(f"Environment variable placeholder '{match.group(0)}' found within a string. Full string substitution is not supported. Skipping substitution.")
                        return value
                else:
                    logger.warning(f"Environment variable '{var_name}' not found. Could not substitute placeholder '{match.group(0)}'.")
                    return ""
            return value
        elif isinstance(value, list):
            return [_substitute_env_vars(item) for item in value]
        elif isinstance(value, dict):
            return {k: _substitute_env_vars(v) for k, v in value.items()}
        else:
            return value

    user_mcp_tools_list = []
    mcp_config_path = os.path.join(os.getcwd(), "mcp.json") # TODO: Make this configurable or discoverable

    # Initialize _loaded_mcp_toolsets if it's None (e.g., first call)
    # This check might be redundant if it's always initialized globally, but good for safety.
    if _loaded_mcp_toolsets is None:
        _loaded_mcp_toolsets = {}

    if not os.path.exists(mcp_config_path):
        logger.info("mcp.json not found. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list

    with open(mcp_config_path, "r") as f:
        mcp_config = json.load(f)

    servers = mcp_config.get('mcpServers', {})
    if not servers:
        logger.info("No 'mcpServers' found in mcp.json. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list

    server_names = list(servers.keys())
    logger.info("Available MCP servers:")
    for idx, name in enumerate(server_names):
        logger.info(f"  {idx+1}. {name}")

    # Load MCP toolsets from mcp.json
    for server_name, server_config in servers.items():
        try:
            # Substitute environment variables in the server configuration
            processed_config = _substitute_env_vars(server_config)

            connection_params = None
            if "url" in processed_config:
                # Assume SseServerParams for URL-based servers
                if not isinstance(processed_config.get("url"), str):
                    logger.warning(f"Failed to load MCP Toolset \'{server_name}\': \'url\' must be a string after env var substitution.")
                    continue
                connection_params = SseServerParams(url=processed_config["url"])
            elif "command" in processed_config and "args" in processed_config:
                # Assume StdioServerParameters
                if not isinstance(processed_config.get("command"), str):
                    logger.warning(f"Failed to load MCP Toolset '{server_name}': 'command' must be a string after env var substitution.")
                    continue
                if not isinstance(processed_config.get("args"), list):
                    logger.warning(f"Failed to load MCP Toolset '{server_name}': 'args' must be a list after env var substitution.")
                    continue

                # Ensure command and args are lists of strings after substitution
                processed_args = []
                for arg in processed_config["args"]:
                    if not isinstance(arg, str):
                        logger.warning(f"Failed to load MCP Toolset '{server_name}': Argument '{arg}' in 'args' is not a string after env var substitution. Skipping toolset.")
                        processed_args = None # Indicate failure for this toolset
                        break
                    processed_args.append(arg)
                
                if processed_args is None:
                    continue # Skip this toolset due to invalid args

                processed_env = processed_config.get("env", {})
                # Ensure env values are strings after substitution
                for key, value in processed_env.items():
                    if not isinstance(value, str):
                        logger.warning(f"Failed to load MCP Toolset '{server_name}': Environment variable value for '{key}' is not a string after env var substitution. Converting to string.")
                        processed_env[key] = str(value)

                connection_params = StdioServerParameters(
                    command=processed_config["command"],
                    args=processed_args,
                    env=processed_env,
                )
            else:
                logger.warning(f"Failed to load MCP Toolset '{server_name}': Configuration must contain either 'url' or 'command' and 'args'.")
                continue

            if connection_params:
                # Check if this server_name is already in _loaded_mcp_toolsets (e.g. from core tools)
                if server_name in _loaded_mcp_toolsets and _loaded_mcp_toolsets[server_name] is not None:
                    logger.info(f"MCP Toolset '{server_name}' already loaded (likely as a core tool). Adding existing instance to user tools list.")
                    # Add the existing instance to the list if it's not already there by reference
                    # This check might be overly cautious depending on how lists are built
                    if _loaded_mcp_toolsets[server_name] not in user_mcp_tools_list:
                        user_mcp_tools_list.append(_loaded_mcp_toolsets[server_name])
                    continue # Skip re-initialization

                mcp_toolset = MCPToolset(
                    connection_params=connection_params,
                    # Optionally, you can pass a name to MCPToolset if its constructor supports it
                    # name=server_name 
                )
                user_mcp_tools_list.append(mcp_toolset)
                _loaded_mcp_toolsets[server_name] = mcp_toolset # Store in global registry
                logger.info(f"MCP Toolset '{server_name}' initialized successfully by setup.py and added to user tools.")

        except Exception as e:
            logger.warning(f"Failed to load MCP Toolset '{server_name}' in setup.py: {e}.")

    return user_mcp_tools_list

def load_all_tools_and_toolsets():
    """Loads all core and user-defined tools and toolsets."""
    core_tools = load_core_tools_and_toolsets()
    user_tools = load_user_tools_and_toolsets()
    return core_tools + user_tools

# IMPORTANT NOTE ON CLEANUP:
# The `cleanup_mcp_toolsets` coroutine below is designed to properly close
# the resources (like subprocesses and network connections) used by MCP toolsets.
# However, due to potential limitations in how the ADK runner or main application
# handles task cancellation during shutdown (e.g., on KeyboardInterrupt), 
# awaiting this cleanup function from a cancellable task (like the agent's main run loop)
# may itself be interrupted, potentially leading to errors like
# "RuntimeError: Attempted to exit cancel scope in a different task than it was entered in".
#
# For a truly clean exit, the application running this agent should ideally
# call and await `cleanup_mcp_toolsets()` from a non-cancellable context
# during its shutdown sequence, or ensure that any cancellation allows
# sufficient time and context for cleanup tasks to complete.
# If running with a standard ADK runner that exhibits this issue, a perfectly
# clean shutdown free of this specific error might not be achievable from
# within the agent's code itself.

async def cleanup_mcp_toolsets():
    """Iterates through loaded MCP toolsets and calls their close() method."""
    logger.info("Starting cleanup of MCP toolsets...")
    for toolset_name, toolset_instance in list(_loaded_mcp_toolsets.items()): # Iterate on a copy
        if toolset_instance and hasattr(toolset_instance, 'close') and callable(toolset_instance.close):
            try:
                if asyncio.iscoroutinefunction(toolset_instance.close):
                    logger.info(f"Asynchronously closing MCP Toolset: {toolset_name}")
                    await toolset_instance.close()
                else:
                    logger.info(f"Synchronously closing MCP Toolset: {toolset_name} (if it blocks, this might be an issue)")
                    toolset_instance.close() # type: ignore
                logger.info(f"Successfully closed MCP Toolset: {toolset_name}")
            except Exception as e:
                logger.error(f"Error closing MCP Toolset {toolset_name}: {e}", exc_info=True)
            finally:
                # Optionally remove from dict or mark as closed
                _loaded_mcp_toolsets[toolset_name] = None # Mark as closed or remove
        elif toolset_instance:
            logger.warning(f"MCP Toolset {toolset_name} does not have a callable 'close' method.")
        # If toolset_instance is None, it was either never loaded or already cleaned up
    logger.info("Finished cleanup of MCP toolsets.")
