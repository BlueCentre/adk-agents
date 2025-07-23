"""Context assembly system for budget-constrained conversation building."""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Optional

from .token_optimization import TokenCounter

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for context assembly."""

    CRITICAL = "critical"  # System messages, current turn, active tool chains
    HIGH = "high"  # Recent errors, incomplete tasks, tool results
    MEDIUM = "medium"  # Recent conversations with tool activity
    LOW = "low"  # Older conversations, background context
    MINIMAL = "minimal"  # Emergency fallback content


@dataclass
class BudgetAllocation:
    """Budget allocation across priority levels."""

    total_budget: int
    critical_budget: int
    high_budget: int
    medium_budget: int
    low_budget: int
    minimal_budget: int
    reserved_emergency: int

    def __post_init__(self):
        """Validate budget allocation consistency."""
        allocated_total = (
            self.critical_budget
            + self.high_budget
            + self.medium_budget
            + self.low_budget
            + self.minimal_budget
            + self.reserved_emergency
        )

        if allocated_total > self.total_budget:
            raise ValueError(
                f"Budget allocation exceeds total: {allocated_total} > {self.total_budget}"
            )


@dataclass
class AssemblyResult:
    """Result of context assembly process."""

    assembled_content: list[dict[str, Any]]
    total_tokens_used: int
    budget_utilization: float
    content_by_priority: dict[str, list[dict[str, Any]]]
    tokens_by_priority: dict[str, int]
    assembly_strategy: str
    emergency_mode_used: bool
    truncation_applied: bool
    preserved_critical_content: bool


class ContextAssembler:
    """Priority-based context assembly for token budget management."""

    def __init__(
        self, token_counter: Optional[TokenCounter] = None, config: Optional[dict[str, Any]] = None
    ):
        """
        Initialize the context assembler.

        Args:
            token_counter: TokenCounter instance for token calculations
            config: Optional configuration for assembly behavior
        """
        self.token_counter = token_counter
        default_config = self._get_default_config()
        if config:
            default_config.update(config)
        self.config = default_config

        logger.debug(f"ContextAssembler initialized with config: {self.config}")

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration for context assembly."""
        return {
            # Budget allocation percentages
            "critical_budget_pct": 0.25,  # 25% for critical content
            "high_budget_pct": 0.30,  # 30% for high priority
            "medium_budget_pct": 0.25,  # 25% for medium priority
            "low_budget_pct": 0.15,  # 15% for low priority
            "minimal_budget_pct": 0.05,  # 5% for minimal content
            # Emergency and safety settings
            "emergency_reserve_pct": 0.10,  # 10% emergency reserve
            "min_critical_tokens": 500,  # Minimum tokens for critical content
            "emergency_threshold": 0.90,  # Trigger emergency mode at 90% budget
            # Assembly behavior
            "allow_partial_inclusion": True,  # Allow partial content inclusion
            "preserve_message_boundaries": True,  # Don't break messages mid-content
            "prioritize_recent_errors": True,  # Give recent errors extra priority
            "max_assembly_items": 1000,  # Maximum items to process
        }

    def calculate_budget_allocation(self, total_budget: int) -> BudgetAllocation:
        """
        Calculate budget allocation across priority levels.

        Args:
            total_budget: Total token budget available

        Returns:
            BudgetAllocation with tokens allocated per priority level
        """
        config = self.config

        # Calculate emergency reserve first
        emergency_reserve = int(total_budget * config["emergency_reserve_pct"])
        available_budget = total_budget - emergency_reserve

        # Handle very small budgets
        if available_budget < config["min_critical_tokens"]:
            # For very small budgets, adjust allocations accordingly
            critical_budget = max(50, available_budget // 2)  # At least 50 tokens or half budget
            emergency_reserve = total_budget - available_budget
        else:
            # Normal allocation
            critical_budget = max(
                config["min_critical_tokens"], int(available_budget * config["critical_budget_pct"])
            )
        high_budget = int(available_budget * config["high_budget_pct"])
        medium_budget = int(available_budget * config["medium_budget_pct"])
        low_budget = int(available_budget * config["low_budget_pct"])
        minimal_budget = int(available_budget * config["minimal_budget_pct"])

        # Adjust if critical minimum causes overflow
        total_allocated = (
            critical_budget + high_budget + medium_budget + low_budget + minimal_budget
        )
        if total_allocated > available_budget:
            # Proportionally reduce non-critical allocations
            excess = total_allocated - available_budget
            non_critical_total = high_budget + medium_budget + low_budget + minimal_budget

            if non_critical_total > 0:
                reduction_factor = min(1.0, excess / non_critical_total)

                high_budget = max(0, int(high_budget * (1 - reduction_factor)))
                medium_budget = max(0, int(medium_budget * (1 - reduction_factor)))
                low_budget = max(0, int(low_budget * (1 - reduction_factor)))
                minimal_budget = max(0, int(minimal_budget * (1 - reduction_factor)))
            else:
                # If all non-critical budgets are 0, use minimal allocations
                remaining = available_budget - critical_budget
                if remaining >= 4:
                    high_budget = max(0, remaining // 4)
                    medium_budget = max(0, remaining // 4)
                    low_budget = max(0, remaining // 4)
                    minimal_budget = max(0, remaining // 4)
                else:
                    high_budget = medium_budget = low_budget = minimal_budget = 0

        allocation = BudgetAllocation(
            total_budget=total_budget,
            critical_budget=critical_budget,
            high_budget=high_budget,
            medium_budget=medium_budget,
            low_budget=low_budget,
            minimal_budget=minimal_budget,
            reserved_emergency=emergency_reserve,
        )

        logger.debug(
            f"Budget allocation: Critical={critical_budget}, High={high_budget}, "
            f"Medium={medium_budget}, Low={low_budget}, Minimal={minimal_budget}, "
            f"Emergency={emergency_reserve}"
        )

        return allocation

    def _classify_content_priority(self, content: dict[str, Any]) -> PriorityLevel:
        """
        Classify content into priority levels.

        Args:
            content: Content item with priority_score and metadata

        Returns:
            PriorityLevel classification
        """
        priority_score = content.get("priority_score", 0.0)

        # Critical content: System messages, current turn, incomplete tool chains
        if (
            content.get("is_system_message", False)
            or content.get("is_current_turn", False)
            or content.get("is_incomplete_tool_chain", False)
            or priority_score >= 0.9
        ):
            return PriorityLevel.CRITICAL

        # High priority: Errors, recent tool activity, high scores
        if (
            content.get("error_indicators")
            or content.get("has_recent_errors", False)
            or (content.get("tool_count", 0) > 0 and priority_score >= 0.7)
        ):
            return PriorityLevel.HIGH

        # Medium priority: Some tool activity, moderate scores
        if content.get("tool_count", 0) > 0 or priority_score >= 0.5:
            return PriorityLevel.MEDIUM

        # Low priority: Basic content with some relevance
        if priority_score >= 0.2:
            return PriorityLevel.LOW

        # Minimal priority: Everything else
        return PriorityLevel.MINIMAL

    def _calculate_content_tokens(self, content: dict[str, Any]) -> int:
        """
        Calculate token count for content item.

        Args:
            content: Content item

        Returns:
            Estimated token count
        """
        if not self.token_counter:
            # Fallback estimation
            text = content.get("text", "")
            return len(text) // 4

        text = content.get("text", "")
        return self.token_counter.count_tokens(text)

    def _assemble_priority_level(
        self, content_items: list[dict[str, Any]], budget: int, priority_level: PriorityLevel
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Assemble content for a specific priority level within budget.

        Args:
            content_items: Content items for this priority level
            budget: Token budget for this priority level
            priority_level: Priority level being assembled

        Returns:
            Tuple of (selected_content, tokens_used)
        """
        if not content_items or budget <= 0:
            return [], 0

        selected_content = []
        tokens_used = 0

        # Sort by priority score within level (highest first)
        sorted_items = sorted(
            content_items, key=lambda x: x.get("priority_score", 0.0), reverse=True
        )

        for item in sorted_items:
            item_tokens = self._calculate_content_tokens(item)

            # Check if item fits in remaining budget
            if tokens_used + item_tokens <= budget:
                selected_content.append(item)
                tokens_used += item_tokens

                logger.debug(
                    f"Added {priority_level.value} priority item: "
                    f"{item_tokens} tokens (total: {tokens_used}/{budget})"
                )
            else:
                # Check if partial inclusion is allowed and beneficial
                if (
                    self.config["allow_partial_inclusion"]
                    and budget - tokens_used >= 100  # At least 100 tokens remaining
                ):
                    # For large content, try to include a summary or key parts
                    remaining_budget = budget - tokens_used
                    if self._try_partial_inclusion(item, remaining_budget):
                        partial_item = self._create_partial_content(item, remaining_budget)
                        if partial_item:
                            partial_tokens = self._calculate_content_tokens(partial_item)
                            selected_content.append(partial_item)
                            tokens_used += partial_tokens

                            logger.debug(
                                f"Added partial {priority_level.value} item: "
                                f"{partial_tokens} tokens"
                            )

                # Budget exhausted for this priority level
                break

        logger.info(
            f"Assembled {len(selected_content)} items for {priority_level.value} priority: "
            f"{tokens_used}/{budget} tokens ({tokens_used / budget * 100:.1f}%)"
        )

        return selected_content, tokens_used

    def _try_partial_inclusion(self, content: dict[str, Any], remaining_budget: int) -> bool:
        """
        Determine if partial inclusion is worthwhile for this content.

        Args:
            content: Content item to evaluate
            remaining_budget: Remaining token budget

        Returns:
            True if partial inclusion should be attempted
        """
        # Don't partially include system messages or critical content
        if content.get("is_system_message", False) or content.get("is_current_turn", False):
            return False

        # Only attempt partial inclusion for substantial content
        content_tokens = self._calculate_content_tokens(content)
        return content_tokens > remaining_budget * 2  # Content is at least 2x remaining budget

    def _create_partial_content(
        self, content: dict[str, Any], budget: int
    ) -> Optional[dict[str, Any]]:
        """
        Create a partial version of content that fits within budget.

        Args:
            content: Original content item
            budget: Available token budget

        Returns:
            Partial content item or None if not feasible
        """
        text = content.get("text", "")
        if not text:
            return None

        # Estimate how much text we can include (roughly 4 chars per token)
        max_chars = budget * 4

        if len(text) <= max_chars:
            return content

        # Try to break at sentence boundaries
        truncated_text = text[:max_chars]

        # Find the last sentence boundary
        last_period = truncated_text.rfind(". ")
        last_newline = truncated_text.rfind("\n")
        break_point = max(last_period, last_newline)

        if break_point > max_chars * 0.5:  # Use sentence boundary if it's not too early
            truncated_text = text[: break_point + 1]

        # Create partial content item
        partial_content = content.copy()
        partial_content["text"] = truncated_text + "... [truncated]"
        partial_content["_partial"] = True
        partial_content["_original_length"] = len(text)

        return partial_content

    def assemble_prioritized_context(
        self, prioritized_content: list[dict[str, Any]], target_budget: int
    ) -> AssemblyResult:
        """
        Assemble prioritized context within target budget.

        Args:
            prioritized_content: Content items with priority scores
            target_budget: Target token budget

        Returns:
            AssemblyResult with assembled context and metadata
        """
        logger.info(
            f"Assembling context from {len(prioritized_content)} items "
            f"with {target_budget:,} token budget"
        )

        if not prioritized_content:
            return self._create_empty_result()

        # Calculate budget allocation
        budget_allocation = self.calculate_budget_allocation(target_budget)

        # Group content by priority level
        content_by_priority = {level.value: [] for level in PriorityLevel}

        for item in prioritized_content[: self.config["max_assembly_items"]]:
            priority_level = self._classify_content_priority(item)
            content_by_priority[priority_level.value].append(item)

        # Log priority distribution
        for level, items in content_by_priority.items():
            logger.debug(f"{level.title()} priority: {len(items)} items")

        # Assemble content for each priority level
        assembled_content = []
        tokens_by_priority = {}
        total_tokens_used = 0
        emergency_mode_used = False
        truncation_applied = False

        # Define priority order and budget mapping
        priority_budgets = [
            (PriorityLevel.CRITICAL, budget_allocation.critical_budget),
            (PriorityLevel.HIGH, budget_allocation.high_budget),
            (PriorityLevel.MEDIUM, budget_allocation.medium_budget),
            (PriorityLevel.LOW, budget_allocation.low_budget),
            (PriorityLevel.MINIMAL, budget_allocation.minimal_budget),
        ]

        for priority_level, level_budget in priority_budgets:
            level_content = content_by_priority[priority_level.value]

            if level_content and level_budget > 0:
                selected_content, tokens_used = self._assemble_priority_level(
                    level_content, level_budget, priority_level
                )

                assembled_content.extend(selected_content)
                tokens_by_priority[priority_level.value] = tokens_used
                total_tokens_used += tokens_used

                # Check for truncation
                if len(selected_content) < len(level_content):
                    truncation_applied = True
            else:
                tokens_by_priority[priority_level.value] = 0

        # Check if emergency mode needed
        budget_utilization = total_tokens_used / target_budget
        if budget_utilization > self.config["emergency_threshold"]:
            emergency_mode_used = True
            logger.warning(f"Emergency mode triggered: {budget_utilization:.1%} budget utilization")

        # Validate critical content preservation
        preserved_critical_content = any(
            item.get("is_system_message", False)
            or item.get("is_current_turn", False)
            or item.get("is_incomplete_tool_chain", False)
            for item in assembled_content
        )

        # Determine assembly strategy used
        if emergency_mode_used:
            assembly_strategy = "emergency"
        elif truncation_applied:
            assembly_strategy = "truncated"
        else:
            assembly_strategy = "standard"

        result = AssemblyResult(
            assembled_content=assembled_content,
            total_tokens_used=total_tokens_used,
            budget_utilization=budget_utilization,
            content_by_priority=content_by_priority,
            tokens_by_priority=tokens_by_priority,
            assembly_strategy=assembly_strategy,
            emergency_mode_used=emergency_mode_used,
            truncation_applied=truncation_applied,
            preserved_critical_content=preserved_critical_content,
        )

        logger.info(
            f"Context assembly complete: {len(assembled_content)} items, "
            f"{total_tokens_used:,} tokens ({budget_utilization:.1%} utilization), "
            f"strategy: {assembly_strategy}"
        )

        return result

    def create_emergency_context(
        self, content_items: list[dict[str, Any]], budget: int
    ) -> AssemblyResult:
        """
        Create minimal emergency context when budget is severely constrained.

        Args:
            content_items: Available content items
            budget: Very limited token budget

        Returns:
            AssemblyResult with emergency context
        """
        logger.warning(f"Creating emergency context with {budget} token budget")

        # Find the most critical items
        critical_items = [
            item
            for item in content_items
            if (
                item.get("is_system_message", False)
                or item.get("is_current_turn", False)
                or item.get("priority_score", 0.0) >= 0.9
            )
        ]

        if not critical_items:
            # No critical items found, try to find highest priority items
            critical_items = sorted(
                content_items, key=lambda x: x.get("priority_score", 0.0), reverse=True
            )[:3]  # Top 3 highest priority items

        # Assemble emergency content
        selected_content, tokens_used = self._assemble_priority_level(
            critical_items, budget, PriorityLevel.CRITICAL
        )

        result = AssemblyResult(
            assembled_content=selected_content,
            total_tokens_used=tokens_used,
            budget_utilization=tokens_used / budget if budget > 0 else 0.0,
            content_by_priority={"critical": critical_items},
            tokens_by_priority={"critical": tokens_used},
            assembly_strategy="emergency",
            emergency_mode_used=True,
            truncation_applied=True,
            preserved_critical_content=len(selected_content) > 0,
        )

        logger.warning(
            f"Emergency context created: {len(selected_content)} items, {tokens_used} tokens"
        )

        return result

    def _create_empty_result(self) -> AssemblyResult:
        """Create an empty assembly result."""
        return AssemblyResult(
            assembled_content=[],
            total_tokens_used=0,
            budget_utilization=0.0,
            content_by_priority={level.value: [] for level in PriorityLevel},
            tokens_by_priority={level.value: 0 for level in PriorityLevel},
            assembly_strategy="empty",
            emergency_mode_used=False,
            truncation_applied=False,
            preserved_critical_content=False,
        )

    def update_config(self, config_updates: dict[str, Any]) -> None:
        """
        Update assembler configuration.

        Args:
            config_updates: Configuration updates to apply
        """
        self.config.update(config_updates)
        logger.info(f"ContextAssembler config updated: {config_updates}")

    def get_config(self) -> dict[str, Any]:
        """
        Get current assembler configuration.

        Returns:
            Current configuration dictionary
        """
        return self.config.copy()
