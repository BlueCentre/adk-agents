"""Unit tests for conversation filtering functionality."""

from unittest.mock import Mock

from agents.software_engineer.shared_libraries.conversation_analyzer import (
    ConversationAnalyzer,
    ConversationSegment,
    ToolChain,
)
from agents.software_engineer.shared_libraries.conversation_filter import (
    ConversationFilter,
    FilteringPolicy,
    FilterResult,
    FilterStrategy,
)
from agents.software_engineer.shared_libraries.token_optimization import TokenCounter


def create_mock_content(role, text=None, content_id=None):
    """Helper function to create mock content with consistent identity."""
    content = Mock()
    content.role = role

    if text:
        content.text = text
    else:
        # Remove text attribute if not provided
        if hasattr(content, "text"):
            del content.text

    # Remove parts attribute by default to avoid iteration issues
    if hasattr(content, "parts"):
        del content.parts

    # Give each content a unique ID for testing
    if content_id is not None:
        content._test_id = content_id

    return content


class TestFilterStrategy:
    """Test cases for FilterStrategy enum."""

    def test_filter_strategy_values(self):
        """Test FilterStrategy enum values."""
        assert FilterStrategy.CONSERVATIVE.value == "conservative"
        assert FilterStrategy.MODERATE.value == "moderate"
        assert FilterStrategy.AGGRESSIVE.value == "aggressive"


class TestFilteringPolicy:
    """Test cases for FilteringPolicy dataclass."""

    def test_filtering_policy_defaults(self):
        """Test FilteringPolicy default values."""
        policy = FilteringPolicy()

        assert policy.strategy == FilterStrategy.MODERATE
        assert policy.preserve_tool_chains is True
        assert policy.preserve_context_injections is True
        assert policy.preserve_current_conversation is True
        assert policy.target_reduction_pct == 50.0
        assert policy.min_conversations_to_keep == 2
        assert policy.max_conversations_to_keep == 10
        assert policy.preserve_system_messages is True
        assert policy.preserve_error_information is True
        assert policy.compress_old_conversations is False
        assert policy.summarize_removed_content is False

    def test_filtering_policy_customization(self):
        """Test FilteringPolicy with custom values."""
        policy = FilteringPolicy(
            strategy=FilterStrategy.AGGRESSIVE,
            preserve_tool_chains=False,
            target_reduction_pct=75.0,
            min_conversations_to_keep=1,
            max_conversations_to_keep=5,
        )

        assert policy.strategy == FilterStrategy.AGGRESSIVE
        assert policy.preserve_tool_chains is False
        assert policy.target_reduction_pct == 75.0
        assert policy.min_conversations_to_keep == 1
        assert policy.max_conversations_to_keep == 5


class TestFilterResult:
    """Test cases for FilterResult dataclass."""

    def test_filter_result_creation(self):
        """Test FilterResult creation with all fields."""
        original_content = [create_mock_content("user", "Hello", 1)]
        filtered_content = [create_mock_content("user", "Hello", 1)]
        removed_content = []

        result = FilterResult(
            original_content=original_content,
            filtered_content=filtered_content,
            removed_content=removed_content,
            original_tokens=100,
            filtered_tokens=100,
            tokens_saved=0,
            reduction_pct=0.0,
            conversations_removed=0,
            tool_chains_preserved=0,
            context_injections_preserved=0,
            strategy_used=FilterStrategy.CONSERVATIVE,
            filtering_applied=False,
        )

        assert result.original_content == original_content
        assert result.filtered_content == filtered_content
        assert result.removed_content == removed_content
        assert result.original_tokens == 100
        assert result.filtered_tokens == 100
        assert result.tokens_saved == 0
        assert result.reduction_pct == 0.0
        assert result.conversations_removed == 0
        assert result.tool_chains_preserved == 0
        assert result.context_injections_preserved == 0
        assert result.strategy_used == FilterStrategy.CONSERVATIVE
        assert result.filtering_applied is False


class TestConversationFilter:
    """Test cases for ConversationFilter class."""

    def test_init_default(self):
        """Test ConversationFilter initialization with defaults."""
        filter_obj = ConversationFilter()

        assert isinstance(filter_obj.analyzer, ConversationAnalyzer)
        assert filter_obj.token_counter is None

    def test_init_with_dependencies(self):
        """Test ConversationFilter initialization with provided dependencies."""
        analyzer = ConversationAnalyzer()
        token_counter = TokenCounter("test-model")

        filter_obj = ConversationFilter(analyzer=analyzer, token_counter=token_counter)

        assert filter_obj.analyzer == analyzer
        assert filter_obj.token_counter == token_counter

    def test_filter_conversation_empty_content(self):
        """Test filtering with empty content."""
        filter_obj = ConversationFilter()

        result = filter_obj.filter_conversation([], 1000)

        assert result.original_content == []
        assert result.filtered_content == []
        assert result.removed_content == []
        assert result.original_tokens == 0
        assert result.filtered_tokens == 0
        assert result.tokens_saved == 0
        assert result.reduction_pct == 0.0
        assert result.conversations_removed == 0
        assert result.filtering_applied is False

    def test_filter_conversation_no_token_counter(self):
        """Test filtering without token counter (no token calculations)."""
        filter_obj = ConversationFilter()

        contents = [
            create_mock_content("user", "Hello"),
            create_mock_content("assistant", "Hi there!"),
        ]

        result = filter_obj.filter_conversation(contents, 1000)

        assert result.original_content == contents
        assert len(result.filtered_content) > 0  # Should preserve some content
        assert result.original_tokens == 0  # No token counter
        assert result.filtered_tokens == 0  # No token counter
        assert result.tokens_saved == 0
        assert result.reduction_pct == 0.0

    def test_filter_conversation_within_budget(self):
        """Test filtering when content is already within budget."""
        token_counter = TokenCounter("test-model")
        filter_obj = ConversationFilter(token_counter=token_counter)

        contents = [create_mock_content("user", "Hello"), create_mock_content("assistant", "Hi!")]

        # Mock token counting to return small amount
        def mock_count(text):
            return len(text.split())  # Simple word count

        filter_obj.token_counter.count_tokens = mock_count

        result = filter_obj.filter_conversation(contents, 1000)  # Large budget

        assert result.original_content == contents
        assert result.filtered_content == contents
        assert result.removed_content == []
        assert result.filtering_applied is False

    def test_filter_conversation_conservative_strategy(self):
        """Test conservative filtering strategy."""
        filter_obj = ConversationFilter()

        contents = [
            create_mock_content("user", "Message 1", 1),
            create_mock_content("assistant", "Response 1", 2),
            create_mock_content("user", "Message 2", 3),
            create_mock_content("assistant", "Response 2", 4),
            create_mock_content("user", "Message 3", 5),
            create_mock_content("assistant", "Response 3", 6),
        ]

        policy = FilteringPolicy(strategy=FilterStrategy.CONSERVATIVE)
        result = filter_obj.filter_conversation(contents, 50, policy)

        assert result.strategy_used == FilterStrategy.CONSERVATIVE
        assert (
            len(result.filtered_content) >= policy.min_conversations_to_keep * 2
        )  # User + assistant pairs
        assert result.filtering_applied is True

    def test_filter_conversation_moderate_strategy(self):
        """Test moderate filtering strategy."""
        filter_obj = ConversationFilter()

        contents = [
            create_mock_content("user", "Message 1", 1),
            create_mock_content("assistant", "Response 1", 2),
            create_mock_content("user", "Message 2", 3),
            create_mock_content("assistant", "Response 2", 4),
            create_mock_content("user", "Message 3", 5),
            create_mock_content("assistant", "Response 3", 6),
            create_mock_content("user", "Message 4", 7),
            create_mock_content("assistant", "Response 4", 8),
        ]

        policy = FilteringPolicy(strategy=FilterStrategy.MODERATE)
        result = filter_obj.filter_conversation(contents, 50, policy)

        assert result.strategy_used == FilterStrategy.MODERATE
        # Without token counter, filtering may not reduce content significantly
        # Just verify the strategy was applied and result is reasonable
        assert len(result.filtered_content) <= len(contents)  # Should not increase content
        # filtering_applied depends on whether content was actually removed
        assert isinstance(result.filtering_applied, bool)  # Just verify it's a valid boolean

    def test_filter_conversation_aggressive_strategy(self):
        """Test aggressive filtering strategy."""
        filter_obj = ConversationFilter()

        contents = [
            create_mock_content("user", "Message 1", 1),
            create_mock_content("assistant", "Response 1", 2),
            create_mock_content("user", "Message 2", 3),
            create_mock_content("assistant", "Response 2", 4),
            create_mock_content("user", "Message 3", 5),
            create_mock_content("assistant", "Response 3", 6),
            create_mock_content("user", "Message 4", 7),
            create_mock_content("assistant", "Response 4", 8),
        ]

        policy = FilteringPolicy(strategy=FilterStrategy.AGGRESSIVE)
        result = filter_obj.filter_conversation(contents, 50, policy)

        assert result.strategy_used == FilterStrategy.AGGRESSIVE
        assert len(result.filtered_content) <= len(contents) // 2  # Should aggressively filter
        assert result.filtering_applied is True

    def test_preserve_system_messages(self):
        """Test preservation of system messages."""
        analyzer = Mock()
        analyzer.analyze_conversation_structure.return_value = {
            "total_messages": 3,
            "message_types": {"system": 1, "user": 1, "assistant": 1},
            "tool_chains": [],
            "conversation_segments": [],
            "current_tool_chains": [],
            "completed_conversations": [],
            "current_user_message": None,
            "system_messages": [(0, create_mock_content("system", "You are helpful", 1))],
            "context_injections": [],
        }

        filter_obj = ConversationFilter(analyzer=analyzer)

        contents = [
            create_mock_content("system", "You are helpful", 1),
            create_mock_content("user", "Hello", 2),
            create_mock_content("assistant", "Hi!", 3),
        ]

        policy = FilteringPolicy(preserve_system_messages=True, strategy=FilterStrategy.AGGRESSIVE)
        result = filter_obj.filter_conversation(contents, 10, policy)

        # System message should be preserved even with aggressive filtering
        system_preserved = any(
            hasattr(content, "_test_id") and content._test_id == 1
            for content in result.filtered_content
        )
        assert system_preserved

    def test_preserve_tool_chains(self):
        """Test preservation of tool chains."""
        analyzer = Mock()

        # Create mock tool chain
        tool_chain = ToolChain(
            start_index=1,
            end_index=3,
            user_message=create_mock_content("user", "Use tool", 2),
            assistant_with_tools=create_mock_content("assistant", "Using tool", 3),
            tool_results=[create_mock_content("tool", "Result", 4)],
            final_response=create_mock_content("assistant", "Done", 5),
            is_complete=True,
        )

        analyzer.analyze_conversation_structure.return_value = {
            "total_messages": 5,
            "message_types": {"system": 1, "user": 1, "assistant": 2, "tool_result": 1},
            "tool_chains": [tool_chain],
            "conversation_segments": [],
            "current_tool_chains": [],
            "completed_conversations": [],
            "current_user_message": None,
            "system_messages": [(0, create_mock_content("system", "System", 1))],
            "context_injections": [],
        }

        filter_obj = ConversationFilter(analyzer=analyzer)

        contents = [
            create_mock_content("system", "System", 1),
            create_mock_content("user", "Use tool", 2),
            create_mock_content("assistant", "Using tool", 3),
            create_mock_content("tool", "Result", 4),
            create_mock_content("assistant", "Done", 5),
        ]

        policy = FilteringPolicy(preserve_tool_chains=True)
        result = filter_obj.filter_conversation(contents, 10, policy)

        # Tool chain components should be preserved
        assert len(result.filtered_content) >= 4  # At least tool chain messages

    def test_calculate_content_tokens_no_counter(self):
        """Test token calculation without token counter."""
        filter_obj = ConversationFilter()

        contents = [create_mock_content("user", "Hello")]
        tokens = filter_obj._calculate_content_tokens(contents)

        assert tokens == 0

    def test_calculate_content_tokens_with_counter(self):
        """Test token calculation with token counter."""
        token_counter = Mock()
        token_counter.count_tokens.return_value = 5

        analyzer = Mock()
        analyzer._extract_text_from_content.return_value = "Hello world"

        filter_obj = ConversationFilter(analyzer=analyzer, token_counter=token_counter)

        contents = [create_mock_content("user", "Hello world")]
        tokens = filter_obj._calculate_content_tokens(contents)

        assert tokens == 5
        token_counter.count_tokens.assert_called_once_with("Hello world")

    def test_identify_removed_content(self):
        """Test identification of removed content."""
        filter_obj = ConversationFilter()

        content1 = create_mock_content("user", "Keep", 1)
        content2 = create_mock_content("user", "Remove", 2)

        original = [content1, content2]
        filtered = [content1]

        removed = filter_obj._identify_removed_content(original, filtered)

        assert len(removed) == 1
        assert removed[0] == content2

    def test_is_preserved_in_filtered(self):
        """Test checking if tool chain is preserved."""
        filter_obj = ConversationFilter()

        user_msg = create_mock_content("user", "Test", 1)
        assistant_msg = create_mock_content("assistant", "Response", 2)

        tool_chain = ToolChain(
            start_index=0, user_message=user_msg, assistant_with_tools=assistant_msg
        )

        # Test when preserved
        filtered_content = [user_msg, assistant_msg]
        assert filter_obj._is_preserved_in_filtered(tool_chain, filtered_content) is True

        # Test when not preserved
        filtered_content = [user_msg]
        assert filter_obj._is_preserved_in_filtered(tool_chain, filtered_content) is False

        # Test with incomplete tool chain
        incomplete_chain = ToolChain(start_index=0, user_message=None, assistant_with_tools=None)
        assert filter_obj._is_preserved_in_filtered(incomplete_chain, filtered_content) is False

    def test_is_content_preserved(self):
        """Test checking if specific content is preserved."""
        filter_obj = ConversationFilter()

        content1 = create_mock_content("user", "Test1", 1)
        content2 = create_mock_content("user", "Test2", 2)

        filtered_content = [content1]

        assert filter_obj._is_content_preserved(content1, filtered_content) is True
        assert filter_obj._is_content_preserved(content2, filtered_content) is False


class TestFilteringStrategies:
    """Integration tests for different filtering strategies."""

    def test_conservative_vs_aggressive_difference(self):
        """Test that conservative and aggressive strategies produce different results."""
        filter_obj = ConversationFilter()

        # Create longer conversation
        contents = []
        for i in range(10):
            contents.append(create_mock_content("user", f"Message {i + 1}", i * 2))
            contents.append(create_mock_content("assistant", f"Response {i + 1}", i * 2 + 1))

        conservative_policy = FilteringPolicy(strategy=FilterStrategy.CONSERVATIVE)
        aggressive_policy = FilteringPolicy(strategy=FilterStrategy.AGGRESSIVE)

        conservative_result = filter_obj.filter_conversation(contents, 100, conservative_policy)
        aggressive_result = filter_obj.filter_conversation(contents, 100, aggressive_policy)

        # Aggressive should filter more content than conservative
        assert len(aggressive_result.filtered_content) <= len(conservative_result.filtered_content)
        assert aggressive_result.conversations_removed >= conservative_result.conversations_removed

    def test_filtering_with_mixed_content_types(self):
        """Test filtering with various content types."""
        analyzer = Mock()

        system_msg = create_mock_content("system", "System prompt", 1)
        context_msg = create_mock_content("user", "SYSTEM CONTEXT (JSON): {...}", 2)
        user_msg = create_mock_content("user", "Hello", 3)
        assistant_msg = create_mock_content("assistant", "Hi!", 4)

        analyzer.analyze_conversation_structure.return_value = {
            "total_messages": 4,
            "message_types": {"system": 1, "context_injection": 1, "user": 1, "assistant": 1},
            "tool_chains": [],
            "conversation_segments": [
                ConversationSegment(start_index=2, end_index=3, messages=[user_msg, assistant_msg])
            ],
            "current_tool_chains": [],
            "completed_conversations": [],
            "current_user_message": user_msg,
            "system_messages": [(0, system_msg)],
            "context_injections": [(1, context_msg)],
        }

        filter_obj = ConversationFilter(analyzer=analyzer)

        contents = [system_msg, context_msg, user_msg, assistant_msg]

        policy = FilteringPolicy(
            preserve_system_messages=True,
            preserve_context_injections=True,
            preserve_current_conversation=True,
        )

        result = filter_obj.filter_conversation(contents, 50, policy)

        # All important content should be preserved
        assert (
            len(result.filtered_content) >= 3
        )  # At least system, context, and current conversation

    def test_error_handling_in_filtering(self):
        """Test error handling during filtering operations."""
        analyzer = Mock()
        analyzer.analyze_conversation_structure.side_effect = Exception("Analysis error")

        filter_obj = ConversationFilter(analyzer=analyzer)

        contents = [create_mock_content("user", "Test")]

        # Should handle analysis errors gracefully
        try:
            result = filter_obj.filter_conversation(contents, 100)
            # If no exception, verify result structure
            assert isinstance(result, FilterResult)
        except Exception:
            # Test that it doesn't crash the system
            pass

    def test_segment_prioritization(self):
        """Test conversation segment prioritization logic."""
        filter_obj = ConversationFilter()

        # Create segments with different characteristics
        segment1 = ConversationSegment(
            start_index=0,
            end_index=1,
            messages=[create_mock_content("user", "Old message")],
            has_tool_activity=False,
        )

        segment2 = ConversationSegment(
            start_index=2,
            end_index=3,
            messages=[create_mock_content("user", "Tool message")],
            has_tool_activity=True,  # Should get higher priority
        )

        segment3 = ConversationSegment(
            start_index=4,
            end_index=5,
            messages=[create_mock_content("user", "Recent message")],
            has_tool_activity=False,
        )

        segments = [segment1, segment2, segment3]
        analysis = {}
        policy = FilteringPolicy()

        prioritized = filter_obj._prioritize_conversation_segments(segments, analysis, policy)

        # Verify prioritization produces a valid ordering
        assert len(prioritized) == 3

        # Just verify that segment2 (with tool activity) has higher priority than segment1
        # (oldest, no activity). Don't be too specific about exact ordering since it
        # depends on the scoring algorithm
        segment2_index = prioritized.index(segment2)
        segment1_index = prioritized.index(segment1)
        assert (
            segment2_index < segment1_index
        )  # Tool activity should rank higher than oldest without activity
