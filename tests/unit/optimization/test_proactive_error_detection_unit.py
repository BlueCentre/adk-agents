from datetime import datetime, timedelta

import pytest

from agents.software_engineer.shared_libraries.proactive_error_detection import (
    ProactiveErrorDetector,
)


class TestProactiveErrorDetectorUnit:
    """Unit tests for the ProactiveErrorDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a ProactiveErrorDetector instance."""
        return ProactiveErrorDetector()

    @pytest.fixture
    def sample_session_state_with_errors(self):
        """Create sample session state with recent errors."""
        current_time = datetime.now()
        return {
            "recent_errors": [
                {
                    "command": "cat nonexistent.txt",
                    "error_type": "file_not_found",
                    "details": "No such file or directory: nonexistent.txt",
                    "stderr": "cat: nonexistent.txt: No such file or directory",
                    "timestamp": (current_time - timedelta(minutes=2)).isoformat(),
                },
                {
                    "command": "python missing_module.py",
                    "error_type": "python_import_error",
                    "details": "ModuleNotFoundError: No module named 'requests'",
                    "stderr": "ModuleNotFoundError: No module named 'requests'",
                    "timestamp": (current_time - timedelta(minutes=1)).isoformat(),
                },
                {
                    "command": "chmod 777 /root/secret",
                    "error_type": "permission_denied",
                    "details": "Permission denied",
                    "stderr": "chmod: changing permissions of '/root/secret': Permission denied",
                    "timestamp": (current_time - timedelta(minutes=3)).isoformat(),
                },
            ]
        }

    def test_analyze_recent_errors_with_valid_errors(
        self, detector, sample_session_state_with_errors
    ):
        """Test analyzing recent errors returns suggestions."""
        analysis = detector.analyze_recent_errors(sample_session_state_with_errors)

        assert analysis is not None
        assert analysis["has_proactive_suggestions"] is True
        assert analysis["error_count"] >= 2  # Should find recent errors within 5 minutes
        assert len(analysis["suggestions"]) <= 3  # Limited to top 3
        assert "generated_at" in analysis

    def test_analyze_recent_errors_no_errors(self, detector):
        """Test analyzing when no errors exist."""
        session_state = {"recent_errors": []}
        analysis = detector.analyze_recent_errors(session_state)

        assert analysis is None

    def test_analyze_recent_errors_old_errors_only(self, detector):
        """Test analyzing when only old errors exist (older than 5 minutes)."""
        old_time = datetime.now() - timedelta(minutes=10)
        session_state = {
            "recent_errors": [
                {
                    "command": "old command",
                    "error_type": "file_not_found",
                    "details": "Old error",
                    "stderr": "Old stderr",
                    "timestamp": old_time.isoformat(),
                }
            ]
        }

        analysis = detector.analyze_recent_errors(session_state)
        assert analysis is None

    def test_analyze_recent_errors_malformed_timestamp(self, detector):
        """Test analyzing errors with malformed timestamps continues processing."""
        current_time = datetime.now()
        session_state = {
            "recent_errors": [
                {
                    "command": "good command",
                    "error_type": "file_not_found",
                    "details": "Good error",
                    "stderr": "No such file or directory",
                    "timestamp": (current_time - timedelta(minutes=1)).isoformat(),
                },
                {
                    "command": "bad timestamp command",
                    "error_type": "file_not_found",
                    "details": "Bad timestamp error",
                    "stderr": "No such file or directory",
                    "timestamp": "invalid-timestamp-format",  # Malformed timestamp
                },
            ]
        }

        # Should still process the good error despite the malformed timestamp
        analysis = detector.analyze_recent_errors(session_state)
        assert analysis is not None
        assert analysis["has_proactive_suggestions"] is True
        assert analysis["error_count"] >= 1  # At least the good error

    def test_generate_error_suggestion_file_not_found(self, detector):
        """Test generating suggestion for file not found error."""
        error = {
            "error_type": "file_not_found",
            "details": "No such file or directory: test.txt",
            "stderr": "cat: test.txt: No such file or directory",
        }

        suggestion = detector._generate_error_suggestion(error)

        assert suggestion is not None
        assert suggestion["error_type"] == "file_not_found"
        assert suggestion["priority"] == "high"
        assert len(suggestion["suggestions"]) > 0
        assert "Check if the file exists using" in suggestion["suggestions"][0]

    def test_generate_error_suggestion_permission_denied(self, detector):
        """Test generating suggestion for permission denied error."""
        error = {
            "error_type": "permission_denied",
            "details": "Permission denied",
            "stderr": "chmod: Permission denied",
        }

        suggestion = detector._generate_error_suggestion(error)

        assert suggestion is not None
        assert suggestion["error_type"] == "permission_denied"
        assert suggestion["priority"] == "high"
        assert "Check file permissions" in suggestion["suggestions"][0]

    def test_generate_error_suggestion_python_import(self, detector):
        """Test generating suggestion for Python import error."""
        error = {
            "error_type": "python_import_error",
            "details": "ModuleNotFoundError: No module named 'requests'",
            "stderr": "ModuleNotFoundError: No module named 'requests'",
        }

        suggestion = detector._generate_error_suggestion(error)

        assert suggestion is not None
        assert suggestion["error_type"] == "python_import_error"
        assert suggestion["priority"] == "medium"
        assert "pip install" in suggestion["suggestions"][0]

    def test_generate_error_suggestion_unknown_error(self, detector):
        """Test generating suggestion for unknown error type."""
        error = {
            "error_type": "unknown_error_type",
            "details": "Some unknown issue",
            "stderr": "Unknown issue occurred",
        }

        suggestion = detector._generate_error_suggestion(error)
        assert suggestion is None

    def test_format_proactive_suggestions(self, detector):
        """Test formatting suggestions for display."""
        analysis = {
            "has_proactive_suggestions": True,
            "error_count": 2,
            "suggestions": [
                {
                    "error": {"command": "cat test.txt"},
                    "suggestion": {
                        "error_type": "file_not_found",
                        "priority": "high",
                        "suggestions": ["Check if file exists", "Verify path"],
                        "context": {"stderr": "No such file or directory"},
                    },
                    "command": "cat test.txt",
                }
            ],
        }

        formatted = detector.format_proactive_suggestions(analysis)

        assert "🔍 **Proactive Error Detection:**" in formatted
        assert "2 recent error(s)" in formatted
        assert "cat test.txt" in formatted
        assert "File Not Found" in formatted
        assert "Check if file exists" in formatted

    def test_format_proactive_suggestions_empty(self, detector):
        """Test formatting when no suggestions available."""
        analysis = {"has_proactive_suggestions": False}
        formatted = detector.format_proactive_suggestions(analysis)
        assert formatted == ""


class TestErrorPatternMatching:
    """Test error pattern matching for different error types."""

    @pytest.fixture
    def detector(self):
        return ProactiveErrorDetector()

    def test_pattern_matching_file_not_found(self, detector):
        """Test pattern matching for file not found errors."""
        error = {
            "error_type": "generic_error",  # Wrong type initially
            "details": "Some error",
            "stderr": "No such file or directory: test.txt",
        }

        suggestion = detector._generate_error_suggestion(error)

        # Should match pattern and reclassify as file_not_found
        assert suggestion is not None
        assert suggestion["error_type"] == "file_not_found"

    def test_pattern_matching_permission_denied(self, detector):
        """Test pattern matching for permission errors."""
        error = {
            "error_type": "generic_error",
            "details": "Permission denied when accessing file",
            "stderr": "Permission denied",
        }

        suggestion = detector._generate_error_suggestion(error)
        assert suggestion["error_type"] == "permission_denied"

    def test_pattern_matching_command_not_found(self, detector):
        """Test pattern matching for command not found errors."""
        error = {
            "error_type": "generic_error",
            "details": "",
            "stderr": "bash: nonexistent_command: command not found",
        }

        suggestion = detector._generate_error_suggestion(error)
        assert suggestion["error_type"] == "command_not_found"
