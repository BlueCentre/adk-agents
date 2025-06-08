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
from prompt_toolkit import PromptSession
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
from google.adk.events.event import Event


class InputFile(BaseModel):
  state: dict[str, object]
  queries: list[str]


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
) -> None:
  runner = Runner(
      app_name=session.app_name,
      agent=root_agent,
      artifact_service=artifact_service,
      session_service=session_service,
  )
  # Initialize Rich Console
  console = Console()
  prompt_session = PromptSession()
  while True:
    with patch_stdout():
      query = await prompt_session.prompt_async('😎 user > ')
    if not query or not query.strip():
      continue
    if query == 'exit':
      break
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(role='user', parts=[types.Part(text=query)]),
    ):
      if event.content and event.content.parts:
        if text := ''.join(part.text or '' for part in event.content.parts):
          markdown_text = Markdown(text)
          panel = Panel(
              markdown_text,
              title=f"🤖 [green]{event.author}[/green]",
              border_style="green",
              expand=True
          )
          console.print(panel)
  await runner.close()


async def run_cli(
    *,
    agent_module_name: str,
    input_file: Optional[str] = None,
    saved_session_file: Optional[str] = None,
    save_session: bool,
    session_id: Optional[str] = None,
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
    )
  else:
    console.print(f'[yellow]Running agent [green]{root_agent.name}[/green], type exit to exit.[/yellow]')
    await run_interactively(
        root_agent,
        artifact_service,
        session,
        session_service,
    )

  if save_session:
    session_id = session_id or input('Session ID to save: ')
    # session_path = (
    #     f'{agent_parent_dir}/{agent_folder_name}/{session_id}.session.json'
    # )
    # TODO(b/341398863): Save session into artifact service or use XDG_STATE_HOME
    print('Session saving is not implemented for installed agents yet.')
