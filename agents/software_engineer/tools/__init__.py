"""Tools for the Software Engineer Agent."""

from . import code_search, filesystem, shell_command, system_info

# Export the code search tool
from .code_search import codebase_search_tool

# Export filesystem tools
from .filesystem import edit_file_tool, list_dir_tool, read_file_tool

# Export selective tool loading functions
# Export load all tools and toolsets
from .setup import (
    create_sub_agent_tool_profiles,
    load_all_tools_and_toolsets,
    load_selective_tools_and_toolsets,
    load_selective_tools_and_toolsets_enhanced,
    load_tools_for_sub_agent,
)

# Export per-sub-agent MCP loading functions
try:
    from .sub_agent_mcp_loader import (
        SubAgentMCPConfig,
        create_sub_agent_mcp_config,
        get_sub_agent_mcp_config,
        list_available_mcp_servers,
        load_sub_agent_mcp_tools,
    )
except ImportError:
    # Fallback if sub_agent_mcp_loader is not available
    pass

# Export shell command tools
from .shell_command import execute_shell_command_tool

# Export system info tools
# from .system_info import get_os_info_tool


__all__ = [
    "SubAgentMCPConfig",
    # Code Search Tools
    "codebase_search_tool",
    "create_sub_agent_mcp_config",
    "create_sub_agent_tool_profiles",
    "edit_file_tool",
    # Shell Command Tools
    "execute_shell_command_tool",
    "get_sub_agent_mcp_config",
    "list_available_mcp_servers",
    "list_dir_tool",
    # Load all tools and toolsets
    "load_all_tools_and_toolsets",
    # Selective tool loading
    "load_selective_tools_and_toolsets",
    "load_selective_tools_and_toolsets_enhanced",
    # Per-sub-agent MCP loading
    "load_sub_agent_mcp_tools",
    "load_tools_for_sub_agent",
    # Filesystem Tools
    "read_file_tool",
    # System Info Tools
    # "get_os_info_tool",
]
