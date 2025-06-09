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

from datetime import datetime
from typing import Optional

import rich_click as click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit.patch_stdout import patch_stdout

from google.genai import types
from pydantic import BaseModel

from google.adk.agents.llm_agent import LlmAgent
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
from .utils.ui import get_cli_instance, UITheme
from google.adk.events.event import Event


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
  
  # Initialize basic console for fallback
  console = Console()
  
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
      output_console = console if fallback_mode else cli.console
      output_console.print("\n[warning]Goodbye! 👋[/warning]")
      break
    except Exception as e:
      # Handle other prompt-related errors gracefully
      output_console = console if fallback_mode else cli.console
      output_console.print(f"\n[red]❌ Prompt error: {str(e)}[/red]")
      output_console.print("[yellow]💡 Try using a simpler terminal or check your environment.[/yellow]")
      output_console.print("[blue]Falling back to basic input mode...[/blue]")
      try:
        query = input('user > ')
      except (EOFError, KeyboardInterrupt):
        output_console.print("\n[warning]Goodbye! 👋[/warning]")
        break
      
    if not query or not query.strip():
      continue
    if query.strip().lower() in ['exit', 'quit', 'bye']:
      output_console = console if fallback_mode else cli.console
      output_console.print("[warning]Goodbye! 👋[/warning]")
      break
    
    # Handle special commands
    if query.strip().lower() == 'clear':
      output_console = console if fallback_mode else cli.console
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
          if not fallback_mode and cli:
            panel = cli.format_agent_response(text, event.author)
            cli.console.print(panel)
          else:
            # Simple output for fallback mode
            console.print(f"[green]{event.author}[/green]: {text}")
  await runner.close()


async def run_cli(
    *,
    agent_module_name: str,
    input_file: Optional[str] = None,
    saved_session_file: Optional[str] = None,
    save_session: bool,
    session_id: Optional[str] = None,
    ui_theme: Optional[str] = None,
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
  """

  # Initialize Rich Console
  console = Console()

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

    await run_interactively(
        root_agent,
        artifact_service,
        session,
        session_service,
        ui_theme,
    )
  else:
    # Use enhanced CLI for startup message too
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
