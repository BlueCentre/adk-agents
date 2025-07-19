"""
This file is used to load the core tools and toolsets for the software engineer agent.
It is used in the software_engineer_agent.py file to load the core tools and toolsets.
"""

import asyncio
from contextlib import AsyncExitStack
import json
import logging
import os
from typing import Any, List, Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseConnectionParams,
    StdioServerParameters,
)

from .. import config as agent_config, prompt

if agent_config.ENABLE_CODE_EXECUTION:
    from google.adk.code_executors import BuiltInCodeExecutor

# Import specific tools from the current package (tools/)
from .code_analysis import (
    analyze_code_tool,
    get_analysis_issues_by_severity_tool,
    suggest_code_fixes_tool,
)
from .code_search import codebase_search_tool
from .filesystem import edit_file_tool, list_dir_tool, read_file_tool
from .persistent_memory_tool import (
    load_memory_from_file_tool,
    save_current_session_to_file_tool,
)
from .search import google_search_grounding
from .shell_command import execute_shell_command_tool
from .system_info import get_os_info_tool

logger = logging.getLogger(__name__)

# Global registry for MCP toolsets and their exit stacks
# Following ADK documentation pattern for proper async lifecycle management
_loaded_mcp_toolsets = {}
_global_mcp_exit_stack = None


def load_core_tools_and_toolsets():
    """Loads and initializes all core tools, sub-agents, and MCP toolsets."""
    devops_core_tools_list = [
        # Filesystem tools
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        # Code search tools
        codebase_search_tool,
        # Shell command tools
        execute_shell_command_tool,
        # System info tools
        get_os_info_tool,
        # Code analysis tools
        analyze_code_tool,
        get_analysis_issues_by_severity_tool,
        suggest_code_fixes_tool,
        # Memory tools
        load_memory_from_file_tool,
        save_current_session_to_file_tool,
        # Note: RAG tools (index_directory_tool, retrieve_code_context_tool, purge_rag_index_tool)
        # are not available in the SWE agent yet
    ]

    # Note: FileSummarizerTool is not available in the SWE agent yet
    # file_summarizer_tool_instance = FileSummarizerTool()
    # devops_core_tools_list.append(file_summarizer_tool_instance)

    # https://google.github.io/adk-docs/tools/built-in-tools/#limitations
    _search_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="google_search_grounding",
        description="An agent providing Google-search grounding capability",
        instruction=prompt.SEARCH_AGENT_INSTR,
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
            instruction=prompt.CODE_EXECUTION_AGENT_INSTR,
            code_executor=[BuiltInCodeExecutor],
        )
        devops_core_tools_list.append(AgentTool(agent=_code_execution_agent))

    return devops_core_tools_list


async def load_user_tools_and_toolsets_async():
    """Loads and initializes user-defined MCP toolsets using the async pattern.

    This is the recommended approach when MCPToolset.from_server() is available.

    Returns:
        tuple: (user_mcp_tools_list, exit_stack_or_none)
    """
    global _loaded_mcp_toolsets, _global_mcp_exit_stack

    user_mcp_tools_list = []
    mcp_config_path = os.path.join(os.getcwd(), ".agent/mcp.json")

    # Initialize _loaded_mcp_toolsets if it's None
    if _loaded_mcp_toolsets is None:
        _loaded_mcp_toolsets = {}

    # Check if MCPToolset.from_server is available (latest ADK)
    has_from_server = hasattr(MCPToolset, "from_server") and callable(MCPToolset.from_server)

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

    with open(mcp_config_path) as f:
        mcp_config = json.load(f)

    servers = mcp_config.get("mcpServers", {})
    if not servers:
        logger.info(
            "No 'mcpServers' found in mcp.json. No user-defined MCP toolsets will be loaded."
        )
        return user_mcp_tools_list, _global_mcp_exit_stack if has_from_server else None

    # Load MCP toolsets from mcp.json using the best available pattern
    for server_name, server_config in servers.items():
        try:
            # Use helper functions to process config and create connection params
            processed_config = _substitute_env_vars(server_config)
            connection_params = _create_connection_params(server_name, processed_config)

            if not connection_params:
                continue

            # Check if this server_name is already in _loaded_mcp_toolsets
            if (
                server_name in _loaded_mcp_toolsets
                and _loaded_mcp_toolsets[server_name] is not None
            ):
                logger.info(
                    f"MCP Toolset '{server_name}' already loaded. Adding existing instance to user tools list."
                )
                existing_tools = _loaded_mcp_toolsets[server_name]
                if isinstance(existing_tools, list):
                    user_mcp_tools_list.extend(existing_tools)
                else:
                    user_mcp_tools_list.append(existing_tools)
                continue

            # Try the appropriate pattern based on ADK version
            if has_from_server:
                # Use the proper async pattern as documented by ADK
                logger.info(
                    f"Loading MCP Toolset '{server_name}' using async pattern with from_server()..."
                )

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

                    logger.info(
                        f"MCP Toolset '{server_name}' initialized successfully using async pattern. Loaded {len(tools)} tools."
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to load MCP Toolset '{server_name}' using async pattern: {e}"
                    )
                    continue
            else:
                # Use the simple MCPToolset pattern compatible with older ADK versions
                logger.info(f"Loading MCP Toolset '{server_name}' using simple pattern...")

                try:
                    mcp_toolset = MCPToolset(connection_params=connection_params)
                    user_mcp_tools_list.append(mcp_toolset)
                    _loaded_mcp_toolsets[server_name] = mcp_toolset
                    logger.info(
                        f"MCP Toolset '{server_name}' initialized successfully using simple pattern."
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to load MCP Toolset '{server_name}' using simple pattern: {e}"
                    )
                    continue

        except Exception as e:
            logger.warning(f"Failed to load MCP Toolset '{server_name}': {e}")

    return user_mcp_tools_list, _global_mcp_exit_stack if has_from_server else None


def load_user_tools_and_toolsets():
    """Synchronous wrapper for loading user MCP toolsets.

    This loads MCP tools synchronously when possible, and lets ADK handle
    the async lifecycle when needed.
    """
    user_mcp_tools_list = []
    mcp_config_path = os.path.join(os.getcwd(), ".agent/mcp.json")

    if not os.path.exists(mcp_config_path):
        logger.info("mcp.json not found. No user-defined MCP toolsets will be loaded.")
        return user_mcp_tools_list

    with open(mcp_config_path) as f:
        mcp_config = json.load(f)

    servers = mcp_config.get("mcpServers", {})
    if not servers:
        logger.info(
            "No 'mcpServers' found in mcp.json. No user-defined MCP toolsets will be loaded."
        )
        return user_mcp_tools_list

    logger.info(f"Found {len(servers)} MCP servers in mcp.json. Attempting to load them...")

    # Check if MCPToolset.from_server is available (latest ADK)
    has_from_server = hasattr(MCPToolset, "from_server") and callable(MCPToolset.from_server)

    # Always use the async pattern if available, regardless of context
    # This ensures consistent cleanup behavior
    if has_from_server:
        try:
            # Always use the async pattern with proper exit stack management
            # This ensures the ADK Runner can properly cleanup MCP toolsets
            logger.info(
                "Loading MCP toolsets using async pattern with proper exit stack management..."
            )
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
                logger.info(
                    f"MCP Toolset '{server_name}' loaded successfully using simple pattern."
                )

        except Exception as e:
            logger.warning(f"Failed to load MCP Toolset '{server_name}': {e}")
            continue

    logger.info(
        f"MCP toolsets loaded using simple pattern. Total: {len(user_mcp_tools_list)} tools."
    )
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
                logger.warning(
                    f"Environment variable placeholder '{match.group(0)}' found within a string. Full string substitution is not supported. Skipping substitution."
                )
                return value
            logger.warning(
                f"Environment variable '{var_name}' not found. Could not substitute placeholder '{match.group(0)}'."
            )
            return ""
        return value
    if isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    if isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    return value


def _create_connection_params(server_name, processed_config):
    """Create connection parameters for an MCP server."""
    connection_params = None

    if "url" in processed_config:
        if not isinstance(processed_config.get("url"), str):
            logger.warning(
                f"Failed to load MCP Toolset '{server_name}': 'url' must be a string after env var substitution."
            )
            return None
        connection_params = SseConnectionParams(url=processed_config["url"])

    elif "command" in processed_config and "args" in processed_config:
        if not isinstance(processed_config.get("command"), str):
            logger.warning(
                f"Failed to load MCP Toolset '{server_name}': 'command' must be a string after env var substitution."
            )
            return None
        if not isinstance(processed_config.get("args"), list):
            logger.warning(
                f"Failed to load MCP Toolset '{server_name}': 'args' must be a list after env var substitution."
            )
            return None

        processed_args = []
        for arg in processed_config["args"]:
            if not isinstance(arg, str):
                logger.warning(
                    f"Failed to load MCP Toolset '{server_name}': Argument '{arg}' in 'args' is not a string after env var substitution. Skipping toolset."
                )
                return None
            processed_args.append(arg)

        # Check if this MCP server should have output suppressed
        should_suppress_output = (
            server_name in ["filesystem", "memory"]
            or processed_config["command"] == "npx"
            or any("server-filesystem" in str(arg) for arg in processed_args)
            or any("server-memory" in str(arg) for arg in processed_args)
            or processed_config.get("suppress_output", False)
        )

        if should_suppress_output:
            # Add shell redirection to suppress startup messages
            original_command = processed_config["command"]
            original_args = processed_args
            processed_config["command"] = "sh"
            processed_args = [
                "-c",
                f"{original_command} {' '.join(original_args)} 2>/dev/null",
            ]

        processed_env = processed_config.get("env", {})
        for key, value in processed_env.items():
            if not isinstance(value, str):
                logger.warning(
                    f"Failed to load MCP Toolset '{server_name}': Environment variable value for '{key}' is not a string after env var substitution. Converting to string."
                )
                processed_env[key] = str(value)

        # Add environment variables to suppress MCP server startup messages
        mcp_quiet_env = {
            "QUIET": "1",
            "SILENT": "1",
            "NO_BANNER": "1",
            "NO_STARTUP_MESSAGE": "1",
            "LOG_LEVEL": "ERROR",
            "MCP_LOG_LEVEL": "ERROR",
            "RUST_LOG": "error",
            "NODE_ENV": "production",
            "NO_COLOR": "1",
            "FORCE_COLOR": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "0",
            **processed_env,
        }

        connection_params = StdioServerParameters(
            command=processed_config["command"],
            args=processed_args,
            env=mcp_quiet_env,
        )
    else:
        logger.warning(
            f"Failed to load MCP Toolset '{server_name}': Configuration must contain either 'url' or 'command' and 'args'."
        )
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
    core_tools = load_core_tools_and_toolsets()

    # Always try to load user tools, regardless of async context
    # The ADK framework will handle the async lifecycle properly
    user_tools = load_user_tools_and_toolsets()

    all_tools = core_tools + user_tools
    logger.info(
        f"All tools loaded. Core: {len(core_tools)}, User/MCP: {len(user_tools)}, Total: {len(all_tools)} tools."
    )
    return all_tools


def _load_filtered_mcp_tools(mcp_server_filter: list[str]) -> list[Any]:
    """
    Load MCP tools filtered by server names.

    This implementation loads only the specified MCP servers, avoiding the issue
    in the base load_selective_tools_and_toolsets where filtering was attempted
    after loading (which didn't work due to missing server metadata).

    Args:
        mcp_server_filter: List of MCP server names to include

    Returns:
        List of tools from the specified MCP servers only
    """
    filtered_tools = []
    mcp_config_path = os.path.join(os.getcwd(), ".agent/mcp.json")

    if not os.path.exists(mcp_config_path):
        logger.info("mcp.json not found. No MCP tools will be loaded.")
        return filtered_tools

    with open(mcp_config_path) as f:
        mcp_config = json.load(f)

    servers = mcp_config.get("mcpServers", {})
    if not servers:
        logger.info("No 'mcpServers' found in mcp.json.")
        return filtered_tools

    # Only load servers that are in the filter list
    for server_name in mcp_server_filter:
        if server_name not in servers:
            logger.warning(f"MCP server '{server_name}' not found in configuration. Skipping.")
            continue

        server_config = servers[server_name]

        try:
            # Process config and create connection params
            processed_config = _substitute_env_vars(server_config)
            connection_params = _create_connection_params(server_name, processed_config)

            if connection_params:
                # Use simple MCPToolset pattern for consistency with load_user_tools_and_toolsets
                mcp_toolset = MCPToolset(connection_params=connection_params)
                filtered_tools.append(mcp_toolset)
                logger.info(f"Loaded filtered MCP server '{server_name}' successfully.")
            else:
                logger.warning(
                    f"Failed to create connection params for MCP server '{server_name}'."
                )

        except Exception as e:
            logger.warning(f"Failed to load filtered MCP server '{server_name}': {e}")
            continue

    logger.info(
        f"Loaded {len(filtered_tools)} tools from {len(mcp_server_filter)} specified MCP servers."
    )
    return filtered_tools


def load_selective_tools_and_toolsets_enhanced(
    included_categories: Optional[list[str]] = None,
    excluded_categories: Optional[list[str]] = None,
    included_tools: Optional[list[str]] = None,
    excluded_tools: Optional[list[str]] = None,
    include_mcp_tools: bool = True,
    mcp_server_filter: Optional[list[str]] = None,
    sub_agent_name: Optional[str] = None,
    include_global_servers: bool = True,
    excluded_servers: Optional[list[str]] = None,
    server_overrides: Optional[dict] = None,
):
    """
    Enhanced version of selective tool loading that supports per-sub-agent MCP configurations.

    Args:
        included_categories: List of tool categories to include
        excluded_categories: List of tool categories to exclude
        included_tools: List of specific tool names to include
        excluded_tools: List of specific tool names to exclude
        include_mcp_tools: Whether to include MCP tools
        mcp_server_filter: List of specific MCP server names to include
        sub_agent_name: Name of the sub-agent for per-sub-agent MCP loading
        include_global_servers: Whether to include globally configured MCP servers
        excluded_servers: List of MCP servers to exclude
        server_overrides: Configuration overrides for specific MCP servers

    Returns:
        List of selected tools including per-sub-agent MCP tools
    """
    # Load core tools using existing selective loading
    selected_tools = load_selective_tools_and_toolsets(
        included_categories=included_categories,
        excluded_categories=excluded_categories,
        included_tools=included_tools,
        excluded_tools=excluded_tools,
        include_mcp_tools=False,  # We'll handle MCP tools separately
        mcp_server_filter=mcp_server_filter,
    )

    # Add MCP tools if requested
    if include_mcp_tools:
        if sub_agent_name:
            # Use per-sub-agent MCP loading
            try:
                from .sub_agent_mcp_loader import load_sub_agent_mcp_tools

                mcp_tools = load_sub_agent_mcp_tools(
                    sub_agent_name=sub_agent_name,
                    mcp_server_filter=mcp_server_filter,
                    include_global_servers=include_global_servers,
                    excluded_servers=excluded_servers,
                    server_overrides=server_overrides,
                )
                selected_tools.extend(mcp_tools)
                logger.info(f"Added {len(mcp_tools)} per-sub-agent MCP tools for {sub_agent_name}")
            except ImportError as e:
                logger.warning(f"Per-sub-agent MCP loading not available: {e}")
                # Fallback to global MCP loading
                mcp_tools = load_user_tools_and_toolsets()
                selected_tools.extend(mcp_tools)
        else:
            # Use global MCP loading
            mcp_tools = load_user_tools_and_toolsets()
            selected_tools.extend(mcp_tools)

    return selected_tools


def load_selective_tools_and_toolsets(
    included_categories: Optional[list[str]] = None,
    excluded_categories: Optional[list[str]] = None,
    included_tools: Optional[list[str]] = None,
    excluded_tools: Optional[list[str]] = None,
    include_mcp_tools: bool = True,
    mcp_server_filter: Optional[list[str]] = None,
):
    """
    Load tools selectively based on categories and specific tool names.

    Args:
        included_categories: List of tool categories to include (e.g., ['filesystem', 'code_analysis'])
        excluded_categories: List of tool categories to exclude
        included_tools: List of specific tool names to include
        excluded_tools: List of specific tool names to exclude
        include_mcp_tools: Whether to include MCP tools
        mcp_server_filter: List of specific MCP server names to include (now properly filters at server level)

    Returns:
        List of selected tools

    Note:
        MCP server filtering now works correctly by loading only the specified servers,
        rather than loading all servers and attempting to filter afterwards.
    """
    # Define tool categories mapping with actual tool names
    tool_categories = {
        "filesystem": [
            "read_file_content",
            "list_directory_contents",
            "edit_file_content",
        ],
        "code_analysis": [
            "_analyze_code",
            "get_issues_by_severity",
            "suggest_fixes",
        ],
        "code_search": [
            "ripgrep_code_search",
        ],
        "shell_command": [
            "execute_shell_command",
        ],
        "search": [
            "google_search_grounding",
        ],
        "memory": [
            "_load_memory_from_file_impl",
            "_save_current_session_to_file_impl",
        ],
        "system_info": [
            "get_os_info",
        ],
        "agents": [
            "google_search_grounding",  # Search agent
            "code_execution",  # Code execution agent
        ],
    }

    # Get all available tools
    all_tools = load_core_tools_and_toolsets()
    selected_tools = []

    # Create a mapping of tool names to tool instances
    tool_name_map = {}
    for tool in all_tools:
        if hasattr(tool, "name"):
            tool_name_map[tool.name] = tool
        elif hasattr(tool, "function") and hasattr(tool.function, "name"):
            tool_name_map[tool.function.name] = tool
        # Handle AgentTool instances
        elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
            tool_name_map[tool.agent.name] = tool

    # Determine which tools to include based on categories
    tools_to_include = set()

    # Include tools by category
    if included_categories:
        for category in included_categories:
            if category in tool_categories:
                tools_to_include.update(tool_categories[category])

    # Add specifically included tools
    if included_tools:
        tools_to_include.update(included_tools)

    # Remove excluded categories
    if excluded_categories:
        for category in excluded_categories:
            if category in tool_categories:
                tools_to_include.difference_update(tool_categories[category])

    # Remove specifically excluded tools
    if excluded_tools:
        tools_to_include.difference_update(excluded_tools)

    # If no specific inclusion criteria, include all core tools
    if not included_categories and not included_tools:
        tools_to_include = set(tool_name_map.keys())

        # Apply exclusions to all tools
        if excluded_categories:
            for category in excluded_categories:
                if category in tool_categories:
                    tools_to_include.difference_update(tool_categories[category])

        if excluded_tools:
            tools_to_include.difference_update(excluded_tools)

    # Select the actual tool instances
    for tool_name in tools_to_include:
        if tool_name in tool_name_map:
            selected_tools.append(tool_name_map[tool_name])

    # Add MCP tools if requested
    if include_mcp_tools:
        if mcp_server_filter:
            # Use filtered MCP loading when server filter is specified
            mcp_tools = _load_filtered_mcp_tools(mcp_server_filter)
        else:
            # Load all MCP tools when no filter is specified
            mcp_tools = load_user_tools_and_toolsets()

        selected_tools.extend(mcp_tools)

    logger.info(
        f"Selective tool loading: {len(selected_tools)} tools selected "
        f"(categories: {included_categories}, tools: {included_tools})"
    )

    return selected_tools


def create_sub_agent_tool_profiles():
    """
    Define tool profiles for different types of sub-agents.
    This provides convenient presets for common sub-agent configurations.
    """
    return {
        "code_quality": {
            "included_categories": ["filesystem", "code_analysis"],
            "included_tools": [],
            "excluded_categories": ["shell_command"],
            "include_mcp_tools": False,
        },
        "testing": {
            "included_categories": ["filesystem", "code_search", "shell_command"],
            "included_tools": [],
            "excluded_categories": ["search"],
            "include_mcp_tools": True,
            "mcp_server_filter": ["filesystem"],  # Only filesystem MCP tools
        },
        "devops": {
            "included_categories": ["filesystem", "shell_command", "system_info"],
            "included_tools": ["codebase_search_tool"],
            "excluded_categories": [],
            "include_mcp_tools": True,
        },
        "code_review": {
            "included_categories": ["filesystem", "code_analysis", "code_search"],
            "included_tools": [],
            "excluded_categories": ["shell_command"],
            "include_mcp_tools": False,
        },
        "debugging": {
            "included_categories": ["filesystem", "code_analysis", "shell_command"],
            "included_tools": ["codebase_search_tool"],
            "excluded_categories": [],
            "include_mcp_tools": True,
        },
        "documentation": {
            "included_categories": ["filesystem", "code_search"],
            "included_tools": [],
            "excluded_categories": ["shell_command", "system_info"],
            "include_mcp_tools": False,
        },
        "design_pattern": {
            "included_categories": ["filesystem", "code_search"],
            "included_tools": [],
            "excluded_categories": ["shell_command"],
            "include_mcp_tools": False,
        },
        "minimal": {
            "included_categories": ["filesystem"],
            "included_tools": [],
            "excluded_categories": [],
            "include_mcp_tools": False,
        },
        "full_access": {
            "included_categories": None,  # Include all
            "included_tools": None,
            "excluded_categories": [],
            "excluded_tools": [],
            "include_mcp_tools": True,
        },
    }


def load_tools_for_sub_agent(
    profile_name: str, custom_config: Optional[dict] = None, sub_agent_name: Optional[str] = None
):
    """
    Load tools for a sub-agent using a predefined profile or custom configuration.

    Args:
        profile_name: Name of the predefined profile to use
        custom_config: Optional custom configuration to override/extend the profile
        sub_agent_name: Optional name of the sub-agent for per-sub-agent MCP loading

    Returns:
        List of tools configured for the sub-agent
    """
    profiles = create_sub_agent_tool_profiles()

    if profile_name not in profiles:
        logger.warning(f"Unknown profile '{profile_name}'. Using 'minimal' profile.")
        profile_name = "minimal"

    # Start with the profile configuration
    config = profiles[profile_name].copy()

    # Apply custom configuration overrides
    if custom_config:
        config.update(custom_config)

    # Extract sub-agent specific MCP configuration
    sub_agent_mcp_config = {}
    if sub_agent_name:
        # Extract sub-agent specific MCP parameters
        sub_agent_mcp_config = {
            "sub_agent_name": sub_agent_name,
            "mcp_server_filter": config.get("mcp_server_filter"),
            "include_global_servers": config.get("include_global_servers", True),
            "excluded_servers": config.get("excluded_servers"),
            "server_overrides": config.get("server_overrides"),
        }
        # Remove MCP-specific keys from the main config to avoid duplication
        # as they are now handled in sub_agent_mcp_config
        config.pop("mcp_server_filter", None)
        config.pop("include_global_servers", None)
        config.pop("excluded_servers", None)
        config.pop("server_overrides", None)

    # Load tools using the selective loading function with enhanced MCP support
    return load_selective_tools_and_toolsets_enhanced(**config, **sub_agent_mcp_config)
