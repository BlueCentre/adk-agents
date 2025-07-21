"""Smart prioritization for context components using relevance-based ranking."""

from dataclasses import dataclass
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RelevanceScore:
    """Container for relevance scoring components."""

    content_relevance: float = 0.0  # Based on content similarity to current task
    recency_score: float = 0.0  # Based on how recent the item is
    frequency_score: float = 0.0  # Based on how often it's accessed
    error_priority: float = 0.0  # Higher priority for error-related content
    context_coherence: float = 0.0  # How well it fits with other selected context
    final_score: float = 0.0  # Weighted combination of all scores


class SmartPrioritizer:
    """Implements smart prioritization for context components."""

    def __init__(self):
        # Weights for different relevance factors
        self.weights = {
            "content_relevance": 0.35,  # Most important - what's relevant to current task
            "recency_score": 0.25,  # Important - recent activity is often relevant
            "frequency_score": 0.15,  # Moderate - frequently accessed items
            "error_priority": 0.15,  # Moderate - errors need attention
            "context_coherence": 0.10,  # Lower - nice to have but not critical
        }

        # Keywords that indicate different types of relevance
        self.error_keywords = [
            "error",
            "exception",
            "fail",
            "crash",
            "bug",
            "issue",
            "problem",
            "stderr",
            "traceback",
            "stacktrace",
            "warning",
            "critical",
        ]

        self.high_value_keywords = [
            "config",
            "setup",
            "install",
            "deploy",
            "build",
            "test",
            "main",
            "init",
            "start",
            "run",
            "execute",
            "import",
            "class",
            "function",
            "api",
            "endpoint",
            "service",
            "database",
            "auth",
            "security",
        ]

    def prioritize_code_snippets(
        self,
        snippets: list[dict[str, Any]],
        current_context: str = "",
        current_turn: int = 0,
    ) -> list[dict[str, Any]]:
        """Prioritize code snippets based on relevance scoring."""

        if not snippets:
            return snippets

        logger.info(f"SMART PRIORITIZATION: Ranking {len(snippets)} code snippets...")

        # Calculate relevance scores for each snippet
        scored_snippets = []
        for snippet in snippets:
            score = self._calculate_snippet_relevance(snippet, current_context, current_turn)
            snippet_with_score = snippet.copy()
            snippet_with_score["_relevance_score"] = score
            scored_snippets.append((score.final_score, snippet_with_score))

            logger.debug(
                f"  Snippet {snippet.get('file', 'unknown')}:{snippet.get('start_line', 0)}"
            )
            logger.debug(
                f"    Content: {score.content_relevance:.3f}, Recency: {score.recency_score:.3f}"
            )
            logger.debug(
                f"    Frequency: {score.frequency_score:.3f}, Error: {score.error_priority:.3f}"
            )
            logger.debug(
                f"    Coherence: {score.context_coherence:.3f}, Final: {score.final_score:.3f}"
            )

        # Sort by relevance score (highest first)
        scored_snippets.sort(key=lambda x: x[0], reverse=True)

        # Log the ranking results
        logger.info("  📊 TOP 5 RANKED SNIPPETS:")
        for i, (score, snippet) in enumerate(scored_snippets[:5]):
            file_path = snippet.get("file", snippet.get("file_path", "unknown"))
            start_line = snippet.get("start_line", 0)
            logger.info(f"    {i + 1}. {file_path}:{start_line} (score: {score:.3f})")

        return [snippet for _, snippet in scored_snippets]

    def prioritize_tool_results(
        self,
        tool_results: list[dict[str, Any]],
        current_context: str = "",
        current_turn: int = 0,
    ) -> list[dict[str, Any]]:
        """Prioritize tool results based on relevance scoring."""

        if not tool_results:
            return tool_results

        logger.info(f"SMART PRIORITIZATION: Ranking {len(tool_results)} tool results...")

        # Calculate relevance scores for each tool result
        scored_results = []
        for result in tool_results:
            score = self._calculate_tool_result_relevance(result, current_context, current_turn)
            result_with_score = result.copy()
            result_with_score["_relevance_score"] = score
            scored_results.append((score.final_score, result_with_score))

            logger.debug(f"  Tool {result.get('tool', 'unknown')} (turn {result.get('turn', 0)})")
            logger.debug(
                f"    Content: {score.content_relevance:.3f}, Recency: {score.recency_score:.3f}"
            )
            logger.debug(f"    Error: {score.error_priority:.3f}, Final: {score.final_score:.3f}")

        # Sort by relevance score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Log the ranking results
        logger.info("  📊 TOP 5 RANKED TOOL RESULTS:")
        for i, (score, result) in enumerate(scored_results[:5]):
            tool_name = result.get("tool", "unknown")
            turn = result.get("turn", 0)
            is_error = result.get("is_error", False)
            error_indicator = " ❌" if is_error else ""
            logger.info(
                f"    {i + 1}. {tool_name} (turn {turn}){error_indicator} (score: {score:.3f})"
            )

        return [result for _, result in scored_results]

    def _calculate_snippet_relevance(
        self, snippet: dict[str, Any], current_context: str, current_turn: int
    ) -> RelevanceScore:
        """Calculate relevance score for a code snippet."""

        score = RelevanceScore()

        # Extract snippet content and metadata
        code_content = snippet.get("code", "")
        file_path = snippet.get("file", snippet.get("file_path", ""))
        last_accessed = snippet.get("last_accessed", 0)
        existing_relevance = snippet.get("relevance_score", 1.0)

        # 1. Content Relevance - based on keyword matching and content analysis
        score.content_relevance = self._calculate_content_relevance(
            code_content + " " + file_path, current_context
        )

        # 2. Recency Score - based on when it was last accessed
        score.recency_score = self._calculate_recency_score(last_accessed, current_turn)

        # 3. Frequency Score - based on existing relevance score (accumulated access)
        score.frequency_score = min(existing_relevance / 5.0, 1.0)  # Normalize to 0-1

        # 4. Error Priority - higher for error-related content
        score.error_priority = self._calculate_error_priority(code_content)

        # 5. Context Coherence - based on file type and location
        score.context_coherence = self._calculate_context_coherence(file_path, current_context)

        # Calculate final weighted score
        score.final_score = (
            score.content_relevance * self.weights["content_relevance"]
            + score.recency_score * self.weights["recency_score"]
            + score.frequency_score * self.weights["frequency_score"]
            + score.error_priority * self.weights["error_priority"]
            + score.context_coherence * self.weights["context_coherence"]
        )

        return score

    def _calculate_tool_result_relevance(
        self, tool_result: dict[str, Any], current_context: str, current_turn: int
    ) -> RelevanceScore:
        """Calculate relevance score for a tool result."""

        score = RelevanceScore()

        # Extract tool result metadata
        summary = tool_result.get("summary", "")
        tool_name = tool_result.get("tool", "")
        turn_number = tool_result.get("turn", 0)
        is_error = tool_result.get("is_error", False)
        severity = tool_result.get("severity", "medium")

        # 1. Content Relevance - based on summary content
        score.content_relevance = self._calculate_content_relevance(
            summary + " " + tool_name, current_context
        )

        # 2. Recency Score - based on turn number
        turn_distance = current_turn - turn_number
        score.recency_score = max(0.0, 1.0 - (turn_distance / 20.0))  # Decay over 20 turns

        # 3. Error Priority - much higher for error results, also consider severity
        if is_error:
            score.error_priority = 1.0
        else:
            # Use severity for non-error results
            severity_scores = {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.2}
            severity_score = severity_scores.get(severity.lower(), 0.3)

            # Combine with error keyword detection
            error_keyword_score = self._calculate_error_priority(summary)
            score.error_priority = max(severity_score, error_keyword_score)

        # 4. Tool-specific bonuses
        if tool_name in [
            "read_file",
            "edit_file",
            "read_file_content",
            "edit_file_content",
        ]:
            score.context_coherence = 0.8  # File operations are often relevant
        elif tool_name in ["execute_vetted_shell_command"]:
            score.context_coherence = 0.6  # Shell commands moderately relevant
        else:
            score.context_coherence = 0.4  # Other tools less relevant

        # Calculate final weighted score (no frequency for tool results)
        score.final_score = (
            score.content_relevance * 0.4  # Higher weight for content
            + score.recency_score * 0.3  # Higher weight for recency
            + score.error_priority * 0.2  # Error priority
            + score.context_coherence * 0.1  # Tool type relevance
        )

        return score

    def _calculate_content_relevance(self, content: str, context: str) -> float:
        """Calculate content relevance based on keyword matching and similarity."""

        if not content or not context:
            return 0.1  # Minimal base score

        content_lower = content.lower()
        context_lower = context.lower()

        # 1. Direct keyword matching
        context_words = set(re.findall(r"\b\w+\b", context_lower))
        content_words = set(re.findall(r"\b\w+\b", content_lower))

        if not context_words:
            return 0.1

        # Calculate word overlap
        common_words = context_words.intersection(content_words)
        word_overlap_score = len(common_words) / len(context_words)

        # 2. High-value keyword bonus - give extra weight for important domain terms
        high_value_matches = 0
        for keyword in self.high_value_keywords:
            if keyword in content_lower:
                # Check if this keyword is also mentioned in context or is contextually important
                if keyword in context_lower or any(
                    k in context_lower for k in ["auth", "security", "error", "fix", "debug"]
                ):
                    high_value_matches += 1

        high_value_score = min(high_value_matches * 0.25, 1.0)

        # 3. Semantic keyword matching - boost score for domain-relevant terms
        domain_keywords = {
            "auth": [
                "authentication",
                "authorize",
                "login",
                "credential",
                "password",
                "token",
            ],
            "security": [
                "vulnerability",
                "secure",
                "encrypt",
                "decrypt",
                "hash",
                "key",
            ],
            "error": ["exception", "fail", "bug", "issue", "problem", "crash"],
            "test": ["testing", "spec", "validate", "verify", "check"],
        }

        semantic_score = 0.0
        for domain, keywords in domain_keywords.items():
            if domain in context_lower:
                # If domain term is in context, boost score for related keywords in content
                domain_matches = sum(1 for keyword in keywords if keyword in content_lower)
                semantic_score += min(domain_matches * 0.2, 0.6)

        # 4. File path relevance (if applicable)
        file_relevance_score = 0.0
        if any(ext in content_lower for ext in [".py", ".js", ".ts", ".java", ".go", ".rs"]):
            file_relevance_score = 0.2  # Source code files are generally relevant
        elif any(ext in content_lower for ext in [".json", ".yaml", ".yml", ".toml"]):
            file_relevance_score = 0.3  # Config files highly relevant

        # Combine scores with weights - give more weight to direct matches
        final_score = (
            word_overlap_score * 0.4  # Direct word matches most important
            + high_value_score * 0.3  # High-value keywords important
            + semantic_score * 0.2  # Semantic relationships helpful
            + file_relevance_score * 0.1  # File type context
        )

        return min(final_score, 1.0)

    def _calculate_recency_score(self, last_accessed: int, current_turn: int) -> float:
        """Calculate recency score based on turn distance."""

        if last_accessed <= 0:
            return 0.1  # Very old or never accessed

        turn_distance = current_turn - last_accessed

        if turn_distance <= 0:
            return 1.0  # Current turn
        if turn_distance <= 3:
            return 0.8  # Very recent
        if turn_distance <= 10:
            return 0.6  # Recent
        if turn_distance <= 20:
            return 0.3  # Somewhat old
        return 0.1  # Old

    def _calculate_error_priority(self, content: str) -> float:
        """Calculate error priority based on error-related keywords."""

        if not content:
            return 0.0

        content_lower = content.lower()
        error_matches = sum(1 for keyword in self.error_keywords if keyword in content_lower)

        # Higher score for more error keywords
        return min(error_matches * 0.3, 1.0)

    def _calculate_context_coherence(self, file_path: str, current_context: str) -> float:
        """Calculate how well the item fits with the current context."""

        if not file_path:
            return 0.5  # Neutral score for unknown files

        file_path_lower = file_path.lower()
        context_lower = current_context.lower() if current_context else ""

        # File type bonuses
        score = 0.0

        # Source code files
        if any(ext in file_path_lower for ext in [".py", ".js", ".ts", ".java"]):
            score += 0.6

        # Configuration files
        elif any(ext in file_path_lower for ext in [".json", ".yaml", ".yml", ".toml"]):
            score += 0.8

        # Documentation files
        elif any(ext in file_path_lower for ext in [".md", ".rst", ".txt"]):
            score += 0.4

        # Test files (if context suggests testing)
        elif "test" in file_path_lower:
            test_bonus = 0.7 if "test" in context_lower else 0.3
            score += test_bonus

        # Directory structure relevance
        if any(dir_name in file_path_lower for dir_name in ["src", "lib", "core", "main"]):
            score += 0.2
        elif any(dir_name in file_path_lower for dir_name in ["config", "settings"]):
            score += 0.3

        return min(score, 1.0)
