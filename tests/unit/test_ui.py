from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

# Import the functions we're testing
from src.wrapper.adk.cli.utils.ui import get_cli_instance
from src.wrapper.adk.cli.utils.ui import get_textual_cli_instance


class TestGetCliInstance:
  """Test the get_cli_instance factory function."""

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_cli_instance_with_valid_dark_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with valid 'dark' theme."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function
    result = get_cli_instance('dark')

    # Verify calls
    mock_ui_theme.assert_called_once_with('dark')
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_enhanced_cli.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_cli_instance_with_valid_light_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with valid 'light' theme."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function
    result = get_cli_instance('light')

    # Verify calls
    mock_ui_theme.assert_called_once_with('light')
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_enhanced_cli.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_cli_instance_with_mixed_case_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with mixed case theme (should convert to lowercase)."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function with mixed case
    result = get_cli_instance('DARK')

    # Verify calls (should be lowercase)
    mock_ui_theme.assert_called_once_with('dark')
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_enhanced_cli.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_cli_instance_with_invalid_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with invalid theme (should handle ValueError)."""
    # Setup mocks - UITheme should raise ValueError for invalid theme
    mock_ui_theme.side_effect = ValueError('Invalid theme')
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function with invalid theme
    result = get_cli_instance('invalid_theme')

    # Verify calls
    mock_ui_theme.assert_called_once_with('invalid_theme')
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is invalid
    mock_enhanced_cli.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  def test_get_cli_instance_with_none_theme(
      self, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with None theme."""
    # Setup mocks
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function with None theme
    result = get_cli_instance(None)

    # Verify calls
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is None
    mock_enhanced_cli.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  def test_get_cli_instance_with_empty_string_theme(
      self, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with empty string theme."""
    # Setup mocks
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function with empty string theme
    result = get_cli_instance('')

    # Verify calls
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is empty
    mock_enhanced_cli.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  def test_get_cli_instance_with_default_parameters(
      self, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test creating CLI instance with default parameters (no arguments)."""
    # Setup mocks
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function with no arguments
    result = get_cli_instance()

    # Verify calls
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is None by default
    mock_enhanced_cli.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_cli_instance


class TestGetTextualCliInstance:
  """Test the get_textual_cli_instance factory function."""

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_textual_cli_instance_with_valid_dark_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with valid 'dark' theme."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function
    result = get_textual_cli_instance('dark')

    # Verify calls
    mock_ui_theme.assert_called_once_with('dark')
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_agent_tui.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_tui_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_textual_cli_instance_with_valid_light_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with valid 'light' theme."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function
    result = get_textual_cli_instance('light')

    # Verify calls
    mock_ui_theme.assert_called_once_with('light')
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_agent_tui.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_tui_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_textual_cli_instance_with_uppercase_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with uppercase theme (should convert to lowercase)."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function with uppercase
    result = get_textual_cli_instance('LIGHT')

    # Verify calls (should be lowercase)
    mock_ui_theme.assert_called_once_with('light')
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_agent_tui.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_tui_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_get_textual_cli_instance_with_invalid_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with invalid theme (should handle ValueError)."""
    # Setup mocks - UITheme should raise ValueError for invalid theme
    mock_ui_theme.side_effect = ValueError('Invalid theme')
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function with invalid theme
    result = get_textual_cli_instance('purple')

    # Verify calls
    mock_ui_theme.assert_called_once_with('purple')
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is invalid
    mock_agent_tui.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_tui_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  def test_get_textual_cli_instance_with_none_theme(
      self, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with None theme."""
    # Setup mocks
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function with None theme
    result = get_textual_cli_instance(None)

    # Verify calls
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is None
    mock_agent_tui.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_tui_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  def test_get_textual_cli_instance_with_whitespace_theme(
      self, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with whitespace-only theme."""
    # Setup mocks
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function with whitespace theme
    result = get_textual_cli_instance('   ')

    # Verify calls - whitespace should be treated as a theme attempt
    # Since "   ".lower() = "   ", this will likely be invalid and handled as such
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is just whitespace
    mock_agent_tui.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_tui_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  def test_get_textual_cli_instance_with_default_parameters(
      self, mock_rich_renderer, mock_agent_tui
  ):
    """Test creating Textual CLI instance with default parameters (no arguments)."""
    # Setup mocks
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call the function with no arguments
    result = get_textual_cli_instance()

    # Verify calls
    mock_rich_renderer.assert_not_called()  # Should not be called when theme is None by default
    mock_agent_tui.assert_called_once_with(theme=None, rich_renderer=None)
    assert result == mock_tui_instance


class TestIntegrationScenarios:
  """Test integration scenarios and edge cases."""

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_both_functions_with_same_valid_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test both factory functions with the same valid theme."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call both functions with the same theme
    cli_result = get_cli_instance('dark')

    # Reset mocks for second call
    mock_ui_theme.reset_mock()
    mock_rich_renderer.reset_mock()

    with patch('src.wrapper.adk.cli.utils.ui.AgentTUI') as mock_agent_tui:
      mock_tui_instance = Mock()
      mock_agent_tui.return_value = mock_tui_instance

      tui_result = get_textual_cli_instance('dark')

      # Verify both calls worked identically
      assert cli_result == mock_cli_instance
      assert tui_result == mock_tui_instance

      # Both should have called UITheme with "dark"
      mock_ui_theme.assert_called_with('dark')

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_numeric_theme_handling(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui, mock_enhanced_cli
  ):
    """Test how functions handle numeric themes."""
    # Setup mocks - numeric theme should cause ValueError
    mock_ui_theme.side_effect = ValueError('Invalid theme')
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call both functions with numeric theme (as string)
    cli_result = get_cli_instance('123')
    tui_result = get_textual_cli_instance('456')

    # Both should handle the error gracefully
    assert cli_result == mock_cli_instance
    assert tui_result == mock_tui_instance

    # Both should have attempted to create UITheme
    assert mock_ui_theme.call_count == 2
    mock_ui_theme.assert_any_call('123')
    mock_ui_theme.assert_any_call('456')

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_special_characters_in_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui, mock_enhanced_cli
  ):
    """Test how functions handle themes with special characters."""
    # Setup mocks - special characters should cause ValueError
    mock_ui_theme.side_effect = ValueError('Invalid theme')
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call functions with special character themes
    cli_result = get_cli_instance('dark@#$%')
    tui_result = get_textual_cli_instance('light!@#')

    # Both should handle the error gracefully
    assert cli_result == mock_cli_instance
    assert tui_result == mock_tui_instance

    # Verify the themes were processed (converted to lowercase)
    mock_ui_theme.assert_any_call('dark@#$%')
    mock_ui_theme.assert_any_call('light!@#')

  @patch('src.wrapper.adk.cli.utils.ui.EnhancedCLI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_rich_renderer_creation_with_valid_theme(
      self, mock_ui_theme, mock_rich_renderer, mock_enhanced_cli
  ):
    """Test that RichRenderer is created correctly with valid theme."""
    # Setup mocks
    mock_theme_instance = Mock()
    mock_ui_theme.return_value = mock_theme_instance
    mock_renderer_instance = Mock()
    mock_rich_renderer.return_value = mock_renderer_instance
    mock_cli_instance = Mock()
    mock_enhanced_cli.return_value = mock_cli_instance

    # Call the function
    result = get_cli_instance('dark')

    # Verify RichRenderer was created with the theme instance
    mock_rich_renderer.assert_called_once_with(mock_theme_instance)
    mock_enhanced_cli.assert_called_once_with(
        theme=mock_theme_instance, rich_renderer=mock_renderer_instance
    )
    assert result == mock_cli_instance

  @patch('src.wrapper.adk.cli.utils.ui.AgentTUI')
  @patch('src.wrapper.adk.cli.utils.ui.RichRenderer')
  @patch('src.wrapper.adk.cli.utils.ui.UITheme')
  def test_edge_case_very_long_theme_name(
      self, mock_ui_theme, mock_rich_renderer, mock_agent_tui
  ):
    """Test handling of very long theme names."""
    # Setup mocks - long theme should cause ValueError
    mock_ui_theme.side_effect = ValueError('Invalid theme')
    mock_tui_instance = Mock()
    mock_agent_tui.return_value = mock_tui_instance

    # Call function with very long theme name
    long_theme = 'a' * 1000
    result = get_textual_cli_instance(long_theme)

    # Should handle gracefully
    assert result == mock_tui_instance
    mock_ui_theme.assert_called_once_with(long_theme)
    mock_rich_renderer.assert_not_called()
    mock_agent_tui.assert_called_once_with(theme=None, rich_renderer=None)
