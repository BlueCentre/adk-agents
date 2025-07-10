"""Cross-turn correlation for linking related code and tool results across conversation turns."""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CorrelationScore:
    """Container for correlation scoring between items."""

    file_similarity: float = 0.0  # Same file or related files
    content_similarity: float = 0.0  # Similar content or keywords
    temporal_proximity: float = 0.0  # Proximity in turns
    tool_sequence: float = 0.0  # Related tool operations
    error_continuation: float = 0.0  # Error resolution chains
    final_score: float = 0.0  # Weighted combination


class CrossTurnCorrelator:
    """Implements cross-turn correlation for context components."""

    def __init__(
        self,
        snippet_correlation_threshold: float = 0.1,
        tool_correlation_threshold: float = 0.1,
        cross_correlation_threshold: float = 0.2,
    ):
        self.snippet_correlation_threshold = snippet_correlation_threshold
        self.tool_correlation_threshold = tool_correlation_threshold
        self.cross_correlation_threshold = cross_correlation_threshold

        # Weights for different correlation factors
        # Weights for different correlation factors
        self.weights = {
            "file_similarity": 0.3,  # File-based relationships
            "content_similarity": 0.25,  # Content-based relationships
            "temporal_proximity": 0.2,  # Time-based relationships
            "tool_sequence": 0.15,  # Tool operation sequences
            "error_continuation": 0.1,  # Error resolution chains
        }

        # File extension groups for similarity detection
        self.file_groups = {
            "python": {".py", ".pyx", ".pyi"},
            "javascript": {".js", ".jsx", ".ts", ".tsx"},
            "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"},
            "documentation": {".md", ".rst", ".txt"},
            "web": {".html", ".css", ".scss", ".sass"},
            "build": {"Makefile", "Dockerfile", ".sh", ".bat"},
        }

        # Tool operation sequences that are commonly related
        self.tool_sequences = [
            ["read_file", "edit_file"],
            ["execute_vetted_shell_command", "read_file"],
            ["codebase_search", "read_file"],
            ["read_file", "execute_vetted_shell_command"],
            ["edit_file", "execute_vetted_shell_command"],
        ]

    def correlate_context_items(
        self,
        code_snippets: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        conversation_turns: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Add correlation scores to context items and reorganize based on relationships."""

        logger.info(
            "CROSS-TURN CORRELATION: Analyzing relationships between context items..."
        )

        # Build correlation graphs
        snippet_correlations = self._build_snippet_correlations(
            code_snippets, conversation_turns
        )
        tool_correlations = self._build_tool_correlations(
            tool_results, conversation_turns
        )
        cross_correlations = self._build_cross_correlations(
            code_snippets, tool_results, conversation_turns
        )

        # Add correlation scores to items
        enhanced_snippets = self._enhance_with_correlations(
            code_snippets, snippet_correlations, "snippet"
        )
        enhanced_tools = self._enhance_with_correlations(
            tool_results, tool_correlations, "tool"
        )

        # Add cross-correlations between snippets and tools
        enhanced_snippets, enhanced_tools = self._add_cross_correlations(
            enhanced_snippets, enhanced_tools, cross_correlations
        )

        # Log correlation analysis
        self._log_correlation_analysis(enhanced_snippets, enhanced_tools)

        return enhanced_snippets, enhanced_tools

    def _build_snippet_correlations(
        self, snippets: List[Dict[str, Any]], conversation_turns: List[Dict[str, Any]]
    ) -> Dict[int, Dict[int, CorrelationScore]]:
        """Build correlation scores between code snippets."""

        correlations = {}

        for i, snippet1 in enumerate(snippets):
            correlations[i] = {}
            for j, snippet2 in enumerate(snippets):
                if i == j:
                    continue

                score = CorrelationScore()

                # File similarity
                score.file_similarity = self._calculate_file_similarity(
                    snippet1.get("file_path", ""), snippet2.get("file_path", "")
                )

                # Content similarity
                score.content_similarity = self._calculate_content_similarity(
                    snippet1.get("code", ""), snippet2.get("code", "")
                )

                # Temporal proximity
                score.temporal_proximity = self._calculate_temporal_proximity(
                    snippet1.get("turn", snippet1.get("last_accessed", 0)),
                    snippet2.get("turn", snippet2.get("last_accessed", 0)),
                )

                # Calculate final weighted score
                score.final_score = (
                    score.file_similarity * self.weights["file_similarity"]
                    + score.content_similarity * self.weights["content_similarity"]
                    + score.temporal_proximity * self.weights["temporal_proximity"]
                )

                if (
                    score.final_score > self.snippet_correlation_threshold
                ):  # Only store meaningful correlations
                    correlations[i][j] = score

        return correlations

    def _build_tool_correlations(
        self,
        tool_results: List[Dict[str, Any]],
        conversation_turns: List[Dict[str, Any]],
    ) -> Dict[int, Dict[int, CorrelationScore]]:
        """Build correlation scores between tool results."""

        correlations = {}

        for i, tool1 in enumerate(tool_results):
            correlations[i] = {}
            for j, tool2 in enumerate(tool_results):
                if i == j:
                    continue

                score = CorrelationScore()

                # Tool sequence similarity
                score.tool_sequence = self._calculate_tool_sequence_similarity(
                    tool1.get("tool", ""),
                    tool2.get("tool", ""),
                    tool1.get("turn", 0),
                    tool2.get("turn", 0),
                )

                # Content similarity (summaries)
                score.content_similarity = self._calculate_content_similarity(
                    tool1.get("summary", ""), tool2.get("summary", "")
                )

                # Temporal proximity
                score.temporal_proximity = self._calculate_temporal_proximity(
                    tool1.get("turn", 0), tool2.get("turn", 0)
                )

                # Error continuation
                score.error_continuation = self._calculate_error_continuation(
                    tool1, tool2
                )

                # Calculate final weighted score
                score.final_score = (
                    score.tool_sequence * self.weights["tool_sequence"]
                    + score.content_similarity * self.weights["content_similarity"]
                    + score.temporal_proximity * self.weights["temporal_proximity"]
                    + score.error_continuation * self.weights["error_continuation"]
                )

                if (
                    score.final_score > self.tool_correlation_threshold
                ):  # Only store meaningful correlations
                    correlations[i][j] = score

        return correlations

    def _build_cross_correlations(
        self,
        code_snippets: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        conversation_turns: List[Dict[str, Any]],
    ) -> Dict[str, List[Tuple[int, int, CorrelationScore]]]:
        """Build correlations between code snippets and tool results."""

        cross_correlations = {"snippet_to_tool": [], "tool_to_snippet": []}

        for i, snippet in enumerate(code_snippets):
            for j, tool in enumerate(tool_results):
                score = CorrelationScore()

                # File-based correlation (if tool operated on same file)
                snippet_file = snippet.get("file_path", "")
                tool_summary = tool.get("summary", "")

                if snippet_file and snippet_file in tool_summary:
                    score.file_similarity = 1.0
                else:
                    # Check if tool summary mentions similar files
                    score.file_similarity = self._calculate_file_mention_similarity(
                        snippet_file, tool_summary
                    )

                # Content similarity
                score.content_similarity = self._calculate_content_similarity(
                    snippet.get("code", ""), tool_summary
                )

                # Temporal proximity
                score.temporal_proximity = self._calculate_temporal_proximity(
                    snippet.get("last_accessed", 0), tool.get("turn", 0)
                )

                # Calculate final score
                score.final_score = (
                    score.file_similarity * 0.4  # Higher weight for file correlation
                    + score.content_similarity * 0.3
                    + score.temporal_proximity * 0.3
                )

                if (
                    score.final_score > self.cross_correlation_threshold
                ):  # Higher threshold for cross-correlations
                    cross_correlations["snippet_to_tool"].append((i, j, score))
                    cross_correlations["tool_to_snippet"].append((j, i, score))

        return cross_correlations

    def _calculate_file_similarity(self, file1: str, file2: str) -> float:
        """Calculate similarity between two file paths."""

        if not file1 or not file2:
            return 0.0

        # Exact match
        if file1 == file2:
            return 1.0

        # Same directory
        dir1 = "/".join(file1.split("/")[:-1])
        dir2 = "/".join(file2.split("/")[:-1])
        if dir1 and dir1 == dir2:
            return 0.7

        # Same file group (extension)
        ext1 = "." + file1.split(".")[-1] if "." in file1 else ""
        ext2 = "." + file2.split(".")[-1] if "." in file2 else ""

        for group_name, extensions in self.file_groups.items():
            if ext1 in extensions and ext2 in extensions:
                return 0.5

        # Same filename, different path
        name1 = file1.split("/")[-1]
        name2 = file2.split("/")[-1]
        if name1 == name2:
            return 0.6

        return 0.0

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate content similarity based on common keywords and patterns."""

        if not content1 or not content2:
            return 0.0

        # Normalize content
        content1_lower = content1.lower()
        content2_lower = content2.lower()

        # Extract keywords (alphanumeric words longer than 2 characters)
        words1 = set(re.findall(r"\b\w{3,}\b", content1_lower))
        words2 = set(re.findall(r"\b\w{3,}\b", content2_lower))

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        jaccard_similarity = intersection / union if union > 0 else 0.0

        # Bonus for code patterns (functions, classes, imports)
        code_patterns = [
            r"def\s+(\w+)",
            r"class\s+(\w+)",
            r"import\s+(\w+)",
            r"from\s+(\w+)",
            r"function\s+(\w+)",
            r"const\s+(\w+)",
        ]

        pattern_bonus = 0.0
        for pattern in code_patterns:
            matches1 = set(re.findall(pattern, content1_lower))
            matches2 = set(re.findall(pattern, content2_lower))
            if matches1.intersection(matches2):
                pattern_bonus += 0.1

        return min(jaccard_similarity + pattern_bonus, 1.0)

    def _calculate_temporal_proximity(self, time1: int, time2: int) -> float:
        """Calculate temporal proximity score."""

        if time1 <= 0 or time2 <= 0:
            return 0.0

        distance = abs(time1 - time2)

        if distance == 0:
            return 1.0
        elif distance <= 2:
            return 0.8
        elif distance <= 5:
            return 0.6
        elif distance <= 10:
            return 0.3
        else:
            return 0.1

    def _calculate_tool_sequence_similarity(
        self, tool1: str, tool2: str, turn1: int, turn2: int
    ) -> float:
        """Calculate similarity based on tool operation sequences."""

        if not tool1 or not tool2:
            return 0.0

        # Check if tools are in a known sequence
        for sequence in self.tool_sequences:
            if len(sequence) >= 2:
                for i in range(len(sequence) - 1):
                    if (
                        sequence[i] in tool1
                        and sequence[i + 1] in tool2
                        and turn2 > turn1
                    ) or (
                        sequence[i] in tool2
                        and sequence[i + 1] in tool1
                        and turn1 > turn2
                    ):
                        return 0.8

        # Same tool type
        if tool1 == tool2:
            return 0.6

        # Related tool families
        file_ops = {"read_file", "edit_file", "read_file_content", "edit_file_content"}
        search_ops = {"codebase_search", "retrieve_code_context_tool"}

        if (tool1 in file_ops and tool2 in file_ops) or (
            tool1 in search_ops and tool2 in search_ops
        ):
            return 0.4

        return 0.0

    def _calculate_error_continuation(
        self, tool1: Dict[str, Any], tool2: Dict[str, Any]
    ) -> float:
        """Calculate error continuation score."""

        is_error1 = tool1.get("is_error", False)
        is_error2 = tool2.get("is_error", False)
        turn1 = tool1.get("turn", 0)
        turn2 = tool2.get("turn", 0)

        # Error followed by potential resolution
        if is_error1 and not is_error2 and turn2 > turn1 and (turn2 - turn1) <= 3:
            return 0.8

        # Sequential errors (same issue)
        if is_error1 and is_error2 and abs(turn1 - turn2) <= 2:
            return 0.6

        return 0.0

    def _calculate_file_mention_similarity(self, file_path: str, content: str) -> float:
        """Calculate similarity based on file mentions in content."""

        if not file_path or not content:
            return 0.0

        content_lower = content.lower()
        file_path_lower = file_path.lower()

        # Check if filename is mentioned
        filename = file_path.split("/")[-1]
        if filename.lower() in content_lower:
            return 0.6

        # Check if directory is mentioned
        directory = "/".join(file_path.split("/")[:-1])
        if directory and directory.lower() in content_lower:
            return 0.3

        # Check for similar file extensions
        ext = "." + file_path.split(".")[-1] if "." in file_path else ""
        if ext and ext in content_lower:
            return 0.2

        return 0.0

    def _enhance_with_correlations(
        self,
        items: List[Dict[str, Any]],
        correlations: Dict[int, Dict[int, CorrelationScore]],
        item_type: str,
    ) -> List[Dict[str, Any]]:
        """Add correlation information to items."""

        enhanced_items = []

        for i, item in enumerate(items):
            enhanced_item = item.copy()
            item_correlations = correlations.get(i, {})

            # Add correlation metadata
            enhanced_item["_correlations"] = {
                "count": len(item_correlations),
                "max_score": max(
                    (score.final_score for score in item_correlations.values()),
                    default=0.0,
                ),
                "related_indices": list(item_correlations.keys()),
                "scores": {
                    j: score.final_score for j, score in item_correlations.items()
                },
            }

            # Add the expected _correlation_score field for tests
            # Use the highest scoring correlation or create a default one
            if item_correlations:
                best_correlation = max(
                    item_correlations.values(), key=lambda x: x.final_score
                )
                enhanced_item["_correlation_score"] = best_correlation
            else:
                # Create a default CorrelationScore for items with no correlations
                enhanced_item["_correlation_score"] = CorrelationScore()

            enhanced_items.append(enhanced_item)

        return enhanced_items

    def _add_cross_correlations(
        self,
        snippets: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        cross_correlations: Dict[str, List[Tuple[int, int, CorrelationScore]]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Add cross-correlations between snippets and tools."""

        # Add tool correlations to snippets
        for snippet_idx, tool_idx, score in cross_correlations["snippet_to_tool"]:
            if snippet_idx < len(snippets):
                if "_cross_correlations" not in snippets[snippet_idx]:
                    snippets[snippet_idx]["_cross_correlations"] = {"tools": []}
                snippets[snippet_idx]["_cross_correlations"]["tools"].append(
                    {
                        "tool_index": tool_idx,
                        "score": score.final_score,
                        "file_similarity": score.file_similarity,
                        "content_similarity": score.content_similarity,
                    }
                )

        # Add snippet correlations to tools
        for tool_idx, snippet_idx, score in cross_correlations["tool_to_snippet"]:
            if tool_idx < len(tools):
                if "_cross_correlations" not in tools[tool_idx]:
                    tools[tool_idx]["_cross_correlations"] = {"snippets": []}
                tools[tool_idx]["_cross_correlations"]["snippets"].append(
                    {
                        "snippet_index": snippet_idx,
                        "score": score.final_score,
                        "file_similarity": score.file_similarity,
                        "content_similarity": score.content_similarity,
                    }
                )

        return snippets, tools

    def _log_correlation_analysis(
        self, snippets: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> None:
        """Log correlation analysis results."""

        snippet_correlations = sum(
            len(s.get("_correlations", {}).get("related_indices", [])) for s in snippets
        )
        tool_correlations = sum(
            len(t.get("_correlations", {}).get("related_indices", [])) for t in tools
        )

        cross_snippet_tools = sum(
            len(s.get("_cross_correlations", {}).get("tools", [])) for s in snippets
        )
        cross_tool_snippets = sum(
            len(t.get("_cross_correlations", {}).get("snippets", [])) for t in tools
        )

        logger.info(f"  📊 CORRELATION ANALYSIS COMPLETE:")
        logger.info(f"    Snippet-to-Snippet correlations: {snippet_correlations}")
        logger.info(f"    Tool-to-Tool correlations: {tool_correlations}")
        logger.info(f"    Cross-correlations (Snippet→Tool): {cross_snippet_tools}")
        logger.info(f"    Cross-correlations (Tool→Snippet): {cross_tool_snippets}")

        # Log top correlations
        logger.info("  🔗 TOP CORRELATIONS:")
        for i, snippet in enumerate(snippets[:3]):  # Top 3 snippets
            correlations = snippet.get("_correlations", {})
            if correlations.get("count", 0) > 0:
                max_score = correlations.get("max_score", 0.0)
                related_count = correlations.get("count", 0)
                file_path = snippet.get("file_path", "unknown")
                logger.info(
                    f"    Snippet {i + 1} ({file_path}): {related_count} correlations (max: {max_score:.3f})"
                )

        for i, tool in enumerate(tools[:3]):  # Top 3 tools
            correlations = tool.get("_correlations", {})
            if correlations.get("count", 0) > 0:
                max_score = correlations.get("max_score", 0.0)
                related_count = correlations.get("count", 0)
                tool_name = tool.get("tool", "unknown")
                logger.info(
                    f"    Tool {i + 1} ({tool_name}): {related_count} correlations (max: {max_score:.3f})"
                )
