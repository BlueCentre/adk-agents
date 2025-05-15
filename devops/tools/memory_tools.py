"""Tools for interacting with the persistent memory service."""

import logging
from typing import Any, Dict, List

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def add_memory_fact_tool(tool_context: ToolContext, entity_name: str, fact_content: str) -> str:
    """Adds a discrete fact to the memory service for the current session."""
    # Access services via _invocation_context
    invocation_context = getattr(tool_context, "_invocation_context", None)
    if not invocation_context:
        logger.error("Invocation context not found in tool context for add_memory_fact.")
        return "Error: Invocation context unavailable."

    memory_service = getattr(invocation_context, "memory_service", None)
    # Session ID might be available directly on session object within invocation_context?
    # Let's check for session first, then session_id directly
    session = getattr(invocation_context, "session", None)
    session_id = getattr(session, "id", None) if session else None
    if not session_id:
        # Fallback: check if session_id is directly on invocation_context (less likely)
        session_id = getattr(invocation_context, "session_id", None)

    # --- Remove Debug --- #
    # logger.warning(f"Inspecting tool_context in add_memory_fact_tool:")
    # try:
    #     context_vars = vars(tool_context)
    #     logger.warning(f"vars(tool_context): {context_vars}")
    # except TypeError:
    #     logger.warning("vars() failed, likely no __dict__. Trying dir():")
    #     context_dir = dir(tool_context)
    #     logger.warning(f"dir(tool_context): {context_dir}")
    # --- End Debug ---

    # Old access method:
    # memory_service = getattr(tool_context, "memory_service", None)
    # session_id = getattr(tool_context, "session_id", None)

    if not memory_service:
        logger.error("Memory service not available in invocation context for add_memory_fact.")
        return "Error: Memory service is not available."
    if not session_id:
        logger.error("Session ID not available in invocation context for add_memory_fact.")
        return "Error: Session ID is not available."

    # Check if add_observations method exists (duck typing)
    if not hasattr(memory_service, "add_observations") or not callable(memory_service.add_observations):
        logger.error("Memory service does not support 'add_observations'.")
        return "Error: Memory service does not support adding observations."

    try:
        # Structure the observation as a dictionary
        observation = {"entity": entity_name, "content": fact_content}
        logger.info(f"Adding memory fact for session {session_id}: {observation}")
        # Call the underlying service method
        memory_service.add_observations(session_id=session_id, observations=[observation])
        return f"Okay, I have remembered that {entity_name} is {fact_content}."

    except Exception as e:
        logger.exception(f"Error calling memory_service.add_observations: {e}")
        return f"Error: Failed to add fact to memory - {e}"


def search_memory_facts_tool(tool_context: ToolContext, query: str) -> List[Dict[str, Any]]:
    """Searches discrete facts in the memory service for the current session."""
    # Access services via _invocation_context
    invocation_context = getattr(tool_context, "_invocation_context", None)
    if not invocation_context:
        logger.error("Invocation context not found in tool context for search_memory_facts.")
        return [{"error": "Invocation context unavailable."}]

    memory_service = getattr(invocation_context, "memory_service", None)
    session = getattr(invocation_context, "session", None)
    session_id = getattr(session, "id", None) if session else None
    if not session_id:
        session_id = getattr(invocation_context, "session_id", None)

    # Old access method:
    # memory_service = getattr(tool_context, "memory_service", None)
    # session_id = getattr(tool_context, "session_id", None)

    if not memory_service:
        logger.error("Memory service not available in invocation context for search_memory_facts.")
        return [{"error": "Memory service is not available."}]
    if not session_id:
        logger.error("Session ID not available in invocation context for search_memory_facts.")
        return [{"error": "Session ID is not available."}]

    # Check if search_nodes method exists (duck typing)
    if not hasattr(memory_service, "search_nodes") or not callable(memory_service.search_nodes):
        logger.error("Memory service does not support 'search_nodes'.")
        return [{"error": "Memory service does not support searching facts (nodes)."}]

    try:
        logger.info(f"Searching memory facts for session {session_id} with query: '{query}'")
        results = memory_service.search_nodes(session_id=session_id, query=query)
        # Return the list of dictionaries directly
        # The agent's prompt will need to guide it on interpreting this list
        return results

    except Exception as e:
        logger.exception(f"Error calling memory_service.search_nodes: {e}")
        return [{"error": f"Failed to search facts in memory - {e}"}]


# Wrap functions with FunctionTool
add_memory_fact = FunctionTool(add_memory_fact_tool)
search_memory_facts = FunctionTool(search_memory_facts_tool)
