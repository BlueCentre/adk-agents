#!/usr/bin/env python3
"""
MCP Tool Separation Verification Script

This script verifies that MCP tools are properly separated between the root agent
and sub-agents, ensuring that sub-agent specific tools are not accessible to the
root agent and vice versa.

Usage:
    python scripts/validation/verify_mcp_separation.py
    # or
    uv run scripts/validation/verify_mcp_separation.py
"""

import os
import sys
from typing import Dict, List, Set

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from agents.software_engineer.tools import (
        load_all_tools_and_toolsets,
        load_tools_for_sub_agent,
    )
    from agents.software_engineer.tools.sub_agent_mcp_loader import (
        get_sub_agent_mcp_config,
        list_available_mcp_servers,
    )
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)


def extract_mcp_servers_from_tools(tools: List) -> List[str]:
    """Extract MCP server names from a list of tools."""
    mcp_servers = []
    for tool in tools:
        if hasattr(tool, "__class__") and "MCPToolset" in str(tool.__class__):
            # Try to get server name from the tool
            if hasattr(tool, "server_name"):
                mcp_servers.append(tool.server_name)
            elif hasattr(tool, "connection_params"):
                # Try to extract from connection params
                if hasattr(tool.connection_params, "command"):
                    mcp_servers.append(f"stdio:{tool.connection_params.command}")
                elif hasattr(tool.connection_params, "url"):
                    mcp_servers.append(f"sse:{tool.connection_params.url}")
                else:
                    mcp_servers.append("unknown_mcp_server")
            else:
                mcp_servers.append("unknown_mcp_server")
    return mcp_servers


def get_core_tool_names(tools: List) -> Set[str]:
    """Extract core tool names from a list of tools."""
    core_tools = set()
    for tool in tools:
        if hasattr(tool, "name"):
            core_tools.add(tool.name)
        elif hasattr(tool, "function") and hasattr(tool.function, "name"):
            core_tools.add(tool.function.name)
        elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
            core_tools.add(tool.agent.name)
    return core_tools


def verify_root_agent_tools():
    """Verify root agent tool configuration."""
    print("🔍 Verifying Root Agent Tools...")

    try:
        root_tools = load_all_tools_and_toolsets()
        core_tools = get_core_tool_names(root_tools)
        mcp_servers = extract_mcp_servers_from_tools(root_tools)

        print(f"✅ Root agent loaded {len(root_tools)} tools")
        print(f"   - Core tools: {len(core_tools)}")
        print(f"   - MCP servers: {len(mcp_servers)}")

        if mcp_servers:
            print("   - MCP servers found:")
            for server in mcp_servers:
                print(f"     • {server}")

        return root_tools, core_tools, mcp_servers

    except Exception as e:
        print(f"❌ Error loading root agent tools: {e}")
        return None, None, None


def verify_sub_agent_tools(sub_agent_name: str, profile: str = None):
    """Verify sub-agent tool configuration."""
    print(f"\n🔍 Verifying {sub_agent_name} Tools...")

    try:
        # Get available servers for this sub-agent
        available_servers = list_available_mcp_servers(sub_agent_name)
        config = get_sub_agent_mcp_config(sub_agent_name)

        print(f"📋 Configuration for {sub_agent_name}:")
        print(f"   - Global servers available: {available_servers.get('global', [])}")
        print(
            f"   - Sub-agent specific servers: {available_servers.get('sub_agent', [])}"
        )
        print(f"   - Global servers included: {config.get('globalServers', [])}")
        print(f"   - Excluded servers: {config.get('excludedServers', [])}")

        # Load actual tools
        if profile:
            tools = load_tools_for_sub_agent(profile, sub_agent_name=sub_agent_name)
        else:
            tools = load_tools_for_sub_agent("minimal", sub_agent_name=sub_agent_name)

        core_tools = get_core_tool_names(tools)
        mcp_servers = extract_mcp_servers_from_tools(tools)

        print(f"✅ {sub_agent_name} loaded {len(tools)} tools")
        print(f"   - Core tools: {len(core_tools)}")
        print(f"   - MCP servers: {len(mcp_servers)}")

        if mcp_servers:
            print("   - MCP servers found:")
            for server in mcp_servers:
                print(f"     • {server}")

        return tools, core_tools, mcp_servers, config

    except Exception as e:
        print(f"❌ Error loading {sub_agent_name} tools: {e}")
        return None, None, None, None


def analyze_separation(root_mcp_servers: List[str], sub_agent_data: Dict):
    """Analyze the separation between root agent and sub-agents."""
    print("\n📊 Analyzing MCP Tool Separation...")

    root_servers = set(root_mcp_servers)

    for sub_agent_name, data in sub_agent_data.items():
        sub_agent_servers = set(data["mcp_servers"])
        config = data["config"]

        # Check for proper separation
        exclusive_to_sub_agent = sub_agent_servers - root_servers
        shared_with_root = sub_agent_servers & root_servers

        print(f"\n🔍 {sub_agent_name} Analysis:")

        if exclusive_to_sub_agent:
            print(f"   ✅ Exclusive tools: {list(exclusive_to_sub_agent)}")
        else:
            print(f"   ℹ️  No exclusive tools found")

        if shared_with_root:
            print(f"   🔄 Shared with root: {list(shared_with_root)}")

        # Check if sub-agent has access to tools it shouldn't
        excluded_servers = set(config.get("excludedServers", []))
        if excluded_servers & sub_agent_servers:
            print(
                f"   ⚠️  WARNING: Sub-agent has access to excluded servers: {list(excluded_servers & sub_agent_servers)}"
            )

        # Check if global servers are properly included
        global_servers_included = set(config.get("globalServers", []))
        if global_servers_included and not (
            global_servers_included & sub_agent_servers
        ):
            print(
                f"   ⚠️  WARNING: Global servers not found in sub-agent tools: {list(global_servers_included)}"
            )


def main():
    """Main verification function."""
    print("🚀 MCP Tool Separation Verification")
    print("=" * 50)

    # Verify root agent
    root_tools, root_core_tools, root_mcp_servers = verify_root_agent_tools()
    if root_tools is None:
        print("❌ Failed to verify root agent tools")
        return

    # Verify sub-agents
    sub_agents_to_check = [
        ("testing_agent", "testing"),
        ("debugging_agent", "debugging"),
        ("code_quality_agent", "code_quality"),
        ("documentation_agent", "documentation"),
        ("devops_agent", "devops"),
    ]

    sub_agent_data = {}

    for sub_agent_name, profile in sub_agents_to_check:
        tools, core_tools, mcp_servers, config = verify_sub_agent_tools(
            sub_agent_name, profile
        )
        if tools is not None:
            sub_agent_data[sub_agent_name] = {
                "tools": tools,
                "core_tools": core_tools,
                "mcp_servers": mcp_servers,
                "config": config,
            }

    # Analyze separation
    if sub_agent_data:
        analyze_separation(root_mcp_servers, sub_agent_data)

    print("\n" + "=" * 50)
    print("✅ Verification complete!")

    # Provide recommendations
    print("\n💡 Recommendations:")
    print("1. Sub-agent specific tools should appear in 'Exclusive tools'")
    print("2. Shared tools should appear in 'Shared with root'")
    print("3. No warnings should appear in the analysis")
    print("4. Root agent should not have access to sub-agent exclusive tools")

    print("\n📚 For more information, see:")
    print("   docs/agents/per-sub-agent-mcp-configuration.md")


if __name__ == "__main__":
    main()
