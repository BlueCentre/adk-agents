import os
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

# Import the functions we're testing
from src.wrapper.adk.cli.utils.envs import _walk_to_root_until_found, load_dotenv_for_agent


class TestWalkToRootUntilFound:
    """Test the _walk_to_root_until_found helper function."""

    def test_file_found_in_current_directory(self):
        """Test finding a file in the current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / ".env"
            with Path.open(test_file, "w") as f:
                f.write("TEST=value")

            # Should find the file in the current directory
            result = _walk_to_root_until_found(Path(temp_dir), ".env")
            assert result == str(test_file)
            assert Path(result).exists()

    def test_file_found_in_parent_directory(self):
        """Test finding a file in a parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested directory structure
            child_dir = Path(temp_dir) / "child"
            grandchild_dir = child_dir / "grandchild"
            grandchild_dir.mkdir(parents=True)

            # Create test file in parent directory
            test_file = Path(temp_dir) / ".env"
            with Path.open(test_file, "w") as f:
                f.write("TEST=value")

            # Should find the file by walking up to parent
            result = _walk_to_root_until_found(Path(grandchild_dir), ".env")
            assert result == str(test_file)
            assert Path(result).exists()

    def test_file_not_found_returns_empty_string(self):
        """Test that missing file returns empty string when reaching root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a deep nested structure without the target file
            deep_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            deep_dir.mkdir(parents=True)

            # Should return empty string when file not found
            result = _walk_to_root_until_found(Path(deep_dir), "nonexistent.env")
            assert result == ""

    def test_file_is_directory_not_file(self):
        """Test behavior when target exists but is a directory, not a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory with the same name as what we're looking for
            dir_path = Path(temp_dir) / ".env"
            dir_path.mkdir(parents=True)

            # Should not find it because it's a directory, not a file
            result = _walk_to_root_until_found(Path(temp_dir), ".env")
            assert result == ""

    def test_reaches_root_directory(self):
        """Test that function stops when reaching filesystem root."""
        # Start from a real but non-existent nested path
        # This tests the condition where parent_folder == folder (reached root)
        nonexistent_path = "/nonexistent/deep/nested/path"

        # Should return empty string when reaching root without finding file
        result = _walk_to_root_until_found(Path(nonexistent_path), "test.env")
        assert result == ""

    def test_multiple_levels_with_file_in_middle(self):
        """Test finding file when it exists several levels up."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure: temp/level1/level2/level3/level4
            levels = ["level1", "level2", "level3", "level4"]
            current_path = Path(temp_dir)
            for level in levels:
                current_path = current_path / level
                current_path.mkdir(parents=True)

            # Place .env file at level2
            env_file = Path(temp_dir) / "level1" / "level2" / ".env"
            with Path.open(env_file, "w") as f:
                f.write("TEST=level2")

            # Search starting from level4 - should find file at level2
            search_start = Path(temp_dir) / "level1" / "level2" / "level3" / "level4"
            result = _walk_to_root_until_found(Path(search_start), ".env")
            assert result == str(env_file)
            assert Path(result).exists()

    def test_different_filename(self):
        """Test searching for different filename than .env."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a custom config file
            config_file = Path(temp_dir) / "app.config"
            with Path.open(config_file, "w") as f:
                f.write("config=value")

            child_dir = Path(temp_dir) / "subdir"
            child_dir.mkdir(parents=True)

            # Should find the custom filename
            result = _walk_to_root_until_found(Path(child_dir), "app.config")
            assert result == str(config_file)
            assert Path(result).exists()


class TestLoadDotenvForAgent:
    """Test the load_dotenv_for_agent main function."""

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_with_agent_parent_folder_success(self, mock_walk, mock_load_dotenv):
        """Test successful dotenv loading with agent_parent_folder provided."""
        # Setup mocks
        mock_env_path = "/path/to/.env"
        mock_walk.return_value = mock_env_path

        # Call function with agent_parent_folder
        load_dotenv_for_agent("test_agent", "/path/to/agents", ".env")

        # Verify calls
        expected_start_folder = Path("/path/to/agents") / "test_agent"
        mock_walk.assert_called_once_with(expected_start_folder.resolve(), ".env")
        mock_load_dotenv.assert_called_once_with(mock_env_path, override=True, verbose=True)

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_with_agent_parent_folder_file_not_found(self, mock_walk, mock_load_dotenv):
        """Test dotenv loading when file is not found."""
        # Setup mocks - file not found
        mock_walk.return_value = ""

        # Call function
        load_dotenv_for_agent("test_agent", "/path/to/agents", ".env")

        # Verify calls
        expected_start_folder = Path("/path/to/agents") / "test_agent"
        mock_walk.assert_called_once_with(expected_start_folder.resolve(), ".env")
        mock_load_dotenv.assert_not_called()  # Should not call load_dotenv if file not found

    @patch("src.wrapper.adk.cli.utils.envs.importlib.resources.files")
    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_with_installed_package_success(
        self, mock_walk, mock_load_dotenv, mock_files
    ):
        """Test dotenv loading for installed package (no agent_parent_folder)."""
        # Setup mocks
        mock_path = Mock()
        mock_path.__str__ = Mock(return_value="/installed/package/path")
        mock_files.return_value = mock_path

        mock_env_path = "/installed/package/.env"
        mock_walk.return_value = mock_env_path

        # Call function without agent_parent_folder
        load_dotenv_for_agent("my.agent.module")

        # Verify calls
        mock_files.assert_called_once_with("my.agent.module")
        mock_walk.assert_called_once_with(mock_path.resolve(), ".env")
        mock_load_dotenv.assert_called_once_with(mock_env_path, override=True, verbose=True)

    @patch("src.wrapper.adk.cli.utils.envs.importlib.resources.files")
    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_with_installed_package_exception(
        self, mock_walk, mock_load_dotenv, mock_files
    ):
        """Test dotenv loading when importlib.resources.files raises exception."""
        # Setup mocks - importlib raises exception
        mock_files.side_effect = ImportError("Module not found")

        # Call function without agent_parent_folder - should handle exception gracefully
        load_dotenv_for_agent("nonexistent.module")

        # Verify calls
        mock_files.assert_called_once_with("nonexistent.module")
        mock_walk.assert_not_called()  # Should not call walk due to exception
        mock_load_dotenv.assert_not_called()  # Should not call load_dotenv due to exception

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_with_custom_filename(self, mock_walk, mock_load_dotenv):
        """Test loading dotenv with custom filename."""
        # Setup mocks
        mock_env_path = "/path/to/.production.env"
        mock_walk.return_value = mock_env_path

        # Call function with custom filename
        load_dotenv_for_agent("test_agent", "/path/to/agents", ".production.env")

        # Verify calls
        expected_start_folder = Path("/path/to/agents") / "test_agent"
        mock_walk.assert_called_once_with(expected_start_folder.resolve(), ".production.env")
        mock_load_dotenv.assert_called_once_with(mock_env_path, override=True, verbose=True)

    @patch("src.wrapper.adk.cli.utils.envs.importlib.resources.files")
    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_package_with_slashes_in_name(
        self, mock_walk, mock_load_dotenv, mock_files
    ):
        """Test dotenv loading with agent name containing slashes."""
        # Setup mocks
        mock_path = Mock()
        mock_path.__str__ = Mock(return_value="/package/nested/path")
        mock_files.return_value = mock_path

        mock_env_path = "/package/.env"
        mock_walk.return_value = mock_env_path

        # Call function with agent name containing slashes
        load_dotenv_for_agent("agents/my_agent")

        # Verify calls - slashes should be converted to dots
        mock_files.assert_called_once_with("agents.my_agent")
        mock_walk.assert_called_once_with(mock_path.resolve(), ".env")
        mock_load_dotenv.assert_called_once_with(mock_env_path, override=True, verbose=True)

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    @patch("src.wrapper.adk.cli.utils.envs._walk_to_root_until_found")
    def test_load_dotenv_default_filename(self, mock_walk, mock_load_dotenv):
        """Test loading dotenv with default filename (.env)."""
        # Setup mocks
        mock_env_path = "/path/to/.env"
        mock_walk.return_value = mock_env_path

        # Call function without specifying filename (should default to '.env')
        load_dotenv_for_agent("test_agent", "/path/to/agents")

        # Verify calls
        expected_start_folder = Path("/path/to/agents") / "test_agent"
        mock_walk.assert_called_once_with(expected_start_folder.resolve(), ".env")
        mock_load_dotenv.assert_called_once_with(mock_env_path, override=True, verbose=True)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    def test_real_filesystem_integration(self, mock_load_dotenv):
        """Test with real filesystem operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent directory structure
            agent_dir = Path(temp_dir) / "my_agent"
            agent_dir.mkdir(parents=True)

            # Create .env file in parent directory
            env_file = Path(temp_dir) / ".env"
            with Path.open(env_file, "w") as f:
                f.write("API_KEY=test123\nDEBUG=true\n")

            # Call the function - should find the .env file
            load_dotenv_for_agent("my_agent", temp_dir)

            # Verify load_dotenv was called with correct path
            mock_load_dotenv.assert_called_once_with(
                str(Path(str(env_file)).resolve()), override=True, verbose=True
            )

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    def test_nested_agent_structure(self, mock_load_dotenv):
        """Test with deeply nested agent directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure: temp/agents/category/my_agent/src
            nested_path = Path(temp_dir) / "agents" / "category" / "my_agent" / "src"
            nested_path.mkdir(parents=True)

            # Create .env file at agents level
            env_file = Path(temp_dir) / "agents" / ".env"
            with Path.open(env_file, "w") as f:
                f.write("NESTED_CONFIG=true\n")

            # Call function from deeply nested path
            load_dotenv_for_agent("my_agent", Path(temp_dir) / "agents" / "category")

            # Should find the .env file by walking up
            mock_load_dotenv.assert_called_once_with(
                str(Path(str(env_file)).resolve()), override=True, verbose=True
            )

    def test_edge_case_empty_agent_name(self):
        """Test edge case with empty agent name."""
        # Should handle gracefully without crashing
        load_dotenv_for_agent("", "/some/path")
        # Function should complete without error

    def test_edge_case_none_agent_parent_folder(self):
        """Test edge case with None agent_parent_folder."""
        with patch("src.wrapper.adk.cli.utils.envs.importlib.resources.files") as mock_files:
            mock_files.side_effect = Exception("Module not found")

            # Should handle gracefully without crashing
            load_dotenv_for_agent("test_agent", None)
            # Function should complete without error

    @patch("src.wrapper.adk.cli.utils.envs.load_dotenv")
    def test_complex_agent_name_with_special_characters(self, mock_load_dotenv):
        """Test agent name with special characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent directory with special characters in path
            agent_name = "my-agent_v2"
            agent_dir = Path(temp_dir) / agent_name
            agent_dir.mkdir(parents=True)

            # Create .env file
            env_file = agent_dir / ".env"
            with Path.open(env_file, "w") as f:
                f.write("SPECIAL_AGENT=true\n")

            # Call function
            load_dotenv_for_agent(agent_name, temp_dir)

            # Should find and load the .env file
            mock_load_dotenv.assert_called_once_with(
                str(Path(str(env_file)).resolve()), override=True, verbose=True
            )

    def test_relative_vs_absolute_paths(self):
        """Test that function handles both relative and absolute paths correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with relative path
            relative_path = Path(os.path.relpath(temp_dir))

            # Should convert to absolute path internally
            load_dotenv_for_agent("test_agent", relative_path)
            # Function should complete without error

    @patch("src.wrapper.adk.cli.utils.envs.logger")
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate log messages are generated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent directory and .env file
            agent_dir = Path(temp_dir) / "logged_agent"
            agent_dir.mkdir(parents=True)
            env_file = agent_dir / ".env"
            with Path.open(env_file, "w") as f:
                f.write("LOG_TEST=true\n")

            # Call function
            load_dotenv_for_agent("logged_agent", temp_dir)

            # Should log success message - just verify that info was called
            mock_logger.info.assert_called()
            # Verify at least one call was made (don't check specific message content)
            assert mock_logger.info.call_count > 0

    @patch("src.wrapper.adk.cli.utils.envs.logger")
    def test_logging_when_file_not_found(self, mock_logger):
        """Test logging when .env file is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent directory without .env file
            agent_dir = Path(temp_dir) / "no_env_agent"
            agent_dir.mkdir(exist_ok=True)

            # Call function
            load_dotenv_for_agent("no_env_agent", temp_dir)

            # Should log "not found" message - just verify that info was called
            mock_logger.info.assert_called()
            # Verify at least one call was made (don't check specific message content)
            assert mock_logger.info.call_count > 0
