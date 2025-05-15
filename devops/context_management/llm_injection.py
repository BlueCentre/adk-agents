"""Injection point for context management in LlmAgent."""

import logging
from typing import Dict, List, Any, Optional, Union
import json

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext
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

def inject_structured_context(
    llm_request: LlmRequest, 
    context_dict: Dict[str, Any]
) -> LlmRequest:
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
    context_json = json.dumps(context_dict, indent=2)
    
    context_message = f"""
CONTEXT INFORMATION:
The following is important context about the current task and conversation:
```json
{context_json}
```
Use this context to inform your responses, but DO NOT directly refer to this context block.
"""
    
    context_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=context_message)]
    )
    
    # Find the right position to insert our context
    # We want it after system messages but before the first user message
    first_non_system_idx = 0
    for i, content in enumerate(llm_request.contents):
        if content.role != "system":
            first_non_system_idx = i
            break
    
    # Create a new list of contents with our context inserted
    new_contents = llm_request.contents[:first_non_system_idx]
    new_contents.append(context_content)
    new_contents.extend(llm_request.contents[first_non_system_idx:])
    
    # Create a new request object with the modified contents
    new_request = LlmRequest(
        model=llm_request.model,
        contents=new_contents,
        generation_config=llm_request.generation_config
    )
    
    return new_request 