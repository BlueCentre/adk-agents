# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

import rich_click as click
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import BaseArtifactService, InMemoryArtifactService
from google.adk.auth.credential_service.base_credential_service import BaseCredentialService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.genai import types
from prompt_toolkit.patch_stdout import patch_stdout
from pydantic import BaseModel
from rich.console import Console

from .utils import envs  # Modified to use our packaged path
from .utils.agent_loader import AgentLoader  # Modified to use our packaged path
from .utils.ui import get_cli_instance, get_textual_cli_instance
from .utils.ui_common import UITheme

logger = logging.getLogger(__name__)


class InputFile(BaseModel):
    state: dict[str, object]
    queries: list[str]


async def run_input_file(
    app_name: str,
    user_id: str,
    root_agent: LlmAgent,
    artifact_service: BaseArtifactService,
    session_service: BaseSessionService,
    credential_service: BaseCredentialService,
    input_path: str,
) -> Session:
    runner = Runner(
        app_name=app_name,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )
    with open(input_path, "r", encoding="utf-8") as f:
        input_file = InputFile.model_validate_json(f.read())
    input_file.state["_time"] = datetime.now()

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state=input_file.state
    )
    for query in input_file.queries:
        click.echo(f"[user]: {query}")
        content = types.Content(role="user", parts=[types.Part(text=query)])
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=content
        ):
            if event.content and event.content.parts:
                if text := "".join(part.text or "" for part in event.content.parts):
                    click.echo(f"[{event.author}]: {text}")
    return session


async def run_interactively(
    root_agent: LlmAgent,
    artifact_service: BaseArtifactService,
    session: Session,
    session_service: BaseSessionService,
    credential_service: BaseCredentialService,
    ui_theme: Optional[str] = None,
) -> None:
    """
    Run the agent interactively with fallback to basic CLI mode.
    This function is used when the user wants to run the agent interactively
    in a terminal with a prompt-toolkit based UI.
    It supports:
    - User input with a prompt
    - Agent thought and response display in a panel
    - Theme switching
    - Basic CLI mode fallback
    - Error handling
    - Token usage tracking
    - Tool execution tracking
    - Agent interruption support
    - Session state management
    Ref: https://google.github.io/adk-docs/runtime/#step-by-step-breakdown
    """

    # Initialize basic console for fallback with scrollback-friendly settings
    console = Console(
        force_interactive=False,  # Disable animations that might interfere with scrollback
        soft_wrap=True,  # Enable soft wrapping to prevent cropping
        width=None,  # Auto-detect width to avoid fixed sizing issues
        height=None,  # Auto-detect height to avoid fixed sizing issues
    )

    # Initialize enhanced CLI with theming
    try:
        cli = get_cli_instance(ui_theme)
        prompt_session = cli.create_enhanced_prompt_session(root_agent.name, session.id)
        fallback_mode = False
    except Exception as e:
        # Fallback to basic CLI if enhanced UI fails
        console.print(
            f"[warning]⚠️ Enhanced UI initialization failed: {str(e)}[/warning]"
        )
        console.print("[info]Falling back to basic CLI mode...[/info]")
        # Create a minimal prompt session
        from prompt_toolkit import PromptSession

        prompt_session = PromptSession()
        cli = None
        fallback_mode = True

    # Welcome message with usage tips
    if not fallback_mode and cli:
        cli.print_welcome_message(root_agent.name)
    else:
        console.print(f"🚀 Starting interactive session with agent {root_agent.name}")
        console.print("Enhanced UI features are disabled. Basic CLI mode active.")

    runner = Runner(
        app_name=session.app_name,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )

    while True:
        # Display the user input prompt
        try:
            if fallback_mode:
                query = await prompt_session.prompt_async("😜 user > ")
            else:
                with patch_stdout():
                    query = await prompt_session.prompt_async("😎 user > ")
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+D and Ctrl+C gracefully
            output_console = (
                console if fallback_mode else (cli.console if cli else console)
            )
            output_console.print("\n👋 [warning]Goodbye![/warning]")
            break
        except Exception as e:
            # Handle other prompt-related errors gracefully
            output_console = (
                console if fallback_mode else (cli.console if cli else console)
            )
            output_console.print(f"\n[red]❌ Prompt error: {str(e)}[/red]")
            output_console.print(
                "[yellow]💡 Try using a simpler terminal or check your environment.[/yellow]"
            )
            output_console.print("[blue]Falling back to basic input mode...[/blue]")
            try:
                query = input("😜 user > ")
            except (EOFError, KeyboardInterrupt):
                output_console = (
                    console if fallback_mode else (cli.console if cli else console)
                )
                output_console.print("\n👋 [warning]Goodbye![/warning]")
                break

        # Handle special independent commands
        if not query or not query.strip():
            continue
        if query.strip().lower() in ["exit", "quit", "bye"]:
            output_console = (
                console if fallback_mode else (cli.console if cli else console)
            )
            output_console.print("👋 [warning]Goodbye![/warning]")
            break
        # Handle special mutually exclusive commands
        if query.strip().lower() == "clear":
            output_console = (
                console if fallback_mode else (cli.console if cli else console)
            )
            output_console.clear()
            continue
        elif query.strip().lower() == "help":
            if not fallback_mode and cli:
                cli.print_help()
            else:
                console.print("[blue]Available Commands:[/blue]")
                console.print("  • exit, quit, bye - Exit the CLI")
                console.print("  • clear - Clear the screen")
                console.print("  • help - Show this help message")
            continue
        elif query.strip().lower().startswith("theme") and not fallback_mode and cli:
            theme_cmd = query.strip().lower().split()
            if len(theme_cmd) == 1 or theme_cmd[1] == "toggle":
                cli.toggle_theme()
                # Recreate prompt session with new theme
                prompt_session = cli.create_enhanced_prompt_session(
                    root_agent.name, session.id
                )
            elif len(theme_cmd) == 2 and theme_cmd[1] in ["dark", "light"]:
                cli.set_theme(UITheme(theme_cmd[1]))
                # Recreate prompt session with new theme
                prompt_session = cli.create_enhanced_prompt_session(
                    root_agent.name, session.id
                )
            continue

        # Run the agent and process events
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(parts=[types.Part(text=query)], role="user"),
            # run_config=types.RunConfig(
            #     max_tokens=1000,
            #     temperature=0.5,
            #     top_p=0.9,
            #     top_k=40,
            #     frequency_penalty=0.0,
            # ),
        ):
            if event.content and event.content.parts:
                regular_parts = []
                thought_parts = []

                # Separate agent thought and response content from parts
                for part in event.content.parts:
                    if hasattr(part, "thought") and part.thought:
                        thought_parts.append(part)
                    else:
                        regular_parts.append(part)

                # Handle thought content
                # if cli and hasattr(cli, "agent_thought_enabled") and thought_parts:
                if cli and thought_parts:
                    for part in thought_parts:
                        if part.text:
                            # cli.add_agent_thought(part.text)
                            cli.display_agent_thought(console, part.text)

                # Handle regular content
                if regular_text := "".join(part.text or "" for part in regular_parts):
                    if regular_text.strip():
                        if not fallback_mode and cli:
                            # cli.add_agent_output(regular_text, event.author)
                            cli.display_agent_response(console, regular_text, event.author)
                        else:
                            # Simple output for fallback mode
                            console.print(
                                f"🤖 {event.author} > {regular_text}"
                            )

    try:
        await runner.close()
    except (asyncio.CancelledError, Exception) as e:
        # Handle MCP client library cleanup errors gracefully
        # These errors are harmless but occur due to async context mismatches
        # in the MCP client library during cleanup
        error_msg = str(e)
        exception_str = str(type(e).__name__)
        
        # Check if this is a known MCP cleanup error
        is_mcp_cleanup_error = any([
            "Attempted to exit cancel scope in a different task" in error_msg,
            "stdio_client" in error_msg,
            "MCP session cleanup" in error_msg,
            "CancelledError" in error_msg,
            "CancelledError" in exception_str,
            "cancel scope" in error_msg.lower(),
            isinstance(e, asyncio.CancelledError)
        ])
        
        if is_mcp_cleanup_error:
            logger.warning(f"MCP cleanup completed with expected async context warnings: {error_msg}")
        else:
            # Re-raise unexpected errors
            raise


async def run_interactively_with_tui(
    root_agent: LlmAgent,
    artifact_service: BaseArtifactService,
    session: Session,
    session_service: BaseSessionService,
    credential_service: BaseCredentialService,
    ui_theme: Optional[str] = None,
) -> None:
    """Run the agent interactively with interruption support using Textual UI."""

    # Create the Textual UI
    app_tui = get_textual_cli_instance(ui_theme)

    # Set agent info
    app_tui.agent_name = root_agent.name

    # Display welcome message through the Textual app
    app_tui.display_agent_welcome(
        root_agent.name, root_agent.description, getattr(root_agent, "tools", [])
    )

    # App TUI handlers for user input and interruption
    async def handle_user_input(user_input: str):
        """Handle user input by running the agent and processing output."""
        try:
            app_tui.add_output(
                f"🔄 Processing: {user_input}",
                author="User",
                rich_format=True,
                style="accent",
            )

            # Create content for the agent
            content = types.Content(role="user", parts=[types.Part(text=user_input)])

            # Run the agent and process events
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=content
            ):
                if event.content and event.content.parts:
                    # Separate thought and non-thought content
                    regular_parts = []
                    thought_parts = []

                    for part in event.content.parts:
                        if hasattr(part, "thought") and part.thought:
                            thought_parts.append(part)
                        else:
                            regular_parts.append(part)

                    # Handle thought content
                    if app_tui.agent_thought_enabled and thought_parts:
                        for part in thought_parts:
                            if part.text:
                                app_tui.add_agent_thought(part.text)

                    # Handle regular content
                    if regular_text := "".join(
                        part.text or "" for part in regular_parts
                    ):
                        if regular_text.strip():
                            app_tui.add_agent_output(regular_text, event.author)

                # Handle token usage from LLM responses
                if hasattr(event, "usage_metadata") and event.usage_metadata:
                    usage = event.usage_metadata
                    prompt_tokens = getattr(usage, "prompt_token_count", 0)
                    completion_tokens = getattr(usage, "candidates_token_count", 0)
                    total_tokens = getattr(usage, "total_token_count", 0)
                    thinking_tokens = getattr(usage, "thoughts_token_count", 0) or 0

                    # Update token usage in the UI
                    app_tui.display_model_usage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        thinking_tokens=thinking_tokens,
                        model_name=getattr(root_agent, "model", "Unknown"),
                    )

        except Exception as e:
            app_tui.add_output(
                f"❌ Error: {str(e)}", author="System", rich_format=True, style="error"
            )

    async def interrupt_agent():
        """Handle agent interruption."""
        app_tui.add_output(
            "⏹️ Agent interruption requested",
            author="System",
            rich_format=True,
            style="warning",
        )

    # Register callbacks with the Textual app
    app_tui.register_input_callback(handle_user_input)
    app_tui.register_interrupt_callback(interrupt_agent)

    # Create runner
    runner = Runner(
        app_name=session.app_name,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )

    # Tool execution tracking
    tool_start_times = {}

    # Store original agent callbacks
    original_before_tool = getattr(root_agent, "before_tool_callback", None)
    original_after_tool = getattr(root_agent, "after_tool_callback", None)
    # original_after_model = getattr(root_agent, 'after_model_callback', None)

    async def enhanced_before_tool(tool, args, tool_context, callback_context=None):
        """Enhanced before_tool callback that also sends events to Textual UI."""
        # Record start time for duration calculation
        tool_start_times[tool.name] = time.time()

        # Send tool start event to Textual UI
        app_tui.add_tool_event(tool.name, "start", args=args)

        # Call original callback if it exists
        if original_before_tool:
            return await original_before_tool(
                tool, args, tool_context, callback_context
            )
        return None

    async def enhanced_after_tool(
        tool, tool_response, callback_context=None, args=None, tool_context=None
    ):
        """Enhanced after_tool callback that also sends events to Textual UI."""
        # Calculate duration
        start_time = tool_start_times.get(tool.name, time.time())
        duration = time.time() - start_time

        # Determine if this was an error
        is_error = False
        if isinstance(tool_response, dict):
            is_error = (
                tool_response.get("status") == "error"
                or tool_response.get("error") is not None
            )

        # Send tool finish/error event to Textual UI
        if is_error:
            app_tui.add_tool_event(
                tool.name, "error", result=tool_response, duration=duration
            )
        else:
            app_tui.add_tool_event(
                tool.name, "finish", result=tool_response, duration=duration
            )

        # Call original callback if it exists
        if original_after_tool:
            return await original_after_tool(
                tool, tool_response, callback_context, args, tool_context
            )
        return None

    # Replace agent callbacks with enhanced versions (if the agent supports it)
    if hasattr(root_agent, "before_tool_callback"):
        root_agent.before_tool_callback = enhanced_before_tool
    if hasattr(root_agent, "after_tool_callback"):
        root_agent.after_tool_callback = enhanced_after_tool

    # Run the Textual application
    await app_tui.run_async()

    # Restore original console and callbacks
    # if original_console:
    #   root_agent._console = original_console
    if hasattr(root_agent, "before_tool_callback"):
        root_agent.before_tool_callback = original_before_tool
    if hasattr(root_agent, "after_tool_callback"):
        root_agent.after_tool_callback = original_after_tool

    try:
        await runner.close()
    except (asyncio.CancelledError, Exception) as e:
        # Handle MCP client library cleanup errors gracefully
        # These errors are harmless but occur due to async context mismatches
        # in the MCP client library during cleanup
        error_msg = str(e)
        exception_str = str(type(e).__name__)
        
        # Check if this is a known MCP cleanup error
        is_mcp_cleanup_error = any([
            "Attempted to exit cancel scope in a different task" in error_msg,
            "stdio_client" in error_msg,
            "MCP session cleanup" in error_msg,
            "CancelledError" in error_msg,
            "CancelledError" in exception_str,
            "cancel scope" in error_msg.lower(),
            isinstance(e, asyncio.CancelledError)
        ])
        
        if is_mcp_cleanup_error:
            logger.warning(f"MCP cleanup completed with expected async context warnings: {error_msg}")
        else:
            # Re-raise unexpected errors
            raise


async def run_cli(
    *,
    agent_module_name: str,
    input_file: Optional[str] = None,
    saved_session_file: Optional[str] = None,
    save_session: bool = False,
    session_id: Optional[str] = None,
    ui_theme: Optional[str] = None,
    tui: bool = False,
) -> None:
    """Runs an interactive CLI for a certain agent.

    Args:
      agent_module_name: str, the module path to the agent, e.g. 'agents.devops'
      input_file: Optional[str], the absolute path to the json file that contains
        the initial session state and user queries, exclusive with
        saved_session_file.
      saved_session_file: Optional[str], the absolute path to the json file that
        contains a previously saved session, exclusive with input_file.
      save_session: bool, whether to save the session on exit.
      session_id: Optional[str], the session ID to save the session to on exit.
      ui_theme: Optional[str], the UI theme to use ('light' or 'dark').
        If not provided, auto-detects from environment.
      tui: bool, whether to use the Textual CLI with persistent
        input and agent interruption capabilities.
    """

    artifact_service = InMemoryArtifactService()
    session_service = InMemorySessionService()
    credential_service = InMemoryCredentialService()

    user_id = "test_user"
    session = await session_service.create_session(
        app_name=agent_module_name, user_id=user_id
    )
    # Use AgentLoader instance to load the agent
    agent_loader = AgentLoader()
    root_agent = agent_loader.load_agent(agent_module_name)
    # Load environment variables specific to the agent
    envs.load_dotenv_for_agent(agent_module_name)
    if input_file:
        session = await run_input_file(
            app_name=agent_module_name,
            user_id=user_id,
            root_agent=root_agent,
            artifact_service=artifact_service,
            session_service=session_service,
            credential_service=credential_service,
            input_path=input_file,
        )
    elif saved_session_file:
        with open(saved_session_file, "r", encoding="utf-8") as f:
            loaded_session = Session.model_validate_json(f.read())

        if loaded_session:
            for event in loaded_session.events:
                await session_service.append_event(session, event)
                content = event.content
                if not content or not content.parts or not content.parts[0].text:
                    continue
                if event.author == "user":
                    click.echo(f"[user]: {content.parts[0].text}")
                else:
                    click.echo(f"[{event.author}]: {content.parts[0].text}")

        await run_interactively(
            root_agent,
            artifact_service,
            session,
            session_service,
            credential_service,
        )
    else:
        click.echo(f"Running agent {root_agent.name}, type exit to exit.")
        if tui:
            await run_interactively_with_tui(
                root_agent=root_agent,
                artifact_service=artifact_service,
                session=session,
                session_service=session_service,
                credential_service=credential_service,
                ui_theme=ui_theme,
            )
        else:
            await run_interactively(
                root_agent=root_agent,
                artifact_service=artifact_service,
                session=session,
                session_service=session_service,
                credential_service=credential_service,
                ui_theme=ui_theme,
            )

    if save_session:
        session_id = session_id or input("Session ID to save: ")
        session_path = (
            # f'{agent_parent_dir}/{agent_folder_name}/{session_id}.session.json'
            f"{session_id}.session.json"
        )

        # Fetch the session again to get all the details.
        session = await session_service.get_session(
            app_name=session.app_name,
            user_id=session.user_id,
            session_id=session.id,
        )
        with open(session_path, "w", encoding="utf-8") as f:
            f.write(session.model_dump_json(indent=2, exclude_none=True))

        print("Session saved to", session_path)
