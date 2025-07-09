"""
This file is used to load the core tools and toolsets for the devops agent.
It is used in the devops_agent.py file to load the core tools and toolsets.
"""

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseConnectionParams,
    StdioServerParameters,
)

from .. import config as agent_config
from .. import prompts

if agent_config.ENABLE_CODE_EXECUTION:
    from google.adk.code_executors import BuiltInCodeExecutor

# Import specific tools from the current package (tools/)
from . import (
    check_command_exists_tool,
    codebase_search_tool,
    execute_vetted_shell_command_tool,
    index_directory_tool,
    purge_rag_index_tool,
    retrieve_code_context_tool,
)
from .code_analysis import (
    analyze_code_tool,
    get_analysis_issues_by_severity_tool,
    suggest_code_fixes_tool,
)
from .file_summarizer_tool import FileSummarizerTool
from .persistent_memory_tool import load_memory_from_file_tool, save_current_session_to_file_tool
from .rag_tools import index_directory_tool, purge_rag_index_tool, retrieve_code_context_tool
from .search import google_search_grounding
from .shell_command import check_command_exists_tool, execute_vetted_shell_command_tool

logger = logging.getLogger(__name__)

# Global registry for MCP toolsets and their exit stacks
# Following ADK documentation pattern for proper async lifecycle management
_loaded_mcp_toolsets = {}
_global_mcp_exit_stack = None

def load_core_tools_and_toolsets():
    """Loads and initializes all core tools, sub-agents, and MCP toolsets."""
    devops_core_tools_list = [
        index_directory_tool,
        retrieve_code_context_tool,
        purge_rag_index_tool,
        codebase_search_tool,
        check_command_exists_tool,
        execute_vetted_shell_command_tool,
    ]

    file_summarizer_tool_instance = FileSummarizerTool()
    devops_core_tools_list.append(file_summarizer_tool_instance)

    # https://google.github.io/adk-docs/tools/built-in-tools/#limitations
    _search_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="google_search_grounding",
        description="An agent providing Google-search grounding capability",
        instruction=prompts.SEARCH_AGENT_INSTR,
        tools=[google_search],
    )
    devops_core_tools_list.append(AgentTool(agent=_search_agent))

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
        devops_core_tools_list.append(AgentTool(agent=_code_execution_agent))

    return devops_core_tools_list

async def load_user_tools_and_toolsets_async():
    """Loads and initializes user-defined MCP toolsets using the best available pattern.
    
    Automatically suppresses startup output from MCP servers to prevent noise in CLI.
    Output suppression is applied to:
    - Known noisy servers: filesystem, memory
    - All npx-based servers (which often output startup messages)
    - Servers with filesystem/memory patterns in their arguments
    - Servers explicitly marked with "suppress_output": true in mcp.json
    
    Returns:
        tuple: (user_mcp_tools_list, exit_stack_or_none)
    """
    global _loaded_mcp_toolsets, _global_mcp_exit_stack
    
    def _substitute_env_vars(value):
        """Recursively substitutes {{env.VAR_NAME}} placeholders with environment variable values."""
        if isinstance(value, str):
            import re
            match = re.search(r"{{env\.([^}]+)}}", value)
            if match:
                var_name = match.group(1)
                env_value = os.environ.get(var_name)
                if env_value is not None:
                    if value == f"{{{{env.{var_name}}}}}":
                        return env_value
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
    mcp_config_path = os.path.join(os.getcwd(), ".agent/mcp.json")

    # Initialize _loaded_mcp_toolsets if it's None
    if _loaded_mcp_toolsets is None:
        _loaded_mcp_toolsets = {}

    # Check if MCPToolset.from_server is available (latest ADK)
    has_from_server = hasattr(MCPToolset, 'from_server') and callable(getattr(MCPToolset, 'from_server'))
    
    if has_from_server:
        logger.info("Latest ADK detected: Using async pattern with MCPToolset.from_server()")
        # Initialize global exit stack if not already done
        if _global_mcp_exit_stack is None:
            _global_mcp_exit_stack = AsyncExitStack()
    else:
        logger.info("Older ADK detected: Using simple pattern with MCPToolset()")

    if not os.path.exists(mcp_config_path):
        logger.info("mcp.json not found. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list, _global_mcp_exit_stack if has_from_server else None

    with open(mcp_config_path, "r") as f:
        mcp_config = json.load(f)

    servers = mcp_config.get('mcpServers', {})
    if not servers:
        logger.info("No 'mcpServers' found in mcp.json. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list, _global_mcp_exit_stack if has_from_server else None

    # Load MCP toolsets from mcp.json using the best available pattern
    for server_name, server_config in servers.items():
        try:
            # Substitute environment variables in the server configuration
            processed_config = _substitute_env_vars(server_config)

            connection_params = None
            if "url" in processed_config:
                if not isinstance(processed_config.get("url"), str):
                    logger.warning(f"Failed to load MCP Toolset '{server_name}': 'url' must be a string after env var substitution.")
                    continue
                connection_params = SseConnectionParams(url=processed_config["url"])
            elif "command" in processed_config and "args" in processed_config:
                if not isinstance(processed_config.get("command"), str):
                    logger.warning(f"Failed to load MCP Toolset '{server_name}': 'command' must be a string after env var substitution.")
                    continue
                if not isinstance(processed_config.get("args"), list):
                    logger.warning(f"Failed to load MCP Toolset '{server_name}': 'args' must be a list after env var substitution.")
                    continue

                processed_args = []
                for arg in processed_config["args"]:
                    if not isinstance(arg, str):
                        logger.warning(f"Failed to load MCP Toolset '{server_name}': Argument '{arg}' in 'args' is not a string after env var substitution. Skipping toolset.")
                        processed_args = None
                        break
                    processed_args.append(arg)
                
                if processed_args is None:
                    continue

                # Check if this MCP server should have output suppressed
                # This handles servers that output startup messages to stderr/stdout
                should_suppress_output = (
                    # Known noisy servers
                    server_name in ['filesystem', 'memory'] or
                    # Servers using npx (often output startup messages)
                    processed_config["command"] == "npx" or
                    # Servers with specific patterns in their args that tend to be noisy
                    any('server-filesystem' in str(arg) for arg in processed_args) or
                    any('server-memory' in str(arg) for arg in processed_args) or
                    # Allow user to explicitly mark servers as quiet in config
                    processed_config.get("suppress_output", False)
                )
                
                if should_suppress_output:
                    # Add shell redirection to suppress startup messages
                    original_command = processed_config["command"]
                    original_args = processed_args
                    
                    # Use shell redirection to suppress stderr (where most startup messages go)
                    processed_config["command"] = "sh"
                    processed_args = [
                        "-c", 
                        f"{original_command} {' '.join(original_args)} 2>/dev/null"
                    ]

                processed_env = processed_config.get("env", {})
                for key, value in processed_env.items():
                    if not isinstance(value, str):
                        logger.warning(f"Failed to load MCP Toolset '{server_name}': Environment variable value for '{key}' is not a string after env var substitution. Converting to string.")
                        processed_env[key] = str(value)

                # Add environment variables to suppress MCP server startup messages
                mcp_quiet_env = {
                    # General output suppression
                    'QUIET': '1',
                    'SILENT': '1',
                    'NO_BANNER': '1',
                    'NO_STARTUP_MESSAGE': '1',
                    # Logging suppression
                    'LOG_LEVEL': 'ERROR',
                    'MCP_LOG_LEVEL': 'ERROR',
                    'RUST_LOG': 'error',
                    'NODE_ENV': 'production',
                    # Disable colors and formatting
                    'NO_COLOR': '1',
                    'FORCE_COLOR': '0',
                    # Python specific
                    'PYTHONIOENCODING': 'utf-8',
                    'PYTHONUNBUFFERED': '0',
                    **processed_env  # User env vars override our defaults
                }

                connection_params = StdioServerParameters(
                    command=processed_config["command"],
                    args=processed_args,
                    env=mcp_quiet_env,
                )
            else:
                logger.warning(f"Failed to load MCP Toolset '{server_name}': Configuration must contain either 'url' or 'command' and 'args'.")
                continue

            if connection_params:
                # Check if this server_name is already in _loaded_mcp_toolsets
                if server_name in _loaded_mcp_toolsets and _loaded_mcp_toolsets[server_name] is not None:
                    logger.info(f"MCP Toolset '{server_name}' already loaded. Adding existing instance to user tools list.")
                    existing_tools = _loaded_mcp_toolsets[server_name]
                    if isinstance(existing_tools, list):
                        user_mcp_tools_list.extend(existing_tools)
                    else:
                        user_mcp_tools_list.append(existing_tools)
                    continue

                # Try the appropriate pattern based on ADK version
                if has_from_server:
                    # Use the proper async pattern as documented by ADK
                    logger.info(f"Loading MCP Toolset '{server_name}' using async pattern with from_server()...")
                    
                    try:
                        # This is the recommended pattern from ADK documentation
                        tools, exit_stack = await MCPToolset.from_server(
                            connection_params=connection_params
                        )
                        
                        # Register the exit stack with our global exit stack for proper cleanup
                        await _global_mcp_exit_stack.enter_async_context(exit_stack)
                        
                        # Add tools to our list (MCPToolset.from_server returns a list of tools)
                        user_mcp_tools_list.extend(tools)
                        _loaded_mcp_toolsets[server_name] = tools
                        
                        logger.info(f"MCP Toolset '{server_name}' initialized successfully using async pattern. Loaded {len(tools)} tools.")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load MCP Toolset '{server_name}' using async pattern: {e}")
                        continue
                else:
                    # Use the simple MCPToolset pattern compatible with older ADK versions
                    logger.info(f"Loading MCP Toolset '{server_name}' using simple pattern...")
                    
                    try:
                        mcp_toolset = MCPToolset(connection_params=connection_params)
                        user_mcp_tools_list.append(mcp_toolset)
                        _loaded_mcp_toolsets[server_name] = mcp_toolset
                        logger.info(f"MCP Toolset '{server_name}' initialized successfully using simple pattern.")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load MCP Toolset '{server_name}' using simple pattern: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Failed to load MCP Toolset '{server_name}': {e}")

    return user_mcp_tools_list, _global_mcp_exit_stack if has_from_server else None

def load_user_tools_and_toolsets():
    """Synchronous wrapper for loading user MCP toolsets.
    
    This handles the async context issue by deferring MCP loading to when
    the agent actually runs, which is compatible with the ADK framework.
    """
    user_mcp_tools_list = []
    mcp_config_path = os.path.join(os.getcwd(), ".agent/mcp.json")

    if not os.path.exists(mcp_config_path):
        logger.info("mcp.json not found. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list

    with open(mcp_config_path, "r") as f:
        mcp_config = json.load(f)

    servers = mcp_config.get('mcpServers', {})
    if not servers:
        logger.info("No 'mcpServers' found in mcp.json. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list

    logger.info(f"Found {len(servers)} MCP servers in mcp.json. Attempting to load them...")

    # Check if MCPToolset.from_server is available (latest ADK)
    has_from_server = hasattr(MCPToolset, 'from_server') and callable(getattr(MCPToolset, 'from_server'))
    
    # Always use the async pattern if available, regardless of context
    # This ensures consistent cleanup behavior
    if has_from_server:
        try:
            # Always use the async pattern with proper exit stack management
            # This ensures the ADK Runner can properly cleanup MCP toolsets
            logger.info("Loading MCP toolsets using async pattern with proper exit stack management...")
            tools, exit_stack = asyncio.run(load_user_tools_and_toolsets_async())
            global _global_mcp_exit_stack
            _global_mcp_exit_stack = exit_stack
            user_mcp_tools_list.extend(tools)
            logger.info(f"MCP toolsets loaded using async pattern. Total: {len(tools)} tools.")
            
        except Exception as e:
            logger.warning(f"Failed to load MCP toolsets using async pattern: {e}")
            logger.info("Falling back to simple pattern...")
            # Fallback to simple pattern if async pattern fails
            user_mcp_tools_list = _load_mcp_tools_simple_pattern(servers)
    else:
        # Use simple pattern for older ADK versions
        logger.info("Using simple pattern for older ADK version...")
        user_mcp_tools_list = _load_mcp_tools_simple_pattern(servers)

    return user_mcp_tools_list


def _load_mcp_tools_simple_pattern(servers):
    """Load MCP tools using the simple pattern for fallback or older ADK versions."""
    user_mcp_tools_list = []
    
    for server_name, server_config in servers.items():
        try:
            # Process config and create connection params
            processed_config = _substitute_env_vars(server_config)
            connection_params = _create_connection_params(server_name, processed_config)

            if connection_params:
                # Use simple MCPToolset pattern
                mcp_toolset = MCPToolset(connection_params=connection_params)
                user_mcp_tools_list.append(mcp_toolset)
                logger.info(f"MCP Toolset '{server_name}' loaded successfully using simple pattern.")

        except Exception as e:
            logger.warning(f"Failed to load MCP Toolset '{server_name}': {e}")
            continue
    
    logger.info(f"MCP toolsets loaded using simple pattern. Total: {len(user_mcp_tools_list)} tools.")
    return user_mcp_tools_list


def _substitute_env_vars(value):
    """Recursively substitutes {{env.VAR_NAME}} placeholders with environment variable values."""
    if isinstance(value, str):
        import re
        match = re.search(r"{{env\.([^}]+)}}", value)
        if match:
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            if env_value is not None:
                if value == f"{{{{env.{var_name}}}}}":
                    return env_value
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


def _create_connection_params(server_name, processed_config):
    """Create connection parameters for an MCP server."""
    connection_params = None

    if "url" in processed_config:
        if not isinstance(processed_config.get("url"), str):
            logger.warning(f"Failed to load MCP Toolset '{server_name}': 'url' must be a string after env var substitution.")
            return None
        connection_params = SseConnectionParams(url=processed_config["url"])

    elif "command" in processed_config and "args" in processed_config:
        if not isinstance(processed_config.get("command"), str):
            logger.warning(f"Failed to load MCP Toolset '{server_name}': 'command' must be a string after env var substitution.")
            return None
        if not isinstance(processed_config.get("args"), list):
            logger.warning(f"Failed to load MCP Toolset '{server_name}': 'args' must be a list after env var substitution.")
            return None

        processed_args = []
        for arg in processed_config["args"]:
            if not isinstance(arg, str):
                logger.warning(f"Failed to load MCP Toolset '{server_name}': Argument '{arg}' in 'args' is not a string after env var substitution. Skipping toolset.")
                return None
            processed_args.append(arg)

        # Check if this MCP server should have output suppressed
        should_suppress_output = (
            server_name in ['filesystem', 'memory'] or
            processed_config["command"] == "npx" or
            any('server-filesystem' in str(arg) for arg in processed_args) or
            any('server-memory' in str(arg) for arg in processed_args) or
            processed_config.get("suppress_output", False)
        )

        if should_suppress_output:
            # Add shell redirection to suppress startup messages
            original_command = processed_config["command"]
            original_args = processed_args
            processed_config["command"] = "sh"
            processed_args = ["-c", f"{original_command} {' '.join(original_args)} 2>/dev/null"]

        processed_env = processed_config.get("env", {})
        for key, value in processed_env.items():
            if not isinstance(value, str):
                logger.warning(f"Failed to load MCP Toolset '{server_name}': Environment variable value for '{key}' is not a string after env var substitution. Converting to string.")
                processed_env[key] = str(value)

        # Add environment variables to suppress MCP server startup messages
        mcp_quiet_env = {
            'QUIET': '1', 'SILENT': '1', 'NO_BANNER': '1', 'NO_STARTUP_MESSAGE': '1',
            'LOG_LEVEL': 'ERROR', 'MCP_LOG_LEVEL': 'ERROR', 'RUST_LOG': 'error',
            'NODE_ENV': 'production', 'NO_COLOR': '1', 'FORCE_COLOR': '0',
            'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '0',
            **processed_env
        }

        connection_params = StdioServerParameters(
            command=processed_config["command"],
            args=processed_args,
            env=mcp_quiet_env,
        )
    else:
        logger.warning(f"Failed to load MCP Toolset '{server_name}': Configuration must contain either 'url' or 'command' and 'args'.")
        return None

    return connection_params

async def load_all_tools_and_toolsets_async():
    """Loads all core and user-defined tools and toolsets using the proper async pattern.
    
    Returns:
        tuple: (all_tools, exit_stack) where exit_stack must be properly closed
    """
    core_tools = load_core_tools_and_toolsets()
    user_tools, exit_stack = await load_user_tools_and_toolsets_async()
    return core_tools + user_tools, exit_stack

def load_all_tools_and_toolsets():
    """Synchronous wrapper for loading all tools and toolsets.
    
    This is compatible with the ADK framework's synchronous agent definition
    while still supporting proper async MCP lifecycle management.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're already in an async context, just load core tools
        # MCP tools will be loaded asynchronously when the agent runs
        logger.info("Detected async context. Loading core tools only, MCP toolsets will be loaded when agent runs.")
        return load_core_tools_and_toolsets()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        logger.info("Loading all tools and toolsets synchronously...")
        tools, exit_stack = asyncio.run(load_all_tools_and_toolsets_async())
        # Store the exit stack globally for cleanup
        global _global_mcp_exit_stack
        _global_mcp_exit_stack = exit_stack
        logger.info(f"All tools loaded synchronously. Total: {len(tools)} tools.")
        return tools
