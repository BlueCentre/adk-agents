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
from pydantic import BaseModel
from typing import Optional
import re
import sys
import time

import rich_click as click
from rich.console import Console
from prompt_toolkit.patch_stdout import patch_stdout

from google.genai import types
from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts import BaseArtifactService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session

from .utils import envs
from .utils.agent_loader import AgentLoader
from .utils.envs import load_dotenv_for_agent
from .utils.ui import get_cli_instance, get_textual_cli_instance
from .utils.ui_common import UITheme


class InputFile(BaseModel):
  state: dict[str, object]
  queries: list[str]


# This function is now replaced by the UI module functionality


async def run_input_file(
    app_name: str,
    user_id: str,
    root_agent: BaseAgent,
    artifact_service: BaseArtifactService,
    session_service: BaseSessionService,
    input_path: str,
) -> Session:
  runner = Runner(
      app_name=app_name,
      agent=root_agent,
      artifact_service=artifact_service,
      session_service=session_service,
  )
  # Initialize Rich Console
  console = Console()
  with open(input_path, 'r', encoding='utf-8') as f:
    input_file = InputFile.model_validate_json(f.read())
  input_file.state['_time'] = datetime.now()

  session = await session_service.create_session(
      app_name=app_name, user_id=user_id, state=input_file.state
  )
  console.print(f"[bold blue]Running from input file:[/bold blue] [blue]{input_path}[/blue]")
  for query in input_file.queries:
    console.print(f'[blue][user][/blue]: {query}')
    content = types.Content(role='user', parts=[types.Part(text=query)])
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=content
    ):
      if event.content and event.content.parts:
        if text := ''.join(part.text or '' for part in event.content.parts):
          console.print(f'[green][{event.author}][/green]: {text}')
  
  # Use graceful cleanup to handle MCP session cleanup errors
  from .utils.cleanup import close_runner_gracefully
  await close_runner_gracefully(runner)
  return session


async def run_interactively(
    root_agent: BaseAgent,
    artifact_service: BaseArtifactService,
    session: Session,
    session_service: BaseSessionService,
    ui_theme: Optional[str] = None,
) -> None:
  runner = Runner(
      app_name=session.app_name,
      agent=root_agent,
      artifact_service=artifact_service,
      session_service=session_service,
  )

  # Initialize basic console for fallback with scrollback-friendly settings
  console = Console(
      force_interactive=False,  # Disable animations that might interfere with scrollback
      soft_wrap=True,           # Enable soft wrapping to prevent cropping
      width=None,               # Auto-detect width to avoid fixed sizing issues
      height=None               # Auto-detect height to avoid fixed sizing issues
  )

  # Initialize enhanced CLI with theming
  try:
    cli = get_cli_instance(ui_theme)
    prompt_session = cli.create_enhanced_prompt_session(root_agent.name, session.id)
    fallback_mode = False
  except Exception as e:
    # Fallback to basic CLI if enhanced UI fails
    console.print(f"[warning]⚠️  Enhanced UI initialization failed: {str(e)}[/warning]")
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

  while True:
    try:
      if fallback_mode:
        query = await prompt_session.prompt_async('😜 user > ')
      else:
        with patch_stdout():
          query = await prompt_session.prompt_async('😎 user > ')
    except (EOFError, KeyboardInterrupt):
      # Handle Ctrl+D and Ctrl+C gracefully
      output_console = console if fallback_mode else (cli.console if cli else console)
      output_console.print("\n[warning]Goodbye! 👋[/warning]")
      break
    except Exception as e:
      # Handle other prompt-related errors gracefully
      output_console = console if fallback_mode else (cli.console if cli else console)
      output_console.print(f"\n[red]❌ Prompt error: {str(e)}[/red]")
      output_console.print("[yellow]💡 Try using a simpler terminal or check your environment.[/yellow]")
      output_console.print("[blue]Falling back to basic input mode...[/blue]")
      try:
        query = input('😜 user > ')
      except (EOFError, KeyboardInterrupt):
        output_console = console if fallback_mode else (cli.console if cli else console)
        output_console.print("\n[warning]Goodbye! 👋[/warning]")
        break

    if not query or not query.strip():
      continue
    if query.strip().lower() in ['exit', 'quit', 'bye']:
      output_console = console if fallback_mode else (cli.console if cli else console)
      output_console.print("[warning]Goodbye! 👋[/warning]")
      break

    # Handle special commands
    if query.strip().lower() == 'clear':
      output_console = console if fallback_mode else (cli.console if cli else console)
      output_console.clear()
      continue
    elif query.strip().lower() == 'help':
      if not fallback_mode and cli:
        cli.print_help()
      else:
        console.print("[blue]Available Commands:[/blue]")
        console.print("  • exit, quit, bye - Exit the CLI")
        console.print("  • clear - Clear the screen")
        console.print("  • help - Show this help message")
      continue
    elif query.strip().lower().startswith('theme') and not fallback_mode and cli:
      theme_cmd = query.strip().lower().split()
      if len(theme_cmd) == 1 or theme_cmd[1] == 'toggle':
        cli.toggle_theme()
        # Recreate prompt session with new theme
        prompt_session = cli.create_enhanced_prompt_session(root_agent.name, session.id)
      elif len(theme_cmd) == 2 and theme_cmd[1] in ['dark', 'light']:
        cli.set_theme(UITheme(theme_cmd[1]))
        # Recreate prompt session with new theme
        prompt_session = cli.create_enhanced_prompt_session(root_agent.name, session.id)
      continue

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(role='user', parts=[types.Part(text=query)]),
    ):
      if event.content and event.content.parts:
        if text := ''.join(part.text or '' for part in event.content.parts):
          # Filter out thought content to prevent duplication
          filtered_text, extracted_thoughts = _filter_thought_content(text)
          
          if filtered_text.strip():  # Only display if there's non-thought content
            if not fallback_mode and cli:
              panel = cli.format_agent_response(filtered_text, event.author)
              cli.console.print(panel)
            else:
              # Simple output for fallback mode
              console.print(f"[green]{event.author}[/green]: {filtered_text}")

          # Display agent thoughts in the thought pane if enabled
          if cli and hasattr(cli, 'agent_thought_enabled') and cli.agent_thought_enabled and extracted_thoughts:
            for thought in extracted_thoughts:
              cli.add_thought(thought)

  # Use graceful cleanup to handle MCP session cleanup errors
  from .utils.cleanup import close_runner_gracefully
  await close_runner_gracefully(runner)


def _filter_thought_content(text: str) -> tuple[str, list[str]]:
  """Filter out thought content patterns from agent responses and return both filtered text and extracted thoughts."""
  if not text or not text.strip():
    return text, []
    
  lines = text.split('\n')
  filtered_lines = []
  extracted_thoughts = []
  skip_section = False
  current_thought = []
  
  for i, line in enumerate(lines):
    line_lower = line.lower().strip()
    
    # Check for thought section markers - expand patterns based on agent's _is_thought_content
    thought_markers = [
      'thinking', 'approach', 'analytical', 'process', 'determining', 
      'navigating', 'finding', 'current time', 'my approach',
      # Add more patterns from the agent's _is_thought_content method
      'thinking through', 'my analytical process', 'providing the requested information'
    ]
    
    if line.startswith('**') and any(marker in line_lower for marker in thought_markers):
      skip_section = True
      current_thought = [line]  # Start collecting thought content
      continue
    
    # Check for end of thought section (empty line or new content)
    if skip_section and (not line.strip() or line.startswith('#') or 
                        line.startswith('The ') or line.startswith('I ') or
                        line.startswith('Here ') or line.startswith('Based on')):
      if current_thought:
        thought_text = '\n'.join(current_thought)
        extracted_thoughts.append(thought_text)
        current_thought = []
      if line.startswith('The ') or line.startswith('I ') or line.startswith('Here ') or line.startswith('Based on'):
        skip_section = False
        filtered_lines.append(line)
      continue
    
    # Skip lines that are part of thought content but collect them
    if skip_section:
      current_thought.append(line)
      continue
      
    # Check for standalone thought patterns - expand based on agent patterns
    standalone_patterns = [
      'okay, so the user wants', 'let me think about', 'my best bet is to',
      'first step is to', 'given my understanding', 'i recognize that',
      'i need to', 'let\'s see', 'good practice, always', 'it\'s important to',
      'essentially,', 'the logic is straightforward', 'i\'ll just', 'no need to',
      'i remember that', 'i already', 'therefore,'
    ]
    
    if any(pattern in line_lower for pattern in standalone_patterns):
      extracted_thoughts.append(line)
      continue
    
    # Keep the line if it's not thought content
    filtered_lines.append(line)
    
  # Add any remaining thought content if the section didn't end gracefully
  if current_thought:
    thought_text = '\n'.join(current_thought)
    extracted_thoughts.append(thought_text)
    
  return '\n'.join(filtered_lines), extracted_thoughts


# def _strip_rich_markup(text: str) -> str:
#   """Strip rich markup from a string."""
#   # This is a very basic stripping. For robust stripping, consider rich.text.Text.plain
#   # or a more comprehensive regex.
#   # Remove common rich tags like [], [bold], [green], etc.
#   return re.sub(r"\[/?\w+\s*=\s*[^]]+\]|\[/?\w+\]", "", text)


async def run_interactively_with_interruption(
    root_agent: BaseAgent,
    artifact_service: BaseArtifactService,
    session: Session,
    session_service: BaseSessionService,
    ui_theme: Optional[str] = None,
) -> None:
  """Run the agent interactively with interruption support using Textual UI."""

  # Create the Textual UI
  app_tui = get_textual_cli_instance(ui_theme)

  # Set agent info
  app_tui.agent_name = root_agent.name

  # Create runner
  runner = Runner(
      app_name=session.app_name,
      agent=root_agent,
      artifact_service=artifact_service,
      session_service=session_service,
  )

  # Store original agent console and replace it with a custom one that redirects to Textual UI
  original_console = getattr(root_agent, '_console', None)
  if original_console:
    # Create a custom console that intercepts agent thought output
    class TextualConsoleRedirect:
      def __init__(self, original_console, textual_ui):
        self.original_console = original_console
        self.textual_ui = textual_ui

      def print(self, *args, **kwargs):
        # Check if this is an agent thought panel
        if args and hasattr(args[0], 'title') and '🧠 Agent Thought' in str(args[0].title):
          # Extract the thought content and send to Textual UI
          if hasattr(args[0], 'renderable') and hasattr(args[0].renderable, 'plain'):
            thought_text = args[0].renderable.plain
            self.textual_ui.add_agent_thought(thought_text)
          elif hasattr(args[0], 'renderable'):
            # Fallback: convert to string
            thought_text = str(args[0].renderable)
            self.textual_ui.add_agent_thought(thought_text)
        else:
          # For non-thought output, pass through to original console
          self.original_console.print(*args, **kwargs)

      def __getattr__(self, name):
        # Delegate all other methods to the original console
        return getattr(self.original_console, name)

    # Replace the agent's console
    root_agent._console = TextualConsoleRedirect(original_console, app_tui)

  # Store original agent callbacks
  original_before_tool = getattr(root_agent, 'before_tool_callback', None)
  original_after_tool = getattr(root_agent, 'after_tool_callback', None)
  original_after_model = getattr(root_agent, 'after_model_callback', None)

  # Tool execution tracking
  tool_start_times = {}

  async def enhanced_before_tool(tool, args, tool_context, callback_context=None):
    """Enhanced before_tool callback that also sends events to Textual UI."""
    # Record start time for duration calculation
    tool_start_times[tool.name] = time.time()

    # Send tool start event to Textual UI
    app_tui.add_tool_event(tool.name, "start", args=args)

    # Call original callback if it exists
    if original_before_tool:
      return await original_before_tool(tool, args, tool_context, callback_context)
    return None

  async def enhanced_after_tool(tool, tool_response, callback_context=None, args=None, tool_context=None):
    """Enhanced after_tool callback that also sends events to Textual UI."""
    # Calculate duration
    start_time = tool_start_times.get(tool.name, time.time())
    duration = time.time() - start_time

    # Determine if this was an error
    is_error = False
    if isinstance(tool_response, dict):
      is_error = tool_response.get("status") == "error" or tool_response.get("error") is not None

    # Send tool finish/error event to Textual UI
    if is_error:
      app_tui.add_tool_event(tool.name, "error", result=tool_response, duration=duration)
    else:
      app_tui.add_tool_event(tool.name, "finish", result=tool_response, duration=duration)

    # Call original callback if it exists
    if original_after_tool:
      return await original_after_tool(tool, tool_response, callback_context, args, tool_context)
    return None

  # Replace agent callbacks with enhanced versions (if the agent supports it)
  if hasattr(root_agent, 'before_tool_callback'):
    root_agent.before_tool_callback = enhanced_before_tool
  if hasattr(root_agent, 'after_tool_callback'):
    root_agent.after_tool_callback = enhanced_after_tool

  async def handle_user_input(user_input: str):
    """Handle user input by running the agent and processing output."""
    try:
      app_tui.add_output(f"🔄 Processing: {user_input}", author="User", rich_format=True, style="accent")

      # Create content for the agent
      content = types.Content(role='user', parts=[types.Part(text=user_input)])

      # Run the agent and process events
      async for event in runner.run_async(
          user_id=session.user_id,
          session_id=session.id,
          new_message=content
      ):
        if event.content and event.content.parts:
          if text := ''.join(part.text or '' for part in event.content.parts):
            # Filter out thought content to prevent duplication
            filtered_text, extracted_thoughts = _filter_thought_content(text)

            # Display agent thoughts in the thought pane if enabled (fallback approach)
            if app_tui.agent_thought_enabled and extracted_thoughts:
              for thought in extracted_thoughts:
                app_tui.add_agent_thought(thought)

            # Display main agent output in the output pane
            if filtered_text.strip():  # Only display if there's non-thought content
              app_tui.add_agent_output(filtered_text, event.author)

        # Handle token usage from LLM responses
        if hasattr(event, 'usage_metadata') and event.usage_metadata:
          usage = event.usage_metadata
          prompt_tokens = getattr(usage, 'prompt_token_count', 0)
          completion_tokens = getattr(usage, 'candidates_token_count', 0)
          total_tokens = getattr(usage, 'total_token_count', 0)
          thinking_tokens = getattr(usage, 'thoughts_token_count', 0) or 0

          # Update token usage in the UI
          app_tui.display_model_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            thinking_tokens=thinking_tokens,
            model_name=getattr(root_agent, 'model', 'Unknown')
          )

    except Exception as e:
      app_tui.add_output(f"❌ Error: {str(e)}", author="System", rich_format=True, style="error")

  async def interrupt_agent():
    """Handle agent interruption."""
    app_tui.add_output("⏹️ Agent interruption requested", author="System", rich_format=True, style="warning")

  # Register callbacks with the Textual app
  app_tui.register_input_callback(handle_user_input)
  app_tui.register_interrupt_callback(interrupt_agent)

  # Display welcome message through the Textual app
  app_tui.display_agent_welcome(root_agent.name, root_agent.description, getattr(root_agent, 'tools', []))

  # Run the Textual application
  await app_tui.run_async()

  # Restore original console and callbacks
  if original_console:
    root_agent._console = original_console
  if hasattr(root_agent, 'before_tool_callback'):
    root_agent.before_tool_callback = original_before_tool
  if hasattr(root_agent, 'after_tool_callback'):
    root_agent.after_tool_callback = original_after_tool

  # Use graceful cleanup to handle MCP session cleanup errors
  from .utils.cleanup import close_runner_gracefully
  await close_runner_gracefully(runner)


# async def _process_agent_responses(agent_gen, cli):
#   """Process events from the agent generator and display them in the CLI."""
#   async for event in agent_gen:
#     if event.content and event.content.parts:
#       if text := ''.join(part.text or '' for part in event.content.parts):
#         # Filter out thought content to prevent duplication
#         filtered_text, extracted_thoughts = _filter_thought_content(text)
        
#         # Display agent thoughts in the thought pane if enabled
#         if cli.agent_thought_enabled and extracted_thoughts:
#           for thought in extracted_thoughts:
#             cli.add_thought(thought)
            
#         # Display main agent output in the output pane
#         if filtered_text.strip():  # Only display if there's non-thought content
#           cli.add_agent_output(filtered_text, event.author)


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
  # Load environment variables specific to the agent
  load_dotenv_for_agent(agent_module_name)

  if input_file and saved_session_file:
    print("Error: Cannot specify both --input-file and --saved-session.")
    sys.exit(1)

  # Use AgentLoader instance to load the agent
  agent_loader = AgentLoader()
  root_agent = agent_loader.load_agent(agent_module_name)
  
  artifact_service = InMemoryArtifactService()
  session_service = InMemorySessionService()

  if input_file:
    await run_input_file(
        app_name=agent_module_name,
        user_id="default-user",
        root_agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        input_path=input_file,
    )
  elif saved_session_file:
    session = await session_service.get_session(session_id=saved_session_file, app_name=agent_module_name)
    if not session:
      print(f"Error: Session with ID {saved_session_file} not found.")
      sys.exit(1)
    await run_interactively(
        root_agent=root_agent,
        artifact_service=artifact_service,
        session=session,
        session_service=session_service,
        ui_theme=ui_theme,
    )
  else:
    session = await session_service.create_session(app_name=agent_module_name, user_id="default-user")
    if tui:
      await run_interactively_with_interruption(
          root_agent=root_agent,
          artifact_service=artifact_service,
          session=session,
          session_service=session_service,
          ui_theme=ui_theme,
      )
    else:
      await run_interactively(
          root_agent=root_agent,
          artifact_service=artifact_service,
          session=session,
          session_service=session_service,
          ui_theme=ui_theme,
      )

  if save_session:
    session_id = session_id or input('📝 Session ID to save: ')
    session_path = (
        # f'{agent_parent_dir}/{agent_folder_name}/{session_id}.session.json'
        f'{session_id}.session.json'
    )

    # Fetch the session again to get all the details.
    session = await session_service.get_session(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    with open(session_path, 'w', encoding='utf-8') as f:
      f.write(session.model_dump_json(indent=2, exclude_none=True))

    print('Session saved to', session_path)


# @click.group()
# def cli():
#   pass


# @cli.command()
# @click.option('--agent', '-a', required=True, help='Agent module name (e.g., agents.devops)')
# @click.option('--input-file', '-i', help='Input file with queries')
# @click.option('--saved-session', '-s', help='Saved session file to resume')
# @click.option('--save-session', is_flag=True, help='Save session on exit')
# @click.option('--session-id', help='Session ID for saving')
# @click.option('--theme', type=click.Choice(['light', 'dark']), help='UI theme')
# @click.option('--tui', is_flag=True, help='Use Textual CLI with persistent input pane')
# def main(agent: str, input_file: Optional[str], saved_session: Optional[str], 
#          save_session: bool, session_id: Optional[str], theme: Optional[str], tui: bool):
#   # Load environment variables specific to the agent
#   load_dotenv_for_agent(agent)

#   if input_file and saved_session:
#     print("Error: Cannot specify both --input-file and --saved-session.")
#     sys.exit(1)

#   # Use AgentLoader instance to load the agent
#   agent_loader = AgentLoader()
#   root_agent = agent_loader.load_agent(agent)
  
#   artifact_service = InMemoryArtifactService()
#   session_service = InMemorySessionService()

#   if input_file:
#     asyncio.run(
#         run_input_file(
#             app_name=agent,
#             user_id="default-user",
#             root_agent=root_agent,
#             artifact_service=artifact_service,
#             session_service=session_service,
#             input_path=input_file,
#         )
#     )
#   elif saved_session:
#     session = asyncio.run(session_service.get_session(session_id=saved_session, app_name=agent))
#     if not session:
#       print(f"Error: Session with ID {saved_session} not found.")
#       sys.exit(1)
#     asyncio.run(
#         run_interactively(
#             root_agent=root_agent,
#             artifact_service=artifact_service,
#             session=session,
#             session_service=session_service,
#             ui_theme=theme,
#         )
#     )
#   else:
#     session = asyncio.run(session_service.create_session(app_name=agent, user_id="default-user"))
#     if tui:
#       asyncio.run(
#           run_interactively_with_interruption(
#               root_agent=root_agent,
#               artifact_service=artifact_service,
#               session=session,
#               session_service=session_service,
#               ui_theme=theme,
#           )
#       )
#     else:
#       asyncio.run(
#           run_interactively(
#               root_agent=root_agent,
#               artifact_service=artifact_service,
#               session=session,
#               session_service=session_service,
#               ui_theme=theme,
#           )
#       )

#   if save_session:
#     # This part remains a placeholder as InMemorySessionService does not support direct file saving.
#     # Future implementations might use a different SessionService or a custom saving mechanism.
#     print("Session saving is not implemented for InMemorySessionService.")
#     print("To enable session saving, configure a persistent session service (e.g., database or Vertex AI).")


# if __name__ == '__main__':
#   main()
