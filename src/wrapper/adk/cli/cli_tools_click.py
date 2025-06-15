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
import collections
from contextlib import asynccontextmanager
from datetime import datetime
import functools
import logging
import os
import sys
import tempfile
from typing import Optional

import rich_click as click
from fastapi import FastAPI
import uvicorn

from . import cli_create
from . import cli_deploy
from .. import version
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from .cli import run_cli
from .fast_api import get_fast_api_app
from .utils import envs
from .utils import logs


class HelpfulCommand(click.Command):
  """Command that shows full help on error instead of just the error message.

  A custom Click Command class that overrides the default error handling
  behavior to display the full help text when a required argument is missing,
  followed by the error message. This provides users with better context
  about command usage without needing to run a separate --help command.

  Args:
    *args: Variable length argument list to pass to the parent class.
    **kwargs: Arbitrary keyword arguments to pass to the parent class.

  Returns:
    None. Inherits behavior from the parent Click Command class.

  Returns:
  """

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  @staticmethod
  def _format_missing_arg_error(click_exception):
    """Format the missing argument error with uppercase parameter name.

    Args:
      click_exception: The MissingParameter exception from Click.

    Returns:
      str: Formatted error message with uppercase parameter name.
    """
    name = click_exception.param.name
    return f"Missing required argument: {name.upper()}"

  def parse_args(self, ctx, args):
    """Override the parse_args method to show help text on error.

    Args:
      ctx: Click context object for the current command.
      args: List of command-line arguments to parse.

    Returns:
      The parsed arguments as returned by the parent class's parse_args method.

    Raises:
      click.MissingParameter: When a required parameter is missing, but this
        is caught and handled by displaying the help text before exiting.
    """
    try:
      return super().parse_args(ctx, args)
    except click.MissingParameter as exc:
      error_message = self._format_missing_arg_error(exc)

      click.echo(ctx.get_help())
      click.secho(f"\nError: {error_message}", fg="red", err=True)
      ctx.exit(2)


logger = logging.getLogger("google_adk." + __name__)


@click.group(context_settings={"max_content_width": 240})
@click.version_option(version.__version__)
def main():
  """Agent Development Kit CLI tools."""
  pass


@main.group()
def deploy():
  """Deploys agent to hosted environments."""
  pass


@main.command("create", cls=HelpfulCommand)
@click.option(
    "--model",
    type=str,
    help="Optional. The model used for the root agent.",
)
@click.option(
    "--api_key",
    type=str,
    help=(
        "Optional. The API Key needed to access the model, e.g. Google AI API"
        " Key."
    ),
)
@click.option(
    "--project",
    type=str,
    help="Optional. The Google Cloud Project for using VertexAI as backend.",
)
@click.option(
    "--region",
    type=str,
    help="Optional. The Google Cloud Region for using VertexAI as backend.",
)
@click.argument("app_name", type=str, required=True)
def cli_create_cmd(
    app_name: str,
    model: Optional[str],
    api_key: Optional[str],
    project: Optional[str],
    region: Optional[str],
):
  """Creates a new app in the current folder with prepopulated agent template.

  APP_NAME: required, the folder of the agent source code.

  Example:

    adk create path/to/my_app
  """
  cli_create.run_cmd(
      app_name,
      model=model,
      google_api_key=api_key,
      google_cloud_project=project,
      google_cloud_region=region,
  )


def validate_exclusive(ctx, param, value):
  # Store the validated parameters in the context
  if not hasattr(ctx, "exclusive_opts"):
    ctx.exclusive_opts = {}

  # If this option has a value and we've already seen another exclusive option
  if value is not None and any(ctx.exclusive_opts.values()):
    exclusive_opt = next(key for key, val in ctx.exclusive_opts.items() if val)
    raise click.UsageError(
        f"Options '{param.name}' and '{exclusive_opt}' cannot be set together."
    )

  # Record this option's value
  ctx.exclusive_opts[param.name] = value is not None
  return value


@main.command("run")
@click.option(
    "--save_session",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Optional. Whether to save the session to a json file on exit.",
)
@click.option(
    "--session_id",
    type=str,
    help=(
        "Optional. The session ID to save the session to on exit when"
        " --save_session is set to true. User will be prompted to enter a"
        " session ID if not set."
    ),
)
@click.option(
    "--replay",
    type=click.Path(
        exists=True, dir_okay=False, file_okay=True, resolve_path=True
    ),
    help=(
        "The json file that contains the initial state of the session and user"
        " queries. A new session will be created using this state. And user"
        " queries are run againt the newly created session. Users cannot"
        " continue to interact with the agent."
    ),
    callback=validate_exclusive,
)
@click.option(
    "--resume",
    type=click.Path(
        exists=True, dir_okay=False, file_okay=True, resolve_path=True
    ),
    help=(
        "The json file that contains a previously saved session (by"
        "--save_session option). The previous session will be re-displayed. And"
        " user can continue to interact with the agent."
    ),
    callback=validate_exclusive,
)
@click.option(
    "--ui_theme",
    type=click.Choice(["dark", "light"], case_sensitive=False),
    help=(
        "Optional. UI theme for the CLI interface. Choices: 'dark', 'light'. "
        "If not provided, auto-detects from environment (ADK_CLI_THEME) or defaults to dark."
    ),
)
@click.option(
    "--interruptible",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Optional. Use interruptible CLI with persistent input pane and agent interruption capabilities. "
        "Allows typing while agent is responding and interrupting with Ctrl+C."
    ),
)
@click.argument(
    "agent_module_name",
    type=str,
)
def cli_run(
    agent_module_name: str,
    save_session: bool,
    session_id: Optional[str],
    replay: Optional[str],
    resume: Optional[str],
    ui_theme: Optional[str],
    interruptible: bool,
):
  """Runs an interactive CLI for a certain agent.

  AGENT_MODULE_NAME: required, the module path to the agent, e.g. 'agents.devops'

  Example:

    adk-agent run agents.devops
  """
  logs.log_to_tmp_folder()
  asyncio.run(
      run_cli(
          agent_module_name=agent_module_name,
          input_file=replay,
          saved_session_file=resume,
          save_session=save_session,
          session_id=session_id,
          ui_theme=ui_theme,
          interruptible=interruptible,
      )
  )


def fast_api_common_options():
  """Common options for FastAPI commands."""

  def decorator(func):
    @click.option(
        "--session_db_url",
        help=(
            """Optional. The database URL to store the session.
          - Use 'agentengine://<agent_engine_resource_id>' to connect to Agent Engine sessions.
          - Use 'sqlite://<path_to_sqlite_file>' to connect to a SQLite DB.
          - See https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls for more details on supported DB URLs."""
        ),
    )
    @click.option(
        "--artifact_storage_uri",
        type=str,
        help=(
            "Optional. The artifact storage URI to store the artifacts,"
            " supported URIs: gs://<bucket name> for GCS artifact service."
        ),
        default=None,
    )
    @click.option(
        "--host",
        type=str,
        help="Optional. The binding host of the server",
        default="127.0.0.1",
        show_default=True,
    )
    @click.option(
        "--port",
        type=int,
        help="Optional. The port of the server",
        default=8000,
    )
    @click.option(
        "--allow_origins",
        help="Optional. Any additional origins to allow for CORS.",
        multiple=True,
    )
    @click.option(
        "--log_level",
        type=click.Choice(
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            case_sensitive=False,
        ),
        default="INFO",
        help="Optional. Set the logging level",
    )
    @click.option(
        "--trace_to_cloud",
        is_flag=True,
        show_default=True,
        default=False,
        help="Optional. Whether to enable cloud trace for telemetry."
    )
    @click.option(
        "--reload/--no-reload",
        default=True,
        help="Optional. Whether to enable auto reload for server.",
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
      # Set up logging before running the FastAPI app.
      logs.setup_adk_logger(kwargs["log_level"])
      return func(*args, **kwargs)
    return wrapper

  return decorator


@main.command("web")
@fast_api_common_options()
@click.argument(
    "agents_dir",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, resolve_path=True
    ),
    default=os.getcwd(),
)
def cli_web(
    agents_dir: str,
    session_db_url: str = "",
    artifact_storage_uri: Optional[str] = None,
    log_level: str = "INFO",
    allow_origins: Optional[list[str]] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    trace_to_cloud: bool = False,
    reload: bool = True,
):
  """Runs a local FastAPI server for the ADK Web UI.

  AGENTS_DIR: required, the directory of agents, where each sub-directory is a
  single agent.

  Example:

    adk web agents/devops
  """
  uvicorn.run(
      get_fast_api_app(
          agents_dir=agents_dir,
          session_db_url=session_db_url,
          artifact_storage_uri=artifact_storage_uri,
          allow_origins=list(allow_origins) if allow_origins else None,
          web=True,
          trace_to_cloud=trace_to_cloud,
      ),
      host=host,
      port=port,
      reload=reload,
  )


@main.command("api_server")
# The directory of agents, where each sub-directory is a single agent.
# By default, it is the current working directory
@click.argument(
    "agents_dir",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, resolve_path=True
    ),
    default=os.getcwd(),
)
@fast_api_common_options()
def cli_api_server(
    agents_dir: str,
    session_db_url: str = "",
    artifact_storage_uri: Optional[str] = None,
    log_level: str = "INFO",
    allow_origins: Optional[list[str]] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    trace_to_cloud: bool = False,
    reload: bool = True,
):
  """Runs a local FastAPI server.

  AGENTS_DIR: required, the directory of agents, where each sub-directory is a
  single agent.

  Example:

    adk api_server agents/devops
  """
  uvicorn.run(
      get_fast_api_app(
          agents_dir=agents_dir,
          session_db_url=session_db_url,
          artifact_storage_uri=artifact_storage_uri,
          allow_origins=list(allow_origins) if allow_origins else None,
          web=False,
          trace_to_cloud=trace_to_cloud,
      ),
      host=host,
      port=port,
      reload=reload,
  )


@deploy.command("cloud_run")
@click.option(
    "--project",
    type=str,
    help=(
        "Required. Google Cloud project to deploy the agent. When absent,"
        " default project from gcloud config is used."
    ),
)
@click.option(
    "--region",
    type=str,
    help=(
        "Required. Google Cloud region to deploy the agent. When absent,"
        " gcloud run deploy will prompt later."
    ),
)
@click.option(
    "--service_name",
    type=str,
    default="adk-default-service-name",
    help=(
        "Optional. The service name to use in Cloud Run (default:"
        " 'adk-default-service-name')."
    ),
)
@click.option(
    "--app_name",
    type=str,
    default="",
    help=(
        "Optional. App name of the ADK API server (default: the folder name"
        " of the AGENT source code)."
    ),
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Optional. The port of the ADK API server (default: 8000).",
)
@click.option(
    "--trace_to_cloud",
    is_flag=True,
    show_default=True,
    default=False,
    help="Optional. Whether to enable Cloud Trace for cloud run.",
)
@click.option(
    "--with_ui",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Optional. Deploy ADK Web UI if set. (default: deploy ADK API server"
        " only)"
    ),
)
@click.option(
    "--temp_folder",
    type=str,
    default=os.path.join(
        tempfile.gettempdir(),
        "cloud_run_deploy_src",
        datetime.now().strftime("%Y%m%d_%H%M%S"),
    ),
    help=(
        "Optional. Temp folder for the generated Cloud Run source files"
        " (default: a timestamped folder in the system temp directory)."
    ),
)
@click.option(
    "--verbosity",
    type=click.Choice(
        ["debug", "info", "warning", "error", "critical"], case_sensitive=False
    ),
    default="WARNING",
    help="Optional. Override the default verbosity level.",
)
@click.option(
    "--session_db_url",
    help=(
        """Optional. The database URL to store the session.

  - Use 'agentengine://<agent_engine_resource_id>' to connect to Agent Engine sessions.

  - Use 'sqlite://<path_to_sqlite_file>' to connect to a SQLite DB.

  - See https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls for more details on supported DB URLs."""
    ),
)
@click.option(
    "--artifact_storage_uri",
    type=str,
    help=(
        "Optional. The artifact storage URI to store the artifacts, supported"
        " URIs: gs://<bucket name> for GCS artifact service."
    ),
    default=None,
)
@click.argument(
    "agent",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, resolve_path=True
    ),
)
@click.option(
    "--adk_version",
    type=str,
    default=version.__version__,
    show_default=True,
    help=(
        "Optional. The ADK version used in Cloud Run deployment. (default: the"
        " version in the dev environment)"
    ),
)
def cli_deploy_cloud_run(
    agent: str,
    project: Optional[str],
    region: Optional[str],
    service_name: str,
    app_name: str,
    temp_folder: str,
    port: int,
    trace_to_cloud: bool,
    with_ui: bool,
    verbosity: str,
    session_db_url: str,
    artifact_storage_uri: Optional[str],
    adk_version: str,
):
  """Deploys an agent to Cloud Run.

  AGENT: required, the file path to the agent entry point (e.g.,
  agents/devops/agent.py or agents/devops/__init__.py).

  Example:

    adk deploy cloud_run agents/devops/agent.py --project my-gcp-project
  """
  cli_deploy.to_cloud_run(
      agent_folder=agent,
      project=project,
      region=region,
      service_name=service_name,
      app_name=app_name,
      temp_folder=temp_folder,
      port=port,
      trace_to_cloud=trace_to_cloud,
      with_ui=with_ui,
      verbosity=verbosity,
      session_db_url=session_db_url,
      artifact_storage_uri=artifact_storage_uri,
      adk_version=adk_version,
  )


@deploy.command("agent_engine")
@click.option(
    "--project",
    type=str,
    help="Required. Google Cloud project to deploy the agent.",
)
@click.option(
    "--region",
    type=str,
    help="Required. Google Cloud region to deploy the agent.",
)
@click.option(
    "--staging_bucket",
    type=str,
    help="Required. GCS bucket for staging the deployment artifacts.",
)
@click.option(
    "--trace_to_cloud",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Optional. Whether to enable Cloud Trace for Agent Engine.",
)
@click.option(
    "--adk_app",
    type=str,
    default="agent_engine_app",
    help=(
        "Optional. Python file for defining the ADK application"
        " (default: a file named agent_engine_app.py)"
    ),
)
@click.option(
    "--temp_folder",
    type=str,
    default=os.path.join(
        tempfile.gettempdir(),
        "agent_engine_deploy_src",
        datetime.now().strftime("%Y%m%d_%H%M%S"),
    ),
    help=(
        "Optional. Temp folder for the generated Agent Engine source files."
        " If the folder already exists, its contents will be removed."
        " (default: a timestamped folder in the system temp directory)."
    ),
)
@click.option(
    "--env_file",
    type=str,
    default="",
    help=(
        "Optional. The filepath to the `.env` file for environment variables."
        " (default: the `.env` file in the `agent` directory, if any.)"
    ),
)
@click.option(
    "--requirements_file",
    type=str,
    default="",
    help=(
        "Optional. The filepath to the `requirements.txt` file to use."
        " (default: the `requirements.txt` file in the `agent` directory, if"
        " any.)"
    ),
)
@click.argument(
    "agent",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, resolve_path=True
    ),
)
def cli_deploy_agent_engine(
    agent: str,
    project: str,
    region: str,
    staging_bucket: str,
    trace_to_cloud: bool,
    adk_app: str,
    temp_folder: str,
    env_file: str,
    requirements_file: str,
):
  """Deploys an agent to Agent Engine.

  AGENT: required, the file path to the agent entry point (e.g.,
  agents/devops/agent.py or agents/devops/__init__.py).

  Example:

    adk deploy agent_engine agents/devops/agent.py --project my-gcp-project
    --region us-central1 --staging_bucket my-bucket
  """
  cli_deploy.to_agent_engine(
      agent_folder=agent,
      project=project,
      region=region,
      staging_bucket=staging_bucket,
      trace_to_cloud=trace_to_cloud,
      adk_app=adk_app,
      temp_folder=temp_folder,
      env_file=env_file,
      requirements_file=requirements_file,
  )
