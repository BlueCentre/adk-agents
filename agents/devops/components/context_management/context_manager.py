"""Context management for agent loop to optimize token usage while preserving quality."""

from dataclasses import dataclass, field
from enum import Enum, auto
import json
import logging
from pathlib import Path
import time
from typing import Any, Callable, Optional

from google import genai
from google.genai.types import Content, CountTokensResponse, Part  # For native token counting
from rich.console import Console

from .cross_turn_correlation import CrossTurnCorrelator
from .dynamic_context_expansion import DiscoveredContent, DynamicContextExpander, ExpansionContext
from .intelligent_summarization import ContentType, IntelligentSummarizer, SummarizationContext
from .proactive_context import ProactiveContextGatherer
from .smart_prioritization import SmartPrioritizer

# Attempt to import tiktoken for accurate token counting
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning(
        "tiktoken library not found. Token counting will be a rough estimate based on "
        "character count if native counter also fails."
    )

# Set up logging
logger = logging.getLogger(__name__)


class ContextPriority(Enum):
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    MINIMAL = auto()


@dataclass
class CodeSnippet:
    file_path: str
    code: str
    start_line: int
    end_line: int
    last_accessed: int
    relevance_score: float = 1.0
    token_count: int = 0
    priority: ContextPriority = ContextPriority.LOW


@dataclass
class ToolResult:
    tool_name: str
    result_summary: str
    full_result: Any
    turn_number: int
    is_error: bool = False
    relevance_score: float = 1.0
    token_count: int = 0
    priority: ContextPriority = ContextPriority.HIGH


@dataclass
class ConversationTurn:
    turn_number: int
    user_message: Optional[str] = None
    agent_message: Optional[str] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    user_message_tokens: int = 0
    agent_message_tokens: int = 0
    tool_calls_tokens: int = 0
    timestamp: float = field(default_factory=time.time)
    priority: ContextPriority = ContextPriority.MEDIUM

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens for this turn."""
        return self.user_message_tokens + self.agent_message_tokens + self.tool_calls_tokens

    @property
    def has_tool_activity(self) -> bool:
        """Check if this turn contains tool activity."""
        return bool(self.tool_calls)


@dataclass
class ContextState:
    core_goal: str = ""
    current_phase: str = ""
    key_decisions: list[str] = field(default_factory=list)
    last_modified_files: list[str] = field(default_factory=list)
    core_goal_tokens: int = 0
    current_phase_tokens: int = 0
    decisions_tokens: int = 0
    files_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens for context state."""
        return (
            self.core_goal_tokens
            + self.current_phase_tokens
            + self.decisions_tokens
            + self.files_tokens
        )


class ContextManager:
    def __init__(
        self,
        model_name: str,
        max_llm_token_limit: int,
        llm_client: Optional[genai.Client] = None,
        target_recent_turns: int = 20,
        target_code_snippets: int = 25,
        target_tool_results: int = 30,
        max_stored_code_snippets: int = 100,
        max_stored_tool_results: int = 150,
    ):
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
                from ... import config as agent_config

                # Create genai client with API key directly
                if agent_config.GOOGLE_API_KEY:
                    llm_client = genai.Client(api_key=agent_config.GOOGLE_API_KEY)
                    logger.info("Created genai client with API key from config in ContextManager")
                else:
                    llm_client = genai.Client()
                    logger.info(
                        "Created default genai client without explicit API key in ContextManager"
                    )
                logger.info("Created default genai client in ContextManager")
            except Exception as e:
                logger.warning(f"Could not create default genai client in ContextManager: {e}")
                # Continue with llm_client=None - we'll use fallback token counting strategies

        self.llm_client = llm_client
        self._token_counting_fn = self._initialize_token_counting_strategy()
        self.state = ContextState()
        self.conversation_turns: list[ConversationTurn] = []
        self.code_snippets: list[CodeSnippet] = []
        self.tool_results: list[ToolResult] = []
        self.current_turn_number = 0
        self.console = Console(stderr=True)
        self.system_messages: list[tuple[str, int]] = []

        # Initialize proactive context gatherer and smart prioritizer
        self.proactive_gatherer = ProactiveContextGatherer()
        self._proactive_context_cache: Optional[dict[str, Any]] = None
        self._proactive_context_tokens: int = 0

        # Initialize smart prioritizer and cross-turn correlator for Phase 2 enhancements
        self.smart_prioritizer = SmartPrioritizer()
        self.cross_turn_correlator = CrossTurnCorrelator()

        # Initialize intelligent summarizer and dynamic context expander
        self.intelligent_summarizer = IntelligentSummarizer()
        self.dynamic_expander = DynamicContextExpander(workspace_root=".")

        # Dynamic targeting based on conversation length
        self._adaptive_limits = self._calculate_adaptive_limits()

        # Performance tracking
        self._last_context_tokens = 0
        self._token_growth_history: list[tuple[int, int]] = []  # (turn, tokens)

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
        logger.info(
            f"LLM Client Type: {type(self.llm_client).__name__ if self.llm_client else 'None'}"
        )
        logger.info(
            f"Token Counting Strategy: "
            f"{self._token_counting_fn.__name__ if hasattr(self._token_counting_fn, '__name__') else 'lambda function'}"  # noqa: E501
        )
        logger.info("=" * 60)

    def _initialize_token_counting_strategy(self) -> Callable[[str], int]:
        # Strategy 1: Native Google GenAI client's count_tokens
        if (
            self.llm_client is not None
            and isinstance(self.llm_client, genai.Client)
            and hasattr(self.llm_client, "models")
            and hasattr(self.llm_client.models, "count_tokens")
        ):
            try:

                def native_google_counter(text: str) -> int:
                    try:
                        # For simple text, wrap in Content/Part structure
                        content_for_counting = Content(parts=[Part(text=text)])
                        # Call count_tokens via client.models
                        response: CountTokensResponse = self.llm_client.models.count_tokens(
                            model=self.model_name, contents=content_for_counting
                        )
                        return response.total_tokens
                    except Exception as e_native_call:
                        logger.debug(
                            f"Native Google count_tokens call (via Content object) failed for "
                            f"model {self.model_name}: {e_native_call}. "
                            "Attempting string directly."
                        )
                        try:  # Try with string directly as contents
                            response: CountTokensResponse = self.llm_client.models.count_tokens(
                                model=self.model_name, contents=text
                            )
                            return response.total_tokens
                        except Exception as e_native_str_call:
                            logger.warning(
                                f"Native Google count_tokens (string direct) also failed for "
                                f"model {self.model_name}: {e_native_str_call}. Falling back."
                            )
                            # Fall through to tiktoken if native fails unexpectedly
                            if TIKTOKEN_AVAILABLE:
                                try:
                                    tokenizer = tiktoken.get_encoding("cl100k_base")
                                    return len(tokenizer.encode(text))
                                except Exception as te:
                                    logger.error(f"Fallback to cl100k_base also failed: {te}")
                            return len(text) // 4  # Ultimate fallback

                # Perform a quick test call
                # Note: The 'contents' arg is used in the new SDK for count_tokens
                test_response = self.llm_client.models.count_tokens(
                    model=self.model_name, contents="test"
                )
                if isinstance(test_response, CountTokensResponse) and hasattr(
                    test_response, "total_tokens"
                ):
                    logger.info(
                        f"Using native Google GenAI token counter for model "
                        f"{self.model_name} (via google.genai client)."
                    )
                    return native_google_counter
                logger.warning(
                    f"Native Google count_tokens for {self.model_name} did not return expected "
                    f"response ({type(test_response)}). Falling back."
                )
            except Exception as e_init:
                logger.warning(
                    f"Could not initialize or test native Google count_tokens for model "
                    f"{self.model_name}: {e_init}. Falling back."
                )
        else:
            if self.llm_client is None:
                logger.warning("llm_client is None - cannot use native token counter")
            elif not isinstance(self.llm_client, genai.Client):
                logger.warning(
                    f"llm_client is not a genai.Client instance (got "
                    f"{type(self.llm_client).__name__})"
                )
            elif not hasattr(self.llm_client, "models") or not hasattr(
                self.llm_client.models, "count_tokens"
            ):
                logger.warning("llm_client does not have the required methods for token counting")

        # Strategy 2: Tiktoken
        if TIKTOKEN_AVAILABLE:
            tokenizer = None
            try:
                tokenizer = tiktoken.encoding_for_model(self.model_name)
                logger.info(f"Using tiktoken with model-specific encoding for {self.model_name}.")
            except KeyError:  # Model not found in tiktoken
                try:
                    tokenizer = tiktoken.get_encoding("cl100k_base")
                    logger.info(
                        f"Using tiktoken with cl100k_base encoding for "
                        f"{self.model_name} (model-specific not found)."
                    )
                except Exception as e_cl100k:
                    logger.error(
                        f"Failed to get cl100k_base tokenizer: {e_cl100k}. "
                        f"Tiktoken unavailable for {self.model_name}."
                    )

            if tokenizer:
                final_tokenizer = tokenizer
                return lambda text: len(final_tokenizer.encode(text))

        # Strategy 3: Character count fallback
        logger.warning(
            f"No advanced tokenizer available for {self.model_name}. "
            "Using character-based token estimation (len // 4)."
        )
        return lambda text: len(text) // 4

    def _count_tokens(self, text: str) -> int:
        if not isinstance(text, str):
            logger.debug(
                f"Non-string type ({type(text)}) passed to _count_tokens. "
                "Converting to string for counting."
            )
            text = str(text)
        if not text:  # Handle empty or None string
            return 0
        try:
            return self._token_counting_fn(text)
        except Exception as e:
            logger.error(
                f"Error during token counting for text '{text[:50]}...': "
                f"{e}. Falling back to char count.",
                exc_info=True,
            )
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
            user_message_tokens=user_tokens,
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

    def add_tool_call(self, turn_number: int, tool_name: str, args: dict[str, Any]) -> None:
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
        logger.info(f"Added key decision: {decision}")  # Tokens for list calculated on assembly

    def add_code_snippet(self, file_path: str, code: str, start_line: int, end_line: int) -> None:
        # Check for existing snippet at same location
        for i, snippet in enumerate(self.code_snippets):
            if (
                snippet.file_path == file_path
                and snippet.start_line == start_line
                and snippet.end_line == end_line
            ):
                self.code_snippets[i].last_accessed = self.current_turn_number
                self.code_snippets[i].relevance_score += 0.2
                logger.info(f"Updated existing code snippet: {file_path}:{start_line}-{end_line}")
                return

        new_snippet = CodeSnippet(
            file_path=file_path,
            code=code,
            start_line=start_line,
            end_line=end_line,
            last_accessed=self.current_turn_number,
            token_count=self._count_tokens(code),
        )
        if len(self.code_snippets) >= self.max_stored_code_snippets:
            self.code_snippets.sort(key=lambda s: (s.relevance_score, s.last_accessed))
            removed = self.code_snippets.pop(0)
            logger.debug(f"Removed code snippet due to store limit: {removed.file_path}")
        self.code_snippets.append(new_snippet)
        logger.info(
            f"Added code snippet from {file_path} ({start_line}-{end_line}), "
            f"tokens: {new_snippet.token_count}"
        )

    def add_full_file_content(self, file_path: str, content: str) -> None:
        """Add full file content as context when files are read/modified."""
        # With 1M+ tokens available, we can afford to include full file contents
        lines = content.split("\n")

        # For small files (< 100 lines), add as single snippet
        if len(lines) <= 100:
            self.add_code_snippet(file_path, content, 1, len(lines))
        else:
            # For larger files, add in chunks to maintain context
            chunk_size = 50  # lines per chunk
            for i in range(0, len(lines), chunk_size):
                end_idx = min(i + chunk_size, len(lines))
                chunk_content = "\n".join(lines[i:end_idx])
                self.add_code_snippet(file_path, chunk_content, i + 1, end_idx)

        # Also track as modified file
        self.track_file_modification(file_path)
        logger.info(
            f"Added full file content for {file_path}: {len(lines)} lines, {len(content)} chars"
        )

    def add_tool_result(self, tool_name: str, result: Any, summary: Optional[str] = None) -> None:
        if summary is None:
            summary = self._generate_tool_result_summary(tool_name, result)

        is_error = isinstance(result, dict) and (
            result.get("status") == "error" or result.get("error")
        )
        summary_tokens = self._count_tokens(summary)

        new_result = ToolResult(
            tool_name=tool_name,
            result_summary=summary,
            full_result=result,
            turn_number=self.current_turn_number,
            is_error=is_error,
            token_count=summary_tokens,
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
        MAX_SUMMARY_LEN = 2000  # Increased from 500 - we have 1M+ tokens available!
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
            if (
                isinstance(result, dict)
                and result.get("status") == "success"
                and "content" in result
            ):
                content = result["content"]
                if isinstance(content, str):
                    if any(kw in content for kw in ["def ", "class ", "import ", "function("]):
                        summary = (
                            f"Read code file. Length: {len(content)} chars. Content (truncated): "
                            f"{content[:500]}...{content[-500:] if len(content) > 1000 else ''}"
                        )
                    else:
                        summary = (
                            f"Read file. Length: {len(content)} chars. Content (truncated): "
                            f"{content[:500]}...{content[-500:] if len(content) > 1000 else ''}"
                        )

                    # Log transformation details for file content
                    logger.info("Transformation Type: File content summary")
                    logger.info(f"Original File Content Size: {len(content):,} characters")
                    logger.info(
                        "Content Type: "
                        f"{'Code file' if any(kw in content for kw in ['def ', 'class ', 'import ', 'function(']) else 'Text file'}"  # noqa: E501
                    )
                else:
                    summary = f"Read file, content type: {type(content).__name__}."
            elif isinstance(result, dict) and result.get("status") == "error":
                summary = f"Error reading file: {result.get('message', 'Unknown error')}"
            else:
                summary = f"Tool {tool_name} produced an unexpected result structure."
        elif tool_name == "execute_vetted_shell_command":
            if isinstance(result, dict):
                parts = [f"Shell command '{result.get('command_executed', 'unknown_command')}'"]
                if result.get("return_code") == 0:
                    parts.append("succeeded (rc=0).")
                else:
                    parts.append(f"failed (rc={result.get('return_code', 'N/A')}).")

                stdout = result.get("stdout")
                stderr = result.get("stderr")

                # Log shell command output transformation
                if stdout:
                    logger.info(f"Original Stdout Size: {len(stdout):,} characters")
                    if "[Output truncated" in stdout:
                        logger.info("Stdout Transformation: Already truncated by tool")
                        newline = "\n"
                        parts.append(
                            f"Stdout was large and truncated. First/last parts: "
                            f"{stdout.split(newline, 1)[-1]}"
                        )  # Show after truncation message
                    else:
                        logger.info(
                            f"Stdout Transformation: Truncating to "
                            f"{MAX_SUMMARY_LEN // 2} characters"
                        )
                        parts.append(
                            f"Stdout: {stdout[: MAX_SUMMARY_LEN // 2]}"
                        )  # Show more stdout with increased limits

                if stderr:
                    logger.info(f"Original Stderr Size: {len(stderr):,} characters")
                    if "[Output truncated" in stderr:
                        logger.info("Stderr Transformation: Already truncated by tool")
                        newline = "\n"
                        parts.append(
                            f"Stderr was large and truncated. First/last parts: "
                            f"{stderr.split(newline, 1)[-1]}"
                        )
                    else:
                        logger.info(
                            f"Stderr Transformation: Truncating to "
                            f"{MAX_SUMMARY_LEN // 2} characters"
                        )
                        parts.append(f"Stderr: {stderr[: MAX_SUMMARY_LEN // 2]}")

                if not stdout and not stderr and result.get("return_code") == 0:
                    parts.append("No output on stdout or stderr.")
                elif not stdout and not stderr and result.get("return_code") != 0:
                    parts.append("No output on stdout or stderr, but command failed.")
                summary = " ".join(parts)
            else:
                summary = (
                    f"Tool {tool_name} (shell command) produced non-dict result: "
                    f"{str(result)[:100]}"
                )
        elif tool_name in ["ripgrep_code_search", "retrieve_code_context_tool"]:
            if isinstance(result, dict):
                if "matches" in result and isinstance(result["matches"], list):
                    summary = f"Search returned {len(result['matches'])} matches."
                    logger.info(
                        "Search Result Transformation: Condensed "
                        f"{len(result['matches'])} matches to count summary"
                    )
                elif "retrieved_chunks" in result and isinstance(result["retrieved_chunks"], list):
                    summary = f"Retrieved {len(result['retrieved_chunks'])} code chunks."
                    logger.info(
                        "Code Retrieval Transformation: Condensed "
                        f"{len(result['retrieved_chunks'])} chunks to count summary"
                    )
                else:
                    summary = f"{tool_name} completed. Keys: {list(result.keys())}"
                    logger.info(
                        f"Generic Dict Transformation: Listed keys only: {list(result.keys())}"
                    )
            else:
                summary = f"{tool_name} completed with non-dict result."
        else:
            if isinstance(result, dict):
                important_keys = [
                    "status",
                    "message",
                    "summary",
                    "error",
                    "output",
                    "stdout",
                    "stderr",
                ]
                summary_parts = []
                logger.info(
                    "Generic Dict Transformation: Extracting important keys from "
                    f'"{list(result.keys())}"'
                )
                for key in important_keys:
                    if result.get(key):
                        val_str = str(result[key])
                        truncated_val = val_str[:300] + "..." if len(val_str) > 300 else val_str
                        summary_parts.append(f"{key}: {truncated_val}")
                        if len(val_str) > 300:
                            logger.info(
                                f"  Key '{key}': Truncated from {len(val_str)} to 300 characters"
                            )
                        else:
                            logger.info(
                                f"  Key '{key}': Kept full content ({len(val_str)} characters)"
                            )

                if summary_parts:
                    summary = f"Tool {tool_name}: " + "; ".join(summary_parts)
                else:
                    original_str = str(result)
                    summary = (
                        f"Tool {tool_name} completed. Result (truncated): "
                        f"{original_str[:800]}..."  # Increased from 200
                    )
                    logger.info(
                        f"Fallback Transformation: Truncated result from "
                        f"{len(original_str)} to 800 characters"
                    )
            elif isinstance(result, str):
                summary = (
                    f"Tool {tool_name} output (truncated): {result[:800]}..."  # Increased from 200
                )
                logger.info(
                    f"String Result Transformation: Truncated from {len(result)} to 800 characters"
                )
            else:
                summary = f"Tool {tool_name} completed with result type: {type(result).__name__}."
                logger.info(
                    f"Non-string Result Transformation: Converted "
                    f"{type(result).__name__} to type description"
                )

        # Apply final length limit and log if truncated
        if len(summary) > MAX_SUMMARY_LEN:
            original_summary_len = len(summary)
            summary = summary[: MAX_SUMMARY_LEN - len(TRUNC_MSG_TEMPLATE)] + TRUNC_MSG_TEMPLATE
            logger.info(
                f"Final Summary Transformation: Truncated from "
                f"{original_summary_len} to {MAX_SUMMARY_LEN} characters"
            )

        # Log the final transformed summary
        logger.info(f"Final Summary Size: {len(summary):,} characters")
        logger.info(f"Final Summary: {summary}")
        logger.info(
            f"Transformation Ratio: {(len(summary) / len(original_content) * 100):.1f}% of original"
        )
        logger.info("=" * 50)

        return summary

    def track_file_modification(self, file_path: str) -> None:
        if file_path not in self.state.last_modified_files:
            if len(self.state.last_modified_files) >= 15:  # Increased from 5 to track more files
                self.state.last_modified_files.pop(0)
            self.state.last_modified_files.append(file_path)
            logger.info(f"Tracked file modification: {file_path}")

    def _gather_proactive_context(self) -> dict[str, Any]:
        """Gather proactive context and cache it for token counting."""
        if self._proactive_context_cache is None:
            logger.info(
                "PROACTIVE CONTEXT: Gathering project files, Git history, and documentation..."
            )

            # Enhanced diagnostic logging
            logger.info("DIAGNOSTIC: Starting proactive context gathering...")
            logger.info(f"DIAGNOSTIC: Current working directory: {Path.cwd()}")
            logger.info(f"DIAGNOSTIC: Workspace root: {getattr(self, 'workspace_root', 'Not set')}")

            try:
                self._proactive_context_cache = self.proactive_gatherer.gather_all_context()

                # Detailed diagnostic logging
                if self._proactive_context_cache:
                    logger.info(
                        f"DIAGNOSTIC: Proactive context keys: "
                        f"{list(self._proactive_context_cache.keys())}"
                    )
                    for key, value in self._proactive_context_cache.items():
                        if isinstance(value, list):
                            logger.info(f"DIAGNOSTIC: {key}: {len(value)} items")
                            if len(value) > 0:
                                logger.info(f"DIAGNOSTIC: {key} sample: {str(value[0])[:100]}...")
                        elif isinstance(value, dict):
                            logger.info(
                                f"DIAGNOSTIC: {key}: dict with {len(value)} keys: "
                                f"{list(value.keys())[:5]}"
                            )
                        else:
                            logger.info(
                                f"DIAGNOSTIC: {key}: {type(value).__name__} - {str(value)[:100]}..."
                            )
                else:
                    logger.warning("DIAGNOSTIC: Proactive context gathering returned None/empty!")

            except Exception as e:
                logger.error(
                    f"DIAGNOSTIC: Exception during proactive context gathering: {e}",
                    exc_info=True,
                )
                self._proactive_context_cache = {}

            # Calculate total tokens for proactive context
            if self._proactive_context_cache:
                context_str = json.dumps(self._proactive_context_cache)
                self._proactive_context_tokens = self._count_tokens(context_str)
                logger.info(
                    f"PROACTIVE CONTEXT: Gathered context with "
                    f"{self._proactive_context_tokens:,} tokens"
                )

                # Log summary of what was gathered
                for key, value in self._proactive_context_cache.items():
                    if isinstance(value, list):
                        logger.info(f"  {key}: {len(value)} items")
                    else:
                        logger.info(f"  {key}: {type(value).__name__}")
            else:
                self._proactive_context_tokens = 0
                logger.warning(
                    "PROACTIVE CONTEXT: No proactive context gathered - investigating..."
                )

                # Additional diagnostics when gathering fails
                logger.info("DIAGNOSTIC: Checking proactive gatherer state...")
                logger.info(f"DIAGNOSTIC: Gatherer type: {type(self.proactive_gatherer)}")
                logger.info(
                    f"DIAGNOSTIC: Gatherer workspace: "
                    f"{getattr(self.proactive_gatherer, 'workspace_root', 'Not found')}"
                )

        return self._proactive_context_cache or {}

    def assemble_context(self, base_prompt_tokens: int) -> tuple[dict[str, Any], int]:
        """
        Assemble context dictionary with intelligent token management.

        Returns:
            Tuple of (context_dict, total_context_tokens)
        """
        logger.info(
            f"🧠 ASSEMBLING CONTEXT: Base prompt={base_prompt_tokens:,}, "
            f"Limit={self.max_token_limit:,}"
        )

        # Calculate available token budget with adaptive safety margin
        initial_safety_margin = 2000  # Reserve for response generation
        available_tokens = self.max_token_limit - base_prompt_tokens - initial_safety_margin

        # If budget is negative, reduce safety margin progressively
        if available_tokens <= 0:
            logger.warning(
                f"Initial token budget negative: {available_tokens:,}. Reducing safety margin."
            )
            # Try with reduced safety margins
            for reduced_margin in [1000, 500, 200, 100, 50]:
                available_tokens = self.max_token_limit - base_prompt_tokens - reduced_margin
                if available_tokens > 0:
                    logger.warning(f"Using reduced safety margin of {reduced_margin} tokens")
                    break

            # If still negative, use minimal emergency allocation
            if available_tokens <= 0:
                available_tokens = max(50, self.max_token_limit - base_prompt_tokens)
                logger.error(f"Emergency token allocation: {available_tokens:,} tokens")

        if available_tokens <= 0:
            logger.error(
                f"No tokens available for context! Base prompt too large: {base_prompt_tokens:,}"
            )
            # Return minimal emergency context
            return self._create_minimal_emergency_context(), 0

        logger.info(f"🧠 Available context budget: {available_tokens:,} tokens")

        # Try multiple optimization strategies
        context_dict, total_tokens = self._assemble_with_priority_optimization(available_tokens)

        if total_tokens > available_tokens:
            logger.warning(
                f"Priority optimization exceeded budget: {total_tokens:,} > {available_tokens:,}"
            )
            context_dict, total_tokens = self._assemble_with_emergency_optimization(
                available_tokens
            )

        # Track token growth
        self._token_growth_history.append((self.current_turn_number, total_tokens))
        self._last_context_tokens = total_tokens

        # Log optimization results
        utilization = (total_tokens / available_tokens) * 100 if available_tokens > 0 else 0
        logger.info("🧠 CONTEXT ASSEMBLY COMPLETE:")
        logger.info(
            f"   📊 Context tokens: {total_tokens:,} / {available_tokens:,} ({utilization:.1f}%)"
        )
        logger.info(f"   📊 Turns included: {len(context_dict.get('conversation_history', []))}")
        logger.info(f"   📊 Code snippets: {len(context_dict.get('code_snippets', []))}")
        logger.info(f"   📊 Tool results: {len(context_dict.get('tool_results', []))}")

        return context_dict, total_tokens

    def _assemble_with_priority_optimization(
        self, available_tokens: int
    ) -> tuple[dict[str, Any], int]:
        """Assemble context using priority-based optimization."""
        context_dict = {}
        used_tokens = 0

        # 1. CRITICAL: Core state (always include)
        self._update_state_token_counts()
        state_tokens = self.state.total_tokens
        if state_tokens <= available_tokens:
            context_dict.update(
                {
                    "core_goal": self.state.core_goal,
                    "current_phase": self.state.current_phase,
                    "key_decisions": self.state.key_decisions,
                    "last_modified_files": self.state.last_modified_files,
                }
            )
            used_tokens += state_tokens
            logger.debug(f"🧠 Added core state: {state_tokens:,} tokens")

        # 2. HIGH PRIORITY: Recent conversation with tool activity
        conversation_budget = min(available_tokens - used_tokens, available_tokens // 2)
        selected_turns, turn_tokens = self._select_prioritized_turns(conversation_budget)
        if selected_turns:
            context_dict["conversation_history"] = selected_turns
            used_tokens += turn_tokens
            logger.debug(
                f"🧠 Added conversation history: {turn_tokens:,} tokens "
                f"({len(selected_turns)} turns)"
            )

        # 3. HIGH PRIORITY: Recent tool results
        results_budget = min(available_tokens - used_tokens, available_tokens // 4)
        selected_results, results_tokens = self._select_prioritized_tool_results(results_budget)
        if selected_results:
            context_dict["tool_results"] = selected_results
            used_tokens += results_tokens
            logger.debug(
                f"🧠 Added tool results: {results_tokens:,} tokens "
                f"({len(selected_results)} results)"
            )

        # 4. MEDIUM PRIORITY: Code snippets (remaining budget)
        snippets_budget = available_tokens - used_tokens
        selected_snippets, snippets_tokens = self._select_prioritized_code_snippets(snippets_budget)
        if selected_snippets:
            context_dict["code_snippets"] = selected_snippets
            used_tokens += snippets_tokens
            logger.debug(
                f"🧠 Added code snippets: {snippets_tokens:,} tokens "
                f"({len(selected_snippets)} snippets)"
            )

        return context_dict, used_tokens

    def _assemble_with_emergency_optimization(
        self, available_tokens: int
    ) -> tuple[dict[str, Any], int]:
        """
        Emergency context assembly when normal optimization fails.
        Extremely aggressive truncation to fit within tiny token budgets.
        """
        logger.warning(f"⚠️  EMERGENCY OPTIMIZATION: Only {available_tokens} tokens available")

        # For extremely small budgets (<= 300 tokens), return minimal context
        if available_tokens <= 300:
            minimal_context = {
                "conversation_history": [],
                "code_snippets": [],
                "tool_results": [],
                "core_goal": "Context severely limited due to token constraints",
            }

            # If we have any recent turn, include just the user message
            if self.conversation_turns:
                latest_turn = self.conversation_turns[-1]
                user_message = latest_turn.user_message[:100]  # Truncate to 100 chars
                minimal_context["conversation_history"] = [
                    {
                        "role": "user",
                        "content": user_message + "..."
                        if len(latest_turn.user_message) > 100
                        else user_message,
                        "turn": latest_turn.turn_number,
                    }
                ]

            # Estimate minimal token count (very conservative)
            estimated_tokens = min(50, available_tokens - 10)  # Leave buffer
            return minimal_context, estimated_tokens

        # For small budgets (301-1000 tokens), use aggressive optimization
        context_dict = {
            "conversation_history": [],
            "code_snippets": [],
            "tool_results": [],
            "core_goal": self.state.core_goal or "Emergency mode - limited context",
            "current_phase": self.state.current_phase or "active",
        }

        remaining_tokens = available_tokens - 100  # Reserve for structure

        # Only include the most recent turn if space allows
        if self.conversation_turns and remaining_tokens > 50:
            latest_turn = self.conversation_turns[-1]

            # Drastically truncate user message
            user_msg = (
                latest_turn.user_message[:200] + "..."
                if len(latest_turn.user_message) > 200
                else latest_turn.user_message
            )
            user_tokens = len(user_msg.split()) * 1.3  # Conservative estimate

            if user_tokens <= remaining_tokens:
                context_dict["conversation_history"].append(
                    {
                        "role": "user",
                        "content": user_msg,
                        "turn": latest_turn.turn_number,
                    }
                )
                remaining_tokens -= user_tokens

        # Only include critical code snippets if space allows
        if remaining_tokens > 50 and self.code_snippets:
            # Sort by importance and recency
            recent_snippets = sorted(
                self.code_snippets.values(),
                key=lambda x: (x.get("last_accessed", 0), -len(x.get("content", ""))),
                reverse=True,
            )

            for snippet in recent_snippets[:2]:  # Max 2 snippets
                # Extremely truncated snippet
                content = (
                    snippet.get("content", "")[:100] + "..."
                    if len(snippet.get("content", "")) > 100
                    else snippet.get("content", "")
                )
                snippet_tokens = len(content.split()) * 1.3

                if snippet_tokens <= remaining_tokens:
                    context_dict["code_snippets"].append(
                        {
                            "file_path": snippet.get("file_path", "unknown"),
                            "content": content,
                            "line_start": snippet.get("line_start", 1),
                            "line_end": snippet.get("line_end", 1),
                        }
                    )
                    remaining_tokens -= snippet_tokens
                else:
                    break

        # Calculate actual token usage
        total_content = str(context_dict)
        estimated_tokens = len(total_content.split()) * 1.3

        # Final safety check - if still too large, return absolute minimum
        if estimated_tokens > available_tokens:
            logger.warning(
                f"Emergency optimization still too large "
                f"({estimated_tokens} > {available_tokens}), "
                f"returning absolute minimum"
            )
            return {
                "conversation_history": [],
                "code_snippets": [],
                "tool_results": [],
                "core_goal": "Minimal context",
            }, 20

        logger.warning(f"Emergency optimization complete: {estimated_tokens} tokens used")
        return context_dict, int(estimated_tokens)

    def _select_prioritized_turns(self, budget: int) -> tuple[list[dict[str, Any]], int]:
        """Select conversation turns based on priority and token budget."""
        if not self.conversation_turns:
            return [], 0

        # Sort by priority then recency
        sorted_turns = sorted(
            self.conversation_turns, key=lambda t: (t.priority.value, -t.turn_number)
        )

        selected = []
        used_tokens = 0

        for turn in sorted_turns:
            if (
                used_tokens + turn.total_tokens <= budget
                and len(selected) < self.target_recent_turns
            ):
                turn_dict = {
                    "turn_number": turn.turn_number,
                    "user_message": turn.user_message,
                    "agent_message": turn.agent_message,
                    "tool_calls": turn.tool_calls,
                    "timestamp": turn.timestamp,
                    "has_tool_activity": turn.has_tool_activity,
                }
                selected.append(turn_dict)
                used_tokens += turn.total_tokens
            elif used_tokens + turn.total_tokens > budget:
                break

        # Sort selected turns by turn number for chronological order
        selected.sort(key=lambda t: t["turn_number"])
        return selected, used_tokens

    def _select_prioritized_tool_results(self, budget: int) -> tuple[list[dict[str, Any]], int]:
        """Select tool results based on priority and token budget."""
        if not self.tool_results:
            return [], 0

        # Sort by priority then recency
        sorted_results = sorted(self.tool_results, key=lambda r: (r.priority.value, -r.turn_number))

        selected = []
        used_tokens = 0

        for result in sorted_results:
            if (
                used_tokens + result.token_count <= budget
                and len(selected) < self.target_tool_results
            ):
                result_dict = {
                    "tool_name": result.tool_name,
                    "response": result.full_result,
                    "summary": result.result_summary,
                    "is_error": result.is_error,
                    "turn_number": result.turn_number,
                }
                selected.append(result_dict)
                used_tokens += result.token_count
            elif used_tokens + result.token_count > budget:
                break

        return selected, used_tokens

    def _select_prioritized_code_snippets(self, budget: int) -> tuple[list[dict[str, Any]], int]:
        """Select code snippets based on relevance and token budget."""
        if not self.code_snippets:
            return [], 0

        # Sort by relevance score and recency
        sorted_snippets = sorted(
            self.code_snippets, key=lambda s: (-s.relevance_score, -s.last_accessed)
        )

        selected = []
        used_tokens = 0

        for snippet in sorted_snippets:
            if (
                used_tokens + snippet.token_count <= budget
                and len(selected) < self.target_code_snippets
            ):
                snippet_dict = {
                    "file_path": snippet.file_path,
                    "code": snippet.code,
                    "start_line": snippet.start_line,
                    "end_line": snippet.end_line,
                    "last_accessed": snippet.last_accessed,
                    "relevance_score": snippet.relevance_score,
                }
                selected.append(snippet_dict)
                used_tokens += snippet.token_count
            elif used_tokens + snippet.token_count > budget:
                break

        return selected, used_tokens

    def _update_state_token_counts(self) -> None:
        """Update token counts for state elements."""
        self.state.core_goal_tokens = self._count_tokens(self.state.core_goal)
        self.state.current_phase_tokens = self._count_tokens(self.state.current_phase)

        try:
            decisions_json = json.dumps(self.state.key_decisions)
            self.state.decisions_tokens = self._count_tokens(decisions_json)
        except Exception:
            self.state.decisions_tokens = self._count_tokens(str(self.state.key_decisions))

        try:
            files_json = json.dumps(self.state.last_modified_files)
            self.state.files_tokens = self._count_tokens(files_json)
        except Exception:
            self.state.files_tokens = self._count_tokens(str(self.state.last_modified_files))

    def _calculate_adaptive_limits(self) -> dict[str, int]:
        """Calculate adaptive limits based on conversation progress."""
        conversation_length = len(self.conversation_turns)

        if conversation_length <= 3:
            # Early conversation: generous limits
            return {
                "target_recent_turns": 5,
                "target_code_snippets": 8,
                "target_tool_results": 10,
                "emergency_turns": 2,
                "emergency_snippets": 2,
                "emergency_results": 3,
            }
        if conversation_length <= 10:
            # Mid conversation: balanced limits
            return {
                "target_recent_turns": 4,
                "target_code_snippets": 5,
                "target_tool_results": 7,
                "emergency_turns": 2,
                "emergency_snippets": 1,
                "emergency_results": 2,
            }
        # Long conversation: conservative limits
        return {
            "target_recent_turns": 3,
            "target_code_snippets": 3,
            "target_tool_results": 5,
            "emergency_turns": 1,
            "emergency_snippets": 0,
            "emergency_results": 1,
        }

    def get_token_growth_analysis(self) -> dict[str, Any]:
        """Analyze token growth patterns over conversation history."""
        if len(self._token_growth_history) < 2:
            return {"status": "insufficient_data"}

        # Calculate growth rate
        first_turn, first_tokens = self._token_growth_history[0]
        last_turn, last_tokens = self._token_growth_history[-1]

        growth_rate = ((last_tokens - first_tokens) / first_tokens * 100) if first_tokens > 0 else 0
        avg_tokens_per_turn = sum(tokens for _, tokens in self._token_growth_history) / len(
            self._token_growth_history
        )

        # Detect concerning patterns
        concerns = []
        if growth_rate > 50:
            concerns.append(f"High growth rate: {growth_rate:.1f}%")
        if last_tokens > self.max_token_limit * 0.8:
            concerns.append(f"Approaching token limit: {last_tokens:,}/{self.max_token_limit:,}")

        return {
            "status": "analyzed",
            "total_turns": len(self._token_growth_history),
            "growth_rate_percent": growth_rate,
            "current_tokens": last_tokens,
            "average_tokens_per_turn": avg_tokens_per_turn,
            "concerns": concerns,
            "adaptive_limits": self._adaptive_limits,
        }

    def expand_context_dynamically(
        self, current_errors: Optional[list[str]] = None, max_expansion_files: int = 10
    ) -> list[DiscoveredContent]:
        """Perform dynamic context expansion to discover relevant files."""

        if current_errors is None:
            current_errors = []

        # Extract current files in context
        current_files = set()
        for snippet in self.code_snippets:
            current_files.add(snippet.file_path)
        for file_path in self.state.last_modified_files:
            current_files.add(file_path)

        # Extract keywords from current goal and phase
        keywords = []
        if self.state.core_goal:
            keywords.extend([word for word in self.state.core_goal.split() if len(word) > 3])
        if self.state.current_phase:
            keywords.extend([word for word in self.state.current_phase.split() if len(word) > 3])

        # Create expansion context
        expansion_context = ExpansionContext(
            current_task=self.state.core_goal,
            error_context=len(current_errors) > 0,
            file_context=current_files,
            keywords=keywords,
            max_files_to_explore=max_expansion_files,
            max_depth=3,
            current_working_directory=".",
        )

        # Perform expansion
        return self.dynamic_expander.expand_context(
            expansion_context, current_files, current_errors
        )

    def auto_add_discovered_content(
        self, discovered_content: list[DiscoveredContent], max_files_to_add: int = 5
    ) -> int:
        """Automatically add discovered content to context."""

        added_count = 0

        for content in discovered_content[:max_files_to_add]:
            try:
                if (
                    content.content_type in ["python_code", "js_code"]
                    and content.size_bytes < 50000
                ):
                    # Add code files as code snippets
                    with Path(content.full_path).open(encoding="utf-8") as f:
                        file_content = f.read()

                    # Add as full file content
                    self.add_full_file_content(content.file_path, file_content)
                    added_count += 1
                    logger.info(
                        f"AUTO-ADDED: Code file {content.file_path} ({content.relevance_score:.2f})"
                    )

                elif (
                    content.content_type in ["config", "dependency"] and content.size_bytes < 20000
                ):
                    # Add config files to context
                    with Path(content.full_path).open(encoding="utf-8") as f:
                        file_content = f.read()

                    # Create a summarized version for config files
                    context = SummarizationContext(
                        current_task=self.state.core_goal,
                        relevant_keywords=[
                            word for word in self.state.core_goal.split() if len(word) > 3
                        ]
                        if self.state.core_goal
                        else [],
                        target_length=1000,
                    )

                    summary = self.intelligent_summarizer.summarize_content(
                        file_content, context, ContentType.CONFIGURATION
                    )

                    self.add_code_snippet(
                        content.file_path, summary, 1, len(file_content.split("\n"))
                    )
                    added_count += 1
                    logger.info(
                        f"AUTO-ADDED: Config file {content.file_path} "
                        f"(summarized, {content.relevance_score:.2f})"
                    )

                elif content.content_type == "documentation" and content.size_bytes < 30000:
                    # Add documentation with summarization
                    with Path(content.full_path).open(encoding="utf-8") as f:
                        file_content = f.read()

                    context = SummarizationContext(
                        current_task=self.state.core_goal,
                        relevant_keywords=[
                            word for word in self.state.core_goal.split() if len(word) > 3
                        ]
                        if self.state.core_goal
                        else [],
                        target_length=800,
                    )

                    summary = self.intelligent_summarizer.summarize_content(
                        file_content, context, ContentType.DOCUMENTATION
                    )

                    self.add_code_snippet(
                        content.file_path, summary, 1, len(file_content.split("\n"))
                    )
                    added_count += 1
                    logger.info(
                        f"AUTO-ADDED: Documentation {content.file_path} "
                        f"(summarized, {content.relevance_score:.2f})"
                    )

            except Exception as e:
                logger.warning(f"Could not auto-add discovered content {content.file_path}: {e}")

        return added_count

    def _create_minimal_emergency_context(self) -> dict[str, Any]:
        """Create minimal emergency context when tokens are critically low."""
        context = {}

        # Only include core goal if it exists and is short
        if self.state.core_goal and len(self.state.core_goal) < 100:
            context["core_goal"] = self.state.core_goal

        # Include most recent conversation turn if very short
        if self.conversation_turns:
            recent_turn = self.conversation_turns[-1]
            if recent_turn.user_message and len(recent_turn.user_message) < 50:
                context["conversation_history"] = [
                    {
                        "turn_number": recent_turn.turn_number,
                        "user_message": recent_turn.user_message,
                        "agent_message": recent_turn.agent_message[:100]
                        if recent_turn.agent_message
                        else None,
                    }
                ]

        logger.warning(f"🚨 Created minimal emergency context: {len(context)} components")
        return context
