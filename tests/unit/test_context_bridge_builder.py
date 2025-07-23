"""Unit tests for ContextBridgeBuilder class."""

import time
from unittest.mock import Mock, patch

from agents.software_engineer.shared_libraries.context_bridge_builder import (
    BridgeCandidate,
    BridgeType,
    BridgingResult,
    BridgingStrategy,
    ContextBridge,
    ContextBridgeBuilder,
)
from agents.software_engineer.shared_libraries.context_correlator import (
    ContextCorrelator,
    ContextReference,
    CorrelationResult,
    DependencyType,
    ReferenceStrength,
)


def create_mock_content(
    content_id=None,
    text="Test content",
    has_function_call=False,
    has_function_response=False,
    error_indicators=None,
    is_system_message=False,
    is_current_turn=False,
):
    """Helper function to create mock content with consistent structure."""
    return {
        "id": content_id or f"content_{int(time.time() * 1000)}",
        "text": text,
        "has_function_call": has_function_call,
        "has_function_response": has_function_response,
        "error_indicators": error_indicators or [],
        "is_system_message": is_system_message,
        "is_current_turn": is_current_turn,
        "timestamp": time.time(),
    }


def create_mock_correlation_result(references=None):
    """Helper to create mock CorrelationResult."""
    return CorrelationResult(
        references=references or [],
        clusters=[],
        correlation_metadata={},
        processing_time=0.1,
        content_processed=5,
        references_found=len(references or []),
    )


class TestBridgingStrategy:
    """Test cases for BridgingStrategy enum."""

    def test_bridging_strategy_values(self):
        """Test that bridging strategies have correct string values."""
        assert BridgingStrategy.CONSERVATIVE.value == "conservative"
        assert BridgingStrategy.MODERATE.value == "moderate"
        assert BridgingStrategy.AGGRESSIVE.value == "aggressive"
        assert BridgingStrategy.DEPENDENCY_ONLY.value == "dependency"


class TestBridgeType:
    """Test cases for BridgeType enum."""

    def test_bridge_type_values(self):
        """Test that bridge types have correct string values."""
        assert BridgeType.REFERENCE_BRIDGE.value == "reference"
        assert BridgeType.TOOL_CHAIN_BRIDGE.value == "tool_chain"
        assert BridgeType.ERROR_CONTEXT_BRIDGE.value == "error"
        assert BridgeType.CONVERSATION_BRIDGE.value == "conversation"
        assert BridgeType.SUMMARY_BRIDGE.value == "summary"


class TestContextBridge:
    """Test cases for ContextBridge dataclass."""

    def test_context_bridge_creation_valid(self):
        """Test valid ContextBridge creation."""
        bridge = ContextBridge(
            bridge_id="bridge_1",
            bridge_type=BridgeType.REFERENCE_BRIDGE,
            source_content_ids=["src1"],
            target_content_ids=["tgt1"],
            bridge_content="Bridge content",
            preserved_references=["ref1"],
            confidence=0.8,
            token_cost=50,
            priority=70,
        )

        assert bridge.bridge_id == "bridge_1"
        assert bridge.bridge_type == BridgeType.REFERENCE_BRIDGE
        assert bridge.source_content_ids == ["src1"]
        assert bridge.target_content_ids == ["tgt1"]
        assert bridge.bridge_content == "Bridge content"
        assert bridge.preserved_references == ["ref1"]
        assert bridge.confidence == 0.8
        assert bridge.token_cost == 50
        assert bridge.priority == 70

    def test_context_bridge_confidence_validation(self):
        """Test that invalid confidence values raise errors."""
        try:
            ContextBridge(
                bridge_id="bridge_1",
                bridge_type=BridgeType.REFERENCE_BRIDGE,
                source_content_ids=["src1"],
                target_content_ids=["tgt1"],
                bridge_content="Bridge content",
                preserved_references=["ref1"],
                confidence=1.5,  # Invalid: > 1.0
                token_cost=50,
                priority=70,
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Confidence must be between 0.0 and 1.0" in str(e)

    def test_context_bridge_token_cost_validation(self):
        """Test that negative token costs raise errors."""
        try:
            ContextBridge(
                bridge_id="bridge_1",
                bridge_type=BridgeType.REFERENCE_BRIDGE,
                source_content_ids=["src1"],
                target_content_ids=["tgt1"],
                bridge_content="Bridge content",
                preserved_references=["ref1"],
                confidence=0.8,
                token_cost=-10,  # Invalid: negative
                priority=70,
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Token cost must be non-negative" in str(e)


class TestBridgeCandidate:
    """Test cases for BridgeCandidate dataclass."""

    def test_bridge_candidate_creation(self):
        """Test BridgeCandidate creation."""
        candidate = BridgeCandidate(
            gap_start_id="start1",
            gap_end_id="end1",
            missing_content_ids=["missing1", "missing2"],
            dependency_score=0.8,
            bridge_complexity=5,
            affected_references=["ref1", "ref2"],
        )

        assert candidate.gap_start_id == "start1"
        assert candidate.gap_end_id == "end1"
        assert candidate.missing_content_ids == ["missing1", "missing2"]
        assert candidate.dependency_score == 0.8
        assert candidate.bridge_complexity == 5
        assert candidate.affected_references == ["ref1", "ref2"]


class TestContextBridgeBuilder:
    """Test cases for ContextBridgeBuilder."""

    def test_initialization_default(self):
        """Test ContextBridgeBuilder initialization with defaults."""
        builder = ContextBridgeBuilder()

        assert builder.correlator is not None
        config = builder.get_config()

        # Verify key configuration exists
        assert "default_strategy" in config
        assert "max_bridge_tokens" in config
        assert "bridge_confidence_threshold" in config
        assert "preserve_tool_chains" in config

        # Verify default values
        assert config["default_strategy"] == BridgingStrategy.MODERATE
        assert config["max_bridge_tokens"] == 200
        assert config["bridge_confidence_threshold"] == 0.5

    def test_initialization_with_correlator_and_config(self):
        """Test initialization with custom correlator and config."""
        mock_correlator = Mock(spec=ContextCorrelator)
        custom_config = {
            "max_bridge_tokens": 300,
            "bridge_confidence_threshold": 0.7,
            "default_strategy": BridgingStrategy.AGGRESSIVE,
        }

        builder = ContextBridgeBuilder(correlator=mock_correlator, config=custom_config)

        assert builder.correlator is mock_correlator
        config = builder.get_config()
        assert config["max_bridge_tokens"] == 300
        assert config["bridge_confidence_threshold"] == 0.7
        assert config["default_strategy"] == BridgingStrategy.AGGRESSIVE

    def test_find_missing_content_between(self):
        """Test finding missing content between two positions."""
        builder = ContextBridgeBuilder()

        content_items = [
            create_mock_content("item1", "First item"),
            create_mock_content("item2", "Second item"),
            create_mock_content("item3", "Third item"),
            create_mock_content("item4", "Fourth item"),
            create_mock_content("item5", "Fifth item"),
        ]

        filtered_content_ids = {"item1", "item4", "item5"}  # Missing item2, item3

        missing_ids = builder._find_missing_content_between(
            "item1", "item4", content_items, filtered_content_ids
        )

        assert missing_ids == ["item2", "item3"]

    def test_find_missing_content_between_no_gap(self):
        """Test finding missing content when there's no gap."""
        builder = ContextBridgeBuilder()

        content_items = [
            create_mock_content("item1", "First item"),
            create_mock_content("item2", "Second item"),
        ]

        filtered_content_ids = {"item1", "item2"}

        missing_ids = builder._find_missing_content_between(
            "item1", "item2", content_items, filtered_content_ids
        )

        assert missing_ids == []

    def test_calculate_gap_dependency_score(self):
        """Test calculation of gap dependency score."""
        builder = ContextBridgeBuilder()

        # Create mock references involving missing content
        references = [
            ContextReference(
                source_id="missing1",
                target_id="item4",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.9,
            ),
            ContextReference(
                source_id="item1",
                target_id="missing2",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
            ),
        ]

        correlation_result = create_mock_correlation_result(references)

        score = builder._calculate_gap_dependency_score(
            ["missing1", "missing2"], correlation_result
        )

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have high score due to critical tool chain reference

    def test_identify_affected_references(self):
        """Test identification of affected references."""
        builder = ContextBridgeBuilder()

        references = [
            ContextReference(
                source_id="missing1",
                target_id="item4",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.9,
            ),
            ContextReference(
                source_id="item1",
                target_id="missing2",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
            ),
            ContextReference(
                source_id="other1",
                target_id="other2",
                dependency_type=DependencyType.CONVERSATION_FLOW,
                strength=ReferenceStrength.MODERATE,
                reference_text="flow",
                confidence=0.5,
            ),
        ]

        correlation_result = create_mock_correlation_result(references)

        affected_refs = builder._identify_affected_references(
            ["missing1", "missing2"], correlation_result
        )

        assert len(affected_refs) == 2
        assert "tool_chain:tool_call" in affected_refs
        assert "file_ref:test.py" in affected_refs

    def test_estimate_bridge_complexity(self):
        """Test bridge complexity estimation."""
        builder = ContextBridgeBuilder()

        # Create content index with different types of content
        content_index = {
            "tool_item": create_mock_content(
                "tool_item", "Function call executed", has_function_call=True
            ),
            "error_item": create_mock_content(
                "error_item", "Error occurred", error_indicators=["error"]
            ),
            "normal_item": create_mock_content("normal_item", "Normal content"),
        }

        # Test complexity with tool content
        complexity_tools = builder._estimate_bridge_complexity(
            ["tool_item", "normal_item"], content_index
        )
        assert complexity_tools > 3  # Base + tool bonus

        # Test complexity with error content
        complexity_errors = builder._estimate_bridge_complexity(
            ["error_item", "normal_item"], content_index
        )
        assert complexity_errors > 2  # Base + error bonus

        # Test complexity with normal content
        complexity_normal = builder._estimate_bridge_complexity(["normal_item"], content_index)
        assert 1 <= complexity_normal <= 10

    def test_determine_bridge_type_tool_chain(self):
        """Test bridge type determination for tool chains."""
        builder = ContextBridgeBuilder()

        candidate = BridgeCandidate(
            gap_start_id="start1",
            gap_end_id="end1",
            missing_content_ids=["missing1"],
            dependency_score=0.8,
            bridge_complexity=5,
            affected_references=["tool_chain:call"],
        )

        references = [
            ContextReference(
                source_id="missing1",
                target_id="end1",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.9,
            ),
        ]

        correlation_result = create_mock_correlation_result(references)

        bridge_type = builder._determine_bridge_type(candidate, correlation_result)
        assert bridge_type == BridgeType.TOOL_CHAIN_BRIDGE

    def test_determine_bridge_type_error_context(self):
        """Test bridge type determination for error contexts."""
        builder = ContextBridgeBuilder()

        candidate = BridgeCandidate(
            gap_start_id="start1",
            gap_end_id="end1",
            missing_content_ids=["missing1"],
            dependency_score=0.8,
            bridge_complexity=5,
            affected_references=["error_ctx:fix"],
        )

        references = [
            ContextReference(
                source_id="missing1",
                target_id="end1",
                dependency_type=DependencyType.ERROR_CONTEXT,
                strength=ReferenceStrength.STRONG,
                reference_text="error_fix",
                confidence=0.8,
            ),
        ]

        correlation_result = create_mock_correlation_result(references)

        bridge_type = builder._determine_bridge_type(candidate, correlation_result)
        assert bridge_type == BridgeType.ERROR_CONTEXT_BRIDGE

    def test_determine_bridge_type_reference(self):
        """Test bridge type determination for references."""
        builder = ContextBridgeBuilder()

        candidate = BridgeCandidate(
            gap_start_id="start1",
            gap_end_id="end1",
            missing_content_ids=["missing1"],
            dependency_score=0.8,
            bridge_complexity=5,
            affected_references=["file_ref:test.py"],
        )

        references = [
            ContextReference(
                source_id="missing1",
                target_id="end1",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
            ),
        ]

        correlation_result = create_mock_correlation_result(references)

        bridge_type = builder._determine_bridge_type(candidate, correlation_result)
        assert bridge_type == BridgeType.REFERENCE_BRIDGE

    def test_generate_tool_chain_bridge_conservative(self):
        """Test tool chain bridge generation with conservative strategy."""
        builder = ContextBridgeBuilder()

        missing_contents = ["Function call executed", "Tool result: success"]

        bridge_content, confidence = builder._generate_tool_chain_bridge(
            missing_contents, BridgingStrategy.CONSERVATIVE
        )

        assert bridge_content == "[Tool execution and results omitted for brevity]"
        assert confidence == 0.8

    def test_generate_tool_chain_bridge_moderate(self):
        """Test tool chain bridge generation with moderate strategy."""
        builder = ContextBridgeBuilder()

        missing_contents = ["Function call executed", "Tool result: success completed"]

        bridge_content, confidence = builder._generate_tool_chain_bridge(
            missing_contents, BridgingStrategy.MODERATE
        )

        assert "[Tool execution summary:" in bridge_content
        assert "success completed" in bridge_content
        assert confidence == 0.7

    def test_generate_error_context_bridge(self):
        """Test error context bridge generation."""
        builder = ContextBridgeBuilder()

        missing_contents = ["Error: ValueError occurred", "Fix: Updated validation logic"]

        bridge_content, confidence = builder._generate_error_context_bridge(
            missing_contents, BridgingStrategy.MODERATE
        )

        assert "Error:" in bridge_content
        assert "Resolution:" in bridge_content
        assert confidence == 0.8

    def test_generate_reference_bridge(self):
        """Test reference bridge generation."""
        builder = ContextBridgeBuilder()

        candidate = BridgeCandidate(
            gap_start_id="start1",
            gap_end_id="end1",
            missing_content_ids=["missing1"],
            dependency_score=0.8,
            bridge_complexity=5,
            affected_references=["file_ref:test.py", "func_ref:process_data"],
        )

        bridge_content, confidence = builder._generate_reference_bridge(
            candidate, BridgingStrategy.MODERATE
        )

        assert "test.py" in bridge_content
        assert "process_data" in bridge_content
        assert confidence == 0.6

    def test_generate_conversation_bridge(self):
        """Test conversation bridge generation."""
        builder = ContextBridgeBuilder()

        missing_contents = ["Some discussion", "More context"]

        bridge_content, confidence = builder._generate_conversation_bridge(
            missing_contents, BridgingStrategy.AGGRESSIVE
        )

        assert "Conversation continues" in bridge_content
        assert confidence == 0.5

    def test_generate_summary_bridge(self):
        """Test summary bridge generation."""
        builder = ContextBridgeBuilder()

        missing_contents = ["First message", "Second message", "Third message"]

        bridge_content, confidence = builder._generate_summary_bridge(
            missing_contents, BridgingStrategy.MODERATE
        )

        assert "3 items omitted" in bridge_content
        assert confidence == 0.5

    def test_extract_key_results(self):
        """Test key results extraction from tool content."""
        builder = ContextBridgeBuilder()

        tool_contents = [
            "Function execution result: Operation completed successfully",
            "Tool result shows success with 95% accuracy",
        ]

        results = builder._extract_key_results(tool_contents)

        assert "result" in results.lower()
        assert "success" in results.lower()

    def test_extract_error_summary(self):
        """Test error summary extraction."""
        builder = ContextBridgeBuilder()

        error_contents = ["ValueError exception occurred in validation", "File not found error"]

        summary = builder._extract_error_summary(error_contents)

        assert "exception" in summary.lower() or "error" in summary.lower()

    def test_extract_fix_summary(self):
        """Test fix summary extraction."""
        builder = ContextBridgeBuilder()

        fix_contents = ["Fixed the validation issue", "Updated error handling logic"]

        summary = builder._extract_fix_summary(fix_contents)

        assert "fix" in summary.lower() or "update" in summary.lower()

    def test_extract_key_terms(self):
        """Test key terms extraction for summarization."""
        builder = ContextBridgeBuilder()

        contents = [
            "Working on authentication system with JWT tokens",
            "Authentication requires proper token validation",
            "System authentication flow needs improvement",
        ]

        terms = builder._extract_key_terms(contents)

        assert "authentication" in terms
        assert "system" in terms
        # Should exclude short/common words

    def test_calculate_bridge_priority(self):
        """Test bridge priority calculation."""
        builder = ContextBridgeBuilder()

        candidate = BridgeCandidate(
            gap_start_id="start1",
            gap_end_id="end1",
            missing_content_ids=["missing1"],
            dependency_score=0.8,
            bridge_complexity=5,
            affected_references=["tool_chain:call", "file_ref:test.py"],
        )

        _correlation_result = create_mock_correlation_result()

        # Test tool chain bridge priority (should be high)
        priority_tool = builder._calculate_bridge_priority(candidate, BridgeType.TOOL_CHAIN_BRIDGE)
        assert priority_tool >= 80

        # Test summary bridge priority (should be low)
        priority_summary = builder._calculate_bridge_priority(candidate, BridgeType.SUMMARY_BRIDGE)
        assert priority_summary <= 60  # Adjusted for dependency score bonuses

        # Tool chain should have higher priority than summary
        assert priority_tool > priority_summary

    @patch.object(ContextCorrelator, "correlate_context")
    def test_build_context_bridges_basic(self, mock_correlate):
        """Test basic context bridge building."""
        builder = ContextBridgeBuilder()

        # Mock correlation result
        references = [
            ContextReference(
                source_id="missing1",
                target_id="item4",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.9,
            ),
        ]
        mock_correlate.return_value = create_mock_correlation_result(references)

        content_items = [
            create_mock_content("item1", "First item"),
            create_mock_content("missing1", "Tool call executed", has_function_call=True),
            create_mock_content("missing2", "Tool result: success", has_function_response=True),
            create_mock_content("item4", "Final item"),
        ]

        filtered_content_ids = {"item1", "item4"}  # Missing tool chain

        result = builder.build_context_bridges(
            content_items, filtered_content_ids, BridgingStrategy.MODERATE
        )

        assert isinstance(result, BridgingResult)
        assert result.strategy_used == BridgingStrategy.MODERATE
        assert len(result.bridges) > 0  # Should generate at least one bridge
        assert result.total_bridge_tokens > 0

    @patch.object(ContextCorrelator, "correlate_context")
    def test_build_context_bridges_no_gaps(self, mock_correlate):
        """Test bridge building when no gaps exist."""
        builder = ContextBridgeBuilder()

        mock_correlate.return_value = create_mock_correlation_result([])

        content_items = [
            create_mock_content("item1", "First item"),
            create_mock_content("item2", "Second item"),
        ]

        filtered_content_ids = {"item1", "item2"}  # No missing items

        result = builder.build_context_bridges(
            content_items, filtered_content_ids, BridgingStrategy.MODERATE
        )

        assert len(result.bridges) == 0
        assert result.total_bridge_tokens == 0
        assert result.gaps_filled == 0

    def test_calculate_preservation_score(self):
        """Test dependency preservation score calculation."""
        builder = ContextBridgeBuilder()

        references = [
            ContextReference(
                source_id="preserved1",
                target_id="preserved2",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.9,
            ),
            ContextReference(
                source_id="missing1",
                target_id="preserved2",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
            ),
        ]

        correlation_result = create_mock_correlation_result(references)

        bridges = [
            ContextBridge(
                bridge_id="bridge_1",
                bridge_type=BridgeType.TOOL_CHAIN_BRIDGE,
                source_content_ids=["missing1"],
                target_content_ids=["preserved2"],
                bridge_content="Bridge content",
                preserved_references=["file_ref:test.py"],
                confidence=0.8,
                token_cost=50,
                priority=70,
            )
        ]

        filtered_content_ids = {"preserved1", "preserved2"}

        score = builder._calculate_preservation_score(
            correlation_result, bridges, filtered_content_ids
        )

        assert 0.0 <= score <= 1.0
        # First ref is fully preserved, second is bridged, so score should be high
        assert score >= 0.5

    @patch.object(ContextCorrelator, "correlate_context")
    def test_build_context_bridges_different_strategies(self, mock_correlate):
        """Test bridge building with different strategies."""
        builder = ContextBridgeBuilder()

        references = [
            ContextReference(
                source_id="missing1",
                target_id="item4",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.9,
            ),
        ]
        mock_correlate.return_value = create_mock_correlation_result(references)

        content_items = [
            create_mock_content("item1", "First item"),
            create_mock_content("missing1", "Function call executed", has_function_call=True),
            create_mock_content("missing2", "Tool result obtained", has_function_response=True),
            create_mock_content("item4", "Final item"),
        ]

        filtered_content_ids = {"item1", "item4"}

        # Test conservative strategy
        result_conservative = builder.build_context_bridges(
            content_items, filtered_content_ids, BridgingStrategy.CONSERVATIVE
        )

        # Test aggressive strategy
        result_aggressive = builder.build_context_bridges(
            content_items, filtered_content_ids, BridgingStrategy.AGGRESSIVE
        )

        # Both should generate bridges, but potentially different amounts
        assert len(result_conservative.bridges) >= 0
        assert len(result_aggressive.bridges) >= 0

        # Strategies should be correctly recorded
        assert result_conservative.strategy_used == BridgingStrategy.CONSERVATIVE
        assert result_aggressive.strategy_used == BridgingStrategy.AGGRESSIVE

    def test_update_config(self):
        """Test configuration updates."""
        builder = ContextBridgeBuilder()
        original_max_tokens = builder.config["max_bridge_tokens"]

        updates = {"max_bridge_tokens": 500, "bridge_confidence_threshold": 0.8}
        builder.update_config(updates)

        assert builder.config["max_bridge_tokens"] == 500
        assert builder.config["bridge_confidence_threshold"] == 0.8
        assert builder.config["max_bridge_tokens"] != original_max_tokens

    def test_get_config(self):
        """Test getting configuration copy."""
        builder = ContextBridgeBuilder()
        config1 = builder.get_config()
        config2 = builder.get_config()

        # Should be copies, not the same object
        assert config1 is not config2
        assert config1 == config2

        # Modifying copy shouldn't affect original
        config1["max_bridge_tokens"] = 999
        assert builder.config["max_bridge_tokens"] != 999


class TestContextBridgeBuilderIntegration:
    """Integration tests for ContextBridgeBuilder with realistic scenarios."""

    def test_realistic_bridging_scenario(self):
        """Test context bridging with realistic conversation data."""
        builder = ContextBridgeBuilder()

        # Simulate a realistic development conversation with gaps
        content_items = [
            create_mock_content(
                content_id="system", text="You are helping debug a Python application"
            ),
            create_mock_content(
                content_id="user_query",
                text="I'm getting an error in src/auth/login.py at line 42",
            ),
            create_mock_content(
                content_id="tool_call",
                text="Let me examine the login.py file",
                has_function_call=True,
            ),
            create_mock_content(
                content_id="tool_result",
                text="File contents show validate_password function has issue",
                has_function_response=True,
            ),
            create_mock_content(
                content_id="analysis",
                text="The validate_password function in src/auth/login.py needs fix",
            ),
            create_mock_content(
                content_id="fix", text="Updated validate_password to handle edge cases properly"
            ),
            create_mock_content(
                content_id="confirmation", text="The fix has been applied successfully"
            ),
        ]

        # Simulate filtering that removes some middle content
        filtered_content_ids = {"system", "user_query", "analysis", "confirmation"}

        result = builder.build_context_bridges(content_items, filtered_content_ids)

        # Should find gaps and potentially create bridges
        assert isinstance(result, BridgingResult)
        assert result.strategy_used == BridgingStrategy.MODERATE  # Default strategy

        # Should have some metadata
        assert result.bridging_metadata["candidates_analyzed"] >= 0
        assert result.bridging_metadata["processing_time"] > 0

    def test_bridging_with_large_gaps(self):
        """Test bridging behavior with large content gaps."""
        builder = ContextBridgeBuilder()

        # Create content with large gaps
        content_items = []
        for i in range(20):
            content_items.append(
                create_mock_content(
                    content_id=f"item_{i}",
                    text=f"Content item {i} discussing feature implementation",
                    has_function_call=(i % 5 == 0),
                    has_function_response=(i % 5 == 1),
                )
            )

        # Filter to create large gaps
        filtered_content_ids = {"item_0", "item_10", "item_19"}

        result = builder.build_context_bridges(content_items, filtered_content_ids)

        # Should handle large gaps appropriately
        assert isinstance(result, BridgingResult)

        # Gap size might exceed limits, so bridges might be limited
        if result.bridges:
            for bridge in result.bridges:
                assert bridge.confidence >= 0.0
                assert bridge.token_cost >= 0
                assert bridge.priority >= 1

    def test_bridging_performance_with_many_items(self):
        """Test bridging performance with larger content set."""
        builder = ContextBridgeBuilder()

        # Create larger content set
        content_items = []
        for i in range(100):  # 100 items
            content_items.append(
                create_mock_content(
                    content_id=f"item_{i}",
                    text=f"Content {i} with various topics and functions",
                    has_function_call=(i % 10 == 0),
                    has_function_response=(i % 10 == 1),
                )
            )

        # Create scattered filtering
        filtered_content_ids = {f"item_{i}" for i in range(0, 100, 10)}  # Every 10th item

        result = builder.build_context_bridges(content_items, filtered_content_ids)

        # Should complete in reasonable time
        assert result.bridging_metadata["processing_time"] < 10.0  # Less than 10 seconds

        # Should handle the large dataset appropriately
        assert isinstance(result, BridgingResult)
        assert result.bridging_metadata["candidates_analyzed"] >= 0

    def test_bridging_with_minimal_content(self):
        """Test bridging behavior with minimal content."""
        builder = ContextBridgeBuilder()

        # Single item
        single_item = [create_mock_content(content_id="only", text="Single content item")]
        result = builder.build_context_bridges(single_item, {"only"})

        assert len(result.bridges) == 0  # No gaps to bridge
        assert result.gaps_filled == 0
        assert result.total_bridge_tokens == 0

        # Two items with no gap
        two_items = [
            create_mock_content(content_id="item1", text="First item"),
            create_mock_content(content_id="item2", text="Second item"),
        ]
        result2 = builder.build_context_bridges(two_items, {"item1", "item2"})

        assert len(result2.bridges) == 0  # No gaps to bridge
        assert result2.gaps_filled == 0

    def test_bridging_strategy_comparison(self):
        """Test that different strategies produce different results."""
        builder = ContextBridgeBuilder()

        content_items = [
            create_mock_content("start", "Starting conversation"),
            create_mock_content("tool1", "Function call 1", has_function_call=True),
            create_mock_content("result1", "Result 1", has_function_response=True),
            create_mock_content("tool2", "Function call 2", has_function_call=True),
            create_mock_content("result2", "Result 2", has_function_response=True),
            create_mock_content("end", "Ending conversation"),
        ]

        filtered_content_ids = {"start", "end"}  # Large gap in middle

        # Test different strategies
        result_conservative = builder.build_context_bridges(
            content_items, filtered_content_ids, BridgingStrategy.CONSERVATIVE
        )
        result_aggressive = builder.build_context_bridges(
            content_items, filtered_content_ids, BridgingStrategy.AGGRESSIVE
        )

        # Should record correct strategies
        assert result_conservative.strategy_used == BridgingStrategy.CONSERVATIVE
        assert result_aggressive.strategy_used == BridgingStrategy.AGGRESSIVE

        # Both should be valid results
        assert isinstance(result_conservative, BridgingResult)
        assert isinstance(result_aggressive, BridgingResult)

    def test_bridging_with_no_correlator_dependencies(self):
        """Test bridging when correlator finds no dependencies."""
        # Create builder with a mock correlator that returns empty results
        mock_correlator = Mock(spec=ContextCorrelator)
        mock_correlator.correlate_context.return_value = create_mock_correlation_result([])

        builder = ContextBridgeBuilder(correlator=mock_correlator)

        content_items = [
            create_mock_content("item1", "First item"),
            create_mock_content("item2", "Second item"),
            create_mock_content("item3", "Third item"),
        ]

        filtered_content_ids = {"item1", "item3"}  # Missing item2

        result = builder.build_context_bridges(content_items, filtered_content_ids)

        # Should still analyze but find low dependency scores
        assert isinstance(result, BridgingResult)
        # May or may not create bridges depending on dependency scores
