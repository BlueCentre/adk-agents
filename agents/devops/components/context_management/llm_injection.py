"""Injection point for context management in LlmAgent."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from google.genai import types as genai_types

# Set up logging
logger = logging.getLogger(__name__)


def get_last_user_content(llm_request: LlmRequest) -> Optional[str]:
    """Extract the last user message from an LLM request.

    Args:
        llm_request: The LLM request object

    Returns:
        The text of the last user content, or None if not found
    """
    if not llm_request.contents:
        return None

    # Loop through contents in reverse to find the last user message
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    return part.text
    return None


def inject_structured_context(llm_request: LlmRequest, context_dict: dict[str, Any]) -> LlmRequest:
    """Inject structured context into an LLM request.

    This modifies the request to include structured context before the user's messages.

    Args:
        llm_request: The original LLM request
        context_dict: The structured context dictionary

    Returns:
        The modified LLM request
    """
    if not llm_request.contents:
        logger.warning("No contents in LLM request, cannot inject context")
        return llm_request

    # Create a new content object with the structured context
    # Use compact JSON for token efficiency
    context_json = json.dumps(context_dict, separators=(",", ":"))

    # More concise preamble
    context_message = f"""SYSTEM CONTEXT (JSON):
```json
{context_json}
```
Use this context to inform your response. Do not directly refer to this context block."""

    context_content = genai_types.Content(
        role="user",  # Still using 'user' role as it's a common and effective way to inject context
        parts=[genai_types.Part(text=context_message)],
    )

    # Find the right position to insert our context
    # We want it after system messages but before the first non-system message that isn't our own context block
    first_non_system_idx = 0
    for i, content in enumerate(llm_request.contents):
        if content.role != "system":
            # Avoid inserting multiple times if this function is called repeatedly on the same request
            if content.parts and content.parts[0].text.startswith("SYSTEM CONTEXT (JSON):"):
                logger.debug("Context block already present, replacing.")
                new_contents = list(llm_request.contents)
                new_contents[i] = context_content  # Replace existing context block
                return LlmRequest(
                    model=llm_request.model, contents=new_contents, config=llm_request.config
                )
            first_non_system_idx = i
            break
    else:  # If only system messages exist or no messages at all (though we checked for empty contents)
        first_non_system_idx = len(llm_request.contents)

    # Create a new list of contents with our context inserted
    new_contents = llm_request.contents[:first_non_system_idx]
    new_contents.append(context_content)
    new_contents.extend(llm_request.contents[first_non_system_idx:])

    # Create a new request object with the modified contents
    return LlmRequest(model=llm_request.model, contents=new_contents, config=llm_request.config)
