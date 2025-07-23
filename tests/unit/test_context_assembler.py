"""Unit tests for ContextAssembler class."""

import time
from unittest.mock import Mock

from agents.software_engineer.shared_libraries.context_assembler import (
    AssemblyResult,
    BudgetAllocation,
    ContextAssembler,
    PriorityLevel,
)
from agents.software_engineer.shared_libraries.token_optimization import TokenCounter


def create_mock_content(
    text="Test content",
    priority_score=0.5,
    is_system_message=False,
    is_current_turn=False,
    is_incomplete_tool_chain=False,
    error_indicators=None,
    has_recent_errors=False,
    tool_count=0,
    content_id=None,
):
    """Helper function to create mock content with consistent structure."""
    content = {
        "text": text,
        "priority_score": priority_score,
        "is_system_message": is_system_message,
        "is_current_turn": is_current_turn,
        "is_incomplete_tool_chain": is_incomplete_tool_chain,
        "error_indicators": error_indicators or [],
        "has_recent_errors": has_recent_errors,
        "tool_count": tool_count,
        "timestamp": time.time(),
    }

    if content_id is not None:
        content["_test_id"] = content_id

    return content


class TestPriorityLevel:
    """Test cases for PriorityLevel enum."""

    def test_priority_level_values(self):
        """Test that priority levels have correct string values."""
        assert PriorityLevel.CRITICAL.value == "critical"
        assert PriorityLevel.HIGH.value == "high"
        assert PriorityLevel.MEDIUM.value == "medium"
        assert PriorityLevel.LOW.value == "low"
        assert PriorityLevel.MINIMAL.value == "minimal"


class TestBudgetAllocation:
    """Test cases for BudgetAllocation dataclass."""

    def test_budget_allocation_valid(self):
        """Test valid budget allocation creation."""
        allocation = BudgetAllocation(
            total_budget=10000,
            critical_budget=2500,
            high_budget=2500,
            medium_budget=2000,
            low_budget=1500,
            minimal_budget=500,
            reserved_emergency=1000,
        )

        assert allocation.total_budget == 10000
        assert allocation.critical_budget == 2500
        assert allocation.high_budget == 2500
        # Sum should equal total
        total_allocated = (
            allocation.critical_budget
            + allocation.high_budget
            + allocation.medium_budget
            + allocation.low_budget
            + allocation.minimal_budget
            + allocation.reserved_emergency
        )
        assert total_allocated == allocation.total_budget

    def test_budget_allocation_invalid(self):
        """Test that invalid budget allocation raises error."""
        try:
            BudgetAllocation(
                total_budget=1000,
                critical_budget=500,
                high_budget=600,  # This makes the total exceed budget
                medium_budget=250,
                low_budget=150,
                minimal_budget=50,
                reserved_emergency=100,
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "exceeds total" in str(e)


class TestContextAssembler:
    """Test cases for ContextAssembler."""

    def test_initialization_default(self):
        """Test ContextAssembler initialization with defaults."""
        assembler = ContextAssembler()

        assert assembler.token_counter is None
        config = assembler.get_config()

        # Verify key configuration exists
        assert "critical_budget_pct" in config
        assert "high_budget_pct" in config
        assert "emergency_reserve_pct" in config
        assert "min_critical_tokens" in config

        # Verify budget percentages sum to reasonable total
        total_pct = (
            config["critical_budget_pct"]
            + config["high_budget_pct"]
            + config["medium_budget_pct"]
            + config["low_budget_pct"]
            + config["minimal_budget_pct"]
        )
        assert 0.9 <= total_pct <= 1.1  # Should be approximately 100%

    def test_initialization_with_token_counter(self):
        """Test ContextAssembler initialization with TokenCounter."""
        token_counter = Mock(spec=TokenCounter)
        assembler = ContextAssembler(token_counter=token_counter)

        assert assembler.token_counter is token_counter

    def test_initialization_with_custom_config(self):
        """Test ContextAssembler initialization with custom config."""
        custom_config = {
            "critical_budget_pct": 0.4,
            "emergency_reserve_pct": 0.2,
            "min_critical_tokens": 1000,
        }

        assembler = ContextAssembler(config=custom_config)
        config = assembler.get_config()

        assert config["critical_budget_pct"] == 0.4
        assert config["emergency_reserve_pct"] == 0.2
        assert config["min_critical_tokens"] == 1000

    def test_calculate_budget_allocation_normal(self):
        """Test budget allocation calculation for normal case."""
        assembler = ContextAssembler()
        allocation = assembler.calculate_budget_allocation(10000)

        assert isinstance(allocation, BudgetAllocation)
        assert allocation.total_budget == 10000
        assert allocation.critical_budget > 0
        assert allocation.high_budget > 0
        assert allocation.medium_budget > 0
        assert allocation.low_budget > 0
        assert allocation.minimal_budget > 0
        assert allocation.reserved_emergency > 0

        # Total allocation should not exceed budget
        total_allocated = (
            allocation.critical_budget
            + allocation.high_budget
            + allocation.medium_budget
            + allocation.low_budget
            + allocation.minimal_budget
            + allocation.reserved_emergency
        )
        assert total_allocated <= allocation.total_budget

    def test_calculate_budget_allocation_with_min_critical(self):
        """Test budget allocation when minimum critical tokens is enforced."""
        custom_config = {"min_critical_tokens": 8000}  # Very high minimum
        assembler = ContextAssembler(config=custom_config)

        allocation = assembler.calculate_budget_allocation(10000)

        # Critical budget should meet minimum requirement
        assert allocation.critical_budget >= 8000

        # Other budgets should be reduced proportionally
        assert allocation.high_budget > 0  # Should still have some allocation
        assert allocation.medium_budget > 0

        # Total should still be within bounds
        total_allocated = (
            allocation.critical_budget
            + allocation.high_budget
            + allocation.medium_budget
            + allocation.low_budget
            + allocation.minimal_budget
            + allocation.reserved_emergency
        )
        assert total_allocated <= allocation.total_budget

    def test_classify_content_priority_critical(self):
        """Test classification of critical priority content."""
        assembler = ContextAssembler()

        # System message
        content = create_mock_content(is_system_message=True)
        assert assembler._classify_content_priority(content) == PriorityLevel.CRITICAL

        # Current turn
        content = create_mock_content(is_current_turn=True)
        assert assembler._classify_content_priority(content) == PriorityLevel.CRITICAL

        # Incomplete tool chain
        content = create_mock_content(is_incomplete_tool_chain=True)
        assert assembler._classify_content_priority(content) == PriorityLevel.CRITICAL

        # Very high priority score
        content = create_mock_content(priority_score=0.95)
        assert assembler._classify_content_priority(content) == PriorityLevel.CRITICAL

    def test_classify_content_priority_high(self):
        """Test classification of high priority content."""
        assembler = ContextAssembler()

        # Content with errors
        content = create_mock_content(error_indicators=["error", "exception"])
        assert assembler._classify_content_priority(content) == PriorityLevel.HIGH

        # Recent errors
        content = create_mock_content(has_recent_errors=True)
        assert assembler._classify_content_priority(content) == PriorityLevel.HIGH

        # Tool activity with high score
        content = create_mock_content(tool_count=3, priority_score=0.75)
        assert assembler._classify_content_priority(content) == PriorityLevel.HIGH

    def test_classify_content_priority_medium(self):
        """Test classification of medium priority content."""
        assembler = ContextAssembler()

        # Content with some tool activity
        content = create_mock_content(tool_count=1, priority_score=0.4)
        assert assembler._classify_content_priority(content) == PriorityLevel.MEDIUM

        # Content with medium score
        content = create_mock_content(priority_score=0.6)
        assert assembler._classify_content_priority(content) == PriorityLevel.MEDIUM

    def test_classify_content_priority_low(self):
        """Test classification of low priority content."""
        assembler = ContextAssembler()

        content = create_mock_content(priority_score=0.3)
        assert assembler._classify_content_priority(content) == PriorityLevel.LOW

    def test_classify_content_priority_minimal(self):
        """Test classification of minimal priority content."""
        assembler = ContextAssembler()

        content = create_mock_content(priority_score=0.1)
        assert assembler._classify_content_priority(content) == PriorityLevel.MINIMAL

    def test_calculate_content_tokens_with_counter(self):
        """Test token calculation with TokenCounter."""
        mock_counter = Mock()
        mock_counter.count_tokens.return_value = 50

        assembler = ContextAssembler(token_counter=mock_counter)
        content = create_mock_content(text="Test content")

        tokens = assembler._calculate_content_tokens(content)

        assert tokens == 50
        mock_counter.count_tokens.assert_called_once_with("Test content")

    def test_calculate_content_tokens_without_counter(self):
        """Test token calculation without TokenCounter (fallback)."""
        assembler = ContextAssembler()  # No token counter
        content = create_mock_content(text="This is test content")

        tokens = assembler._calculate_content_tokens(content)

        # Should use character count / 4 as fallback
        expected = len("This is test content") // 4
        assert tokens == expected

    def test_assemble_priority_level_basic(self):
        """Test basic priority level assembly."""
        assembler = ContextAssembler()

        content_items = [
            create_mock_content(text="High priority", priority_score=0.8, content_id=1),
            create_mock_content(text="Medium priority", priority_score=0.6, content_id=2),
            create_mock_content(text="Low priority", priority_score=0.3, content_id=3),
        ]

        budget = 200  # Enough for multiple items
        selected_content, tokens_used = assembler._assemble_priority_level(
            content_items, budget, PriorityLevel.HIGH
        )

        # Should select content in priority order
        assert len(selected_content) > 0
        assert tokens_used > 0
        assert tokens_used <= budget

        # Highest priority should be first
        assert selected_content[0]["_test_id"] == 1

    def test_assemble_priority_level_budget_constraint(self):
        """Test priority level assembly with tight budget constraints."""
        assembler = ContextAssembler()

        content_items = [
            create_mock_content(text="A" * 400, priority_score=0.8, content_id=1),  # ~100 tokens
            create_mock_content(text="B" * 400, priority_score=0.7, content_id=2),  # ~100 tokens
            create_mock_content(text="C" * 400, priority_score=0.6, content_id=3),  # ~100 tokens
        ]

        budget = 150  # Only enough for ~1.5 items
        selected_content, tokens_used = assembler._assemble_priority_level(
            content_items, budget, PriorityLevel.HIGH
        )

        # Should respect budget constraint
        assert tokens_used <= budget

        # Should select highest priority items that fit
        assert len(selected_content) >= 1
        assert selected_content[0]["_test_id"] == 1

    def test_assemble_priority_level_empty_inputs(self):
        """Test priority level assembly with empty inputs."""
        assembler = ContextAssembler()

        # Empty content list
        selected_content, tokens_used = assembler._assemble_priority_level(
            [], 1000, PriorityLevel.HIGH
        )
        assert selected_content == []
        assert tokens_used == 0

        # Zero budget
        content_items = [create_mock_content(text="Test", content_id=1)]
        selected_content, tokens_used = assembler._assemble_priority_level(
            content_items, 0, PriorityLevel.HIGH
        )
        assert selected_content == []
        assert tokens_used == 0

    def test_try_partial_inclusion_allowed(self):
        """Test partial inclusion decision for allowed content."""
        assembler = ContextAssembler()

        # Large content that's not system/current turn
        content = create_mock_content(
            text="A" * 1000,  # Large content
            is_system_message=False,
            is_current_turn=False,
        )

        # Small budget, content is much larger
        should_include = assembler._try_partial_inclusion(content, 100)
        assert should_include is True

    def test_try_partial_inclusion_not_allowed(self):
        """Test partial inclusion decision for protected content."""
        assembler = ContextAssembler()

        # System message should not be partially included
        content = create_mock_content(text="A" * 1000, is_system_message=True)

        should_include = assembler._try_partial_inclusion(content, 100)
        assert should_include is False

        # Current turn should not be partially included
        content = create_mock_content(text="A" * 1000, is_current_turn=True)

        should_include = assembler._try_partial_inclusion(content, 100)
        assert should_include is False

    def test_create_partial_content(self):
        """Test partial content creation."""
        assembler = ContextAssembler()

        original_text = "This is a long piece of content that should be truncated. " * 10
        content = create_mock_content(text=original_text)

        partial_content = assembler._create_partial_content(content, 50)  # 50 tokens ~ 200 chars

        assert partial_content is not None
        assert partial_content["_partial"] is True
        assert partial_content["_original_length"] == len(original_text)
        assert "... [truncated]" in partial_content["text"]
        assert len(partial_content["text"]) < len(original_text)

    def test_create_partial_content_small_content(self):
        """Test partial content creation when content already fits."""
        assembler = ContextAssembler()

        original_text = "Short content"
        content = create_mock_content(text=original_text)

        partial_content = assembler._create_partial_content(content, 100)  # Large budget

        # Should return original content unchanged
        assert partial_content == content

    def test_create_partial_content_empty_text(self):
        """Test partial content creation with empty text."""
        assembler = ContextAssembler()

        content = create_mock_content(text="")
        partial_content = assembler._create_partial_content(content, 50)

        assert partial_content is None

    def test_assemble_prioritized_context_basic(self):
        """Test basic prioritized context assembly."""
        assembler = ContextAssembler()

        prioritized_content = [
            create_mock_content(
                text="Critical system message", is_system_message=True, content_id=1
            ),
            create_mock_content(
                text="High priority error",
                error_indicators=["error"],
                priority_score=0.8,
                content_id=2,
            ),
            create_mock_content(
                text="Medium priority content", tool_count=1, priority_score=0.6, content_id=3
            ),
            create_mock_content(text="Low priority content", priority_score=0.3, content_id=4),
        ]

        result = assembler.assemble_prioritized_context(prioritized_content, 2000)

        assert isinstance(result, AssemblyResult)
        assert len(result.assembled_content) > 0
        assert result.total_tokens_used > 0
        assert result.total_tokens_used <= 2000
        assert 0.0 <= result.budget_utilization <= 1.0
        assert result.preserved_critical_content is True  # Should preserve system message
        assert result.assembly_strategy in ["standard", "truncated", "emergency"]

    def test_assemble_prioritized_context_empty(self):
        """Test assembly with empty content list."""
        assembler = ContextAssembler()

        result = assembler.assemble_prioritized_context([], 1000)

        assert isinstance(result, AssemblyResult)
        assert result.assembled_content == []
        assert result.total_tokens_used == 0
        assert result.budget_utilization == 0.0
        assert result.assembly_strategy == "empty"
        assert result.preserved_critical_content is False

    def test_assemble_prioritized_context_tight_budget(self):
        """Test assembly with very tight budget."""
        assembler = ContextAssembler()

        prioritized_content = [
            create_mock_content(text="A" * 400, is_system_message=True, content_id=1),
            create_mock_content(text="B" * 400, error_indicators=["error"], content_id=2),
            create_mock_content(text="C" * 400, tool_count=1, content_id=3),
        ]

        result = assembler.assemble_prioritized_context(prioritized_content, 200)  # Tight budget

        assert result.total_tokens_used <= 200
        # With very tight budget, may not be able to include much content
        assert 0.0 <= result.budget_utilization <= 1.0
        assert result.truncation_applied is True  # Should have truncated content
        # Critical content may not be preserved if budget is too tight
        assert isinstance(result.preserved_critical_content, bool)

    def test_create_emergency_context(self):
        """Test emergency context creation."""
        assembler = ContextAssembler()

        content_items = [
            create_mock_content(text="System", is_system_message=True, content_id=1),
            create_mock_content(text="Current", is_current_turn=True, content_id=2),
            create_mock_content(text="High priority", priority_score=0.95, content_id=3),
            create_mock_content(text="Low priority", priority_score=0.1, content_id=4),
        ]

        result = assembler.create_emergency_context(content_items, 100)

        assert isinstance(result, AssemblyResult)
        assert result.emergency_mode_used is True
        assert result.assembly_strategy == "emergency"
        assert result.total_tokens_used <= 100

        # Should prioritize critical items
        assembled_ids = {item.get("_test_id") for item in result.assembled_content}
        assert (
            1 in assembled_ids or 2 in assembled_ids or 3 in assembled_ids
        )  # At least one critical item

    def test_create_emergency_context_no_critical_items(self):
        """Test emergency context when no critical items are available."""
        assembler = ContextAssembler()

        content_items = [
            create_mock_content(text="Medium", priority_score=0.6, content_id=1),
            create_mock_content(text="Low", priority_score=0.3, content_id=2),
            create_mock_content(text="Minimal", priority_score=0.1, content_id=3),
        ]

        result = assembler.create_emergency_context(content_items, 100)

        assert result.emergency_mode_used is True
        assert len(result.assembled_content) <= 3  # Should take top 3 items

        # Should take highest priority items available
        if result.assembled_content:
            first_item = result.assembled_content[0]
            assert first_item["_test_id"] == 1  # Highest priority item

    def test_update_config(self):
        """Test configuration updates."""
        assembler = ContextAssembler()
        original_critical_pct = assembler.config["critical_budget_pct"]

        updates = {"critical_budget_pct": 0.5, "emergency_threshold": 0.95}
        assembler.update_config(updates)

        assert assembler.config["critical_budget_pct"] == 0.5
        assert assembler.config["emergency_threshold"] == 0.95
        assert assembler.config["critical_budget_pct"] != original_critical_pct

    def test_get_config(self):
        """Test getting configuration copy."""
        assembler = ContextAssembler()
        config1 = assembler.get_config()
        config2 = assembler.get_config()

        # Should be copies, not the same object
        assert config1 is not config2
        assert config1 == config2

        # Modifying copy shouldn't affect original
        config1["critical_budget_pct"] = 0.99
        assert assembler.config["critical_budget_pct"] != 0.99


class TestContextAssemblerIntegration:
    """Integration tests for ContextAssembler with realistic scenarios."""

    def test_realistic_conversation_assembly(self):
        """Test context assembly with realistic conversation data."""
        assembler = ContextAssembler()

        # Simulate a realistic conversation scenario
        prioritized_content = [
            # System context
            create_mock_content(
                text="SYSTEM CONTEXT: You are a helpful programming assistant.",
                is_system_message=True,
                priority_score=1.0,
                content_id=1,
            ),
            # Current user query
            create_mock_content(
                text="User: Please help me debug this Python function.",
                is_current_turn=True,
                priority_score=0.95,
                content_id=2,
            ),
            # Recent error with tool activity
            create_mock_content(
                text="Error: NameError in function process_data() at line 15.",
                error_indicators=["error", "name_error"],
                has_recent_errors=True,
                tool_count=2,
                priority_score=0.85,
                content_id=3,
            ),
            # Tool result with medium priority
            create_mock_content(
                text="Function analysis shows undefined variable 'result'.",
                tool_count=1,
                priority_score=0.7,
                content_id=4,
            ),
            # Older conversation
            create_mock_content(
                text="Earlier we discussed best practices for error handling.",
                priority_score=0.4,
                content_id=5,
            ),
            # Irrelevant old content
            create_mock_content(
                text="Yesterday we talked about weather API integration.",
                priority_score=0.1,
                content_id=6,
            ),
        ]

        result = assembler.assemble_prioritized_context(prioritized_content, 5000)

        # Verify critical content is preserved
        assert result.preserved_critical_content is True

        # Verify system message and current turn are included
        assembled_ids = {item.get("_test_id") for item in result.assembled_content}
        assert 1 in assembled_ids  # System message
        assert 2 in assembled_ids  # Current turn

        # Error content should be prioritized
        assert 3 in assembled_ids  # Recent error

        # Should use reasonable amount of budget (text is short, so low utilization expected)
        assert 0.0 <= result.budget_utilization <= 1.0

        # Strategy should be appropriate
        assert result.assembly_strategy in ["standard", "truncated"]

    def test_progressive_budget_pressure(self):
        """Test behavior under increasing budget pressure."""
        assembler = ContextAssembler()

        # Create substantial content
        content_items = []
        for i in range(20):
            is_system = i == 0
            is_current = i == 1
            error_indicators = ["error"] if i < 6 and i > 1 else []

            content = create_mock_content(
                text=f"Content item {i} with substantial text content " * 5,
                is_system_message=is_system,
                is_current_turn=is_current,
                error_indicators=error_indicators,
                priority_score=1.0 - (i * 0.05),  # Decreasing priority
                content_id=i,
            )
            content_items.append(content)

        # Test with different budget levels
        budgets = [10000, 5000, 2000, 1000, 500]  # Decreasing budgets

        for budget in budgets:
            result = assembler.assemble_prioritized_context(content_items, budget)

            # Should always respect budget
            assert result.total_tokens_used <= budget

            # Should preserve critical content when budget allows
            if budget >= 1000:  # Reasonable minimum budget for critical content
                assert result.preserved_critical_content is True

            # Higher budget pressure should lead to more truncation
            if budget <= 1000:
                assert result.truncation_applied is True

    def test_assembly_with_token_counter_integration(self):
        """Test assembly with actual TokenCounter integration."""
        # Mock TokenCounter for predictable testing
        mock_counter = Mock()
        mock_counter.count_tokens.side_effect = lambda text: len(text) // 3  # Predictable count

        assembler = ContextAssembler(token_counter=mock_counter)

        content_items = [
            create_mock_content(
                text="A" * 300, is_system_message=True, content_id=1
            ),  # ~100 tokens
            create_mock_content(text="B" * 150, is_current_turn=True, content_id=2),  # ~50 tokens
            create_mock_content(
                text="C" * 600, error_indicators=["error"], content_id=3
            ),  # ~200 tokens
        ]

        result = assembler.assemble_prioritized_context(content_items, 300)

        # Should use TokenCounter for accurate counting
        assert mock_counter.count_tokens.call_count > 0

        # Should respect budget based on actual token counts
        assert result.total_tokens_used <= 300

        # Critical content should be included (at least one)
        assembled_ids = {item.get("_test_id") for item in result.assembled_content}
        # Should include at least one critical item (system message or current turn)
        critical_items_included = (1 in assembled_ids) or (2 in assembled_ids)
        assert critical_items_included, (
            f"No critical content included. Assembled IDs: {assembled_ids}"
        )
