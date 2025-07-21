"""
Comprehensive example demonstrating selective tool loading for sub-agents.

This example shows various approaches to configure tools for different sub-agent scenarios:
1. Using predefined profiles
2. Customizing profiles with overrides
3. Direct selective loading with custom parameters
4. Dynamic tool loading based on runtime conditions
5. Creating custom tool profiles

Run this example to see the different tool loading strategies in action.
"""

import logging

from ..tools import (
    create_sub_agent_tool_profiles,
    load_selective_tools_and_toolsets,
    load_tools_for_sub_agent,
)

# Configure logging to see tool loading details
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_predefined_profiles():
    """Example 1: Using predefined profiles for common sub-agent types."""
    print("\n=== Example 1: Predefined Profiles ===")

    # Load tools for different sub-agent types using predefined profiles
    profiles_to_test = ["code_quality", "testing", "devops", "code_review", "minimal"]

    for profile in profiles_to_test:
        tools = load_tools_for_sub_agent(profile)
        print(f"Profile '{profile}': {len(tools)} tools loaded")

        # Print first few tool names for demonstration
        tool_names = []
        for tool in tools[:3]:  # Show first 3 tools
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "function") and hasattr(tool.function, "name"):
                tool_names.append(tool.function.name)

        if tool_names:
            print(f"  Sample tools: {', '.join(tool_names)}")


def example_2_custom_profile_overrides():
    """Example 2: Customizing predefined profiles with overrides."""
    print("\n=== Example 2: Custom Profile Overrides ===")

    # Customize the code_quality profile to include shell command tools
    custom_config = {
        "included_categories": ["filesystem", "code_analysis", "shell_command"],
        "excluded_categories": [],  # Override the default exclusion
        "include_mcp_tools": True,  # Override to include MCP tools
    }

    tools = load_tools_for_sub_agent("code_quality", custom_config)
    print(f"Customized code_quality profile: {len(tools)} tools loaded")

    # Example of adding specific tools to a profile
    testing_with_extras = {
        "included_tools": ["google_search_grounding", "analyze_code_tool"],
        "excluded_tools": ["execute_shell_command_tool"],  # Remove shell access for security
    }

    tools = load_tools_for_sub_agent("testing", testing_with_extras)
    print(f"Testing with extras: {len(tools)} tools loaded")


def example_3_direct_selective_loading():
    """Example 3: Direct selective loading with custom parameters."""
    print("\n=== Example 3: Direct Selective Loading ===")

    # Load only filesystem and search tools, exclude everything else
    tools = load_selective_tools_and_toolsets(
        included_categories=["filesystem", "search"],
        excluded_categories=["shell_command", "code_analysis"],
        include_mcp_tools=False,
    )
    print(f"Filesystem + Search only: {len(tools)} tools loaded")

    # Load specific tools by name
    tools = load_selective_tools_and_toolsets(
        included_tools=[
            "read_file_tool",
            "codebase_search_tool",
            "google_search_grounding",
        ],
        excluded_tools=[],
        include_mcp_tools=True,
        mcp_server_filter=["filesystem"],
    )
    print(f"Specific tools selection: {len(tools)} tools loaded")


def example_4_dynamic_tool_loading():
    """Example 4: Dynamic tool loading based on runtime conditions."""
    print("\n=== Example 4: Dynamic Tool Loading ===")

    # Simulate different runtime conditions
    environments = ["development", "testing", "production"]

    for env in environments:
        print(f"\nEnvironment: {env}")

        # Adjust tool selection based on environment
        if env == "development":
            # Full access for development
            tools = load_tools_for_sub_agent("full_access")
        elif env == "testing":
            # Testing environment needs test tools but no production access
            config = {
                "included_categories": ["filesystem", "code_search", "shell_command"],
                "excluded_categories": ["system_info"],
                "include_mcp_tools": True,
                "mcp_server_filter": ["filesystem", "testing"],
            }
            tools = load_selective_tools_and_toolsets(**config)
        else:  # production
            # Production environment - minimal tools for security
            tools = load_tools_for_sub_agent("minimal")

        print(f"  {len(tools)} tools loaded for {env}")


def example_5_custom_tool_profiles():
    """Example 5: Creating and using custom tool profiles."""
    print("\n=== Example 5: Custom Tool Profiles ===")

    # Get the default profiles
    profiles = create_sub_agent_tool_profiles()

    # Add custom profiles
    custom_profiles = {
        "security_auditor": {
            "included_categories": ["filesystem", "code_analysis"],
            "excluded_categories": ["shell_command"],  # No shell access for security
            "included_tools": ["codebase_search_tool"],
            "include_mcp_tools": False,
        },
        "ai_assistant": {
            "included_categories": ["filesystem", "search"],
            "included_tools": ["google_search_grounding"],
            "excluded_categories": ["shell_command", "system_info"],
            "include_mcp_tools": True,
            "mcp_server_filter": ["knowledge_base", "web_search"],
        },
        "deployment_manager": {
            "included_categories": ["filesystem", "shell_command", "system_info"],
            "excluded_categories": ["code_analysis"],
            "include_mcp_tools": True,
            "mcp_server_filter": ["docker", "kubernetes", "aws", "gcp"],
        },
    }

    # Merge custom profiles with default ones
    profiles.update(custom_profiles)

    # Test custom profiles
    for profile_name in custom_profiles:
        config = profiles[profile_name]
        tools = load_selective_tools_and_toolsets(**config)
        print(f"Custom profile '{profile_name}': {len(tools)} tools loaded")


def example_6_conditional_tool_loading():
    """Example 6: Conditional tool loading based on agent capabilities."""
    print("\n=== Example 6: Conditional Tool Loading ===")

    # Simulate different agent capabilities
    agent_capabilities = {
        "has_internet_access": True,
        "can_execute_shell": False,
        "has_file_access": True,
        "debug_mode": True,
    }

    # Build configuration based on capabilities
    config = {
        "included_categories": [],
        "excluded_categories": [],
        "included_tools": [],
        "excluded_tools": [],
        "include_mcp_tools": False,
    }

    # Add tools based on capabilities
    if agent_capabilities["has_file_access"]:
        config["included_categories"].append("filesystem")

    if agent_capabilities["has_internet_access"]:
        config["included_categories"].append("search")
        config["included_tools"].append("google_search_grounding")

    if agent_capabilities["can_execute_shell"]:
        config["included_categories"].append("shell_command")
    else:
        config["excluded_categories"].append("shell_command")

    if agent_capabilities["debug_mode"]:
        config["included_categories"].append("code_analysis")
        config["include_mcp_tools"] = True

    tools = load_selective_tools_and_toolsets(**config)
    print(f"Capability-based loading: {len(tools)} tools loaded")
    print(f"Configuration: {config}")


def main():
    """Run all examples to demonstrate selective tool loading."""
    print("Selective Tool Loading Examples")
    print("=" * 50)

    try:
        example_1_predefined_profiles()
        example_2_custom_profile_overrides()
        example_3_direct_selective_loading()
        example_4_dynamic_tool_loading()
        example_5_custom_tool_profiles()
        example_6_conditional_tool_loading()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    main()
