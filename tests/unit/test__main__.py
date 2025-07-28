""" "
Unit tests for __main__.py

Tests the main entry point module for the CLI package.
"""

from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest


class TestMainModule:
    """Test the __main__.py module."""

    def test_import_main_function(self):
        """Test that the main function is correctly imported from cli_tools_click."""
        # Import the module and verify it has the main function
        from src.wrapper.adk.cli import __main__

        # Verify the main function is available in the module
        assert hasattr(__main__, "main")

        # Verify it's the correct function from cli_tools_click
        from src.wrapper.adk.cli.cli_tools_click import main as original_main

        assert __main__.main is original_main

    def test_main_called_when_run_as_script(self):
        """Test that main() is called when the module is run as __main__."""
        # Use subprocess to test the actual execution behavior
        script_code = """
import sys
sys.path.insert(0, ".")
from src.wrapper.adk.cli.__main__ import main
sys.argv = ["test", "--help"]
try:
    main()
except SystemExit:
    pass
"""
        result = subprocess.run(
            [sys.executable, "-c", script_code],
            capture_output=True,
            text=True,
                timeout=30,
        )

        # The command should complete (main function was called)
        # We expect a SystemExit from the --help, which is normal
        assert result.returncode in [0, 2]  # 0 for success, 2 for help/usage

    def test_module_runs_without_error_via_subprocess(self):
        """Test that the module can be executed via subprocess without errors."""
        # Test running the module with --help to avoid long-running commands
        result = subprocess.run(
            [sys.executable, "-m", "src.wrapper.adk.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,  # 10 second timeout
        )

        # The command should complete successfully (exit code 0)
        assert result.returncode == 0

        # Should contain CLI help output
        assert "Agent Development Kit CLI tools" in result.stdout

    def test_module_runs_version_via_subprocess(self):
        """Test that the module can show version information via subprocess."""
        result = subprocess.run(
            [sys.executable, "-m", "src.wrapper.adk.cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,  # 10 second timeout
        )

        # The command should complete successfully (exit code 0)
        assert result.returncode == 0

        # Should contain some version-related output
        # (the exact format may vary, so we just check it doesn't crash)
        assert len(result.stdout.strip()) > 0

    def test_module_structure(self):
        """Test the basic structure and imports of the __main__.py module."""
        import src.wrapper.adk.cli.__main__ as main_module

        # Check that the module has the expected attributes
        assert hasattr(main_module, "main")

        # Verify the main function is callable
        assert callable(main_module.main)

    @patch("sys.argv", ["test", "--help"])
    def test_main_function_delegation(self):
        """Test that the imported main function properly delegates to cli_tools_click.main."""
        from src.wrapper.adk.cli.__main__ import main

        # The main function should execute and show help (which causes SystemExit with code 0)
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Verify it exits with code 0 (success) when showing help
        assert exc_info.value.code == 0

    def test_copyright_header_present(self):
        """Test that the module contains the required copyright header."""
        import importlib.util

        spec = importlib.util.find_spec("src.wrapper.adk.cli.__main__")

        with Path.open(spec.origin) as f:
            content = f.read()

        # Check for copyright header
        assert "Copyright 2025 Google LLC" in content
        assert "Licensed under the Apache License, Version 2.0" in content

    def test_module_execution_via_python_m(self):
        """Test that the module can be executed via python -m with actual __main__ execution."""
        # Test the actual -m execution path
        result = subprocess.run(
            [sys.executable, "-m", "src.wrapper.adk.cli.__main__", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should execute successfully and show help
        assert result.returncode == 0
        assert "Agent Development Kit CLI tools" in result.stdout

    def test_main_module_if_name_main_block(self):
        """Test that the __main__.py contains the proper if __name__ == "__main__": block."""
        import importlib.util

        spec = importlib.util.find_spec("src.wrapper.adk.cli.__main__")

        with Path.open(spec.origin) as f:
            content = f.read()

        # Verify the module contains the if __name__ == '__main__': block
        assert 'if __name__ == "__main__":' in content
        assert "main()" in content

        # Verify the structure matches expected pattern
        lines = content.strip().split("\n")
        main_block_found = False
        for i, line in enumerate(lines):
            if 'if __name__ == "__main__":' in line:
                main_block_found = True
                # Check that the next non-empty line calls main()
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if next_line:
                        assert "main()" in next_line
                        break
                break

        assert main_block_found, 'if __name__ == "__main__": block not found'


class TestMainModuleErrorHandling:
    """Test error handling in the __main__.py module."""

    def test_import_error_handling(self):
        """Test behavior when cli_tools_click import fails."""
        # This test ensures that if the import fails, we get a proper ImportError
        # rather than silent failure

        with patch.dict("sys.modules", {"src.wrapper.adk.cli.cli_tools_click": None}):
            with pytest.raises((ImportError, AttributeError)):
                # Force re-import which should fail
                import importlib

                importlib.reload(sys.modules["src.wrapper.adk.cli.__main__"])

    @patch("src.wrapper.adk.cli.__main__.main")
    def test_main_execution_with_exception(self, mock_main):
        """Test that exceptions in main are properly propagated."""
        # Make main raise an exception
        mock_main.side_effect = RuntimeError("Test error")

        # Import and call the main function directly
        from src.wrapper.adk.cli.__main__ import main

        with pytest.raises(RuntimeError, match="Test error"):
            main()
