"""Unit tests for ContentPrioritizer class."""

import time
from unittest.mock import patch

from agents.software_engineer.shared_libraries.content_prioritizer import ContentPrioritizer


class TestContentPrioritizer:
    """Test cases for ContentPrioritizer."""

    def test_initialization_default_config(self):
        """Test ContentPrioritizer initialization with default config."""
        prioritizer = ContentPrioritizer()
        config = prioritizer.get_config()

        # Check that all expected keys are present
        expected_keys = {
            "relevance_weight",
            "recency_weight",
            "tool_activity_weight",
            "error_priority_weight",
            "recency_decay_factor",
            "max_recency_hours",
        }
        assert expected_keys.issubset(config.keys())

        # Check weights sum approximately to 1.0 (excluding decay factors)
        weight_sum = (
            config["relevance_weight"]
            + config["recency_weight"]
            + config["tool_activity_weight"]
            + config["error_priority_weight"]
        )
        assert 0.9 <= weight_sum <= 1.1

    def test_initialization_custom_config(self):
        """Test ContentPrioritizer initialization with custom config."""
        custom_config = {
            "relevance_weight": 0.4,
            "recency_weight": 0.3,
            "tool_activity_weight": 0.2,
            "error_priority_weight": 0.1,
        }
        prioritizer = ContentPrioritizer(custom_config)
        config = prioritizer.get_config()

        assert config["relevance_weight"] == 0.4
        assert config["recency_weight"] == 0.3
        assert config["tool_activity_weight"] == 0.2
        assert config["error_priority_weight"] == 0.1

    def test_calculate_relevance_score_exact_match(self):
        """Test relevance scoring with exact word matches."""
        prioritizer = ContentPrioritizer()

        # Perfect match
        score = prioritizer.calculate_relevance_score(
            "debug the authentication function", "debug authentication"
        )
        assert score == 1.0  # Both words match

        # Partial match
        score = prioritizer.calculate_relevance_score(
            "debug the authentication function", "debug login system"
        )
        assert 0.0 < score < 1.0  # Only "debug" matches

    def test_calculate_relevance_score_phrase_bonus(self):
        """Test relevance scoring with phrase bonus for longer queries."""
        prioritizer = ContentPrioritizer()

        # Test that long query triggers phrase bonus (>10 chars)
        score_long_query = prioritizer.calculate_relevance_score(
            "Here is the exact text: test function for debugging authentication systems",
            "test function for debugging authentication",  # >10 chars, will trigger phrase bonus check  # noqa: E501
        )

        # Short query won't trigger phrase bonus
        score_short_query = prioritizer.calculate_relevance_score(
            "Here test function debugging authentication systems",
            "test debug",  # <10 chars, no phrase bonus
        )

        # Both should be valid scores between 0 and 1
        assert 0.0 <= score_long_query <= 1.0
        assert 0.0 <= score_short_query <= 1.0
        assert score_long_query > 0  # Should have some relevance

    def test_calculate_relevance_score_reference_bonus(self):
        """Test relevance scoring with file/function reference bonus."""
        prioritizer = ContentPrioritizer()

        # Query with file reference
        score_with_file = prioritizer.calculate_relevance_score(
            "Error in auth.py file on line 42", "auth.py error"
        )

        # Same query without file reference
        score_without_file = prioritizer.calculate_relevance_score(
            "Error in authentication file on line 42", "auth error"
        )

        assert score_with_file > score_without_file

    def test_calculate_relevance_score_edge_cases(self):
        """Test relevance scoring edge cases."""
        prioritizer = ContentPrioritizer()

        # Empty inputs
        assert prioritizer.calculate_relevance_score("", "test") == 0.0
        assert prioritizer.calculate_relevance_score("test", "") == 0.0
        assert prioritizer.calculate_relevance_score("", "") == 0.0

        # No word matches
        score = prioritizer.calculate_relevance_score(
            "completely different content", "unrelated query terms"
        )
        assert score == 0.0

    def test_calculate_recency_score_current_time(self):
        """Test recency scoring for current time."""
        prioritizer = ContentPrioritizer()
        current_time = time.time()

        # Message from right now should have score close to 1.0
        score = prioritizer.calculate_recency_score(current_time, current_time)
        assert score == 1.0

    def test_calculate_recency_score_exponential_decay(self):
        """Test recency scoring exponential decay."""
        prioritizer = ContentPrioritizer()
        current_time = time.time()

        # Message from 1 hour ago
        one_hour_ago = current_time - 3600
        score_1h = prioritizer.calculate_recency_score(one_hour_ago, current_time)

        # Message from 2 hours ago
        two_hours_ago = current_time - 7200
        score_2h = prioritizer.calculate_recency_score(two_hours_ago, current_time)

        # Message from 4 hours ago
        four_hours_ago = current_time - 14400
        score_4h = prioritizer.calculate_recency_score(four_hours_ago, current_time)

        # Verify exponential decay (more recent = higher score)
        assert score_1h > score_2h > score_4h
        assert 0.0 < score_4h < score_2h < score_1h < 1.0

    def test_calculate_recency_score_max_hours_cap(self):
        """Test recency scoring maximum hours cap."""
        prioritizer = ContentPrioritizer()
        current_time = time.time()

        # Message from exactly max hours ago
        max_hours = prioritizer.config["max_recency_hours"]
        max_age_time = current_time - (max_hours * 3600)
        score_max = prioritizer.calculate_recency_score(max_age_time, current_time)

        # Message from way beyond max hours ago
        very_old_time = current_time - (max_hours * 2 * 3600)  # Double the max
        score_very_old = prioritizer.calculate_recency_score(very_old_time, current_time)

        # Both should have the same score due to capping
        assert score_max == score_very_old

    def test_calculate_tool_activity_score_no_activity(self):
        """Test tool activity scoring with no activity."""
        prioritizer = ContentPrioritizer()

        content = {
            "has_function_call": False,
            "has_function_response": False,
            "tool_count": 0,
            "error_count": 0,
            "message_count": 1,
        }

        score = prioritizer.calculate_tool_activity_score(content)
        assert score == 0.0

    def test_calculate_tool_activity_score_basic_activity(self):
        """Test tool activity scoring with basic activity."""
        prioritizer = ContentPrioritizer()

        content_with_call = {
            "has_function_call": True,
            "has_function_response": False,
            "tool_count": 1,
            "error_count": 0,
            "message_count": 1,
        }

        content_with_response = {
            "has_function_call": False,
            "has_function_response": True,
            "tool_count": 1,
            "error_count": 0,
            "message_count": 1,
        }

        score_call = prioritizer.calculate_tool_activity_score(content_with_call)
        score_response = prioritizer.calculate_tool_activity_score(content_with_response)

        assert score_call > 0.0
        assert score_response > 0.0
        # Both should get same base score for having tool activity
        assert abs(score_call - score_response) < 0.1

    def test_calculate_tool_activity_score_multiple_tools(self):
        """Test tool activity scoring with multiple tools."""
        prioritizer = ContentPrioritizer()

        content_single = {
            "has_function_call": True,
            "tool_count": 1,
            "error_count": 0,
            "message_count": 1,
        }

        content_multiple = {
            "has_function_call": True,
            "tool_count": 5,
            "error_count": 0,
            "message_count": 1,
        }

        score_single = prioritizer.calculate_tool_activity_score(content_single)
        score_multiple = prioritizer.calculate_tool_activity_score(content_multiple)

        assert score_multiple > score_single

    def test_calculate_tool_activity_score_with_errors(self):
        """Test tool activity scoring with errors."""
        prioritizer = ContentPrioritizer()

        content_no_errors = {
            "has_function_call": True,
            "tool_count": 2,
            "error_count": 0,
            "message_count": 1,
        }

        content_with_errors = {
            "has_function_call": True,
            "tool_count": 2,
            "error_count": 3,
            "message_count": 1,
        }

        score_no_errors = prioritizer.calculate_tool_activity_score(content_no_errors)
        score_with_errors = prioritizer.calculate_tool_activity_score(content_with_errors)

        # Errors should reduce the score
        assert score_with_errors < score_no_errors

    def test_calculate_error_priority_score_no_errors(self):
        """Test error priority scoring with no errors."""
        prioritizer = ContentPrioritizer()

        content = {"error_indicators": []}
        score = prioritizer.calculate_error_priority_score(content)
        assert score == 0.0

    def test_calculate_error_priority_score_different_types(self):
        """Test error priority scoring with different error types."""
        prioritizer = ContentPrioritizer()

        # Test different error priorities
        test_cases = [
            (["critical"], 1.0),
            (["exception"], 0.9),
            (["error"], 0.8),
            (["failure"], 0.7),
            (["timeout"], 0.6),
            (["not_found"], 0.5),
            (["warning"], 0.3),
        ]

        for error_indicators, expected_base in test_cases:
            content = {"error_indicators": error_indicators}
            score = prioritizer.calculate_error_priority_score(content)
            assert abs(score - expected_base) < 0.1  # Allow for small variations

    def test_calculate_error_priority_score_multiple_errors(self):
        """Test error priority scoring with multiple error types."""
        prioritizer = ContentPrioritizer()

        content = {"error_indicators": ["warning", "error", "critical"]}

        score = prioritizer.calculate_error_priority_score(content)
        # Should get the maximum score (critical = 1.0)
        assert score >= 0.9

    def test_calculate_error_priority_score_recent_errors(self):
        """Test error priority scoring with recent errors boost."""
        prioritizer = ContentPrioritizer()

        content_old_error = {"error_indicators": ["error"], "has_recent_errors": False}

        content_recent_error = {"error_indicators": ["error"], "has_recent_errors": True}

        score_old = prioritizer.calculate_error_priority_score(content_old_error)
        score_recent = prioritizer.calculate_error_priority_score(content_recent_error)

        assert score_recent > score_old

    def test_calculate_composite_score_basic(self):
        """Test basic composite scoring."""
        prioritizer = ContentPrioritizer()
        current_time = time.time()

        content = {
            "text": "debug authentication function",
            "timestamp": current_time,
            "has_function_call": True,
            "tool_count": 2,
            "error_count": 0,
            "error_indicators": [],
        }

        context = {"user_query": "debug authentication"}

        score = prioritizer.calculate_composite_score(content, context)
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should have some score due to relevance and tool activity

    def test_calculate_composite_score_system_message_bonus(self):
        """Test composite scoring with system message bonus."""
        prioritizer = ContentPrioritizer()

        content_regular = {
            "text": "regular message",
            "timestamp": time.time(),
            "is_system_message": False,
        }

        content_system = {
            "text": "regular message",
            "timestamp": time.time(),
            "is_system_message": True,
        }

        context = {"user_query": "test"}

        score_regular = prioritizer.calculate_composite_score(content_regular, context)
        score_system = prioritizer.calculate_composite_score(content_system, context)

        assert score_system > score_regular

    def test_calculate_composite_score_current_turn_bonus(self):
        """Test composite scoring with current turn bonus."""
        prioritizer = ContentPrioritizer()

        content_old = {"text": "old message", "timestamp": time.time(), "is_current_turn": False}

        content_current = {"text": "old message", "timestamp": time.time(), "is_current_turn": True}

        context = {"user_query": "test"}

        score_old = prioritizer.calculate_composite_score(content_old, context)
        score_current = prioritizer.calculate_composite_score(content_current, context)

        assert score_current > score_old

    def test_prioritize_content_list(self):
        """Test content list prioritization."""
        prioritizer = ContentPrioritizer()
        current_time = time.time()

        content_list = [
            {
                "text": "low priority message",
                "timestamp": current_time - 7200,  # 2 hours ago
                "tool_count": 0,
                "error_indicators": [],
            },
            {
                "text": "high priority debug authentication",
                "timestamp": current_time - 600,  # 10 minutes ago
                "tool_count": 3,
                "has_function_call": True,
                "error_indicators": ["error"],
            },
            {
                "text": "medium priority authentication",
                "timestamp": current_time - 1800,  # 30 minutes ago
                "tool_count": 1,
                "error_indicators": [],
            },
        ]

        context = {"user_query": "debug authentication"}

        prioritized = prioritizer.prioritize_content_list(content_list, context)

        # Should be sorted by priority score (highest first)
        assert len(prioritized) == 3
        assert all("priority_score" in item for item in prioritized)

        # Verify sorting (scores should be in descending order)
        scores = [item["priority_score"] for item in prioritized]
        assert scores == sorted(scores, reverse=True)

        # High priority item should be first
        assert prioritized[0]["text"] == "high priority debug authentication"

    def test_update_config(self):
        """Test configuration updates."""
        prioritizer = ContentPrioritizer()
        original_weight = prioritizer.config["relevance_weight"]

        updates = {"relevance_weight": 0.5}
        prioritizer.update_config(updates)

        assert prioritizer.config["relevance_weight"] == 0.5
        assert prioritizer.config["relevance_weight"] != original_weight

    def test_get_config(self):
        """Test getting configuration copy."""
        prioritizer = ContentPrioritizer()
        config1 = prioritizer.get_config()
        config2 = prioritizer.get_config()

        # Should be copies, not the same object
        assert config1 is not config2
        assert config1 == config2

        # Modifying copy shouldn't affect original
        config1["relevance_weight"] = 0.99
        assert prioritizer.config["relevance_weight"] != 0.99


class TestContentPrioritizerIntegration:
    """Integration tests for ContentPrioritizer with realistic scenarios."""

    def test_realistic_conversation_prioritization(self):
        """Test prioritization with realistic conversation data."""
        prioritizer = ContentPrioritizer()
        current_time = time.time()

        # Simulate a realistic conversation with different types of content
        content_list = [
            {
                "text": "SYSTEM CONTEXT (JSON): System initialization",
                "timestamp": current_time - 3600,  # 1 hour ago
                "is_system_message": True,
                "tool_count": 0,
                "error_indicators": [],
            },
            {
                "text": "User: Please help me debug the login.py file",
                "timestamp": current_time - 10,  # 10 seconds ago
                "is_current_turn": True,
                "tool_count": 0,
                "error_indicators": [],
            },
            {
                "text": "I'll analyze the login.py file for you",
                "timestamp": current_time - 600,  # 10 minutes ago
                "has_function_call": True,
                "tool_count": 2,
                "error_indicators": [],
            },
            {
                "text": "File not found error when accessing login.py",
                "timestamp": current_time - 300,  # 5 minutes ago
                "tool_count": 1,
                "error_indicators": ["not_found", "error"],
                "has_recent_errors": True,
            },
            {
                "text": "Earlier we discussed the weather",
                "timestamp": current_time - 7200,  # 2 hours ago
                "tool_count": 0,
                "error_indicators": [],
            },
        ]

        context = {"user_query": "debug login.py file"}

        prioritized = prioritizer.prioritize_content_list(content_list, context)

        # Current turn should have high priority
        current_turn_item = next(item for item in prioritized if item.get("is_current_turn", False))
        assert prioritized.index(current_turn_item) <= 1  # Should be in top 2

        # Irrelevant old content should be deprioritized
        weather_item = next(item for item in prioritized if "weather" in item["text"])
        assert prioritized.index(weather_item) == len(prioritized) - 1  # Should be last

    @patch("time.time")
    def test_time_dependent_scoring(self, mock_time):
        """Test that scoring changes based on time progression."""
        mock_time.return_value = 1000.0  # Fixed time for testing

        prioritizer = ContentPrioritizer()

        content = {
            "text": "test message",
            "timestamp": 900.0,  # 100 seconds ago
            "tool_count": 1,
            "error_indicators": [],
        }

        context = {"user_query": "test"}

        # Score at time 1000
        score_t1 = prioritizer.calculate_composite_score(content, context)

        # Advance time
        mock_time.return_value = 2000.0  # 1000 seconds later

        # Score should be lower due to age
        score_t2 = prioritizer.calculate_composite_score(content, context)

        assert score_t2 < score_t1
