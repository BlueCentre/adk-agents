"""Smart conversation filtering for token optimization."""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Optional

from .conversation_analyzer import ConversationAnalyzer, ConversationSegment, ToolChain
from .token_optimization import TokenCounter

logger = logging.getLogger(__name__)


class FilterStrategy(Enum):
    """Different filtering strategies for conversation optimization."""

    CONSERVATIVE = "conservative"  # Keep most content, minimal filtering
    MODERATE = "moderate"  # Balanced filtering approach
    AGGRESSIVE = "aggressive"  # Aggressive filtering to maximize token savings


@dataclass
class FilteringPolicy:
    """Configuration policy for conversation filtering behavior."""

    # Core filtering settings
    strategy: FilterStrategy = FilterStrategy.MODERATE
    preserve_tool_chains: bool = True
    preserve_context_injections: bool = True
    preserve_current_conversation: bool = True

    # Token management
    target_reduction_pct: float = 50.0  # Target percentage reduction
    min_conversations_to_keep: int = 2  # Minimum conversation turns to preserve
    max_conversations_to_keep: int = 10  # Maximum conversation turns to keep

    # Advanced settings
    preserve_system_messages: bool = True
    preserve_error_information: bool = True
    compress_old_conversations: bool = False
    summarize_removed_content: bool = False


@dataclass
class FilterResult:
    """Result of conversation filtering operation."""

    original_content: list[Any]
    filtered_content: list[Any]
    removed_content: list[Any]

    # Token statistics
    original_tokens: int
    filtered_tokens: int
    tokens_saved: int
    reduction_pct: float

    # Filtering statistics
    conversations_removed: int
    tool_chains_preserved: int
    context_injections_preserved: int

    # Metadata
    strategy_used: FilterStrategy
    filtering_applied: bool


class ConversationFilter:
    """Smart conversation filtering for token optimization."""

    def __init__(
        self,
        analyzer: Optional[ConversationAnalyzer] = None,
        token_counter: Optional[TokenCounter] = None,
    ):
        """
        Initialize the conversation filter.

        Args:
            analyzer: ConversationAnalyzer instance (created if not provided)
            token_counter: TokenCounter instance (optional, for token calculations)
        """
        self.analyzer = analyzer or ConversationAnalyzer()
        self.token_counter = token_counter

    def filter_conversation(
        self,
        contents: list[Any],
        target_token_budget: int,
        policy: Optional[FilteringPolicy] = None,
    ) -> FilterResult:
        """
        Filter conversation contents to fit within target token budget.

        Args:
            contents: List of conversation contents/messages
            target_token_budget: Maximum tokens allowed after filtering
            policy: Filtering policy configuration

        Returns:
            FilterResult with filtered content and statistics
        """
        if not contents:
            return self._create_empty_result(contents)

        # Use default policy if none provided
        policy = policy or FilteringPolicy()

        logger.info(
            f"Starting conversation filtering with {len(contents)} messages, "
            f"target budget: {target_token_budget:,} tokens, strategy: {policy.strategy.value}"
        )

        # Analyze conversation structure
        analysis = self.analyzer.analyze_conversation_structure(contents)

        # Calculate original token count if token counter available
        original_tokens = 0
        if self.token_counter:
            original_tokens = self._calculate_content_tokens(contents)

            # Check if filtering is even needed
            if original_tokens <= target_token_budget:
                logger.info(
                    f"No filtering needed: {original_tokens:,} tokens <= "
                    f"{target_token_budget:,} budget"
                )
                return self._create_no_filter_result(contents, original_tokens, policy.strategy)

        # Apply filtering strategy
        filtered_content = self._apply_filtering_strategy(
            contents, analysis, target_token_budget, policy
        )

        # Calculate token savings if token counter available
        filtered_tokens = 0
        tokens_saved = 0
        reduction_pct = 0.0
        if self.token_counter:
            filtered_tokens = self._calculate_content_tokens(filtered_content)
            tokens_saved = original_tokens - filtered_tokens
            reduction_pct = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0.0

        # Create filter result
        removed_content = self._identify_removed_content(contents, filtered_content)

        result = FilterResult(
            original_content=contents,
            filtered_content=filtered_content,
            removed_content=removed_content,
            original_tokens=original_tokens,
            filtered_tokens=filtered_tokens,
            tokens_saved=tokens_saved,
            reduction_pct=reduction_pct,
            conversations_removed=len(contents) - len(filtered_content),
            tool_chains_preserved=len(
                [
                    tc
                    for tc in analysis["tool_chains"]
                    if self._is_preserved_in_filtered(tc, filtered_content)
                ]
            ),
            context_injections_preserved=len(
                [
                    ci
                    for ci in analysis["context_injections"]
                    if self._is_content_preserved(ci[1], filtered_content)
                ]
            ),
            strategy_used=policy.strategy,
            filtering_applied=len(filtered_content) < len(contents),
        )

        logger.info(
            f"Filtering complete: {len(contents)} -> {len(filtered_content)} messages "
            f"({result.tokens_saved:,} tokens saved, {result.reduction_pct:.1f}% reduction)"
        )

        return result

    def _apply_filtering_strategy(
        self,
        contents: list[Any],
        analysis: dict[str, Any],
        target_budget: int,
        policy: FilteringPolicy,
    ) -> list[Any]:
        """
        Apply the configured filtering strategy to reduce token usage.

        Args:
            contents: Original conversation contents
            analysis: Conversation structure analysis
            target_budget: Target token budget
            policy: Filtering policy configuration

        Returns:
            Filtered conversation contents
        """
        # Start with all content
        preserved_content = list(contents)

        # Always preserve certain types of content
        must_preserve_indices = self._identify_must_preserve_content(analysis, policy)

        # Get conversation segments ordered by priority
        prioritized_segments = self._prioritize_conversation_segments(
            analysis["conversation_segments"], analysis, policy
        )

        # Apply strategy-specific filtering
        if policy.strategy == FilterStrategy.CONSERVATIVE:
            preserved_content = self._apply_conservative_filtering(
                contents, prioritized_segments, must_preserve_indices, policy
            )
        elif policy.strategy == FilterStrategy.MODERATE:
            preserved_content = self._apply_moderate_filtering(
                contents, prioritized_segments, must_preserve_indices, target_budget, policy
            )
        elif policy.strategy == FilterStrategy.AGGRESSIVE:
            preserved_content = self._apply_aggressive_filtering(
                contents, prioritized_segments, must_preserve_indices, target_budget, policy
            )

        return preserved_content

    def _identify_must_preserve_content(
        self, analysis: dict[str, Any], policy: FilteringPolicy
    ) -> set[int]:
        """
        Identify content that must always be preserved.

        Args:
            analysis: Conversation structure analysis
            policy: Filtering policy configuration

        Returns:
            Set of content indices that must be preserved
        """
        must_preserve = set()

        # Always preserve system messages if configured
        if policy.preserve_system_messages:
            for idx, _content in analysis["system_messages"]:
                must_preserve.add(idx)

        # Always preserve context injections if configured
        if policy.preserve_context_injections:
            for idx, _content in analysis["context_injections"]:
                must_preserve.add(idx)

        # Always preserve complete tool chains if configured
        if policy.preserve_tool_chains:
            for tool_chain in analysis["tool_chains"]:
                # Preserve all messages in the tool chain
                for i in range(
                    tool_chain.start_index, (tool_chain.end_index or tool_chain.start_index) + 1
                ):
                    must_preserve.add(i)

        # Always preserve current conversation if configured
        if policy.preserve_current_conversation:
            if analysis["current_user_message"]:
                # Find the index of current user message
                for i, content in enumerate(
                    analysis["original_content"] if "original_content" in analysis else []
                ):
                    if content == analysis["current_user_message"]:
                        must_preserve.add(i)
                        # Also preserve any responses after it
                        for j in range(
                            i + 1,
                            len(
                                analysis["original_content"]
                                if "original_content" in analysis
                                else []
                            ),
                        ):
                            must_preserve.add(j)
                        break

        return must_preserve

    def _prioritize_conversation_segments(
        self, segments: list[ConversationSegment], analysis: dict[str, Any], policy: FilteringPolicy
    ) -> list[ConversationSegment]:
        """
        Prioritize conversation segments for filtering decisions.

        Args:
            segments: List of conversation segments
            analysis: Full conversation analysis
            policy: Filtering policy configuration

        Returns:
            Segments ordered by priority (highest first)
        """

        def segment_priority_score(segment: ConversationSegment) -> float:
            """Calculate priority score for a segment (higher = more important)."""
            score = 0.0

            # Recent conversations are more important
            position_score = (len(segments) - segments.index(segment)) / len(segments)
            score += position_score * 100

            # Tool activity increases importance
            if segment.has_tool_activity:
                score += 50

            # Conversations with errors are important for context
            for message in segment.messages:
                if self.analyzer._has_tool_errors(message):
                    score += 25
                    break

            # Longer conversations may be more important
            message_count_score = min(len(segment.messages) / 10, 1.0) * 10
            score += message_count_score

            # If policy emphasizes error information, boost error-containing segments
            if policy.preserve_error_information:
                for message in segment.messages:
                    if self.analyzer._has_tool_errors(message):
                        score += 20
                        break

            # Consider current user message priority from analysis
            if analysis.get("current_user_message") and any(
                msg == analysis["current_user_message"] for msg in segment.messages
            ):
                score += 75  # High priority for current conversation

            return score

        # Sort segments by priority (highest first)
        prioritized = sorted(segments, key=segment_priority_score, reverse=True)

        logger.debug(
            f"Prioritized {len(segments)} conversation segments: "
            f"scores = {[segment_priority_score(s) for s in prioritized[:3]][:3]}"
        )

        return prioritized

    def _apply_conservative_filtering(
        self,
        contents: list[Any],
        prioritized_segments: list[ConversationSegment],
        must_preserve: set[int],
        policy: FilteringPolicy,
    ) -> list[Any]:
        """Apply conservative filtering (minimal removal)."""
        # Conservative: only remove oldest, non-essential conversations
        # Keep at least min_conversations_to_keep, prefer max_conversations_to_keep

        segments_to_keep = min(
            len(prioritized_segments),
            max(policy.min_conversations_to_keep, len(prioritized_segments) - 2),
        )

        preserved_indices = set(must_preserve)

        # Keep the highest priority segments
        for segment in prioritized_segments[:segments_to_keep]:
            for i in range(segment.start_index, segment.end_index + 1):
                preserved_indices.add(i)

        return [contents[i] for i in sorted(preserved_indices) if i < len(contents)]

    def _apply_moderate_filtering(
        self,
        contents: list[Any],
        prioritized_segments: list[ConversationSegment],
        must_preserve: set[int],
        target_budget: int,
        policy: FilteringPolicy,
    ) -> list[Any]:
        """Apply moderate filtering (balanced approach)."""
        preserved_indices = set(must_preserve)

        # Add segments by priority until we have enough content
        target_segments = min(
            len(prioritized_segments),
            max(policy.min_conversations_to_keep, policy.max_conversations_to_keep // 2),
        )

        for segment in prioritized_segments[:target_segments]:
            for i in range(segment.start_index, segment.end_index + 1):
                preserved_indices.add(i)

        # If we have token counter, try to fit within budget
        if self.token_counter and target_budget > 0:
            preserved_content = [
                contents[i] for i in sorted(preserved_indices) if i < len(contents)
            ]

            # Remove segments from the end until we fit budget
            while len(prioritized_segments[:target_segments]) > policy.min_conversations_to_keep:
                tokens = self._calculate_content_tokens(preserved_content)
                if tokens <= target_budget:
                    break

                # Remove lowest priority segment that's not must-preserve
                removed_segment = None
                for segment in reversed(prioritized_segments[:target_segments]):
                    if not any(
                        i in must_preserve
                        for i in range(segment.start_index, segment.end_index + 1)
                    ):
                        removed_segment = segment
                        break

                if removed_segment:
                    for i in range(removed_segment.start_index, removed_segment.end_index + 1):
                        preserved_indices.discard(i)
                    target_segments -= 1
                    preserved_content = [
                        contents[i] for i in sorted(preserved_indices) if i < len(contents)
                    ]
                else:
                    break  # Can't remove any more without violating must-preserve

        return [contents[i] for i in sorted(preserved_indices) if i < len(contents)]

    def _apply_aggressive_filtering(
        self,
        contents: list[Any],
        prioritized_segments: list[ConversationSegment],
        must_preserve: set[int],
        target_budget: int,
        policy: FilteringPolicy,
    ) -> list[Any]:
        """Apply aggressive filtering (maximum token reduction)."""
        preserved_indices = set(must_preserve)

        # Aggressive: only keep minimum required segments + current conversation
        target_segments = min(len(prioritized_segments), policy.min_conversations_to_keep)

        # Keep only the highest priority segments
        for segment in prioritized_segments[:target_segments]:
            for i in range(segment.start_index, segment.end_index + 1):
                preserved_indices.add(i)

        # If we have token counter, aggressively remove content to fit budget
        if self.token_counter and target_budget > 0:
            preserved_content = [
                contents[i] for i in sorted(preserved_indices) if i < len(contents)
            ]
            tokens = self._calculate_content_tokens(preserved_content)

            # If still over budget, try more aggressive measures
            if tokens > target_budget:
                # Remove individual messages that aren't absolutely essential
                removable_indices = []
                for i in sorted(preserved_indices):
                    if i not in must_preserve:
                        removable_indices.append(i)

                # Remove from the middle (keep start and end context)
                for i in removable_indices[
                    len(removable_indices) // 4 : -len(removable_indices) // 4
                ]:
                    preserved_indices.discard(i)
                    preserved_content = [
                        contents[j] for j in sorted(preserved_indices) if j < len(contents)
                    ]
                    tokens = self._calculate_content_tokens(preserved_content)
                    if tokens <= target_budget:
                        break

        return [contents[i] for i in sorted(preserved_indices) if i < len(contents)]

    def _calculate_content_tokens(self, contents: list[Any]) -> int:
        """Calculate total tokens for content list."""
        if not self.token_counter:
            return 0

        total_tokens = 0
        for content in contents:
            try:
                # Extract text and count tokens
                text = self.analyzer._extract_text_from_content(content)
                if text and isinstance(text, str):
                    total_tokens += self.token_counter.count_tokens(text)
            except Exception as e:
                logger.debug(f"Error counting tokens for content: {e}")

        return total_tokens

    def _identify_removed_content(self, original: list[Any], filtered: list[Any]) -> list[Any]:
        """Identify content that was removed during filtering."""
        filtered_set = {id(item) for item in filtered}
        return [item for item in original if id(item) not in filtered_set]

    def _is_preserved_in_filtered(self, tool_chain: ToolChain, filtered_content: list[Any]) -> bool:
        """Check if a tool chain is preserved in filtered content."""
        if not tool_chain.user_message or not tool_chain.assistant_with_tools:
            return False

        # Check if key components are present
        filtered_ids = {id(item) for item in filtered_content}
        return (
            id(tool_chain.user_message) in filtered_ids
            and id(tool_chain.assistant_with_tools) in filtered_ids
        )

    def _is_content_preserved(self, content: Any, filtered_content: list[Any]) -> bool:
        """Check if specific content is preserved in filtered content."""
        return id(content) in {id(item) for item in filtered_content}

    def _create_empty_result(self, contents: list[Any]) -> FilterResult:
        """Create FilterResult for empty content."""
        return FilterResult(
            original_content=contents,
            filtered_content=contents,
            removed_content=[],
            original_tokens=0,
            filtered_tokens=0,
            tokens_saved=0,
            reduction_pct=0.0,
            conversations_removed=0,
            tool_chains_preserved=0,
            context_injections_preserved=0,
            strategy_used=FilterStrategy.CONSERVATIVE,
            filtering_applied=False,
        )

    def _create_no_filter_result(
        self, contents: list[Any], original_tokens: int, strategy: FilterStrategy
    ) -> FilterResult:
        """Create FilterResult when no filtering is needed."""
        return FilterResult(
            original_content=contents,
            filtered_content=contents,
            removed_content=[],
            original_tokens=original_tokens,
            filtered_tokens=original_tokens,
            tokens_saved=0,
            reduction_pct=0.0,
            conversations_removed=0,
            tool_chains_preserved=0,
            context_injections_preserved=0,
            strategy_used=strategy,
            filtering_applied=False,
        )
