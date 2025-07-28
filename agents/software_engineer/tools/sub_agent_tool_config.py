"""
Centralized configuration for sub-agent tool profiles and policies.

This module provides a centralized way to manage tool access policies and configurations
for different types of sub-agents. It supports:
- Predefined profiles for common sub-agent types
- Environment-specific tool policies
- Security-based tool restrictions
- Custom tool groupings and categories

Usage:
    from ..tools.sub_agent_tool_config import get_tool_profile, apply_security_policy

    # Load tools with security policy
    tools = load_tools_for_sub_agent('testing')
    tools = apply_security_policy(tools, 'restricted')
"""

from enum import Enum
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for tool access policies."""

    UNRESTRICTED = "unrestricted"
    STANDARD = "standard"
    RESTRICTED = "restricted"
    LOCKED_DOWN = "locked_down"


class EnvironmentType(Enum):
    """Environment types for context-specific tool loading."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


# Tool category definitions with enhanced metadata
TOOL_CATEGORIES = {
    "filesystem": {
        "tools": [
            "read_file_content_tool",
            "list_directory_contents_tool",
            "edit_file_content_tool",
        ],
        "description": "File system operations (read, write, list)",
        "security_risk": "medium",
        "required_permissions": ["file_read", "file_write"],
    },
    "code_analysis": {
        "tools": [
            "analyze_code_tool",
            "get_analysis_issues_by_severity_tool",
            "suggest_code_fixes_tool",
        ],
        "description": "Static code analysis and quality checks",
        "security_risk": "low",
        "required_permissions": ["code_read"],
    },
    "code_search": {
        "tools": ["codebase_search_tool"],
        "description": "Semantic code search and discovery",
        "security_risk": "low",
        "required_permissions": ["code_read"],
    },
    "shell_command": {
        "tools": ["execute_shell_command_tool"],
        "description": "Shell command execution",
        "security_risk": "high",
        "required_permissions": ["shell_execute"],
    },
    "search": {
        "tools": ["google_search_grounding"],
        "description": "Web search and information retrieval",
        "security_risk": "medium",
        "required_permissions": ["internet_access"],
    },
    "memory": {
        "tools": ["load_memory_from_file_tool", "save_current_session_to_file_tool"],
        "description": "Session memory and persistence",
        "security_risk": "low",
        "required_permissions": ["memory_access"],
    },
    "system_info": {
        "tools": ["get_os_info_tool"],
        "description": "System information and diagnostics",
        "security_risk": "medium",
        "required_permissions": ["system_read"],
    },
    "agents": {
        "tools": ["google_search_grounding", "code_execution"],
        "description": "Sub-agent delegation and specialized agents",
        "security_risk": "medium",
        "required_permissions": ["agent_delegation"],
    },
}


# Enhanced sub-agent profiles with metadata
SUB_AGENT_PROFILES = {
    "code_quality": {
        "config": {
            "included_categories": ["filesystem", "code_analysis"],
            "excluded_categories": ["shell_command"],
            "include_mcp_tools": False,
        },
        "description": "Code quality analysis and improvement suggestions",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [EnvironmentType.DEVELOPMENT, EnvironmentType.TESTING],
        "required_permissions": ["code_read", "file_read"],
    },
    "testing": {
        "config": {
            "included_categories": ["filesystem", "code_search", "shell_command"],
            "excluded_categories": ["search"],
            "include_mcp_tools": True,
            "mcp_server_filter": ["filesystem", "test-runner", "coverage"],
            "include_global_servers": True,
            "excluded_servers": ["production-db"],
            "server_overrides": {"test-runner": {"env": {"TEST_MODE": "1"}}},
        },
        "description": "Test generation, execution, and validation",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [EnvironmentType.DEVELOPMENT, EnvironmentType.TESTING],
        "required_permissions": [
            "code_read",
            "file_read",
            "file_write",
            "shell_execute",
        ],
    },
    "devops": {
        "config": {
            "included_categories": ["filesystem", "shell_command", "system_info"],
            "included_tools": ["codebase_search_tool"],
            "excluded_categories": [],
            "include_mcp_tools": True,
        },
        "description": "DevOps, CI/CD, and infrastructure management",
        "security_level": SecurityLevel.RESTRICTED,
        "suitable_environments": [EnvironmentType.DEVELOPMENT, EnvironmentType.STAGING],
        "required_permissions": [
            "file_read",
            "file_write",
            "shell_execute",
            "system_read",
        ],
    },
    "code_review": {
        "config": {
            "included_categories": ["filesystem", "code_analysis", "code_search"],
            "excluded_categories": ["shell_command"],
            "include_mcp_tools": False,
        },
        "description": "Code review and architectural analysis",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [
            EnvironmentType.DEVELOPMENT,
            EnvironmentType.TESTING,
            EnvironmentType.STAGING,
        ],
        "required_permissions": ["code_read", "file_read"],
    },
    "debugging": {
        "config": {
            "included_categories": ["filesystem", "code_analysis", "shell_command"],
            "included_tools": ["codebase_search_tool"],
            "excluded_categories": [],
            "include_mcp_tools": True,
            "mcp_server_filter": ["filesystem", "debugger", "profiler", "monitoring"],
            "include_global_servers": True,
            "excluded_servers": ["production-db", "external-api"],
            "server_overrides": {
                "debugger": {"env": {"DEBUG_MODE": "1", "VERBOSE": "1"}},
                "profiler": {"args": ["--memory-profiling", "--cpu-profiling"]},
            },
        },
        "description": "Debugging and troubleshooting assistance",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [EnvironmentType.DEVELOPMENT, EnvironmentType.TESTING],
        "required_permissions": [
            "code_read",
            "file_read",
            "file_write",
            "shell_execute",
        ],
    },
    "documentation": {
        "config": {
            "included_categories": ["filesystem", "code_search"],
            "excluded_categories": ["shell_command", "system_info"],
            "include_mcp_tools": False,
        },
        "description": "Documentation generation and maintenance",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [
            EnvironmentType.DEVELOPMENT,
            EnvironmentType.TESTING,
            EnvironmentType.STAGING,
        ],
        "required_permissions": ["code_read", "file_read", "file_write"],
    },
    "design_pattern": {
        "config": {
            "included_categories": ["filesystem", "code_search"],
            "excluded_categories": ["shell_command"],
            "include_mcp_tools": False,
        },
        "description": "Design pattern analysis and recommendations",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [EnvironmentType.DEVELOPMENT, EnvironmentType.TESTING],
        "required_permissions": ["code_read", "file_read"],
    },
    "security_auditor": {
        "config": {
            "included_categories": ["filesystem", "code_analysis"],
            "excluded_categories": ["shell_command"],
            "included_tools": ["codebase_search_tool"],
            "include_mcp_tools": False,
        },
        "description": "Security analysis and vulnerability assessment",
        "security_level": SecurityLevel.RESTRICTED,
        "suitable_environments": [EnvironmentType.DEVELOPMENT, EnvironmentType.TESTING],
        "required_permissions": ["code_read", "file_read"],
    },
    "minimal": {
        "config": {
            "included_categories": ["filesystem"],
            "excluded_categories": [],
            "include_mcp_tools": False,
        },
        "description": "Minimal tool set for basic operations",
        "security_level": SecurityLevel.STANDARD,
        "suitable_environments": [EnvironmentType.PRODUCTION],
        "required_permissions": ["file_read"],
    },
    "full_access": {
        "config": {
            "included_categories": None,  # Include all
            "excluded_categories": [],
            "excluded_tools": [],
            "include_mcp_tools": True,
        },
        "description": "Full access to all available tools",
        "security_level": SecurityLevel.UNRESTRICTED,
        "suitable_environments": [EnvironmentType.DEVELOPMENT],
        "required_permissions": ["*"],
    },
}


# Security policies for different levels
SECURITY_POLICIES = {
    SecurityLevel.UNRESTRICTED: {
        "allowed_categories": "all",
        "blocked_categories": [],
        "allow_mcp_tools": True,
        "allow_shell_commands": True,
        "allow_file_write": True,
        "allow_system_access": True,
    },
    SecurityLevel.STANDARD: {
        "allowed_categories": [
            "filesystem",
            "code_analysis",
            "code_search",
            "memory",
            "agents",
        ],
        "blocked_categories": ["shell_command", "system_info"],
        "allow_mcp_tools": True,
        "allow_shell_commands": False,
        "allow_file_write": True,
        "allow_system_access": False,
    },
    SecurityLevel.RESTRICTED: {
        "allowed_categories": ["filesystem", "code_analysis", "code_search"],
        "blocked_categories": ["shell_command", "system_info", "search"],
        "allow_mcp_tools": False,
        "allow_shell_commands": False,
        "allow_file_write": True,
        "allow_system_access": False,
    },
    SecurityLevel.LOCKED_DOWN: {
        "allowed_categories": ["filesystem"],
        "blocked_categories": ["shell_command", "system_info", "search", "agents"],
        "allow_mcp_tools": False,
        "allow_shell_commands": False,
        "allow_file_write": False,
        "allow_system_access": False,
    },
}


# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    EnvironmentType.DEVELOPMENT: {
        "default_security_level": SecurityLevel.STANDARD,
        "allow_experimental_tools": True,
        "enable_debug_tools": True,
        "max_tool_count": None,
    },
    EnvironmentType.TESTING: {
        "default_security_level": SecurityLevel.STANDARD,
        "allow_experimental_tools": True,
        "enable_debug_tools": True,
        "max_tool_count": 20,
    },
    EnvironmentType.STAGING: {
        "default_security_level": SecurityLevel.RESTRICTED,
        "allow_experimental_tools": False,
        "enable_debug_tools": False,
        "max_tool_count": 15,
    },
    EnvironmentType.PRODUCTION: {
        "default_security_level": SecurityLevel.LOCKED_DOWN,
        "allow_experimental_tools": False,
        "enable_debug_tools": False,
        "max_tool_count": 10,
    },
}


def get_tool_profile(profile_name: str) -> dict[str, Any]:
    """
    Get a tool profile configuration by name.

    Args:
        profile_name: Name of the profile to retrieve

    Returns:
        Dictionary containing the profile configuration

    Raises:
        ValueError: If the profile doesn't exist
    """
    if profile_name not in SUB_AGENT_PROFILES:
        available_profiles = list(SUB_AGENT_PROFILES.keys())
        raise ValueError(
            f"Unknown profile '{profile_name}'. Available profiles: {available_profiles}"
        )

    return SUB_AGENT_PROFILES[profile_name].copy()


def apply_security_policy(config: dict[str, Any], security_level: SecurityLevel) -> dict[str, Any]:
    """
    Apply security policy constraints to a tool configuration.

    Args:
        config: Tool configuration to constrain
        security_level: Security level to apply

    Returns:
        Modified configuration with security constraints applied
    """
    policy = SECURITY_POLICIES[security_level]
    modified_config = config.copy()

    # Apply category restrictions
    if policy["allowed_categories"] != "all":
        if "included_categories" in modified_config:
            allowed_categories = set(policy["allowed_categories"])
            current_categories = set(modified_config["included_categories"] or [])
            modified_config["included_categories"] = list(current_categories & allowed_categories)

        # Add blocked categories to exclusion list
        if "excluded_categories" not in modified_config:
            modified_config["excluded_categories"] = []
        modified_config["excluded_categories"].extend(policy["blocked_categories"])

    # Apply MCP tool restrictions
    if not policy["allow_mcp_tools"]:
        modified_config["include_mcp_tools"] = False

    # Apply shell command restrictions
    if not policy["allow_shell_commands"]:
        if "excluded_categories" not in modified_config:
            modified_config["excluded_categories"] = []
        if "shell_command" not in modified_config["excluded_categories"]:
            modified_config["excluded_categories"].append("shell_command")

    # Apply file write restrictions
    if not policy["allow_file_write"]:
        if "excluded_tools" not in modified_config:
            modified_config["excluded_tools"] = []
        if "edit_file_content_tool" not in modified_config["excluded_tools"]:
            modified_config["excluded_tools"].append("edit_file_content_tool")

    return modified_config


def get_environment_config(env_type: EnvironmentType) -> dict[str, Any]:
    """
    Get environment-specific configuration.

    Args:
        env_type: Environment type

    Returns:
        Environment configuration dictionary
    """
    return ENVIRONMENT_CONFIGS[env_type].copy()


def validate_profile_for_environment(profile_name: str, env_type: EnvironmentType) -> bool:
    """
    Validate if a profile is suitable for a given environment.

    Args:
        profile_name: Name of the profile to validate
        env_type: Environment type to validate against

    Returns:
        True if profile is suitable for the environment
    """
    if profile_name not in SUB_AGENT_PROFILES:
        return False

    profile = SUB_AGENT_PROFILES[profile_name]
    return env_type in profile["suitable_environments"]


def get_recommended_profiles_for_environment(env_type: EnvironmentType) -> list[str]:
    """
    Get list of recommended profiles for a given environment.

    Args:
        env_type: Environment type

    Returns:
        List of recommended profile names
    """
    recommended = []
    for profile_name, profile in SUB_AGENT_PROFILES.items():
        if env_type in profile["suitable_environments"]:
            recommended.append(profile_name)
    return recommended


def create_custom_profile(
    name: str,
    included_categories: Optional[list[str]] = None,
    excluded_categories: Optional[list[str]] = None,
    included_tools: Optional[list[str]] = None,
    excluded_tools: Optional[list[str]] = None,
    include_mcp_tools: bool = True,
    mcp_server_filter: Optional[list[str]] = None,
    description: Optional[str] = None,
    security_level: SecurityLevel = SecurityLevel.STANDARD,
    suitable_environments: Optional[list[EnvironmentType]] = None,
    required_permissions: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Create a custom tool profile.

    Args:
        name: Name of the custom profile
        included_categories: Categories to include
        excluded_categories: Categories to exclude
        included_tools: Specific tools to include
        excluded_tools: Specific tools to exclude
        include_mcp_tools: Whether to include MCP tools
        mcp_server_filter: MCP servers to filter by
        description: Profile description
        security_level: Security level for the profile
        suitable_environments: Environments where profile is suitable
        required_permissions: Required permissions

    Returns:
        Custom profile configuration
    """
    profile = {
        "config": {
            "included_categories": included_categories,
            "excluded_categories": excluded_categories or [],
            "included_tools": included_tools or [],
            "excluded_tools": excluded_tools or [],
            "include_mcp_tools": include_mcp_tools,
        },
        "description": description or f"Custom profile: {name}",
        "security_level": security_level,
        "suitable_environments": suitable_environments or [EnvironmentType.DEVELOPMENT],
        "required_permissions": required_permissions or [],
    }

    if mcp_server_filter:
        profile["config"]["mcp_server_filter"] = mcp_server_filter

    return profile


def register_custom_profile(name: str, profile: dict[str, Any]) -> None:
    """
    Register a custom profile globally.

    Args:
        name: Name of the profile
        profile: Profile configuration
    """
    SUB_AGENT_PROFILES[name] = profile
    logger.info(f"Registered custom profile: {name}")


def list_available_profiles() -> list[str]:
    """
    List all available profile names.

    Returns:
        List of available profile names
    """
    return list(SUB_AGENT_PROFILES.keys())


def get_profile_info(profile_name: str) -> dict[str, Any]:
    """
    Get detailed information about a profile.

    Args:
        profile_name: Name of the profile

    Returns:
        Profile information including config and metadata
    """
    if profile_name not in SUB_AGENT_PROFILES:
        raise ValueError(f"Unknown profile: {profile_name}")

    profile = SUB_AGENT_PROFILES[profile_name]
    return {
        "name": profile_name,
        "description": profile["description"],
        "security_level": profile["security_level"].value,
        "suitable_environments": [env.value for env in profile["suitable_environments"]],
        "required_permissions": profile["required_permissions"],
        "config": profile["config"],
    }
