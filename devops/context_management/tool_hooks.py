"""Tool hooks for context management in agent loop."""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from .context_manager import ContextManager
from .file_tracker import file_change_tracker

# Set up logging
logger = logging.getLogger(__name__)

def process_read_file_results(
    context_manager: ContextManager, 
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process read_file tool results and extract code snippets.
    
    Args:
        context_manager: The context manager instance
        tool: The tool that was executed
        result: The result from the tool
    """
    if not result.get("content"):
        return
        
    if "target_file" not in result:
        logger.warning("read_file result missing target_file field")
        return
        
    file_path = result["target_file"]
    content = result["content"]
    
    # Register this file with the file change tracker
    file_change_tracker.register_file_read(file_path, content)
    
    # Extract line numbers if available
    start_line = result.get("start_line", 1)
    end_line = result.get("end_line", start_line + content.count('\n'))
    
    # Add the entire content as a code snippet
    context_manager.add_code_snippet(
        file_path=file_path,
        code=content,
        start_line=start_line,
        end_line=end_line
    )

def process_edit_file_results(
    context_manager: ContextManager, 
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process edit_file tool results.
    
    Args:
        context_manager: The context manager instance
        tool: The tool that was executed
        result: The result from the tool
    """
    if "target_file" not in result:
        logger.warning("edit_file result missing target_file field")
        return
        
    file_path = result["target_file"]
    
    # Track the file modification in context manager
    context_manager.track_file_modification(file_path)
    
    # If we have the content after edit, add it as a snippet and track changes
    if "content_after" in result:
        # Get the previous content if available
        old_content = ""
        if "content_before" in result:
            old_content = result["content_before"]
        
        new_content = result["content_after"]
        
        # Register the edit with the file change tracker
        changed = file_change_tracker.register_file_edit(file_path, new_content)
        
        # If content changed, try to identify modified functions
        if changed and old_content:
            try:
                modified_functions = file_change_tracker.extract_modified_functions(old_content, new_content)
                if modified_functions:
                    logger.info(f"Identified modified functions in {file_path}: {', '.join(modified_functions)}")
                    # We could use this information to add more specific code snippets or decision context
            except Exception as e:
                logger.warning(f"Error extracting modified functions: {e}")
        
        # Add the updated content as a code snippet
        context_manager.add_code_snippet(
            file_path=file_path,
            code=new_content,
            start_line=1,
            end_line=new_content.count('\n') + 1
        )

def process_codebase_search_results(
    context_manager: ContextManager, 
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process codebase_search tool results.
    
    Args:
        context_manager: The context manager instance
        tool: The tool that was executed
        result: The result from the tool
    """
    if "matches" not in result or not isinstance(result["matches"], list):
        return
        
    for match in result["matches"]:
        if "file" not in match or "content" not in match:
            continue
            
        file_path = match["file"]
        content = match["content"]
        
        # Extract line numbers if available, otherwise use placeholders
        start_line = match.get("start_line", 1)
        end_line = match.get("end_line", start_line + content.count('\n'))
        
        # Add the match as a code snippet
        context_manager.add_code_snippet(
            file_path=file_path,
            code=content,
            start_line=start_line,
            end_line=end_line
        )

def process_execute_shell_command_results(
    context_manager: ContextManager, 
    tool: BaseTool, 
    result: Dict[str, Any]
) -> None:
    """Process shell command execution results.
    
    Args:
        context_manager: The context manager instance
        tool: The tool that was executed
        result: The result from the tool
    """
    # For shell commands, we're mainly interested in summarizing the output
    if "stdout" in result or "stderr" in result:
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        command = result.get("command_executed", "Unknown command")
        
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
            
        # Override the automatic summary generation with our custom one
        context_manager.add_tool_result(
            tool_name=tool.name,
            result=result,
            summary=summary
        )
        return True  # Signal that we've handled the summary
    
    return False  # Let default handling occur

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

def process_user_message(context_manager: ContextManager, message: str) -> None:
    """Process a user message to extract goals and context.
    
    Args:
        context_manager: The context manager instance
        message: The user's message
    """
    # Try to extract the user's goal
    goal = extract_goal_from_user_message(message)
    if goal:
        # Update the core goal if it seems like a new task
        if not context_manager.state.core_goal or len(message) > 100:
            context_manager.update_goal(goal)
            
    # Start a new conversation turn with this message
    context_manager.start_new_turn(user_message=message) 