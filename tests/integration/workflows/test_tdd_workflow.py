from pathlib import Path

from google.adk.tools import ToolContext  # noqa: F401  # Imported for type reference only
import pytest

from agents.software_engineer.enhanced_agent import _auto_run_tests_after_edit
from agents.software_engineer.tools.testing_tools import _run_pytest
from tests.shared.helpers import create_test_workspace


@pytest.mark.integration
def test_tdd_auto_run_after_edit(monkeypatch):
    """TDD mode auto-runs pytest after a simulated successful edit callback."""
    # Prepare isolated workspace
    workspace = Path(create_test_workspace())

    # Switch CWD to the workspace for this test
    monkeypatch.chdir(workspace)

    # Create a simple passing test file under tests/
    tests_dir = workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    target = tests_dir / "test_auto.py"
    target.write_text(
        """
def test_auto_smoke():
    assert 2 + 2 == 4
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Build a minimal context with a writable 'state' mapping
    class MockCtx:
        def __init__(self, state):
            self.state = state

    ctx = MockCtx(
        {
            "TDD_mode_enabled": True,
            "require_edit_approval": False,
            "workspace_root": str(workspace),
        }
    )

    # Simulate after-tool callback for a successful edit
    class MockTool:
        name = "edit_file_content"

    args = {"filepath": str(target)}
    response = {"status": "success"}

    _auto_run_tests_after_edit(MockTool(), args, ctx, response)

    last = ctx.state.get("last_test_run")
    assert last is not None, "Expected last_test_run in session state"
    assert isinstance(last.get("success"), bool)


@pytest.mark.integration
def test_run_pytest_parsing(tmp_path):
    # Minimal passing test file
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "test_ok.py").write_text(
        """
def test_ok():
    assert True
""".strip()
        + "\n",
        encoding="utf-8",
    )

    class MockToolContext:
        def __init__(self):
            self.state = {"workspace_root": str(tmp_path)}

    ctx = MockToolContext()
    res = _run_pytest({"target": str(tmp_path)}, ctx)
    assert res.success is True
    assert (res.summary_line or "").strip() != ""
    assert (res.tests_passed or 0) >= 1
