"""
Integration Tests for Single Agent Patterns

This module contains integration tests for core single agent patterns
based on Google ADK integration testing approaches. These tests focus
on fundamental agent behaviors and instruction compliance.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import agent components - use existing instances instead of creating new ones
from agents.devops.devops_agent import MyDevopsAgent
from agents.software_engineer.agent import root_agent as software_engineer_agent

# Test utilities
from tests.fixtures.test_helpers import (
    create_mock_llm_client,
    create_mock_session_state,
    create_test_workspace,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.foundation
class TestSingleAgentPatterns:
    """Integration tests for single agent patterns and behaviors."""

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
    async def test_single_agent_basic_response_structure(
        self, mock_llm_client, mock_session_state
    ):
        """Test basic agent response generation structure."""
        # Test the software engineer agent structure
        assert hasattr(software_engineer_agent, "name")
        assert hasattr(software_engineer_agent, "description")
        assert hasattr(software_engineer_agent, "instruction")

        # Verify basic properties are set
        assert software_engineer_agent.name == "software_engineer"
        assert software_engineer_agent.description is not None
        assert software_engineer_agent.instruction is not None
        assert len(software_engineer_agent.instruction) > 0

    @pytest.mark.asyncio
    async def test_single_agent_instruction_structure(
        self, mock_llm_client, mock_session_state
    ):
        """Test agent instruction structure and content."""
        # Verify the software engineer agent has proper instructions
        assert hasattr(software_engineer_agent, "instruction")
        instruction = software_engineer_agent.instruction

        # Instructions should contain role definition
        assert isinstance(instruction, str)
        assert len(instruction) > 50  # Should be substantial

        # Should mention software engineering or development
        assert any(
            keyword in instruction.lower()
            for keyword in [
                "software",
                "engineer",
                "development",
                "code",
                "programming",
            ]
        )

    @pytest.mark.asyncio
    async def test_single_agent_tool_availability(
        self, mock_llm_client, mock_session_state, test_workspace
    ):
        """Test agent has tools configured correctly."""
        # Verify the software engineer agent has tools
        assert hasattr(software_engineer_agent, "tools")
        assert software_engineer_agent.tools is not None
        assert len(software_engineer_agent.tools) > 0

        # Check that tools have proper structure
        for tool in software_engineer_agent.tools:
            assert hasattr(tool, "name") or hasattr(tool, "__class__")

    @pytest.mark.asyncio
    async def test_single_agent_model_configuration(
        self, mock_llm_client, mock_session_state
    ):
        """Test agent model configuration."""
        # Verify the software engineer agent has a model configured
        assert hasattr(software_engineer_agent, "model")
        assert software_engineer_agent.model is not None

        # Model should be a valid model specification
        assert isinstance(software_engineer_agent.model, str) or hasattr(
            software_engineer_agent.model, "model"
        )

    @pytest.mark.asyncio
    async def test_single_agent_sub_agent_structure(
        self, mock_llm_client, mock_session_state
    ):
        """Test agent sub-agent management structure."""
        # Verify the software engineer agent has sub-agents
        assert hasattr(software_engineer_agent, "sub_agents")
        assert software_engineer_agent.sub_agents is not None
        assert len(software_engineer_agent.sub_agents) > 0

        # Each sub-agent should have proper structure
        for sub_agent in software_engineer_agent.sub_agents:
            assert hasattr(sub_agent, "name")
            assert hasattr(sub_agent, "description")

    @pytest.mark.asyncio
    async def test_agent_class_structure(self, mock_llm_client, mock_session_state):
        """Test the MyDevopsAgent class has the expected structure."""
        # Test class attributes and methods without instantiation
        assert hasattr(MyDevopsAgent, "__init__")
        assert hasattr(MyDevopsAgent, "model_post_init")

        # Check that the class has expected private attributes
        private_attrs = [attr for attr in dir(MyDevopsAgent) if attr.startswith("_")]
        expected_private = [
            "_console",
            "_status_indicator",
            "_state_manager",
            "_context_manager",
        ]

        for expected_attr in expected_private:
            # The class should define these as private attributes
            assert expected_attr in MyDevopsAgent.__annotations__ or any(
                expected_attr in str(attr) for attr in private_attrs
            )

    @pytest.mark.asyncio
    async def test_agent_output_capabilities(self, mock_llm_client, mock_session_state):
        """Test agent output and response capabilities."""
        # Test the software engineer agent's output configuration
        assert hasattr(software_engineer_agent, "output_key")
        assert software_engineer_agent.output_key == "software_engineer"

        # Agent should have proper identification
        assert software_engineer_agent.name is not None
        assert len(software_engineer_agent.name) > 0

    @pytest.mark.asyncio
    async def test_agent_role_consistency_structure(
        self, mock_llm_client, mock_session_state
    ):
        """Test agent maintains consistent role structure."""
        # Check that the software engineer agent has role-appropriate configuration
        instruction = software_engineer_agent.instruction.lower()

        # Should have software engineering focus
        engineering_keywords = [
            "software",
            "development",
            "code",
            "engineer",
            "programming",
        ]
        assert any(keyword in instruction for keyword in engineering_keywords)

        # Should have sub-agents for specialized tasks
        assert (
            len(software_engineer_agent.sub_agents) > 3
        )  # Should have multiple specializations

    @pytest.mark.asyncio
    async def test_agent_boundary_and_scope_structure(
        self, mock_llm_client, mock_session_state
    ):
        """Test agent has proper boundary and scope definition."""
        # Software engineer agent should have defined scope through sub-agents
        sub_agent_names = [agent.name for agent in software_engineer_agent.sub_agents]

        # Should have specialized sub-agents for different domains
        expected_specializations = ["code", "test", "review", "quality", "document"]
        found_specializations = []

        for specialization in expected_specializations:
            if any(specialization in name.lower() for name in sub_agent_names):
                found_specializations.append(specialization)

        # Should have at least 3 different specializations
        assert len(found_specializations) >= 3
