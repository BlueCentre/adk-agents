"""
Unit tests for src.wrapper.adk.cli.utils.__init__.py

Tests the utility functions for creating empty states for agents.
"""

import re
from typing import Any
from typing import Optional

import pytest

from src.wrapper.adk.cli.utils import create_empty_state


# Mock objects that mimic the real agent interfaces without inheritance
class TestLlmAgent:
  """Test agent that mimics LlmAgent behavior."""

  def __init__(self, instruction: str = "", sub_agents: Optional[list] = None):
    self.instruction = instruction
    self.sub_agents = sub_agents or []


class TestBaseAgent:
  """Test agent that mimics BaseAgent behavior."""

  def __init__(self, sub_agents: Optional[list] = None):
    self.sub_agents = sub_agents or []


def test_regex_pattern_extraction():
  """Test the regex pattern used to extract template variables."""
  # This tests the core regex logic from the _create_empty_state function
  pattern = r"{([\w]+)}"

  # Test various instruction patterns
  test_cases = [
      ("Hello {name}, your task is {task}", {"name", "task"}),
      (
          "Use {tool} to complete {action} with {params}",
          {"tool", "action", "params"},
      ),
      ("No variables here", set()),
      ("{single}", {"single"}),
      ("Multiple {var1} and {var2} and {var3}", {"var1", "var2", "var3"}),
      ("Duplicate {var} and {var} again", {"var"}),  # Should deduplicate
      (
          "Mixed {valid} and {123invalid} vars",
          {"valid", "123invalid"},
      ),  # \w+ includes digits
      ("", set()),
      ("Just text without braces", set()),
      ("{}", set()),  # Empty braces shouldn't match
      ("{ space }", set()),  # Spaces inside braces shouldn't match
  ]

  for instruction, expected_vars in test_cases:
    found_vars = set(re.findall(pattern, instruction))
    assert found_vars == expected_vars, f"Failed for instruction: {instruction}"


def test_create_empty_state_integration():
  """Integration test using the real create_empty_state function with test agents."""
  # Note: This test will only work if we can create agents that the function recognizes
  # Since we can't mock isinstance, we'll test what we can

  # Test with an object that won't be recognized as LlmAgent
  base_agent = TestBaseAgent()
  result = create_empty_state(base_agent)

  # For non-LLM agents, should return empty dict
  assert result == {}


def test_create_empty_state_with_initialized_states():
  """Test create_empty_state with pre-initialized states."""
  base_agent = TestBaseAgent()

  # Test with some initialized states
  initialized_states = {"existing_var": "value"}
  result = create_empty_state(base_agent, initialized_states)

  # Should return empty dict since base_agent has no instruction
  assert result == {}


def test_create_empty_state_edge_cases():
  """Test edge cases for create_empty_state function."""
  # Test with None initialized_states
  base_agent = TestBaseAgent()
  result = create_empty_state(base_agent, None)
  assert result == {}

  # Test with empty initialized_states
  result = create_empty_state(base_agent, {})
  assert result == {}


def test_template_variable_patterns():
  """Test various template variable patterns that should be recognized."""
  # Test the regex pattern directly
  pattern = r"{([\w]+)}"

  valid_patterns = [
      "{name}",
      "{task_name}",
      "{user123}",
      "{_private}",
      "{CONSTANT}",
      "{mixedCase}",
  ]

  for pattern_str in valid_patterns:
    matches = re.findall(pattern, pattern_str)
    assert len(matches) == 1, f"Should match one variable in: {pattern_str}"

  invalid_patterns = [
      "{}",  # Empty
      "{my-var}",  # Contains hyphen
      "{my var}",  # Contains space
      "{my.var}",  # Contains dot
      "{ name }",  # Spaces around name
  ]

  for pattern_str in invalid_patterns:
    matches = re.findall(pattern, pattern_str)
    assert (
        len(matches) == 0
    ), f"Should not match any variables in: {pattern_str}"


def test_exported_functions():
  """Test that required functions are exported in __all__."""
  from src.wrapper.adk.cli.utils import __all__

  expected_exports = {
      "create_empty_state",
      "get_cli_instance",
      "EnhancedCLI",
      "UITheme",
  }

  for export in expected_exports:
    assert export in __all__, f"{export} should be in __all__"


def test_imports_available():
  """Test that we can import the main functions."""
  # This verifies the module structure
  from src.wrapper.adk.cli.utils import _create_empty_state
  from src.wrapper.adk.cli.utils import create_empty_state

  # Functions should be callable
  assert callable(create_empty_state)
  assert callable(_create_empty_state)


# Test the core regex extraction logic in isolation
class TestRegexExtraction:
  """Test the regex pattern matching logic used in the utility functions."""

  def test_basic_variable_extraction(self):
    """Test basic template variable extraction."""
    pattern = r"{([\w]+)}"
    instruction = "Hello {name}, please complete {task}"

    variables = re.findall(pattern, instruction)
    assert set(variables) == {"name", "task"}

  def test_duplicate_variables(self):
    """Test that duplicate variables are handled correctly."""
    pattern = r"{([\w]+)}"
    instruction = "Use {tool} then {tool} again"

    variables = set(re.findall(pattern, instruction))
    assert variables == {"tool"}

  def test_no_variables(self):
    """Test instruction with no template variables."""
    pattern = r"{([\w]+)}"
    instruction = "This is a plain instruction"

    variables = re.findall(pattern, instruction)
    assert variables == []

  def test_empty_instruction(self):
    """Test empty instruction."""
    pattern = r"{([\w]+)}"
    instruction = ""

    variables = re.findall(pattern, instruction)
    assert variables == []

  def test_complex_variable_names(self):
    """Test various valid variable name patterns."""
    pattern = r"{([\w]+)}"
    instruction = (
        "Use {tool_name} and {API_KEY} with {user123} and {_private} and"
        " {123numeric}"
    )

    variables = set(re.findall(pattern, instruction))
    expected = {"tool_name", "API_KEY", "user123", "_private", "123numeric"}
    assert variables == expected
