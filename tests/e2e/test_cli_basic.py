import pytest
import os
import io
import sys
from unittest.mock import patch

from src.wrapper.adk.cli.cli_tools_click import main as cli_main

def run_cli_command(command_args: list[str], input_str: str = None):
    """Helper to run CLI commands by directly invoking cli_main and capturing output."""
    # Use StringIO to capture stdout and stderr
    new_stdout = io.StringIO()
    new_stderr = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = new_stdout
    sys.stderr = new_stderr

    exit_code = 0
    try:
        # Patch click.prompt and click.confirm for automated input
        with patch('src.wrapper.adk.cli.cli_create._prompt_for_model', return_value="gemini-2.0-flash-001"),             patch('src.wrapper.adk.cli.cli_create._prompt_to_choose_backend', return_value=("dummy_api_key", None, None)),             patch('src.wrapper.adk.cli.cli_create.click.confirm', return_value=True):
            cli_main.main(args=command_args, standalone_mode=False)
    except SystemExit as e:
        exit_code = e.code
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    stdout_output = new_stdout.getvalue().strip()
    stderr_output = new_stderr.getvalue().strip()

    return stdout_output, stderr_output, exit_code

def test_cli_help_command():
    """Test that the CLI displays help information."""
    stdout, stderr, returncode = run_cli_command(["--help"])
    assert returncode == 0
    assert "Usage:" in stdout
    
    assert not stderr # Stderr should be clean

def test_cli_create_project_command(tmp_path):
    """Test the 'create project' CLI command."""
    project_name = "my_new_agent"
    project_path = tmp_path / project_name

    # Change to the temporary directory before running the command
    original_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        stdout, stderr, returncode = run_cli_command(
            ["create", project_name],
            input_str="1\n1\ndummy_api_key\n" # Provide input for interactive prompts
        )
    finally:
        # Change back to the original working directory
        os.chdir(original_cwd)

    print(f"CLI Command Return Code: {returncode}")
    print(f"CLI Command STDOUT:\n{stdout}")
    print(f"CLI Command STDERR:\n{stderr}")

    assert returncode == 0
    assert f"Agent created in {project_path}" in stdout
    assert project_path.is_dir()
    assert (project_path / ".env").is_file()
    assert (project_path / "__init__.py").is_file()
    assert (project_path / "agent.py").is_file()
    assert not stderr
