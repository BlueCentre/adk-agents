"""Content prioritization system for intelligent conversation filtering."""

import logging
import math
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ContentPrioritizer:
    """Multi-factor content scoring for intelligent conversation prioritization."""

    def __init__(self, config: Optional[dict[str, float]] = None):
        """
        Initialize the content prioritizer with configurable weights.

        Args:
            config: Optional configuration with scoring weights
        """
        # Default scoring weights - can be tuned based on usage patterns
        self.config = config or {
            "relevance_weight": 0.3,
            "recency_weight": 0.25,
            "tool_activity_weight": 0.25,
            "error_priority_weight": 0.2,
            "recency_decay_factor": 0.1,  # How quickly recency scores decay
            "max_recency_hours": 24.0,  # Maximum hours for recency calculation
        }

        logger.debug(f"ContentPrioritizer initialized with config: {self.config}")

    def calculate_relevance_score(self, content: str, user_query: str) -> float:
        """
        Calculate relevance score based on content similarity to user query.

        This implementation uses keyword-based similarity. In production,
        this could be enhanced with semantic embeddings.

        Args:
            content: The content to score
            user_query: The current user query for comparison

        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not content or not user_query:
            return 0.0

        # Convert to lowercase for comparison
        content_lower = content.lower()
        query_lower = user_query.lower()

        # Simple keyword-based relevance scoring
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())

        if not query_words:
            return 0.0

        # Calculate intersection ratio
        common_words = query_words.intersection(content_words)
        relevance_ratio = len(common_words) / len(query_words)

        # Boost score for exact phrase matches
        phrase_bonus = 0.0
        if len(user_query) > 10 and query_lower in content_lower:
            phrase_bonus = 0.3

        # Boost score for file/function references
        reference_bonus = 0.0
        for word in query_words:
            if len(word) > 3 and (
                word.endswith((".py", ".js", ".ts", ".md", ".json"))
                or "." in word
                or "_" in word
                or word.startswith(("def ", "class ", "function"))
            ):
                if word in content_lower:
                    reference_bonus += 0.1

        final_score = min(1.0, relevance_ratio + phrase_bonus + reference_bonus)
        logger.debug(f"Relevance score for content length {len(content)}: {final_score}")
        return final_score

    def calculate_recency_score(
        self, message_timestamp: float, current_time: Optional[float] = None
    ) -> float:
        """
        Calculate recency score with exponential decay.

        Args:
            message_timestamp: Unix timestamp of the message
            current_time: Current time (defaults to time.time())

        Returns:
            Recency score between 0.0 and 1.0
        """
        if current_time is None:
            current_time = time.time()

        # Calculate age in hours
        age_seconds = max(0, current_time - message_timestamp)
        age_hours = age_seconds / 3600.0

        # Cap at maximum recency hours
        age_hours = min(age_hours, self.config["max_recency_hours"])

        # Exponential decay: score = e^(-decay_factor * age_hours)
        decay_factor = self.config["recency_decay_factor"]
        recency_score = math.exp(-decay_factor * age_hours)

        logger.debug(f"Recency score for {age_hours:.1f}h old message: {recency_score:.3f}")
        return recency_score

    def calculate_tool_activity_score(self, content: dict[str, Any]) -> float:
        """
        Calculate tool activity score based on tool usage density.

        Args:
            content: Content metadata including tool activity information

        Returns:
            Tool activity score between 0.0 and 1.0
        """
        # Extract tool activity indicators
        has_function_call = content.get("has_function_call", False)
        has_function_response = content.get("has_function_response", False)
        tool_count = content.get("tool_count", 0)
        error_count = content.get("error_count", 0)

        # Base score for any tool activity
        base_score = 0.0
        if has_function_call or has_function_response:
            base_score = 0.4

        # Bonus for multiple tools
        tool_bonus = min(0.3, tool_count * 0.1)

        # Penalty for errors (but still prioritize over non-tool content)
        error_penalty = min(0.2, error_count * 0.05)

        # Activity density bonus (prefer tool-heavy conversations)
        activity_density = tool_count / max(1, content.get("message_count", 1))
        density_bonus = min(0.3, activity_density * 0.5)

        final_score = min(1.0, base_score + tool_bonus + density_bonus - error_penalty)
        logger.debug(
            f"Tool activity score: {final_score} (tools: {tool_count}, errors: {error_count})"
        )
        return final_score

    def calculate_error_priority_score(self, content: dict[str, Any]) -> float:
        """
        Calculate error priority score - critical errors get highest priority.

        Args:
            content: Content metadata including error information

        Returns:
            Error priority score between 0.0 and 1.0
        """
        error_indicators = content.get("error_indicators", [])
        if not error_indicators:
            return 0.0

        # Different error types have different priorities
        error_priority_map = {
            "critical": 1.0,
            "exception": 0.9,
            "error": 0.8,
            "failure": 0.7,
            "warning": 0.3,
            "timeout": 0.6,
            "permission": 0.8,
            "not_found": 0.5,
        }

        max_error_score = 0.0
        for error_type in error_indicators:
            error_score = error_priority_map.get(error_type.lower(), 0.4)
            max_error_score = max(max_error_score, error_score)

        # Recent errors get priority boost
        error_recency_boost = 0.0
        if content.get("has_recent_errors", False):
            error_recency_boost = 0.2

        final_score = min(1.0, max_error_score + error_recency_boost)
        logger.debug(f"Error priority score: {final_score} (errors: {error_indicators})")
        return final_score

    def calculate_composite_score(self, content: dict[str, Any], context: dict[str, Any]) -> float:
        """
        Calculate composite score combining all factors.

        Args:
            content: Content metadata with all scoring information
            context: Additional context including user query

        Returns:
            Composite score between 0.0 and 1.0
        """
        user_query = context.get("user_query", "")
        content_text = content.get("text", "")
        message_timestamp = content.get("timestamp", time.time())

        # Calculate individual scores
        relevance_score = self.calculate_relevance_score(content_text, user_query)
        recency_score = self.calculate_recency_score(message_timestamp)
        tool_activity_score = self.calculate_tool_activity_score(content)
        error_priority_score = self.calculate_error_priority_score(content)

        # Apply weights
        weighted_scores = [
            relevance_score * self.config["relevance_weight"],
            recency_score * self.config["recency_weight"],
            tool_activity_score * self.config["tool_activity_weight"],
            error_priority_score * self.config["error_priority_weight"],
        ]

        composite_score = sum(weighted_scores)

        # Apply bonuses for special content types
        if content.get("is_system_message", False):
            composite_score += 0.1  # Small system message boost

        if content.get("is_current_turn", False):
            composite_score += 0.2  # Current turn gets priority

        if content.get("is_incomplete_tool_chain", False):
            composite_score += 0.15  # Incomplete chains need preservation

        final_score = min(1.0, composite_score)

        logger.debug(
            f"Composite score: {final_score:.3f} "
            f"(rel: {relevance_score:.2f}, rec: {recency_score:.2f}, "
            f"tool: {tool_activity_score:.2f}, err: {error_priority_score:.2f})"
        )

        return final_score

    def prioritize_content_list(
        self, content_list: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Prioritize a list of content items using composite scoring.

        Args:
            content_list: List of content items to prioritize
            context: Context information including user query

        Returns:
            List of content items sorted by priority (highest first)
        """
        logger.info(f"Prioritizing {len(content_list)} content items")

        # Calculate scores for all items
        scored_content = []
        for item in content_list:
            score = self.calculate_composite_score(item, context)
            scored_item = item.copy()
            scored_item["priority_score"] = score
            scored_content.append(scored_item)

        # Sort by score (highest first)
        prioritized_content = sorted(
            scored_content, key=lambda x: x["priority_score"], reverse=True
        )

        logger.info(
            f"Content prioritization complete. Score range: "
            f"{prioritized_content[-1]['priority_score']:.3f} - "
            f"{prioritized_content[0]['priority_score']:.3f}"
        )

        return prioritized_content

    def update_config(self, config_updates: dict[str, float]) -> None:
        """
        Update prioritization configuration.

        Args:
            config_updates: Dictionary of configuration updates
        """
        self.config.update(config_updates)
        logger.info(f"Content prioritizer config updated: {config_updates}")

    def get_config(self) -> dict[str, float]:
        """
        Get current prioritization configuration.

        Returns:
            Current configuration dictionary
        """
        return self.config.copy()
