import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from textual.widgets import RichLog

from src.wrapper.adk.cli.utils.ui_common import UITheme
from src.wrapper.adk.cli.utils.ui_rich import RichRenderer
from src.wrapper.adk.cli.utils.ui_textual import (
    AgentTUI,
    CategorizedInput,
    CompletionWidget,
    SubmittableTextArea,
)


def get_log_text(log: RichLog) -> str:
    """Extracts plain text from a RichLog, handling Text and Panel objects."""
    text_parts = []
    for line in log.lines:
        if isinstance(line, Text):
            text_parts.append(line.plain)
        elif isinstance(line, Panel) and hasattr(line.renderable, "markup"):
            # For Panels containing Markdown
            text_parts.append(line.renderable.markup)
        elif isinstance(line, Panel) and hasattr(line.renderable, "plain"):
            # For Panels containing Text
            text_parts.append(line.renderable.plain)
    return "".join(text_parts)


@pytest.mark.asyncio
async def test_agent_tui_initialization():
    """Test the initialization of the AgentTUI app."""
    app = AgentTUI(theme=UITheme.LIGHT)
    async with app.run_test():
        assert app._current_ui_theme == UITheme.LIGHT
        assert isinstance(app.rich_renderer, RichRenderer)
        assert isinstance(app.console, Console)


@pytest.mark.asyncio
async def test_agent_tui_compose():
    """Test the composition of the AgentTUI app."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        assert pilot.app.query_one("#output-log", RichLog)
        assert pilot.app.query_one("#event-log", RichLog)
        assert pilot.app.query_one("#input-area", CategorizedInput)
        assert pilot.app.query_one("#status-bar")


@pytest.mark.asyncio
async def test_toggle_multiline_input():
    """Test toggling between single and multi-line input."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        # Initial state is single-line input
        assert isinstance(pilot.app.query_one("#input-area"), CategorizedInput)

        # Toggle to multi-line
        await pilot.press("f12")
        assert isinstance(pilot.app.query_one("#input-area"), SubmittableTextArea)

        # Toggle back to single-line
        await pilot.press("f12")
        assert isinstance(pilot.app.query_one("#input-area"), CategorizedInput)


@pytest.mark.asyncio
async def test_callbacks_registration():
    """Test registration of input and interrupt callbacks."""
    app = AgentTUI()
    input_cb = AsyncMock()
    interrupt_cb = AsyncMock()

    app.register_input_callback(input_cb)
    app.register_interrupt_callback(interrupt_cb)

    async with app.run_test():
        assert app.input_callback == input_cb
        assert app.interrupt_callback == interrupt_cb


@pytest.mark.asyncio
async def test_input_submission():
    """Test submitting input from the user."""
    app = AgentTUI()
    input_cb = AsyncMock()
    app.register_input_callback(input_cb)

    async with app.run_test() as pilot:
        input_widget = pilot.app.query_one(CategorizedInput)
        input_widget.value = "test input"
        await pilot.press("enter")
        input_cb.assert_awaited_once_with("test input")
        # Cleanup to prevent state leakage
        input_widget.value = ""
        pilot.app.user_input_history.clear()


@pytest.mark.asyncio
async def test_interrupt_action():
    """Test the interrupt action (Ctrl+C)."""
    app = AgentTUI()
    interrupt_cb = AsyncMock()
    app.register_interrupt_callback(interrupt_cb)

    async with app.run_test():
        with patch.object(app, "exit") as mock_exit:
            app.action_interrupt_agent()
            await asyncio.sleep(0.1)
            interrupt_cb.assert_awaited_once()
            mock_exit.assert_not_called()


@pytest.mark.asyncio
async def test_theme_toggle():
    """Test toggling the theme."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        initial_theme = pilot.app._current_ui_theme
        await pilot.press("ctrl+t")
        assert pilot.app._current_ui_theme != initial_theme
        await pilot.press("ctrl+t")
        assert pilot.app._current_ui_theme == initial_theme


@pytest.mark.asyncio
async def test_thought_pane_toggle():
    """Test toggling the thought pane visibility."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        assert pilot.app.agent_thought_enabled is True
        assert pilot.app.query_one("#event-log")

        await pilot.press("ctrl+y")
        assert pilot.app.agent_thought_enabled is False
        assert pilot.app.query_one("#event-log").display is False

        await pilot.press("ctrl+y")
        assert pilot.app.agent_thought_enabled is True
        assert pilot.app.query_one("#event-log").display is True


@pytest.mark.asyncio
async def test_categorized_input_history():
    """Test history navigation in CategorizedInput."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        input_widget = pilot.app.query_one(CategorizedInput)
        input_widget.value = ""  # Ensure value is empty
        input_widget.add_to_history("cmd1")
        input_widget.add_to_history("cmd2")

        await pilot.press("up")
        assert input_widget.value == "cmd2"
        await pilot.press("up")
        assert input_widget.value == "cmd1"
        await pilot.press("down")
        assert input_widget.value == "cmd2"
        await pilot.press("down")
        assert input_widget.value == ""


@pytest.mark.skip(reason="RichLog not updating in tests")
@pytest.mark.asyncio
async def test_add_output():
    """Test adding output to the RichLog."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        output_log = pilot.app.query_one("#output-log", RichLog)
        pilot.app.add_output("test message")
        await asyncio.sleep(0.2)
        content = get_log_text(output_log)
        assert "User: test message" in content


@pytest.mark.asyncio
async def test_add_agent_thought():
    """Test adding agent thoughts to the event log."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        with patch.object(pilot.app.query_one("#event-log"), "write") as mock_write:
            pilot.app.add_agent_thought("Thinking...")
            await asyncio.sleep(0.1)
            mock_write.assert_called_once()
            call_args = mock_write.call_args[0][0]
            assert isinstance(call_args, Panel)
            assert "Thinking..." in call_args.renderable.markup


@pytest.mark.asyncio
async def test_categorized_input_completion():
    """Test tab completion in CategorizedInput."""
    app = AgentTUI()
    commands = {"test": ["command1", "command2"]}
    app.user_categorized_commands = commands

    async with app.run_test() as pilot:
        input_widget = pilot.app.query_one(CategorizedInput)
        input_widget.value = "com"
        with patch.object(input_widget.app, "push_screen") as mock_push_screen:
            await pilot.press("tab")
            mock_push_screen.assert_called_once()
            completion_widget = mock_push_screen.call_args[0][0]
            assert isinstance(completion_widget, CompletionWidget)
            assert "command1" in completion_widget.completions


@pytest.mark.asyncio
async def test_completion_widget_selection():
    """Test selecting a completion from the CompletionWidget."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        completions = ["test1", "test2"]
        widget = CompletionWidget(completions, {})
        with patch.object(widget, "dismiss") as mock_dismiss:
            await pilot.app.push_screen(widget)
            await pilot.press("enter")
            mock_dismiss.assert_called_once_with("test1")


@pytest.mark.asyncio
async def test_display_model_usage():
    """Test display of model usage."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        with patch.object(pilot.app.query_one("#event-log"), "write") as mock_write:
            pilot.app.display_model_usage(
                total_tokens=150,
                thinking_tokens=25,
                model_name="gpt-4",
            )
            await asyncio.sleep(0.1)
            mock_write.assert_called()
            last_call_args = mock_write.call_args[0][0]
            assert isinstance(last_call_args, Panel)
            renderable_text = last_call_args.renderable.plain
            assert "150" in renderable_text
            assert "gpt-4" in renderable_text


@pytest.mark.asyncio
async def test_add_tool_event():
    """Test adding tool events."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        with patch.object(pilot.app.query_one("#event-log"), "write") as mock_write:
            pilot.app.add_tool_event("test_tool", "start", {"arg": "value"})
            await asyncio.sleep(0.1)
            mock_write.assert_called_once()
            call_args = mock_write.call_args[0][0]
            assert isinstance(call_args, Panel)
            renderable_text = call_args.renderable.plain
            assert "test_tool" in renderable_text
            assert "arg=value" in renderable_text


@pytest.mark.skip(reason="RichLog not updating in tests")
@pytest.mark.asyncio
async def test_builtin_commands():
    """Test built-in commands like /exit, /clear, /help."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        output_log = pilot.app.query_one("#output-log", RichLog)
        pilot.app.add_output("some content")
        await asyncio.sleep(0.2)
        content = get_log_text(output_log)
        assert "User: some content" in content

        input_widget = pilot.app.query_one(CategorizedInput)
        input_widget.value = "/clear"
        await pilot.press("enter")
        await asyncio.sleep(0.2)
        content = get_log_text(output_log)
        assert "User: some content" not in content

        input_widget.value = "/help"
        await pilot.press("enter")
        await asyncio.sleep(0.2)
        content = get_log_text(output_log)
        assert "Available Commands" in content

        with patch.object(app, "exit") as mock_exit:
            input_widget.value = "/exit"
            await pilot.press("enter")
            mock_exit.assert_called_once()


@pytest.mark.skip(reason="Key press not working in test")
@pytest.mark.asyncio
async def test_submittable_text_area_submit():
    """Test Ctrl+Enter submission for SubmittableTextArea."""
    app = AgentTUI()
    input_cb = AsyncMock()
    app.register_input_callback(input_cb)

    async with app.run_test() as pilot:
        await pilot.press("f12")  # Switch to multiline
        text_area = pilot.app.query_one("#input-area")
        assert isinstance(text_area, SubmittableTextArea)
        text_area.text = "multi-line\ninput"

        await pilot.press("ctrl+enter")
        await asyncio.sleep(0.1)  # Give time for message to be processed

        input_cb.assert_awaited_once_with("multi-line\ninput")
        # Text area should be cleared after submission
        assert text_area.text == ""


@pytest.mark.asyncio
async def test_start_stop_thinking_animation():
    """Test the thinking animation start and stop."""
    app = AgentTUI()
    async with app.run_test() as pilot:
        pilot.app.start_thinking()
        assert pilot.app.agent_thinking is True
        assert pilot.app._thinking_timer is not None
        await asyncio.sleep(0.5)
        status_bar = pilot.app.query_one("#status-bar")
        assert "Thinking" in str(status_bar.renderable)

        pilot.app.stop_thinking()
        assert pilot.app.agent_thinking is False
        assert pilot.app._thinking_timer is None
