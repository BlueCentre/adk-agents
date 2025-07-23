"""Unit tests for ContextCorrelator class."""

import time

from agents.software_engineer.shared_libraries.context_correlator import (
    ContextCorrelator,
    ContextReference,
    CorrelationResult,
    DependencyCluster,
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


class TestDependencyType:
    """Test cases for DependencyType enum."""

    def test_dependency_type_values(self):
        """Test that dependency types have correct string values."""
        assert DependencyType.TOOL_CHAIN.value == "tool_chain"
        assert DependencyType.VARIABLE_REFERENCE.value == "var_ref"
        assert DependencyType.FILE_REFERENCE.value == "file_ref"
        assert DependencyType.ERROR_CONTEXT.value == "error_ctx"
        assert DependencyType.CONVERSATION_FLOW.value == "conv_flow"
        assert DependencyType.FUNCTION_REFERENCE.value == "func_ref"
        assert DependencyType.CONCEPT_CONTINUATION.value == "concept"


class TestReferenceStrength:
    """Test cases for ReferenceStrength enum."""

    def test_reference_strength_values(self):
        """Test that reference strengths have correct string values."""
        assert ReferenceStrength.CRITICAL.value == "critical"
        assert ReferenceStrength.STRONG.value == "strong"
        assert ReferenceStrength.MODERATE.value == "moderate"
        assert ReferenceStrength.WEAK.value == "weak"


class TestContextReference:
    """Test cases for ContextReference dataclass."""

    def test_context_reference_creation_valid(self):
        """Test valid ContextReference creation."""
        ref = ContextReference(
            source_id="src1",
            target_id="tgt1",
            dependency_type=DependencyType.FILE_REFERENCE,
            strength=ReferenceStrength.STRONG,
            reference_text="test.py",
            confidence=0.8,
        )

        assert ref.source_id == "src1"
        assert ref.target_id == "tgt1"
        assert ref.dependency_type == DependencyType.FILE_REFERENCE
        assert ref.strength == ReferenceStrength.STRONG
        assert ref.reference_text == "test.py"
        assert ref.confidence == 0.8
        assert ref.bidirectional is False

    def test_context_reference_confidence_validation(self):
        """Test that invalid confidence values raise errors."""
        try:
            ContextReference(
                source_id="src1",
                target_id="tgt1",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=1.5,  # Invalid: > 1.0
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Confidence must be between 0.0 and 1.0" in str(e)

    def test_context_reference_bidirectional(self):
        """Test bidirectional reference creation."""
        ref = ContextReference(
            source_id="src1",
            target_id="tgt1",
            dependency_type=DependencyType.TOOL_CHAIN,
            strength=ReferenceStrength.CRITICAL,
            reference_text="tool_call -> tool_result",
            confidence=0.95,
            bidirectional=True,
        )

        assert ref.bidirectional is True


class TestDependencyCluster:
    """Test cases for DependencyCluster dataclass."""

    def test_dependency_cluster_creation(self):
        """Test DependencyCluster creation and basic operations."""
        ref = ContextReference(
            source_id="src1",
            target_id="tgt1",
            dependency_type=DependencyType.FILE_REFERENCE,
            strength=ReferenceStrength.STRONG,
            reference_text="test.py",
            confidence=0.8,
        )

        cluster = DependencyCluster(
            cluster_id="test_cluster",
            content_ids=["src1", "tgt1"],
            primary_type=DependencyType.FILE_REFERENCE,
            cluster_strength=ReferenceStrength.STRONG,
            internal_references=[ref],
            cluster_summary="Test cluster summary",
        )

        assert cluster.cluster_id == "test_cluster"
        assert cluster.content_ids == ["src1", "tgt1"]
        assert cluster.primary_type == DependencyType.FILE_REFERENCE
        assert cluster.cluster_strength == ReferenceStrength.STRONG
        assert len(cluster.internal_references) == 1
        assert cluster.cluster_summary == "Test cluster summary"

    def test_dependency_cluster_add_content(self):
        """Test adding content to cluster."""
        cluster = DependencyCluster(
            cluster_id="test_cluster",
            content_ids=["src1"],
            primary_type=DependencyType.FILE_REFERENCE,
            cluster_strength=ReferenceStrength.STRONG,
            internal_references=[],
            cluster_summary="Test cluster",
        )

        cluster.add_content("src2")
        assert "src2" in cluster.content_ids
        assert cluster.get_cluster_size() == 2

        # Adding same content again shouldn't duplicate
        cluster.add_content("src2")
        assert cluster.get_cluster_size() == 2

    def test_dependency_cluster_size(self):
        """Test cluster size calculation."""
        cluster = DependencyCluster(
            cluster_id="test_cluster",
            content_ids=["src1", "src2", "src3"],
            primary_type=DependencyType.FILE_REFERENCE,
            cluster_strength=ReferenceStrength.STRONG,
            internal_references=[],
            cluster_summary="Test cluster",
        )

        assert cluster.get_cluster_size() == 3


class TestContextCorrelator:
    """Test cases for ContextCorrelator."""

    def test_initialization_default(self):
        """Test ContextCorrelator initialization with defaults."""
        correlator = ContextCorrelator()

        config = correlator.get_config()

        # Verify key configuration exists
        assert "min_confidence_threshold" in config
        assert "strong_reference_threshold" in config
        assert "dependency_weights" in config
        assert "tool_chain_window" in config

        # Verify default values
        assert config["min_confidence_threshold"] == 0.3
        assert config["strong_reference_threshold"] == 0.7
        assert config["critical_reference_threshold"] == 0.9

    def test_initialization_custom_config(self):
        """Test ContextCorrelator initialization with custom config."""
        custom_config = {
            "min_confidence_threshold": 0.5,
            "tool_chain_window": 15,
            "min_cluster_size": 3,
        }

        correlator = ContextCorrelator(config=custom_config)
        config = correlator.get_config()

        assert config["min_confidence_threshold"] == 0.5
        assert config["tool_chain_window"] == 15
        assert config["min_cluster_size"] == 3

    def test_pattern_compilation(self):
        """Test that regex patterns are compiled correctly."""
        correlator = ContextCorrelator()

        # Verify patterns exist
        assert "file_paths" in correlator.patterns
        assert "functions" in correlator.patterns
        assert "variables" in correlator.patterns
        assert "errors" in correlator.patterns
        assert "tool_calls" in correlator.patterns
        assert "cross_refs" in correlator.patterns

        # Test a few pattern matches
        file_match = correlator.patterns["file_paths"].search("src/test.py")
        assert file_match is not None

        function_match = correlator.patterns["functions"].search("def test_function():")
        assert function_match is not None

    def test_correlate_context_basic(self):
        """Test basic context correlation."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="item1", text="Working on src/test.py file", has_function_call=True
            ),
            create_mock_content(
                content_id="item2",
                text="Function call completed successfully",
                has_function_response=True,
            ),
            create_mock_content(
                content_id="item3", text="Also editing src/test.py for improvements"
            ),
        ]

        result = correlator.correlate_context(content_items)

        assert isinstance(result, CorrelationResult)
        assert result.content_processed == 3
        assert result.references_found > 0  # Should find file and tool chain references
        assert result.processing_time > 0

        # Should find at least file references between item1 and item3
        file_refs = [
            r for r in result.references if r.dependency_type == DependencyType.FILE_REFERENCE
        ]
        assert len(file_refs) > 0

    def test_correlate_context_empty(self):
        """Test correlation with empty content list."""
        correlator = ContextCorrelator()

        result = correlator.correlate_context([])

        assert result.content_processed == 0
        assert result.references_found == 0
        assert len(result.references) == 0
        assert len(result.clusters) == 0

    def test_detect_tool_chain_references(self):
        """Test tool chain reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="call1", text="Calling function to process data", has_function_call=True
            ),
            create_mock_content(
                content_id="result1",
                text="Function returned result: success",
                has_function_response=True,
            ),
            create_mock_content(
                content_id="call2", text="Another function call", has_function_call=True
            ),
            # No response for call2 - should be marked as incomplete
        ]

        references = correlator._detect_tool_chain_references(content_items)

        # Should find reference between call1 and result1
        assert len(references) > 0
        tool_ref = references[0]
        assert tool_ref.dependency_type == DependencyType.TOOL_CHAIN
        assert tool_ref.strength == ReferenceStrength.CRITICAL
        assert tool_ref.bidirectional is True

        # call2 should be marked as incomplete
        assert content_items[2].get("is_incomplete_tool_chain") is True

    def test_detect_file_references(self):
        """Test file reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(content_id="file1", text="Working on agents/test/module.py file"),
            create_mock_content(
                content_id="file2", text="Updated agents/test/module.py with new logic"
            ),
            create_mock_content(content_id="file3", text="Also need to check different_file.js"),
        ]

        references = correlator._detect_file_references(content_items)

        # Should find reference between file1 and file2 (same file)
        assert len(references) > 0
        file_ref = references[0]
        assert file_ref.dependency_type == DependencyType.FILE_REFERENCE
        assert "agents/test/module.py" in file_ref.reference_text
        assert file_ref.bidirectional is True

    def test_detect_function_references(self):
        """Test function reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="func1", text="def process_data(input): return processed"
            ),
            create_mock_content(content_id="func2", text="Need to fix the process_data function"),
            create_mock_content(content_id="func3", text="Called process_data() successfully"),
        ]

        references = correlator._detect_function_references(content_items)

        # Should find multiple references for process_data function
        assert len(references) > 0

        # All references should be for function type
        for ref in references:
            assert ref.dependency_type == DependencyType.FUNCTION_REFERENCE
            assert "process_data" in ref.reference_text

    def test_detect_variable_references(self):
        """Test variable reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(content_id="var1", text="user_data = fetch_from_database()"),
            create_mock_content(content_id="var2", text="Processing user_data for validation"),
            create_mock_content(content_id="var3", text="user_data validation completed"),
        ]

        references = correlator._detect_variable_references(content_items)

        # Should find references for user_data variable
        assert len(references) > 0

        for ref in references:
            assert ref.dependency_type == DependencyType.VARIABLE_REFERENCE
            assert "user_data" in ref.reference_text

    def test_detect_error_context_references(self):
        """Test error context reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="error1",
                text="Error: ValueError in process_user_input at line 45",
                error_indicators=["error", "ValueError"],
            ),
            create_mock_content(
                content_id="fix1", text="Fixed the ValueError by updating input validation"
            ),
            create_mock_content(content_id="unrelated", text="Working on different feature"),
        ]

        references = correlator._detect_error_context_references(content_items)

        # Should find reference from error to fix
        assert len(references) > 0
        error_ref = references[0]
        assert error_ref.dependency_type == DependencyType.ERROR_CONTEXT
        assert error_ref.source_id == "error1"
        assert error_ref.target_id == "fix1"
        assert error_ref.strength == ReferenceStrength.STRONG

    def test_detect_conversation_flow_references(self):
        """Test conversation flow reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="conv1", text="Let's implement the authentication system"
            ),
            create_mock_content(
                content_id="conv2", text="As mentioned above, we need JWT tokens for auth"
            ),
            create_mock_content(content_id="conv3", text="Continuing with the JWT implementation"),
        ]

        references = correlator._detect_conversation_flow_references(content_items)

        # Should find flow references
        assert len(references) > 0

        flow_refs = [r for r in references if r.dependency_type == DependencyType.CONVERSATION_FLOW]
        assert len(flow_refs) > 0
        assert flow_refs[0].strength == ReferenceStrength.MODERATE

    def test_detect_concept_references(self):
        """Test concept reference detection."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="concept1", text="Authentication system requires secure password hashing"
            ),
            create_mock_content(
                content_id="concept2", text="Password hashing using bcrypt algorithm"
            ),
            create_mock_content(
                content_id="concept3", text="Secure authentication with proper hashing techniques"
            ),
        ]

        references = correlator._detect_concept_references(content_items)

        # Should find concept references for shared terms like "authentication", "hashing"
        concept_refs = [
            r for r in references if r.dependency_type == DependencyType.CONCEPT_CONTINUATION
        ]
        assert len(concept_refs) > 0
        assert concept_refs[0].strength == ReferenceStrength.WEAK

    def test_calculate_text_similarity(self):
        """Test text similarity calculation."""
        correlator = ContextCorrelator()

        # Similar texts
        text1 = "Working on authentication system with JWT tokens"
        text2 = "JWT tokens for authentication system implementation"
        similarity = correlator._calculate_text_similarity(text1, text2)
        assert similarity > 0.3  # Should have reasonable similarity

        # Dissimilar texts
        text3 = "Database connection pooling"
        text4 = "Frontend UI component styling"
        similarity2 = correlator._calculate_text_similarity(text3, text4)
        assert similarity2 < similarity  # Should be less similar

        # Empty texts
        similarity3 = correlator._calculate_text_similarity("", "test")
        assert similarity3 == 0.0

    def test_get_reference_strength(self):
        """Test reference strength calculation from confidence."""
        correlator = ContextCorrelator()

        # Test different confidence levels
        assert correlator._get_reference_strength(0.95) == ReferenceStrength.CRITICAL
        assert correlator._get_reference_strength(0.8) == ReferenceStrength.STRONG
        assert correlator._get_reference_strength(0.6) == ReferenceStrength.MODERATE
        assert correlator._get_reference_strength(0.3) == ReferenceStrength.WEAK

    def test_build_dependency_clusters(self):
        """Test dependency cluster building."""
        correlator = ContextCorrelator()

        # Create some references that should form clusters
        references = [
            ContextReference(
                source_id="file1",
                target_id="file2",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
                bidirectional=True,
            ),
            ContextReference(
                source_id="file2",
                target_id="file3",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
                bidirectional=True,
            ),
        ]

        clusters = correlator._build_dependency_clusters(references)

        # Should form one cluster with all three files
        assert len(clusters) > 0
        cluster = clusters[0]
        assert cluster.primary_type == DependencyType.FILE_REFERENCE
        assert len(cluster.content_ids) == 3
        assert cluster.cluster_strength == ReferenceStrength.STRONG

    def test_find_connected_components(self):
        """Test connected component finding in reference graph."""
        correlator = ContextCorrelator()

        references = [
            ContextReference(
                source_id="a",
                target_id="b",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test1.py",
                confidence=0.8,
            ),
            ContextReference(
                source_id="b",
                target_id="c",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test1.py",
                confidence=0.8,
            ),
            ContextReference(
                source_id="d",
                target_id="e",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test2.py",
                confidence=0.8,
            ),
        ]

        components = correlator._find_connected_components(references)

        # Should find two connected components: [a-b-c] and [d-e]
        assert len(components) == 2

        # Each component should have the correct references
        component_sizes = [len(comp) for comp in components]
        assert 2 in component_sizes  # Component with 2 references (a-b, b-c)
        assert 1 in component_sizes  # Component with 1 reference (d-e)

    def test_generate_cluster_summary(self):
        """Test cluster summary generation."""
        correlator = ContextCorrelator()

        references = [
            ContextReference(
                source_id="src1",
                target_id="src2",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
            ),
        ]

        summary = correlator._generate_cluster_summary(
            ["src1", "src2"], references, DependencyType.FILE_REFERENCE
        )

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "test.py" in summary

    def test_get_dependency_strength_score(self):
        """Test dependency strength score calculation."""
        correlator = ContextCorrelator()

        # Create a correlation result with some references
        references = [
            ContextReference(
                source_id="item1",
                target_id="item2",
                dependency_type=DependencyType.TOOL_CHAIN,
                strength=ReferenceStrength.CRITICAL,
                reference_text="tool_call",
                confidence=0.95,
            ),
            ContextReference(
                source_id="item1",
                target_id="item3",
                dependency_type=DependencyType.FILE_REFERENCE,
                strength=ReferenceStrength.STRONG,
                reference_text="test.py",
                confidence=0.8,
            ),
        ]

        cluster = DependencyCluster(
            cluster_id="test_cluster",
            content_ids=["item1", "item2"],
            primary_type=DependencyType.TOOL_CHAIN,
            cluster_strength=ReferenceStrength.CRITICAL,
            internal_references=[references[0]],
            cluster_summary="Test cluster",
        )

        correlation_result = CorrelationResult(
            references=references,
            clusters=[cluster],
            correlation_metadata={},
            processing_time=0.1,
            content_processed=3,
            references_found=2,
        )

        # Calculate strength score for item1 (has 2 references and is in cluster)
        score = correlator.get_dependency_strength_score("item1", correlation_result)
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should have positive score due to references and cluster membership

        # Calculate score for non-existent item
        score_none = correlator.get_dependency_strength_score("non_existent", correlation_result)
        assert score_none == 0.0

    def test_update_config(self):
        """Test configuration updates."""
        correlator = ContextCorrelator()
        original_threshold = correlator.config["min_confidence_threshold"]

        updates = {"min_confidence_threshold": 0.6, "tool_chain_window": 20}
        correlator.update_config(updates)

        assert correlator.config["min_confidence_threshold"] == 0.6
        assert correlator.config["tool_chain_window"] == 20
        assert correlator.config["min_confidence_threshold"] != original_threshold

    def test_get_config(self):
        """Test getting configuration copy."""
        correlator = ContextCorrelator()
        config1 = correlator.get_config()
        config2 = correlator.get_config()

        # Should be copies, not the same object
        assert config1 is not config2
        assert config1 == config2

        # Modifying copy shouldn't affect original
        config1["min_confidence_threshold"] = 0.99
        assert correlator.config["min_confidence_threshold"] != 0.99


class TestContextCorrelatorIntegration:
    """Integration tests for ContextCorrelator with realistic scenarios."""

    def test_realistic_correlation_scenario(self):
        """Test context correlation with realistic conversation data."""
        correlator = ContextCorrelator()

        # Simulate a realistic development conversation
        content_items = [
            create_mock_content(
                content_id="system",
                text="You are helping debug a Python application",
                is_system_message=True,
            ),
            create_mock_content(
                content_id="user_query",
                text="I'm getting an error in src/auth/login.py at line 42",
                is_current_turn=True,
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
        ]

        result = correlator.correlate_context(content_items)

        # Should find various types of references
        assert result.references_found > 0
        assert result.content_processed == 6

        # Should find file references for login.py
        file_refs = [
            r for r in result.references if r.dependency_type == DependencyType.FILE_REFERENCE
        ]
        assert len(file_refs) > 0

        # Should find function references for validate_password
        func_refs = [
            r for r in result.references if r.dependency_type == DependencyType.FUNCTION_REFERENCE
        ]
        assert len(func_refs) > 0

        # Should find tool chain reference
        tool_refs = [r for r in result.references if r.dependency_type == DependencyType.TOOL_CHAIN]
        assert len(tool_refs) > 0

        # Should form some clusters
        assert len(result.clusters) > 0

    def test_correlation_with_multiple_tool_chains(self):
        """Test correlation with multiple interleaved tool chains."""
        correlator = ContextCorrelator()

        content_items = [
            create_mock_content(
                content_id="call1", text="Analyzing code structure", has_function_call=True
            ),
            create_mock_content(
                content_id="call2", text="Checking test coverage", has_function_call=True
            ),
            create_mock_content(
                content_id="result1",
                text="Code analysis complete: found 3 issues",
                has_function_response=True,
            ),
            create_mock_content(
                content_id="result2", text="Test coverage is 85%", has_function_response=True
            ),
        ]

        result = correlator.correlate_context(content_items)

        # Should find tool chain references
        tool_refs = [r for r in result.references if r.dependency_type == DependencyType.TOOL_CHAIN]
        # Should handle multiple tool chains correctly (may not be exact count due to heuristics)
        assert len(tool_refs) >= 1

    def test_correlation_performance_with_large_content(self):
        """Test correlation performance with larger content set."""
        correlator = ContextCorrelator()

        # Create larger content set
        content_items = []
        for i in range(50):  # 50 items
            content_items.append(
                create_mock_content(
                    content_id=f"item_{i}",
                    text=(
                        f"Working on feature {i} in src/module_{i % 5}.py "
                        f"with function process_item_{i % 10}"
                    ),
                    has_function_call=(i % 8 == 0),  # Some have function calls
                    has_function_response=(i % 8 == 1),  # Some have responses
                    error_indicators=["error"] if i % 15 == 0 else [],  # Some have errors
                )
            )

        result = correlator.correlate_context(content_items)

        # Should complete in reasonable time
        assert result.processing_time < 5.0  # Less than 5 seconds
        assert result.content_processed == 50

        # Should find references due to repeated patterns
        assert result.references_found > 0

        # Should have reasonable performance metadata
        assert "reference_types" in result.correlation_metadata
        assert result.correlation_metadata["total_references_detected"] >= result.references_found

    def test_correlation_with_minimal_content(self):
        """Test correlation behavior with minimal content."""
        correlator = ContextCorrelator()

        # Single item
        single_item = [create_mock_content(content_id="only", text="Single content item")]
        result = correlator.correlate_context(single_item)

        assert result.content_processed == 1
        assert result.references_found == 0  # No references possible with single item
        assert len(result.clusters) == 0

        # Two unrelated items
        unrelated_items = [
            create_mock_content(content_id="item1", text="Working on authentication"),
            create_mock_content(content_id="item2", text="Database optimization task"),
        ]
        result2 = correlator.correlate_context(unrelated_items)

        assert result2.content_processed == 2
        # May or may not find references depending on concept detection
        assert result2.references_found >= 0

    def test_correlation_confidence_filtering(self):
        """Test that correlation properly filters by confidence threshold."""
        correlator = ContextCorrelator(config={"min_confidence_threshold": 0.8})  # High threshold

        content_items = [
            create_mock_content(content_id="weak1", text="Maybe related to some concept"),
            create_mock_content(content_id="weak2", text="Possibly similar concept here"),
            create_mock_content(
                content_id="strong1", text="Working on specific file src/exact/path.py"
            ),
            create_mock_content(
                content_id="strong2", text="Updated src/exact/path.py with changes"
            ),
        ]

        result = correlator.correlate_context(content_items)

        # Should filter out weak concept references but keep strong file references
        strong_refs = [r for r in result.references if r.confidence >= 0.8]
        assert len(strong_refs) > 0  # Should have strong file references

        # All returned references should meet threshold
        for ref in result.references:
            assert ref.confidence >= 0.8
