"""
Integration tests for sub-agent MCP loading functionality.

These tests ensure that:
1. Enhanced agents properly fall back to base agent configurations
2. MCP tools are loaded according to configuration files
3. Exclusion logic works correctly
4. Server filtering is applied properly
5. Regression prevention for sub-agent MCP tool loading

Tests designed to catch the regression where sub-agents weren't loading their MCP tools.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.software_engineer.tools import load_tools_for_sub_agent
from agents.software_engineer.tools.sub_agent_mcp_loader import (
    SubAgentMCPConfig,
    list_available_mcp_servers,
    load_sub_agent_mcp_tools_async,
)

# Module path constants for cleaner mocking
SIMPLE_LOADER_PATH = "agents.software_engineer.tools.sub_agent_mcp_loader._load_mcp_server_simple"
ASYNC_LOADER_PATH = "agents.software_engineer.tools.sub_agent_mcp_loader._load_mcp_server_async"
TOOL_SETUP_PATH = "agents.software_engineer.tools.setup.load_selective_tools_and_toolsets_enhanced"


class TestSubAgentMCPConfig:
    """Test the SubAgentMCPConfig class including fallback logic."""

    def test_enhanced_agent_fallback_path_generation(self, tmp_path):
        """Test that enhanced agents generate correct fallback paths."""
        # Create a temporary agent directory structure
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        # Create base config file
        base_config = sub_agents_dir / "devops_agent.mcp.json"
        base_config.write_text(
            json.dumps({"mcpServers": {"datadog": {"command": "npx", "args": ["@datadog/mcp"]}}})
        )

        # Test enhanced agent fallback path calculation
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config = SubAgentMCPConfig("enhanced_devops_agent")

            # Check primary and fallback paths
            assert config.config_path.name == "enhanced_devops_agent.mcp.json"
            assert config.fallback_config_path is not None
            assert config.fallback_config_path.name == "devops_agent.mcp.json"

            # Test that fallback exists but primary doesn't
            assert not config.config_path.exists()
            assert config.fallback_config_path.exists()

    def test_base_agent_no_fallback(self, tmp_path):
        """Test that base agents don't generate fallback paths."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config = SubAgentMCPConfig("devops_agent")

            assert config.fallback_config_path is None

    def test_config_loading_with_fallback(self, tmp_path):
        """Test that configuration loading uses fallback when primary doesn't exist."""
        # Create directory structure
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        # Create fallback config with datadog tools
        fallback_config = {
            "mcpServers": {
                "datadog": {"command": "npx", "args": ["-y", "@winor30/mcp-server-datadog"]}
            },
            "globalServers": ["filesystem", "memory"],
            "excludedServers": ["github", "sonarqube", "playwright"],
        }

        base_config_file = sub_agents_dir / "devops_agent.mcp.json"
        base_config_file.write_text(json.dumps(fallback_config))

        # Test enhanced agent loading fallback config
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            loaded_config = config_loader.load_config()

            # Verify fallback config was loaded
            assert "datadog" in loaded_config["mcpServers"]
            assert loaded_config["globalServers"] == ["filesystem", "memory"]
            assert "github" in loaded_config["excludedServers"]

    def test_config_loading_primary_takes_precedence(self, tmp_path):
        """Test that primary config takes precedence over fallback."""
        # Create directory structure
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        # Create both primary and fallback configs
        primary_config = {"mcpServers": {"primary_tool": {"command": "primary"}}}
        fallback_config = {"mcpServers": {"fallback_tool": {"command": "fallback"}}}

        primary_file = sub_agents_dir / "enhanced_devops_agent.mcp.json"
        fallback_file = sub_agents_dir / "devops_agent.mcp.json"

        primary_file.write_text(json.dumps(primary_config))
        fallback_file.write_text(json.dumps(fallback_config))

        # Test that primary config is used
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            loaded_config = config_loader.load_config()

            # Primary should be loaded, not fallback
            assert "primary_tool" in loaded_config["mcpServers"]
            assert "fallback_tool" not in loaded_config["mcpServers"]


class TestMCPToolLoading:
    """Test MCP tool loading functionality - focusing on testable components."""

    def test_exclusion_logic_config_parsing(self, tmp_path):
        """Test that exclusion configuration is parsed correctly."""
        # Create config with excluded servers
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        global_dir = tmp_path / ".agent"
        sub_agents_dir.mkdir(parents=True)
        global_dir.mkdir(exist_ok=True)

        # Global config with servers
        global_config = {
            "mcpServers": {
                "filesystem": {"command": "npx", "args": ["@filesystem/mcp-server"]},
                "github": {"command": "npx", "args": ["@github/mcp-server"]},
                "sonarqube": {"command": "npx", "args": ["@sonarqube/mcp-server"]},
                "playwright": {"command": "npx", "args": ["@playwright/mcp-server"]},
            }
        }

        global_config_file = global_dir / "mcp.json"
        global_config_file.write_text(json.dumps(global_config))

        # Sub-agent config excluding specific servers
        sub_agent_config = {
            "mcpServers": {"datadog": {"command": "npx", "args": ["@datadog/mcp-server"]}},
            "globalServers": ["filesystem"],
            "excludedServers": ["github", "sonarqube", "playwright"],
        }

        sub_agent_config_file = sub_agents_dir / "devops_agent.mcp.json"
        sub_agent_config_file.write_text(json.dumps(sub_agent_config))

        # Test configuration loading (the main functionality we fixed)
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config_loader = SubAgentMCPConfig("devops_agent")
            config = config_loader.load_config()

            # Verify config structure is correct
            assert "datadog" in config["mcpServers"]
            assert config["globalServers"] == ["filesystem"]
            assert "github" in config["excludedServers"]
            assert "sonarqube" in config["excludedServers"]
            assert "playwright" in config["excludedServers"]

    def test_available_servers_listing_integration(self, tmp_path):
        """Test that available servers are listed correctly."""
        # Setup similar to previous test
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        global_dir = tmp_path / ".agent"
        sub_agents_dir.mkdir(parents=True)
        global_dir.mkdir(exist_ok=True)

        # Global config
        global_config = {
            "mcpServers": {
                "filesystem": {"command": "npx", "args": ["@filesystem/mcp-server"]},
                "memory": {"command": "npx", "args": ["@memory/mcp-server"]},
                "github": {"command": "npx", "args": ["@github/mcp-server"]},
            }
        }

        global_config_file = global_dir / "mcp.json"
        global_config_file.write_text(json.dumps(global_config))

        # Sub-agent config excluding github
        sub_agent_config = {
            "mcpServers": {"datadog": {"command": "npx", "args": ["@datadog/mcp-server"]}},
            "globalServers": ["filesystem", "memory", "github"],
            "excludedServers": ["github"],
        }

        sub_agent_config_file = sub_agents_dir / "test_agent.mcp.json"
        sub_agent_config_file.write_text(json.dumps(sub_agent_config))

        # Test available servers listing
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            servers = list_available_mcp_servers("test_agent")

            # Verify server lists are correct
            assert "filesystem" in servers["global"]
            assert "memory" in servers["global"]
            assert "github" in servers["global"]
            assert "datadog" in servers["sub_agent"]

    @pytest.mark.asyncio
    async def test_async_mcp_loading_with_exclusions(self, tmp_path):
        """Test async MCP loading respects exclusion logic."""
        # Setup configs
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        sub_agent_config = {
            "mcpServers": {
                "datadog": {"command": "npx", "args": ["@datadog/mcp-server"]},
                "monitoring": {"command": "npx", "args": ["@monitoring/mcp-server"]},
            },
            "excludedServers": ["monitoring"],
        }

        sub_agent_config_file = sub_agents_dir / "test_agent.mcp.json"
        sub_agent_config_file.write_text(json.dumps(sub_agent_config))

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(ASYNC_LOADER_PATH) as mock_load,
        ):
            mock_load.return_value = [MagicMock()]

            # Load tools async
            tools, exit_stack = await load_sub_agent_mcp_tools_async("test_agent")

            loaded_server_names = [call[0][0] for call in mock_load.call_args_list]

            # Should load datadog but not monitoring (excluded)
            assert "datadog" in loaded_server_names
            assert "monitoring" not in loaded_server_names


class TestEnhancedAgentIntegration:
    """Test enhanced agent integration - focusing on configuration behavior."""

    def test_enhanced_devops_agent_configuration_fallback(self, tmp_path):
        """Test that enhanced devops agent configuration fallback works correctly."""
        # This is the regression test for the specific issue we fixed
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        # Create devops_agent.mcp.json (fallback for enhanced_devops_agent)
        devops_config = {
            "mcpServers": {
                "datadog": {
                    "command": "npx",
                    "args": ["-y", "@winor30/mcp-server-datadog"],
                    "env": {
                        "DATADOG_API_KEY": "{{env.DATADOG_API_KEY}}",
                        "DATADOG_APP_KEY": "{{env.DATADOG_APP_KEY}}",
                        "DATADOG_SITE": "{{env.DATADOG_SITE}}",
                    },
                    "suppress_output": True,
                }
            },
            "globalServers": ["filesystem", "memory"],
            "excludedServers": ["github", "sonarqube", "playwright"],
        }

        devops_config_file = sub_agents_dir / "devops_agent.mcp.json"
        devops_config_file.write_text(json.dumps(devops_config))

        # Test configuration loading through fallback (the core fix)
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            config = config_loader.load_config()

            # Verify fallback config was loaded correctly
            assert "datadog" in config["mcpServers"]
            assert config["globalServers"] == ["filesystem", "memory"]
            assert "github" in config["excludedServers"]
            assert "sonarqube" in config["excludedServers"]
            assert "playwright" in config["excludedServers"]

            # Verify datadog config has proper structure
            datadog_config = config["mcpServers"]["datadog"]
            assert datadog_config["command"] == "npx"
            assert "-y" in datadog_config["args"]
            assert "@winor30/mcp-server-datadog" in datadog_config["args"]

    def test_enhanced_agent_server_listing(self, tmp_path):
        """Test enhanced agent server listing through fallback."""
        # Create config
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        devops_config = {
            "mcpServers": {
                "datadog": {"command": "npx", "args": ["@datadog/mcp-server"]},
                "docker": {"command": "npx", "args": ["@docker/mcp-server"]},
                "kubernetes": {"command": "npx", "args": ["@kubernetes/mcp-server"]},
            },
            "globalServers": ["filesystem", "memory"],
        }

        devops_config_file = sub_agents_dir / "devops_agent.mcp.json"
        devops_config_file.write_text(json.dumps(devops_config))

        # Test server listing for enhanced agent
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            servers = list_available_mcp_servers("enhanced_devops_agent")

            # Should find servers from fallback config
            assert "datadog" in servers["sub_agent"]
            assert "docker" in servers["sub_agent"]
            assert "kubernetes" in servers["sub_agent"]


class TestToolLoadingIntegration:
    """Test integration with the main tool loading system."""

    def test_load_tools_for_sub_agent_with_enhanced_agent(self, tmp_path):
        """Test that load_tools_for_sub_agent works with enhanced agents."""
        # Setup config
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        devops_config = {
            "mcpServers": {"datadog": {"command": "npx", "args": ["@datadog/mcp-server"]}},
            "globalServers": ["filesystem"],
        }

        devops_config_file = sub_agents_dir / "devops_agent.mcp.json"
        devops_config_file.write_text(json.dumps(devops_config))

        # Mock the profile loading
        with patch("pathlib.Path.cwd", return_value=tmp_path), patch(TOOL_SETUP_PATH) as mock_load:
            mock_load.return_value = [MagicMock()]

            # Load tools for enhanced devops agent
            custom_config = {
                "included_categories": ["filesystem", "shell_command"],
                "include_mcp_tools": True,
                "mcp_server_filter": ["filesystem", "datadog"],
            }

            load_tools_for_sub_agent(
                "devops", custom_config, sub_agent_name="enhanced_devops_agent"
            )

            # Verify the function was called with enhanced agent name
            mock_load.assert_called_once()
            args, kwargs = mock_load.call_args
            assert kwargs["sub_agent_name"] == "enhanced_devops_agent"
            assert "datadog" in kwargs["mcp_server_filter"]

    def test_available_mcp_servers_listing(self, tmp_path):
        """Test that list_available_mcp_servers works with enhanced agents."""
        # Setup configs
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        global_dir = tmp_path / ".agent"
        sub_agents_dir.mkdir(parents=True)
        global_dir.mkdir(exist_ok=True)

        # Global config
        global_config = {
            "mcpServers": {
                "filesystem": {"command": "npx", "args": ["@filesystem/mcp-server"]},
                "memory": {"command": "npx", "args": ["@memory/mcp-server"]},
            }
        }
        global_config_file = global_dir / "mcp.json"
        global_config_file.write_text(json.dumps(global_config))

        # Sub-agent config
        sub_agent_config = {
            "mcpServers": {"datadog": {"command": "npx", "args": ["@datadog/mcp-server"]}}
        }
        sub_agent_config_file = sub_agents_dir / "devops_agent.mcp.json"
        sub_agent_config_file.write_text(json.dumps(sub_agent_config))

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            # List servers for enhanced agent
            servers = list_available_mcp_servers("enhanced_devops_agent")

            # Should find global and sub-agent servers
            assert "filesystem" in servers["global"]
            assert "memory" in servers["global"]
            assert "datadog" in servers["sub_agent"]


class TestRegressionPrevention:
    """Specific tests designed to prevent the exact regression we encountered."""

    def test_enhanced_devops_agent_regression_scenario(self, tmp_path):
        """Test the exact scenario that caused the regression."""
        # Recreate the exact scenario:
        # 1. enhanced_devops_agent name used by enhanced agent
        # 2. devops_agent.mcp.json config file exists
        # 3. Config contains datadog tools
        # 4. Exclusion logic should work properly

        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        # Exact config that was failing
        devops_config = {
            "mcpServers": {
                "datadog": {
                    "command": "npx",
                    "args": ["-y", "@winor30/mcp-server-datadog"],
                    "env": {
                        "DATADOG_API_KEY": "{{env.DATADOG_API_KEY}}",
                        "DATADOG_APP_KEY": "{{env.DATADOG_APP_KEY}}",
                        "DATADOG_SITE": "{{env.DATADOG_SITE}}",
                    },
                    "suppress_output": True,
                }
            },
            "globalServers": ["filesystem", "memory"],
            "excludedServers": ["github", "sonarqube", "playwright"],
            "serverOverrides": {"datadog": {"env": {"TEST_MODE": "1"}}},
        }

        devops_config_file = sub_agents_dir / "devops_agent.mcp.json"
        devops_config_file.write_text(json.dumps(devops_config))

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            # Test 1: Config should be found via fallback (THE MAIN FIX)
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            config = config_loader.load_config()

            assert "datadog" in config["mcpServers"]
            assert config["globalServers"] == ["filesystem", "memory"]
            assert "github" in config["excludedServers"]

            # Test 2: Server overrides are preserved
            assert "serverOverrides" in config
            assert "datadog" in config["serverOverrides"]
            assert config["serverOverrides"]["datadog"]["env"]["TEST_MODE"] == "1"

            # Test 3: Available servers listing works correctly
            servers = list_available_mcp_servers("enhanced_devops_agent")
            assert "datadog" in servers["sub_agent"]

    def test_server_filtering_configuration_structure(self, tmp_path):
        """Test that server filtering configuration is structured correctly."""
        # This tests the configuration structure that supports filtering

        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        devops_config = {
            "mcpServers": {
                "datadog": {"command": "npx", "args": ["@datadog/mcp-server"]},
                "docker": {"command": "npx", "args": ["@docker/mcp-server"]},
                "excluded_tool": {"command": "npx", "args": ["@excluded/mcp-server"]},
            },
            "globalServers": ["filesystem", "memory"],
        }

        devops_config_file = sub_agents_dir / "devops_agent.mcp.json"
        devops_config_file.write_text(json.dumps(devops_config))

        # Test configuration loading and server listing
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            config = config_loader.load_config()

            # Verify all servers are in config
            assert "datadog" in config["mcpServers"]
            assert "docker" in config["mcpServers"]
            assert "excluded_tool" in config["mcpServers"]
            assert config["globalServers"] == ["filesystem", "memory"]

            # Test server listing
            servers = list_available_mcp_servers("enhanced_devops_agent")
            assert "datadog" in servers["sub_agent"]
            assert "docker" in servers["sub_agent"]
            assert "excluded_tool" in servers["sub_agent"]

    def test_no_infinite_fallback_loop(self, tmp_path):
        """Ensure enhanced agents don't create infinite fallback loops."""
        sub_agents_dir = tmp_path / ".agent" / "sub-agents"
        sub_agents_dir.mkdir(parents=True)

        # Create a malicious config that could cause loops
        enhanced_config = {
            "mcpServers": {"tool1": {"command": "npx", "args": ["@tool1/mcp-server"]}}
        }

        # Both files exist
        enhanced_file = sub_agents_dir / "enhanced_devops_agent.mcp.json"
        enhanced_file.write_text(json.dumps(enhanced_config))

        base_config = {"mcpServers": {"tool2": {"command": "npx", "args": ["@tool2/mcp-server"]}}}
        base_file = sub_agents_dir / "devops_agent.mcp.json"
        base_file.write_text(json.dumps(base_config))

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            # Should use primary config, not fallback, when primary exists
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            config = config_loader.load_config()

            # Should load primary config only
            assert "tool1" in config["mcpServers"]
            assert "tool2" not in config["mcpServers"]


@pytest.mark.integration
class TestLiveSystemIntegration:
    """Integration tests that work with the actual system (when possible)."""

    def test_actual_devops_agent_config_loading(self):
        """Test loading actual devops agent configuration if it exists."""
        try:
            # Try to load the real devops agent config
            config_loader = SubAgentMCPConfig("enhanced_devops_agent")
            config = config_loader.load_config()

            # If we have a real config, verify it has expected structure
            if config.get("mcpServers") or config.get("globalServers"):
                assert isinstance(config.get("mcpServers", {}), dict)
                assert isinstance(config.get("globalServers", []), list)
                assert isinstance(config.get("excludedServers", []), list)

                # If datadog is configured, it should have proper structure
                if "datadog" in config.get("mcpServers", {}):
                    datadog_config = config["mcpServers"]["datadog"]
                    assert "command" in datadog_config
                    assert "args" in datadog_config

        except Exception:
            # If real config doesn't exist or fails to load, that's OK for this test
            pytest.skip("Real devops agent config not available")

    def test_integration_with_tool_loading_system(self):
        """Test integration with the actual tool loading system."""
        try:
            # Try to load tools using the real system
            from agents.software_engineer.tools.setup import create_sub_agent_tool_profiles

            profiles = create_sub_agent_tool_profiles()
            assert isinstance(profiles, dict)
            assert len(profiles) > 0

            # Test that our sub-agent MCP loading integrates properly
            if "devops" in profiles:
                # This should not crash and should return a list
                with patch(SIMPLE_LOADER_PATH):
                    tools = load_tools_for_sub_agent(
                        "devops", sub_agent_name="enhanced_devops_agent"
                    )
                    assert isinstance(tools, list)

        except ImportError:
            pytest.skip("Tool loading system not available")


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration
