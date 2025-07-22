import asyncio
import logging

from agents.software_engineer.tools.sub_agent_mcp_loader import (
    SubAgentMCPConfig,
    load_sub_agent_mcp_tools_async,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def verify_mcp_loading():
    """Debug MCP loading for the enhanced devops agent."""
    sub_agent_name = "enhanced_devops_agent"

    print(f"Testing MCP loading for: {sub_agent_name}")

    # Test the config loader
    config_loader = SubAgentMCPConfig(sub_agent_name)

    print(f"Primary config path: {config_loader.config_path}")
    print(f"Primary config exists: {config_loader.config_path.exists()}")

    if config_loader.fallback_config_path:
        print(f"Fallback config path: {config_loader.fallback_config_path}")
        print(f"Fallback config exists: {config_loader.fallback_config_path.exists()}")

    # Load the configuration
    config = config_loader.load_config()
    print(f"Loaded config: {config}")

    # Try loading the MCP tools
    try:
        tools, exit_stack = await load_sub_agent_mcp_tools_async(sub_agent_name)
        print(f"Successfully loaded {len(tools)} MCP tools")
        for tool in tools:
            print(f"  - {tool}")

        if exit_stack:
            await exit_stack.aclose()
    except Exception as e:
        print(f"Error loading MCP tools: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_mcp_loading())
