from pathlib import Path

import pytest

from agents.software_engineer.tools.filesystem import (
    configure_edit_approval,
    replace_content_regex,
)


# Helper for creating a dummy ToolContext for testing
@pytest.fixture
def mock_tool_context():
    class MockToolContext:
        def __init__(self):
            self.state = {"require_edit_approval": False}  # Default to no approval for tests

        def get_state(self, key, default=None):
            return self.state.get(key, default)

        def set_state(self, key, value):
            self.state[key] = value

    return MockToolContext()


@pytest.fixture
def temp_file(tmp_path):
    def _create_temp_file(filename="test_file.txt", content=""):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return str(file_path)

    return _create_temp_file


def test_replace_content_regex_simple_replacement(temp_file, mock_tool_context):
    filepath = temp_file(content="Hello World\nHello Python\nHello Regex")
    pattern = "Hello"
    replacement = "Goodbye"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "success"
    assert "Successfully applied regex replacement" in result["message"]
    assert Path(filepath).read_text() == "Goodbye World\nGoodbye Python\nGoodbye Regex"


def test_replace_content_regex_no_match(temp_file, mock_tool_context):
    filepath = temp_file(content="Apple Banana Cherry")
    pattern = "Orange"
    replacement = "Kiwi"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "success"
    assert "No changes made" in result["message"]
    assert not result["changes_made"]
    assert Path(filepath).read_text() == "Apple Banana Cherry"


def test_replace_content_regex_multiple_matches_all(temp_file, mock_tool_context):
    filepath = temp_file(content="One two three one two three")
    pattern = "two"
    replacement = "2"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "success"
    assert Path(filepath).read_text() == "One 2 three one 2 three"


def test_replace_content_regex_limited_matches(temp_file, mock_tool_context):
    filepath = temp_file(content="apple, banana, apple, orange")
    pattern = "apple"
    replacement = "kiwi"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context, count=1)
    assert result["status"] == "success"
    assert Path(filepath).read_text() == "kiwi, banana, apple, orange"


def test_replace_content_regex_capture_groups(temp_file, mock_tool_context):
    filepath = temp_file(content="Name: John Doe, Age: 30")
    pattern = r"Name: (.*?), Age: (\d+)"
    replacement = r"Age: \2, Name: \1"  # Swap order
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "success"
    assert Path(filepath).read_text() == "Age: 30, Name: John Doe"


def test_replace_content_regex_invalid_pattern(temp_file, mock_tool_context):
    filepath = temp_file(content="Some content")
    pattern = "["  # Invalid regex
    replacement = "something"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "error"
    assert result["error_type"] == "InvalidRegex"
    assert "Invalid regex pattern provided" in result["message"]


def test_replace_content_regex_file_not_found(mock_tool_context):
    filepath = "non_existent_file.txt"
    pattern = "test"
    replacement = "new"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "error"
    assert result["error_type"] == "FileNotFound"
    assert "File not found" in result["message"]


def test_replace_content_regex_approval_pending(temp_file, mock_tool_context):
    filepath = temp_file(content="Initial content.")
    configure_edit_approval(True, mock_tool_context)  # Require approval
    pattern = "Initial"
    replacement = "Modified"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "pending_approval"
    assert "Proposed regex replacement" in result["message"]
    assert Path(filepath).read_text() == "Initial content."  # Content should not be written yet


def test_replace_content_regex_approval_success_no_approval_needed(temp_file, mock_tool_context):
    filepath = temp_file(content="Old content here.")
    configure_edit_approval(False, mock_tool_context)  # No approval needed
    pattern = "Old"
    replacement = "New"
    result = replace_content_regex(filepath, pattern, replacement, mock_tool_context)
    assert result["status"] == "success"
    assert "Successfully applied regex replacement" in result["message"]
    assert Path(filepath).read_text() == "New content here."
