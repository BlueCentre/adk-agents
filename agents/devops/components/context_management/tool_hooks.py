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

def _add_snippet_to_state(code_snippets: List[Dict], file_path: str, content: str, 
                         start_line: int, end_line: int, relevance_score: float) -> None:
    """Helper function to add or update a code snippet in the state."""
    # Check if snippet already exists to update last_accessed/relevance
    found = False
    for snippet in code_snippets:
        if snippet.get('file_path') == file_path and \
           snippet.get('start_line') == start_line and \
           snippet.get('end_line') == end_line:
            # Update existing snippet
            snippet['relevance_score'] = snippet.get('relevance_score', 1.0) + 0.3
            snippet['code'] = content  # Update with latest content
            found = True
            break

    if not found:
        new_snippet = {
            'file_path': file_path,
            'code': content,
            'start_line': start_line,
            'end_line': end_line,
            'last_accessed': 0, # Placeholder, needs current turn info from context
            'relevance_score': relevance_score,
            # Token count will happen during context assembly
        }
        code_snippets.append(new_snippet)

def process_read_file_results(
    state: Dict[str, Any], # Accept state dictionary
    tool: BaseTool, 
    result: Any  # Changed from Dict to Any to handle CallToolResult
) -> None:
    """Process read_file tool results and extract code snippets.
    
    Args:
        state: The context state dictionary
        tool: The tool that was executed
        result: The result from the tool (could be CallToolResult or dict)
    """
    if not state:
        logger.warning("State not available for process_read_file_results.")
        return
        
    # Debug logging to understand MCP structure
    logger.info(f"DEBUG: Tool hook received result type: {type(result)}")
    logger.info(f"DEBUG: Tool object type: {type(tool)}, tool.name: {getattr(tool, 'name', 'NO_NAME')}")
    if hasattr(tool, 'args'):
        logger.info(f"DEBUG: Tool args type: {type(tool.args)}, value: {tool.args}")
        if hasattr(tool.args, '__dict__'):
            logger.info(f"DEBUG: Tool args attributes: {tool.args.__dict__}")
    if hasattr(result, '__dict__'):
        logger.info(f"DEBUG: Result attributes: {list(result.__dict__.keys())}")
        logger.info(f"DEBUG: Result content preview: {getattr(result, 'content', 'NO_CONTENT')[:200] if hasattr(result, 'content') else 'NO_CONTENT'}")
        
    # Handle both MCP CallToolResult and dictionary formats
    content = None
    file_path = None
    
    # Try the most direct approach first
    if hasattr(result, 'content'):
        # Direct content attribute
        content_obj = result.content
        logger.info(f"DEBUG: Found direct content attribute, type: {type(content_obj)}")
        if isinstance(content_obj, list) and len(content_obj) > 0:
            # Extract text from the first content item
            content_item = content_obj[0]
            if hasattr(content_item, 'text'):
                content = content_item.text
            else:
                content = str(content_item)
        else:
            content = str(content_obj)
    elif hasattr(result, 'result') and hasattr(result.result, 'content'):
        # MCP CallToolResult format
        content_obj = result.result.content
        logger.info(f"DEBUG: Found result.result.content, type: {type(content_obj)}")
        if isinstance(content_obj, list) and len(content_obj) > 0:
            content = content_obj[0].text if hasattr(content_obj[0], 'text') else str(content_obj[0])
        else:
            content = str(content_obj)
    elif isinstance(result, dict):
        # Dictionary format (legacy)
        content = result.get("content")
        logger.info(f"DEBUG: Using dictionary format, content found: {bool(content)}")
    else:
        logger.warning(f"Unknown result format for process_read_file_results: {type(result)}")
        # Try to extract any string content as fallback
        if hasattr(result, '__str__'):
            content = str(result)
            logger.info(f"DEBUG: Fallback to string representation")
        else:
            return
    
    # Extract file path from tool arguments (most reliable)
    if hasattr(tool, 'args') and tool.args:
        # Try multiple ways to access tool args
        if isinstance(tool.args, dict):
            file_path = tool.args.get("path") or tool.args.get("filepath") or tool.args.get("target_file")
        else:
            # Try accessing as attributes
            file_path = getattr(tool.args, 'path', None) or getattr(tool.args, 'filepath', None) or getattr(tool.args, 'target_file', None)
    
    # Fallback: try to get from result
    if not file_path and isinstance(result, dict):
        file_path = result.get("filepath") or result.get("target_file") or result.get("path") or result.get("file")
        
    logger.info(f"DEBUG: Extracted - Content length: {len(content) if content else 0}, File path: {file_path}")
        
    if not content or not file_path:
        logger.warning(f"Missing content or file path for process_read_file_results. Content: {bool(content)}, Path: {bool(file_path)}")
        return
        
    try:
        # Register this file with the file change tracker (assuming file_tracker can operate without ContextManager instance)
        file_change_tracker.register_file_read(file_path, content)
        
        # Extract line numbers if available
        start_line = 1  # Default for MCP tools
        end_line = start_line + content.count('\n')
        
        # Add the entire content as a code snippet to state - be more inclusive with our massive token budget!
        code_snippets = state.get('app:code_snippets', [])
        if code_snippets is None:
            code_snippets = []
        
        # For full file reads, add the complete content as chunks to provide better context
        lines = content.split('\n')
        if end_line >= len(lines) - 5:  # Full or near-full file read
            # Split large files into overlapping chunks for better context
            if len(lines) > 100:
                chunk_size = 75  # Larger chunks with our token abundance
                overlap = 25   # Overlap for continuity
                for i in range(0, len(lines), chunk_size - overlap):
                    end_idx = min(i + chunk_size, len(lines))
                    chunk_content = '\n'.join(lines[i:end_idx])
                    _add_snippet_to_state(code_snippets, file_path, chunk_content, i + 1, end_idx, 1.2)
            else:
                # Small files - add as single snippet
                _add_snippet_to_state(code_snippets, file_path, content, start_line, end_line, 1.0)
        else:
            # Partial file read - add the specific section
            _add_snippet_to_state(code_snippets, file_path, content, start_line, end_line, 1.1)

        state['app:code_snippets'] = code_snippets
        logger.info(f"Enhanced code snippet capture from read_file: {file_path} ({len(lines)} lines)")
        
    except Exception as e:
        logger.error(f"Error processing read_file results for {file_path}: {e}", exc_info=True)

def process_edit_file_results(
    state: Dict[str, Any], # Accept state dictionary
    tool: BaseTool, 
    result: Any  # Changed from Dict to Any to handle CallToolResult
) -> None:
    """Process edit_file tool results.
    
    Args:
        state: The context state dictionary
        tool: The tool that was executed
        result: The result from the tool (could be CallToolResult or dict)
    """
    if not state:
        logger.warning("State not available for process_edit_file_results.")
        return
        
    # Debug logging to understand MCP structure
    logger.info(f"DEBUG EDIT: Tool hook received result type: {type(result)}")
    logger.info(f"DEBUG EDIT: Tool object type: {type(tool)}, tool.name: {getattr(tool, 'name', 'NO_NAME')}")
    if hasattr(tool, 'args'):
        logger.info(f"DEBUG EDIT: Tool args: {tool.args}")
    if hasattr(result, '__dict__'):
        logger.info(f"DEBUG EDIT: Result attributes: {list(result.__dict__.keys())}")
        
    # Extract file path from tool arguments (most reliable for edits)
    file_path = None
    if hasattr(tool, 'args'):
        file_path = tool.args.get("path") or tool.args.get("filepath") or tool.args.get("target_file")
        
    # Fallback: try to get from result if it's a dictionary
    if not file_path and isinstance(result, dict):
        file_path = result.get("filepath") or result.get("target_file") or result.get("path") or result.get("file")
        
    logger.info(f"DEBUG EDIT: Extracted file path: {file_path}")
        
    if not file_path:
        logger.warning(f"Missing file path for process_edit_file_results.")
        return
        
    try:
        # Track the file modification in state - be more generous with tracking
        last_modified_files = state.get('app:last_modified_files', [])
        if last_modified_files is None:
            last_modified_files = []
        if file_path not in last_modified_files:
            # With increased capacity, track up to 20 recently modified files
            if len(last_modified_files) >= 20:
                last_modified_files.pop(0)
            last_modified_files.append(file_path)
            state['app:last_modified_files'] = last_modified_files
        logger.info(f"Tracked file modification in state: {file_path}")
        
        # For write operations, we need to read the current content to track changes
        # Since MCP write_file doesn't provide before/after content, we'll read it
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                new_content = f.read()
                logger.info(f"DEBUG EDIT: Read current file content, length: {len(new_content)}")
        except Exception as e:
            logger.warning(f"Could not read file content after write: {e}")
            return
        
        # Register the edit with the file change tracker
        changed = file_change_tracker.register_file_edit(file_path, new_content)
        
        # Add the new content as code snippets for context
        code_snippets = state.get('app:code_snippets', [])
        if code_snippets is None:
            code_snippets = []
        
        # Remove old snippets for this file to avoid duplication
        code_snippets = [s for s in code_snippets if s.get('file_path') != file_path]
        
        # Add new content as primary snippet
        lines = new_content.split('\n')
        if len(lines) > 100:
            # Split large files into chunks
            chunk_size = 75
            overlap = 25
            for i in range(0, len(lines), chunk_size - overlap):
                end_idx = min(i + chunk_size, len(lines))
                chunk_content = '\n'.join(lines[i:end_idx])
                _add_snippet_to_state(code_snippets, file_path, chunk_content, i + 1, end_idx, 1.5)
        else:
            # Small files - add as single snippet with high relevance
            _add_snippet_to_state(code_snippets, file_path, new_content, 1, len(lines), 1.5)
            
        state['app:code_snippets'] = code_snippets
        logger.info(f"Enhanced code snippet capture from edit_file: {file_path} ({len(lines)} lines)")
        
    except Exception as e:
        logger.error(f"Error processing edit_file results for {file_path}: {e}", exc_info=True)

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
    """
    if not state:
        logger.warning("State not available for process_execute_shell_command_results.")
        return

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

        logger.info(f"Enhanced shell command result capture: {command[:50]}...")
    
    # Always return None for consistency with other processors

# Map of tool names to processing functions
TOOL_PROCESSORS = {
    # Disabled custom tools (keeping for backward compatibility if re-enabled)
    "read_file_content": process_read_file_results,
    "edit_file_content": process_edit_file_results,
    
    # Standard MCP filesystem tool names
    "read_file": process_read_file_results,
    "edit_file": process_edit_file_results,
    "write_file": process_edit_file_results,  # Alternative MCP name
    
    # Other tools
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