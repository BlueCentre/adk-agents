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
from typing import Optional

import rich_click as click
from rich.console import Console
# from rich.markdown import Markdown
# from rich.panel import Panel
from prompt_toolkit.patch_stdout import patch_stdout
from contextlib import redirect_stdout, redirect_stderr

from google.genai import types
from pydantic import BaseModel

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts import BaseArtifactService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from .utils import envs
from .utils.agent_loader import AgentLoader
from .utils.envs import load_dotenv_for_agent
from .utils.ui import get_cli_instance, get_interruptible_cli_instance, UITheme


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
        query = await prompt_session.prompt_async('user > ')
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
        query = input('user > ')
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
          filtered_text = _filter_thought_content(text)
          if filtered_text.strip():  # Only display if there's non-thought content
            if not fallback_mode and cli:
              panel = cli.format_agent_response(filtered_text, event.author)
              cli.console.print(panel)
            else:
              # Simple output for fallback mode
              console.print(f"[green]{event.author}[/green]: {filtered_text}")
  # Use graceful cleanup to handle MCP session cleanup errors
  from .utils.cleanup import close_runner_gracefully
  await close_runner_gracefully(runner)


def _filter_thought_content(text: str) -> str:
  """Filter out thought content patterns from agent responses."""
  if not text or not text.strip():
    return text
    
  lines = text.split('\n')
  filtered_lines = []
  skip_section = False
  
  for line in lines:
    line_lower = line.lower().strip()
    
    # Check for thought section markers
    if line.startswith('**') and any(marker in line_lower for marker in [
      'thinking', 'approach', 'analytical', 'process', 'determining', 
      'navigating', 'finding', 'current time', 'my approach'
    ]):
      skip_section = True
      continue
    
    # Check for end of thought section (empty line or new content)
    if skip_section and (not line.strip() or line.startswith('#') or 
                        line.startswith('The ') or line.startswith('I ')):
      if line.startswith('The ') or line.startswith('I '):
        skip_section = False
        filtered_lines.append(line)
      continue
    
    # Skip lines that are part of thought content
    if skip_section:
      continue
      
    # Check for standalone thought patterns
    if any(pattern in line_lower for pattern in [
      'okay, so the user wants', 'let me think about', 'my best bet is to',
      'first step is to', 'given my understanding', 'i recognize that'
    ]):
      continue
    
    # Keep the line if it's not thought content
    filtered_lines.append(line)
  
  return '\n'.join(filtered_lines)


def _strip_rich_markup(text: str) -> str:
  """Aggressively strip Rich markup, panels, and ANSI codes from text."""
  import re
  from rich.console import Console
  from io import StringIO
  
  try:
    # Create a console that outputs plain text
    string_io = StringIO()
    temp_console = Console(
        file=string_io, 
        force_terminal=False, 
        width=120, 
        legacy_windows=False,
        force_jupyter=False,
        _environ={}
    )
    
    # Print the text and capture plain output
    temp_console.print(text, markup=False, highlight=False, crop=False, overflow="ignore")
    rendered_text = string_io.getvalue()
    
  except Exception:
    rendered_text = text
  
  # Remove box drawing characters and panel borders (comprehensive set)
  box_chars = r'[┌┐└┘├┤┬┴┼─│╭╮╰╯╠╣╦╩╬═║╔╗╚╝╠╣╦╩╬▀▄█▌▐░▒▓■□▪▫▬▲►▼◄◊○●◦☼♠♣♥♦♪♫☺☻♂♀]'
  clean_text = re.sub(box_chars, '', rendered_text)
  
  # Remove panel structures completely
  panel_patterns = [
      r'╭[─]*.*?─*╮',  # Panel tops
      r'╰[─]*.*?─*╯',  # Panel bottoms  
      r'│.*?│',        # Panel sides (but preserve content)
      r'┌[─]*.*?─*┐',  # Box tops
      r'└[─]*.*?─*┘',  # Box bottoms
  ]
  
  for pattern in panel_patterns:
      clean_text = re.sub(pattern, '', clean_text, flags=re.DOTALL)
  
  # Remove Rich markup patterns
  markup_patterns = [
      r'\[/?bold\]',
      r'\[/?italic\]', 
      r'\[/?underline\]',
      r'\[/?dim\]',
      r'\[/?bright\]',
      r'\[/?reverse\]',
      r'\[/?strike\]',
      r'\[/?blink\]',
      r'\[/?conceal\]',
      r'\[/?[a-z_]+\]',  # Any other markup tags
      r'\[/?#[0-9a-fA-F]{6}\]',  # Hex colors
      r'\[/?rgb\(\d+,\d+,\d+\)\]',  # RGB colors
      r'\[/?on [a-z_]+\]',  # Background colors
  ]
  
  for pattern in markup_patterns:
      clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
  
  # Remove ANSI escape sequences
  ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
  clean_text = ansi_escape.sub('', clean_text)
  
  # Extract meaningful content from specific patterns
  # Handle Token Usage patterns
  token_match = re.search(r'Token Usage[:\s]*([^│\n\r]*)', clean_text, re.IGNORECASE)
  if token_match:
      token_info = token_match.group(1).strip()
      clean_text = re.sub(r'.*Token Usage.*?(?=\n\n|\n[A-Z]|\Z)', f'Token Usage: {token_info}', clean_text, flags=re.DOTALL | re.IGNORECASE)
  
  # Handle Agent Thought/Thinking patterns  
  thought_match = re.search(r'Agent (?:Thought|Thinking)[:\s]*(.*?)(?=\n\n|\n[A-Z]|\Z)', clean_text, re.DOTALL | re.IGNORECASE)
  if thought_match:
      thought_content = thought_match.group(1).strip()
      clean_text = re.sub(r'.*Agent (?:Thought|Thinking).*?(?=\n\n|\n[A-Z]|\Z)', f'Agent Thought: {thought_content}', clean_text, flags=re.DOTALL | re.IGNORECASE)
  
  # Clean up whitespace and normalize
  clean_text = re.sub(r'[ \t]+', ' ', clean_text)  # Multiple spaces to single
  clean_text = re.sub(r'\n\s*\n+', '\n', clean_text)  # Multiple newlines to single
  clean_text = re.sub(r'^\s*\n', '', clean_text)  # Remove leading newlines
  clean_text = '\n'.join(line.strip() for line in clean_text.split('\n') if line.strip())
  
  return clean_text.strip()


async def run_interactively_with_interruption(
    root_agent: BaseAgent,
    artifact_service: BaseArtifactService,
    session: Session,
    session_service: BaseSessionService,
    ui_theme: Optional[str] = None,
) -> None:
  """Run interactively with persistent input and interruption capabilities."""
  # Disable Rich formatting to prevent conflicts with prompt_toolkit
  import os
  import sys
  from io import StringIO
  
  original_env = {}
  rich_disable_vars = {
      'NO_COLOR': '1',
      'TERM': 'dumb',
      'FORCE_COLOR': '0',
      'RICH_FORCE_TERMINAL': 'false',
  }
  
  # Store original values and set new ones
  for key, value in rich_disable_vars.items():
      original_env[key] = os.environ.get(key)
      os.environ[key] = value
  
  try:
    # Suppress MCP server output during Runner initialization
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        runner = Runner(
            app_name=session.app_name,
            agent=root_agent,
            artifact_service=artifact_service,
            session_service=session_service,
        )
  
    # Initialize the interruptible CLI
    cli = get_interruptible_cli_instance(ui_theme)
    
    # Set up callbacks for agent interaction
    async def handle_user_input(query: str):
      """Handle user input and run agent."""
      current_task = None
      try:
        # Create async generator for agent responses
        agent_gen = runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(role='user', parts=[types.Part(text=query)]),
        )
        
        # Create task for agent execution
        current_task = asyncio.create_task(_process_agent_responses(agent_gen, cli))
        cli.set_agent_task(current_task)
        
        # Wait for completion
        await current_task
        
      except asyncio.CancelledError:
        cli.add_agent_output("⚠️ Agent execution was interrupted", "System")
      except Exception as e:
        cli.add_agent_output(f"❌ Error: {str(e)}", "System")
    
    async def handle_interrupt():
      """Handle agent interruption."""
      # Additional cleanup can be added here
      cli.add_agent_output("🛑 Agent interrupted - you can continue with a new query", "System")
    
    # Register callbacks
    cli.register_input_callback(handle_user_input)
    cli.register_interrupt_callback(handle_interrupt)
    
    # Create and run the application with output patching
    app = cli.create_application()
    with patch_stdout():
        await app.run_async()
    
  except Exception as e:
    # Fallback to regular CLI if InterruptibleCLI fails
    console = Console()
    console.print(f"[warning]⚠️  InterruptibleCLI failed: {str(e)}[/warning]")
    console.print("[info]Falling back to regular CLI...[/info]")
    await run_interactively(root_agent, artifact_service, session, session_service, ui_theme)
  
  finally:
    # Clean up CLI resources
    if 'cli' in locals():
        cli.cleanup()
    
    # Restore original environment variables
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
  
  # Use graceful cleanup to handle MCP session cleanup errors
  from .utils.cleanup import close_runner_gracefully
  await close_runner_gracefully(runner)


async def _process_agent_responses(agent_gen, cli):
  """Process agent responses and add them to the CLI output."""
  from io import StringIO
  from contextlib import redirect_stdout, redirect_stderr
  
  # Use output redirection to intercept any Rich console output from the agent
  with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
    async for event in agent_gen:
      if event.content and event.content.parts:
        if text := ''.join(part.text or '' for part in event.content.parts):
          # Filter out thought content to prevent duplication
          filtered_text = _filter_thought_content(text)
          if filtered_text.strip():  # Only display if there's non-thought content
            # Strip any Rich markup/ANSI codes for clean prompt_toolkit display
            clean_text = _strip_rich_markup(filtered_text)
            cli.add_agent_output(clean_text, event.author)
      
      # Also check if the event itself contains Rich objects or formatted content
      # This handles cases where the agent generates Rich panels directly
      if hasattr(event, '__dict__'):
        for attr_name, attr_value in event.__dict__.items():
          if attr_name not in ['content', 'author', 'timestamp'] and attr_value:
            # Check if this attribute contains Rich content
            if hasattr(attr_value, '__rich__') or hasattr(attr_value, '__rich_console__'):
              clean_attr_text = _strip_rich_markup(str(attr_value))
              if clean_attr_text.strip():
                cli.add_agent_output(clean_attr_text, f"{event.author} ({attr_name})")


async def run_cli(
    *,
    agent_module_name: str,
    input_file: Optional[str] = None,
    saved_session_file: Optional[str] = None,
    save_session: bool,
    session_id: Optional[str] = None,
    ui_theme: Optional[str] = None,
    interruptible: bool = False,
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
    interruptible: bool, whether to use the interruptible CLI with persistent
      input and agent interruption capabilities.
  """

  # Initialize Rich Console with scrollback-friendly settings
  console = Console(
      force_interactive=False,  # Disable animations that might interfere with scrollback
      soft_wrap=True,           # Enable soft wrapping to prevent cropping
      width=None,               # Auto-detect width to avoid fixed sizing issues
      height=None               # Auto-detect height to avoid fixed sizing issues
  )

  artifact_service = InMemoryArtifactService()
  session_service = InMemorySessionService()

  user_id = 'test_user'
  session = await session_service.create_session(
      app_name=agent_module_name, user_id=user_id
  )
  root_agent: BaseAgent = AgentLoader().load_agent(agent_module_name)

  # Ensure the loaded agent is an LlmAgent before proceeding.
  if not isinstance(root_agent, LlmAgent):
    raise ValueError(
        f"Loaded agent '{agent_module_name}' is of type {type(root_agent).__name__},"
        " but an LlmAgent is required."
    )

  envs.load_dotenv_for_agent(agent_module_name)
  if input_file:
    session = await run_input_file(
        app_name=agent_module_name,
        user_id=user_id,
        root_agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        input_path=input_file,
    )
  elif saved_session_file:
    with open(saved_session_file, 'r', encoding='utf-8') as f:
      loaded_session = Session.model_validate_json(f.read())

    if loaded_session:
      console.print(f"[bold blue]Loading session from[/bold blue] [blue]{saved_session_file}[/blue]")
      for event in loaded_session.events:
        await session_service.append_event(session, event)
        content = event.content
        if not content or not content.parts or not content.parts[0].text:
          continue
        if event.author == 'user':
          console.print(f'[blue][user][/blue]: {content.parts[0].text}')
        else:
          console.print(f'[{event.author}]: {content.parts[0].text}')

    if interruptible:
      await run_interactively_with_interruption(
          root_agent,
          artifact_service,
          session,
          session_service,
          ui_theme,
      )
    else:
      await run_interactively(
          root_agent,
          artifact_service,
          session,
          session_service,
          ui_theme,
      )
  else:
    # Use enhanced CLI for startup message too
    if interruptible:
      # InterruptibleCLI handles its own welcome message
      await run_interactively_with_interruption(
          root_agent,
          artifact_service,
          session,
          session_service,
          ui_theme,
      )
    else:
      cli = get_cli_instance(ui_theme)
      cli.console.print(f'[accent]🚀 Starting interactive session with agent [agent]{root_agent.name}[/agent][/accent]')
      cli.console.print(f'[muted]Type [user]help[/user] for commands or [user]exit[/user] to quit[/muted]')
      await run_interactively(
          root_agent,
          artifact_service,
          session,
          session_service,
          ui_theme,
      )

  if save_session:
    session_id = session_id or input('Session ID to save: ')
    # session_path = (
    #     f'{agent_parent_dir}/{agent_folder_name}/{session_id}.session.json'
    # )
    # TODO(b/341398863): Save session into artifact service or use XDG_STATE_HOME
    print('Session saving is not implemented for installed agents yet.')


@click.command()
@click.option('--agent', '-a', required=True, help='Agent module name (e.g., agents.devops)')
@click.option('--input-file', '-i', help='Input file with queries')
@click.option('--saved-session', '-s', help='Saved session file to resume')
@click.option('--save-session', is_flag=True, help='Save session on exit')
@click.option('--session-id', help='Session ID for saving')
@click.option('--theme', type=click.Choice(['light', 'dark']), help='UI theme')
@click.option('--interruptible', is_flag=True, help='Use interruptible CLI with persistent input pane')
def main(agent: str, input_file: Optional[str], saved_session: Optional[str], 
         save_session: bool, session_id: Optional[str], theme: Optional[str], interruptible: bool):
    """ADK Agent CLI with optional interruptible interface."""
    import asyncio
    
    asyncio.run(run_cli(
        agent_module_name=agent,
        input_file=input_file,
        saved_session_file=saved_session,
        save_session=save_session,
        session_id=session_id,
        ui_theme=theme,
        interruptible=interruptible,
    ))

if __name__ == '__main__':
    main()
