"""Context management for agent loop to optimize token usage while preserving quality."""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple
import json
from rich.console import Console

# Set up logging
logger = logging.getLogger(__name__)

class ContextPriority(Enum):
    """Priority levels for context elements."""
    CRITICAL = auto()  # Always include (core goal, latest user message)
    HIGH = auto()      # Include unless absolutely necessary to trim (recent conversation)
    MEDIUM = auto()    # Include if space permits (relevant code snippets)
    LOW = auto()       # First to be trimmed (older tool outputs, older conversation)

@dataclass
class CodeSnippet:
    """Represents a code snippet relevant to the current conversation."""
    file_path: str
    code: str
    start_line: int
    end_line: int
    last_accessed: int  # Turn number when this was last relevant
    relevance_score: float = 1.0  # Higher means more relevant

@dataclass
class ToolResult:
    """Represents a summarized tool execution result."""
    tool_name: str
    result_summary: str
    full_result: Any  # The original result
    turn_number: int
    is_error: bool = False
    relevance_score: float = 1.0

@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    turn_number: int
    user_message: Optional[str] = None
    agent_message: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ContextState:
    """Tracks the current state of the conversation/task."""
    core_goal: str = ""
    current_phase: str = ""
    key_decisions: List[str] = field(default_factory=list)
    last_modified_files: List[str] = field(default_factory=list)

class ContextManager:
    """Manages the context for the agent loop, optimizing token usage."""
    
    def __init__(self, 
                 max_token_limit: int = 100000,
                 recent_turns_to_keep: int = 5,
                 max_code_snippets: int = 10,
                 max_tool_results: int = 20):
        """Initialize the context manager.
        
        Args:
            max_token_limit: Maximum tokens to include in context
            recent_turns_to_keep: Number of recent conversation turns to always keep
            max_code_snippets: Maximum number of code snippets to track
            max_tool_results: Maximum number of tool results to track
        """
        self.max_token_limit = max_token_limit
        self.recent_turns_to_keep = recent_turns_to_keep
        self.max_code_snippets = max_code_snippets
        self.max_tool_results = max_tool_results
        
        # Initialize context components
        self.state = ContextState()
        self.conversation_turns: List[ConversationTurn] = []
        self.code_snippets: List[CodeSnippet] = []
        self.tool_results: List[ToolResult] = []
        self.current_turn_number = 0
        self.console = Console(stderr=True)
        
    def start_new_turn(self, user_message: Optional[str] = None) -> int:
        """Start a new conversation turn.
        
        Args:
            user_message: The user's message for this turn
            
        Returns:
            The turn number
        """
        self.current_turn_number += 1
        turn = ConversationTurn(
            turn_number=self.current_turn_number,
            user_message=user_message
        )
        self.conversation_turns.append(turn)
        return self.current_turn_number
    
    def update_agent_response(self, turn_number: int, agent_message: str) -> None:
        """Update the agent's response for a given turn.
        
        Args:
            turn_number: The turn number to update
            agent_message: The agent's response
        """
        for turn in self.conversation_turns:
            if turn.turn_number == turn_number:
                turn.agent_message = agent_message
                return
        logger.warning(f"Turn {turn_number} not found when updating agent response")
    
    def add_tool_call(self, turn_number: int, tool_name: str, args: Dict[str, Any]) -> None:
        """Add a tool call to the given turn.
        
        Args:
            turn_number: The turn number
            tool_name: Name of the tool called
            args: Arguments passed to the tool
        """
        for turn in self.conversation_turns:
            if turn.turn_number == turn_number:
                turn.tool_calls.append({
                    "tool_name": tool_name,
                    "args": args
                })
                return
        logger.warning(f"Turn {turn_number} not found when adding tool call")
    
    def update_goal(self, goal: str) -> None:
        """Update the core goal/task.
        
        Args:
            goal: The new goal description
        """
        self.state.core_goal = goal
        logger.info(f"Updated core goal: {goal}")
    
    def update_phase(self, phase: str) -> None:
        """Update the current phase of work.
        
        Args:
            phase: Description of the current phase
        """
        self.state.current_phase = phase
        logger.info(f"Updated current phase: {phase}")
    
    def add_key_decision(self, decision: str) -> None:
        """Add a key decision to the state.
        
        Args:
            decision: Description of the decision made
        """
        self.state.key_decisions.append(decision)
        logger.info(f"Added key decision: {decision}")
    
    def add_code_snippet(self, file_path: str, code: str, start_line: int, end_line: int) -> None:
        """Add a relevant code snippet.
        
        Args:
            file_path: Path to the file
            code: The code content
            start_line: Starting line number
            end_line: Ending line number
        """
        # Check if we already have this snippet
        for i, snippet in enumerate(self.code_snippets):
            if (snippet.file_path == file_path and 
                snippet.start_line == start_line and 
                snippet.end_line == end_line):
                # Update existing snippet's access time and bump relevance
                self.code_snippets[i].last_accessed = self.current_turn_number
                self.code_snippets[i].relevance_score += 0.2
                return
        
        # Add new snippet
        new_snippet = CodeSnippet(
            file_path=file_path,
            code=code,
            start_line=start_line,
            end_line=end_line,
            last_accessed=self.current_turn_number
        )
        
        # If we're at capacity, remove the least relevant snippet
        if len(self.code_snippets) >= self.max_code_snippets:
            # Sort by relevance and recency
            self.code_snippets.sort(key=lambda s: (s.relevance_score, s.last_accessed))
            self.code_snippets.pop(0)  # Remove least relevant
            
        self.code_snippets.append(new_snippet)
        logger.info(f"Added code snippet from {file_path} ({start_line}-{end_line})")
    
    def add_tool_result(self, tool_name: str, result: Any, summary: Optional[str] = None) -> None:
        """Add a tool execution result.
        
        Args:
            tool_name: Name of the tool
            result: The full result from the tool
            summary: Optional summary of the result (will be generated if None)
        """
        # Generate summary if not provided
        if summary is None:
            summary = self._generate_tool_result_summary(tool_name, result)
            
        is_error = False
        if isinstance(result, dict) and (result.get("status") == "error" or result.get("error")):
            is_error = True
            
        new_result = ToolResult(
            tool_name=tool_name,
            result_summary=summary,
            full_result=result,
            turn_number=self.current_turn_number,
            is_error=is_error
        )
        
        # If we're at capacity, remove the oldest tool result
        if len(self.tool_results) >= self.max_tool_results:
            # Sort by turn number (oldest first)
            self.tool_results.sort(key=lambda r: r.turn_number)
            self.tool_results.pop(0)  # Remove oldest
            
        self.tool_results.append(new_result)
        logger.info(f"Added tool result for {tool_name}")
    
    def _generate_tool_result_summary(self, tool_name: str, result: Any) -> str:
        """Generate a summary of a tool result.
        
        Args:
            tool_name: Name of the tool
            result: The result to summarize
            
        Returns:
            A summary string
        """
        # Handle different tool types
        if tool_name == "read_file":
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                # Get first 50 and last 50 characters for the summary
                if len(content) > 200:
                    return f"File content (truncated): {content[:100]}...{content[-100:]}"
                else:
                    return f"File content: {content}"
        elif tool_name in ["codebase_search", "grep_search"]:
            if isinstance(result, dict) and "matches" in result:
                match_count = len(result["matches"])
                return f"Found {match_count} matches in codebase"
        
        # Default handling for other tool results
        if isinstance(result, dict):
            # Try to create a concise representation
            important_keys = ["status", "message", "summary", "error"]
            summary_parts = []
            
            for key in important_keys:
                if key in result:
                    summary_parts.append(f"{key}: {result[key]}")
                    
            if summary_parts:
                return "; ".join(summary_parts)
            else:
                # Fallback to a truncated string representation
                result_str = str(result)
                if len(result_str) > 200:
                    return result_str[:200] + "..."
                return result_str
        else:
            # For non-dict results, just truncate if needed
            result_str = str(result)
            if len(result_str) > 200:
                return result_str[:200] + "..."
            return result_str
    
    def track_file_modification(self, file_path: str) -> None:
        """Track a file that has been modified.
        
        Args:
            file_path: Path to the modified file
        """
        if file_path not in self.state.last_modified_files:
            # Keep last 5 modified files
            if len(self.state.last_modified_files) >= 5:
                self.state.last_modified_files.pop(0)
            self.state.last_modified_files.append(file_path)
    
    def assemble_context(self) -> Tuple[Dict[str, Any], int]:
        """Assemble the full context for the language model.
        
        Returns:
            Tuple of (context_dict, estimated_token_count)
        """
        # Start with state information
        context = {
            "core_goal": self.state.core_goal,
            "current_phase": self.state.current_phase,
            "key_decisions": self.state.key_decisions[-5:] if self.state.key_decisions else [],
            "recent_modified_files": self.state.last_modified_files
        }
        
        # Add recent conversation turns
        if self.conversation_turns:
            recent_turns = self.conversation_turns[-self.recent_turns_to_keep:]
            context["recent_conversation"] = [
                {
                    "turn": turn.turn_number,
                    "user": turn.user_message,
                    "agent": turn.agent_message,
                    "tool_calls": turn.tool_calls
                }
                for turn in recent_turns
            ]
        
        # Add relevant code snippets (sort by relevance and recency)
        self.code_snippets.sort(key=lambda s: (-s.relevance_score, -s.last_accessed))
        context["relevant_code"] = [
            {
                "file": snippet.file_path,
                "start_line": snippet.start_line,
                "end_line": snippet.end_line,
                "code": snippet.code
            }
            for snippet in self.code_snippets[:5]  # Include top 5 most relevant snippets
        ]
        
        # Add recent tool results (prioritize errors and recent results)
        # First include all error results from recent turns
        error_results = [r for r in self.tool_results 
                        if r.is_error and r.turn_number >= self.current_turn_number - 3]
        
        # Then add recent non-error results
        recent_results = [r for r in self.tool_results 
                         if not r.is_error and r.turn_number >= self.current_turn_number - 3]
        
        # Sort by turn number (newest first)
        recent_results.sort(key=lambda r: -r.turn_number)
        
        # Combine error and recent results, prioritizing errors
        tool_results_to_include = error_results + recent_results
        
        context["recent_tool_results"] = [
            {
                "tool": result.tool_name,
                "turn": result.turn_number,
                "summary": result.result_summary,
                "is_error": result.is_error
            }
            for result in tool_results_to_include[:10]  # Include up to 10 tool results
        ]
        
        # Estimate token count (very rough estimate)
        estimated_tokens = self._estimate_token_count(context)
        
        return context, estimated_tokens
    
    def _estimate_token_count(self, context: Dict[str, Any]) -> int:
        """Estimate the token count for the given context.
        
        This is a very rough estimate based on character count.
        For accurate counts, a proper tokenizer would be needed.
        
        Args:
            context: The context dictionary
            
        Returns:
            Estimated token count
        """
        # Serialize to string for estimation
        context_str = json.dumps(context)
        # Very rough estimate: ~1 token per 4 characters
        return len(context_str) // 4
    
    def get_relevant_code_for_file(self, file_path: str) -> List[CodeSnippet]:
        """Get all relevant code snippets for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of code snippets for the file
        """
        return [s for s in self.code_snippets if s.file_path == file_path] 