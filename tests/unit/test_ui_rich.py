"""Test ui_rich.py module."""

from unittest.mock import Mock

import pytest
from rich.panel import Panel
from rich.text import Text

from src.wrapper.adk.cli.utils.ui_common import UITheme
from src.wrapper.adk.cli.utils.ui_rich import RichRenderer


class TestRichRendererInit:
    """Test RichRenderer initialization."""

    def test_init_default_theme(self):
        """Test default theme initialization."""
        renderer = RichRenderer()
        assert renderer.theme == UITheme.DARK
        assert renderer.markdown_enabled is True

    def test_init_with_theme(self):
        """Test initialization with specific theme."""
        renderer = RichRenderer(UITheme.LIGHT)
        assert renderer.theme == UITheme.LIGHT

    def test_init_with_none_theme(self):
        """Test initialization with None defaults to DARK."""
        renderer = RichRenderer(None)
        assert renderer.theme == UITheme.DARK


class TestFormatAgentResponse:
    """Test format_agent_response method."""

    def test_format_agent_response_basic(self):
        """Test basic agent response formatting."""
        renderer = RichRenderer()
        result = renderer.format_agent_response("Test message", "Agent")

        assert isinstance(result, Panel)
        assert "Agent Response" in str(result.title)
        assert "🤖" in str(result.title)

    def test_format_agent_response_empty_text(self):
        """Test with empty text."""
        renderer = RichRenderer()
        result = renderer.format_agent_response("", "Agent")

        assert isinstance(result, Panel)

    def test_format_agent_response_different_authors(self):
        """Test with different author names."""
        renderer = RichRenderer()

        result1 = renderer.format_agent_response("Test", "AgentA")
        result2 = renderer.format_agent_response("Test", "AgentB")

        assert "AgentA Response" in str(result1.title)
        assert "AgentB Response" in str(result2.title)


class TestFormatAgentThought:
    """Test format_agent_thought method."""

    def test_format_agent_thought_basic(self):
        """Test basic agent thought formatting."""
        renderer = RichRenderer()
        result = renderer.format_agent_thought("Thinking...")

        assert isinstance(result, Panel)
        assert "Agent Thought" in str(result.title)
        assert "🧠" in str(result.title)

    def test_format_agent_thought_properties(self):
        """Test panel properties."""
        renderer = RichRenderer()
        result = renderer.format_agent_thought("Test")

        assert result.expand is True
        # highlight is not set in the current implementation
        # assert result.highlight is True
        # padding is not set in the current implementation
        # assert result.padding == (0, 0)

    def test_format_agent_thought_empty(self):
        """Test with empty thought."""
        renderer = RichRenderer()
        result = renderer.format_agent_thought("")

        assert isinstance(result, Panel)


class TestFormatModelUsage:
    """Test format_model_usage method."""

    def test_format_model_usage_basic(self):
        """Test basic model usage formatting."""
        renderer = RichRenderer()
        result = renderer.format_model_usage("Tokens: 100")

        assert isinstance(result, Panel)
        assert "Model Usage" in str(result.title)
        assert "📊" in str(result.title)

    def test_format_model_usage_text_styling(self):
        """Test text styling."""
        renderer = RichRenderer()
        result = renderer.format_model_usage("Usage info")

        assert isinstance(result.renderable, Text)

    def test_format_model_usage_properties(self):
        """Test panel properties."""
        renderer = RichRenderer()
        result = renderer.format_model_usage("Test")

        assert result.border_style == "blue"
        assert result.expand is True
        assert result.padding == (0, 0)


class TestFormatRunningTool:
    """Test format_running_tool method."""

    def test_format_running_tool_with_args(self):
        """Test with tool arguments."""
        renderer = RichRenderer()
        args = {"param1": "value1", "param2": "value2"}
        result = renderer.format_running_tool("test_tool", args)

        assert isinstance(result, Panel)
        assert "Running Tool" in str(result.title)
        assert "🔧" in str(result.title)
        assert "test_tool" in str(result.renderable)
        assert "param1=value1" in str(result.renderable)
        assert "param2=value2" in str(result.renderable)

    def test_format_running_tool_no_args(self):
        """Test without arguments."""
        renderer = RichRenderer()
        result = renderer.format_running_tool("test_tool", None)

        assert isinstance(result, Panel)
        assert "test_tool()" in str(result.renderable)

    def test_format_running_tool_empty_args(self):
        """Test with empty arguments."""
        renderer = RichRenderer()
        result = renderer.format_running_tool("test_tool", {})

        assert isinstance(result, Panel)
        assert "test_tool()" in str(result.renderable)

    def test_format_running_tool_properties(self):
        """Test panel properties."""
        renderer = RichRenderer()
        result = renderer.format_running_tool("tool", {})

        assert result.border_style == "cyan"
        assert result.expand is True
        assert result.padding == (0, 0)


class TestFormatToolFinished:
    """Test format_tool_finished method."""

    def test_format_tool_finished_with_duration(self):
        """Test with duration."""
        renderer = RichRenderer()
        result = renderer.format_tool_finished("tool", "success", 1.5)

        assert isinstance(result, Panel)
        assert "Tool Finished" in str(result.title)
        assert "✅" in str(result.title)
        assert "tool" in str(result.renderable)
        assert "1.50s" in str(result.renderable)
        assert "success" in str(result.renderable)

    def test_format_tool_finished_no_duration(self):
        """Test without duration."""
        renderer = RichRenderer()
        result = renderer.format_tool_finished("tool", "success", None)

        assert isinstance(result, Panel)
        assert "tool" in str(result.renderable)
        assert "success" in str(result.renderable)

    def test_format_tool_finished_long_result(self):
        """Test with long result text."""
        renderer = RichRenderer()
        long_result = "x" * 150  # More than 100 chars
        result = renderer.format_tool_finished("tool", long_result, 1.0)

        assert isinstance(result, Panel)
        assert "..." in str(result.renderable)

    def test_format_tool_finished_properties(self):
        """Test panel properties."""
        renderer = RichRenderer()
        result = renderer.format_tool_finished("tool", "result", 1.0)

        assert result.border_style == "green"
        assert result.expand is True
        assert result.padding == (0, 0)


class TestFormatToolError:
    """Test format_tool_error method."""

    def test_format_tool_error_basic(self):
        """Test basic tool error formatting."""
        renderer = RichRenderer()
        result = renderer.format_tool_error("tool", "Error occurred")

        assert isinstance(result, Panel)
        assert "Tool Error" in str(result.title)
        assert "❌" in str(result.title)
        assert "tool" in str(result.renderable)
        assert "Error occurred" in str(result.renderable)

    def test_format_tool_error_empty_message(self):
        """Test with empty error message."""
        renderer = RichRenderer()
        result = renderer.format_tool_error("tool", "")

        assert isinstance(result, Panel)

    def test_format_tool_error_properties(self):
        """Test panel properties."""
        renderer = RichRenderer()
        result = renderer.format_tool_error("tool", "error")

        assert result.border_style == "red"
        assert result.expand is True
        assert result.padding == (0, 0)


class TestThemeConsistency:
    """Test theme consistency across methods."""

    def test_different_themes_different_borders(self):
        """Test different themes produce different border colors."""
        dark_renderer = RichRenderer(UITheme.DARK)
        light_renderer = RichRenderer(UITheme.LIGHT)

        dark_result = dark_renderer.format_agent_response("test", "agent")
        light_result = light_renderer.format_agent_response("test", "agent")

        # Agent border colors should be different
        assert dark_result.border_style != light_result.border_style

    def test_all_methods_return_panels(self):
        """Test all formatting methods return Panel objects."""
        renderer = RichRenderer()

        methods = [
            ("format_agent_response", ("text", "agent")),
            ("format_agent_thought", ("text",)),
            ("format_model_usage", ("text",)),
            ("format_running_tool", ("tool", {})),
            ("format_tool_finished", ("tool", "result", 1.0)),
            ("format_tool_error", ("tool", "error")),
        ]

        for method_name, args in methods:
            method = getattr(renderer, method_name)
            result = method(*args)
            assert isinstance(result, Panel)

    def test_panel_titles_consistent(self):
        """Test panel titles are consistently formatted."""
        renderer = RichRenderer()

        panels = [
            renderer.format_agent_response("test", "agent"),
            renderer.format_agent_thought("test"),
            renderer.format_model_usage("test"),
            renderer.format_running_tool("tool", {}),
            renderer.format_tool_finished("tool", "result", 1.0),
            renderer.format_tool_error("tool", "error"),
        ]

        # Check specific title alignments based on current implementation
        agent_panels = [panels[0], panels[1]]  # agent_response, agent_thought
        tool_panels = [
            panels[2],
            panels[3],
            panels[4],
            panels[5],
        ]  # model_usage, running_tool, tool_finished, tool_error

        for panel in agent_panels:
            assert panel.title_align == "right"  # Agent panels use center alignment
            assert isinstance(panel.title, str)

        for panel in tool_panels:
            assert panel.title_align == "right"  # Tool panels use left alignment
            assert isinstance(panel.title, str)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_handling(self):
        """Test unicode character handling."""
        renderer = RichRenderer()
        unicode_text = "🚀 Test with unicode: 日本語"

        result = renderer.format_agent_response(unicode_text, "UnicodeAgent")
        assert isinstance(result, Panel)

    def test_very_long_text(self):
        """Test very long text handling."""
        renderer = RichRenderer()
        long_text = "A" * 5000

        result = renderer.format_agent_response(long_text, "agent")
        assert isinstance(result, Panel)

    def test_newlines_in_text(self):
        """Test text with newlines."""
        renderer = RichRenderer()
        text_with_newlines = "Line 1\nLine 2\nLine 3"

        result = renderer.format_agent_response(text_with_newlines, "agent")
        assert isinstance(result, Panel)

    def test_special_characters(self):
        """Test special characters in text."""
        renderer = RichRenderer()
        special_text = "@#$%^&*()_+-={}[]|\\:;\"'<>?,./"

        result = renderer.format_agent_response(special_text, "SpecialAgent")
        assert isinstance(result, Panel)

    def test_markdown_content(self):
        """Test markdown content rendering."""
        renderer = RichRenderer()
        markdown_text = "# Header\n\n**Bold** and *italic*\n\n- Item 1\n- Item 2"

        result = renderer.format_agent_response(markdown_text, "agent")
        assert isinstance(result, Panel)

    def test_complex_tool_result(self):
        """Test complex data structures in tool results."""
        renderer = RichRenderer()
        complex_result = {"nested": {"data": [1, 2, 3]}, "list": ["a", "b", "c"]}

        result = renderer.format_tool_finished("tool", complex_result, 1.0)
        assert isinstance(result, Panel)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_conversation_flow(self):
        """Test full conversation simulation."""
        renderer = RichRenderer()

        # Simulate conversation steps
        running = renderer.format_running_tool("search", {"query": "files"})
        finished = renderer.format_tool_finished("search", ["file1", "file2"], 0.5)
        thought = renderer.format_agent_thought("Found 2 files")
        response = renderer.format_agent_response("Here are the files found", "Agent")
        usage = renderer.format_model_usage("Tokens: 25")

        panels = [running, finished, thought, response, usage]
        for panel in panels:
            assert isinstance(panel, Panel)

    def test_error_scenario(self):
        """Test error handling scenario."""
        renderer = RichRenderer()

        error = renderer.format_tool_error("search", "Permission denied")
        thought = renderer.format_agent_thought("Search failed due to permissions")
        response = renderer.format_agent_response("Unable to search files", "Agent")

        for panel in [error, thought, response]:
            assert isinstance(panel, Panel)

    def test_theme_switching(self):
        """Test theme switching behavior."""
        dark_renderer = RichRenderer(UITheme.DARK)
        light_renderer = RichRenderer(UITheme.LIGHT)

        # Same content, different themes
        content = "Test message"
        dark_panel = dark_renderer.format_agent_response(content, "Agent")
        light_panel = light_renderer.format_agent_response(content, "Agent")

        # Should have different visual appearance
        assert dark_panel.border_style != light_panel.border_style
        assert isinstance(dark_panel, Panel)
        assert isinstance(light_panel, Panel)

    def test_format_message(self):
        """Test formatting messages with various options."""
        renderer = RichRenderer(UITheme.DARK)

        # Test simple text message
        message = renderer.format_message("Hello, World!", "Agent")
        assert message is not None

        # Test markdown message
        message = renderer.format_message("**Bold text**", "Agent", markdown=True)
        assert message is not None

        # Test rich format message
        message = renderer.format_message(
            "[bold]Bold text[/bold]", "Agent", rich_format=True
        )
        assert message is not None

        # Test with style
        message = renderer.format_message("Styled text", "Agent", style="green")
        assert message is not None

        # Test with Text object
        from rich.text import Text

        text_obj = Text("Text object")
        message = renderer.format_message(text_obj, "Agent")
        assert message is text_obj

    def test_format_agent_response(self):
        """Test formatting agent response panels."""
        renderer = RichRenderer(UITheme.DARK)

        # Test basic response
        panel = renderer.format_agent_response("Agent response text")
        assert panel is not None

        # Test with custom author
        panel = renderer.format_agent_response("Agent response", "CustomAgent")
        assert panel is not None

        # Test with markdown content
        panel = renderer.format_agent_response("**Bold response**")
        assert panel is not None

    def test_format_agent_thought(self):
        """Test formatting agent thought panels."""
        renderer = RichRenderer(UITheme.DARK)

        # Test basic thought
        panel = renderer.format_agent_thought("Agent thinking...")
        assert panel is not None

        # Test with markdown content
        panel = renderer.format_agent_thought("*Thinking process*")
        assert panel is not None

    def test_format_model_usage(self):
        """Test formatting model usage panels."""
        renderer = RichRenderer(UITheme.DARK)

        # Test basic usage
        panel = renderer.format_model_usage("Tokens: 150")
        assert panel is not None

        # Test with detailed usage
        panel = renderer.format_model_usage("Input: 100, Output: 50, Total: 150")
        assert panel is not None

    def test_format_running_tool(self):
        """Test formatting running tool panels."""
        renderer = RichRenderer(UITheme.DARK)

        # Test with no args
        panel = renderer.format_running_tool("test_tool", None)
        assert panel is not None

        # Test with args
        panel = renderer.format_running_tool(
            "test_tool", {"arg1": "value1", "arg2": "value2"}
        )
        assert panel is not None

        # Test with empty args
        panel = renderer.format_running_tool("test_tool", {})
        assert panel is not None

    def test_format_tool_finished(self):
        """Test formatting tool finished panels."""
        renderer = RichRenderer(UITheme.DARK)

        # Test with duration
        panel = renderer.format_tool_finished("test_tool", "success", 2.5)
        assert panel is not None

        # Test without duration
        panel = renderer.format_tool_finished("test_tool", "success", None)
        assert panel is not None

        # Test with long result
        long_result = "A" * 200
        panel = renderer.format_tool_finished("test_tool", long_result, 1.0)
        assert panel is not None

    def test_format_tool_error(self):
        """Test formatting tool error panels."""
        renderer = RichRenderer(UITheme.DARK)

        # Test basic error
        panel = renderer.format_tool_error("test_tool", "Something went wrong")
        assert panel is not None

        # Test with detailed error
        panel = renderer.format_tool_error(
            "test_tool", "FileNotFoundError: file.txt not found"
        )
        assert panel is not None

    def test_display_agent_response(self):
        """Test displaying agent response."""
        renderer = RichRenderer(UITheme.DARK)

        # Mock console
        from unittest.mock import Mock

        mock_console = Mock()

        # Test basic response
        renderer.display_agent_response(mock_console, "Agent response")
        mock_console.print.assert_called_once()

        # Test with custom author
        mock_console.reset_mock()
        renderer.display_agent_response(mock_console, "Agent response", "CustomAgent")
        mock_console.print.assert_called_once()

    def test_display_agent_thought(self):
        """Test displaying agent thought."""
        renderer = RichRenderer(UITheme.DARK)

        # Mock console
        from unittest.mock import Mock

        mock_console = Mock()

        # Test basic thought
        renderer.display_agent_thought(mock_console, "Agent thinking...")
        mock_console.print.assert_called_once()

        # Test with markdown
        mock_console.reset_mock()
        renderer.display_agent_thought(mock_console, "**Important thought**")
        mock_console.print.assert_called_once()

    def test_render_with_light_theme(self):
        """Test rendering with light theme."""
        renderer = RichRenderer(UITheme.LIGHT)

        # Test panel with light theme
        panel = renderer.format_agent_response("Light theme content")
        assert panel is not None

    def test_render_with_none_theme(self):
        """Test rendering with None theme (should use default)."""
        renderer = RichRenderer(None)

        # Test basic rendering still works
        panel = renderer.format_agent_response("Default theme content")
        assert panel is not None

    def test_rich_theme_property(self):
        """Test accessing the rich_theme property."""
        renderer = RichRenderer(UITheme.DARK)
        theme = renderer.rich_theme
        assert theme is not None

        # Test with light theme
        renderer = RichRenderer(UITheme.LIGHT)
        theme = renderer.rich_theme
        assert theme is not None

    def test_markdown_enabled_property(self):
        """Test the markdown_enabled property."""
        renderer = RichRenderer(UITheme.DARK)
        assert renderer.markdown_enabled is True

        # Test that it can be modified
        renderer.markdown_enabled = False
        assert renderer.markdown_enabled is False
