"""
This file is used to load the core tools and toolsets for the devops agent.
It is used in the devops_agent.py file to load the core tools and toolsets.
"""

import logging
import json
import os
import asyncio
import atexit
from contextlib import AsyncExitStack

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

from .. import config as agent_config
from .. import prompts

if agent_config.ENABLE_CODE_EXECUTION:
    from google.adk.code_executors import BuiltInCodeExecutor

# Import specific tools from the current package (tools/)
from . import (
    index_directory_tool,
    retrieve_code_context_tool,
    purge_rag_index_tool,
    codebase_search_tool,
    execute_vetted_shell_command_tool,
    check_command_exists_tool,
)
from .file_summarizer_tool import FileSummarizerTool
from .code_analysis import (
    analyze_code_tool,
    get_analysis_issues_by_severity_tool,
    suggest_code_fixes_tool,
)
from .shell_command import (
    check_command_exists_tool,
    execute_vetted_shell_command_tool,
)
from .search import google_search_grounding
from .rag_tools import (
    index_directory_tool,
    retrieve_code_context_tool,
    purge_rag_index_tool,
)
from .persistent_memory_tool import (
    save_current_session_to_file_tool,
    load_memory_from_file_tool,
)
from .file_summarizer_tool import FileSummarizerTool

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
    
    Tries the proper async pattern first (MCPToolset.from_server) and falls back
    to the simple pattern if not available.
    
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
                connection_params = SseServerParams(url=processed_config["url"])
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

                processed_env = processed_config.get("env", {})
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
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're already in an async context, return a placeholder that will
        # trigger async loading when the agent actually runs
        logger.info("Detected async context. MCP toolsets will be loaded asynchronously when agent runs.")
        return []  # Return empty list, MCP tools will be loaded later
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        logger.info("Loading MCP toolsets synchronously...")
        tools, exit_stack = asyncio.run(load_user_tools_and_toolsets_async())
        # Store the exit stack globally for cleanup
        global _global_mcp_exit_stack
        _global_mcp_exit_stack = exit_stack
        logger.info(f"MCP toolsets loaded synchronously. Loaded {len(tools)} tools.")
        return tools

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

# IMPORTANT NOTE ON CLEANUP:
# The `cleanup_mcp_toolsets` coroutine below is designed to properly close
# the resources (like subprocesses and network connections) used by MCP toolsets.
# This follows the ADK documentation pattern for proper async lifecycle management.

async def cleanup_mcp_toolsets():
    global _loaded_mcp_toolsets, _global_mcp_exit_stack
    logger.info("atexit: Starting cleanup of MCP toolsets...")
    cleanup_errors = []

    # 1. Close the global exit stack (handles newer ADK pattern toolsets)
    # This is idempotent and safe to call.
    if _global_mcp_exit_stack is not None:
        logger.info("atexit: Closing global MCP exit stack...")
        try:
            await _global_mcp_exit_stack.aclose()
            logger.info("atexit: Successfully closed global MCP exit stack.")
        except Exception as e:
            error_msg = f"atexit: Error closing global MCP exit stack: {e}"
            logger.error(error_msg, exc_info=True)
            cleanup_errors.append(error_msg)
        # Set to None regardless, to prevent re-attempts if atexit were somehow called multiple times
        _global_mcp_exit_stack = None

    # 2. Close individual MCPToolset instances (older ADK pattern or direct instantiations)
    if _loaded_mcp_toolsets:
        logger.info("atexit: Processing _loaded_mcp_toolsets...")
        for toolset_name, toolset_obj in list(_loaded_mcp_toolsets.items()): # Use list() for safe iteration if modifying dict
            if toolset_obj is None:
                logger.info(f"atexit: Toolset {toolset_name} is already None. Skipping.")
                continue

            if isinstance(toolset_obj, MCPToolset): # Check if it's the toolset itself
                logger.info(f"atexit: Attempting to close MCPToolset instance: {toolset_name}")
                if hasattr(toolset_obj, 'close') and callable(toolset_obj.close):
                    try:
                        if asyncio.iscoroutinefunction(toolset_obj.close):
                            logger.info(f"atexit: Asynchronously closing MCPToolset: {toolset_name}")
                            await asyncio.wait_for(toolset_obj.close(), timeout=3.0) # Short timeout
                        else:
                            logger.info(f"atexit: Synchronously closing MCPToolset: {toolset_name} (unexpected for ADK MCPToolset)")
                            toolset_obj.close()
                        logger.info(f"atexit: Successfully initiated close for MCPToolset: {toolset_name}")
                    except asyncio.TimeoutError:
                        error_msg = f"atexit: Timeout (3s) while closing MCPToolset {toolset_name}. It might have been stuck or already handled."
                        logger.warning(error_msg)
                        cleanup_errors.append(error_msg)
                    except asyncio.CancelledError:
                        error_msg = f"atexit: MCPToolset {toolset_name} close operation was cancelled. Likely already handled/cancelled by ADK."
                        logger.warning(error_msg)
                        cleanup_errors.append(error_msg)
                    except RuntimeError as e:
                        error_msg = f"atexit: RuntimeError while closing MCPToolset {toolset_name} (e.g. event loop closed): {e}"
                        logger.warning(error_msg)
                        cleanup_errors.append(error_msg)
                    except Exception as e:
                        error_msg = f"atexit: Error closing MCPToolset {toolset_name}: {e}"
                        logger.error(error_msg, exc_info=True)
                        cleanup_errors.append(error_msg)
                else:
                    logger.warning(f"atexit: MCPToolset instance {toolset_name} does not have a callable 'close' method.")
            elif isinstance(toolset_obj, list):
                logger.info(f"atexit: Toolset {toolset_name} is a list (new ADK pattern tools). Cleanup assumed handled by global exit stack. Skipping individual close here.")
            else:
                logger.warning(f"atexit: Toolset {toolset_name} is of unexpected type: {type(toolset_obj)}. Skipping.")
            
            _loaded_mcp_toolsets[toolset_name] = None
    
    if _loaded_mcp_toolsets: # Check before clearing, mainly for logging
        _loaded_mcp_toolsets.clear()
        logger.info("atexit: Cleared _loaded_mcp_toolsets registry.")

    if cleanup_errors:
        logger.warning(f"atexit: Finished cleanup of MCP toolsets with {len(cleanup_errors)} errors/warnings.")
    else:
        logger.info("atexit: Finished cleanup of MCP toolsets (according to atexit handler).")

# Ensure MCPToolset is imported if not already (it should be).
# from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

atexit.register(lambda: asyncio.run(cleanup_mcp_toolsets()))