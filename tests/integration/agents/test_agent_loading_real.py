"""Integration tests for real agent loading scenarios.

This test module verifies that real agent modules can be loaded without mocking,
catching configuration errors that unit tests with mocks might miss.

BACKGROUND:
Unit tests use mocks for AgentLoader and don't catch real-world failures like:
- Agent validation errors (e.g., sub-agents with multiple parents)
- Import errors in agent modules
- Configuration issues that only manifest during actual loading

This test suite fills that gap by testing the actual agent loading pipeline
without mocks, ensuring that the CLI command 'uv run agent run <module>' works.

The test was created after a real scenario where:
- All unit tests passed with mocks
- The real command 'uv run agent run agents.swe.enhanced_agent' failed
- The failure was due to a validation error not caught by mocked tests
"""

from unittest.mock import patch

import pytest

from src.wrapper.adk.cli.utils.agent_loader import AgentLoader


class TestRealAgentLoading:
    """Test real agent loading scenarios that could fail in production."""

    def test_agent_module_imports_successfully(self):
        """Test that common agent modules can be imported without errors."""
        agent_loader = AgentLoader()

        # Test basic agent modules that should always work
        working_modules = [
            "agents.devops",
            "agents.software_engineer",
        ]

        for module_name in working_modules:
            try:
                agent = agent_loader.load_agent(module_name)
                assert agent is not None
                assert hasattr(agent, "name")
                print(f"✅ Successfully loaded {module_name}: {agent.name}")
            except Exception as e:
                pytest.fail(f"Failed to load {module_name}: {e!s}")

    def test_enhanced_agent_loading_success(self):
        """Test enhanced agent loading now works after fixing parent conflicts."""
        agent_loader = AgentLoader()

        # This agent should now load successfully after fixing parent conflicts
        try:
            agent = agent_loader.load_agent("agents.swe.enhanced_agent")
            assert agent is not None
            assert hasattr(agent, "name")
            assert agent.name == "enhanced_software_engineer"
            print(f"✅ Successfully loaded agents.swe.enhanced_agent: {agent.name}")
        except Exception as e:
            pytest.fail(f"Enhanced agent should load successfully but failed: {e!s}")

    @pytest.mark.parametrize(
        "agent_module",
        [
            "agents.devops",
            "agents.software_engineer",
        ],
    )
    def test_agent_loading_end_to_end_mock_free(self, agent_module):
        """Test end-to-end agent loading without any mocks."""
        agent_loader = AgentLoader()

        # Load the agent (no mocks)
        agent = agent_loader.load_agent(agent_module)

        # Verify basic agent properties
        assert agent is not None
        assert hasattr(agent, "name")
        assert hasattr(agent, "description")

        # Check for either 'instruction' or 'instructions' (agents use different names)
        assert hasattr(agent, "instruction") or hasattr(agent, "instructions")

        # Verify agent name is not empty
        assert agent.name.strip() != ""

        # Verify the agent has tools (if it should)
        if hasattr(agent, "tools"):
            assert isinstance(agent.tools, list)

        print(f"✅ End-to-end validation passed for {agent_module}")

    def test_cli_command_simulation_with_real_agent_loading(self):
        """Simulate the CLI command execution path with real agent loading."""
        from src.wrapper.adk.cli.utils import envs

        # Test agent module that should work
        agent_module_name = "agents.devops"

        # Load environment variables for the agent (like the real CLI does)
        envs.load_dotenv_for_agent(agent_module_name)

        # Create an agent loader and load the agent (like the real CLI does)
        agent_loader = AgentLoader()
        agent = agent_loader.load_agent(agent_module_name)

        # Verify the agent loaded successfully
        assert agent is not None
        assert agent.name is not None

        print(f"✅ CLI simulation test passed for {agent_module_name}")

    def test_exact_cli_command_scenario_now_works(self):
        """
        Test the exact scenario that was failing now works:
        'uv run agent run agents.swe.enhanced_agent'
        """
        from src.wrapper.adk.cli.utils import envs

        # Test the exact scenario that was previously failing
        target_agent = "agents.swe.enhanced_agent"

        # Load environment variables for the agent (like the real CLI does)
        envs.load_dotenv_for_agent(target_agent)

        # Create an agent loader and load the agent (like the real CLI does)
        agent_loader = AgentLoader()

        # This should now work successfully after fixing parent conflicts
        try:
            agent = agent_loader.load_agent(target_agent)
            assert agent is not None
            assert hasattr(agent, "name")
            assert agent.name == "enhanced_software_engineer"
            print(f"✅ Previously failing CLI scenario now works: {target_agent}")
        except Exception as e:
            pytest.fail(f"Previously failing agent should now work but failed: {e!s}")

    def test_working_cli_command_scenarios(self):
        """Test CLI command scenarios that should work correctly."""
        from src.wrapper.adk.cli.utils import envs

        working_agents = [
            "agents.devops",
            "agents.software_engineer",
        ]

        for agent_module in working_agents:
            # Load environment variables for the agent (like the real CLI does)
            envs.load_dotenv_for_agent(agent_module)

            # Create an agent loader and load the agent (like the real CLI does)
            agent_loader = AgentLoader()
            agent = agent_loader.load_agent(agent_module)

            # Verify the agent loaded successfully
            assert agent is not None
            assert agent.name is not None

            print(f"✅ Working CLI scenario passed for {agent_module}")

    def test_real_world_cli_execution_path(self):
        """Test the real-world execution path that mirrors the actual CLI command."""
        import asyncio

        from src.wrapper.adk.cli.cli import run_cli

        # Test with a known working agent
        agent_module = "agents.devops"

        # Mock out the interactive parts since we can't run them in tests
        with patch("src.wrapper.adk.cli.cli.run_interactively") as mock_run_interactive:
            mock_run_interactive.return_value = None

            # This should not raise any exceptions during the setup phase
            try:
                # This mirrors the exact path taken by the CLI command
                asyncio.run(
                    run_cli(
                        agent_module_name=agent_module,
                        input_file=None,
                        saved_session_file=None,
                        save_session=False,
                        session_id=None,
                        ui_theme=None,
                        tui=False,
                    )
                )
                print(f"✅ Real-world CLI execution path test passed for {agent_module}")
            except Exception as e:
                pytest.fail(f"Real-world CLI execution failed for {agent_module}: {e!s}")

    def test_problematic_agents_fail_gracefully(self):
        """Test that problematic agents fail with clear error messages."""
        agent_loader = AgentLoader()

        # Test a non-existent agent that should fail
        with pytest.raises(ValueError) as exc_info:
            agent_loader.load_agent("agents.nonexistent.fake_agent")

        error_message = str(exc_info.value)

        # Verify the error message is informative
        assert "agents.nonexistent.fake_agent" in error_message

        print("✅ Problematic agent failed gracefully with clear error message")

    def test_agent_import_error_handling(self):
        """Test handling of non-existent agent modules."""
        agent_loader = AgentLoader()

        with pytest.raises(ValueError) as exc_info:
            agent_loader.load_agent("agents.nonexistent.fake_agent")

        error_message = str(exc_info.value)
        assert "agents.nonexistent.fake_agent" in error_message

        print("✅ Non-existent agent handled gracefully")
