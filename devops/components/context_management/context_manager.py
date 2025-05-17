"""Context management for agent loop to optimize token usage while preserving quality."""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple, Callable
import json
from rich.console import Console

from google import genai
from google.genai.types import Content, Part, CountTokensResponse # For native token counting

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
                 target_recent_turns: int = 5,
                 target_code_snippets: int = 5,
                 target_tool_results: int = 5,
                 max_stored_code_snippets: int = 20,
                 max_stored_tool_results: int = 30):
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
        for i, snippet in enumerate(self.code_snippets):
            if (snippet.file_path == file_path and 
                snippet.start_line == start_line and 
                snippet.end_line == end_line):
                self.code_snippets[i].last_accessed = self.current_turn_number
                self.code_snippets[i].relevance_score += 0.2 
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
        summary = ""
        MAX_SUMMARY_LEN = 500 # Max characters for a summary
        TRUNC_MSG_TEMPLATE = " (truncated due to length)"

        if tool_name == "read_file_content" or tool_name == "read_file":
            if isinstance(result, dict) and result.get("status") == "success" and "content" in result:
                content = result["content"]
                if isinstance(content, str):
                    if any(kw in content for kw in ["def ", "class ", "import ", "function("]): 
                        summary = f"Read code file. Length: {len(content)} chars. Content (truncated): {content[:150]}...{content[-150:] if len(content) > 300 else ''}"
                    else:
                        summary = f"Read file. Length: {len(content)} chars. Content (truncated): {content[:150]}...{content[-150:] if len(content) > 300 else ''}"
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

                if stdout and "[Output truncated" in stdout:
                    parts.append(f"Stdout was large and truncated. First/last parts: {stdout.split('\\n', 1)[-1]}") # Show after truncation message
                elif stdout:
                    parts.append(f"Stdout: {stdout[:MAX_SUMMARY_LEN // 3]}") # Show a bit more of stdout if not truncated already
                
                if stderr and "[Output truncated" in stderr:
                    parts.append(f"Stderr was large and truncated. First/last parts: {stderr.split('\\n', 1)[-1]}")
                elif stderr:
                    parts.append(f"Stderr: {stderr[:MAX_SUMMARY_LEN // 3]}")
                
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
                elif "retrieved_chunks" in result and isinstance(result["retrieved_chunks"], list):
                    summary = f"Retrieved {len(result['retrieved_chunks'])} code chunks."
                else:
                    summary = f"{tool_name} completed. Keys: {list(result.keys())}"
            else:
                summary = f"{tool_name} completed with non-dict result."
        else: 
            if isinstance(result, dict):
                important_keys = ["status", "message", "summary", "error", "output", "stdout", "stderr"]
                summary_parts = []
                for key in important_keys:
                    if key in result and result[key]:
                        val_str = str(result[key])
                        summary_parts.append(f"{key}: {val_str[:100] + '...' if len(val_str) > 100 else val_str}")                 
                if summary_parts:
                    summary = f"Tool {tool_name}: " + "; ".join(summary_parts)
                else:
                    summary = f"Tool {tool_name} completed. Result (truncated): {str(result)[:200]}..."
            elif isinstance(result, str):
                summary = f"Tool {tool_name} output (truncated): {result[:200]}..."
            else:
                summary = f"Tool {tool_name} completed with result type: {type(result).__name__}."
        
        if len(summary) > MAX_SUMMARY_LEN: 
            summary = summary[:MAX_SUMMARY_LEN - len(TRUNC_MSG_TEMPLATE)] + TRUNC_MSG_TEMPLATE
        return summary

    def track_file_modification(self, file_path: str) -> None:
        if file_path not in self.state.last_modified_files:
            if len(self.state.last_modified_files) >= 5:
                self.state.last_modified_files.pop(0)
            self.state.last_modified_files.append(file_path)

    def assemble_context(self, base_prompt_tokens: int) -> Tuple[Dict[str, Any], int]:
        available_tokens = self.max_token_limit - base_prompt_tokens - self._count_tokens(f"SYSTEM CONTEXT (JSON):\n```json\n```\nUse this context to inform your response. Do not directly refer to this context block.") - 50 # 50 for safety margin
        if available_tokens <= 0:
            logger.warning("No token budget available for structured context after accounting for base prompt and wrapper.")
            return {}, 0

        context_dict: Dict[str, Any] = {}
        current_tokens = 0

        # CRITICAL: Core Goal & Phase
        if self.state.core_goal and (current_tokens + self.state.core_goal_tokens <= available_tokens):
            context_dict["core_goal"] = self.state.core_goal
            current_tokens += self.state.core_goal_tokens
        if self.state.current_phase and (current_tokens + self.state.current_phase_tokens <= available_tokens):
            context_dict["current_phase"] = self.state.current_phase
            current_tokens += self.state.current_phase_tokens
        
        if self.system_messages:
            context_dict["system_notes"] = []
            for msg, tkns in reversed(self.system_messages):
                if current_tokens + tkns <= available_tokens:
                    context_dict["system_notes"].append(msg)
                    current_tokens += tkns
                else:
                    break
            if not context_dict["system_notes"]: del context_dict["system_notes"]

        temp_conversation = []
        if self.conversation_turns:
            for turn in reversed(self.conversation_turns):
                turn_tokens = turn.user_message_tokens + turn.agent_message_tokens + turn.tool_calls_tokens
                turn_tokens += self._count_tokens(json.dumps({"turn":0, "user":"", "agent":"", "tool_calls":[]})) 
                if current_tokens + turn_tokens <= available_tokens and len(temp_conversation) < self.target_recent_turns:
                    temp_conversation.append({
                        "turn": turn.turn_number,
                        "user": turn.user_message,
                        "agent": turn.agent_message,
                        "tool_calls": turn.tool_calls
                    })
                    current_tokens += turn_tokens
                else:
                    break 
            if temp_conversation:
                context_dict["recent_conversation"] = list(reversed(temp_conversation))

        valid_code_snippets = [s for s in self.code_snippets if s.token_count > 0]
        valid_code_snippets.sort(key=lambda s: (-s.relevance_score, -s.last_accessed))
        temp_code_snippets = []
        for snippet in valid_code_snippets:
            snippet_tokens = snippet.token_count + self._count_tokens(json.dumps({"file":"", "start_line":0, "end_line":0, "code":""}))
            if current_tokens + snippet_tokens <= available_tokens and len(temp_code_snippets) < self.target_code_snippets:
                temp_code_snippets.append({
                    "file": snippet.file_path,
                    "start_line": snippet.start_line,
                    "end_line": snippet.end_line,
                    "code": snippet.code
                })
                current_tokens += snippet_tokens
            else:
                break
        if temp_code_snippets:
            context_dict["relevant_code"] = temp_code_snippets

        # Handle case where any of the sort values might be None
        def tool_result_sort_key(r):
            # Default to False if is_error is None
            error_key = -1 if r.is_error else 0 
            # Default to 0 if relevance_score is None
            relevance_key = -1 * (r.relevance_score or 0)
            # Default to 0 if turn_number is None
            turn_key = -1 * (r.turn_number or 0)
            return (error_key, relevance_key, turn_key)
        
        self.tool_results.sort(key=tool_result_sort_key)
        
        temp_tool_results = []
        for result in self.tool_results:
            result_tokens = result.token_count + self._count_tokens(json.dumps({"tool":"", "turn":0, "summary":"", "is_error": False}))
            if current_tokens + result_tokens <= available_tokens and len(temp_tool_results) < self.target_tool_results:
                temp_tool_results.append({
                    "tool": result.tool_name,
                    "turn": result.turn_number,
                    "summary": result.result_summary,
                    "is_error": result.is_error
                })
                current_tokens += result_tokens
            else:
                break
        if temp_tool_results:
            context_dict["recent_tool_results"] = temp_tool_results
        
        temp_key_decisions_str = json.dumps(self.state.key_decisions[-5:]) # last 5 decisions
        decisions_tokens = self._count_tokens(temp_key_decisions_str)
        if self.state.key_decisions and (current_tokens + decisions_tokens <= available_tokens):
            context_dict["key_decisions"] = self.state.key_decisions[-5:]
            current_tokens += decisions_tokens
        
        if self.state.last_modified_files:
            modified_files_json = json.dumps(self.state.last_modified_files)
            modified_files_tokens = self._count_tokens(modified_files_json)
            if current_tokens + modified_files_tokens <= available_tokens:
                context_dict["recent_modified_files"] = self.state.last_modified_files
                current_tokens += modified_files_tokens

        logger.info(f"Assembled context with {current_tokens} tokens for context block. Available budget was {available_tokens}. Keys: {list(context_dict.keys())}")
        # The returned token count is for the JSON content itself, not including the wrapper.
        return context_dict, current_tokens

    def get_relevant_code_for_file(self, file_path: str) -> List[CodeSnippet]:
        return [s for s in self.code_snippets if s.file_path == file_path]
