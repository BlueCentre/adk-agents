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

import importlib.resources
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__file__)


def _get_current_dir_dotenv_path() -> str:
    """Get the path to the current directory's .env file."""
    current_dir = Path.cwd()
    dotenv_path = current_dir / ".env"
    if dotenv_path.exists():
        return str(dotenv_path)
    return ""


def _get_user_dotenv_path() -> str:
    """Get the path to the user's .env file."""
    home_dir = Path.home()
    dotenv_path = home_dir / ".env"
    if dotenv_path.exists():
        return str(dotenv_path)
    return ""


def _walk_to_root_until_found(folder, filename) -> str:
    folder = Path(folder)  # Ensure folder is a Path object
    checkpath = folder / filename
    if checkpath.exists() and checkpath.is_file():
        return str(checkpath)

    parent_folder = folder.parent
    if parent_folder == Path(folder):  # reached the root
        return ""

    return _walk_to_root_until_found(parent_folder, filename)


def load_dotenv_for_agent(
    agent_name: str, agent_parent_folder: Optional[str] = None, filename: str = ".env"
):
    """Loads the .env file for the agent module."""

    # Gets the folder of agent_module as starting_folder
    if agent_parent_folder:
        starting_folder = (Path(agent_parent_folder) / agent_name).resolve()
    else:
        # If agent_parent_folder is not provided, assume it's an installed package
        # and try to find the module's location
        try:
            # First try the agent_name as-is (for packages)
            module_path = importlib.resources.files(agent_name.replace("/", "."))
            starting_folder = module_path.resolve()
        except Exception as e:
            # If that fails, try extracting the package part (for modules within packages)
            try:
                # Extract package path by removing the last component
                package_parts = agent_name.replace("/", ".").split(".")
                if len(package_parts) > 1:
                    package_name = ".".join(package_parts[:-1])  # Remove last component
                    module_path = importlib.resources.files(package_name)
                    starting_folder = module_path.resolve()
                else:
                    raise e  # Re-raise original error if no package structure
            except Exception:
                logger.warning(f"Could not determine agent module path for {agent_name}: {e}")
                logger.info("No %s file found for %s", filename, agent_name)
                return

    dotenv_file_path = _walk_to_root_until_found(starting_folder, filename)
    if dotenv_file_path:
        load_dotenv(dotenv_file_path, override=True, verbose=True)
        logger.info(
            "Loaded %s file for %s at %s",
            filename,
            agent_name,
            dotenv_file_path,
        )
    elif _get_current_dir_dotenv_path():
        load_dotenv(_get_current_dir_dotenv_path(), override=True, verbose=True)
        logger.info(
            "Loaded %s file for %s at %s",
            filename,
            agent_name,
            _get_current_dir_dotenv_path(),
        )
    elif _get_user_dotenv_path():
        load_dotenv(_get_user_dotenv_path(), override=True, verbose=True)
        logger.info(
            "Loaded %s file for %s at %s",
            filename,
            agent_name,
            _get_user_dotenv_path(),
        )
    else:
        logger.info("No %s file found for %s", filename, agent_name)
