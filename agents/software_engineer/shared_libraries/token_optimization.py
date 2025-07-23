"""Token optimization utilities for Software Engineer Agent."""

import functools
import logging
from typing import Callable, Optional

from google import genai
from google.adk.models.llm_request import LlmRequest
from google.genai.types import Content, CountTokensResponse, Part

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

logger = logging.getLogger(__name__)


def _token_counting_error_handler(func):
    """Decorator to handle token counting errors gracefully."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Token counting error in {func.__name__}: {e}")
            # Fallback to character-based estimation
            if args and isinstance(args[1], str):  # assuming text is second arg
                return len(args[1]) // 4
            return 0

    return wrapper


class TokenCounter:
    """Token counting with multiple fallback strategies for reliability."""

    def __init__(self, model_name: str, llm_client: Optional[genai.Client] = None):
        """Initialize token counter with model-specific configuration.

        Args:
            model_name: The model name for token counting strategy selection
            llm_client: Optional GenAI client for native token counting
        """
        self.model_name = model_name
        self.llm_client = llm_client
        self._token_counting_fn = self._initialize_token_counting_strategy()

    def _initialize_token_counting_strategy(self) -> Callable[[str], int]:
        """Initialize the most accurate available token counting strategy.

        Returns:
            A function that takes text and returns token count
        """
        # Strategy 1: Native Google GenAI client's count_tokens
        if self._try_native_google_counter():
            logger.info(f"Using native Google GenAI token counter for {self.model_name}")
            return self._native_google_counter

        # Strategy 2: Tiktoken
        if TIKTOKEN_AVAILABLE and self._try_tiktoken_counter():
            logger.info(f"Using tiktoken token counter for {self.model_name}")
            return self._tiktoken_counter

        # Strategy 3: Character count fallback
        logger.warning(
            f"No advanced tokenizer available for {self.model_name}. "
            "Using character-based token estimation (len // 4)."
        )
        return self._character_count_fallback

    def _try_native_google_counter(self) -> bool:
        """Test if native Google GenAI token counting is available."""
        if (
            self.llm_client is not None
            and isinstance(self.llm_client, genai.Client)
            and hasattr(self.llm_client, "models")
            and hasattr(self.llm_client.models, "count_tokens")
        ):
            try:
                # Test with a small sample
                test_content = Content(parts=[Part(text="test")])
                response: CountTokensResponse = self.llm_client.models.count_tokens(
                    model=self.model_name, contents=test_content
                )
                return response.total_tokens > 0
            except Exception as e:
                logger.debug(f"Native Google counter test failed: {e}")
                return False
        return False

    def _try_tiktoken_counter(self) -> bool:
        """Test if tiktoken is available and working."""
        try:
            tokenizer = None
            try:
                tokenizer = tiktoken.encoding_for_model(self.model_name)
            except KeyError:
                # Model not found, try generic encoder
                tokenizer = tiktoken.get_encoding("cl100k_base")

            if tokenizer:
                # Test tokenizer
                test_tokens = tokenizer.encode("test")
                self._tiktoken_tokenizer = tokenizer
                return len(test_tokens) > 0
        except Exception as e:
            logger.debug(f"Tiktoken test failed: {e}")
        return False

    @_token_counting_error_handler
    def _native_google_counter(self, text: str) -> int:
        """Count tokens using native Google GenAI client."""
        if not text:
            return 0

        content_for_counting = Content(parts=[Part(text=text)])
        response: CountTokensResponse = self.llm_client.models.count_tokens(
            model=self.model_name, contents=content_for_counting
        )
        return response.total_tokens

    @_token_counting_error_handler
    def _tiktoken_counter(self, text: str) -> int:
        """Count tokens using tiktoken library."""
        if not text:
            return 0
        return len(self._tiktoken_tokenizer.encode(text))

    def _character_count_fallback(self, text: str) -> int:
        """Fallback token counting using character estimation."""
        if not text:
            return 0
        return len(text) // 4

    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text.

        Args:
            text: The text to count tokens for

        Returns:
            The number of tokens in the text
        """
        # Handle None values explicitly
        if text is None:
            return 0

        if not isinstance(text, str):
            logger.debug(
                f"Non-string type ({type(text)}) passed to count_tokens. "
                "Converting to string for counting."
            )
            text = str(text)

        if not text:
            return 0

        try:
            return self._token_counting_fn(text)
        except Exception as e:
            logger.error(
                f"Error during token counting for text '{text[:50]}...': {e}. "
                "Falling back to character count."
            )
            return len(text) // 4

    def count_llm_request_tokens(self, llm_request: LlmRequest) -> dict[str, int]:
        """Count tokens for different components of an LLM request.

        Args:
            llm_request: The LLM request to analyze

        Returns:
            Dictionary with token counts for different components
        """
        token_breakdown = {
            "system_instruction": 0,
            "tools": 0,
            "user_message": 0,
            "conversation_history": 0,
            "total": 0,
        }

        try:
            # Count system instruction tokens
            if hasattr(llm_request, "system_instruction") and llm_request.system_instruction:
                token_breakdown["system_instruction"] = self.count_tokens(
                    str(llm_request.system_instruction)
                )

            # Count tools definition tokens
            if hasattr(llm_request, "tools") and llm_request.tools:
                token_breakdown["tools"] = self.count_tokens(str(llm_request.tools))

            # Count conversation content tokens
            if hasattr(llm_request, "contents") and isinstance(llm_request.contents, list):
                conversation_tokens = 0
                current_user_tokens = 0

                for content in llm_request.contents:
                    if hasattr(content, "parts") and content.parts:
                        for part in content.parts:
                            if hasattr(part, "text") and part.text:
                                part_tokens = self.count_tokens(part.text)
                                conversation_tokens += part_tokens

                                # Try to identify current user message
                                if content.role == "user" and not part.text.startswith(
                                    "SYSTEM CONTEXT (JSON):"
                                ):
                                    current_user_tokens = part_tokens

                token_breakdown["conversation_history"] = conversation_tokens
                token_breakdown["user_message"] = current_user_tokens

            # Calculate total
            token_breakdown["total"] = sum(v for k, v in token_breakdown.items() if k != "total")

        except Exception as e:
            logger.error(f"Error counting LLM request tokens: {e}")

        return token_breakdown


class ContextBudgetManager:
    """Manages token budget calculation and allocation."""

    def __init__(self, max_token_limit: int = 1_000_000):
        """Initialize budget manager.

        Args:
            max_token_limit: Maximum tokens allowed for the model
        """
        self.max_token_limit = max_token_limit

    def calculate_base_prompt_tokens(
        self, llm_request: LlmRequest, token_counter: TokenCounter
    ) -> int:
        """Calculate base prompt tokens (non-optimizable components).

        Args:
            llm_request: The LLM request to analyze
            token_counter: Token counter instance

        Returns:
            Number of base prompt tokens
        """
        token_breakdown = token_counter.count_llm_request_tokens(llm_request)

        # Base prompt includes system instruction, tools, and current user message
        base_tokens = (
            token_breakdown["system_instruction"]
            + token_breakdown["tools"]
            + token_breakdown["user_message"]
        )

        logger.debug(f"Base prompt tokens: {base_tokens:,}")
        logger.debug(f"  System instruction: {token_breakdown['system_instruction']:,}")
        logger.debug(f"  Tools: {token_breakdown['tools']:,}")
        logger.debug(f"  User message: {token_breakdown['user_message']:,}")

        return base_tokens

    def determine_safety_margin(self, base_tokens: int) -> int:
        """Determine appropriate safety margin based on base token usage.

        Args:
            base_tokens: Number of base prompt tokens

        Returns:
            Safety margin in tokens
        """
        # Progressive safety margins based on available space
        remaining_capacity = self.max_token_limit - base_tokens

        if remaining_capacity > 100_000:
            return 2000  # Conservative margin when plenty of space
        if remaining_capacity > 50_000:
            return 1000  # Moderate margin
        if remaining_capacity > 10_000:
            return 500  # Tight margin
        if remaining_capacity > 1_000:
            return 200  # Very tight margin
        return 50  # Emergency minimal margin

    def calculate_available_context_budget(
        self, llm_request: LlmRequest, token_counter: TokenCounter
    ) -> tuple[int, dict[str, int]]:
        """Calculate available budget for context optimization.

        Args:
            llm_request: The LLM request to analyze
            token_counter: Token counter instance

        Returns:
            Tuple of (available_budget, budget_breakdown)
        """
        base_tokens = self.calculate_base_prompt_tokens(llm_request, token_counter)
        safety_margin = self.determine_safety_margin(base_tokens)

        available_budget = self.max_token_limit - base_tokens - safety_margin

        budget_breakdown = {
            "max_limit": self.max_token_limit,
            "base_tokens": base_tokens,
            "safety_margin": safety_margin,
            "available_budget": max(0, available_budget),
            "utilization_pct": (base_tokens / self.max_token_limit) * 100,
        }

        # Log budget information
        logger.info("Token budget calculation:")
        logger.info(f"  Max limit: {self.max_token_limit:,}")
        logger.info(f"  Base tokens: {base_tokens:,}")
        logger.info(f"  Safety margin: {safety_margin:,}")
        logger.info(f"  Available budget: {budget_breakdown['available_budget']:,}")
        logger.info(f"  Base utilization: {budget_breakdown['utilization_pct']:.1f}%")

        return budget_breakdown["available_budget"], budget_breakdown
