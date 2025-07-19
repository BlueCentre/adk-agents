import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the classes and functions we're testing
from src.wrapper.adk.cli.utils.agent_loader import AgentLoader, load_agent_from_module


class MockBaseAgent:
    """Mock BaseAgent for testing."""

    def __init__(self, name="TestAgent"):
        self.name = name


class TestAgentLoaderInit:
    """Test AgentLoader initialization."""

    def test_init_with_agents_dir(self):
        """Test initialization with agents_dir provided."""
        agents_dir = "/path/to/agents/"
        loader = AgentLoader(agents_dir)

        # Should strip trailing slash
        assert loader.agents_dir == "/path/to/agents"
        assert loader._original_sys_path is None
        assert loader._agent_cache == {}

    def test_init_with_agents_dir_no_trailing_slash(self):
        """Test initialization with agents_dir without trailing slash."""
        agents_dir = "/path/to/agents"
        loader = AgentLoader(agents_dir)

        assert loader.agents_dir == "/path/to/agents"
        assert loader._original_sys_path is None
        assert loader._agent_cache == {}

    def test_init_with_none_agents_dir(self):
        """Test initialization with None agents_dir."""
        loader = AgentLoader(None)

        assert loader.agents_dir is None
        assert loader._original_sys_path is None
        assert loader._agent_cache == {}

    def test_init_with_empty_agents_dir(self):
        """Test initialization with empty string agents_dir."""
        loader = AgentLoader("")

        # Empty string is falsy, so it becomes None
        assert loader.agents_dir is None
        assert loader._original_sys_path is None
        assert loader._agent_cache == {}


class TestGetAvailableAgentModules:
    """Test the get_available_agent_modules static method."""

    def test_get_available_modules_with_valid_directory(self):
        """Test getting available modules from a directory with agents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create various agent structures
            # 1. Package-style agent (directory with __init__.py)
            agent_pkg_dir = os.path.join(temp_dir, "package_agent")
            os.makedirs(agent_pkg_dir)
            with open(os.path.join(agent_pkg_dir, "__init__.py"), "w") as f:
                f.write("# Package agent\n")

            # 2. Module-style agent (.py file)
            with open(os.path.join(temp_dir, "module_agent.py"), "w") as f:
                f.write("# Module agent\n")

            # 3. Directory without __init__.py (should still be included)
            simple_dir = os.path.join(temp_dir, "simple_agent")
            os.makedirs(simple_dir)

            # 4. Hidden directory (should be excluded)
            hidden_dir = os.path.join(temp_dir, ".hidden_agent")
            os.makedirs(hidden_dir)

            # 5. __pycache__ directory (should be excluded)
            pycache_dir = os.path.join(temp_dir, "__pycache__")
            os.makedirs(pycache_dir)

            # 6. Hidden .py file (should be excluded)
            with open(os.path.join(temp_dir, ".hidden.py"), "w") as f:
                f.write("# Hidden file\n")

            # 7. __init__.py file (should be excluded as separate agent)
            with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
                f.write("# Init file\n")

            # Get available modules
            modules = AgentLoader.get_available_agent_modules(temp_dir)

            # Should return sorted list of valid agents
            expected = ["module_agent", "package_agent", "simple_agent"]
            assert modules == expected

    def test_get_available_modules_empty_directory(self):
        """Test getting modules from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            modules = AgentLoader.get_available_agent_modules(temp_dir)
            assert modules == []

    def test_get_available_modules_nonexistent_directory(self):
        """Test getting modules from non-existent directory."""
        nonexistent_path = "/path/that/does/not/exist"
        modules = AgentLoader.get_available_agent_modules(nonexistent_path)
        assert modules == []

    def test_get_available_modules_file_instead_of_directory(self):
        """Test getting modules when path is a file, not directory."""
        with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
            modules = AgentLoader.get_available_agent_modules(temp_file.name)
            assert modules == []

    def test_get_available_modules_sorting(self):
        """Test that modules are returned sorted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agents in non-alphabetical order
            for name in ["zebra_agent", "alpha_agent", "beta_agent"]:
                agent_dir = os.path.join(temp_dir, name)
                os.makedirs(agent_dir)

            modules = AgentLoader.get_available_agent_modules(temp_dir)

            # Should be sorted alphabetically
            assert modules == ["alpha_agent", "beta_agent", "zebra_agent"]


class TestLoadFromModuleOrPackage:
    """Test the _load_from_module_or_package method."""

    def test_load_from_module_success_with_base_agent(self):
        """Test successful loading when module has valid root_agent."""
        loader = AgentLoader("/test/agents")

        # Create a mock that will pass isinstance check
        from google.adk.agents.base_agent import BaseAgent

        mock_agent = Mock(spec=BaseAgent)

        mock_module = Mock()
        mock_module.root_agent = mock_agent

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            result = loader._load_from_module_or_package("test_agent")

            assert result == mock_agent
            mock_importlib.import_module.assert_called_with("test_agent")

    def test_load_from_module_root_agent_wrong_type(self):
        """Test loading when root_agent exists but is not BaseAgent instance."""
        loader = AgentLoader("/test/agents")

        mock_module = Mock()
        mock_module.root_agent = (  # Wrong type (string, not BaseAgent)
            "not_an_agent"
        )

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            result = loader._load_from_module_or_package("test_agent")

            assert result is None  # Should return None since string is not BaseAgent
            mock_importlib.import_module.assert_called_with("test_agent")

    def test_load_from_module_no_root_agent(self):
        """Test loading when module has no root_agent attribute."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_module = Mock()
            # Remove root_agent attribute
            del mock_module.root_agent
            mock_import.return_value = mock_module

            result = loader._load_from_module_or_package("test_agent")

            assert result is None
            mock_import.assert_called_once_with("test_agent")

    def test_load_from_module_module_not_found(self):
        """Test loading when main module is not found."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            # Module itself not found
            mock_import.side_effect = ModuleNotFoundError("No module named 'test_agent'")
            mock_import.side_effect.name = "test_agent"

            result = loader._load_from_module_or_package("test_agent")

            assert result is None
            mock_import.assert_called_once_with("test_agent")

    def test_load_from_module_dependency_not_found(self):
        """Test loading when module's dependency is not found."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            # Dependency not found
            error = ModuleNotFoundError("No module named 'some_dependency'")
            error.name = "some_dependency"
            mock_import.side_effect = error

            with pytest.raises(ValueError, match="Fail to load 'test_agent' module"):
                loader._load_from_module_or_package("test_agent")

    def test_load_from_module_general_exception(self):
        """Test loading when general exception occurs."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("General import error")

            with pytest.raises(ValueError, match="Fail to load 'test_agent' module"):
                loader._load_from_module_or_package("test_agent")


class TestLoadFromSubmodule:
    """Test the _load_from_submodule method."""

    def test_load_from_submodule_success(self):
        """Test successful loading from {agent_name}.agent submodule."""
        loader = AgentLoader("/test/agents")

        # Create a mock that will pass isinstance check
        from google.adk.agents.base_agent import BaseAgent

        mock_agent = Mock(spec=BaseAgent)

        mock_module = Mock()
        mock_module.root_agent = mock_agent

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            result = loader._load_from_submodule("test_agent")

            assert result == mock_agent
            mock_importlib.import_module.assert_called_with("test_agent.agent")

    def test_load_from_submodule_wrong_type(self):
        """Test loading from submodule when root_agent is wrong type."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.root_agent = "not_an_agent"
            mock_import.return_value = mock_module

            with patch(
                "src.wrapper.adk.cli.utils.agent_loader.isinstance",
                return_value=False,
            ):
                result = loader._load_from_submodule("test_agent")

                assert result is None

    def test_load_from_submodule_no_root_agent(self):
        """Test loading from submodule when no root_agent attribute."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_module = Mock()
            del mock_module.root_agent
            mock_import.return_value = mock_module

            result = loader._load_from_submodule("test_agent")

            assert result is None

    def test_load_from_submodule_module_not_found(self):
        """Test loading when submodule is not found."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            error = ModuleNotFoundError("No module named 'test_agent.agent'")
            error.name = "test_agent.agent"
            mock_import.side_effect = error

            result = loader._load_from_submodule("test_agent")

            assert result is None

    def test_load_from_submodule_dependency_error(self):
        """Test loading when submodule dependency fails."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            error = ModuleNotFoundError("No module named 'dependency'")
            error.name = "dependency"
            mock_import.side_effect = error

            with pytest.raises(ValueError, match="Fail to load 'test_agent.agent' module"):
                loader._load_from_submodule("test_agent")


class TestPerformLoad:
    """Test the _perform_load method."""

    def test_perform_load_with_agents_dir_success_from_module(self):
        """Test successful agent loading with agents_dir set."""
        agents_dir = "/test/agents"
        loader = AgentLoader(agents_dir)
        mock_agent = MockBaseAgent("TestAgent")

        with patch("src.wrapper.adk.cli.utils.agent_loader.sys.path") as mock_path:
            mock_path.__contains__ = Mock(return_value=False)
            mock_path.insert = Mock()

            with patch(
                "src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"
            ) as mock_load_env:
                with patch.object(loader, "_load_from_module_or_package", return_value=mock_agent):
                    result = loader._perform_load("test_agent")

                    assert result == mock_agent
                    mock_path.insert.assert_called_once_with(0, agents_dir)
                    mock_load_env.assert_called_once_with("test_agent", agents_dir)

    def test_perform_load_with_agents_dir_success_from_submodule(self):
        """Test successful agent loading from submodule when module pattern fails."""
        agents_dir = "/test/agents"
        loader = AgentLoader(agents_dir)
        mock_agent = MockBaseAgent("TestAgent")

        with patch("src.wrapper.adk.cli.utils.agent_loader.sys.path") as mock_path:
            mock_path.__contains__ = Mock(return_value=False)
            mock_path.insert = Mock()

            with patch(
                "src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"
            ) as mock_load_env:
                with patch.object(loader, "_load_from_module_or_package", return_value=None):
                    with patch.object(loader, "_load_from_submodule", return_value=mock_agent):
                        result = loader._perform_load("test_agent")

                        assert result == mock_agent
                        mock_load_env.assert_called_once_with("test_agent", agents_dir)

    def test_perform_load_without_agents_dir(self):
        """Test agent loading when agents_dir is None."""
        loader = AgentLoader(None)
        mock_agent = MockBaseAgent("TestAgent")

        with patch(
            "src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"
        ) as mock_load_env:
            with patch.object(loader, "_load_from_module_or_package", return_value=mock_agent):
                result = loader._perform_load("test_agent")

                assert result == mock_agent
                mock_load_env.assert_called_once_with("test_agent")

    def test_perform_load_agents_dir_already_in_path(self):
        """Test loading when agents_dir is already in sys.path."""
        agents_dir = "/test/agents"
        loader = AgentLoader(agents_dir)
        mock_agent = MockBaseAgent("TestAgent")

        with patch("src.wrapper.adk.cli.utils.agent_loader.sys.path") as mock_path:
            mock_path.__contains__ = Mock(return_value=True)  # Already in path
            mock_path.insert = Mock()

            with patch(
                "src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"
            ) as mock_load_env:
                with patch.object(loader, "_load_from_module_or_package", return_value=mock_agent):
                    result = loader._perform_load("test_agent")

                    assert result == mock_agent
                    mock_path.insert.assert_not_called()  # Should not add to path
                    mock_load_env.assert_called_once_with("test_agent", agents_dir)

    def test_perform_load_no_agent_found(self):
        """Test loading when no agent is found by any pattern."""
        loader = AgentLoader("/test/agents")

        with patch("src.wrapper.adk.cli.utils.agent_loader.sys.path"):
            with patch("src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"):
                with patch.object(loader, "_load_from_module_or_package", return_value=None):
                    with patch.object(loader, "_load_from_submodule", return_value=None):
                        with pytest.raises(
                            ValueError, match="No root_agent found for 'test_agent'"
                        ):
                            loader._perform_load("test_agent")


class TestLoadAgent:
    """Test the load_agent method (with caching)."""

    def test_load_agent_from_cache(self):
        """Test loading agent from cache."""
        loader = AgentLoader("/test/agents")
        mock_agent = MockBaseAgent("CachedAgent")

        # Pre-populate cache
        loader._agent_cache["test_agent"] = mock_agent

        result = loader.load_agent("test_agent")

        assert result == mock_agent
        # Should not call _perform_load

    def test_load_agent_not_in_cache(self):
        """Test loading agent when not in cache."""
        loader = AgentLoader("/test/agents")
        mock_agent = MockBaseAgent("NewAgent")

        with patch.object(loader, "_perform_load", return_value=mock_agent) as mock_perform:
            result = loader.load_agent("test_agent")

            assert result == mock_agent
            assert loader._agent_cache["test_agent"] == mock_agent
            mock_perform.assert_called_once_with("test_agent")

    def test_load_agent_caching_behavior(self):
        """Test that subsequent calls use cache."""
        loader = AgentLoader("/test/agents")
        mock_agent = MockBaseAgent("CachedAgent")

        with patch.object(loader, "_perform_load", return_value=mock_agent) as mock_perform:
            # First call
            result1 = loader.load_agent("test_agent")
            # Second call
            result2 = loader.load_agent("test_agent")

            assert result1 == mock_agent
            assert result2 == mock_agent
            assert result1 is result2  # Same object
            mock_perform.assert_called_once()  # Only called once


class TestLoadAgentFromModule:
    """Test the standalone load_agent_from_module function."""

    def test_load_agent_from_module_success(self):
        """Test successful loading from module."""
        # Create a mock that will pass isinstance check
        from google.adk.agents.base_agent import BaseAgent

        mock_agent = Mock(spec=BaseAgent)

        mock_module = Mock()
        mock_module.root_agent = mock_agent

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            result = load_agent_from_module("my.agent.module")

            assert result == mock_agent
            mock_importlib.import_module.assert_called_with("my.agent.module")

    def test_load_agent_from_module_no_root_agent(self):
        """Test loading when module has no root_agent."""
        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_module = Mock()
            del mock_module.root_agent
            mock_import.return_value = mock_module

            with pytest.raises(ValueError, match="No 'root_agent' found in module"):
                load_agent_from_module("my.agent.module")

    def test_load_agent_from_module_wrong_type(self):
        """Test loading when root_agent is wrong type."""
        mock_module = Mock()
        mock_module.root_agent = (  # Wrong type (string, not BaseAgent)
            "not_an_agent"
        )

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            # TypeError gets wrapped in ValueError by the exception handler
            with pytest.raises(
                ValueError,
                match=("Failed to load agent from module.*Error:.*is not an instance of BaseAgent"),
            ):
                load_agent_from_module("my.agent.module")

    def test_load_agent_from_module_not_found(self):
        """Test loading when module is not found."""
        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = ModuleNotFoundError("No module named 'my.agent.module'")

            with pytest.raises(ValueError, match="Agent module.*not found"):
                load_agent_from_module("my.agent.module")

    def test_load_agent_from_module_general_exception(self):
        """Test loading when general exception occurs."""
        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("General import error")

            with pytest.raises(ValueError, match="Failed to load agent from module"):
                load_agent_from_module("my.agent.module")

    def test_load_agent_from_module_empty_string(self):
        """Test loading with empty string as module name."""
        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = ModuleNotFoundError("No module named ''")

            with pytest.raises(ValueError, match="Agent module.*not found"):
                load_agent_from_module("")

    def test_load_agent_from_module_root_agent_is_none(self):
        """Test loading when root_agent exists but is None."""
        mock_module = Mock()
        mock_module.root_agent = None

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            with pytest.raises(
                ValueError,
                match="Failed to load agent from module.*Error:.*is not an instance of BaseAgent",
            ):
                load_agent_from_module("my.agent.module")

    def test_load_agent_from_module_complex_object_type(self):
        """Test loading when root_agent is a complex object but not BaseAgent."""

        class FakeAgent:
            def __init__(self):
                self.name = "fake"

        mock_module = Mock()
        mock_module.root_agent = FakeAgent()

        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_module

            with pytest.raises(
                ValueError,
                match="Failed to load agent from module.*Error:.*is not an instance of BaseAgent",
            ):
                load_agent_from_module("my.agent.module")

    def test_load_agent_from_module_import_error_with_cause(self):
        """Test loading when import fails with specific cause."""
        with patch("src.wrapper.adk.cli.utils.agent_loader.importlib.import_module") as mock_import:
            original_error = ImportError("Circular import detected")
            mock_import.side_effect = original_error

            with pytest.raises(ValueError, match="Failed to load agent from module") as exc_info:
                load_agent_from_module("my.agent.module")

            # Check that the original exception is preserved as the cause
            assert exc_info.value.__cause__ is original_error


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_real_filesystem_agent_discovery(self):
        """Test agent discovery with real filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a realistic agent structure
            agent_dir = os.path.join(temp_dir, "test_agent")
            os.makedirs(agent_dir)

            # Create agent.py with mock content
            agent_file = os.path.join(agent_dir, "agent.py")
            with open(agent_file, "w") as f:
                f.write("# Mock agent file\n")

            # Create another agent as .py file
            with open(os.path.join(temp_dir, "simple_agent.py"), "w") as f:
                f.write("# Simple agent\n")

            # Test discovery
            modules = AgentLoader.get_available_agent_modules(temp_dir)

            assert "test_agent" in modules
            assert "simple_agent" in modules

    def test_agent_loader_with_complex_scenarios(self):
        """Test AgentLoader with various edge cases."""
        loader = AgentLoader("/test/agents")

        # Test multiple agents in cache
        agent1 = MockBaseAgent("Agent1")
        agent2 = MockBaseAgent("Agent2")

        loader._agent_cache["agent1"] = agent1
        loader._agent_cache["agent2"] = agent2

        assert loader.load_agent("agent1") == agent1
        assert loader.load_agent("agent2") == agent2
        assert len(loader._agent_cache) == 2

    def test_agents_dir_path_handling(self):
        """Test various agents_dir path formats."""
        # Test with different path formats
        test_cases = [
            ("/path/to/agents/", "/path/to/agents"),
            ("/path/to/agents", "/path/to/agents"),
            ("relative/path/", "relative/path"),
            ("relative/path", "relative/path"),
            ("", None),  # Empty string becomes None
            (None, None),
        ]

        for input_path, expected in test_cases:
            loader = AgentLoader(input_path)
            assert loader.agents_dir == expected

    def test_error_propagation(self):
        """Test that errors are properly propagated with context."""
        loader = AgentLoader("/test/agents")

        with (
            patch.object(
                loader,
                "_load_from_module_or_package",
                side_effect=ValueError("Test error"),
            ),
            pytest.raises(ValueError, match="Test error"),
        ):
            loader._perform_load("test_agent")

    def test_logger_usage(self):
        """Test that logger is called appropriately."""
        loader = AgentLoader("/test/agents")
        mock_agent = MockBaseAgent("LoggedAgent")

        with patch("src.wrapper.adk.cli.utils.agent_loader.logger") as mock_logger:
            with patch.object(loader, "_perform_load", return_value=mock_agent):
                # First load (not in cache)
                loader.load_agent("test_agent")
                mock_logger.debug.assert_called()

                # Second load (from cache)
                loader.load_agent("test_agent")
                # Should log cache hit
                debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
                assert any("cached" in call.lower() for call in debug_calls)

    def test_sys_path_manipulation_edge_cases(self):
        """Test sys.path manipulation in various scenarios."""
        # Test when sys.path is modified during loading
        loader = AgentLoader("/test/agents")
        mock_agent = MockBaseAgent("PathAgent")

        sys.path.copy()

        with patch("src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"):
            with patch.object(loader, "_load_from_module_or_package", return_value=mock_agent):
                loader._perform_load("test_agent")

        # sys.path should be restored to original state
        # (In this test we're just ensuring no exceptions occur)
        assert True  # If we get here, the test passed

    def test_empty_and_none_agent_names(self):
        """Test handling of empty or None agent names."""
        loader = AgentLoader("/test/agents")

        # These should trigger module loading attempts and fail appropriately
        with patch("src.wrapper.adk.cli.utils.agent_loader.envs.load_dotenv_for_agent"):
            with patch.object(loader, "_load_from_module_or_package", return_value=None):
                with patch.object(loader, "_load_from_submodule", return_value=None):
                    with pytest.raises(ValueError):
                        loader._perform_load("")
