"""Smart context bridging system for dependency-preserving conversation optimization."""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Optional

from .context_correlator import (
    ContextCorrelator,
    CorrelationResult,
    DependencyType,
    ReferenceStrength,
)

logger = logging.getLogger(__name__)


class BridgingStrategy(Enum):
    """Strategies for context bridging."""

    CONSERVATIVE = "conservative"  # Preserve most context, minimal bridging
    MODERATE = "moderate"  # Balanced approach with smart bridging
    AGGRESSIVE = "aggressive"  # Maximum optimization with extensive bridging
    DEPENDENCY_ONLY = "dependency"  # Bridge only critical dependencies


class BridgeType(Enum):
    """Types of context bridges."""

    REFERENCE_BRIDGE = "reference"  # Preserves critical references
    TOOL_CHAIN_BRIDGE = "tool_chain"  # Maintains tool execution continuity
    ERROR_CONTEXT_BRIDGE = "error"  # Links errors to fixes
    CONVERSATION_BRIDGE = "conversation"  # Maintains dialogue flow
    SUMMARY_BRIDGE = "summary"  # Summarized context bridge


@dataclass
class ContextBridge:
    """Represents a context bridge between content items."""

    bridge_id: str
    bridge_type: BridgeType
    source_content_ids: list[str]  # Content being bridged from
    target_content_ids: list[str]  # Content being bridged to
    bridge_content: str  # Actual bridge text
    preserved_references: list[str]  # Critical references preserved
    confidence: float  # Confidence in bridge quality (0.0-1.0)
    token_cost: int  # Estimated tokens for this bridge
    priority: int  # Bridge priority (higher = more important)

    def __post_init__(self):
        """Validate bridge data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.token_cost < 0:
            raise ValueError(f"Token cost must be non-negative, got {self.token_cost}")


@dataclass
class BridgingResult:
    """Result of context bridging analysis."""

    bridges: list[ContextBridge]
    bridged_content_ids: set[str]  # Content that has been bridged
    preserved_content_ids: set[str]  # Content preserved due to bridges
    total_bridge_tokens: int  # Total tokens used for bridges
    bridging_metadata: dict[str, Any]
    strategy_used: BridgingStrategy
    gaps_filled: int  # Number of context gaps filled


@dataclass
class BridgeCandidate:
    """Candidate location for context bridging."""

    gap_start_id: str  # Content ID where gap starts
    gap_end_id: str  # Content ID where gap ends
    missing_content_ids: list[str]  # Content IDs that would be removed
    dependency_score: float  # Importance of bridging this gap
    bridge_complexity: int  # Estimated complexity of bridge needed
    affected_references: list[str]  # References that would be broken


class ContextBridgeBuilder:
    """Advanced context bridging system with dependency preservation."""

    def __init__(
        self,
        correlator: Optional[ContextCorrelator] = None,
        config: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the context bridge builder.

        Args:
            correlator: ContextCorrelator instance for dependency analysis
            config: Optional configuration for bridging behavior
        """
        self.correlator = correlator or ContextCorrelator()
        default_config = self._get_default_config()
        if config:
            default_config.update(config)
        self.config = default_config

        logger.debug(f"ContextBridgeBuilder initialized with config: {self.config}")

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration for context bridging."""
        return {
            # Bridging strategy settings
            "default_strategy": BridgingStrategy.MODERATE,
            "max_bridge_tokens": 200,  # Maximum tokens per bridge
            "min_dependency_score": 0.3,  # Minimum score for bridging
            "bridge_confidence_threshold": 0.5,  # Minimum bridge confidence
            # Gap detection settings
            "max_gap_size": 10,  # Maximum content items in a gap
            "min_gap_size": 2,  # Minimum gap size to consider bridging
            "gap_analysis_window": 20,  # Window for gap analysis
            # Reference preservation
            "preserve_tool_chains": True,  # Always preserve tool chains
            "preserve_error_contexts": True,  # Always preserve error-fix links
            "preserve_file_references": True,  # Preserve file reference chains
            "critical_reference_boost": 0.3,  # Boost for critical references
            # Bridge generation
            "max_bridges_per_conversation": 10,  # Limit bridge count
            "bridge_token_budget_pct": 0.15,  # Percentage of budget for bridges
            "summarization_enabled": True,  # Enable summary bridges
            "summary_compression_ratio": 0.3,  # Target compression for summaries
            # Performance settings
            "max_analysis_items": 500,  # Maximum items for analysis
            "bridge_generation_timeout": 30,  # Timeout for bridge generation
        }

    def build_context_bridges(
        self,
        content_items: list[dict[str, Any]],
        filtered_content_ids: set[str],
        strategy: Optional[BridgingStrategy] = None,
    ) -> BridgingResult:
        """
        Build context bridges for filtered content to preserve dependencies.

        Args:
            content_items: Original content items
            filtered_content_ids: IDs of content that will be preserved
            strategy: Bridging strategy to use

        Returns:
            BridgingResult with generated bridges and metadata
        """
        import time

        start_time = time.time()

        strategy = strategy or self.config["default_strategy"]

        logger.info(
            f"Building context bridges for {len(content_items)} items "
            f"with {len(filtered_content_ids)} preserved, strategy: {strategy.value}"
        )

        # Analyze dependencies using correlator
        correlation_result = self.correlator.correlate_context(content_items)

        # Identify content gaps that need bridging
        bridge_candidates = self._identify_bridge_candidates(
            content_items, filtered_content_ids, correlation_result
        )

        # Generate bridges based on strategy
        bridges = self._generate_bridges(
            bridge_candidates, content_items, correlation_result, strategy
        )

        # Calculate bridging metadata
        processing_time = time.time() - start_time
        bridged_content_ids = set()
        preserved_content_ids = set()

        for bridge in bridges:
            bridged_content_ids.update(bridge.source_content_ids)
            preserved_content_ids.update(bridge.target_content_ids)

        bridging_metadata = {
            "processing_time": processing_time,
            "candidates_analyzed": len(bridge_candidates),
            "bridges_generated": len(bridges),
            "bridge_types": {
                bridge_type.value: len([b for b in bridges if b.bridge_type == bridge_type])
                for bridge_type in BridgeType
            },
            "average_bridge_confidence": sum(b.confidence for b in bridges) / len(bridges)
            if bridges
            else 0.0,
            "dependency_preservation_score": self._calculate_preservation_score(
                correlation_result, bridges, filtered_content_ids
            ),
        }

        result = BridgingResult(
            bridges=bridges,
            bridged_content_ids=bridged_content_ids,
            preserved_content_ids=preserved_content_ids,
            total_bridge_tokens=sum(b.token_cost for b in bridges),
            bridging_metadata=bridging_metadata,
            strategy_used=strategy,
            gaps_filled=len([b for b in bridges if b.bridge_type != BridgeType.SUMMARY_BRIDGE]),
        )

        logger.info(
            f"Context bridging complete: {len(bridges)} bridges, "
            f"{result.total_bridge_tokens} tokens, {result.gaps_filled} gaps filled"
        )

        return result

    def _identify_bridge_candidates(
        self,
        content_items: list[dict[str, Any]],
        filtered_content_ids: set[str],
        correlation_result: CorrelationResult,
    ) -> list[BridgeCandidate]:
        """Identify locations where context bridges might be needed."""
        candidates = []

        # Create index of content items
        content_index = {item.get("id", str(i)): item for i, item in enumerate(content_items)}

        # Analyze gaps in filtered content sequence
        filtered_items = [item for item in content_items if item.get("id") in filtered_content_ids]

        for i in range(len(filtered_items) - 1):
            current_item = filtered_items[i]
            next_item = filtered_items[i + 1]

            current_id = current_item.get("id")
            next_id = next_item.get("id")

            # Find missing content between current and next
            missing_content_ids = self._find_missing_content_between(
                current_id, next_id, content_items, filtered_content_ids
            )

            if len(missing_content_ids) >= self.config["min_gap_size"]:
                # Calculate dependency score for this gap
                dependency_score = self._calculate_gap_dependency_score(
                    missing_content_ids, correlation_result
                )

                if dependency_score >= self.config["min_dependency_score"]:
                    # Identify affected references
                    affected_references = self._identify_affected_references(
                        missing_content_ids, correlation_result
                    )

                    candidate = BridgeCandidate(
                        gap_start_id=current_id,
                        gap_end_id=next_id,
                        missing_content_ids=missing_content_ids,
                        dependency_score=dependency_score,
                        bridge_complexity=self._estimate_bridge_complexity(
                            missing_content_ids, content_index
                        ),
                        affected_references=affected_references,
                    )

                    candidates.append(candidate)

        # Sort candidates by dependency score (highest first)
        candidates.sort(key=lambda x: x.dependency_score, reverse=True)

        logger.debug(f"Identified {len(candidates)} bridge candidates")
        return candidates

    def _find_missing_content_between(
        self,
        start_id: str,
        end_id: str,
        content_items: list[dict[str, Any]],
        filtered_content_ids: set[str],
    ) -> list[str]:
        """Find content IDs that are missing between start and end in filtered set."""
        missing_ids = []

        # Find positions of start and end items
        start_pos = None
        end_pos = None

        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))
            if item_id == start_id:
                start_pos = i
            elif item_id == end_id:
                end_pos = i

        if start_pos is not None and end_pos is not None and start_pos < end_pos:
            # Check items between start and end
            for i in range(start_pos + 1, end_pos):
                item_id = content_items[i].get("id", str(i))
                if item_id not in filtered_content_ids:
                    missing_ids.append(item_id)

        return missing_ids

    def _calculate_gap_dependency_score(
        self,
        missing_content_ids: list[str],
        correlation_result: CorrelationResult,
    ) -> float:
        """Calculate importance score for bridging a content gap."""
        total_score = 0.0
        reference_count = 0

        # Check references involving missing content
        for ref in correlation_result.references:
            if ref.source_id in missing_content_ids or ref.target_id in missing_content_ids:
                reference_count += 1

                # Weight by dependency type
                type_weights = {
                    DependencyType.TOOL_CHAIN: 1.0,
                    DependencyType.ERROR_CONTEXT: 0.9,
                    DependencyType.FILE_REFERENCE: 0.8,
                    DependencyType.FUNCTION_REFERENCE: 0.7,
                    DependencyType.VARIABLE_REFERENCE: 0.6,
                    DependencyType.CONVERSATION_FLOW: 0.4,
                    DependencyType.CONCEPT_CONTINUATION: 0.3,
                }

                type_weight = type_weights.get(ref.dependency_type, 0.5)

                # Weight by reference strength
                strength_weights = {
                    ReferenceStrength.CRITICAL: 1.0,
                    ReferenceStrength.STRONG: 0.8,
                    ReferenceStrength.MODERATE: 0.6,
                    ReferenceStrength.WEAK: 0.4,
                }

                strength_weight = strength_weights.get(ref.strength, 0.5)

                # Combine weights with reference confidence
                score = ref.confidence * type_weight * strength_weight
                total_score += score

        # Normalize by gap size to avoid bias toward large gaps
        gap_size = len(missing_content_ids)
        normalized_score = total_score / max(1, gap_size * 0.5) if gap_size > 0 else 0.0

        # Boost score for critical content types
        critical_boost = 0.0
        for _content_id in missing_content_ids:
            # This would require access to content metadata
            # For now, assume boost is calculated elsewhere
            pass

        final_score = min(1.0, normalized_score + critical_boost)

        logger.debug(
            f"Gap dependency score: {final_score:.3f} ({reference_count} refs, {gap_size} items)"
        )

        return final_score

    def _identify_affected_references(
        self, missing_content_ids: list[str], correlation_result: CorrelationResult
    ) -> list[str]:
        """Identify references that would be affected by missing content."""
        affected_refs = []

        for ref in correlation_result.references:
            if ref.source_id in missing_content_ids or ref.target_id in missing_content_ids:
                # Create reference description
                ref_desc = f"{ref.dependency_type.value}:{ref.reference_text}"
                affected_refs.append(ref_desc)

        return affected_refs

    def _estimate_bridge_complexity(
        self, missing_content_ids: list[str], content_index: dict[str, dict[str, Any]]
    ) -> int:
        """Estimate complexity of bridging this gap (1-10 scale)."""
        complexity = 1

        # Base complexity on gap size
        gap_size = len(missing_content_ids)
        complexity += min(gap_size // 2, 5)  # Up to +5 for size

        # Increase complexity for tool chains
        has_tool_content = any(
            content_index.get(content_id, {}).get("has_function_call", False)
            or content_index.get(content_id, {}).get("has_function_response", False)
            for content_id in missing_content_ids
        )
        if has_tool_content:
            complexity += 2

        # Increase complexity for errors
        has_error_content = any(
            content_index.get(content_id, {}).get("error_indicators")
            for content_id in missing_content_ids
        )
        if has_error_content:
            complexity += 1

        return min(complexity, 10)

    def _generate_bridges(
        self,
        candidates: list[BridgeCandidate],
        content_items: list[dict[str, Any]],
        correlation_result: CorrelationResult,
        strategy: BridgingStrategy,
    ) -> list[ContextBridge]:
        """Generate actual context bridges based on candidates and strategy."""
        bridges = []
        bridge_id_counter = 0

        # Strategy-specific limits
        strategy_limits = {
            BridgingStrategy.CONSERVATIVE: {"max_bridges": 3, "max_tokens_per_bridge": 100},
            BridgingStrategy.MODERATE: {"max_bridges": 6, "max_tokens_per_bridge": 150},
            BridgingStrategy.AGGRESSIVE: {"max_bridges": 10, "max_tokens_per_bridge": 200},
            BridgingStrategy.DEPENDENCY_ONLY: {"max_bridges": 5, "max_tokens_per_bridge": 80},
        }

        limits = strategy_limits[strategy]
        max_bridges = min(limits["max_bridges"], self.config["max_bridges_per_conversation"])

        # Create content index
        content_index = {item.get("id", str(i)): item for i, item in enumerate(content_items)}

        for candidate in candidates[:max_bridges]:
            bridge_id_counter += 1

            # Determine bridge type based on affected references
            bridge_type = self._determine_bridge_type(candidate, correlation_result)

            # Generate bridge content based on type and strategy
            bridge_content, confidence = self._generate_bridge_content(
                candidate, content_index, bridge_type, strategy
            )

            if bridge_content and confidence >= self.config["bridge_confidence_threshold"]:
                # Calculate token cost
                token_cost = len(bridge_content) // 4  # Rough estimation
                token_cost = min(token_cost, limits["max_tokens_per_bridge"])

                # Calculate priority
                priority = self._calculate_bridge_priority(candidate, bridge_type)

                bridge = ContextBridge(
                    bridge_id=f"bridge_{bridge_id_counter}",
                    bridge_type=bridge_type,
                    source_content_ids=[candidate.gap_start_id],
                    target_content_ids=[candidate.gap_end_id],
                    bridge_content=bridge_content,
                    preserved_references=candidate.affected_references,
                    confidence=confidence,
                    token_cost=token_cost,
                    priority=priority,
                )

                bridges.append(bridge)
                logger.debug(
                    f"Generated {bridge_type.value} bridge: {token_cost} tokens, "
                    f"confidence {confidence:.2f}"
                )

        # Sort bridges by priority (highest first)
        bridges.sort(key=lambda x: x.priority, reverse=True)

        return bridges

    def _determine_bridge_type(
        self, candidate: BridgeCandidate, correlation_result: CorrelationResult
    ) -> BridgeType:
        """Determine the most appropriate bridge type for a candidate."""
        # Analyze affected references to determine bridge type
        ref_types = []

        for ref in correlation_result.references:
            if (
                ref.source_id in candidate.missing_content_ids
                or ref.target_id in candidate.missing_content_ids
            ):
                ref_types.append(ref.dependency_type)

        # Priority order for bridge types
        if DependencyType.TOOL_CHAIN in ref_types:
            return BridgeType.TOOL_CHAIN_BRIDGE
        if DependencyType.ERROR_CONTEXT in ref_types:
            return BridgeType.ERROR_CONTEXT_BRIDGE
        if (
            DependencyType.FILE_REFERENCE in ref_types
            or DependencyType.FUNCTION_REFERENCE in ref_types
        ):
            return BridgeType.REFERENCE_BRIDGE
        if DependencyType.CONVERSATION_FLOW in ref_types:
            return BridgeType.CONVERSATION_BRIDGE
        return BridgeType.SUMMARY_BRIDGE

    def _generate_bridge_content(
        self,
        candidate: BridgeCandidate,
        content_index: dict[str, dict[str, Any]],
        bridge_type: BridgeType,
        strategy: BridgingStrategy,
    ) -> tuple[str, float]:
        """Generate bridge content and return content with confidence score."""

        # Get missing content for analysis
        missing_contents = [
            content_index.get(content_id, {}).get("text", "")
            for content_id in candidate.missing_content_ids
        ]

        if bridge_type == BridgeType.TOOL_CHAIN_BRIDGE:
            return self._generate_tool_chain_bridge(missing_contents, strategy)
        if bridge_type == BridgeType.ERROR_CONTEXT_BRIDGE:
            return self._generate_error_context_bridge(missing_contents, strategy)
        if bridge_type == BridgeType.REFERENCE_BRIDGE:
            return self._generate_reference_bridge(candidate, strategy)
        if bridge_type == BridgeType.CONVERSATION_BRIDGE:
            return self._generate_conversation_bridge(missing_contents, strategy)
        if bridge_type == BridgeType.SUMMARY_BRIDGE:
            return self._generate_summary_bridge(missing_contents, strategy)
        return "", 0.0

    def _generate_tool_chain_bridge(
        self, missing_contents: list[str], strategy: BridgingStrategy
    ) -> tuple[str, float]:
        """Generate a bridge for tool chain continuity."""
        # Identify tool-related content
        tool_contents = []
        for content in missing_contents:
            if any(
                keyword in content.lower()
                for keyword in ["function", "call", "result", "tool", "execute", "run"]
            ):
                tool_contents.append(content)

        if not tool_contents:
            return "", 0.0

        # Create bridge based on strategy
        if strategy == BridgingStrategy.CONSERVATIVE:
            # Minimal bridge - just indicate tool activity
            bridge = "[Tool execution and results omitted for brevity]"
            confidence = 0.8
        elif strategy in [BridgingStrategy.MODERATE, BridgingStrategy.AGGRESSIVE]:
            # More detailed bridge with key results
            key_results = self._extract_key_results(tool_contents)
            bridge = f"[Tool execution summary: {key_results}]"
            confidence = 0.7
        else:  # DEPENDENCY_ONLY
            # Minimal dependency preservation
            bridge = "[Tool chain continues...]"
            confidence = 0.6

        return bridge, confidence

    def _generate_error_context_bridge(
        self, missing_contents: list[str], strategy: BridgingStrategy
    ) -> tuple[str, float]:
        """Generate a bridge for error-fix context."""
        # Find error-related content
        error_contents = []
        fix_contents = []

        for content in missing_contents:
            content_lower = content.lower()
            if any(
                keyword in content_lower for keyword in ["error", "exception", "failed", "issue"]
            ):
                error_contents.append(content)
            elif any(
                keyword in content_lower
                for keyword in ["fix", "solve", "correct", "update", "resolve"]
            ):
                fix_contents.append(content)

        if not (error_contents or fix_contents):
            return "", 0.0

        # Generate bridge
        if strategy == BridgingStrategy.CONSERVATIVE:
            bridge = "[Error analysis and resolution steps omitted]"
            confidence = 0.7
        else:
            # Extract key error and fix information
            error_summary = self._extract_error_summary(error_contents)
            fix_summary = self._extract_fix_summary(fix_contents)

            bridge_parts = []
            if error_summary:
                bridge_parts.append(f"Error: {error_summary}")
            if fix_summary:
                bridge_parts.append(f"Resolution: {fix_summary}")

            bridge = f"[{' | '.join(bridge_parts)}]" if bridge_parts else ""
            confidence = 0.8 if bridge_parts else 0.0

        return bridge, confidence

    def _generate_reference_bridge(
        self, candidate: BridgeCandidate, strategy: BridgingStrategy
    ) -> tuple[str, float]:
        """Generate a bridge for file/function references."""
        # Extract references from affected references
        references = []
        for ref_desc in candidate.affected_references:
            if ":" in ref_desc:
                ref_type, ref_text = ref_desc.split(":", 1)
                if ref_type in ["file_ref", "func_ref"]:
                    references.append(ref_text)

        if not references:
            return "", 0.0

        # Generate bridge
        unique_refs = list(set(references))[:3]  # Limit to top 3 references

        if strategy == BridgingStrategy.CONSERVATIVE:
            bridge = f"[References to {', '.join(unique_refs)} omitted]"
            confidence = 0.7
        else:
            bridge = f"[Discussion of {', '.join(unique_refs)} continues...]"
            confidence = 0.6

        return bridge, confidence

    def _generate_conversation_bridge(
        self, missing_contents: list[str], strategy: BridgingStrategy
    ) -> tuple[str, float]:
        """Generate a bridge for conversation flow."""
        if not missing_contents:
            return "", 0.0

        # Simple conversation continuity bridge
        if strategy == BridgingStrategy.AGGRESSIVE:
            bridge = "[Conversation continues with additional context and discussion]"
            confidence = 0.5
        else:
            bridge = "[Additional discussion omitted]"
            confidence = 0.6

        return bridge, confidence

    def _generate_summary_bridge(
        self, missing_contents: list[str], strategy: BridgingStrategy
    ) -> tuple[str, float]:
        """Generate a summary bridge for general content."""
        if not missing_contents:
            return "", 0.0

        # Create a very basic summary
        content_count = len(missing_contents)

        if strategy == BridgingStrategy.AGGRESSIVE and self.config["summarization_enabled"]:
            # Attempt basic summarization
            key_terms = self._extract_key_terms(missing_contents)
            if key_terms:
                bridge = (
                    f"[Summary: Discussion of {', '.join(key_terms[:3])} ({content_count} items)]"
                )
                confidence = 0.4
            else:
                bridge = f"[{content_count} messages omitted for brevity]"
                confidence = 0.3
        else:
            bridge = f"[{content_count} items omitted]"
            confidence = 0.5

        return bridge, confidence

    def _extract_key_results(self, tool_contents: list[str]) -> str:
        """Extract key results from tool-related content."""
        # Simple extraction - look for common result patterns
        results = []
        for content in tool_contents:
            if "result" in content.lower() or "success" in content.lower():
                # Extract short result description
                words = content.split()[:10]  # First 10 words
                results.append(" ".join(words))

        return "; ".join(results[:2]) if results else "execution completed"

    def _extract_error_summary(self, error_contents: list[str]) -> str:
        """Extract error summary from error content."""
        if not error_contents:
            return ""

        # Look for error messages or types
        for content in error_contents:
            # Simple pattern matching for common errors
            words = content.split()
            for i, word in enumerate(words):
                if word.lower() in ["error", "exception", "failed"]:
                    # Extract a few words around the error
                    start = max(0, i - 2)
                    end = min(len(words), i + 4)
                    return " ".join(words[start:end])

        return "error encountered"

    def _extract_fix_summary(self, fix_contents: list[str]) -> str:
        """Extract fix summary from fix content."""
        if not fix_contents:
            return ""

        # Look for fix actions
        for content in fix_contents:
            words = content.split()
            for i, word in enumerate(words):
                if word.lower() in ["fix", "fixed", "solve", "update"]:
                    # Extract context around fix
                    start = max(0, i - 1)
                    end = min(len(words), i + 5)
                    return " ".join(words[start:end])

        return "issue resolved"

    def _extract_key_terms(self, contents: list[str]) -> list[str]:
        """Extract key terms from content for summarization."""
        # Simple term extraction
        word_freq = {}

        for content in contents:
            words = content.lower().split()
            for word in words:
                # Filter out common words and short words
                if len(word) > 3 and word not in {
                    "this",
                    "that",
                    "with",
                    "from",
                    "they",
                    "will",
                    "have",
                    "been",
                }:
                    word_freq[word] = word_freq.get(word, 0) + 1

        # Return most frequent terms
        sorted_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [term for term, freq in sorted_terms[:5] if freq > 1]

    def _calculate_bridge_priority(
        self,
        candidate: BridgeCandidate,
        bridge_type: BridgeType,
    ) -> int:
        """Calculate priority for a bridge (1-100 scale)."""
        base_priority = 50

        # Adjust based on bridge type
        type_priorities = {
            BridgeType.TOOL_CHAIN_BRIDGE: 90,
            BridgeType.ERROR_CONTEXT_BRIDGE: 80,
            BridgeType.REFERENCE_BRIDGE: 70,
            BridgeType.CONVERSATION_BRIDGE: 40,
            BridgeType.SUMMARY_BRIDGE: 30,
        }

        base_priority = type_priorities.get(bridge_type, base_priority)

        # Adjust based on dependency score
        dependency_bonus = int(candidate.dependency_score * 20)

        # Adjust based on reference count
        ref_bonus = min(len(candidate.affected_references) * 5, 15)

        return min(100, base_priority + dependency_bonus + ref_bonus)

    def _calculate_preservation_score(
        self,
        correlation_result: CorrelationResult,
        bridges: list[ContextBridge],
        filtered_content_ids: set[str],
    ) -> float:
        """Calculate how well dependencies are preserved after bridging."""
        if not correlation_result.references:
            return 1.0

        preserved_refs = 0
        total_critical_refs = 0

        for ref in correlation_result.references:
            if ref.strength in [ReferenceStrength.CRITICAL, ReferenceStrength.STRONG]:
                total_critical_refs += 1

                # Check if reference is preserved either directly or via bridges
                source_preserved = ref.source_id in filtered_content_ids or any(
                    ref.source_id in bridge.source_content_ids for bridge in bridges
                )
                target_preserved = ref.target_id in filtered_content_ids or any(
                    ref.target_id in bridge.target_content_ids for bridge in bridges
                )

                if source_preserved and target_preserved:
                    preserved_refs += 1

        return (preserved_refs / total_critical_refs) if total_critical_refs > 0 else 1.0

    def update_config(self, config_updates: dict[str, Any]) -> None:
        """
        Update bridge builder configuration.

        Args:
            config_updates: Configuration updates to apply
        """
        self.config.update(config_updates)
        logger.info(f"ContextBridgeBuilder config updated: {config_updates}")

    def get_config(self) -> dict[str, Any]:
        """
        Get current bridge builder configuration.

        Returns:
            Current configuration dictionary
        """
        return self.config.copy()
