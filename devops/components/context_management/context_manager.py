"""Context management for agent loop to optimize token usage while preserving quality."""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple, Callable
import json
from rich.console import Console

from google import genai
from google.genai.types import Content, Part, CountTokensResponse # For native token counting
from .proactive_context import ProactiveContextGatherer
from .smart_prioritization import SmartPrioritizer
from .cross_turn_correlation import CrossTurnCorrelator

# Attempt to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken library not found. Token counting will be a rough estimate based on character count if native counter also fails.")

# Set up logging
logger = logging.getLogger(__name__)

class ContextPriority(Enum):
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()

@dataclass
class CodeSnippet:
    file_path: str
    code: str
    start_line: int
    end_line: int
    last_accessed: int
    relevance_score: float = 1.0
    token_count: int = 0

@dataclass
class ToolResult:
    tool_name: str
    result_summary: str
    full_result: Any
    turn_number: int
    is_error: bool = False
    relevance_score: float = 1.0
    token_count: int = 0

@dataclass
class ConversationTurn:
    turn_number: int
    user_message: Optional[str] = None
    agent_message: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    user_message_tokens: int = 0
    agent_message_tokens: int = 0
    tool_calls_tokens: int = 0

@dataclass
class ContextState:
    core_goal: str = ""
    current_phase: str = ""
    key_decisions: List[str] = field(default_factory=list)
    last_modified_files: List[str] = field(default_factory=list)
    core_goal_tokens: int = 0
    current_phase_tokens: int = 0

class ContextManager:
    def __init__(self, 
                 model_name: str,
                 max_llm_token_limit: int,
                 llm_client: Optional[genai.Client] = None, 
                 target_recent_turns: int = 20,
                 target_code_snippets: int = 25,
                 target_tool_results: int = 30,
                 max_stored_code_snippets: int = 100,
                 max_stored_tool_results: int = 150):
        self.model_name = model_name
        self.max_token_limit = max_llm_token_limit
        self.target_recent_turns = target_recent_turns
        self.target_code_snippets = target_code_snippets
        self.target_tool_results = target_tool_results
        self.max_stored_code_snippets = max_stored_code_snippets
        self.max_stored_tool_results = max_stored_tool_results
        
        # If llm_client is None, try to create one if possible
        if llm_client is None:
            try:
                import os
                from ... import config as agent_config
                # Create genai client with API key directly
                if agent_config.GOOGLE_API_KEY:
                    llm_client = genai.Client(api_key=agent_config.GOOGLE_API_KEY)
                    logger.info("Created genai client with API key from config in ContextManager")
                else:
                    llm_client = genai.Client()
                    logger.info("Created default genai client without explicit API key in ContextManager")
                logger.info("Created default genai client in ContextManager")
            except Exception as e:
                logger.warning(f"Could not create default genai client in ContextManager: {e}")
                # Continue with llm_client=None - we'll use fallback token counting strategies
        
        self.llm_client = llm_client
        self._token_counting_fn = self._initialize_token_counting_strategy()
        self.state = ContextState()
        self.conversation_turns: List[ConversationTurn] = []
        self.code_snippets: List[CodeSnippet] = []
        self.tool_results: List[ToolResult] = []
        self.current_turn_number = 0
        self.console = Console(stderr=True)
        self.system_messages: List[Tuple[str, int]] = []
        
        # Initialize proactive context gatherer and smart prioritizer
        self.proactive_gatherer = ProactiveContextGatherer()
        self._proactive_context_cache: Optional[Dict[str, Any]] = None
        self._proactive_context_tokens: int = 0
        
        # Initialize smart prioritizer and cross-turn correlator for Phase 2 enhancements
        self.smart_prioritizer = SmartPrioritizer()
        self.cross_turn_correlator = CrossTurnCorrelator()
        
        # Log detailed configuration information for optimization analysis
        self._log_configuration()

    def _log_configuration(self):
        """Log detailed ContextManager configuration for optimization analysis."""
        logger.info("=" * 60)
        logger.info("CONTEXTMANAGER CONFIGURATION LOADED")
        logger.info("=" * 60)
        logger.info(f"Model Name: {self.model_name}")
        logger.info(f"Max LLM Token Limit: {self.max_token_limit:,}")
        logger.info(f"Target Recent Turns: {self.target_recent_turns}")
        logger.info(f"Target Code Snippets: {self.target_code_snippets}")
        logger.info(f"Target Tool Results: {self.target_tool_results}")
        logger.info(f"Max Stored Code Snippets: {self.max_stored_code_snippets}")
        logger.info(f"Max Stored Tool Results: {self.max_stored_tool_results}")
        logger.info(f"LLM Client Type: {type(self.llm_client).__name__ if self.llm_client else 'None'}")
        logger.info(f"Token Counting Strategy: {self._token_counting_fn.__name__ if hasattr(self._token_counting_fn, '__name__') else 'lambda function'}")
        logger.info("=" * 60)

    def _initialize_token_counting_strategy(self) -> Callable[[str], int]:
        # Strategy 1: Native Google GenAI client's count_tokens
        if self.llm_client is not None and isinstance(self.llm_client, genai.Client) and \
           hasattr(self.llm_client, 'models') and hasattr(self.llm_client.models, 'count_tokens'):
            try:
                def native_google_counter(text: str) -> int:
                    try:
                        # For simple text, wrap in Content/Part structure
                        content_for_counting = Content(parts=[Part(text=text)])
                        # Call count_tokens via client.models
                        response: CountTokensResponse = self.llm_client.models.count_tokens(model=self.model_name, contents=content_for_counting)
                        return response.total_tokens
                    except Exception as e_native_call:
                        logger.debug(f"Native Google count_tokens call (via Content object) failed for model {self.model_name}: {e_native_call}. Attempting string directly.")
                        try: # Try with string directly as contents
                            response: CountTokensResponse = self.llm_client.models.count_tokens(model=self.model_name, contents=text)
                            return response.total_tokens
                        except Exception as e_native_str_call:
                            logger.warning(f"Native Google count_tokens (string direct) also failed for model {self.model_name}: {e_native_str_call}. Falling back.")
                            # Fall through to tiktoken if native fails unexpectedly
                            if TIKTOKEN_AVAILABLE:
                                try:
                                    tokenizer = tiktoken.get_encoding("cl100k_base")
                                    return len(tokenizer.encode(text))
                                except Exception as te:
                                    logger.error(f"Fallback to cl100k_base also failed: {te}")
                            return len(text) // 4 # Ultimate fallback

                # Perform a quick test call
                # Note: The 'contents' arg is used in the new SDK for count_tokens
                test_response = self.llm_client.models.count_tokens(model=self.model_name, contents="test")
                if isinstance(test_response, CountTokensResponse) and hasattr(test_response, 'total_tokens'):
                    logger.info(f"Using native Google GenAI token counter for model {self.model_name} (via google.genai client).")
                    return native_google_counter
                else:
                    logger.warning(f"Native Google count_tokens for {self.model_name} did not return expected response ({type(test_response)}). Falling back.")
            except Exception as e_init:
                logger.warning(f"Could not initialize or test native Google count_tokens for model {self.model_name}: {e_init}. Falling back.")
        else:
            if self.llm_client is None:
                logger.warning("llm_client is None - cannot use native token counter")
            elif not isinstance(self.llm_client, genai.Client):
                logger.warning(f"llm_client is not a genai.Client instance (got {type(self.llm_client).__name__})")
            elif not hasattr(self.llm_client, 'models') or not hasattr(self.llm_client.models, 'count_tokens'):
                logger.warning("llm_client does not have the required methods for token counting")

        # Strategy 2: Tiktoken
        if TIKTOKEN_AVAILABLE:
            tokenizer = None
            try:
                tokenizer = tiktoken.encoding_for_model(self.model_name)
                logger.info(f"Using tiktoken with model-specific encoding for {self.model_name}.")
            except KeyError: # Model not found in tiktoken
                try:
                    tokenizer = tiktoken.get_encoding("cl100k_base")
                    logger.info(f"Using tiktoken with cl100k_base encoding for {self.model_name} (model-specific not found).")
                except Exception as e_cl100k:
                    logger.error(f"Failed to get cl100k_base tokenizer: {e_cl100k}. Tiktoken unavailable for {self.model_name}.")
            
            if tokenizer:
                final_tokenizer = tokenizer
                return lambda text: len(final_tokenizer.encode(text))

        # Strategy 3: Character count fallback
        logger.warning(f"No advanced tokenizer available for {self.model_name}. Using character-based token estimation (len // 4).")
        return lambda text: len(text) // 4

    def _count_tokens(self, text: str) -> int:
        if not isinstance(text, str):
            logger.debug(f"Non-string type ({type(text)}) passed to _count_tokens. Converting to string for counting.")
            text = str(text)
        if not text: # Handle empty or None string
             return 0
        try:
            return self._token_counting_fn(text)
        except Exception as e:
            logger.error(f"Error during token counting for text '{text[:50]}...': {e}. Falling back to char count.", exc_info=True)
            return len(text) // 4

    def add_system_message(self, message: str):
        tokens = self._count_tokens(message)
        self.system_messages.append((message, tokens))
        logger.info(f"Added system message (tokens: {tokens}): {message[:100]}...")

    def start_new_turn(self, user_message: Optional[str] = None) -> int:
        self.current_turn_number += 1
        user_tokens = self._count_tokens(user_message) if user_message else 0
        turn = ConversationTurn(
            turn_number=self.current_turn_number,
            user_message=user_message,
            user_message_tokens=user_tokens
        )
        self.conversation_turns.append(turn)
        return self.current_turn_number
    
    def update_agent_response(self, turn_number: int, agent_message: str) -> None:
        for turn in self.conversation_turns:
            if turn.turn_number == turn_number:
                turn.agent_message = agent_message
                turn.agent_message_tokens = self._count_tokens(agent_message)
                return
        logger.warning(f"Turn {turn_number} not found when updating agent response")
    
    def add_tool_call(self, turn_number: int, tool_name: str, args: Dict[str, Any]) -> None:
        for turn in self.conversation_turns:
            if turn.turn_number == turn_number:
                call_data = {"tool_name": tool_name, "args": args}
                turn.tool_calls.append(call_data)
                turn.tool_calls_tokens += self._count_tokens(json.dumps(call_data))
                return
        logger.warning(f"Turn {turn_number} not found when adding tool call")
    
    def update_goal(self, goal: str) -> None:
        self.state.core_goal = goal
        self.state.core_goal_tokens = self._count_tokens(goal)
        logger.info(f"Updated core goal (tokens: {self.state.core_goal_tokens}): {goal}")
    
    def update_phase(self, phase: str) -> None:
        self.state.current_phase = phase
        self.state.current_phase_tokens = self._count_tokens(phase)
        logger.info(f"Updated current phase (tokens: {self.state.current_phase_tokens}): {phase}")
    
    def add_key_decision(self, decision: str) -> None:
        self.state.key_decisions.append(decision)
        logger.info(f"Added key decision: {decision}") # Tokens for list calculated on assembly
    
    def add_code_snippet(self, file_path: str, code: str, start_line: int, end_line: int) -> None:
        # Check for existing snippet at same location
        for i, snippet in enumerate(self.code_snippets):
            if (snippet.file_path == file_path and 
                snippet.start_line == start_line and 
                snippet.end_line == end_line):
                self.code_snippets[i].last_accessed = self.current_turn_number
                self.code_snippets[i].relevance_score += 0.2 
                logger.info(f"Updated existing code snippet: {file_path}:{start_line}-{end_line}")
                return
        
        new_snippet = CodeSnippet(
            file_path=file_path, code=code, start_line=start_line, end_line=end_line,
            last_accessed=self.current_turn_number, token_count=self._count_tokens(code)
        )
        if len(self.code_snippets) >= self.max_stored_code_snippets:
            self.code_snippets.sort(key=lambda s: (s.relevance_score, s.last_accessed))
            removed = self.code_snippets.pop(0)
            logger.debug(f"Removed code snippet due to store limit: {removed.file_path}")
        self.code_snippets.append(new_snippet)
        logger.info(f"Added code snippet from {file_path} ({start_line}-{end_line}), tokens: {new_snippet.token_count}")
    
    def add_full_file_content(self, file_path: str, content: str) -> None:
        """Add full file content as context when files are read/modified."""
        # With 1M+ tokens available, we can afford to include full file contents
        lines = content.split('\n')
        
        # For small files (< 100 lines), add as single snippet
        if len(lines) <= 100:
            self.add_code_snippet(file_path, content, 1, len(lines))
        else:
            # For larger files, add in chunks to maintain context
            chunk_size = 50  # lines per chunk
            for i in range(0, len(lines), chunk_size):
                end_idx = min(i + chunk_size, len(lines))
                chunk_content = '\n'.join(lines[i:end_idx])
                self.add_code_snippet(file_path, chunk_content, i + 1, end_idx)
        
        # Also track as modified file
        self.track_file_modification(file_path)
        logger.info(f"Added full file content for {file_path}: {len(lines)} lines, {len(content)} chars")

    def add_tool_result(self, tool_name: str, result: Any, summary: Optional[str] = None) -> None:
        if summary is None:
            summary = self._generate_tool_result_summary(tool_name, result)
            
        is_error = isinstance(result, dict) and (result.get("status") == "error" or result.get("error"))
        summary_tokens = self._count_tokens(summary)

        new_result = ToolResult(
            tool_name=tool_name, result_summary=summary, full_result=result,
            turn_number=self.current_turn_number, is_error=is_error, token_count=summary_tokens
        )
        if len(self.tool_results) >= self.max_stored_tool_results:
            self.tool_results.sort(key=lambda r: r.turn_number) 
            removed = self.tool_results.pop(0)
            logger.debug(f"Removed tool result due to store limit: {removed.tool_name}")
        self.tool_results.append(new_result)
        logger.info(f"Added tool result for {tool_name}, summary tokens: {summary_tokens}")

    def _generate_tool_result_summary(self, tool_name: str, result: Any) -> str:
        """Generate a summary of tool result with transformation logging."""
        summary = ""
        MAX_SUMMARY_LEN = 2000 # Increased from 500 - we have 1M+ tokens available!
        TRUNC_MSG_TEMPLATE = " (truncated due to length)"
        
        # Log the original content before transformation
        original_content = str(result)
        logger.info("=" * 50)
        logger.info("TOOL RESULT TRANSFORMATION")
        logger.info("=" * 50)
        logger.info(f"Tool Name: {tool_name}")
        logger.info(f"Original Result Type: {type(result).__name__}")
        logger.info(f"Original Content Size: {len(original_content):,} characters")
        logger.info(f"Original Content Preview: {original_content[:200]}...")

        if tool_name == "read_file_content" or tool_name == "read_file":
            if isinstance(result, dict) and result.get("status") == "success" and "content" in result:
                content = result["content"]
                if isinstance(content, str):
                    if any(kw in content for kw in ["def ", "class ", "import ", "function("]): 
                        summary = f"Read code file. Length: {len(content)} chars. Content (truncated): {content[:500]}...{content[-500:] if len(content) > 1000 else ''}"
                    else:
                        summary = f"Read file. Length: {len(content)} chars. Content (truncated): {content[:500]}...{content[-500:] if len(content) > 1000 else ''}"
                    
                    # Log transformation details for file content
                    logger.info(f"Transformation Type: File content summary")
                    logger.info(f"Original File Content Size: {len(content):,} characters")
                    logger.info(f"Content Type: {'Code file' if any(kw in content for kw in ['def ', 'class ', 'import ', 'function(']) else 'Text file'}")
                else:
                    summary = f"Read file, content type: {type(content).__name__}."
            elif isinstance(result, dict) and result.get("status") == "error":
                summary = f"Error reading file: {result.get('message', 'Unknown error')}"
            else:
                summary = f"Tool {tool_name} produced an unexpected result structure."
        elif tool_name == "execute_vetted_shell_command":
            if isinstance(result, dict):
                parts = [f"Shell command '{result.get('command_executed', 'unknown_command')}'"]
                if result.get('return_code') == 0:
                    parts.append(f"succeeded (rc=0).")
                else:
                    parts.append(f"failed (rc={result.get('return_code', 'N/A')}).")
                
                stdout = result.get('stdout')
                stderr = result.get('stderr')
                
                # Log shell command output transformation
                if stdout:
                    logger.info(f"Original Stdout Size: {len(stdout):,} characters")
                    if "[Output truncated" in stdout:
                        logger.info("Stdout Transformation: Already truncated by tool")
                        parts.append(f"Stdout was large and truncated. First/last parts: {stdout.split('\\n', 1)[-1]}") # Show after truncation message
                    else:
                        logger.info(f"Stdout Transformation: Truncating to {MAX_SUMMARY_LEN // 2} characters")
                        parts.append(f"Stdout: {stdout[:MAX_SUMMARY_LEN // 2]}") # Show more stdout with increased limits
                
                if stderr:
                    logger.info(f"Original Stderr Size: {len(stderr):,} characters")
                    if "[Output truncated" in stderr:
                        logger.info("Stderr Transformation: Already truncated by tool")
                        parts.append(f"Stderr was large and truncated. First/last parts: {stderr.split('\\n', 1)[-1]}")
                    else:
                        logger.info(f"Stderr Transformation: Truncating to {MAX_SUMMARY_LEN // 2} characters")
                        parts.append(f"Stderr: {stderr[:MAX_SUMMARY_LEN // 2]}")
                
                if not stdout and not stderr and result.get('return_code') == 0:
                    parts.append("No output on stdout or stderr.")
                elif not stdout and not stderr and result.get('return_code') != 0:
                     parts.append("No output on stdout or stderr, but command failed.")
                summary = " ".join(parts)
            else:
                summary = f"Tool {tool_name} (shell command) produced non-dict result: {str(result)[:100]}"
        elif tool_name in ["ripgrep_code_search", "retrieve_code_context_tool"]:
            if isinstance(result, dict):
                if "matches" in result and isinstance(result["matches"], list):
                    summary = f"Search returned {len(result['matches'])} matches."
                    logger.info(f"Search Result Transformation: Condensed {len(result['matches'])} matches to count summary")
                elif "retrieved_chunks" in result and isinstance(result["retrieved_chunks"], list):
                    summary = f"Retrieved {len(result['retrieved_chunks'])} code chunks."
                    logger.info(f"Code Retrieval Transformation: Condensed {len(result['retrieved_chunks'])} chunks to count summary")
                else:
                    summary = f"{tool_name} completed. Keys: {list(result.keys())}"
                    logger.info(f"Generic Dict Transformation: Listed keys only: {list(result.keys())}")
            else:
                summary = f"{tool_name} completed with non-dict result."
        else: 
            if isinstance(result, dict):
                important_keys = ["status", "message", "summary", "error", "output", "stdout", "stderr"]
                summary_parts = []
                logger.info(f"Generic Dict Transformation: Extracting important keys from {list(result.keys())}")
                for key in important_keys:
                    if key in result and result[key]:
                        val_str = str(result[key])
                        truncated_val = val_str[:300] + '...' if len(val_str) > 300 else val_str
                        summary_parts.append(f"{key}: {truncated_val}")
                        if len(val_str) > 300:
                            logger.info(f"  Key '{key}': Truncated from {len(val_str)} to 300 characters")
                        else:
                            logger.info(f"  Key '{key}': Kept full content ({len(val_str)} characters)")
                            
                if summary_parts:
                    summary = f"Tool {tool_name}: " + "; ".join(summary_parts)
                else:
                    original_str = str(result)
                    summary = f"Tool {tool_name} completed. Result (truncated): {original_str[:800]}..."  # Increased from 200
                    logger.info(f"Fallback Transformation: Truncated result from {len(original_str)} to 800 characters")
            elif isinstance(result, str):
                summary = f"Tool {tool_name} output (truncated): {result[:800]}..."  # Increased from 200
                logger.info(f"String Result Transformation: Truncated from {len(result)} to 800 characters")
            else:
                summary = f"Tool {tool_name} completed with result type: {type(result).__name__}."
                logger.info(f"Non-string Result Transformation: Converted {type(result).__name__} to type description")
        
        # Apply final length limit and log if truncated
        if len(summary) > MAX_SUMMARY_LEN: 
            original_summary_len = len(summary)
            summary = summary[:MAX_SUMMARY_LEN - len(TRUNC_MSG_TEMPLATE)] + TRUNC_MSG_TEMPLATE
            logger.info(f"Final Summary Transformation: Truncated from {original_summary_len} to {MAX_SUMMARY_LEN} characters")
        
        # Log the final transformed summary
        logger.info(f"Final Summary Size: {len(summary):,} characters")
        logger.info(f"Final Summary: {summary}")
        logger.info(f"Transformation Ratio: {(len(summary) / len(original_content) * 100):.1f}% of original")
        logger.info("=" * 50)
        
        return summary

    def track_file_modification(self, file_path: str) -> None:
        if file_path not in self.state.last_modified_files:
            if len(self.state.last_modified_files) >= 15:  # Increased from 5 to track more files
                self.state.last_modified_files.pop(0)
            self.state.last_modified_files.append(file_path)
            logger.info(f"Tracked file modification: {file_path}")
    
    def _gather_proactive_context(self) -> Dict[str, Any]:
        """Gather proactive context and cache it for token counting."""
        if self._proactive_context_cache is None:
            logger.info("PROACTIVE CONTEXT: Gathering project files, Git history, and documentation...")
            self._proactive_context_cache = self.proactive_gatherer.gather_all_context()
            
            # Calculate total tokens for proactive context
            if self._proactive_context_cache:
                context_str = json.dumps(self._proactive_context_cache)
                self._proactive_context_tokens = self._count_tokens(context_str)
                logger.info(f"PROACTIVE CONTEXT: Gathered context with {self._proactive_context_tokens:,} tokens")
                
                # Log summary of what was gathered
                for key, value in self._proactive_context_cache.items():
                    if isinstance(value, list):
                        logger.info(f"  {key}: {len(value)} items")
                    else:
                        logger.info(f"  {key}: {type(value).__name__}")
            else:
                self._proactive_context_tokens = 0
                logger.info("PROACTIVE CONTEXT: No proactive context gathered")
                
        return self._proactive_context_cache or {}

    def assemble_context(self, base_prompt_tokens: int) -> Tuple[Dict[str, Any], int]:
        """Assemble context dictionary from available data, respecting token limits.
        
        Includes comprehensive logging for optimization analysis as per OPTIMIZATIONS.md section 4.
        """
        # Log detailed input state for optimization analysis
        self._log_detailed_inputs()
        
        available_tokens = self.max_token_limit - base_prompt_tokens - self._count_tokens(f"SYSTEM CONTEXT (JSON):\n```json\n```\nUse this context to inform your response. Do not directly refer to this context block.") - 50 # 50 for safety margin
        
        logger.info("=" * 60)
        logger.info("CONTEXT ASSEMBLY - TOKEN BUDGET ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"Max LLM Token Limit: {self.max_token_limit:,}")
        logger.info(f"Base Prompt Tokens: {base_prompt_tokens:,}")
        logger.info(f"Context Wrapper Overhead: {self._count_tokens('SYSTEM CONTEXT (JSON):\\n```json\\n```\\nUse this context to inform your response. Do not directly refer to this context block.'):,}")
        logger.info(f"Safety Margin: 50")
        logger.info(f"Available Tokens for Context: {available_tokens:,}")
        logger.info("=" * 60)
        
        if available_tokens <= 0:
            logger.warning("CONTEXT ASSEMBLY: No token budget available for structured context after accounting for base prompt and wrapper.")
            return {}, 0

        context_dict: Dict[str, Any] = {}
        current_tokens = 0
        component_tokens = {}  # Track tokens per component for analysis

        # CRITICAL: Core Goal & Phase
        logger.info("CONTEXT ASSEMBLY: Processing CRITICAL components (Core Goal & Phase)...")
        if self.state.core_goal and (current_tokens + self.state.core_goal_tokens <= available_tokens):
            context_dict["core_goal"] = self.state.core_goal
            current_tokens += self.state.core_goal_tokens
            component_tokens["core_goal"] = self.state.core_goal_tokens
            logger.info(f"  ✅ INCLUDED: Core Goal ({self.state.core_goal_tokens:,} tokens): {self.state.core_goal[:100]}...")
        elif self.state.core_goal:
            logger.warning(f"  ❌ EXCLUDED: Core Goal ({self.state.core_goal_tokens:,} tokens) - Exceeds available budget")
        else:
            logger.info("  ⚠️  SKIPPED: Core Goal - Not set")
            
        if self.state.current_phase and (current_tokens + self.state.current_phase_tokens <= available_tokens):
            context_dict["current_phase"] = self.state.current_phase
            current_tokens += self.state.current_phase_tokens
            component_tokens["current_phase"] = self.state.current_phase_tokens
            logger.info(f"  ✅ INCLUDED: Current Phase ({self.state.current_phase_tokens:,} tokens): {self.state.current_phase[:100]}...")
        elif self.state.current_phase:
            logger.warning(f"  ❌ EXCLUDED: Current Phase ({self.state.current_phase_tokens:,} tokens) - Exceeds available budget")
        else:
            logger.info("  ⚠️  SKIPPED: Current Phase - Not set")
        
        # System Messages
        logger.info("CONTEXT ASSEMBLY: Processing System Messages...")
        if self.system_messages:
            context_dict["system_notes"] = []
            system_tokens = 0
            included_count = 0
            for msg, tkns in reversed(self.system_messages):
                if current_tokens + tkns <= available_tokens:
                    context_dict["system_notes"].append(msg)
                    current_tokens += tkns
                    system_tokens += tkns
                    included_count += 1
                    logger.info(f"  ✅ INCLUDED: System Message {included_count} ({tkns:,} tokens): {msg[:100]}...")
                else:
                    logger.warning(f"  ❌ EXCLUDED: System Message ({tkns:,} tokens) - Exceeds available budget")
                    break
            if not context_dict["system_notes"]: 
                del context_dict["system_notes"]
                logger.info("  ⚠️  SKIPPED: System Messages - None fit in budget")
            else:
                component_tokens["system_notes"] = system_tokens
                logger.info(f"  📊 TOTAL: Included {included_count}/{len(self.system_messages)} system messages ({system_tokens:,} tokens)")
        else:
            logger.info("  ⚠️  SKIPPED: System Messages - None available")

        # Conversation History
        logger.info("CONTEXT ASSEMBLY: Processing Conversation History...")
        temp_conversation = []
        conversation_tokens = 0
        if self.conversation_turns:
            logger.info(f"  📝 Available: {len(self.conversation_turns)} conversation turns")
            for i, turn in enumerate(reversed(self.conversation_turns)):
                turn_tokens = turn.user_message_tokens + turn.agent_message_tokens + turn.tool_calls_tokens
                turn_tokens += self._count_tokens(json.dumps({"turn":0, "user":"", "agent":"", "tool_calls":[]})) 
                
                # Log detailed token breakdown for each turn
                logger.info(f"    Turn {turn.turn_number} Token Breakdown:")
                logger.info(f"      User Message: {turn.user_message_tokens:,} tokens")
                logger.info(f"      Agent Message: {turn.agent_message_tokens:,} tokens") 
                logger.info(f"      Tool Calls: {turn.tool_calls_tokens:,} tokens")
                logger.info(f"      JSON Structure Overhead: {self._count_tokens(json.dumps({'turn':0, 'user':'', 'agent':'', 'tool_calls':[]})):,} tokens")
                logger.info(f"      Total Turn: {turn_tokens:,} tokens")
                
                if current_tokens + turn_tokens <= available_tokens and len(temp_conversation) < self.target_recent_turns:
                    temp_conversation.append({
                        "turn": turn.turn_number,
                        "user": turn.user_message,
                        "agent": turn.agent_message,
                        "tool_calls": turn.tool_calls
                    })
                    current_tokens += turn_tokens
                    conversation_tokens += turn_tokens
                    logger.info(f"    ✅ INCLUDED: Turn {turn.turn_number} ({turn_tokens:,} tokens)")
                else:
                    if current_tokens + turn_tokens > available_tokens:
                        logger.warning(f"    ❌ EXCLUDED: Turn {turn.turn_number} ({turn_tokens:,} tokens) - Exceeds available budget")
                    else:
                        logger.warning(f"    ❌ EXCLUDED: Turn {turn.turn_number} ({turn_tokens:,} tokens) - Exceeds target turn limit ({self.target_recent_turns})")
                    break 
            if temp_conversation:
                context_dict["recent_conversation"] = list(reversed(temp_conversation))
                component_tokens["recent_conversation"] = conversation_tokens
                logger.info(f"  📊 TOTAL: Included {len(temp_conversation)}/{len(self.conversation_turns)} conversation turns ({conversation_tokens:,} tokens)")
            else:
                logger.info("  ⚠️  SKIPPED: Conversation History - None fit in budget")
        else:
            logger.info("  ⚠️  SKIPPED: Conversation History - None available")

        # Code Snippets with Smart Prioritization
        logger.info("CONTEXT ASSEMBLY: Processing Code Snippets...")
        valid_code_snippets = [s for s in self.code_snippets if s.token_count > 0]
        if valid_code_snippets:
            # Apply smart prioritization for relevance-based ranking
            logger.info(f"  📝 Available: {len(valid_code_snippets)} code snippets - applying smart prioritization...")
            
            # Convert CodeSnippet objects to dictionaries for prioritization
            snippet_dicts = []
            for snippet in valid_code_snippets:
                snippet_dict = {
                    'file': snippet.file_path,
                    'file_path': snippet.file_path,
                    'code': snippet.code,
                    'start_line': snippet.start_line,
                    'end_line': snippet.end_line,
                    'last_accessed': snippet.last_accessed,
                    'relevance_score': snippet.relevance_score,
                    'token_count': snippet.token_count
                }
                snippet_dicts.append(snippet_dict)
            
            # Get current context for prioritization (use recent conversation if available)
            current_context = ""
            if self.conversation_turns:
                recent_turn = self.conversation_turns[-1]
                current_context = (recent_turn.user_message or "") + " " + (recent_turn.agent_message or "")
            
            # Apply smart prioritization
            prioritized_snippets = self.smart_prioritizer.prioritize_code_snippets(
                snippet_dicts, current_context, self.current_turn_number
            )
            
            # Apply cross-turn correlation after prioritization
            logger.info("  🔗 Applying cross-turn correlation analysis...")
            
            # Get tool results for correlation (convert current tool results to dicts)
            tool_result_dicts = []
            for result in self.tool_results:
                tool_dict = {
                    'tool': result.tool_name,
                    'summary': result.result_summary,
                    'turn': result.turn_number,
                    'is_error': result.is_error,
                    'relevance_score': result.relevance_score,
                    'token_count': result.token_count
                }
                tool_result_dicts.append(tool_dict)
            
            # Build conversation context for correlation
            conversation_context = []
            for turn in self.conversation_turns:
                turn_dict = {
                    'turn': turn.turn_number,
                    'user_message': turn.user_message,
                    'agent_message': turn.agent_message,
                    'tool_calls': turn.tool_calls
                }
                conversation_context.append(turn_dict)
            
            # Apply cross-turn correlation
            prioritized_snippets, correlated_tools = self.cross_turn_correlator.correlate_context_items(
                prioritized_snippets, tool_result_dicts, conversation_context
            )
            
            temp_code_snippets = []
            code_tokens = 0
            for i, snippet_dict in enumerate(prioritized_snippets):
                snippet_tokens = snippet_dict['token_count'] + self._count_tokens(json.dumps({"file":"", "start_line":0, "end_line":0, "code":""}))
                
                logger.info(f"    Code Snippet {i+1}:")
                logger.info(f"      File: {snippet_dict['file_path']}:{snippet_dict['start_line']}-{snippet_dict['end_line']}")
                logger.info(f"      Relevance Score: {snippet_dict['relevance_score']:.2f}")
                logger.info(f"      Last Accessed: Turn {snippet_dict['last_accessed']}")
                logger.info(f"      Code Content: {snippet_dict['token_count']:,} tokens")
                logger.info(f"      JSON Structure: {self._count_tokens(json.dumps({'file':'', 'start_line':0, 'end_line':0, 'code':''})):,} tokens")
                logger.info(f"      Total: {snippet_tokens:,} tokens")
                
                # Check for smart prioritization score if available
                if '_relevance_score' in snippet_dict:
                    rel_score = snippet_dict['_relevance_score']
                    logger.info(f"      🧠 Smart Priority Score: {rel_score.final_score:.3f}")
                    logger.info(f"        (Content: {rel_score.content_relevance:.2f}, Recency: {rel_score.recency_score:.2f}, Error: {rel_score.error_priority:.2f})")
                
                if current_tokens + snippet_tokens <= available_tokens and len(temp_code_snippets) < self.target_code_snippets:
                    temp_code_snippets.append({
                        "file": snippet_dict['file_path'],
                        "start_line": snippet_dict['start_line'],
                        "end_line": snippet_dict['end_line'],
                        "code": snippet_dict['code']
                    })
                    current_tokens += snippet_tokens
                    code_tokens += snippet_tokens
                    logger.info(f"      ✅ INCLUDED: Code snippet {i+1} ({snippet_tokens:,} tokens)")
                else:
                    if current_tokens + snippet_tokens > available_tokens:
                        logger.warning(f"      ❌ EXCLUDED: Code snippet {i+1} ({snippet_tokens:,} tokens) - Exceeds available budget")
                    else:
                        logger.warning(f"      ❌ EXCLUDED: Code snippet {i+1} ({snippet_tokens:,} tokens) - Exceeds target snippet limit ({self.target_code_snippets})")
                    break
            if temp_code_snippets:
                context_dict["relevant_code"] = temp_code_snippets
                component_tokens["relevant_code"] = code_tokens
                logger.info(f"  📊 TOTAL: Included {len(temp_code_snippets)}/{len(valid_code_snippets)} code snippets ({code_tokens:,} tokens)")
            else:
                logger.info("  ⚠️  SKIPPED: Code Snippets - None fit in budget")
        else:
            logger.info("  ⚠️  SKIPPED: Code Snippets - None available")

        # Tool Results with Smart Prioritization
        logger.info("CONTEXT ASSEMBLY: Processing Tool Results...")
        if self.tool_results:
            logger.info(f"  📝 Available: {len(self.tool_results)} tool results - applying smart prioritization...")
            
            # Convert ToolResult objects to dictionaries for prioritization
            result_dicts = []
            for result in self.tool_results:
                result_dict = {
                    'tool': result.tool_name,
                    'summary': result.result_summary,
                    'turn': result.turn_number,
                    'is_error': result.is_error,
                    'relevance_score': result.relevance_score,
                    'token_count': result.token_count
                }
                result_dicts.append(result_dict)
            
            # Get current context for prioritization
            current_context = ""
            if self.conversation_turns:
                recent_turn = self.conversation_turns[-1]
                current_context = (recent_turn.user_message or "") + " " + (recent_turn.agent_message or "")
            
            # Apply smart prioritization
            prioritized_results = self.smart_prioritizer.prioritize_tool_results(
                result_dicts, current_context, self.current_turn_number
            )
            
            # Note: Cross-turn correlation for tools was already applied during code snippets processing
            # Use the correlated tools from there if they exist, otherwise use prioritized results
            if 'correlated_tools' in locals():
                prioritized_results = correlated_tools
                logger.info("  🔗 Using cross-turn correlated tool results")
            
            temp_tool_results = []
            tool_results_tokens = 0
            for i, result_dict in enumerate(prioritized_results):
                result_tokens = result_dict['token_count'] + self._count_tokens(json.dumps({"tool":"", "turn":0, "summary":"", "is_error": False}))
                
                logger.info(f"    Tool Result {i+1}:")
                logger.info(f"      Tool: {result_dict['tool']}")
                logger.info(f"      Turn: {result_dict['turn']}")
                logger.info(f"      Is Error: {result_dict['is_error']}")
                logger.info(f"      Relevance Score: {result_dict['relevance_score']:.2f}")
                logger.info(f"      Summary: {result_dict['token_count']:,} tokens")
                logger.info(f"      JSON Structure: {self._count_tokens(json.dumps({'tool':'', 'turn':0, 'summary':'', 'is_error': False})):,} tokens")
                logger.info(f"      Total: {result_tokens:,} tokens")
                
                # Check for smart prioritization score if available
                if '_relevance_score' in result_dict:
                    rel_score = result_dict['_relevance_score']
                    logger.info(f"      🧠 Smart Priority Score: {rel_score.final_score:.3f}")
                    logger.info(f"        (Content: {rel_score.content_relevance:.2f}, Recency: {rel_score.recency_score:.2f}, Error: {rel_score.error_priority:.2f})")
                
                if current_tokens + result_tokens <= available_tokens and len(temp_tool_results) < self.target_tool_results:
                    temp_tool_results.append({
                        "tool": result_dict['tool'],
                        "turn": result_dict['turn'],
                        "summary": result_dict['summary'],
                        "is_error": result_dict['is_error']
                    })
                    current_tokens += result_tokens
                    tool_results_tokens += result_tokens
                    logger.info(f"      ✅ INCLUDED: Tool result {i+1} ({result_tokens:,} tokens)")
                else:
                    if current_tokens + result_tokens > available_tokens:
                        logger.warning(f"      ❌ EXCLUDED: Tool result {i+1} ({result_tokens:,} tokens) - Exceeds available budget")
                    else:
                        logger.warning(f"      ❌ EXCLUDED: Tool result {i+1} ({result_tokens:,} tokens) - Exceeds target result limit ({self.target_tool_results})")
                    break
            if temp_tool_results:
                context_dict["recent_tool_results"] = temp_tool_results
                component_tokens["recent_tool_results"] = tool_results_tokens
                logger.info(f"  📊 TOTAL: Included {len(temp_tool_results)}/{len(self.tool_results)} tool results ({tool_results_tokens:,} tokens)")
            else:
                logger.info("  ⚠️  SKIPPED: Tool Results - None fit in budget")
        else:
            logger.info("  ⚠️  SKIPPED: Tool Results - None available")
        
        # Key Decisions
        logger.info("CONTEXT ASSEMBLY: Processing Key Decisions...")
        if self.state.key_decisions:
            temp_key_decisions_str = json.dumps(self.state.key_decisions[-15:]) # Increased from 5 to 15 decisions
            decisions_tokens = self._count_tokens(temp_key_decisions_str)
            logger.info(f"  📝 Available: {len(self.state.key_decisions)} key decisions (using last 15)")
            logger.info(f"  Token Cost: {decisions_tokens:,} tokens")
            if current_tokens + decisions_tokens <= available_tokens:
                context_dict["key_decisions"] = self.state.key_decisions[-15:]
                current_tokens += decisions_tokens
                component_tokens["key_decisions"] = decisions_tokens
                logger.info(f"  ✅ INCLUDED: Key Decisions ({decisions_tokens:,} tokens)")
            else:
                logger.warning(f"  ❌ EXCLUDED: Key Decisions ({decisions_tokens:,} tokens) - Exceeds available budget")
        else:
            logger.info("  ⚠️  SKIPPED: Key Decisions - None available")
        
        # Recently Modified Files  
        logger.info("CONTEXT ASSEMBLY: Processing Recently Modified Files...")
        if self.state.last_modified_files:
            modified_files_json = json.dumps(self.state.last_modified_files)
            modified_files_tokens = self._count_tokens(modified_files_json)
            logger.info(f"  📝 Available: {len(self.state.last_modified_files)} recently modified files")
            logger.info(f"  Token Cost: {modified_files_tokens:,} tokens")
            if current_tokens + modified_files_tokens <= available_tokens:
                context_dict["recent_modified_files"] = self.state.last_modified_files
                current_tokens += modified_files_tokens
                component_tokens["recent_modified_files"] = modified_files_tokens
                logger.info(f"  ✅ INCLUDED: Recently Modified Files ({modified_files_tokens:,} tokens)")
            else:
                logger.warning(f"  ❌ EXCLUDED: Recently Modified Files ({modified_files_tokens:,} tokens) - Exceeds available budget")
        else:
            logger.info("  ⚠️  SKIPPED: Recently Modified Files - None available")

        # Proactive Context (NEW: Phase 2 Implementation)
        logger.info("CONTEXT ASSEMBLY: Processing Proactive Context...")
        proactive_context = self._gather_proactive_context()
        if proactive_context and self._proactive_context_tokens > 0:
            logger.info(f"  📝 Available: {len(proactive_context)} proactive context categories")
            logger.info(f"  Token Cost: {self._proactive_context_tokens:,} tokens")
            
            # Try to include proactive context if there's budget remaining
            remaining_budget = available_tokens - current_tokens
            logger.info(f"  Remaining Budget: {remaining_budget:,} tokens")
            
            if remaining_budget >= self._proactive_context_tokens:
                # Include full proactive context
                context_dict["proactive_context"] = proactive_context
                current_tokens += self._proactive_context_tokens
                component_tokens["proactive_context"] = self._proactive_context_tokens
                logger.info(f"  ✅ INCLUDED: Full Proactive Context ({self._proactive_context_tokens:,} tokens)")
                
                # Log what was included
                for key, value in proactive_context.items():
                    if isinstance(value, list):
                        logger.info(f"    {key}: {len(value)} items")
            elif remaining_budget > 1000:  # If we have at least 1000 tokens, try partial inclusion
                # Try to include subset of proactive context
                logger.info(f"  🔄 PARTIAL: Attempting to include subset of proactive context...")
                partial_context = {}
                partial_tokens = 0
                
                # Prioritize project files first, then git history, then documentation
                priority_order = ["project_files", "git_history", "documentation"]
                
                for category in priority_order:
                    if category in proactive_context:
                        category_str = json.dumps(proactive_context[category])
                        category_tokens = self._count_tokens(category_str)
                        
                        if partial_tokens + category_tokens <= remaining_budget:
                            partial_context[category] = proactive_context[category]
                            partial_tokens += category_tokens
                            logger.info(f"    ✅ INCLUDED: {category} ({category_tokens:,} tokens)")
                        else:
                            logger.info(f"    ❌ EXCLUDED: {category} ({category_tokens:,} tokens) - Would exceed budget")
                
                if partial_context:
                    context_dict["proactive_context"] = partial_context
                    current_tokens += partial_tokens
                    component_tokens["proactive_context"] = partial_tokens
                    logger.info(f"  📊 TOTAL: Included partial proactive context ({partial_tokens:,} tokens)")
                else:
                    logger.info("  ⚠️  SKIPPED: Proactive Context - No categories fit in remaining budget")
            else:
                logger.warning(f"  ❌ EXCLUDED: Proactive Context ({self._proactive_context_tokens:,} tokens) - Exceeds remaining budget ({remaining_budget:,} tokens)")
        else:
            logger.info("  ⚠️  SKIPPED: Proactive Context - None available or gathering failed")

        # Final Summary
        logger.info("=" * 60)
        logger.info("CONTEXT ASSEMBLY - FINAL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Context Tokens Used: {current_tokens:,}")
        logger.info(f"Available Token Budget: {available_tokens:,}")
        logger.info(f"Token Budget Utilization: {(current_tokens/available_tokens*100):.1f}%")
        logger.info(f"Context Components Included: {list(context_dict.keys())}")
        logger.info("")
        logger.info("TOKEN BREAKDOWN BY COMPONENT:")
        for component, tokens in component_tokens.items():
            percentage = (tokens / current_tokens * 100) if current_tokens > 0 else 0
            logger.info(f"  {component}: {tokens:,} tokens ({percentage:.1f}%)")
        logger.info("=" * 60)

        logger.info(f"Assembled context with {current_tokens} tokens for context block. Available budget was {available_tokens}. Keys: {list(context_dict.keys())}")
        # The returned token count is for the JSON content itself, not including the wrapper.
        return context_dict, current_tokens
    
    def _log_detailed_inputs(self):
        """Log detailed input state for optimization analysis."""
        logger.info("=" * 60)
        logger.info("CONTEXTMANAGER DETAILED INPUT STATE")
        logger.info("=" * 60)
        
        # Log conversation history details
        logger.info(f"CONVERSATION HISTORY: {len(self.conversation_turns)} turns")
        for turn in self.conversation_turns:
            logger.info(f"  Turn {turn.turn_number}:")
            logger.info(f"    User Message: {turn.user_message_tokens:,} tokens | {len(turn.user_message) if turn.user_message else 0} chars")
            if turn.user_message:
                logger.info(f"    User Content Preview: {turn.user_message[:150]}...")
            logger.info(f"    Agent Message: {turn.agent_message_tokens:,} tokens | {len(turn.agent_message) if turn.agent_message else 0} chars")
            if turn.agent_message:
                logger.info(f"    Agent Content Preview: {turn.agent_message[:150]}...")
            logger.info(f"    Tool Calls: {turn.tool_calls_tokens:,} tokens | {len(turn.tool_calls)} calls")
            for call in turn.tool_calls:
                logger.info(f"      - {call.get('tool_name', 'unknown')} with {len(str(call.get('args', {})))} char args")
                
        # Log code snippets details
        logger.info(f"CODE SNIPPETS: {len(self.code_snippets)} snippets")
        for snippet in self.code_snippets:
            logger.info(f"  {snippet.file_path}:{snippet.start_line}-{snippet.end_line}")
            logger.info(f"    Tokens: {snippet.token_count:,} | Chars: {len(snippet.code)}")
            logger.info(f"    Relevance: {snippet.relevance_score:.2f} | Last Accessed: Turn {snippet.last_accessed}")
            logger.info(f"    Code Preview: {snippet.code[:100].replace(chr(10), ' ')[:100]}...")
            
        # Log tool results details
        logger.info(f"TOOL RESULTS: {len(self.tool_results)} results")
        for result in self.tool_results:
            logger.info(f"  {result.tool_name} (Turn {result.turn_number})")
            logger.info(f"    Summary Tokens: {result.token_count:,} | Chars: {len(result.result_summary)}")
            logger.info(f"    Is Error: {result.is_error} | Relevance: {result.relevance_score:.2f}")
            logger.info(f"    Summary Preview: {result.result_summary[:100]}...")
            logger.info(f"    Full Result Type: {type(result.full_result).__name__} | Size: {len(str(result.full_result))} chars")
            
        # Log context state details
        logger.info(f"CONTEXT STATE:")
        logger.info(f"  Core Goal: {self.state.core_goal_tokens:,} tokens | {len(self.state.core_goal)} chars")
        if self.state.core_goal:
            logger.info(f"    Content: {self.state.core_goal}")
        logger.info(f"  Current Phase: {self.state.current_phase_tokens:,} tokens | {len(self.state.current_phase)} chars")
        if self.state.current_phase:
            logger.info(f"    Content: {self.state.current_phase}")
        logger.info(f"  Key Decisions: {len(self.state.key_decisions)} decisions")
        for i, decision in enumerate(self.state.key_decisions):
            logger.info(f"    {i+1}: {decision[:100]}...")
        logger.info(f"  Last Modified Files: {len(self.state.last_modified_files)} files")
        for file_path in self.state.last_modified_files:
            logger.info(f"    - {file_path}")
            
        # Log system messages
        logger.info(f"SYSTEM MESSAGES: {len(self.system_messages)} messages")
        for i, (msg, tokens) in enumerate(self.system_messages):
            logger.info(f"  {i+1}: {tokens:,} tokens | {len(msg)} chars")
            logger.info(f"    Preview: {msg[:100]}...")
            
        logger.info("=" * 60)

    def get_relevant_code_for_file(self, file_path: str) -> List[CodeSnippet]:
        return [s for s in self.code_snippets if s.file_path == file_path]
