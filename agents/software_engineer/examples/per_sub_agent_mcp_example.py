"""
Comprehensive example demonstrating per-sub-agent MCP tool loading.

This example shows how to:
1. Configure per-sub-agent MCP tools
2. Use both global and sub-agent specific MCP servers
3. Apply server overrides and filtering
4. Create custom MCP configurations for different sub-agents
5. Load tools with the enhanced system

Usage:
    python -m agents.software_engineer.examples.per_sub_agent_mcp_example
"""

import json
import logging
from pathlib import Path

from ..tools import (
    create_sub_agent_mcp_config,
    get_sub_agent_mcp_config,
    list_available_mcp_servers,
    load_tools_for_sub_agent,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_basic_per_sub_agent_mcp():
    """Example 1: Basic per-sub-agent MCP tool loading."""
    print("\n=== Example 1: Basic Per-Sub-Agent MCP Loading ===")

    # Load tools for debugging agent with per-sub-agent MCP configuration
    debugging_tools = load_tools_for_sub_agent(
        profile_name="debugging", sub_agent_name="debugging_agent"
    )

    print(f"Debugging agent tools loaded: {len(debugging_tools)}")

    # Load tools for testing agent with per-sub-agent MCP configuration
    testing_tools = load_tools_for_sub_agent(profile_name="testing", sub_agent_name="testing_agent")

    print(f"Testing agent tools loaded: {len(testing_tools)}")


def example_2_create_custom_mcp_config():
    """Example 2: Create custom MCP configurations for sub-agents."""
    print("\n=== Example 2: Create Custom MCP Configurations ===")

    # Create custom MCP configuration for debugging agent
    debugging_mcp_servers = {
        "debugger": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-debugger"],
            "env": {"DEBUG_MODE": "1", "VERBOSE": "1"},
        },
        "profiler": {
            "command": "python",
            "args": ["-m", "profiler_mcp_server"],
            "env": {"PROFILER_OUTPUT_DIR": "/tmp/profiler"},
        },
        "monitoring": {
            "url": "http://localhost:8080/mcp",
            "headers": {"Authorization": "Bearer debug-token"},
        },
    }

    create_sub_agent_mcp_config(
        sub_agent_name="debugging_agent",
        mcp_servers=debugging_mcp_servers,
        global_servers=["filesystem"],  # Include global filesystem server
        excluded_servers=["production-db", "external-api"],
        server_overrides={"filesystem": {"env": {"DEBUG_FS": "1"}}},
    )

    # Create custom MCP configuration for testing agent
    testing_mcp_servers = {
        "test-runner": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-test-runner"],
            "env": {"TEST_MODE": "1", "COVERAGE_ENABLED": "1"},
        },
        "coverage": {
            "command": "python",
            "args": ["-m", "coverage_mcp_server"],
            "env": {"COVERAGE_DIR": "./coverage"},
        },
    }

    create_sub_agent_mcp_config(
        sub_agent_name="testing_agent",
        mcp_servers=testing_mcp_servers,
        global_servers=["filesystem"],
        excluded_servers=["production-db"],
        server_overrides={"test-runner": {"env": {"PARALLEL_TESTS": "1"}}},
    )

    print("Custom MCP configurations created for debugging_agent and testing_agent")


def example_3_load_with_custom_config():
    """Example 3: Load tools with custom MCP configuration."""
    print("\n=== Example 3: Load Tools with Custom MCP Configuration ===")

    # Load debugging tools with custom MCP configuration
    custom_debugging_config = {
        "include_mcp_tools": True,
        "mcp_server_filter": ["debugger", "profiler"],  # Only specific servers
        "include_global_servers": False,  # Exclude global servers
        "server_overrides": {"debugger": {"env": {"CUSTOM_DEBUG": "1"}}},
    }

    debugging_tools = load_tools_for_sub_agent(
        profile_name="debugging",
        custom_config=custom_debugging_config,
        sub_agent_name="debugging_agent",
    )

    print(f"Custom debugging tools loaded: {len(debugging_tools)}")

    # Load testing tools with different MCP configuration
    custom_testing_config = {
        "include_mcp_tools": True,
        "mcp_server_filter": ["test-runner", "coverage"],
        "include_global_servers": True,
        "excluded_servers": ["slow-server"],
    }

    testing_tools = load_tools_for_sub_agent(
        profile_name="testing",
        custom_config=custom_testing_config,
        sub_agent_name="testing_agent",
    )

    print(f"Custom testing tools loaded: {len(testing_tools)}")


def example_4_configuration_management():
    """Example 4: Configuration management and inspection."""
    print("\n=== Example 4: Configuration Management ===")

    # List available MCP servers for debugging agent
    available_servers = list_available_mcp_servers("debugging_agent")
    print("Available MCP servers for debugging_agent:")
    print(f"  Global servers: {available_servers.get('global', [])}")
    print(f"  Sub-agent servers: {available_servers.get('sub_agent', [])}")

    # Get current configuration for debugging agent
    current_config = get_sub_agent_mcp_config("debugging_agent")
    print("Current MCP configuration for debugging_agent:")
    print(f"  MCP servers: {list(current_config.get('mcpServers', {}).keys())}")
    print(f"  Global servers: {current_config.get('globalServers', [])}")
    print(f"  Excluded servers: {current_config.get('excludedServers', [])}")


def example_5_environment_specific_configs():
    """Example 5: Environment-specific MCP configurations."""
    print("\n=== Example 5: Environment-Specific Configurations ===")

    environments = ["development", "testing", "staging"]

    for env in environments:
        print(f"\n--- {env.upper()} Environment ---")

        if env == "development":
            # Development: Full access to all debugging tools
            config = {
                "include_mcp_tools": True,
                "mcp_server_filter": ["debugger", "profiler", "monitoring"],
                "include_global_servers": True,
                "server_overrides": {
                    "debugger": {"env": {"DEBUG_LEVEL": "verbose"}},
                    "profiler": {"env": {"PROFILE_MEMORY": "1"}},
                },
            }
        elif env == "testing":
            # Testing: Limited debugging tools, focus on testing
            config = {
                "include_mcp_tools": True,
                "mcp_server_filter": ["test-runner", "coverage"],
                "include_global_servers": True,
                "excluded_servers": ["debugger", "profiler"],
                "server_overrides": {"test-runner": {"env": {"PARALLEL_TESTS": "1"}}},
            }
        else:  # staging
            # Staging: Minimal tools for security
            config = {
                "include_mcp_tools": True,
                "mcp_server_filter": ["monitoring"],
                "include_global_servers": False,
                "excluded_servers": ["debugger", "profiler", "test-runner"],
            }

        # Load tools for this environment
        tools = load_tools_for_sub_agent(
            profile_name="debugging",
            custom_config=config,
            sub_agent_name=f"debugging_agent_{env}",
        )

        print(f"Tools loaded for {env}: {len(tools)}")


def example_6_dynamic_mcp_server_selection():
    """Example 6: Dynamic MCP server selection based on task context."""
    print("\n=== Example 6: Dynamic MCP Server Selection ===")

    # Simulate different task contexts
    task_contexts = [
        {
            "name": "performance_debugging",
            "servers": ["profiler", "monitoring"],
            "overrides": {"profiler": {"env": {"PROFILE_CPU": "1", "PROFILE_MEMORY": "1"}}},
        },
        {
            "name": "security_analysis",
            "servers": ["security-scanner", "monitoring"],
            "exclude_global": True,
            "overrides": {"security-scanner": {"env": {"SCAN_DEPTH": "deep"}}},
        },
        {
            "name": "integration_testing",
            "servers": ["test-runner", "coverage", "monitoring"],
            "overrides": {
                "test-runner": {"env": {"TEST_TYPE": "integration"}},
                "coverage": {"env": {"COVERAGE_THRESHOLD": "80"}},
            },
        },
    ]

    for context in task_contexts:
        print(f"\n--- Task Context: {context['name']} ---")

        config = {
            "include_mcp_tools": True,
            "mcp_server_filter": context["servers"],
            "include_global_servers": not context.get("exclude_global", False),
            "server_overrides": context.get("overrides", {}),
        }

        tools = load_tools_for_sub_agent(
            profile_name="debugging",
            custom_config=config,
            sub_agent_name=f"debugging_agent_{context['name']}",
        )

        print(f"Tools loaded for {context['name']}: {len(tools)}")
        print(f"MCP servers: {context['servers']}")


def example_7_configuration_files():
    """Example 7: Working with configuration files."""
    print("\n=== Example 7: Configuration Files ===")

    # Example configuration file content
    config_content = {
        "mcpServers": {
            "custom-debugger": {
                "command": "python",
                "args": ["-m", "my_custom_debugger"],
                "env": {"DEBUG_PORT": "9999", "DEBUG_HOST": "localhost"},
            },
            "log-analyzer": {
                "command": "npx",
                "args": ["@my-org/log-analyzer-mcp"],
                "env": {"LOG_DIR": "/var/log/app"},
            },
        },
        "globalServers": ["filesystem"],
        "excludedServers": ["production-db"],
        "serverOverrides": {"filesystem": {"env": {"FS_DEBUG": "1"}}},
    }

    # Save configuration to file
    config_dir = Path.cwd() / ".agent" / "sub-agents"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "custom_debugging_agent.mcp.json"
    with config_path.open("w") as f:
        json.dump(config_content, f, indent=2)

    print(f"Configuration saved to: {config_path}")

    # Load tools using the configuration file
    tools = load_tools_for_sub_agent(
        profile_name="minimal",  # Use minimal profile as base
        sub_agent_name="custom_debugging_agent",
    )

    print(f"Tools loaded from configuration file: {len(tools)}")

    # Clean up
    if Path(config_path).exists():
        Path(config_path).unlink()
        print("Configuration file cleaned up")


def main():
    """Run all examples to demonstrate per-sub-agent MCP tool loading."""
    print("Per-Sub-Agent MCP Tool Loading Examples")
    print("=" * 60)

    try:
        example_1_basic_per_sub_agent_mcp()
        example_2_create_custom_mcp_config()
        example_3_load_with_custom_config()
        example_4_configuration_management()
        example_5_environment_specific_configs()
        example_6_dynamic_mcp_server_selection()
        example_7_configuration_files()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    main()
