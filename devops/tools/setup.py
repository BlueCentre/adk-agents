"""
This file is used to load the core tools and toolsets for the devops agent.
It is used in the devops_agent.py file to load the core tools and toolsets.
"""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import built_in_code_execution
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

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
    "filesystem": None,
    "gitmcp": None,
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

    if not _loaded_mcp_toolsets["filesystem"]:
        try:
            mcp_filesystem_toolset = MCPToolset(
                connection_params=StdioServerParameters(
                    command="rust-mcp-filesystem",
                    args=["--allow-write", *agent_config.MCP_ALLOWED_DIRECTORIES],
                ),
            )
            _loaded_mcp_toolsets["filesystem"] = mcp_filesystem_toolset
            logger.info("MCP Filesystem Toolset initialized successfully by setup.py.")
        except Exception as e:
            logger.warning(
                f"Failed to load MCP Filesystem Toolset in setup.py: {e}. "
                "DevOps agent will fallback to using the built-in file system tools."
            )
    
    if _loaded_mcp_toolsets["filesystem"]:
        devops_core_tools_list.append(_loaded_mcp_toolsets["filesystem"])
    else:
        logger.info("MCP Filesystem Toolset was not loaded or already loaded, not adding to core tools list again unless it's the first load.")

    if not _loaded_mcp_toolsets["gitmcp"]:
        try:
            mcp_gitmcp_toolset = MCPToolset(
                connection_params=SseServerParams(
                    url="https://gitmcp.io/google/adk-python",
                ),
            )
            _loaded_mcp_toolsets["gitmcp"] = mcp_gitmcp_toolset
            logger.info("MCP GitMCP Toolset initialized successfully by setup.py.")
        except Exception as e:
            logger.warning(
                f"Failed to load MCP GitMCP Toolset in setup.py: {e}. "
                "DevOps agent will fallback to using the built-in git tools."
            )
    
    if _loaded_mcp_toolsets["gitmcp"]:
        devops_core_tools_list.append(_loaded_mcp_toolsets["gitmcp"])
    else:
        logger.info("MCP GitMCP Toolset was not loaded or already loaded, not adding to core tools list again unless it's the first load.")


    if agent_config.MCP_PLAYWRIGHT_ENABLED:
        if not _loaded_mcp_toolsets["playwright"]:
            try:
                mcp_playwright_toolset = MCPToolset(
                    connection_params=StdioServerParameters(
                        command="npx",
                        args=["@playwright/mcp@latest"],
                        # args=["-y", "@executeautomation/playwright-mcp-server"],
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
