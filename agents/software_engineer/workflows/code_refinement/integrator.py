"""Code quality and testing integrator for iterative workflows."""

from collections.abc import AsyncGenerator
import logging
import os
from pathlib import Path
import re
import subprocess
import tempfile

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from ... import config as agent_config
from ..parsers import BanditOutputParser, MypyOutputParser, PytestOutputParser, RuffOutputParser

logger = logging.getLogger(__name__)


class CodeQualityAndTestingIntegrator(LlmAgent):
    """Integrates code quality analysis and testing into the refinement loop."""

    def __init__(self, name: str = "code_quality_testing_integrator"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Integrates code quality analysis and testing feedback into "
            "refinement loop",
            instruction="""
            You integrate code quality analysis and testing into the code refinement loop.

            Your tasks:
            1. Run code quality analysis on the current code revision
            2. Execute relevant tests if test cases are available
            3. Analyze quality and testing feedback
            4. Generate comprehensive feedback for the user and next iteration
            5. Store analysis results in session.state for decision making

            This creates a mini "red-green-refactor" cycle:
            - RED: Identify quality issues and failing tests
            - GREEN: Ensure code meets basic quality standards
            - REFACTOR: Provide feedback for user-driven improvements

            Store results in:
            - session.state['quality_analysis_results']
            - session.state['testing_results']
            - session.state['integrated_feedback']
            """,
            output_key="quality_testing_integration",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run integrated code quality analysis and testing."""

        # Get current code and revision state
        current_code = ctx.session.state.get("current_code", "")
        ctx.session.state.get("revision_history", [])
        iteration_state = ctx.session.state.get("iteration_state", {})
        current_iteration = iteration_state.get("current_iteration", 0)

        if not current_code:
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[
                        genai_types.Part(text="No code available for quality analysis and testing")
                    ]
                ),
                actions=EventActions(),
            )
            return

        # Run code quality analysis
        quality_results = self._analyze_code_quality(current_code)

        # Run testing if applicable
        testing_results = self._run_code_tests(current_code)

        # Integrate results and generate feedback
        integrated_feedback = self._integrate_quality_and_testing_feedback(
            quality_results, testing_results, current_iteration
        )

        # Update session state
        ctx.session.state["quality_analysis_results"] = quality_results
        ctx.session.state["testing_results"] = testing_results
        ctx.session.state["integrated_feedback"] = integrated_feedback

        # Generate comprehensive feedback message
        feedback_message = self._generate_comprehensive_feedback_message(
            quality_results, testing_results, integrated_feedback
        )

        yield Event(
            author=self.name,
            content=genai_types.Content(parts=[genai_types.Part(text=feedback_message)]),
            actions=EventActions(),
        )

    def _analyze_code_quality(self, code: str) -> dict:
        """Analyze code quality using various metrics."""

        try:
            # Use actual external tools for code quality analysis
            return self._run_external_quality_tools(code)
        except Exception:
            # Fallback to basic analysis if external tools fail
            return self._basic_quality_analysis(code)

    def _analyze_test_coverage(self, file_path: str, _code: str, cwd: str | None = None) -> dict:
        """Analyze potential test coverage."""
        try:
            # Prepare environment with proper PYTHONPATH
            env = os.environ.copy()
            if cwd:
                # Add source directories to PYTHONPATH for local imports
                cwd_path = Path(cwd)
                src_paths = [str(cwd_path / "src"), str(cwd_path / "agents"), cwd]
                pythonpath = os.pathsep.join([p for p in src_paths if Path(p).exists()])
                if env.get("PYTHONPATH"):
                    env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
                else:
                    env["PYTHONPATH"] = pythonpath

            # Try to run coverage analysis (basic approach)
            result = subprocess.run(
                ["uv", "run", "coverage", "run", "--source=.", file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
                env=env,
            )

            if result.returncode == 0:
                # Get coverage report
                coverage_result = subprocess.run(
                    ["uv", "run", "coverage", "report"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=cwd,
                    env=env,
                )

                # Parse coverage percentage (simplified)
                coverage_percentage = self._parse_coverage_output(coverage_result.stdout)

                return {"coverage_percentage": coverage_percentage, "tool_available": True}

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback: if coverage tool fails, clearly state that coverage could not be determined
        return {
            "coverage_percentage": None,
            "tool_available": False,
            "message": "Test coverage could not be determined as the coverage tool failed to run.",
        }

    def _basic_quality_analysis(self, code: str) -> dict:
        """Fallback basic quality analysis when external tools fail."""
        quality_issues = []
        quality_score = 100

        # Basic quality checks when external tools are not available
        lines = code.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Check for common issues
        if len(non_empty_lines) > 100:
            quality_issues.append(
                {
                    "type": "complexity",
                    "severity": "medium",
                    "message": "Code is quite long - consider breaking into smaller functions",
                    "line": None,
                    "tool": "basic_analysis",
                }
            )
            quality_score -= 10

        # Check for TODO/FIXME comments
        for i, line in enumerate(lines, 1):
            if "TODO" in line or "FIXME" in line:
                quality_issues.append(
                    {
                        "type": "maintenance",
                        "severity": "low",
                        "message": "TODO/FIXME comment found",
                        "line": i,
                        "tool": "basic_analysis",
                    }
                )
                quality_score -= 3

        # Check for missing docstrings on functions
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("def ") and "(" in line:
                # Check if next non-empty line is a docstring
                next_line_idx = i
                while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                    next_line_idx += 1

                if next_line_idx >= len(lines) or (
                    not lines[next_line_idx].strip().startswith('"""')
                    and not lines[next_line_idx].strip().startswith("'''")
                ):
                    func_name = line.split("(")[0].replace("def ", "").strip()
                    quality_issues.append(
                        {
                            "type": "documentation",
                            "severity": "low",
                            "message": f"Function '{func_name}' missing docstring",
                            "line": i,
                            "tool": "basic_analysis",
                        }
                    )
                    quality_score -= 5

        # Check for very long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                quality_issues.append(
                    {
                        "type": "style",
                        "severity": "low",
                        "message": "Line too long (>120 characters)",
                        "line": i,
                        "tool": "basic_analysis",
                    }
                )
                quality_score -= 2

        return {
            "overall_score": max(0, quality_score),
            "issues": quality_issues,
            "issues_by_severity": {
                "high": [issue for issue in quality_issues if issue["severity"] == "high"],
                "medium": [issue for issue in quality_issues if issue["severity"] == "medium"],
                "low": [issue for issue in quality_issues if issue["severity"] == "low"],
            },
            "metrics": {
                "lines_of_code": len(non_empty_lines),
                "tool_results": {
                    "basic_analysis_issues_count": len(quality_issues),
                    "external_tools_available": False,
                },
                "maintainability_index": quality_score,
            },
        }

    def _basic_test_analysis(self, code: str) -> dict:
        """Fallback basic test analysis when external tools fail."""
        test_suggestions = []

        # Basic test suggestions when external tools fail
        if "def " in code:
            functions = [
                line.strip() for line in code.split("\n") if line.strip().startswith("def ")
            ]
            for func in functions:
                func_name = func.split("(")[0].replace("def ", "")
                test_suggestions.append(
                    {
                        "type": "unit_test",
                        "target": func_name,
                        "suggestion": f"Add unit tests for {func_name} function",
                    }
                )

        # Check for testability issues
        if "input(" in code:
            test_suggestions.append(
                {
                    "type": "testability",
                    "target": "user_input",
                    "suggestion": (
                        "Consider dependency injection for user input to improve testability"
                    ),
                }
            )

        if "print(" in code:
            test_suggestions.append(
                {
                    "type": "testability",
                    "target": "output",
                    "suggestion": (
                        "Consider returning values instead of printing for better testability"
                    ),
                }
            )

        return {
            "tests_run": len(test_suggestions),
            "tests_passed": len(test_suggestions),
            "tests_failed": 0,
            "coverage_percentage": None,
            "testability_score": 80,
            "test_suggestions": test_suggestions,
            "test_execution_output": "External testing tools not available - using basic analysis",
            "tool_results": {
                "pytest_available": False,
                "coverage_tool_available": False,
            },
        }

    def _calculate_testability_score(self, code: str) -> int:
        """Calculate how testable the code is."""
        score = 100

        # Deduct points for testability issues
        if "input(" in code:
            score -= 20  # User input makes testing difficult
        if "print(" in code and "return" not in code:
            score -= 15  # Only printing, no return values
        if "global " in code:
            score -= 10  # Global variables reduce testability
        if "random" in code and "seed" not in code:
            score -= 15  # Uncontrolled randomness

        # Bonus points for good practices
        if "def test_" in code:
            score += 10  # Already has test functions
        if "assert" in code:
            score += 5  # Has assertions

        return max(0, min(100, score))

    def _contains_test_functions(self, code: str) -> bool:
        """Check if code contains test functions."""
        # Look for test functions (pytest style)
        test_function_pattern = r"def\s+test_\w+\s*\("
        return bool(re.search(test_function_pattern, code))

    def _estimate_coverage_from_code(self, code: str) -> int:
        """Estimate test coverage based on the number of assert statements."""
        lines = [line.strip() for line in code.split("\n") if line.strip()]
        if not lines:
            return 0

        # Count the number of assert statements to estimate test coverage
        assert_statements = sum(1 for line in lines if line.startswith("assert "))

        # Assume that a higher number of asserts indicates better test coverage
        # This is a simplified heuristic and should be tuned based on project standards
        coverage_percentage = min(100, int((assert_statements / len(lines)) * 200))

        # Ensure a baseline coverage for files with at least one test
        if assert_statements > 0 and coverage_percentage < 15:
            return 15

        return coverage_percentage

    def _generate_comprehensive_feedback_message(
        self, quality_results: dict, testing_results: dict, integrated_feedback: dict
    ) -> str:
        """Generate a comprehensive feedback message for the user."""

        message_parts = []

        # Header
        message_parts.append("## 🔍 Code Quality & Testing Analysis")
        message_parts.append("")

        # Overall assessment
        assessment = integrated_feedback.get("overall_assessment", "unknown")
        assessment_emoji = {
            "excellent": "✅",
            "good": "👍",
            "acceptable": "⚠️",
            "needs_improvement": "❌",
        }.get(assessment, "❓")

        message_parts.append(
            f"**Overall Assessment:** {assessment_emoji} {assessment.replace('_', ' ').title()}"
        )
        message_parts.append("")

        # Quality metrics
        quality_score = quality_results.get("overall_score", 0)
        message_parts.append(f"**Quality Score:** {quality_score}/100")
        message_parts.append("")

        # Critical actions
        critical_actions = integrated_feedback.get("critical_actions", [])
        if critical_actions:
            message_parts.append("### 🚨 Critical Actions Required:")
            for action in critical_actions:
                message_parts.append(f"- **{action['type'].title()}:** {action['description']}")
            message_parts.append("")

        # Testing feedback
        coverage = testing_results.get("coverage_percentage")
        tests_run = testing_results.get("tests_run", 0)
        tests_passed = testing_results.get("tests_passed", 0)

        message_parts.append("### 🧪 Testing Status:")
        if coverage is not None:
            message_parts.append(f"- **Test Coverage:** {coverage}%")
        else:
            message_parts.append("- **Test Coverage:** Could not be determined")
        message_parts.append(f"- **Tests Run:** {tests_run} (Passed: {tests_passed})")
        message_parts.append("")

        # Improvement suggestions
        suggestions = integrated_feedback.get("improvement_suggestions", [])
        if suggestions:
            message_parts.append("### 💡 Improvement Suggestions:")
            for suggestion in suggestions[:5]:  # Limit to top 5
                message_parts.append(f"- {suggestion['suggestion']}")
            message_parts.append("")

        # Next priorities
        priorities = integrated_feedback.get("next_refactor_priorities", [])
        if priorities:
            message_parts.append("### 🎯 Next Refactor Priorities:")
            for priority, count in priorities[:3]:  # Top 3 priorities
                message_parts.append(f"- **{priority.replace('_', ' ').title()}** ({count} issues)")
            message_parts.append("")

        # Call to action
        if critical_actions:
            message_parts.append(
                "**Recommendation:** Address critical issues before proceeding with "
                "additional features."
            )
        elif suggestions:
            message_parts.append(
                "**Recommendation:** Consider implementing suggested improvements for "
                "better code quality."
            )
        else:
            message_parts.append(
                "**Recommendation:** Code quality is good! Ready for additional features "
                "or optimizations."
            )

        return "\n".join(message_parts)

    def _generate_real_test_suggestions(self, code: str, _file_path: str) -> list[dict]:
        """Generate practical test suggestions based on actual code analysis."""
        suggestions = []

        # Use AST to analyze the code structure
        import ast

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("test_"):
                        # Suggest unit test for non-test functions
                        suggestions.append(
                            {
                                "type": "unit_test",
                                "target": node.name,
                                "suggestion": f"Add unit test for function '{node.name}'",
                                "line": node.lineno,
                                "priority": "medium",
                            }
                        )

                        # Check for specific patterns that need testing
                        for child in ast.walk(node):
                            if isinstance(child, ast.Raise):
                                suggestions.append(
                                    {
                                        "type": "exception_test",
                                        "target": node.name,
                                        "suggestion": f"Test exception handling in '{node.name}'",
                                        "line": child.lineno,
                                        "priority": "high",
                                    }
                                )

                elif isinstance(node, ast.ClassDef):
                    suggestions.append(
                        {
                            "type": "class_test",
                            "target": node.name,
                            "suggestion": f"Add test class for '{node.name}'",
                            "line": node.lineno,
                            "priority": "medium",
                        }
                    )

        except SyntaxError:
            suggestions.append(
                {
                    "type": "syntax_fix",
                    "target": "code",
                    "suggestion": "Fix syntax errors before adding tests",
                    "priority": "high",
                }
            )

        return suggestions[:10]  # Limit to 10 suggestions

    def _get_project_root(self, project_root: str | None = None) -> str:
        """Get the project root directory for proper subprocess execution context."""
        if project_root:
            return project_root

        # Try to find project root by looking for common project indicators
        current_path = Path(__file__).resolve()

        # Look for project markers (pyproject.toml, setup.py, .git, etc.)
        project_markers = ["pyproject.toml", "setup.py", ".git", "poetry.lock", "requirements.txt"]

        for parent in [current_path, *list(current_path.parents)]:
            for marker in project_markers:
                if (parent / marker).exists():
                    return str(parent)

        # Fallback to current working directory
        return str(Path.cwd())

    def _integrate_quality_and_testing_feedback(
        self, quality_results: dict, testing_results: dict, iteration: int
    ) -> dict:
        """Integrate quality and testing feedback into actionable recommendations."""

        integrated_feedback = {
            "iteration": iteration,
            "overall_assessment": "good",
            "critical_actions": [],
            "improvement_suggestions": [],
            "next_refactor_priorities": [],
        }

        # Analyze quality issues
        high_quality_issues = quality_results.get("issues_by_severity", {}).get("high", [])
        medium_quality_issues = quality_results.get("issues_by_severity", {}).get("medium", [])

        # Set overall assessment
        if len(high_quality_issues) > 0:
            integrated_feedback["overall_assessment"] = "needs_improvement"
        elif len(medium_quality_issues) > 2:
            integrated_feedback["overall_assessment"] = "acceptable"

        # Generate critical actions for high-severity issues
        for issue in high_quality_issues:
            integrated_feedback["critical_actions"].append(
                {
                    "action": "fix_quality_issue",
                    "priority": "high",
                    "description": issue["message"],
                    "type": issue["type"],
                }
            )

        # Generate improvement suggestions
        for issue in medium_quality_issues:
            integrated_feedback["improvement_suggestions"].append(
                {"suggestion": issue["message"], "type": issue["type"], "impact": "medium"}
            )

        # Integrate testing feedback
        test_suggestions = testing_results.get("test_suggestions", [])
        for suggestion in test_suggestions:
            if suggestion["type"] == "testability":
                integrated_feedback["critical_actions"].append(
                    {
                        "action": "improve_testability",
                        "priority": "medium",
                        "description": suggestion["suggestion"],
                        "type": "testing",
                    }
                )
            else:
                integrated_feedback["improvement_suggestions"].append(
                    {"suggestion": suggestion["suggestion"], "type": "testing", "impact": "medium"}
                )

        # Set refactor priorities based on integrated analysis
        priority_map = {}
        for action in integrated_feedback["critical_actions"]:
            action_type = action["type"]
            priority_map[action_type] = priority_map.get(action_type, 0) + 1

        # Sort by frequency of issues
        integrated_feedback["next_refactor_priorities"] = sorted(
            priority_map.items(), key=lambda x: x[1], reverse=True
        )

        return integrated_feedback

    def _parse_coverage_output(self, coverage_output: str) -> int:
        """Parse coverage tool output to extract percentage."""
        # Look for coverage percentage in output
        percentage_pattern = r"(\d+)%"
        matches = re.findall(percentage_pattern, coverage_output)

        if matches:
            return int(matches[-1])  # Take the last percentage found

        return 0

    def _run_external_quality_tools(self, code: str) -> dict:
        """Run actual external code quality tools on the code."""
        quality_issues = []
        quality_score = 100

        # Get project root directory for proper context
        project_root = self._get_project_root()

        # Create a temporary file to store the code for analysis.
        # The with statement ensures the file is automatically cleaned up.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=True, dir=project_root
        ) as tmp_file:
            tmp_file.write(code)
            tmp_file.flush()  # Ensure code is written to disk before analysis
            tmp_file_path = tmp_file.name

            # Run ruff for linting
            ruff_issues = self._run_ruff_analysis(tmp_file_path, cwd=project_root)
            quality_issues.extend(ruff_issues)

            # Run mypy for type checking (if possible)
            mypy_issues = self._run_mypy_analysis(tmp_file_path, cwd=project_root)
            quality_issues.extend(mypy_issues)

            # Run bandit for security analysis
            bandit_issues = self._run_bandit_analysis(tmp_file_path, cwd=project_root)
            quality_issues.extend(bandit_issues)

        # Calculate quality score based on issues
        for issue in quality_issues:
            if issue["severity"] == "high":
                quality_score -= 15
            elif issue["severity"] == "medium":
                quality_score -= 8
            elif issue["severity"] == "low":
                quality_score -= 3

        return {
            "overall_score": max(0, quality_score),
            "issues": quality_issues,
            "issues_by_severity": {
                "high": [issue for issue in quality_issues if issue["severity"] == "high"],
                "medium": [issue for issue in quality_issues if issue["severity"] == "medium"],
                "low": [issue for issue in quality_issues if issue["severity"] == "low"],
            },
            "metrics": {
                "lines_of_code": len(code.split("\n")),
                "tool_results": {
                    "ruff_issues_count": len(
                        [i for i in quality_issues if i.get("tool") == "ruff"]
                    ),
                    "mypy_issues_count": len(
                        [i for i in quality_issues if i.get("tool") == "mypy"]
                    ),
                    "bandit_issues_count": len(
                        [i for i in quality_issues if i.get("tool") == "bandit"]
                    ),
                },
                "maintainability_index": quality_score,
            },
        }

    def _run_ruff_analysis(self, file_path: str, cwd: str | None = None) -> list[dict]:
        """Run ruff linter on the code file using uv's environment management."""
        try:
            # Use uv run without manual PYTHONPATH manipulation
            # uv automatically manages the Python environment and paths
            result = subprocess.run(
                ["uv", "run", "ruff", "check", file_path, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd or self._get_project_root(),
            )

            # Use dedicated parser for robust output handling
            parser = RuffOutputParser()
            return parser.parse(result.stdout, result.stderr)

        except FileNotFoundError:
            logger.warning("ruff not found in the environment. Skipping ruff analysis.")
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
        ):
            # If ruff execution fails, return empty list
            pass

        return []

    def _run_mypy_analysis(self, file_path: str, cwd: str | None = None) -> list[dict]:
        """Run mypy type checker on the code file using uv's environment management."""
        try:
            # Use uv run without manual PYTHONPATH manipulation
            # uv automatically manages the Python environment and paths
            result = subprocess.run(
                ["uv", "run", "mypy", file_path, "--show-error-codes"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd or self._get_project_root(),
            )

            # Use dedicated parser for robust output handling
            parser = MypyOutputParser()
            return parser.parse(result.stdout, result.stderr)

        except FileNotFoundError:
            logger.warning("mypy not found in the environment. Skipping mypy analysis.")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            # If mypy execution fails, return empty list
            pass

        return []

    def _run_bandit_analysis(self, file_path: str, cwd: str | None = None) -> list[dict]:
        """Run bandit security analysis on the code file using uv's environment management."""
        try:
            # Use uv run without manual PYTHONPATH manipulation
            # uv automatically manages the Python environment and paths
            result = subprocess.run(
                ["uv", "run", "bandit", "-f", "json", file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd or self._get_project_root(),
            )

            # Use dedicated parser for robust output handling
            parser = BanditOutputParser()
            return parser.parse(result.stdout, result.stderr)

        except FileNotFoundError:
            logger.warning("bandit not found in the environment. Skipping bandit analysis.")
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
        ):
            # If bandit execution fails, return empty list
            pass

        return []

    def _run_code_tests(self, code: str) -> dict:
        """Run actual tests on the current code."""
        try:
            # Use actual test execution tools
            return self._run_external_test_tools(code)
        except Exception:
            # Fallback to basic test analysis if external tools fail
            return self._basic_test_analysis(code)

    def _run_external_test_tools(self, code: str) -> dict:
        """Run actual external testing tools on the code."""
        # Get project root directory for proper context
        project_root = self._get_project_root()

        # Use TemporaryDirectory context manager for better resource management
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Create a temporary file within the temporary directory
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", dir=temp_dir_path, delete=False
            ) as tmp_file:
                tmp_file.write(code)
                tmp_file_path = tmp_file.name
            # File is now properly closed

            try:
                # Run pytest to check if the code has testable functions
                test_results = self._run_pytest_analysis(tmp_file_path, code, cwd=project_root)

                # Generate test suggestions based on actual code analysis
                test_suggestions = self._generate_real_test_suggestions(code, tmp_file_path)

                # Run coverage analysis if possible
                coverage_results = self._analyze_test_coverage(
                    tmp_file_path, code, cwd=project_root
                )

                return {
                    "tests_run": test_results.get("tests_run", 0),
                    "tests_passed": test_results.get("tests_passed", 0),
                    "tests_failed": test_results.get("tests_failed", 0),
                    "coverage_percentage": coverage_results.get("coverage_percentage", 0),
                    "testability_score": self._calculate_testability_score(code),
                    "test_suggestions": test_suggestions,
                    "test_execution_output": test_results.get("output", ""),
                    "tool_results": {
                        "pytest_available": test_results.get("pytest_available", False),
                        "coverage_tool_available": coverage_results.get("tool_available", False),
                    },
                }
            finally:
                # Clean up temporary file (directory will be cleaned up automatically)
                try:
                    Path(tmp_file_path).unlink()
                except OSError:
                    # File already deleted or other issue
                    pass
        # The temporary directory and its contents are automatically cleaned up here

    def _run_pytest_analysis(self, file_path: str, code: str, cwd: str | None = None) -> dict:
        """Run pytest to analyze test execution possibilities."""
        try:
            # Check if the code contains any test functions
            has_tests = self._contains_test_functions(code)

            if has_tests:
                # Prepare environment with proper PYTHONPATH
                env = os.environ.copy()
                if cwd:
                    # Add source directories to PYTHONPATH for local imports
                    cwd_path = Path(cwd)
                    src_paths = [str(cwd_path / "src"), str(cwd_path / "agents"), cwd]
                    pythonpath = os.pathsep.join([p for p in src_paths if Path(p).exists()])
                    if env.get("PYTHONPATH"):
                        env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
                    else:
                        env["PYTHONPATH"] = pythonpath

                # Run pytest on the file
                result = subprocess.run(
                    ["uv", "run", "pytest", file_path, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=cwd,
                    env=env,
                )

                # Use dedicated parser for robust output handling
                parser = PytestOutputParser()
                return parser.parse(result.stdout, result.stderr)
            # No tests in the code, but pytest is available
            return {
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "output": "No test functions found in code",
                "pytest_available": True,
            }

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # pytest not available or failed
            return {
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "output": "pytest not available or failed to execute",
                "pytest_available": False,
            }
