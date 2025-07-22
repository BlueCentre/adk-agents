"""
Per-Sub-Agent MCP Tool Loading System.

This module extends the existing tool loading system to support per-sub-agent MCP configurations.
It allows users to specify custom MCP tools for each sub-agent while maintaining compatibility
with the existing global MCP configuration.

Key Features:
- Per-sub-agent MCP tool configurations
- Hierarchical configuration (global + per-sub-agent)
- Backward compatibility with existing profiles
- Support for both profile-based and custom configurations
- Security policies and environment-specific constraints
"""

import asyncio
from contextlib import AsyncExitStack
import json
import logging
from pathlib import Path
from typing import Any, Optional

from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
)

from .setup import (
    _create_connection_params,
    _global_mcp_exit_stack,
    _substitute_env_vars,
)

logger = logging.getLogger(__name__)

# Global registry for sub-agent specific MCP toolsets
_sub_agent_mcp_toolsets = {}


class SubAgentMCPConfig:
    """Configuration class for per-sub-agent MCP tools."""

    def __init__(self, sub_agent_name: str):
        self.sub_agent_name = sub_agent_name
        self.config_path = Path(Path.cwd(), ".agent", "sub-agents", f"{sub_agent_name}.mcp.json")
        self.global_config_path = Path(Path.cwd(), ".agent", "mcp.json")

        # Calculate fallback path for enhanced agents
        # Enhanced agents fallback to base name (enhanced_devops_agent -> devops_agent)
        self.fallback_config_path = None
        if sub_agent_name.startswith("enhanced_"):
            base_name = sub_agent_name.replace("enhanced_", "", 1)
            self.fallback_config_path = Path(
                Path.cwd(), ".agent", "sub-agents", f"{base_name}.mcp.json"
            )

    def load_config(self) -> dict[str, Any]:
        """Load configuration for this sub-agent."""
        config = {
            "mcpServers": {},
            "globalServers": [],
            "excludedServers": [],
            "serverOverrides": {},
        }

        # Load global MCP configuration
        if Path(self.global_config_path).exists():
            with Path(self.global_config_path).open() as f:
                global_config = json.load(f)
                config["globalServers"] = list(global_config.get("mcpServers", {}).keys())

        # Load sub-agent specific configuration with fallback support
        config_file_to_use = None
        if Path(self.config_path).exists():
            config_file_to_use = self.config_path
            logger.debug(f"Using primary config file for {self.sub_agent_name}: {self.config_path}")
        elif self.fallback_config_path and Path(self.fallback_config_path).exists():
            config_file_to_use = self.fallback_config_path
            logger.info(
                f"Using fallback config file for {self.sub_agent_name}: {self.fallback_config_path}"
            )

        if config_file_to_use:
            with config_file_to_use.open() as f:
                sub_agent_config = json.load(f)
                config.update(sub_agent_config)

        return config

    def save_config(self, config: dict[str, Any]) -> None:
        """Save configuration for this sub-agent."""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with Path(self.config_path).open("w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved MCP configuration for {self.sub_agent_name}")


async def load_sub_agent_mcp_tools_async(
    sub_agent_name: str,
    mcp_server_filter: Optional[list[str]] = None,
    include_global_servers: bool = True,
    excluded_servers: Optional[list[str]] = None,
    server_overrides: Optional[dict[str, Any]] = None,
) -> tuple[list[Any], Optional[AsyncExitStack]]:
    """
    Load MCP tools for a specific sub-agent using async pattern.

    Args:
        sub_agent_name: Name of the sub-agent
        mcp_server_filter: List of specific MCP servers to include
        include_global_servers: Whether to include globally configured servers
        excluded_servers: List of servers to exclude
        server_overrides: Configuration overrides for specific servers

    Returns:
        Tuple of (tools_list, exit_stack)
    """
    global _sub_agent_mcp_toolsets, _global_mcp_exit_stack

    # Initialize registries
    if _sub_agent_mcp_toolsets is None:
        _sub_agent_mcp_toolsets = {}
    if sub_agent_name not in _sub_agent_mcp_toolsets:
        _sub_agent_mcp_toolsets[sub_agent_name] = {}

    # Load configuration
    config_loader = SubAgentMCPConfig(sub_agent_name)
    config = config_loader.load_config()

    # Apply function parameters to configuration
    if mcp_server_filter:
        config["serverFilter"] = mcp_server_filter
    if not include_global_servers:
        config["globalServers"] = []
    if excluded_servers:
        config["excludedServers"] = excluded_servers
    if server_overrides:
        config["serverOverrides"] = server_overrides

    # Get combined excluded servers list from both config and parameters
    combined_excluded_servers = set(config.get("excludedServers", []))
    if excluded_servers:
        combined_excluded_servers.update(excluded_servers)

    # Prepare tools list and exit stack
    tools_list = []
    local_exit_stack = AsyncExitStack()

    # Check if MCPToolset.from_server is available
    has_from_server = hasattr(MCPToolset, "from_server") and callable(MCPToolset.from_server)

    if has_from_server:
        logger.info(f"Loading MCP tools for {sub_agent_name} using async pattern")

        # Initialize global exit stack if needed
        if _global_mcp_exit_stack is None:
            _global_mcp_exit_stack = AsyncExitStack()
    else:
        logger.info(f"Loading MCP tools for {sub_agent_name} using simple pattern")

    # Load global MCP servers (if enabled)
    if include_global_servers and Path(config_loader.global_config_path).exists():
        with Path(config_loader.global_config_path).open() as f:
            global_mcp_config = json.load(f)
            global_servers = global_mcp_config.get("mcpServers", {})

            for server_name, server_config in global_servers.items():
                # Apply filtering
                if mcp_server_filter and server_name not in mcp_server_filter:
                    continue
                if server_name in combined_excluded_servers:
                    continue

                # Apply overrides
                if server_overrides and server_name in server_overrides:
                    server_config = {**server_config, **server_overrides[server_name]}

                # Load the server
                tools = await _load_mcp_server_async(
                    server_name,
                    server_config,
                    sub_agent_name,
                    local_exit_stack,
                    has_from_server,
                )
                tools_list.extend(tools)

    # Load sub-agent specific MCP servers
    sub_agent_servers = config.get("mcpServers", {})
    for server_name, server_config in sub_agent_servers.items():
        # Apply filtering
        if mcp_server_filter and server_name not in mcp_server_filter:
            continue
        if server_name in combined_excluded_servers:
            continue

        # Apply overrides
        if server_overrides and server_name in server_overrides:
            server_config = {**server_config, **server_overrides[server_name]}

        # Load the server
        tools = await _load_mcp_server_async(
            server_name,
            server_config,
            sub_agent_name,
            local_exit_stack,
            has_from_server,
        )
        tools_list.extend(tools)

    # Register local exit stack with global one
    if has_from_server and _global_mcp_exit_stack:
        await _global_mcp_exit_stack.enter_async_context(local_exit_stack)
        return tools_list, _global_mcp_exit_stack

    return tools_list, local_exit_stack if has_from_server else None


async def _load_mcp_server_async(
    server_name: str,
    server_config: dict[str, Any],
    sub_agent_name: str,
    exit_stack: AsyncExitStack,
    has_from_server: bool,
) -> list[Any]:
    """Load a single MCP server for a sub-agent."""
    tools = []

    # Check if already loaded for this sub-agent
    sub_agent_key = f"{sub_agent_name}:{server_name}"
    if sub_agent_key in _sub_agent_mcp_toolsets:
        logger.info(f"MCP server '{server_name}' already loaded for {sub_agent_name}")
        existing_tools = _sub_agent_mcp_toolsets[sub_agent_key]
        if isinstance(existing_tools, list):
            return existing_tools
        return [existing_tools]

    try:
        # Process configuration
        processed_config = _substitute_env_vars(server_config)
        connection_params = _create_connection_params(server_name, processed_config)

        if not connection_params:
            return tools

        # Load using appropriate pattern
        if has_from_server:
            try:
                server_tools, server_exit_stack = await MCPToolset.from_server(
                    connection_params=connection_params
                )
                await exit_stack.enter_async_context(server_exit_stack)
                tools.extend(server_tools)
                _sub_agent_mcp_toolsets[sub_agent_key] = server_tools
                logger.info(
                    f"Loaded MCP server '{server_name}' for {sub_agent_name}: "
                    f"{len(server_tools)} tools"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load MCP server '{server_name}' for {sub_agent_name}: {e}"
                )
        else:
            try:
                mcp_toolset = MCPToolset(connection_params=connection_params)
                tools.append(mcp_toolset)
                _sub_agent_mcp_toolsets[sub_agent_key] = mcp_toolset
                logger.info(
                    f"Loaded MCP server '{server_name}' for {sub_agent_name} (simple pattern)"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load MCP server '{server_name}' for {sub_agent_name}: {e}"
                )

    except Exception as e:
        logger.error(f"Error loading MCP server '{server_name}' for {sub_agent_name}: {e}")

    return tools


def load_sub_agent_mcp_tools(
    sub_agent_name: str,
    mcp_server_filter: Optional[list[str]] = None,
    include_global_servers: bool = True,
    excluded_servers: Optional[list[str]] = None,
    server_overrides: Optional[dict[str, Any]] = None,
) -> list[Any]:
    """
    Synchronous wrapper for loading sub-agent MCP tools.

    Args:
        sub_agent_name: Name of the sub-agent
        mcp_server_filter: List of specific MCP servers to include
        include_global_servers: Whether to include globally configured servers
        excluded_servers: List of servers to exclude
        server_overrides: Configuration overrides for specific servers

    Returns:
        List of MCP tools for the sub-agent
    """
    try:
        # Check if we're already in an event loop
        try:
            asyncio.get_running_loop()
            # If we get here, we're in an event loop - can't use asyncio.run()
            logger.info(f"Already in event loop, using simple pattern for {sub_agent_name}")
            return _load_sub_agent_mcp_tools_simple(
                sub_agent_name,
                mcp_server_filter,
                include_global_servers,
                excluded_servers,
                server_overrides,
            )
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            tools, exit_stack = asyncio.run(
                load_sub_agent_mcp_tools_async(
                    sub_agent_name,
                    mcp_server_filter,
                    include_global_servers,
                    excluded_servers,
                    server_overrides,
                )
            )
            return tools
    except Exception as e:
        logger.warning(f"Failed to load MCP tools for {sub_agent_name} using async pattern: {e}")
        # Fallback to simple pattern
        return _load_sub_agent_mcp_tools_simple(
            sub_agent_name,
            mcp_server_filter,
            include_global_servers,
            excluded_servers,
            server_overrides,
        )


def _load_sub_agent_mcp_tools_simple(
    sub_agent_name: str,
    mcp_server_filter: Optional[list[str]] = None,
    include_global_servers: bool = True,
    excluded_servers: Optional[list[str]] = None,
    server_overrides: Optional[dict[str, Any]] = None,
) -> list[Any]:
    """Fallback implementation using simple pattern."""
    tools = []

    # Load configuration
    config_loader = SubAgentMCPConfig(sub_agent_name)
    config = config_loader.load_config()

    # Apply filters
    if mcp_server_filter:
        config["serverFilter"] = mcp_server_filter
    if not include_global_servers:
        config["globalServers"] = []
    if excluded_servers:
        config["excludedServers"] = excluded_servers
    if server_overrides:
        config["serverOverrides"] = server_overrides

    # Get combined excluded servers list from both config and parameters
    combined_excluded_servers = set(config.get("excludedServers", []))
    if excluded_servers:
        combined_excluded_servers.update(excluded_servers)

    # Load global servers if enabled
    if include_global_servers and Path(config_loader.global_config_path).exists():
        with Path(config_loader.global_config_path).open() as f:
            global_mcp_config = json.load(f)
            global_servers = global_mcp_config.get("mcpServers", {})

            for server_name, server_config in global_servers.items():
                if mcp_server_filter and server_name not in mcp_server_filter:
                    continue
                if server_name in combined_excluded_servers:
                    continue

                if server_overrides and server_name in server_overrides:
                    server_config = {**server_config, **server_overrides[server_name]}

                server_tools = _load_mcp_server_simple(server_name, server_config, sub_agent_name)
                tools.extend(server_tools)

    # Load sub-agent specific servers
    sub_agent_servers = config.get("mcpServers", {})
    for server_name, server_config in sub_agent_servers.items():
        if mcp_server_filter and server_name not in mcp_server_filter:
            continue
        if server_name in combined_excluded_servers:
            continue

        if server_overrides and server_name in server_overrides:
            server_config = {**server_config, **server_overrides[server_name]}

        server_tools = _load_mcp_server_simple(server_name, server_config, sub_agent_name)
        tools.extend(server_tools)

    return tools


def _load_mcp_server_simple(
    server_name: str, server_config: dict[str, Any], sub_agent_name: str
) -> list[Any]:
    """Load a single MCP server using simple pattern."""
    tools = []

    # Check if already loaded
    sub_agent_key = f"{sub_agent_name}:{server_name}"
    if sub_agent_key in _sub_agent_mcp_toolsets:
        existing_tools = _sub_agent_mcp_toolsets[sub_agent_key]
        if isinstance(existing_tools, list):
            return existing_tools
        return [existing_tools]

    try:
        processed_config = _substitute_env_vars(server_config)
        connection_params = _create_connection_params(server_name, processed_config)

        if connection_params:
            mcp_toolset = MCPToolset(connection_params=connection_params)
            tools.append(mcp_toolset)
            _sub_agent_mcp_toolsets[sub_agent_key] = mcp_toolset
            logger.info(f"Loaded MCP server '{server_name}' for {sub_agent_name} (simple pattern)")

    except Exception as e:
        logger.warning(f"Failed to load MCP server '{server_name}' for {sub_agent_name}: {e}")

    return tools


def create_sub_agent_mcp_config(
    sub_agent_name: str,
    mcp_servers: dict[str, dict[str, Any]],
    global_servers: Optional[list[str]] = None,
    excluded_servers: Optional[list[str]] = None,
    server_overrides: Optional[dict[str, Any]] = None,
) -> None:
    """
    Create MCP configuration for a sub-agent.

    Args:
        sub_agent_name: Name of the sub-agent
        mcp_servers: Dictionary of MCP server configurations
        global_servers: List of global servers to include
        excluded_servers: List of servers to exclude
        server_overrides: Configuration overrides for specific servers
    """
    config_loader = SubAgentMCPConfig(sub_agent_name)
    config = {
        "mcpServers": mcp_servers,
        "globalServers": global_servers or [],
        "excludedServers": excluded_servers or [],
        "serverOverrides": server_overrides or {},
    }

    config_loader.save_config(config)


def get_sub_agent_mcp_config(sub_agent_name: str) -> dict[str, Any]:
    """Get the current MCP configuration for a sub-agent."""
    config_loader = SubAgentMCPConfig(sub_agent_name)
    return config_loader.load_config()


def list_available_mcp_servers(sub_agent_name: str) -> dict[str, list[str]]:
    """
    List all available MCP servers for a sub-agent.

    Returns:
        Dictionary with 'global' and 'sub_agent' keys containing server lists
    """
    config_loader = SubAgentMCPConfig(sub_agent_name)

    # Get global servers
    global_servers = []
    if Path(config_loader.global_config_path).exists():
        with Path(config_loader.global_config_path).open() as f:
            global_config = json.load(f)
            global_servers = list(global_config.get("mcpServers", {}).keys())

    # Get sub-agent servers with fallback support
    sub_agent_servers = []
    config_file_to_use = None
    if Path(config_loader.config_path).exists():
        config_file_to_use = config_loader.config_path
    elif config_loader.fallback_config_path and Path(config_loader.fallback_config_path).exists():
        config_file_to_use = config_loader.fallback_config_path

    if config_file_to_use:
        with config_file_to_use.open() as f:
            sub_agent_config = json.load(f)
            sub_agent_servers = list(sub_agent_config.get("mcpServers", {}).keys())

    return {"global": global_servers, "sub_agent": sub_agent_servers}
