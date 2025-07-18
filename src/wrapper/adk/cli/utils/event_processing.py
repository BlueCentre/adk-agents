"""Shared agent event processing utilities for CLI modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Protocol

from google.genai import types


@dataclass
class ProcessedAgentEvent:
    """Represents a processed agent event with categorized content parts."""

    regular_text: str
    thought_parts: List[types.Part]
    function_parts: List[types.Part]
    author: str
    usage_metadata: Any = None


class EventDisplayInterface(Protocol):
    """Interface for displaying different types of agent content."""

    def display_agent_response(self, text: str, author: str) -> None:
        """Display regular agent response text."""
        ...

    def display_agent_thought(self, text: str) -> None:
        """Display agent thought content."""
        ...

    def display_function_content(self, text: str) -> None:
        """Display function call content."""
        ...

    def display_usage_metadata(self, usage_metadata: Any, model_name: str) -> None:
        """Display token usage metadata."""
        ...


class AgentEventProcessor:
    """Shared utilities for processing agent events across different CLI modes."""

    def __init__(self, display_interface: EventDisplayInterface):
        self.display_interface = display_interface

    def process_event(self, event: Any, model_name: str = "Unknown") -> None:
        """
        Process an agent event and display it using the configured display interface.

        Args:
            event: The agent event to process
            model_name: The name of the model (for usage metadata display)
        """
        if not event.content or not event.content.parts:
            # Check for usage metadata even if no content parts
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                self.display_interface.display_usage_metadata(
                    event.usage_metadata, model_name
                )
            return

        regular_parts = []
        thought_parts = []
        function_parts = []

        # Separate agent thought and response content from parts
        for part in event.content.parts:
            if hasattr(part, "thought") and part.thought:
                thought_parts.append(part)
            elif hasattr(part, "function_call") and part.function_call:
                function_parts.append(part)
            else:
                regular_parts.append(part)

        # Display function content
        for part in function_parts:
            if part.text:
                self.display_interface.display_function_content(part.text)

        # Display thought content
        for part in thought_parts:
            if part.text:
                self.display_interface.display_agent_thought(part.text)

        # Display regular content
        regular_text = "".join(part.text or "" for part in regular_parts)
        if regular_text.strip():
            self.display_interface.display_agent_response(regular_text, event.author)

        # Display usage metadata if available
        if hasattr(event, "usage_metadata") and event.usage_metadata:
            self.display_interface.display_usage_metadata(
                event.usage_metadata, model_name
            )

    def display_processed_event(
        self, processed_event: ProcessedAgentEvent, model_name: str = "Unknown"
    ) -> None:
        """
        Display a processed agent event using the configured display interface.

        Args:
            processed_event: The processed event to display
            model_name: The name of the model (for usage metadata display)
        """
        # Display function content
        for part in processed_event.function_parts:
            if part.text:
                self.display_interface.display_function_content(part.text)

        # Display thought content
        for part in processed_event.thought_parts:
            if part.text:
                self.display_interface.display_agent_thought(part.text)

        # Display regular content
        if processed_event.regular_text.strip():
            self.display_interface.display_agent_response(
                processed_event.regular_text, processed_event.author
            )

        # Display usage metadata if available
        if processed_event.usage_metadata:
            self.display_interface.display_usage_metadata(
                processed_event.usage_metadata, model_name
            )


class ConsoleEventDisplay:
    """Event display implementation for console/prompt-toolkit UI."""

    def __init__(self, console, cli=None, fallback_mode: bool = False):
        self.console = console
        self.cli = cli
        self.fallback_mode = fallback_mode

    def display_agent_response(self, text: str, author: str) -> None:
        if not self.fallback_mode and self.cli:
            self.cli.display_agent_response(self.console, text, author)
        else:
            self.console.print(f"🤖 {author} > {text}")

    def display_agent_thought(self, text: str) -> None:
        if not self.fallback_mode and self.cli:
            self.cli.display_agent_thought(self.console, text)
        # Note: fallback mode doesn't display thoughts

    def display_function_content(self, text: str) -> None:
        # Function content is typically handled by the agent response display
        self.console.print(f"🔧 Tool: {text}")

    def display_usage_metadata(self, usage_metadata: Any, model_name: str) -> None:
        # Console mode doesn't typically display usage metadata
        pass


class TUIEventDisplay:
    """Event display implementation for Textual UI."""

    def __init__(self, tui_app):
        self.tui_app = tui_app

    def display_agent_response(self, text: str, author: str) -> None:
        self.tui_app.add_agent_output(text, author)

    def display_agent_thought(self, text: str) -> None:
        # Use the add_thought method which is the correct TUI method
        self.tui_app.add_thought(text)

    def display_function_content(self, text: str) -> None:
        self.tui_app.add_output(text, author="Tool", rich_format=True, style="accent")

    def display_usage_metadata(self, usage_metadata: Any, model_name: str) -> None:
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0)
        completion_tokens = getattr(usage_metadata, "candidates_token_count", 0)
        total_tokens = getattr(usage_metadata, "total_token_count", 0)
        thinking_tokens = getattr(usage_metadata, "thoughts_token_count", 0) or 0

        self.tui_app.display_model_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            thinking_tokens=thinking_tokens,
            model_name=model_name,
        )
