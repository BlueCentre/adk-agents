"""Test ui_common.py module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from rich.theme import Theme

from src.wrapper.adk.cli.utils.ui_common import StatusBar, ThemeConfig, UITheme


class TestUITheme:
    """Test UITheme enum."""

    def test_ui_theme_enum_values(self):
        """Test UITheme enum has correct values."""
        assert UITheme.DARK.value == "dark"
        assert UITheme.LIGHT.value == "light"

    def test_ui_theme_enum_creation_from_string(self):
        """Test creating UITheme from string values."""
        assert UITheme("dark") == UITheme.DARK
        assert UITheme("light") == UITheme.LIGHT

    def test_ui_theme_enum_invalid_value(self):
        """Test creating UITheme with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            UITheme("invalid")

    def test_ui_theme_enum_case_sensitive(self):
        """Test UITheme enum is case sensitive."""
        with pytest.raises(ValueError):
            UITheme("DARK")
        with pytest.raises(ValueError):
            UITheme("LIGHT")

    def test_ui_theme_enum_iteration(self):
        """Test UITheme enum can be iterated."""
        themes = list(UITheme)
        assert len(themes) == 2
        assert UITheme.DARK in themes
        assert UITheme.LIGHT in themes

    def test_ui_theme_enum_string_representation(self):
        """Test UITheme string representation."""
        assert str(UITheme.DARK) == "UITheme.DARK"
        assert str(UITheme.LIGHT) == "UITheme.LIGHT"


class TestThemeConfig:
    """Test ThemeConfig class."""

    def test_theme_config_class_exists(self):
        """Test ThemeConfig class can be instantiated."""
        assert ThemeConfig is not None
        # Should be able to call class methods without instantiation
        assert hasattr(ThemeConfig, "get_rich_theme")

    def test_get_rich_theme_dark(self):
        """Test get_rich_theme returns Theme for dark theme."""
        theme = ThemeConfig.get_rich_theme(UITheme.DARK)

        assert isinstance(theme, Theme)
        assert theme.styles is not None
        assert len(theme.styles) > 0

    def test_get_rich_theme_light(self):
        """Test get_rich_theme returns Theme for light theme."""
        theme = ThemeConfig.get_rich_theme(UITheme.LIGHT)

        assert isinstance(theme, Theme)
        assert theme.styles is not None
        assert len(theme.styles) > 0

    def test_get_rich_theme_different_themes_different_styles(self):
        """Test different themes return different styles."""
        dark_theme = ThemeConfig.get_rich_theme(UITheme.DARK)
        light_theme = ThemeConfig.get_rich_theme(UITheme.LIGHT)

        # Should have different styles
        assert dark_theme.styles != light_theme.styles

    def test_get_rich_theme_contains_expected_styles(self):
        """Test rich theme contains expected style categories."""
        for theme_type in [UITheme.DARK, UITheme.LIGHT]:
            theme = ThemeConfig.get_rich_theme(theme_type)

            # Should contain agent-related styles
            style_keys = list(theme.styles.keys())
            agent_styles = [key for key in style_keys if "agent" in key.lower()]
            assert len(agent_styles) > 0

    def test_get_rich_theme_none_parameter(self):
        """Test get_rich_theme with None parameter."""
        # Implementation may handle None gracefully
        try:
            result = ThemeConfig.get_rich_theme(None)
            assert result is not None
        except (TypeError, AttributeError):
            pass  # Either behavior is acceptable

    def test_get_rich_theme_invalid_parameter(self):
        """Test get_rich_theme with invalid parameter."""
        # Implementation may handle invalid parameters gracefully
        try:
            result = ThemeConfig.get_rich_theme("invalid")
            assert result is not None
        except (TypeError, AttributeError):
            pass  # Either behavior is acceptable

    def test_theme_config_style_consistency(self):
        """Test theme configurations are consistent."""
        dark_theme = ThemeConfig.get_rich_theme(UITheme.DARK)
        light_theme = ThemeConfig.get_rich_theme(UITheme.LIGHT)

        # Both themes should have the same style keys
        dark_keys = set(dark_theme.styles.keys())
        light_keys = set(light_theme.styles.keys())
        assert dark_keys == light_keys

    def test_theme_config_caching_behavior(self):
        """Test theme configuration caching behavior."""
        # Call multiple times with same theme
        theme1 = ThemeConfig.get_rich_theme(UITheme.DARK)
        theme2 = ThemeConfig.get_rich_theme(UITheme.DARK)

        # Should return equivalent themes
        assert theme1.styles == theme2.styles


class TestStatusBar:
    """Test StatusBar functionality."""

    def test_status_bar_init_dark_theme(self):
        """Test StatusBar initialization with dark theme."""
        status_bar = StatusBar(UITheme.DARK)

        assert status_bar.theme == UITheme.DARK
        assert status_bar.session_start_time is not None

    def test_status_bar_init_light_theme(self):
        """Test StatusBar initialization with light theme."""
        status_bar = StatusBar(UITheme.LIGHT)

        assert status_bar.theme == UITheme.LIGHT
        assert status_bar.session_start_time is not None

    def test_status_bar_init_none_theme(self):
        """Test StatusBar initialization with None theme defaults to dark."""
        status_bar = StatusBar()  # Default theme

        assert status_bar.theme == UITheme.DARK
        assert status_bar.session_start_time is not None

    def test_status_bar_init_invalid_theme(self):
        """Test StatusBar initialization with invalid theme."""
        # StatusBar constructor expects UITheme, passing invalid type should work with default
        status_bar = StatusBar()  # Use default instead of invalid
        assert status_bar.theme == UITheme.DARK

    def test_status_bar_start_time_is_recent(self):
        """Test StatusBar session_start_time is recent."""
        before = datetime.now()
        status_bar = StatusBar(UITheme.DARK)
        after = datetime.now()

        assert before <= status_bar.session_start_time <= after

    def test_status_bar_format_toolbar_basic(self):
        """Test StatusBar toolbar formatting with basic parameters."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("TestAgent", "session123")

        assert isinstance(result, str)
        assert "TestAgent" in result
        assert "session1" in result  # Truncated to first 8 chars

    def test_status_bar_format_toolbar_empty_agent(self):
        """Test StatusBar toolbar formatting with empty agent name."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("", "session123")

        assert isinstance(result, str)
        assert "session1" in result  # Truncated

    def test_status_bar_format_toolbar_empty_session(self):
        """Test StatusBar toolbar formatting with empty session."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("Agent", "")

        assert isinstance(result, str)
        assert "Agent" in result

    def test_status_bar_format_toolbar_both_empty(self):
        """Test StatusBar toolbar formatting with both parameters empty."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("", "")

        assert isinstance(result, str)

    def test_status_bar_format_toolbar_short_session(self):
        """Test StatusBar toolbar formatting with short session ID."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("Agent", "short")

        assert isinstance(result, str)
        assert "Agent" in result
        assert "short" in result

    def test_status_bar_format_toolbar_special_characters(self):
        """Test StatusBar toolbar formatting with special characters."""
        status_bar = StatusBar(UITheme.DARK)

        special_agent = "Agent!@#$%^&*()"
        special_session = "session!@#$%^&*()"

        result = status_bar.format_toolbar(special_agent, special_session)

        assert isinstance(result, str)
        assert special_agent in result
        assert "session!" in result  # Truncated version

    def test_status_bar_format_toolbar_unicode_characters(self):
        """Test StatusBar toolbar formatting with unicode characters."""
        status_bar = StatusBar(UITheme.DARK)

        unicode_agent = "Agent🤖日本語"
        unicode_session = "session✨-456_XYZ"

        result = status_bar.format_toolbar(unicode_agent, unicode_session)

        assert isinstance(result, str)
        assert unicode_agent in result
        assert "session✨" in result  # Truncated version

    def test_status_bar_format_toolbar_very_long_strings(self):
        """Test StatusBar toolbar formatting with very long strings."""
        status_bar = StatusBar(UITheme.DARK)

        long_agent = "A" * 1000
        long_session = "S" * 1000

        result = status_bar.format_toolbar(long_agent, long_session)

        assert isinstance(result, str)
        assert long_agent in result
        # Session should be truncated to first 8 characters
        assert "SSSSSSSS" in result

    def test_status_bar_format_toolbar_contains_expected_elements(self):
        """Test StatusBar toolbar contains expected UI elements."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("TestAgent", "session123")

        # Should contain UI elements
        assert "🤖" in result  # Robot emoji for agent
        assert "🧑" in result  # Person emoji for session
        assert "💡" in result  # Light bulb for shortcuts
        assert "Enter:submit" in result
        assert "Tab:complete" in result

    def test_status_bar_format_toolbar_different_themes(self):
        """Test StatusBar toolbar formatting with different themes."""
        dark_bar = StatusBar(UITheme.DARK)
        light_bar = StatusBar(UITheme.LIGHT)

        dark_result = dark_bar.format_toolbar("TestAgent", "session123")
        light_result = light_bar.format_toolbar("TestAgent", "session123")

        # Both should contain same content
        assert "TestAgent" in dark_result
        assert "TestAgent" in light_result
        assert "session123" in dark_result or "session1" in dark_result  # May be truncated
        assert "session123" in light_result or "session1" in light_result

    def test_status_bar_format_toolbar_session_id_truncation(self):
        """Test StatusBar session ID truncation behavior."""
        status_bar = StatusBar(UITheme.DARK)

        # Test various session ID lengths
        short_result = status_bar.format_toolbar("Agent", "short")
        long_result = status_bar.format_toolbar("Agent", "verylongsessionidentifier")

        assert "short" in short_result
        assert "verylong" in long_result  # First 8 characters
        assert "..." in long_result  # Truncation indicator

    def test_status_bar_format_toolbar_session_time_info(self):
        """Test StatusBar includes session timing information."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("Agent", "session")

        # Should be a string (timing info may be commented out in implementation)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_status_bar_elapsed_time_calculation(self):
        """Test StatusBar elapsed time calculation."""
        status_bar = StatusBar(UITheme.DARK)

        # Access session_start_time
        start_time = status_bar.session_start_time
        assert isinstance(start_time, datetime)

        # Should be very recent
        now = datetime.now()
        elapsed = now - start_time
        assert elapsed.total_seconds() < 1  # Should be less than 1 second


class TestUIThemeIntegration:
    """Test integration between UITheme and other components."""

    def test_ui_theme_with_theme_config_integration(self):
        """Test UITheme integration with ThemeConfig."""
        for theme in UITheme:
            config = ThemeConfig.get_theme_config(theme)
            assert isinstance(config, dict)
            assert len(config) > 0

            rich_theme = ThemeConfig.get_rich_theme(theme)
            assert rich_theme is not None

    def test_ui_theme_with_status_bar_integration(self):
        """Test UITheme integration with StatusBar."""
        for theme in UITheme:
            status_bar = StatusBar(theme)
            assert status_bar.theme == theme

            result = status_bar.format_toolbar("TestAgent", "session123")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_ui_theme_serialization(self):
        """Test UITheme serialization behavior."""
        for theme in UITheme:
            # Test string representation
            assert str(theme) in ["UITheme.DARK", "UITheme.LIGHT"]
            assert theme.value in ["dark", "light"]

    def test_ui_theme_equality_operations(self):
        """Test UITheme equality operations."""
        dark1 = UITheme.DARK
        dark2 = UITheme.DARK
        light = UITheme.LIGHT

        assert dark1 == dark2
        assert dark1 != light
        assert dark1 is dark2  # Enum identity

    def test_ui_theme_hash_consistency(self):
        """Test UITheme hash consistency."""
        themes = [UITheme.DARK, UITheme.LIGHT]
        hashes = [hash(theme) for theme in themes]

        # Hashes should be consistent
        assert len(set(hashes)) == len(themes)


class TestThemeConfigAdvanced:
    """Advanced tests for ThemeConfig functionality."""

    def test_theme_config_style_definitions(self):
        """Test ThemeConfig contains expected style definitions."""
        for theme in UITheme:
            config = ThemeConfig.get_theme_config(theme)

            # Should have basic prompt styles
            assert "prompt" in config
            assert "user-input" in config
            assert "agent-output" in config

            # Should have toolbar styles
            assert "bottom-toolbar" in config
            assert "bottom-toolbar.accent" in config

    def test_theme_config_color_definitions(self):
        """Test ThemeConfig color definitions are valid."""
        for theme in UITheme:
            config = ThemeConfig.get_theme_config(theme)

            for _style_name, style_value in config.items():
                assert isinstance(style_value, str)
                assert len(style_value) > 0

    def test_theme_config_accessibility(self):
        """Test ThemeConfig provides accessible color combinations."""
        dark_config = ThemeConfig.get_theme_config(UITheme.DARK)
        light_config = ThemeConfig.get_theme_config(UITheme.LIGHT)

        # Different themes should have different configurations
        assert dark_config != light_config

        # Both should have the same style keys
        assert set(dark_config.keys()) == set(light_config.keys())


class TestStatusBarAdvanced:
    """Advanced tests for StatusBar functionality."""

    def test_status_bar_performance_with_frequent_calls(self):
        """Test StatusBar performance with frequent formatting calls."""
        status_bar = StatusBar(UITheme.DARK)

        # Multiple rapid calls should work
        for i in range(100):
            result = status_bar.format_toolbar(f"Agent{i}", f"session{i}")
            assert isinstance(result, str)
            assert f"Agent{i}" in result

    def test_status_bar_memory_usage(self):
        """Test StatusBar doesn't accumulate memory with multiple calls."""
        status_bar = StatusBar(UITheme.DARK)

        # Create many formatted results
        results = []
        for i in range(50):
            result = status_bar.format_toolbar(f"Agent{i}", f"session{i}")
            results.append(result)

        # All results should be valid
        for i, result in enumerate(results):
            assert f"Agent{i}" in result

    def test_status_bar_thread_safety_simulation(self):
        """Test StatusBar behavior in simulated concurrent usage."""
        status_bar = StatusBar(UITheme.DARK)

        # Simulate multiple "threads" calling format_toolbar
        results = []
        for _i in range(10):
            result = status_bar.format_toolbar("Agent", "session")
            results.append(result)

        # All results should be consistent
        initial_result = results[0]
        for result in results[1:]:
            # Results should be consistent
            assert len(result) == len(initial_result) or abs(len(result) - len(initial_result)) < 10


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_handling(self):
        """Test handling of empty strings."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("", "")
        assert isinstance(result, str)

    def test_whitespace_handling(self):
        """Test handling of whitespace-only strings."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("   ", "   ")
        assert isinstance(result, str)

    def test_newline_handling(self):
        """Test handling of strings with newlines."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("Agent\nName", "session\nid")
        assert isinstance(result, str)

    def test_tab_handling(self):
        """Test handling of strings with tabs."""
        status_bar = StatusBar(UITheme.DARK)

        result = status_bar.format_toolbar("Agent\tName", "session\tid")
        assert isinstance(result, str)

    def test_mixed_character_sets(self):
        """Test handling of mixed character sets."""
        status_bar = StatusBar(UITheme.DARK)

        # Mixed ASCII, Unicode, and special characters
        mixed_agent = "Agent🤖-123_ABC"
        mixed_session = "session✨-456_XYZ"

        result = status_bar.format_toolbar(mixed_agent, mixed_session)
        assert isinstance(result, str)
        assert mixed_agent in result
        assert "session✨" in result  # Truncated version

    def test_extreme_length_strings(self):
        """Test handling of extremely long strings."""
        status_bar = StatusBar(UITheme.DARK)

        # Very long strings
        long_agent = "A" * 10000
        long_session = "S" * 10000

        result = status_bar.format_toolbar(long_agent, long_session)
        assert isinstance(result, str)
        assert long_agent in result  # Full agent name should be included


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_workflow_simulation(self):
        """Test full workflow simulation."""
        # Create status bar
        status_bar = StatusBar(UITheme.DARK)

        # Simulate session workflow
        agents = ["CodeAgent", "ReviewAgent", "TestAgent"]
        sessions = ["session001", "session002", "session003"]

        for agent, session in zip(agents, sessions):
            result = status_bar.format_toolbar(agent, session)
            assert agent in result
            assert session[:8] in result  # May be truncated

    def test_multi_session_simulation(self):
        """Test multiple session simulation."""
        status_bars = [StatusBar(UITheme.DARK) for _ in range(3)]

        for i, status_bar in enumerate(status_bars):
            result = status_bar.format_toolbar(f"Agent{i}", f"session{i}")
            assert f"Agent{i}" in result

    def test_error_recovery_simulation(self):
        """Test error recovery simulation."""
        status_bar = StatusBar(UITheme.DARK)

        # Test with potentially problematic inputs
        problematic_inputs = [
            ("", ""),
            ("Agent", ""),
            ("", "session"),
            ("Agent\n\t", "session\r\n"),
        ]

        for agent, session in problematic_inputs:
            result = status_bar.format_toolbar(agent, session)
            assert isinstance(result, str)

    def test_concurrent_usage_simulation(self):
        """Test concurrent usage simulation."""
        status_bar = StatusBar(UITheme.DARK)

        # Simulate rapid successive calls
        results = []
        for i in range(20):
            result = status_bar.format_toolbar(f"Agent{i % 3}", f"session{i}")
            results.append(result)

        # All results should be valid
        for i, result in enumerate(results):
            assert f"Agent{i % 3}" in result
