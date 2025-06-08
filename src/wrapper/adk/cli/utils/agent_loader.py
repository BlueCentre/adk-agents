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

import importlib
import logging
import os
import sys
from typing import Optional
from pathlib import Path

from . import envs
from google.adk.agents.base_agent import BaseAgent

logger = logging.getLogger("google_adk." + __name__)


class AgentLoader:
  """Centralized agent loading with proper isolation, caching, and .env loading.
  Support loading agents from below folder/file structures:
  a)  {agent_name}.agent as a module name:
      agents_dir/{agent_name}/agent.py (with root_agent defined in the module)
  b)  {agent_name} as a module name
      agents_dir/{agent_name}.py (with root_agent defined in the module)
  c)  {agent_name} as a package name
      agents_dir/{agent_name}/__init__.py (with root_agent in the package)

  """

  def __init__(self, agents_dir: Optional[str] = None):
    self.agents_dir = agents_dir.rstrip("/") if agents_dir else None
    self._original_sys_path = None
    self._agent_cache: dict[str, BaseAgent] = {}

  @staticmethod
  def get_available_agent_modules(agents_dir: str) -> list[str]:
    # List all immediate subdirectories and .py files in agents_dir
    base_path = Path(agents_dir)
    if not base_path.exists():
      return []
    if not base_path.is_dir():
      return []

    agent_modules = []
    for item in os.listdir(base_path):
      item_path = base_path / item
      if item_path.is_dir() and not item.startswith(".") and item != "__pycache__":
        # This is a package, so the module name is the directory name
        agent_modules.append(item)
      elif item_path.is_file() and item.endswith(".py") and not item.startswith("."):
        # This is a module, remove .py extension
        module_name = item[:-3]
        if module_name != "__init__":  # Avoid listing __init__.py as a separate agent
          agent_modules.append(module_name)

    agent_modules.sort()
    return agent_modules

  def _load_from_module_or_package(
      self, agent_name: str
  ) -> Optional[BaseAgent]:
    # Load for case: Import "{agent_name}" (as a package or module)
    # Covers structures:
    #   a) agents_dir/{agent_name}.py (with root_agent in the module)
    #   b) agents_dir/{agent_name}/__init__.py (with root_agent in the package)
    try:
      module_candidate = importlib.import_module(agent_name)
      # Check for "root_agent" directly in "{agent_name}" module/package
      if hasattr(module_candidate, "root_agent"):
        logger.debug("Found root_agent directly in %s", agent_name)
        if isinstance(module_candidate.root_agent, BaseAgent):
          return module_candidate.root_agent
        else:
          logger.warning(
              "Root agent found is not an instance of BaseAgent. But a type %s",
              type(module_candidate.root_agent),
          )
      else:
        logger.debug(
            "Module %s has no root_agent. Trying next pattern.",
            agent_name,
        )

    except ModuleNotFoundError as e:
      if e.name == agent_name:
        logger.debug("Module %s itself not found.", agent_name)
      else:
        # it's the case the module imported by {agent_name}.agent module is not
        # found
        raise ValueError(f"Fail to load '{agent_name}' module. {str(e)}") from e
    except Exception as e:
      raise ValueError(
          f"Fail to load '{agent_name}' module. {str(e)}"
      ) from e

    return None

  def _load_from_submodule(self, agent_name: str) -> Optional[BaseAgent]:
    # Load for case: Import "{agent_name}.agent" and look for "root_agent"
    # Covers structure: agents_dir/{agent_name}/agent.py (with root_agent defined in the module)
    try:
      module_candidate = importlib.import_module(f"{agent_name}.agent")
      if hasattr(module_candidate, "root_agent"):
        logger.info("Found root_agent in %s.agent", agent_name)
        if isinstance(module_candidate.root_agent, BaseAgent):
          return module_candidate.root_agent
        else:
          logger.warning(
              "Root agent found is not an instance of BaseAgent. But a type %s",
              type(module_candidate.root_agent),
          )
      else:
        logger.debug(
            "Module %s.agent has no root_agent.",
            agent_name,
        )
    except ModuleNotFoundError as e:
      # if it's agent module not found, it's fine, search for next pattern
      if e.name == f"{agent_name}.agent" or e.name == agent_name:
        logger.debug("Module %s.agent not found.", agent_name)
      else:
        # it's the case the module imported by {agent_name}.agent module is not
        # found
        raise ValueError(f"Fail to load '{agent_name}.agent' module. {str(e)}") from e
    except Exception as e:
      raise ValueError(
          (
              f"Fail to load '{agent_name}.agent' module."
              f" {str(e)}"
          ),
      ) from e

    return None

  def _perform_load(self, agent_name: str) -> BaseAgent:
    """Internal logic to load an agent"""
    # Add self.agents_dir to sys.path
    if self.agents_dir:
      if self.agents_dir not in sys.path:
        sys.path.insert(0, self.agents_dir)

      logger.debug(
          "Loading .env for agent %s from %s", agent_name, self.agents_dir
      )
      envs.load_dotenv_for_agent(agent_name, str(self.agents_dir))
    else: # Handle case when agents_dir is None, so .env file needs to be located differently
      envs.load_dotenv_for_agent(agent_name)

    if root_agent := self._load_from_module_or_package(agent_name):
      return root_agent

    if root_agent := self._load_from_submodule(agent_name):
      return root_agent

    # If no root_agent was found by any pattern
    raise ValueError(
        f"No root_agent found for '{agent_name}'. Searched in"
        f" '{agent_name}.agent.root_agent', '{agent_name}.root_agent'."
        f" Ensure '{self.agents_dir}/{agent_name}' is structured correctly,"
        " an .env file can be loaded if present, and a root_agent is"
        " exposed."
    )

  def load_agent(self, agent_name: str) -> BaseAgent:
    """Load an agent module (with caching & .env) and return its root_agent."""
    if agent_name in self._agent_cache:
      logger.debug("Returning cached agent for %s (async)", agent_name)
      return self._agent_cache[agent_name]

    logger.debug("Loading agent %s - not in cache.", agent_name)
    agent = self._perform_load(agent_name)
    self._agent_cache[agent_name] = agent
    return agent


def load_agent_from_module(agent_module_name: str) -> BaseAgent:
  """Loads an agent directly from an installed Python module.

  Args:
    agent_module_name: The full module path to the agent, e.g., 'agents.devops'.

  Returns:
    The loaded BaseAgent instance.

  Raises:
    ValueError: If the agent module or `root_agent` is not found.
  """
  try:
    module = importlib.import_module(agent_module_name)
    if hasattr(module, "root_agent"):
      if isinstance(module.root_agent, BaseAgent):
        return module.root_agent
      else:
        raise TypeError(
            f"root_agent in '{agent_module_name}' is not an instance of "
            f"BaseAgent, but type {type(module.root_agent)}."
        )
    else:
      raise ValueError(f"No 'root_agent' found in module '{agent_module_name}'.")
  except ModuleNotFoundError as e:
    raise ValueError(f"Agent module '{agent_module_name}' not found.") from e
  except Exception as e:
    raise ValueError(
        f"Failed to load agent from module '{agent_module_name}'. Error: {e}"
    ) from e
