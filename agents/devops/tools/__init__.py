"""Tools for the Software Engineer Multi-Agent."""

from . import (  # code_analysis,; code_search,; filesystem,; search,; shell_command,; rag_tools,
    analysis_state,
)

# Export code analysis tools
from .code_analysis import (
    analyze_code_tool,
    get_analysis_issues_by_severity_tool,
    suggest_code_fixes_tool,
)

# Export the code search tool for easier imports
from .code_search import codebase_search_tool
from .dynamic_discovery import DynamicToolDiscovery, tool_discovery

# Import the placeholder memory persistence tools
from .persistent_memory_tool import (
    load_memory_from_file_tool,
    save_current_session_to_file_tool,
)

# Export RAG tools
from .rag_tools import (
    index_directory_tool,
    purge_rag_index_tool,
    retrieve_code_context_tool,
)

# Export search tools
from .search import google_search_grounding

# Export shell command tools
from .shell_command import (
    check_command_exists_tool,
    check_shell_command_safety_tool,
    configure_shell_approval_tool,
    configure_shell_whitelist_tool,
    execute_vetted_shell_command_tool,
    execute_vetted_shell_command_with_retry_tool,
)

# Export filesystem tools - DISABLED to avoid confusion with MCP filesystem tools
# from .filesystem import (
#     read_file_tool,
#     list_dir_tool,
#     edit_file_tool,
#     configure_approval_tool,
# )


# Import system info tools


# This file contains the tool registry for the devops agent


__all__ = [
    "DynamicToolDiscovery",
    # Filesystem Tools - DISABLED to avoid confusion with MCP filesystem tools
    # "read_file_tool",
    # "list_dir_tool",
    # "edit_file_tool",
    # "configure_approval_tool",
    # Shell Command Tools
    "check_command_exists_tool",
    "check_shell_command_safety_tool",
    "codebase_search_tool",
    "configure_shell_approval_tool",
    "configure_shell_whitelist_tool",
    "execute_vetted_shell_command_tool",
    "execute_vetted_shell_command_with_retry_tool",
    # Code Analysis Tools (add if needed by root agent, or keep in sub-agent)
    # "analyze_code_tool",
    # "get_analysis_issues_by_severity_tool",
    # "suggest_code_fixes_tool",
    # Search Tools
    "google_search_grounding",
    # RAG Tools
    "index_directory_tool",
    "load_memory_from_file_tool",
    "purge_rag_index_tool",
    "retrieve_code_context_tool",
    # Placeholder Persistent Memory Tools
    "save_current_session_to_file_tool",
    "tool_discovery",
]


# Initialize tool discovery on module import
def get_environment_capabilities():
    """Get cached environment capabilities."""
    return tool_discovery.discover_environment_capabilities()


def get_tool_suggestions(task_description: str):
    """Get tool suggestions for a task."""
    return tool_discovery.suggest_tools_for_task(task_description)
