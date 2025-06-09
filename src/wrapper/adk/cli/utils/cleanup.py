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

import asyncio
import logging
from typing import List

from google.adk.runners import Runner

logger = logging.getLogger("google_adk." + __name__)


async def close_runners(runners: List[Runner]) -> None:
  cleanup_tasks = [asyncio.create_task(runner.close()) for runner in runners]
  if cleanup_tasks:
    # Wait for all cleanup tasks with timeout
    done, pending = await asyncio.wait(
        cleanup_tasks,
        timeout=30.0,  # 30 second timeout for cleanup
        return_when=asyncio.ALL_COMPLETED,
    )

    # If any tasks are still pending, log it
    if pending:
      logger.warning(
          "%s runner close tasks didn't complete in time", len(pending)
      )
      for task in pending:
        task.cancel()


async def close_runner_gracefully(runner: Runner) -> None:
  """
  Gracefully close a single runner, handling MCP cleanup errors.
  
  This function specifically handles the common "cancel scope" error
  that occurs during MCP session cleanup when exiting agents.
  """
  try:
    await runner.close()
  except asyncio.CancelledError as e:
    # Handle asyncio.CancelledError specifically (common in MCP cleanup)
    logger.warning(f"MCP session cleanup completed with cancellation (this is normal): {e}")
  except Exception as e:
    error_msg = str(e)
    # Handle known MCP cleanup issues gracefully
    if ("cancel scope" in error_msg.lower() or 
        "mcp" in error_msg.lower()):
      logger.warning(f"MCP session cleanup completed with warning (this is normal): {error_msg}")
    else:
      # For other errors, log them but don't fail the cleanup
      logger.error(f"Runner cleanup error: {error_msg}", exc_info=True)
      raise  # Re-raise non-MCP errors
