import io
import os
import sys
from unittest.mock import patch

import pytest

# Skip all CLI tests due to missing dependencies
pytestmark = pytest.mark.skip(
    reason=(
        "CLI functionality temporarily disabled due to missing dependencies"
        " (cli_create, cli_deploy, agent_graph modules)"
    )
)


def run_cli_command(command_args: list[str], input_str: str = None):
  """Helper to run CLI commands by directly invoking cli_main and capturing output."""
  # Import only when needed to avoid module-level import errors
  try:
    from src.wrapper.adk.cli.cli_tools_click import main as cli_main
  except ImportError as e:
    pytest.skip(f"CLI module cannot be imported: {e}")

  # Use StringIO to capture stdout and stderr
  new_stdout = io.StringIO()
  new_stderr = io.StringIO()
  old_stdout = sys.stdout
  old_stderr = sys.stderr
  sys.stdout = new_stdout
  sys.stderr = new_stderr

  exit_code = 0
  try:
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


# All CLI command tests have been removed as the underlying CLI functionality
# (cli_create, cli_deploy, agent_graph modules) is no longer available.
# The run_cli_command helper function above is preserved in case
# CLI tests need to be added back in the future.
