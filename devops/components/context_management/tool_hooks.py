"""Tool hooks for context management in agent loop."""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from google.adk.tools.base_tool import BaseTool
# from google.adk.tools.tool_context import ToolContext # Not needed if passing state directly

# from .context_manager import ContextManager # Not needed if operating on state dict directly
from .file_tracker import file_change_tracker

# Set up logging
logger = logging.getLogger(__name__)

def process_read_file_results(
    state: Dict[str, Any], # Accept state dictionary
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process read_file tool results and extract code snippets.
    
    Args:
        state: The context state dictionary
        tool: The tool that was executed
        result: The result from the tool
    """
    if not state or not result.get("content"):
        logger.warning("State or result content not available for process_read_file_results.")
        return
        
    if "target_file" not in result:
        logger.warning("read_file result missing target_file field")
        return
        
    file_path = result["target_file"]
    content = result["content"]
    
    # Register this file with the file change tracker (assuming file_tracker can operate without ContextManager instance)
    file_change_tracker.register_file_read(file_path, content)
    
    # Extract line numbers if available
    start_line = result.get("start_line", 1)
    end_line = result.get("end_line", start_line + content.count('\n'))
    
    # Add the entire content as a code snippet to state
    code_snippets = state.get('app:code_snippets', [])
    # Check if snippet already exists to update last_accessed/relevance
    found = False
    for snippet in code_snippets:
        if snippet.get('file_path') == file_path and \
           snippet.get('start_line') == start_line and \
           snippet.get('end_line') == end_line:
            # Assuming current turn number is available in state or context
            # For now, just update relevance score - last_accessed needs context
            snippet['relevance_score'] = snippet.get('relevance_score', 1.0) + 0.2
            found = True
            break

    if not found:
        new_snippet = {
            'file_path': file_path,
            'code': content,
            'start_line': start_line,
            'end_line': end_line,
            'last_accessed': 0, # Placeholder, needs current turn info from context
            'relevance_score': 1.0,
             # Token count should ideally be calculated here, but we need a token counter instance.
             # For now, just store the data. Token counting will happen during context assembly.
        }
        code_snippets.append(new_snippet)

    state['app:code_snippets'] = code_snippets
    logger.debug(f"Added code snippet to state from read_file: {file_path}")

def process_edit_file_results(
    state: Dict[str, Any], # Accept state dictionary
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process edit_file tool results.
    
    Args:
        state: The context state dictionary
        tool: The tool that was executed
        result: The result from the tool
    """
    if not state or "target_file" not in result:
        logger.warning("State or target_file not available for process_edit_file_results.")
        return
        
    file_path = result["target_file"]
    
    # Track the file modification in state
    last_modified_files = state.get('app:last_modified_files', [])
    if file_path not in last_modified_files:
        last_modified_files.append(file_path)
        state['app:last_modified_files'] = last_modified_files
    logger.debug(f"Tracked file modification in state: {file_path}")
    
    # If we have the content after edit, add it as a snippet and track changes
    if "content_after" in result:
        # Get the previous content if available
        old_content = result.get("content_before", "")
        new_content = result["content_after"]
        
        # Register the edit with the file change tracker
        changed = file_change_tracker.register_file_edit(file_path, new_content)
        
        # If content changed, try to identify modified functions
        if changed and old_content:
            try:
                # file_change_tracker needs to be updated to work without ContextManager instance if it relies on it
                modified_functions = file_change_tracker.extract_modified_functions(old_content, new_content)
                if modified_functions:
                    logger.info(f"Identified modified functions in {file_path}: {', '.join(modified_functions)}")
                    # We could use this information to add more specific code snippets or decision context to state
            except Exception as e:
                logger.warning(f"Error extracting modified functions: {e}")
        
        # Add the updated content as a code snippet to state
        code_snippets = state.get('app:code_snippets', [])
        # Remove old snippet for this file if it exists
        code_snippets = [s for s in code_snippets if not (s.get('file_path') == file_path and s.get('start_line') == 1)] # Assuming edit replaces full file
        
        new_snippet = {
            'file_path': file_path,
            'code': new_content,
            'start_line': 1,
            'end_line': new_content.count('\n') + 1,
            'last_accessed': 0, # Placeholder
            'relevance_score': 1.0,
             # Token count will happen during context assembly
        }
        code_snippets.append(new_snippet)
        state['app:code_snippets'] = code_snippets
        logger.debug(f"Updated code snippet in state from edit_file: {file_path}")

def process_codebase_search_results(
    state: Dict[str, Any], # Accept state dictionary
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process codebase_search tool results.
    
    Args:
        state: The context state dictionary
        tool: The tool that was executed
        result: The result from the tool
    """
    if not state or "matches" not in result or not isinstance(result["matches"], list):
        logger.warning("State or search results not available for process_codebase_search_results.")
        return
        
    code_snippets = state.get('app:code_snippets', [])
    for match in result["matches"]:
        if "file" not in match or "content" not in match:
            continue
            
        file_path = match["file"]
        content = match["content"]
        
        # Extract line numbers if available, otherwise use placeholders
        start_line = match.get("start_line", 1)
        end_line = match.get("end_line", start_line + content.count('\n'))
        
        # Check if snippet already exists to update last_accessed/relevance
        found = False
        for snippet in code_snippets:
            if snippet.get('file_path') == file_path and \
               snippet.get('start_line') == start_line and \
               snippet.get('end_line') == end_line:
                # Assuming current turn number is available in state or context
                 snippet['relevance_score'] = snippet.get('relevance_score', 1.0) + 0.1 # Slightly lower relevance boost than direct read/edit
                 found = True
                 break

        if not found:
            new_snippet = {
                'file_path': file_path,
                'code': content,
                'start_line': start_line,
                'end_line': end_line,
                'last_accessed': 0, # Placeholder
                'relevance_score': match.get('score', 1.0), # Use search score if available
                # Token count will happen during context assembly
            }
            code_snippets.append(new_snippet)

    state['app:code_snippets'] = code_snippets
    logger.debug(f"Added {len(result['matches'])} code snippets to state from codebase_search.")

def process_execute_shell_command_results(
    state: Dict[str, Any], # Accept state dictionary
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process shell command execution results.
    
    Args:
        state: The context state dictionary
        tool: The tool that was executed
        result: The result from the tool
    
    Returns:
        True if the summary was handled, False otherwise.
    """
    if not state:
        logger.warning("State not available for process_execute_shell_command_results.")
        return False

    # For shell commands, we're mainly interested in summarizing the output
    if "stdout" in result or "stderr" in result:
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        command = result.get("command_executed", result.get('command', 'Unknown command')) # Also check for 'command' key
        
        # Create a summary of the command output
        summary = f"Command: {command}\n"
        if stdout:
            # Truncate long output
            if len(stdout) > 500:
                summary += f"stdout (truncated): {stdout[:250]}...{stdout[-250:]}\n"
            else:
                summary += f"stdout: {stdout}\n"
                
        if stderr:
            summary += f"stderr: {stderr}\n"
            
        # Add the tool result to the temporary state for the current turn
        tool_results = state.get('temp:tool_results_current_turn', [])
        if tool_results is None: # Ensure it's a list
             tool_results = []

        tool_results.append({
             'tool_name': tool.name,
             'response': result, # Store the full result
             'summary': summary, # Store the custom summary
             # is_error and turn_number will be added when integrating into history
        })
        state['temp:tool_results_current_turn'] = tool_results

        logger.debug(f"Added shell command result summary to state: {command[:50]}...")
        return True  # Signal that we've handled the summary
    
    return False  # Let default handling occur if no stdout/stderr

# Map of tool names to processing functions
TOOL_PROCESSORS = {
    "read_file": process_read_file_results,
    "edit_file": process_edit_file_results,
    "codebase_search": process_codebase_search_results,
    "execute_vetted_shell_command": process_execute_shell_command_results,
}

def extract_goal_from_user_message(message: str) -> Optional[str]:
    """Attempt to extract the user's core goal from their message.
    
    Args:
        message: The user's message
        
    Returns:
        The extracted goal, or None if not found
    """
    # Look for patterns that typically indicate user goals
    goal_indicators = [
        r"(?:can you|could you|please|help me|I want to|I need to|I'd like to) (.*?)(?:\?|$|\.)",
        r"(?:How do I|How can I|What's the best way to) (.*?)(?:\?|$|\.)",
        r"(?:I'm trying to) (.*?)(?:\?|$|\.)",
    ]
    
    for pattern in goal_indicators:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no patterns match, use the first sentence as a fallback
    first_sentence = message.split('. ')[0].split('? ')[0].split('! ')[0]
    if len(first_sentence) > 10:  # Only use if it's reasonably long
        return first_sentence
        
    return None

# Removed process_user_message as it is now handled in devops_agent.py
# def process_user_message(context_manager: ContextManager, message: str) -> None:
#     """Process a user message to extract goals and context.
    
#     Args:
#         context_manager: The context manager instance
#         message: The user's message
#     """
#     # Try to extract the user's goal
#     goal = extract_goal_from_user_message(message)
#     if goal:
#         # Update the core goal if it seems like a new task
#         if not context_manager.state.core_goal or len(message) > 100:
#             context_manager.update_goal(goal)
            
#     # Start a new conversation turn with this message
#     context_manager.start_new_turn(user_message=message) 