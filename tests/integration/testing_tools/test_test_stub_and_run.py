from pathlib import Path

import pytest

from agents.software_engineer.tools.testing_tools import (
    _generate_test_stub,
    _run_pytest,
)


@pytest.fixture
def mock_tool_context():
    class MockToolContext:
        def __init__(self):
            self.state = {"require_edit_approval": False}

    return MockToolContext()


def test_generate_test_stub_writes_file(tmp_path: Path, mock_tool_context):
    target_path = tmp_path / "test_add.py"
    args = {
        "target_file": str(target_path),
        "function_signature": "def add(a, b):",
        "language": "python",
    }

    result = _generate_test_stub(args, mock_tool_context)

    assert result.status in {"success", "pending_approval"}
    assert target_path.exists()
    content = target_path.read_text(encoding="utf-8")
    assert "def test_add(" in content


def test_run_pytest_on_temp_dir(tmp_path: Path, mock_tool_context):
    # Create a minimal passing test in a temp directory
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    tfile = tmp_path / "test_sample.py"
    tfile.write_text(
        """
def test_always_passes():
    assert 1 == 1
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_pytest({"target": str(tmp_path)}, mock_tool_context)

    assert result.exit_code == 0
    assert result.success is True
    assert "1 passed" in (result.stdout + result.stderr)


def test_generate_test_stub_pending_approval(tmp_path: Path, mock_tool_context):
    # Require approval, so file should not be written yet
    mock_tool_context.state["require_edit_approval"] = True
    target_path = tmp_path / "test_pending.py"
    args = {
        "target_file": str(target_path),
        "description": "simple pending test",
        "language": "python",
    }

    result = _generate_test_stub(args, mock_tool_context)

    assert result.status == "pending_approval"
    assert not target_path.exists()
    assert result.proposed_filepath == str(target_path)
    assert "Auto-generated test stub" in (result.proposed_content or "")


def test_generate_test_stub_derives_filename_from_description(tmp_path: Path, mock_tool_context):
    # Do not pass target_file; use test_dir override so we stay inside tmp
    args = {
        "description": "add numbers function",
        "test_dir": str(tmp_path),
        "language": "python",
    }

    result = _generate_test_stub(args, mock_tool_context)

    assert result.status in {"success", "pending_approval"}
    # When no approval needed, file is written
    # Derivation uses slug of description prefixed with test_
    expected = list(tmp_path.glob("test_add_numbers_function.py"))
    assert expected, "Derived filename not created"
    assert expected[0].read_text(encoding="utf-8").strip() != ""


def test_generate_test_stub_unsupported_language(mock_tool_context):
    args = {
        "target_file": "irrelevant.test",
        "language": "javascript",
    }
    result = _generate_test_stub(args, mock_tool_context)
    assert result.status == "error"
    assert "Unsupported language" in result.message


def test_run_pytest_with_extra_args_k_selection(tmp_path: Path, mock_tool_context):
    # Create two tests and ensure -k selects only one
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "test_a.py").write_text(
        """
def test_alpha():
    assert True
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "test_b.py").write_text(
        """
def test_beta():
    assert True
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_pytest(
        {"target": str(tmp_path), "extra_args": ["-k", "alpha"]},
        mock_tool_context,
    )
    assert result.success is True
    out = result.stdout + result.stderr
    assert "1 passed" in out
    assert "2 passed" not in out


def test_run_pytest_reports_failures(tmp_path: Path, mock_tool_context):
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "test_fail.py").write_text(
        """
def test_will_fail():
    assert False
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_pytest({"target": str(tmp_path)}, mock_tool_context)
    assert result.success is False
    assert result.exit_code != 0
    assert "failed" in (result.stdout + result.stderr).lower()
