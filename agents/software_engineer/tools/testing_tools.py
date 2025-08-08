"""Testing-related tools: test stub generation and pytest execution.

Implements Milestone 5.1:
- _generate_test_stub: create a placeholder test file scaffold
- run_pytest: execute tests using `uv run pytest` and return structured results
"""

from __future__ import annotations

import logging
from pathlib import Path
import re
import subprocess

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

from .filesystem import edit_file_content

logger = logging.getLogger(__name__)


class GenerateTestStubInput(BaseModel):
    """Input for generating a test stub file."""

    # Either provide a direct target_file, or enough info to derive one
    target_file: str | None = Field(
        default=None, description="Optional explicit path for the test file to create"
    )
    function_signature: str | None = Field(
        default=None,
        description=(
            "Optional function/method signature to base the stub name on (e.g., 'def add(a, b):')"
        ),
    )
    description: str | None = Field(
        default=None, description="Optional natural language description of what to test"
    )
    language: str = Field(default="python", description="Target language for the test stub")
    test_dir: str = Field(
        default="tests/unit",
        description="Directory to place the generated test file if target_file not provided",
    )


class GenerateTestStubOutput(BaseModel):
    """Output for generating a test stub file."""

    status: str
    message: str
    proposed_filepath: str | None = None
    proposed_content: str | None = None
    filepath: str | None = None


def _derive_test_filename(
    language: str, test_dir: str, function_signature: str | None, description: str | None
) -> str:
    Path(test_dir).mkdir(parents=True, exist_ok=True)

    if language.lower() == "python":
        function_name = None
        if function_signature:
            match = re.search(r"def\s+(\w+)\s*\(", function_signature)
            if match:
                function_name = match.group(1)

        if not function_name and description:
            # slugify a bit
            slug = _slugify(description)
            slug = slug[:32] if slug else "placeholder"
            function_name = slug

        base = f"test_{function_name or 'placeholder'}.py"
        return str(Path(test_dir) / base)

    # Default fallback
    return str(Path(test_dir) / "test_placeholder.txt")


def _render_python_test_stub(function_signature: str | None, description: str | None) -> str:
    header_lines = [
        "# Auto-generated test stub.",
        "# Replace the placeholder test with real tests.",
        "# Keep tests deterministic and readable.",
        "",
    ]

    body_lines = [
        "import pytest",
        "",
    ]

    title_hint = None
    if function_signature:
        m = re.search(r"def\s+(\w+)\s*\(", function_signature)
        if m:
            title_hint = m.group(1)

    if not title_hint and description:
        slug = _slugify(description)
        title_hint = slug[:24] if slug else None

    test_name = f"test_{title_hint}" if title_hint else "test_placeholder"

    body_lines.extend(
        [
            f"def {test_name}():",
            "    # TODO: replace with real assertions",
            "    assert True",
            "",
        ]
    )

    return "\n".join(header_lines + body_lines) + "\n"


def _slugify(text: str) -> str:
    """Convert arbitrary text to a filesystem-safe slug.

    Keeps alphanumerics and underscores, collapses other chars to underscores,
    trims leading/trailing underscores, and lowercases.
    """
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def _workspace_root(tool_context: ToolContext) -> Path:
    """Determine the secure workspace root for path validation."""
    # Prefer an explicit root from context, else use current working directory
    root = tool_context.state.get("workspace_root") if tool_context and tool_context.state else None
    try:
        return Path(root).resolve() if root else Path.cwd().resolve()
    except Exception:
        return Path.cwd().resolve()


def _resolve_and_validate_path(candidate: str | Path, root: Path) -> Path:
    """Resolve a path and ensure it stays within the given root (no traversal)."""
    p = Path(candidate).expanduser().resolve()
    if not _is_within_root(p, root):
        raise ValueError(f"Path '{p}' is outside the allowed workspace root '{root}'.")
    return p


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _generate_test_stub(args: dict, tool_context: ToolContext) -> GenerateTestStubOutput:
    """Generate a test stub file and propose/write it via edit_file_content.

    Respects the approval flow in edit_file_content. Returns whatever that
    function returns, wrapped in a consistent shape.
    """
    input_data = GenerateTestStubInput(**args)

    if input_data.language.lower() != "python":
        return GenerateTestStubOutput(
            status="error",
            message=(
                f"Unsupported language: {input_data.language}. "
                "Only 'python' is supported at this time."
            ),
        )

    # Secure path handling
    root = _workspace_root(tool_context)
    try:
        if input_data.target_file:
            target_path = _resolve_and_validate_path(input_data.target_file, root)
        else:
            # Derive filename under test_dir (validated)
            derived = _derive_test_filename(
                input_data.language,
                input_data.test_dir,
                input_data.function_signature,
                input_data.description,
            )
            # Ensure test_dir and derived file reside within root
            test_dir_path = _resolve_and_validate_path(input_data.test_dir, root)
            target_path = _resolve_and_validate_path(Path(derived), root)
            # Additionally ensure the derived path is inside the validated test_dir
            if not _is_within_root(target_path, test_dir_path):
                raise ValueError(
                    f"Derived test path '{target_path}' must be within test_dir '{test_dir_path}'."
                )
        target_file = str(target_path)
    except Exception as e:
        return GenerateTestStubOutput(status="error", message=str(e))

    content = _render_python_test_stub(input_data.function_signature, input_data.description)

    logger.info(f"Proposing test stub generation at: {target_file}")
    result = edit_file_content(target_file, content, tool_context)

    # Normalize response
    status = result.get("status", "unknown")
    message = result.get("message", "")
    proposed_filepath = result.get("proposed_filepath") or target_file
    proposed_content = result.get("proposed_content") or content

    filepath = None
    if status == "success":
        filepath = target_file

    return GenerateTestStubOutput(
        status=status,
        message=message,
        proposed_filepath=proposed_filepath,
        proposed_content=proposed_content,
        filepath=filepath,
    )


generate_test_stub_tool = FunctionTool(func=_generate_test_stub)


class RunPytestInput(BaseModel):
    """Input for running pytest."""

    target: str | None = Field(
        default=None,
        description="Optional path for a test file/directory or node-id. Defaults to 'tests/'.",
    )
    extra_args: list[str] | None = Field(
        default=None,
        description="Additional pytest CLI arguments (e.g., ['-q', '-k', 'pattern'])",
    )


class RunPytestOutput(BaseModel):
    """Structured result from running pytest via uv."""

    command: str
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    used_args: list[str] | None = None


def _run_pytest(args: dict, tool_context: ToolContext) -> RunPytestOutput:
    """Run pytest using uv and return structured output.

    Always prefers the user's requirement to use `uv` for Python tasks.
    """
    input_data = RunPytestInput(**args)
    root = _workspace_root(tool_context)
    # Validate target path strictly inside workspace
    target_input = input_data.target or "tests/"
    allow_external = bool(
        tool_context and getattr(tool_context, "state", {}).get("allow_external_target")
    )
    try:
        target_path = (
            Path(target_input).resolve()
            if allow_external
            else _resolve_and_validate_path(target_input, root)
        )
    except Exception as e:
        return RunPytestOutput(
            command="",
            exit_code=2,
            success=False,
            stdout="",
            stderr=f"Invalid target: {e}",
            used_args=None,
        )

    # Sanitize pytest args with a conservative allow-list
    extra_args = input_data.extra_args or []
    safe_singletons = {"-q", "-v", "-vv", "-vvv", "-x", "-s"}
    expects_value = {"-k", "-m", "-n"}
    prefix_allow = {"--maxfail="}

    sanitized: list[str] = []
    i = 0
    while i < len(extra_args):
        arg = str(extra_args[i])
        if arg in safe_singletons:
            sanitized.append(arg)
        elif any(arg.startswith(pref) for pref in prefix_allow):
            # Only allow numeric for --maxfail=
            try:
                val = arg.split("=", 1)[1]
                if val.isdigit():
                    sanitized.append(arg)
            except Exception:
                pass
        elif arg in expects_value:
            # attach next token as value if present and safe-ish (no leading dash)
            val = extra_args[i + 1] if i + 1 < len(extra_args) else None
            if isinstance(val, str) and not val.startswith("-"):
                sanitized.extend([arg, val])
                i += 1
        # else drop the arg silently
        i += 1

    cmd = ["uv", "run", "pytest", str(target_path), "-q", *sanitized]

    logger.info("Running tests: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return RunPytestOutput(
            command=" ".join(cmd),
            exit_code=result.returncode,
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            used_args=sanitized,
        )
    except FileNotFoundError as e:
        # uv missing
        return RunPytestOutput(
            command=" ".join(cmd),
            exit_code=127,
            success=False,
            stdout="",
            stderr=f"Failed to run tests: {e}",
            used_args=sanitized,
        )
    except Exception as e:  # pragma: no cover - safety net
        return RunPytestOutput(
            command=" ".join(cmd),
            exit_code=1,
            success=False,
            stdout="",
            stderr=f"Unexpected error running tests: {e}",
            used_args=sanitized,
        )


run_pytest_tool = FunctionTool(func=_run_pytest)
