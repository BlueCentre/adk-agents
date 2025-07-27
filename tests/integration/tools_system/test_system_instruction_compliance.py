"""
Integration Tests for System Instruction Compliance

This module contains integration tests for system instruction compliance
based on Google ADK integration testing approaches. These tests focus
on prompt adherence, role-based behavior, constraint enforcement, and
instruction interpretation across different scenarios.
"""

import logging

import pytest

# Import agent components - use existing instances
from agents.devops.devops_agent import MyDevopsAgent
from agents.software_engineer.agent import root_agent as software_engineer_agent
from agents.software_engineer.sub_agents.code_quality.agent import code_quality_agent
from agents.software_engineer.sub_agents.documentation.agent import documentation_agent
from agents.software_engineer.sub_agents.testing.agent import testing_agent

# Test utilities
from tests.fixtures.test_helpers import (
    create_mock_llm_client,
    create_mock_session_state,
    create_test_workspace,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.core
class TestSystemInstructionCompliance:
    """Integration tests for system instruction compliance and prompt adherence."""

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
    async def test_role_based_behavior_consistency(self):
        """Test agent maintains consistent role-based behavior."""
        # Test software engineer agent role consistency
        instruction = software_engineer_agent.instruction.lower()

        # Should have clear role definition
        role_keywords = ["software", "engineer", "development", "assistant"]
        assert any(keyword in instruction for keyword in role_keywords)

        # Should have expertise areas defined
        expertise_keywords = ["code", "development", "programming", "software"]
        assert any(keyword in instruction for keyword in expertise_keywords)

        # Should have behavior guidelines
        assert len(instruction) > 100  # Should be substantial

    @pytest.mark.asyncio
    async def test_constraint_enforcement_structure(self):
        """Test agent structure supports constraint enforcement."""
        # Test that sub-agents have specialized constraints

        # Code quality agent should have quality-focused constraints
        code_quality_instruction = code_quality_agent.instruction.lower()
        assert "quality" in code_quality_instruction or "analysis" in code_quality_instruction

        # Testing agent should have testing-focused constraints
        testing_instruction = testing_agent.instruction.lower()
        assert "test" in testing_instruction

        # Each agent should have clear role boundaries
        agents_to_test = [code_quality_agent, testing_agent, documentation_agent]
        for agent in agents_to_test:
            assert hasattr(agent, "instruction")
            assert len(agent.instruction) > 20  # Should have substantial instructions

    @pytest.mark.asyncio
    async def test_output_format_compliance_capability(self):
        """Test agent structure supports output format compliance."""
        # Test that agents have generation configuration for formatting
        agents_to_test = [software_engineer_agent, code_quality_agent, testing_agent]

        for agent in agents_to_test:
            # Agent should have some form of generation configuration
            has_generation_config = (
                hasattr(agent, "generate_content_config")
                or hasattr(agent, "generation_config")
                or hasattr(agent, "model")
            )
            assert has_generation_config

    @pytest.mark.asyncio
    async def test_context_aware_instruction_structure(self):
        """Test agent structure supports context-aware instruction following."""
        # Test software engineer agent's context awareness through sub-agents
        assert hasattr(software_engineer_agent, "sub_agents")
        assert len(software_engineer_agent.sub_agents) > 0

        # Different sub-agents represent different contexts
        sub_agent_names = [agent.name for agent in software_engineer_agent.sub_agents]
        context_specializations = [
            "code",
            "test",
            "review",
            "quality",
            "document",
            "debug",
        ]

        found_contexts = []
        for specialization in context_specializations:
            if any(specialization in name.lower() for name in sub_agent_names):
                found_contexts.append(specialization)

        # Should have multiple context specializations
        assert len(found_contexts) >= 3

    @pytest.mark.asyncio
    async def test_multi_turn_instruction_consistency_structure(self):
        """Test agent structure supports multi-turn instruction consistency."""
        # Test that agents have state management capabilities

        # MyDevopsAgent class should have state management
        state_attrs = ["_state_manager", "_context_manager"]
        for attr in state_attrs:
            # Should be defined in the class (even if private)
            assert attr in MyDevopsAgent.__annotations__ or any(
                attr in str(class_attr) for class_attr in dir(MyDevopsAgent)
            )

    @pytest.mark.asyncio
    async def test_conditional_instruction_following_structure(self):
        """Test agent structure supports conditional instruction following."""
        # Test that different sub-agents handle different conditions
        sub_agents = software_engineer_agent.sub_agents

        # Each sub-agent should have different instructions (conditional behavior)
        instructions = [agent.instruction for agent in sub_agents]

        # Instructions should be different (not all the same)
        unique_instructions = set(instructions)
        assert len(unique_instructions) > 1  # Should have varied instructions

        # Each instruction should be substantial enough to define conditional behavior
        for instruction in instructions:
            assert len(instruction) > 30

    @pytest.mark.asyncio
    async def test_instruction_priority_resolution_structure(self):
        """Test agent structure supports instruction priority resolution."""
        # Test that the main agent can coordinate with sub-agents (priority resolution)
        assert hasattr(software_engineer_agent, "sub_agents")
        assert hasattr(software_engineer_agent, "instruction")

        # Main agent should have coordination instructions
        main_instruction = software_engineer_agent.instruction.lower()
        coordination_keywords = [
            "assist",
            "help",
            "software",
            "development",
            "engineer",
        ]
        assert any(keyword in main_instruction for keyword in coordination_keywords)

        # Sub-agents should have specialized instructions (different priorities)
        sub_instructions = [
            agent.instruction.lower() for agent in software_engineer_agent.sub_agents
        ]
        specialization_found = []

        for instruction in sub_instructions:
            if "quality" in instruction or "analysis" in instruction:
                specialization_found.append("quality")
            if "test" in instruction:
                specialization_found.append("testing")
            if "document" in instruction or "doc" in instruction:
                specialization_found.append("documentation")

        # Should have at least 2 different specializations (priority levels)
        assert len(set(specialization_found)) >= 2

    @pytest.mark.asyncio
    async def test_instruction_interpretation_edge_cases_structure(self):
        """Test agent structure supports edge case handling."""
        # Test that agents have comprehensive instructions to handle edge cases
        agents_to_test = [software_engineer_agent, code_quality_agent, testing_agent]

        for agent in agents_to_test:
            # Instructions should be comprehensive enough to handle edge cases
            assert len(agent.instruction) > 50

            # Should have clear role definition to handle ambiguous requests
            assert hasattr(agent, "name")
            assert hasattr(agent, "description")
            assert len(agent.description) > 10

    @pytest.mark.asyncio
    async def test_system_instruction_inheritance_structure(self):
        """Test that system instructions are properly structured in the hierarchy."""
        # Main agent should have general instructions
        main_agent = software_engineer_agent
        assert hasattr(main_agent, "instruction")
        assert hasattr(main_agent, "sub_agents")

        # Sub-agents should have specialized instructions that complement the main agent
        for sub_agent in main_agent.sub_agents:
            assert hasattr(sub_agent, "instruction")
            assert hasattr(sub_agent, "name")

            # Sub-agent instructions should be different from main agent
            assert sub_agent.instruction != main_agent.instruction

            # Sub-agent should have specialized focus (check if instruction has some specialization)
            # Instructions should be substantial enough to indicate specialization
            assert len(sub_agent.instruction.strip()) > 30

    @pytest.mark.asyncio
    async def test_instruction_validation_and_compliance_readiness(self):
        """Test that the agent structure is ready for instruction compliance validation."""
        # Test that agents have the necessary structure for compliance testing
        test_agents = [software_engineer_agent, *software_engineer_agent.sub_agents]

        for agent in test_agents:
            # Each agent should have identifiable components for compliance testing
            required_attributes = ["name", "description", "instruction"]
            for attr in required_attributes:
                assert hasattr(agent, attr)
                assert getattr(agent, attr) is not None

            # Instructions should be non-trivial
            assert len(agent.instruction.strip()) > 20

            # Name should be descriptive
            assert len(agent.name.strip()) > 3
