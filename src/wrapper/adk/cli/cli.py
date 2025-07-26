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
from datetime import datetime
import logging
from pathlib import Path
import time

from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import BaseArtifactService, InMemoryArtifactService
from google.adk.auth.credential_service.base_credential_service import (
    BaseCredentialService,
)
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.genai import types
from prompt_toolkit.patch_stdout import patch_stdout
from pydantic import BaseModel
from rich.console import Console
import rich_click as click

from .utils import envs  # Modified to use our packaged path
from .utils.agent_loader import AgentLoader  # Modified to use our packaged path
from .utils.command_handling import (  # Import for refactoring
    CommandHandler,
    CommandResult,
    ConsoleCommandDisplay,
    ConsoleThemeHandler,
    TUICommandDisplay,
    TUIThemeHandler,
)
from .utils.error_handling import (  # Import for refactoring
    ConsoleErrorDisplay,
    ErrorHandler,
    TUIErrorDisplay,
)
from .utils.event_processing import (  # Import for refactoring
    AgentEventProcessor,
    ConsoleEventDisplay,
    TUIEventDisplay,
)
from .utils.runner_factory import RunnerFactory  # Import for refactoring
from .utils.ui import get_cli_instance, get_textual_cli_instance

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
    runner = RunnerFactory.create_runner_from_app_name(
        app_name=app_name,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )
    with Path(input_path).open(encoding="utf-8") as f:
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
    ui_theme: str | None = None,
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
        console.print(f"[warning]⚠️ Enhanced UI initialization failed: {e!s}[/warning]")
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

    runner = RunnerFactory.create_runner(
        session=session,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )

    # Create error handler for this UI mode
    error_display = ConsoleErrorDisplay(console, fallback_mode, cli)
    error_handler = ErrorHandler(error_display)

    # Create event processor for this UI mode
    event_display = ConsoleEventDisplay(console, cli=cli, fallback_mode=fallback_mode)
    event_processor = AgentEventProcessor(event_display)

    # Create command handler for this UI mode
    command_display = ConsoleCommandDisplay(console, cli=cli, fallback_mode=fallback_mode)

    def recreate_prompt_session():
        """Recreate the prompt session with the new theme."""
        nonlocal prompt_session
        if cli:
            prompt_session = cli.create_enhanced_prompt_session(root_agent.name, session.id)

    theme_handler = ConsoleThemeHandler(cli, recreate_prompt_session)
    command_handler = CommandHandler(command_display, theme_handler)

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
            output_console = console if fallback_mode else (cli.console if cli else console)
            output_console.print("\n👋 [warning]Goodbye![/warning]")
            break
        except Exception as e:
            # Handle other prompt-related errors gracefully
            output_console = console if fallback_mode else (cli.console if cli else console)
            output_console.print(f"\n[red]❌ Prompt error: {e!s}[/red]")
            output_console.print(
                "[yellow]💡 Try using a simpler terminal or check your environment.[/yellow]"
            )
            output_console.print("[blue]Falling back to basic input mode...[/blue]")
            try:
                query = input("😜 user > ")
            except (EOFError, KeyboardInterrupt):
                output_console = console if fallback_mode else (cli.console if cli else console)
                output_console.print("\n👋 [warning]Goodbye![/warning]")
                break

        # Handle special independent commands
        if not query or not query.strip():
            continue

        # Use CommandHandler to process built-in commands
        command_result = command_handler.process_command(query)
        if command_result == CommandResult.EXIT_REQUESTED:
            break
        if command_result == CommandResult.HANDLED:
            continue
        # If NOT_HANDLED, continue to agent processing

        # Run the agent and process events with error handling
        try:
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
                # Use AgentEventProcessor for event handling
                event_processor.process_event(
                    event, model_name=getattr(root_agent, "model", "Unknown")
                )
        except ValueError as e:
            # Use ErrorHandler for missing function errors
            if not error_handler.handle_missing_function_error(e):
                raise
        except Exception as e:
            # Use ErrorHandler for general errors
            error_handler.handle_general_error(e)

    try:
        await runner.close()
    except (asyncio.CancelledError, asyncio.TimeoutError) as e:
        # Handle asyncio-specific cleanup errors gracefully
        print(f"Warning: Error during MCP session cleanup for stdio_session: {e}")
        # This is expected during cleanup, don't raise
    except Exception as e:
        # Use ErrorHandler for other MCP cleanup errors
        if ErrorHandler.handle_mcp_cleanup_error(e):
            # Error was handled, don't raise
            return
        # Unknown error, re-raise
        raise


async def run_interactively_with_tui(
    root_agent: LlmAgent,
    artifact_service: BaseArtifactService,
    session: Session,
    session_service: BaseSessionService,
    credential_service: BaseCredentialService,
    ui_theme: str | None = None,
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

    # Create error handler for TUI mode
    error_display = TUIErrorDisplay(app_tui)
    error_handler = ErrorHandler(error_display)

    # Create event processor for TUI mode
    event_display = TUIEventDisplay(app_tui)
    event_processor = AgentEventProcessor(event_display)

    # Create command handler for TUI mode
    command_display = TUICommandDisplay(app_tui)
    theme_handler = TUIThemeHandler(app_tui)
    command_handler = CommandHandler(command_display, theme_handler)

    # App TUI handlers for user input and interruption
    async def handle_user_input(user_input: str):
        """Handle user input by running the agent and processing output."""
        try:
            # Use CommandHandler to process built-in commands first
            command_result = command_handler.process_command(user_input)
            if command_result == CommandResult.EXIT_REQUESTED:
                return  # TUI will exit via command_handler
            if command_result == CommandResult.HANDLED:
                return  # Command was handled, don't process further

            # Display the user input in the UI (only for agent queries)
            app_tui.add_output(
                f"🔄 Processing: {user_input}",
                author="User",
                rich_format=True,
                style="accent",
            )

            # Create content for the agent
            content = types.Content(role="user", parts=[types.Part(text=user_input)])

            # Run the agent and process events with error handling
            try:
                async for event in runner.run_async(
                    user_id=session.user_id, session_id=session.id, new_message=content
                ):
                    # Use AgentEventProcessor for event handling
                    event_processor.process_event(
                        event, model_name=getattr(root_agent, "model", "Unknown")
                    )
            except ValueError as e:
                # Use ErrorHandler for missing function errors
                if not error_handler.handle_missing_function_error(e):
                    raise
            except Exception as e:
                # Use ErrorHandler for general errors
                error_handler.handle_general_error(e)
        except Exception as e:
            app_tui.add_output(f"❌ Error: {e!s}", author="System", rich_format=True, style="error")

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
    runner = RunnerFactory.create_runner(
        session=session,
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

        # Call original callback(s) if they exist
        if original_before_tool:
            # Handle both single callback and list of callbacks
            if isinstance(original_before_tool, list):
                # Execute all callbacks in the list
                for callback in original_before_tool:
                    if callback:
                        result = callback(tool, args, tool_context, callback_context)
                        if result is not None and hasattr(result, "__await__"):
                            result = await result
                        # Return the first non-None result from the callback chain
                        if result is not None:
                            return result
            else:
                # Single callback
                result = original_before_tool(tool, args, tool_context, callback_context)
                if result is not None and hasattr(result, "__await__"):
                    return await result
                return result
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
                tool_response.get("status") == "error" or tool_response.get("error") is not None
            )

        # Send tool finish/error event to Textual UI
        if is_error:
            app_tui.add_tool_event(tool.name, "error", result=tool_response, duration=duration)
        else:
            app_tui.add_tool_event(tool.name, "finish", result=tool_response, duration=duration)

        # Call original callback(s) if they exist
        if original_after_tool:
            # Handle both single callback and list of callbacks
            if isinstance(original_after_tool, list):
                # Execute all callbacks in the list
                for callback in original_after_tool:
                    if callback:
                        result = callback(tool, tool_response, callback_context, args, tool_context)
                        if result is not None and hasattr(result, "__await__"):
                            result = await result
                        # Return the first non-None result from the callback chain
                        if result is not None:
                            return result
            else:
                # Single callback
                result = original_after_tool(
                    tool, tool_response, callback_context, args, tool_context
                )
                if result is not None and hasattr(result, "__await__"):
                    return await result
                return result
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
    except (asyncio.CancelledError, asyncio.TimeoutError) as e:
        # Handle asyncio-specific cleanup errors gracefully
        print(f"Warning: Error during MCP session cleanup for stdio_session: {e}")
        # This is expected during cleanup, don't raise
    except Exception as e:
        # Use ErrorHandler for other MCP cleanup errors
        if ErrorHandler.handle_mcp_cleanup_error(e):
            # Error was handled, don't raise
            return
        # Unknown error, re-raise
        raise


async def run_cli(
    *,
    agent_module_name: str,
    input_file: str | None = None,
    saved_session_file: str | None = None,
    save_session: bool = False,
    session_id: str | None = None,
    ui_theme: str | None = None,
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
    session = await session_service.create_session(app_name=agent_module_name, user_id=user_id)
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
        with Path(saved_session_file).open(encoding="utf-8") as f:
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
        with Path(session_path).open("w", encoding="utf-8") as f:
            f.write(session.model_dump_json(indent=2, exclude_none=True))

        print("Session saved to", session_path)
