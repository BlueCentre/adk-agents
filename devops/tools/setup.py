# Agents/devops/tools/setup.py
import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import built_in_code_execution
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters

from .. import config as agent_config
from .. import prompts

# Import specific tools from the current package (tools/)
# These are assumed to be exposed by Agents/devops/tools/__init__.py
# or directly from their defining modules if they are FunctionTool instances.
from . import (
    index_directory_tool,       # Assuming this is already a FunctionTool or similar
    retrieve_code_context_tool, # Assuming this is already a FunctionTool or similar
    purge_rag_index_tool,       # Assuming this is already a FunctionTool or similar
    read_file_tool,
    list_dir_tool,
    edit_file_tool,
    codebase_search_tool,
    execute_vetted_shell_command_tool,
    check_command_exists_tool,
)
from .file_summarizer_tool import FileSummarizerTool

logger = logging.getLogger(__name__)

def load_core_tools_and_toolsets():
    """Loads and initializes all core tools, sub-agents, and MCP toolsets."""

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
    mcp_datadog_toolset = None
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
            devops_observability_tools.append(mcp_datadog_toolset)
            logger.info("MCP Datadog Toolset loaded successfully by setup.py.")
        else:
            logger.warning("DATADOG_API_KEY or DATADOG_APP_KEY not set in config. MCP Datadog Toolset will not be loaded.")
    except Exception as e:
        logger.warning(f"Failed to load MCP DatADOG Toolset in setup.py: {e}. The Datadog tools will be unavailable.")

    _observability_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="observability",
        description="Agent specialized in Observability",
        instruction=prompts.OBSERVABILITY_AGENT_INSTR,
        tools=devops_observability_tools,
    )

    devops_core_tools_list = [
        # RAG and File System Tools
        index_directory_tool,      # Assuming this is the FunctionTool instance
        retrieve_code_context_tool, # Assuming this is the FunctionTool instance
        purge_rag_index_tool,      # <--- USING THE FunctionTool INSTANCE
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        file_summarizer_tool_instance,
        codebase_search_tool,
        # Shell and Command Execution
        execute_vetted_shell_command_tool,
        check_command_exists_tool,
        # Sub-Agents
        AgentTool(agent=_code_execution_agent),
        AgentTool(agent=_search_agent),
        AgentTool(agent=_observability_agent),
    ]

    mcp_filesystem_toolset = None
    try:
        mcp_filesystem_toolset = MCPToolset(
            connection_params=StdioServerParameters(
                command="rust-mcp-filesystem",
                args=["--allow-write", *agent_config.MCP_ALLOWED_DIRECTORIES],
            ),
        )
        devops_core_tools_list.append(mcp_filesystem_toolset)
        logger.info("MCP Filesystem Toolset loaded successfully by setup.py.")
    except Exception as e:
        logger.warning(
            f"Failed to load MCP Filesystem Toolset in setup.py: {e}. "
            "DevOps agent will operate without these MCP file tools."
        )

    mcp_playwright_toolset = None
    if agent_config.MCP_PLAYWRIGHT_ENABLED:
        try:
            mcp_playwright_toolset = MCPToolset(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@executeautomation/playwright-mcp-server"],
                ),
            )
            devops_core_tools_list.append(mcp_playwright_toolset)
            logger.info("MCP Playwright Toolset loaded successfully by setup.py.")
        except Exception as e:
            logger.warning(f"Failed to load MCP Playwright Toolset in setup.py: {e}. Playwright tools will be unavailable.")
    else:
        logger.info("MCP Playwright Toolset is disabled via config in setup.py.")

    return devops_core_tools_list
