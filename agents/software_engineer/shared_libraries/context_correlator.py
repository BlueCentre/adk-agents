"""Context correlation system for cross-turn dependency analysis and bridging."""

from dataclasses import dataclass
from enum import Enum
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of context dependencies."""

    TOOL_CHAIN = "tool_chain"  # Tool call -> result sequences
    VARIABLE_REFERENCE = "var_ref"  # Variable/symbol references
    FILE_REFERENCE = "file_ref"  # File path references
    ERROR_CONTEXT = "error_ctx"  # Error -> fix sequences
    CONVERSATION_FLOW = "conv_flow"  # Natural conversation continuity
    FUNCTION_REFERENCE = "func_ref"  # Function/method references
    CONCEPT_CONTINUATION = "concept"  # Topic/concept continuity


class ReferenceStrength(Enum):
    """Strength of reference relationships."""

    CRITICAL = "critical"  # Essential for understanding (tool chains, direct refs)
    STRONG = "strong"  # Important for context (recent errors, file refs)
    MODERATE = "moderate"  # Helpful for context (conversation flow)
    WEAK = "weak"  # Background context (distant topics)


@dataclass(frozen=True)
class ContextReference:
    """Represents a reference between content items."""

    source_id: str  # ID of content making reference
    target_id: str  # ID of referenced content
    dependency_type: DependencyType  # Type of dependency
    strength: ReferenceStrength  # Strength of relationship
    reference_text: str  # Text that creates the reference
    confidence: float  # Confidence in reference detection (0.0-1.0)
    bidirectional: bool = False  # Whether reference goes both ways

    def __post_init__(self):
        """Validate reference data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class DependencyCluster:
    """A cluster of related content items."""

    cluster_id: str
    content_ids: list[str]
    primary_type: DependencyType
    cluster_strength: ReferenceStrength
    internal_references: list[ContextReference]
    cluster_summary: str

    def add_content(self, content_id: str) -> None:
        """Add content to cluster if not already present."""
        if content_id not in self.content_ids:
            self.content_ids.append(content_id)

    def get_cluster_size(self) -> int:
        """Get number of items in cluster."""
        return len(self.content_ids)


@dataclass
class CorrelationResult:
    """Result of context correlation analysis."""

    references: list[ContextReference]
    clusters: list[DependencyCluster]
    correlation_metadata: dict[str, Any]
    processing_time: float
    content_processed: int
    references_found: int


class ContextCorrelator:
    """Advanced context correlation and dependency analysis system."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the context correlator.

        Args:
            config: Optional configuration for correlation behavior
        """
        default_config = self._get_default_config()
        if config:
            default_config.update(config)
        self.config = default_config

        # Pre-compiled regex patterns for efficiency
        self._compile_patterns()

        logger.debug(f"ContextCorrelator initialized with config: {self.config}")

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration for context correlation."""
        return {
            # Reference detection settings
            "min_confidence_threshold": 0.3,  # Minimum confidence for reference inclusion
            "strong_reference_threshold": 0.7,  # Threshold for strong references
            "critical_reference_threshold": 0.9,  # Threshold for critical references
            # Pattern matching weights
            "exact_match_weight": 1.0,  # Weight for exact text matches
            "fuzzy_match_weight": 0.7,  # Weight for fuzzy matches
            "semantic_match_weight": 0.5,  # Weight for semantic matches
            # Clustering parameters
            "min_cluster_size": 2,  # Minimum items for cluster formation
            "max_cluster_size": 20,  # Maximum items in single cluster
            "cluster_merge_threshold": 0.8,  # Threshold for merging clusters
            # Tool chain settings
            "tool_chain_window": 10,  # Messages to look back for tool chains
            "tool_chain_timeout": 300,  # Seconds after which tool chains expire
            # Reference type priorities
            "dependency_weights": {
                DependencyType.TOOL_CHAIN: 1.0,
                DependencyType.ERROR_CONTEXT: 0.9,
                DependencyType.FILE_REFERENCE: 0.8,
                DependencyType.FUNCTION_REFERENCE: 0.7,
                DependencyType.VARIABLE_REFERENCE: 0.6,
                DependencyType.CONVERSATION_FLOW: 0.4,
                DependencyType.CONCEPT_CONTINUATION: 0.3,
            },
        }

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        self.patterns = {
            # File references (various formats)
            "file_paths": re.compile(
                r"(?:(?:src/|tests/|agents/|\./)[\w/.-]+\.(?:py|js|ts|md|json|yml|yaml)|"
                r"\b[\w.-]+\.(?:py|js|ts|md|json|yml|yaml)\b)",
                re.IGNORECASE,
            ),
            # Function/method references
            "functions": re.compile(
                r"(?:\b(?:def |function |class |async def )?(\w+)(?:\(|\s*=)|"  # Definition
                r"\b(\w+)\.(\w+)\(|"  # Method calls
                r"\b(\w+)\(\)|"  # Function calls
                r"\b(\w+)\s+function\b|"  # "function_name function"
                r"\bfunction\s+(\w+)\b)",  # "function function_name"
                re.IGNORECASE,
            ),
            # Variable references
            "variables": re.compile(
                r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=|"  # Assignment: var =
                r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s+(?:for|in|with|validation|processing))|"  # Usage context  # noqa: E501
                r"\b(self\.[\w.]+)|"  # Self attributes
                r"\$\{?(\w+)\}?",  # Shell variables
                re.IGNORECASE,
            ),
            # Error patterns
            "errors": re.compile(
                r"(?:Error|Exception|Failed?|Issue).*?(?:in|at|on)\s+([^\s\n.,:;]+)|"
                r"(?:line\s+(\d+)|at\s+line\s+(\d+))|"
                r"(?:Traceback|Stack trace)",
                re.IGNORECASE | re.MULTILINE,
            ),
            # Tool call references
            "tool_calls": re.compile(
                r"(?:calling|call|invoke|run|execute)\s+(\w+)|"
                r"tool[:\s]+(\w+)|"
                r"function[:\s]+(\w+)",
                re.IGNORECASE,
            ),
            # Cross references
            "cross_refs": re.compile(
                r"(?:see|refer to|mentioned|discussed|above|below|earlier|previously|"
                r"as shown|as seen|like|similar to)\s+(?:in\s+)?([^\s\n.,:;]+)",
                re.IGNORECASE,
            ),
        }

    def correlate_context(self, content_items: list[dict[str, Any]]) -> CorrelationResult:
        """
        Perform comprehensive context correlation analysis.

        Args:
            content_items: List of content items to analyze

        Returns:
            CorrelationResult with references, clusters, and metadata
        """
        import time

        start_time = time.time()

        logger.info(f"Starting context correlation for {len(content_items)} items")

        # Detect all references
        references = self._detect_all_references(content_items)

        # Filter references by confidence threshold
        filtered_references = [
            ref for ref in references if ref.confidence >= self.config["min_confidence_threshold"]
        ]

        # Build dependency clusters
        clusters = self._build_dependency_clusters(filtered_references)

        # Calculate processing metadata
        processing_time = time.time() - start_time

        correlation_metadata = {
            "processing_time": processing_time,
            "total_references_detected": len(references),
            "filtered_references": len(filtered_references),
            "clusters_formed": len(clusters),
            "average_cluster_size": sum(c.get_cluster_size() for c in clusters) / len(clusters)
            if clusters
            else 0,
            "reference_types": {
                dep_type.value: len(
                    [r for r in filtered_references if r.dependency_type == dep_type]
                )
                for dep_type in DependencyType
            },
        }

        result = CorrelationResult(
            references=filtered_references,
            clusters=clusters,
            correlation_metadata=correlation_metadata,
            processing_time=processing_time,
            content_processed=len(content_items),
            references_found=len(filtered_references),
        )

        logger.info(
            f"Context correlation complete: {len(filtered_references)} references, "
            f"{len(clusters)} clusters in {processing_time:.3f}s"
        )

        return result

    def _detect_all_references(self, content_items: list[dict[str, Any]]) -> list[ContextReference]:
        """Detect all types of references between content items."""
        all_references = []

        # Tool chain references
        tool_refs = self._detect_tool_chain_references(content_items)
        all_references.extend(tool_refs)

        # File references
        file_refs = self._detect_file_references(content_items)
        all_references.extend(file_refs)

        # Function references
        func_refs = self._detect_function_references(content_items)
        all_references.extend(func_refs)

        # Variable references
        var_refs = self._detect_variable_references(content_items)
        all_references.extend(var_refs)

        # Error context references
        error_refs = self._detect_error_context_references(content_items)
        all_references.extend(error_refs)

        # Conversation flow references
        flow_refs = self._detect_conversation_flow_references(content_items)
        all_references.extend(flow_refs)

        # Concept continuation references
        concept_refs = self._detect_concept_references(content_items)
        all_references.extend(concept_refs)

        logger.debug(f"Detected {len(all_references)} total references across all types")

        return all_references

    def _detect_tool_chain_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect tool call -> result reference chains."""
        references = []

        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))

            # Look for tool calls
            if item.get("has_function_call"):
                # Look for subsequent tool results within window
                window_end = min(i + self.config["tool_chain_window"], len(content_items))

                for j in range(i + 1, window_end):
                    next_item = content_items[j]
                    next_id = next_item.get("id", str(j))

                    if next_item.get("has_function_response"):
                        # Strong tool chain reference
                        ref = ContextReference(
                            source_id=item_id,
                            target_id=next_id,
                            dependency_type=DependencyType.TOOL_CHAIN,
                            strength=ReferenceStrength.CRITICAL,
                            reference_text="tool_call -> tool_result",
                            confidence=0.95,
                            bidirectional=True,
                        )
                        references.append(ref)
                        break  # Found the result for this call

            # Look for incomplete tool chains (high priority for preservation)
            if item.get("has_function_call") and not any(
                content_items[k].get("has_function_response")
                for k in range(i + 1, min(i + self.config["tool_chain_window"], len(content_items)))
            ):
                # Mark as incomplete tool chain (needs preservation)
                item["is_incomplete_tool_chain"] = True

        logger.debug(f"Detected {len(references)} tool chain references")
        return references

    def _detect_file_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect file path and name references between content items."""
        references = []

        # Build file reference index
        file_mentions = {}
        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))
            text = item.get("text", "")

            # Find file path mentions
            file_matches = self.patterns["file_paths"].findall(text)
            for file_path in file_matches:
                if file_path not in file_mentions:
                    file_mentions[file_path] = []
                file_mentions[file_path].append((item_id, text))

        # Create references between items mentioning same files
        for file_path, mentions in file_mentions.items():
            if len(mentions) > 1:
                # Create references between all pairs
                for i, (source_id, source_text) in enumerate(mentions):
                    for _, (target_id, target_text) in enumerate(mentions[i + 1 :], i + 1):
                        confidence = self._calculate_file_reference_confidence(
                            file_path, source_text, target_text
                        )

                        if confidence >= self.config["min_confidence_threshold"]:
                            ref = ContextReference(
                                source_id=source_id,
                                target_id=target_id,
                                dependency_type=DependencyType.FILE_REFERENCE,
                                strength=self._get_reference_strength(confidence),
                                reference_text=file_path,
                                confidence=confidence,
                                bidirectional=True,
                            )
                            references.append(ref)

        logger.debug(f"Detected {len(references)} file references")
        return references

    def _detect_function_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect function and method references between content items."""
        references = []

        # Build function reference index
        function_mentions = {}
        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))
            text = item.get("text", "")

            # Find function mentions
            function_matches = self.patterns["functions"].findall(text)
            for match_groups in function_matches:
                # Extract non-empty group (different capture groups from regex)
                function_name = next((g for g in match_groups if g), None)
                if function_name and len(function_name) > 2:  # Filter out short matches
                    if function_name not in function_mentions:
                        function_mentions[function_name] = []
                    function_mentions[function_name].append((item_id, text))

        # Create references between items mentioning same functions
        for function_name, mentions in function_mentions.items():
            if len(mentions) > 1:
                for i, (source_id, source_text) in enumerate(mentions):
                    for _, (target_id, target_text) in enumerate(mentions[i + 1 :], i + 1):
                        confidence = self._calculate_function_reference_confidence(
                            function_name, source_text, target_text
                        )

                        if confidence >= self.config["min_confidence_threshold"]:
                            ref = ContextReference(
                                source_id=source_id,
                                target_id=target_id,
                                dependency_type=DependencyType.FUNCTION_REFERENCE,
                                strength=self._get_reference_strength(confidence),
                                reference_text=function_name,
                                confidence=confidence,
                                bidirectional=True,
                            )
                            references.append(ref)

        logger.debug(f"Detected {len(references)} function references")
        return references

    def _detect_variable_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect variable and symbol references between content items."""
        references = []

        # Build variable reference index (similar pattern to functions)
        variable_mentions = {}
        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))
            text = item.get("text", "")

            # Find variable mentions
            variable_matches = self.patterns["variables"].findall(text)
            for match_groups in variable_matches:
                variable_name = next((g for g in match_groups if g), None)
                if variable_name and len(variable_name) > 1:  # Filter short vars
                    # Skip common words that aren't likely variables
                    if variable_name.lower() not in {
                        "the",
                        "and",
                        "or",
                        "if",
                        "in",
                        "to",
                        "of",
                        "a",
                        "is",
                    }:
                        if variable_name not in variable_mentions:
                            variable_mentions[variable_name] = []
                        variable_mentions[variable_name].append((item_id, text))

        # Create references (similar to function references but with lower confidence)
        for variable_name, mentions in variable_mentions.items():
            if len(mentions) > 1:
                for i, (source_id, source_text) in enumerate(mentions):
                    for _, (target_id, target_text) in enumerate(mentions[i + 1 :], i + 1):
                        confidence = self._calculate_variable_reference_confidence(
                            variable_name, source_text, target_text
                        )

                        if confidence >= self.config["min_confidence_threshold"]:
                            ref = ContextReference(
                                source_id=source_id,
                                target_id=target_id,
                                dependency_type=DependencyType.VARIABLE_REFERENCE,
                                strength=self._get_reference_strength(confidence),
                                reference_text=variable_name,
                                confidence=confidence,
                                bidirectional=True,
                            )
                            references.append(ref)

        logger.debug(f"Detected {len(references)} variable references")
        return references

    def _detect_error_context_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect error -> fix context references."""
        references = []

        # Find error messages and their potential fixes
        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))
            text = item.get("text", "")

            # Check if this item contains error indicators
            if (
                item.get("error_indicators")
                or self.patterns["errors"].search(text)
                or any(
                    keyword in text.lower()
                    for keyword in ["error", "exception", "failed", "traceback"]
                )
            ):
                # Look ahead for potential fixes/solutions
                for j in range(i + 1, min(i + 5, len(content_items))):  # Look at next few items
                    next_item = content_items[j]
                    next_id = next_item.get("id", str(j))
                    next_text = next_item.get("text", "")

                    # Check for fix indicators
                    if any(
                        keyword in next_text.lower()
                        for keyword in ["fix", "solve", "correct", "update", "change", "modify"]
                    ):
                        confidence = 0.7  # Moderate confidence for error-fix relationships
                        ref = ContextReference(
                            source_id=item_id,
                            target_id=next_id,
                            dependency_type=DependencyType.ERROR_CONTEXT,
                            strength=ReferenceStrength.STRONG,
                            reference_text="error -> fix",
                            confidence=confidence,
                        )
                        references.append(ref)

        logger.debug(f"Detected {len(references)} error context references")
        return references

    def _detect_conversation_flow_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect natural conversation flow references."""
        references = []

        for i in range(1, len(content_items)):  # Start from second item
            current_item = content_items[i]
            prev_item = content_items[i - 1]

            current_id = current_item.get("id", str(i))
            prev_id = prev_item.get("id", str(i - 1))
            current_text = current_item.get("text", "")

            # Look for conversation flow indicators
            flow_indicators = self.patterns["cross_refs"].findall(current_text)

            if flow_indicators or any(
                phrase in current_text.lower()
                for phrase in ["as mentioned", "like you said", "continuing", "also", "furthermore"]
            ):
                confidence = 0.5  # Moderate confidence for conversation flow
                ref = ContextReference(
                    source_id=current_id,
                    target_id=prev_id,
                    dependency_type=DependencyType.CONVERSATION_FLOW,
                    strength=ReferenceStrength.MODERATE,
                    reference_text="conversation_flow",
                    confidence=confidence,
                )
                references.append(ref)

        logger.debug(f"Detected {len(references)} conversation flow references")
        return references

    def _detect_concept_references(
        self, content_items: list[dict[str, Any]]
    ) -> list[ContextReference]:
        """Detect concept continuation and topic references."""
        references = []

        # Simple keyword-based concept detection for now
        # In production, this could use more sophisticated NLP

        concept_keywords = {}
        for i, item in enumerate(content_items):
            item_id = item.get("id", str(i))
            text = item.get("text", "").lower()

            # Extract potential concept keywords (nouns, technical terms)
            words = re.findall(r"\b[a-z]{4,}\b", text)  # Words 4+ chars
            for word in words:
                if word not in {
                    "this",
                    "that",
                    "with",
                    "from",
                    "they",
                    "will",
                    "have",
                    "been",
                    "when",
                    "what",
                    "where",
                }:
                    if word not in concept_keywords:
                        concept_keywords[word] = []
                    concept_keywords[word].append(item_id)

        # Create concept references
        for concept, item_ids in concept_keywords.items():
            if len(item_ids) > 2:  # Only if concept appears in multiple items
                # Create references between items sharing concepts
                for i, source_id in enumerate(item_ids):
                    for target_id in item_ids[i + 1 :]:
                        confidence = 0.4  # Lower confidence for concept matching
                        ref = ContextReference(
                            source_id=source_id,
                            target_id=target_id,
                            dependency_type=DependencyType.CONCEPT_CONTINUATION,
                            strength=ReferenceStrength.WEAK,
                            reference_text=concept,
                            confidence=confidence,
                            bidirectional=True,
                        )
                        references.append(ref)

        logger.debug(f"Detected {len(references)} concept references")
        return references

    def _calculate_file_reference_confidence(self, file_path: str, text1: str, text2: str) -> float:
        """Calculate confidence for file reference correlation."""
        base_confidence = 0.7

        # Boost confidence if file path is specific (has directory structure)
        if "/" in file_path:
            base_confidence += 0.1

        # Boost if file appears in similar contexts
        context_similarity = self._calculate_text_similarity(text1, text2)
        confidence = base_confidence + (context_similarity * 0.2)

        return min(1.0, confidence)

    def _calculate_function_reference_confidence(
        self, function_name: str, text1: str, text2: str
    ) -> float:
        """Calculate confidence for function reference correlation."""
        base_confidence = 0.6

        # Boost for longer function names (more specific)
        if len(function_name) > 6:
            base_confidence += 0.1

        # Boost for similar contexts
        context_similarity = self._calculate_text_similarity(text1, text2)
        confidence = base_confidence + (context_similarity * 0.2)

        return min(1.0, confidence)

    def _calculate_variable_reference_confidence(
        self, variable_name: str, text1: str, text2: str
    ) -> float:
        """Calculate confidence for variable reference correlation."""
        base_confidence = 0.4  # Lower base confidence for variables

        # Boost for longer variable names
        if len(variable_name) > 4:
            base_confidence += 0.1

        # Boost for similar contexts
        context_similarity = self._calculate_text_similarity(text1, text2)
        confidence = base_confidence + (context_similarity * 0.15)

        return min(1.0, confidence)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity between two texts."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _get_reference_strength(self, confidence: float) -> ReferenceStrength:
        """Convert confidence score to reference strength."""
        if confidence >= self.config["critical_reference_threshold"]:
            return ReferenceStrength.CRITICAL
        if confidence >= self.config["strong_reference_threshold"]:
            return ReferenceStrength.STRONG
        if confidence >= 0.5:
            return ReferenceStrength.MODERATE
        return ReferenceStrength.WEAK

    def _build_dependency_clusters(
        self, references: list[ContextReference]
    ) -> list[DependencyCluster]:
        """Build clusters of related content based on references."""
        clusters = []

        # Group references by type for initial clustering
        refs_by_type = {}
        for ref in references:
            if ref.dependency_type not in refs_by_type:
                refs_by_type[ref.dependency_type] = []
            refs_by_type[ref.dependency_type].append(ref)

        # Build clusters for each reference type
        cluster_id_counter = 0
        for dep_type, type_refs in refs_by_type.items():
            if not type_refs:
                continue

            # Group connected components
            connected_groups = self._find_connected_components(type_refs)

            for group_refs in connected_groups:
                if len(group_refs) >= self.config["min_cluster_size"]:
                    cluster_id_counter += 1

                    # Collect all content IDs in this cluster
                    content_ids = set()
                    for ref in group_refs:
                        content_ids.add(ref.source_id)
                        content_ids.add(ref.target_id)

                    # Determine cluster strength (highest reference strength)
                    strength_priorities = {
                        ReferenceStrength.CRITICAL: 4,
                        ReferenceStrength.STRONG: 3,
                        ReferenceStrength.MODERATE: 2,
                        ReferenceStrength.WEAK: 1,
                    }
                    max_priority = max(strength_priorities[ref.strength] for ref in group_refs)
                    cluster_strength = next(
                        strength
                        for strength, priority in strength_priorities.items()
                        if priority == max_priority
                    )

                    # Generate cluster summary
                    cluster_summary = self._generate_cluster_summary(
                        list(content_ids), group_refs, dep_type
                    )

                    cluster = DependencyCluster(
                        cluster_id=f"cluster_{cluster_id_counter}",
                        content_ids=list(content_ids),
                        primary_type=dep_type,
                        cluster_strength=cluster_strength,
                        internal_references=group_refs,
                        cluster_summary=cluster_summary,
                    )

                    clusters.append(cluster)

        logger.debug(f"Built {len(clusters)} dependency clusters")
        return clusters

    def _find_connected_components(
        self, references: list[ContextReference]
    ) -> list[list[ContextReference]]:
        """Find connected components in reference graph."""
        # Build adjacency list
        graph = {}
        ref_map = {}

        for ref in references:
            # Add nodes
            if ref.source_id not in graph:
                graph[ref.source_id] = []
            if ref.target_id not in graph:
                graph[ref.target_id] = []

            # Add edges
            graph[ref.source_id].append(ref.target_id)
            if ref.bidirectional:
                graph[ref.target_id].append(ref.source_id)

            # Map edges to references
            edge_key = (ref.source_id, ref.target_id)
            ref_map[edge_key] = ref

        # Find connected components using DFS
        visited = set()
        components = []

        def dfs(node, component_nodes, component_refs):
            visited.add(node)
            component_nodes.add(node)

            for neighbor in graph.get(node, []):
                # Add reference to component
                edge_key = (node, neighbor)
                if edge_key in ref_map:
                    component_refs.add(ref_map[edge_key])

                if neighbor not in visited:
                    dfs(neighbor, component_nodes, component_refs)

        for node in graph:
            if node not in visited:
                component_nodes = set()
                component_refs = set()
                dfs(node, component_nodes, component_refs)
                if component_refs:  # Only include if has references
                    components.append(list(component_refs))

        return components

    def _generate_cluster_summary(
        self,
        content_ids: list[str],
        references: list[ContextReference],
        dep_type: DependencyType,
    ) -> str:
        """Generate a human-readable summary of a dependency cluster."""

        ref_texts = [ref.reference_text for ref in references if ref.reference_text]
        unique_refs = list(set(ref_texts))[:3]  # Top 3 unique references

        type_descriptions = {
            DependencyType.TOOL_CHAIN: f"Tool chain cluster with {len(content_ids)} items",
            DependencyType.FILE_REFERENCE: f"File references: {', '.join(unique_refs[:2])}",
            DependencyType.FUNCTION_REFERENCE: f"Function references: {', '.join(unique_refs[:2])}",
            DependencyType.VARIABLE_REFERENCE: f"Variable references: {', '.join(unique_refs[:2])}",
            DependencyType.ERROR_CONTEXT: f"Error context with {len(references)} connections",
            DependencyType.CONVERSATION_FLOW: (
                f"Conversation flow with {len(content_ids)} connected items"
            ),
            DependencyType.CONCEPT_CONTINUATION: f"Concept cluster: {', '.join(unique_refs[:3])}",
        }

        return type_descriptions.get(
            dep_type, f"{dep_type.value} cluster with {len(content_ids)} items"
        )

    def get_dependency_strength_score(
        self, content_id: str, correlation_result: CorrelationResult
    ) -> float:
        """
        Calculate dependency strength score for a content item.

        Args:
            content_id: ID of content item to score
            correlation_result: Result from correlation analysis

        Returns:
            Dependency strength score (0.0-1.0)
        """
        total_score = 0.0
        reference_count = 0

        # Score based on references involving this content
        for ref in correlation_result.references:
            if ref.source_id == content_id or ref.target_id == content_id:
                # Weight by dependency type and reference strength
                type_weight = self.config["dependency_weights"].get(ref.dependency_type, 0.5)
                strength_weight = {
                    ReferenceStrength.CRITICAL: 1.0,
                    ReferenceStrength.STRONG: 0.8,
                    ReferenceStrength.MODERATE: 0.6,
                    ReferenceStrength.WEAK: 0.4,
                }.get(ref.strength, 0.5)

                score = ref.confidence * type_weight * strength_weight
                total_score += score
                reference_count += 1

        # Score based on cluster membership
        for cluster in correlation_result.clusters:
            if content_id in cluster.content_ids:
                cluster_weight = {
                    ReferenceStrength.CRITICAL: 0.2,
                    ReferenceStrength.STRONG: 0.15,
                    ReferenceStrength.MODERATE: 0.1,
                    ReferenceStrength.WEAK: 0.05,
                }.get(cluster.cluster_strength, 0.05)

                total_score += cluster_weight

        # Normalize score
        if reference_count > 0:
            total_score = total_score / max(1, reference_count * 0.8)  # Slight normalization

        return min(1.0, total_score)

    def update_config(self, config_updates: dict[str, Any]) -> None:
        """
        Update correlator configuration.

        Args:
            config_updates: Configuration updates to apply
        """
        self.config.update(config_updates)
        # Recompile patterns if needed
        if any(key.startswith("pattern") for key in config_updates):
            self._compile_patterns()
        logger.info(f"ContextCorrelator config updated: {config_updates}")

    def get_config(self) -> dict[str, Any]:
        """
        Get current correlator configuration.

        Returns:
            Current configuration dictionary
        """
        return self.config.copy()
