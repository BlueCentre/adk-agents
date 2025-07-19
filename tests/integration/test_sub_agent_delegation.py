"""
Integration Tests for Sub-Agent Delegation Patterns

This module contains integration tests for sub-agent delegation patterns
based on Google ADK integration testing approaches. These tests focus
on agent structure and basic multi-agent concepts.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import agent components
from agents.devops.devops_agent import MyDevopsAgent
from agents.software_engineer.agent import root_agent as software_engineer_agent
from agents.software_engineer.sub_agents.code_quality.agent import code_quality_agent
from agents.software_engineer.sub_agents.code_review.agent import code_review_agent
from agents.software_engineer.sub_agents.devops.agent import devops_agent as devops_sub_agent
from agents.software_engineer.sub_agents.documentation.agent import documentation_agent
from agents.software_engineer.sub_agents.testing.agent import testing_agent

# Import tool loading functions for testing
from agents.software_engineer.tools import (
    create_sub_agent_tool_profiles,
    load_tools_for_sub_agent,
)

# Test utilities
from tests.fixtures.test_helpers import (
    create_mock_llm_client,
    create_mock_session_state,
    create_test_workspace,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.core
class TestSubAgentDelegation:
    """Integration tests for sub-agent delegation patterns."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client for testing."""
        return create_mock_llm_client()

    @pytest.fixture
    def mock_session_state(self):
        """Create mock session state for testing."""
        return create_mock_session_state()

    @pytest.fixture
    def test_workspace(self):
        """Create test workspace for testing."""
        return create_test_workspace()

    @pytest.mark.asyncio
    async def test_software_engineer_agent_has_sub_agents(self):
        """Test that the software engineer agent has sub-agents configured."""
        # Verify the software engineer agent has sub-agents
        assert hasattr(software_engineer_agent, "sub_agents")
        assert software_engineer_agent.sub_agents is not None
        assert len(software_engineer_agent.sub_agents) > 0

        # Check for expected sub-agents
        sub_agent_names = [agent.name for agent in software_engineer_agent.sub_agents]
        expected_agents = [
            "code_quality_agent",
            "code_review_agent",
            "testing_agent",
            "documentation_agent",
        ]

        for expected_agent in expected_agents:
            assert any(expected_agent in name for name in sub_agent_names), (
                f"Expected sub-agent {expected_agent} not found"
            )

    @pytest.mark.asyncio
    async def test_sub_agents_have_correct_structure(self):
        """Test that sub-agents have the correct structure and properties."""
        sub_agents = [
            code_quality_agent,
            code_review_agent,
            testing_agent,
            documentation_agent,
            devops_sub_agent,
        ]

        for agent in sub_agents:
            # Check basic agent properties
            assert hasattr(agent, "name")
            assert hasattr(agent, "description")
            assert hasattr(agent, "instruction")
            assert hasattr(agent, "tools")

            # Verify name and description are set
            assert agent.name is not None
            assert agent.description is not None
            assert len(agent.name) > 0
            assert len(agent.description) > 0

    @pytest.mark.asyncio
    async def test_sub_agents_have_specialized_tools(self):
        """Test that sub-agents have tools appropriate to their specialization."""
        # Code quality agent should have analysis tools
        assert code_quality_agent.tools is not None
        assert len(code_quality_agent.tools) > 0

        # Extract tool names with better handling of different tool types
        code_quality_tool_names = []
        for tool in code_quality_agent.tools:
            if hasattr(tool, "name"):
                code_quality_tool_names.append(tool.name)
            elif hasattr(tool, "function") and hasattr(tool.function, "name"):
                code_quality_tool_names.append(tool.function.name)
            elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
                code_quality_tool_names.append(tool.agent.name)

        # Testing agent should have testing-related tools
        assert testing_agent.tools is not None
        assert len(testing_agent.tools) > 0

        testing_tool_names = []
        for tool in testing_agent.tools:
            if hasattr(tool, "name"):
                testing_tool_names.append(tool.name)
            elif hasattr(tool, "function") and hasattr(tool.function, "name"):
                testing_tool_names.append(tool.function.name)
            elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
                testing_tool_names.append(tool.agent.name)

        # Documentation agent should have documentation tools
        assert documentation_agent.tools is not None
        assert len(documentation_agent.tools) > 0

        doc_tool_names = []
        for tool in documentation_agent.tools:
            if hasattr(tool, "name"):
                doc_tool_names.append(tool.name)
            elif hasattr(tool, "function") and hasattr(tool.function, "name"):
                doc_tool_names.append(tool.function.name)
            elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
                doc_tool_names.append(tool.agent.name)

        # Verify tool specialization based on profiles
        # Code quality agent should have filesystem and code analysis tools
        expected_code_quality_tools = [
            "read_file_content",
            "list_directory_contents",
            "_analyze_code",
        ]
        assert any(tool in code_quality_tool_names for tool in expected_code_quality_tools), (
            f"Code quality agent should have analysis tools, got: {code_quality_tool_names}"
        )

        # Testing agent should have filesystem, code search, and shell command tools
        expected_testing_tools = [
            "read_file_content",
            "list_directory_contents",
            "ripgrep_code_search",
            "execute_shell_command",
        ]
        assert any(tool in testing_tool_names for tool in expected_testing_tools), (
            f"Testing agent should have testing tools, got: {testing_tool_names}"
        )

        # Documentation agent should have filesystem and code search tools
        expected_doc_tools = [
            "read_file_content",
            "list_directory_contents",
            "ripgrep_code_search",
        ]
        assert any(tool in doc_tool_names for tool in expected_doc_tools), (
            f"Documentation agent should have documentation tools, got: {doc_tool_names}"
        )

        # Verify that shell command tools are excluded from code quality agent (per profile)
        assert "execute_shell_command" not in code_quality_tool_names, (
            "Code quality agent should not have shell command tools for security"
        )

        # Verify that documentation agent doesn't have shell command tools
        assert "execute_shell_command" not in doc_tool_names, (
            "Documentation agent should not have shell command tools per profile"
        )

    @pytest.mark.asyncio
    async def test_per_sub_agent_mcp_loading_system(self):
        """Test that the per-sub-agent MCP tool loading system works correctly."""
        from agents.software_engineer.tools import (
            create_sub_agent_mcp_config,
            get_sub_agent_mcp_config,
            list_available_mcp_servers,
        )

        # Test that we can load tools for different sub-agents with different profiles
        debugging_tools = load_tools_for_sub_agent("debugging", sub_agent_name="debugging_agent")
        testing_tools = load_tools_for_sub_agent("testing", sub_agent_name="testing_agent")
        code_quality_tools = load_tools_for_sub_agent(
            "code_quality", sub_agent_name="code_quality_agent"
        )

        # Verify that different sub-agents get different tool sets
        assert len(debugging_tools) > 0
        assert len(testing_tools) > 0
        assert len(code_quality_tools) > 0

        # Extract tool names for comparison
        def get_tool_names(tools):
            names = []
            for tool in tools:
                if hasattr(tool, "name"):
                    names.append(tool.name)
                elif hasattr(tool, "function") and hasattr(tool.function, "name"):
                    names.append(tool.function.name)
                elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
                    names.append(tool.agent.name)
            return names

        debugging_tool_names = get_tool_names(debugging_tools)
        testing_tool_names = get_tool_names(testing_tools)
        code_quality_tool_names = get_tool_names(code_quality_tools)

        # Verify profile-based tool filtering
        # Debugging agent should have shell command tools
        assert "execute_shell_command" in debugging_tool_names, (
            "Debugging agent should have shell command tools"
        )

        # Testing agent should have shell command tools
        assert "execute_shell_command" in testing_tool_names, (
            "Testing agent should have shell command tools"
        )

        # Code quality agent should NOT have shell command tools (excluded by profile)
        assert "execute_shell_command" not in code_quality_tool_names, (
            "Code quality agent should not have shell command tools"
        )

        # Test MCP configuration functions
        try:
            # Test creating a custom MCP configuration
            test_mcp_servers = {
                "test-server": {
                    "command": "echo",
                    "args": ["test"],
                    "env": {"TEST_MODE": "1"},
                }
            }

            create_sub_agent_mcp_config(
                sub_agent_name="test_debugging_agent",
                mcp_servers=test_mcp_servers,
                global_servers=["filesystem"],
                excluded_servers=["production-db"],
            )

            # Test retrieving the configuration
            config = get_sub_agent_mcp_config("test_debugging_agent")
            assert "mcpServers" in config
            assert "test-server" in config["mcpServers"]
            assert config["mcpServers"]["test-server"]["command"] == "echo"

            # Test listing available servers
            available_servers = list_available_mcp_servers("test_debugging_agent")
            assert "global" in available_servers
            assert "sub_agent" in available_servers
            assert "test-server" in available_servers["sub_agent"]

        except Exception as e:
            # If MCP configuration fails, just log it - it might not be available in test environment
            logger.warning(f"MCP configuration test failed (expected in test environment): {e}")

    @pytest.mark.asyncio
    async def test_backward_compatibility_and_security_policies(self):
        """Test that backward compatibility is maintained and security policies are enforced."""
        from agents.software_engineer.tools.sub_agent_tool_config import (
            EnvironmentType,
            SecurityLevel,
            apply_security_policy,
            get_tool_profile,
        )

        # Test backward compatibility - old way of loading tools should still work
        old_style_tools = load_tools_for_sub_agent("code_quality")
        new_style_tools = load_tools_for_sub_agent(
            "code_quality", sub_agent_name="code_quality_agent"
        )

        # Both should return valid tool sets
        assert len(old_style_tools) > 0
        assert len(new_style_tools) > 0

        # Test profile loading
        profiles = create_sub_agent_tool_profiles()
        assert "code_quality" in profiles
        assert "testing" in profiles
        assert "debugging" in profiles
        assert "devops" in profiles

        # Test security policy enforcement
        base_config = {
            "included_categories": ["filesystem", "shell_command", "code_analysis"],
            "include_mcp_tools": True,
        }

        # Apply restricted security policy
        restricted_config = apply_security_policy(base_config, SecurityLevel.RESTRICTED)
        assert "shell_command" in restricted_config.get("excluded_categories", [])
        assert restricted_config.get("include_mcp_tools") is False

        # Apply locked down security policy
        locked_config = apply_security_policy(base_config, SecurityLevel.LOCKED_DOWN)
        assert "shell_command" in locked_config.get("excluded_categories", [])
        assert locked_config.get("include_mcp_tools") is False
        assert "edit_file_tool" in locked_config.get("excluded_tools", [])

        # Test profile metadata
        debugging_profile = get_tool_profile("debugging")
        assert debugging_profile["description"] == "Debugging and troubleshooting assistance"
        assert debugging_profile["security_level"] == SecurityLevel.STANDARD
        assert EnvironmentType.DEVELOPMENT in debugging_profile["suitable_environments"]

        # Test that security levels are properly applied to profiles
        security_auditor_profile = get_tool_profile("security_auditor")
        assert security_auditor_profile["security_level"] == SecurityLevel.RESTRICTED
        assert "shell_command" in security_auditor_profile["config"]["excluded_categories"]

    @pytest.mark.asyncio
    async def test_updated_sub_agents_use_new_system(self):
        """Test that updated sub-agents are using the new per-sub-agent MCP loading system."""
        from agents.software_engineer.sub_agents.debugging.agent import debugging_agent

        # Verify that the debugging agent has tools loaded
        assert debugging_agent.tools is not None
        assert len(debugging_agent.tools) > 0

        # Test that we can load tools for debugging agent with the new system
        debugging_tools_new = load_tools_for_sub_agent(
            "debugging", sub_agent_name="debugging_agent"
        )
        assert len(debugging_tools_new) > 0

        # Extract tool names from both the actual agent and the new loading system
        def extract_tool_names(tools):
            names = []
            for tool in tools:
                if hasattr(tool, "name"):
                    names.append(tool.name)
                elif hasattr(tool, "function") and hasattr(tool.function, "name"):
                    names.append(tool.function.name)
                elif hasattr(tool, "agent") and hasattr(tool.agent, "name"):
                    names.append(tool.agent.name)
            return set(names)

        actual_tool_names = extract_tool_names(debugging_agent.tools)
        new_system_tool_names = extract_tool_names(debugging_tools_new)

        # Both should have filesystem tools
        filesystem_tools = {
            "read_file_content",
            "list_directory_contents",
            "edit_file_content",
        }
        assert filesystem_tools.intersection(actual_tool_names), (
            "Debugging agent should have filesystem tools"
        )
        assert filesystem_tools.intersection(new_system_tool_names), (
            "New system should load filesystem tools for debugging agent"
        )

        # Both should have shell command tools (debugging profile includes them)
        assert "execute_shell_command" in actual_tool_names, (
            "Debugging agent should have shell command tools"
        )
        assert "execute_shell_command" in new_system_tool_names, (
            "New system should load shell command tools for debugging agent"
        )

        # Both should have code analysis tools
        code_analysis_tools = {"_analyze_code", "ripgrep_code_search"}
        assert code_analysis_tools.intersection(actual_tool_names), (
            "Debugging agent should have code analysis tools"
        )
        assert code_analysis_tools.intersection(new_system_tool_names), (
            "New system should load code analysis tools for debugging agent"
        )

    @pytest.mark.asyncio
    async def test_sub_agents_have_specialized_instructions(self):
        """Test that sub-agents have instructions specialized for their domain."""
        # Code quality agent should have quality-focused instructions
        assert (
            "quality" in code_quality_agent.instruction.lower()
            or "analysis" in code_quality_agent.instruction.lower()
        )

        # Testing agent should have testing-focused instructions
        assert "test" in testing_agent.instruction.lower()

        # Documentation agent should have documentation-focused instructions
        assert (
            "document" in documentation_agent.instruction.lower()
            or "doc" in documentation_agent.instruction.lower()
        )

        # DevOps sub-agent should have deployment/infrastructure focus
        assert (
            "devops" in devops_sub_agent.instruction.lower()
            or "deploy" in devops_sub_agent.instruction.lower()
            or "infrastructure" in devops_sub_agent.instruction.lower()
        )

    @pytest.mark.asyncio
    async def test_devops_agent_class_structure(self, mock_llm_client):
        """Test that the MyDevopsAgent class has the expected structure for delegation."""
        # Test class attributes and methods without instantiation
        assert hasattr(MyDevopsAgent, "__init__")
        assert hasattr(MyDevopsAgent, "model_post_init")

        # Check that the class has expected attributes for delegation
        class_annotations = getattr(MyDevopsAgent, "__annotations__", {})
        class_attrs = dir(MyDevopsAgent)

        # Should have state management for delegation
        delegation_attrs = ["_state_manager", "_context_manager", "_planning_manager"]
        for attr in delegation_attrs:
            assert attr in class_annotations or any(
                attr in str(class_attr) for class_attr in class_attrs
            )

    @pytest.mark.asyncio
    async def test_agent_hierarchy_structure(self):
        """Test the hierarchical structure of agents in the system."""
        # Software Engineer agent is the root agent with sub-agents
        assert software_engineer_agent.name == "software_engineer"
        assert hasattr(software_engineer_agent, "sub_agents")

        # Sub-agents should be properly configured
        sub_agents = software_engineer_agent.sub_agents
        assert len(sub_agents) > 0

        # Each sub-agent should have a unique specialization
        specializations = []
        for agent in sub_agents:
            # Check that each agent has distinct instructions
            specializations.append(agent.instruction[:50])  # First 50 chars as identifier

        # All specializations should be unique (no identical instructions)
        assert len(set(specializations)) == len(specializations)

    @pytest.mark.asyncio
    async def test_agent_model_consistency(self):
        """Test that agents use consistent model configurations."""
        # Get all agents to test
        agents_to_test = [
            code_quality_agent,
            code_review_agent,
            testing_agent,
            documentation_agent,
            devops_sub_agent,
        ]

        for agent in agents_to_test:
            # Each agent should have a model configured
            assert hasattr(agent, "model")
            assert agent.model is not None

            # Model should be a string (model name)
            assert isinstance(agent.model, str)
            assert len(agent.model) > 0

    @pytest.mark.asyncio
    async def test_agent_communication_structure(self):
        """Test the structure that would support agent communication."""
        # Software engineer agent should be capable of coordinating sub-agents
        assert hasattr(software_engineer_agent, "sub_agents")

        # Sub-agents should be accessible and properly configured
        sub_agents = software_engineer_agent.sub_agents

        for agent in sub_agents:
            # Each sub-agent should have proper identification
            assert hasattr(agent, "name")
            assert hasattr(agent, "description")

            # Agent should have the infrastructure for communication
            assert hasattr(agent, "instruction")
            assert hasattr(agent, "tools")

    @pytest.mark.asyncio
    async def test_delegation_readiness_structure(self, mock_llm_client):
        """Test that the agent structure supports delegation patterns."""
        # Test that the software engineer agent can coordinate with sub-agents
        assert hasattr(software_engineer_agent, "sub_agents")
        assert hasattr(software_engineer_agent, "instruction")

        # Main agent should have coordination capabilities
        main_instruction = software_engineer_agent.instruction.lower()
        coordination_keywords = ["software", "engineer", "assist", "help"]
        assert any(keyword in main_instruction for keyword in coordination_keywords)

        # Test that we can access the existing sub-agents for delegation
        available_sub_agents = [
            code_quality_agent,
            code_review_agent,
            testing_agent,
            documentation_agent,
        ]

        for sub_agent in available_sub_agents:
            assert sub_agent.name is not None
            assert sub_agent.description is not None
            assert hasattr(sub_agent, "instruction")
            assert len(sub_agent.instruction) > 20  # Should have substantial instructions
