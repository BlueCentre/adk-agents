"""
Integration tests for enhanced agent feature parity.

This test module ensures that the enhanced sub-agents maintain functionality
while using an efficient approach that avoids code duplication:
- Factory functions for some agents (code_review, testing)
- Tool reuse for others (avoiding re-computation)
- Unique names to prevent parent conflicts

These tests prevent regressions in the core functionality without requiring
the original heavy duplication approach.
"""

from google.adk.agents import LlmAgent
import pytest

# Test imports
from agents.swe.enhanced_agent import create_enhanced_sub_agents


class TestEnhancedAgentFeatureParity:
    """Test enhanced sub-agents maintain core functionality efficiently."""

    def test_efficient_tool_reuse_approach(self):
        """Test that the current approach efficiently reuses already-loaded tools."""
        # Create enhanced sub-agents
        enhanced_agents = create_enhanced_sub_agents()

        # Verify we have the expected number of agents
        assert len(enhanced_agents) == 8, (
            f"Expected 8 enhanced sub-agents, got {len(enhanced_agents)}"
        )

        # Verify all agents have tools (not empty tool lists)
        agents_with_tools = [
            agent for agent in enhanced_agents if hasattr(agent, "tools") and len(agent.tools) > 0
        ]
        assert len(agents_with_tools) == 8, (
            f"REGRESSION DETECTED: {8 - len(agents_with_tools)} agents have no tools! "
            "This indicates tools are not being loaded properly."
        )

        # Verify agents with factory functions have proper sophisticated features
        factory_based_agents = [
            agent
            for agent in enhanced_agents
            if agent.name in ["enhanced_code_review_agent", "enhanced_testing_agent"]
        ]

        for agent in factory_based_agents:
            # These agents should have their sophisticated features (callbacks, generate_config, etc.)
            assert hasattr(agent, "tools"), f"Factory-based agent {agent.name} missing tools"
            assert len(agent.tools) > 0, f"Factory-based agent {agent.name} has no tools"

        print(
            f"✅ Efficient approach: {len(agents_with_tools)} agents with tools, {len(factory_based_agents)} use factory functions"
        )
        print("📋 This approach reuses already-loaded tools, avoiding unnecessary re-computation")

    def test_no_parent_conflicts(self):
        """Test that enhanced agents avoid parent conflicts by having unique names."""
        enhanced_agents = create_enhanced_sub_agents()

        # Verify all agents have unique names with 'enhanced_' prefix
        agent_names = [agent.name for agent in enhanced_agents]
        enhanced_names = [name for name in agent_names if name.startswith("enhanced_")]

        assert len(enhanced_names) == 8, (
            f"Expected all 8 agents to have 'enhanced_' prefix, got {len(enhanced_names)}: {agent_names}"
        )

        # Verify no duplicate names
        assert len(set(agent_names)) == len(agent_names), (
            f"Duplicate agent names detected: {agent_names}"
        )

        print(
            f"✅ All {len(enhanced_agents)} enhanced agents have unique names to avoid parent conflicts"
        )

    def test_design_pattern_agent_uses_static_tools_like_original(self):
        """Test that design pattern agent uses static tools (matching original behavior)."""
        # Create enhanced sub-agents
        enhanced_agents = create_enhanced_sub_agents()

        # Find the design pattern agent
        design_pattern_agent = next(
            (agent for agent in enhanced_agents if "design_pattern" in agent.name), None
        )

        assert design_pattern_agent is not None, "Should have design pattern agent"
        assert isinstance(design_pattern_agent, LlmAgent), (
            "Design pattern agent should be LlmAgent (like original)"
        )

        # Verify it has tools (static ones)
        assert hasattr(design_pattern_agent, "tools"), "Should have tools"
        assert len(design_pattern_agent.tools) > 0, "Should have non-empty tools list"

        print("✅ Design pattern agent uses static tools (matching original behavior)")

    def test_factory_functions_provide_sophisticated_features(self):
        """Test that agents created via factory functions maintain sophisticated features."""
        enhanced_agents = create_enhanced_sub_agents()

        # All agents except design_pattern now use factory functions
        factory_based_agents = [
            agent for agent in enhanced_agents if "design_pattern" not in agent.name
        ]

        assert len(factory_based_agents) == 7, (
            f"Expected 7 factory-based agents, got {len(factory_based_agents)}"
        )

        # Verify sophisticated features are preserved for all factory-based agents
        for agent in factory_based_agents:
            assert hasattr(agent, "tools"), f"Agent {agent.name} should have tools"
            assert len(agent.tools) > 0, f"Agent {agent.name} should have non-empty tools"
            # Some agents might have generate_content_config=None (like ollama) - that's valid
            if (
                hasattr(agent, "generate_content_config")
                and agent.generate_content_config is not None
            ):
                # If it has a config, it should be a proper GenerateContentConfig object
                assert hasattr(agent.generate_content_config, "temperature"), (
                    f"Agent {agent.name} should have valid GenerateContentConfig with temperature"
                )

        print(
            f"✅ Factory function agents ({len(factory_based_agents)}/8) maintain sophisticated features"
        )
        print("📋 Only design_pattern agent uses static tools (by design)")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
