"""
This file is used to load the core tools and toolsets for the devops agent.
It is used in the devops_agent.py file to load the core tools and toolsets.
"""

import logging
import json
import os

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import built_in_code_execution
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .. import config as agent_config
from .. import prompts

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
    "datadog": None,
    # "filesystem": None,
    # "gitmcp-adk": None,
    # "gitmcp-genai": None,
    "playwright": None,
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

    _code_execution_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="code_execution",
        description="An agent specialized in code execution",
        instruction=prompts.CODE_EXECUTION_AGENT_INSTR,
        tools=[built_in_code_execution],
    )

    devops_observability_tools = []
    if not _loaded_mcp_toolsets["datadog"]:
        try:
            if agent_config.DATADOG_API_KEY and agent_config.DATADOG_APP_KEY:
                mcp_datadog_toolset = MCPToolset(
                    connection_params=StdioServerParameters(
                        command="npx",
                        args=["-y", "@winor30/mcp-server-datadog"],
                        env={
                            "DATADOG_API_KEY": agent_config.DATADOG_API_KEY,
                            "DATADOG_APP_KEY": agent_config.DATADOG_APP_KEY,
                        },
                    ),
                )
                _loaded_mcp_toolsets["datadog"] = mcp_datadog_toolset
                logger.info("MCP Datadog Toolset initialized successfully by setup.py.")
            else:
                logger.warning("DATADOG_API_KEY or DATADOG_APP_KEY not set in config. MCP Datadog Toolset will not be loaded.")
        except Exception as e:
            logger.warning(f"Failed to load MCP Datadog Toolset in setup.py: {e}. The Datadog tools will be unavailable.")
    
    if _loaded_mcp_toolsets["datadog"]:
        devops_observability_tools.append(_loaded_mcp_toolsets["datadog"])
    else:
        logger.info("MCP Datadog Toolset was not loaded or already loaded, not adding to observability tools again unless it's the first load.")


    _observability_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="observability",
        description="Agent specialized in Observability",
        instruction=prompts.OBSERVABILITY_AGENT_INSTR,
        tools=devops_observability_tools, # tools list will be empty if datadog isn't loaded
    )

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
        AgentTool(agent=_code_execution_agent),
        AgentTool(agent=_search_agent),
        AgentTool(agent=_observability_agent),
    ]

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

    # if not _loaded_mcp_toolsets["gitmcp-adk"]:
    #     try:
    #         mcp_gitmcp_adk_toolset = MCPToolset(
    #             connection_params=SseServerParams(
    #                 url="https://gitmcp.io/google/adk-python",
    #             ),
    #         )
    #         _loaded_mcp_toolsets["gitmcp-adk"] = mcp_gitmcp_adk_toolset
    #         logger.info("MCP GitMCP ADK Toolset initialized successfully by setup.py.")
    #     except Exception as e:
    #         logger.warning(
    #             f"Failed to load MCP GitMCP ADK Toolset in setup.py: {e}. "
    #         )

    # if _loaded_mcp_toolsets["gitmcp-adk"]:
    #     devops_core_tools_list.append(_loaded_mcp_toolsets["gitmcp-adk"])
    # else:
    #     logger.info("MCP GitMCP ADK Toolset was not loaded or already loaded, not adding to core tools list again unless it's the first load.")

    # if not _loaded_mcp_toolsets["gitmcp-genai"]:
    #     try:
    #         mcp_gitmcp_genai_toolset = MCPToolset(
    #             connection_params=SseServerParams(
    #                 url="https://gitmcp.io/googleapis/python-genai",
    #             ),
    #         )
    #         _loaded_mcp_toolsets["gitmcp-genai"] = mcp_gitmcp_genai_toolset
    #         logger.info("MCP GitMCP GenAI Toolset initialized successfully by setup.py.")
    #     except Exception as e:
    #         logger.warning(
    #             f"Failed to load MCP GitMCP GenAI Toolset in setup.py: {e}. "
    #         )
    
    # if _loaded_mcp_toolsets["gitmcp-genai"]:
    #     devops_core_tools_list.append(_loaded_mcp_toolsets["gitmcp-genai"])
    # else:
    #     logger.info("MCP GitMCP GenAI Toolset was not loaded or already loaded, not adding to core tools list again unless it's the first load.")

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

    # Load MCP toolsets from mcp.json
    try:
        with open("mcp.json", "r") as f:
            mcp_config = json.load(f)
    except FileNotFoundError:
        logger.info("mcp.json not found. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse mcp.json: {e}")
        return user_mcp_tools_list

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
                # Assume SseServerParams
                if not isinstance(processed_config.get("url"), str):
                    logger.warning(f"Failed to load MCP Toolset '{server_name}': 'url' must be a string after env var substitution.")
                    continue
                connection_params = SseServerParams(
                    url=processed_config["url"],
                )
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
                mcp_toolset = MCPToolset(
                    connection_params=connection_params,
                )
                user_mcp_tools_list.append(mcp_toolset)
                logger.info(f"MCP Toolset '{server_name}' initialized successfully by setup.py.")

        except Exception as e:
            logger.warning(f"Failed to load MCP Toolset '{server_name}' in setup.py: {e}.")

    return user_mcp_tools_list

def load_all_tools_and_toolsets():
    """Loads all core and user-defined tools and toolsets."""
    core_tools = load_core_tools_and_toolsets()
    user_tools = load_user_tools_and_toolsets()
    return core_tools + user_tools
