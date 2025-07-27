"""Code analysis tool for the software engineer agent.

This tool performs static analysis on code files using language-specific analyzers
and provides detailed reports on quality, complexity, and potential issues.
"""

from enum import Enum
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Optional

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

# Third-party analysis libraries - using try/except to make dependencies optional
try:
    import pylint.lint
    import pylint.reporters.text

    PYLINT_AVAILABLE = True
except ImportError:
    PYLINT_AVAILABLE = False

try:
    # NOTE: flake8.api.legacy is no longer available in newer versions of flake8
    # We'll use a different approach for flake8
    import flake8  # noqa: F401
    from flake8.main.application import Application

    FLAKE8_AVAILABLE = True
except ImportError:
    FLAKE8_AVAILABLE = False

try:
    import radon.complexity
    import radon.metrics

    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

try:
    import bandit
    from bandit.core import manager as bandit_manager

    BANDIT_AVAILABLE = True
except ImportError:
    BANDIT_AVAILABLE = False


class AnalysisSeverity(str, Enum):
    """Severity levels for analysis issues."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CodeIssue(BaseModel):
    """Model for code issues identified during analysis."""

    line: Optional[int] = None
    column: Optional[int] = None
    severity: AnalysisSeverity = AnalysisSeverity.INFO
    message: str
    code: Optional[str] = None
    source: str  # The tool that found this issue (e.g., "pylint", "flake8", "ruff")


class AnalyzeCodeInput(BaseModel):
    """Input model for code analysis."""

    file_path: str = Field(description="Path to the file to analyze")


class CodeAnalysisResult(BaseModel):
    """Result model for code analysis."""

    file_path: str
    language: str
    lines_of_code: int
    issues: list[CodeIssue] = []
    metrics: dict[str, Any] = {}
    status: str
    error: Optional[str] = None


def detect_language(file_path: str) -> str:
    """
    Detect the programming language from a file extension.

    Args:
        file_path: Path to the file

    Returns:
        String representing the language
    """
    ext = Path(file_path).suffix.lower()
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c_header",
        ".hpp": "cpp_header",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".sh": "shell",
    }
    return language_map.get(ext, "unknown")


def check_uv_available() -> bool:
    """Check if uv is available in the system."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_ruff_analysis(file_path: str) -> list[CodeIssue]:
    """
    Run ruff analysis on a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        List of CodeIssue objects found by ruff
    """
    issues = []

    # Try with uv first, then fallback to direct ruff
    commands_to_try = []

    if check_uv_available():
        commands_to_try.extend(
            [
                ["uv", "run", "ruff", "check", file_path, "--output-format=json"],
                ["uv", "run", "ruff", "format", "--check", file_path],
            ]
        )

    commands_to_try.extend(
        [
            ["ruff", "check", file_path, "--output-format=json"],
            ["ruff", "format", "--check", file_path],
        ]
    )

    # Run ruff check
    for cmd in commands_to_try[:2]:  # Only check commands
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 127:  # Command found
                if result.stdout:
                    try:
                        ruff_data = json.loads(result.stdout)
                        for issue in ruff_data:
                            severity = AnalysisSeverity.WARNING
                            if issue.get("code", "").startswith("E"):
                                severity = AnalysisSeverity.ERROR
                            elif issue.get("code", "").startswith("F"):
                                severity = AnalysisSeverity.CRITICAL

                            issues.append(
                                CodeIssue(
                                    line=issue.get("location", {}).get("row"),
                                    column=issue.get("location", {}).get("column"),
                                    severity=severity,
                                    message=issue.get("message", ""),
                                    code=issue.get("code"),
                                    source="ruff",
                                )
                            )
                    except json.JSONDecodeError:
                        pass
                break
        except FileNotFoundError:
            continue

    return issues


def analyze_python_code(file_path: str, code: str) -> dict[str, Any]:
    """
    Analyze Python code using modern tools (ruff preferred) and traditional tools.

    Args:
        file_path: Path to the Python file
        code: Content of the file

    Returns:
        Dict with analysis results
    """
    issues = []
    metrics = {}

    # Try ruff first (modern approach)
    try:
        ruff_issues = run_ruff_analysis(file_path)
        issues.extend(ruff_issues)
    except Exception as e:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.ERROR,
                message=f"Error running ruff: {e!s}",
                source="analyzer",
            )
        )

    # Run pylint
    if PYLINT_AVAILABLE:
        try:
            from io import StringIO

            output = StringIO()
            reporter = pylint.reporters.text.TextReporter(output)

            pylint.lint.Run([file_path, "--output-format=text"], reporter=reporter, exit=False)

            pylint_output = output.getvalue()
            # TODO: Sonar Report - https://sonarcloud.io/project/security_hotspots?id=BlueCentre_code-agent&pullRequest=19&issueStatuses=OPEN,CONFIRMED&sinceLeakPeriod=true  # noqa: E501
            # NOTE: Make sure the regex used here, which is vulnerable to polynomial runtime due to backtracking, cannot lead to denial of service.  # noqa: E501
            # Parse pylint output
            pattern = r"([A-Z]):\s*(\d+),\s*(\d+):\s*(.+)\s*\(([A-Z0-9]+)\)"
            for match in re.finditer(pattern, pylint_output):
                severity_code, line, col, message, code = match.groups()
                severity_map = {
                    "E": AnalysisSeverity.ERROR,
                    "F": AnalysisSeverity.CRITICAL,
                    "W": AnalysisSeverity.WARNING,
                    "C": AnalysisSeverity.INFO,
                    "R": AnalysisSeverity.INFO,
                }

                issues.append(
                    CodeIssue(
                        line=int(line),
                        column=int(col),
                        severity=severity_map.get(severity_code, AnalysisSeverity.INFO),
                        message=message.strip(),
                        code=code,
                        source="pylint",
                    )
                )
        except Exception as e:
            issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.ERROR,
                    message=f"Error running pylint: {e!s}",
                    source="analyzer",
                )
            )

    # Run flake8 (only if ruff didn't work)
    if FLAKE8_AVAILABLE and not any(issue.source == "ruff" for issue in issues):
        try:
            # Use the Application class directly instead of the legacy API
            flake8_app = Application()
            flake8_app.initialize([file_path])
            flake8_app.run_checks([file_path])
            flake8_app.formatter.start()

            for file_errors in flake8_app.guide.stats.statistics_for(""):
                for error in file_errors:
                    if len(error) >= 4:  # Make sure the error has all components
                        line_num, col_num, message = error[0], error[1], error[2]
                        # line_num, col_num, message, code_obj = error[0], error[1], error[2], error[3]  # noqa: E501

                        severity = AnalysisSeverity.WARNING
                        if message.startswith("E"):
                            severity = AnalysisSeverity.ERROR
                        elif message.startswith("F"):
                            severity = AnalysisSeverity.CRITICAL

                        issues.append(
                            CodeIssue(
                                line=line_num,
                                column=col_num,
                                severity=severity,
                                message=message,
                                code=message.split(" ")[0],
                                source="flake8",
                            )
                        )

            flake8_app.formatter.stop()
            flake8_app.report_errors()
        except Exception as e:
            issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.ERROR,
                    message=f"Error running flake8: {e!s}",
                    source="analyzer",
                )
            )

    # Run radon for complexity metrics
    if RADON_AVAILABLE:
        try:
            # Cyclomatic Complexity
            cc_blocks = radon.complexity.cc_visit(code)
            avg_complexity = (
                sum(block.complexity for block in cc_blocks) / len(cc_blocks) if cc_blocks else 0
            )

            # Maintainability Index
            mi_score = radon.metrics.mi_visit(code, multi=True)

            metrics["cyclomatic_complexity"] = {
                "average": avg_complexity,
                "blocks": [
                    {
                        "name": block.name,
                        "complexity": block.complexity,
                        "rank": block.rank,
                        "line": block.lineno,
                    }
                    for block in cc_blocks
                ],
            }

            metrics["maintainability_index"] = mi_score

            # Flag high complexity functions
            for block in cc_blocks:
                if block.complexity > 10:
                    severity = AnalysisSeverity.WARNING
                    if block.complexity > 20:
                        severity = AnalysisSeverity.ERROR
                    if block.complexity > 30:
                        severity = AnalysisSeverity.CRITICAL

                    issues.append(
                        CodeIssue(
                            line=block.lineno,
                            severity=severity,
                            message=f"High cyclomatic complexity ({block.complexity}) in {block.name}",  # noqa: E501
                            code="R001",
                            source="radon",
                        )
                    )
        except Exception as e:
            issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.ERROR,
                    message=f"Error calculating code complexity: {e!s}",
                    source="analyzer",
                )
            )

    # Run bandit for security analysis
    if BANDIT_AVAILABLE:
        try:
            mgr = bandit_manager.BanditManager()
            mgr.discover_files([file_path])
            mgr.run_tests()

            for issue in mgr.get_issue_list():
                severity_map = {
                    bandit.constants.HIGH: AnalysisSeverity.CRITICAL,
                    bandit.constants.MEDIUM: AnalysisSeverity.ERROR,
                    bandit.constants.LOW: AnalysisSeverity.WARNING,
                }

                issues.append(
                    CodeIssue(
                        line=issue.lineno,
                        severity=severity_map.get(issue.severity, AnalysisSeverity.INFO),
                        message=issue.text,
                        code=issue.test_id,
                        source="bandit",
                    )
                )
        except Exception as e:
            issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.ERROR,
                    message=f"Error running security analysis: {e!s}",
                    source="analyzer",
                )
            )

    return {"issues": issues, "metrics": metrics}


def analyze_java_code(file_path: str, code: str) -> dict[str, Any]:
    """
    Analyze Java code using common Java analysis tools.

    Args:
        file_path: Path to the Java file
        code: Content of the file

    Returns:
        Dict with analysis results
    """
    issues = []
    metrics = {}

    # Run SpotBugs if available
    try:
        # Check if spotbugs is available
        result = subprocess.run(["spotbugs", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            # SpotBugs requires compiled classes, so this is a simplified check
            issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.INFO,
                    message="SpotBugs requires compiled classes for full analysis",
                    source="spotbugs",
                )
            )
    except FileNotFoundError:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="SpotBugs not available. Install with: "
                "apt-get install spotbugs or brew install spotbugs",
                source="analyzer",
            )
        )

    # Run PMD if available
    try:
        result = subprocess.run(
            ["pmd", "check", "-f", "text", "-d", file_path], capture_output=True, text=True
        )
        if result.returncode != 127:  # Command found
            # Parse PMD output
            for line in result.stdout.split("\n"):
                if line.strip() and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 4:
                        try:
                            line_num = int(parts[1])
                            message = ":".join(parts[3:]).strip()
                            issues.append(
                                CodeIssue(
                                    line=line_num,
                                    severity=AnalysisSeverity.WARNING,
                                    message=message,
                                    source="pmd",
                                )
                            )
                        except ValueError:
                            continue
    except FileNotFoundError:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="PMD not available. Install with: "
                "brew install pmd or download from https://pmd.github.io/",
                source="analyzer",
            )
        )

    # Run Checkstyle if available
    try:
        result = subprocess.run(
            ["checkstyle", "-f", "plain", file_path], capture_output=True, text=True
        )
        if result.returncode != 127:  # Command found
            for line in result.stdout.split("\n"):
                if "ERROR" in line or "WARN" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[1])
                            message = ":".join(parts[2:]).strip()
                            severity = (
                                AnalysisSeverity.ERROR
                                if "ERROR" in line
                                else AnalysisSeverity.WARNING
                            )
                            issues.append(
                                CodeIssue(
                                    line=line_num,
                                    severity=severity,
                                    message=message,
                                    source="checkstyle",
                                )
                            )
                        except ValueError:
                            continue
    except FileNotFoundError:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="Checkstyle not available. Install with: "
                "brew install checkstyle or download from "
                "https://checkstyle.org/",
                source="analyzer",
            )
        )

    # Basic metrics
    lines = code.split("\n")
    metrics["lines_of_code"] = len(
        [line for line in lines if line.strip() and not line.strip().startswith("//")]
    )
    metrics["comment_lines"] = len([line for line in lines if line.strip().startswith("//")])

    return {"issues": issues, "metrics": metrics}


def analyze_go_code(file_path: str, code: str) -> dict[str, Any]:
    """
    Analyze Go code using Go's built-in tools and common linters.

    Args:
        file_path: Path to the Go file
        code: Content of the file

    Returns:
        Dict with analysis results
    """
    issues = []
    metrics = {}

    # Run go vet
    try:
        result = subprocess.run(
            ["go", "vet", file_path], capture_output=True, text=True, cwd=Path(file_path).parent
        )
        if result.returncode != 127:  # Command found
            for line in result.stderr.split("\n"):
                if line.strip() and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[1])
                            message = ":".join(parts[2:]).strip()
                            issues.append(
                                CodeIssue(
                                    line=line_num,
                                    severity=AnalysisSeverity.WARNING,
                                    message=message,
                                    source="go vet",
                                )
                            )
                        except ValueError:
                            continue
    except FileNotFoundError:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="Go not installed. Install from https://golang.org/",
                source="analyzer",
            )
        )

    # Run go fmt check
    try:
        result = subprocess.run(["gofmt", "-d", file_path], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.INFO,
                    message="File is not formatted according to gofmt standards",
                    source="gofmt",
                )
            )
    except FileNotFoundError:
        pass

    # Run staticcheck if available
    try:
        result = subprocess.run(["staticcheck", file_path], capture_output=True, text=True)
        if result.returncode != 127:  # Command found
            for line in result.stdout.split("\n"):
                if line.strip() and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 4:
                        try:
                            line_num = int(parts[1])
                            message = ":".join(parts[3:]).strip()
                            issues.append(
                                CodeIssue(
                                    line=line_num,
                                    severity=AnalysisSeverity.WARNING,
                                    message=message,
                                    source="staticcheck",
                                )
                            )
                        except ValueError:
                            continue
    except FileNotFoundError:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="staticcheck not available. Install with: "
                "go install honnef.co/go/tools/cmd/staticcheck@latest",
                source="analyzer",
            )
        )

    # Run golint if available
    try:
        result = subprocess.run(["golint", file_path], capture_output=True, text=True)
        if result.returncode != 127:  # Command found
            for line in result.stdout.split("\n"):
                if line.strip() and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[1])
                            message = ":".join(parts[2:]).strip()
                            issues.append(
                                CodeIssue(
                                    line=line_num,
                                    severity=AnalysisSeverity.INFO,
                                    message=message,
                                    source="golint",
                                )
                            )
                        except ValueError:
                            continue
    except FileNotFoundError:
        issues.append(
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="golint not available. Install with: "
                "go install golang.org/x/lint/golint@latest",
                source="analyzer",
            )
        )

    # Basic metrics
    lines = code.split("\n")
    metrics["lines_of_code"] = len(
        [line for line in lines if line.strip() and not line.strip().startswith("//")]
    )
    metrics["comment_lines"] = len([line for line in lines if line.strip().startswith("//")])

    return {"issues": issues, "metrics": metrics}


def analyze_javascript_code(file_path: str, code: str) -> dict[str, Any]:  # noqa: ARG001
    """
    Analyze JavaScript code.

    Currently a placeholder for JavaScript analysis.

    Args:
        file_path: Path to the JavaScript file
        code: Content of the file

    Returns:
        Dict with analysis results
    """
    # Placeholder for JavaScript analysis
    # In a real implementation, we would integrate tools like ESLint
    return {
        "issues": [
            CodeIssue(
                severity=AnalysisSeverity.INFO,
                message="JavaScript analysis not yet implemented",
                source="analyzer",
            )
        ],
        "metrics": {},
    }


def _analyze_code(file_path: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Analyze code in a file for quality issues.

    Args:
        file_path: Path to the file to analyze.
        tool_context: The tool context from ADK.

    Returns:
        Dict containing analysis results.
    """
    try:
        if not Path(file_path).exists():
            return {"error": f"File {file_path} does not exist", "status": "Failed"}

        with Path(file_path).open(encoding="utf-8") as file:
            code = file.read()

        # Store the code in the state for the agent to access
        tool_context.state["analyzed_code"] = code
        tool_context.state["analyzed_file"] = file_path

        # Detect language
        language = detect_language(file_path)

        # Initialize result object
        result = CodeAnalysisResult(
            file_path=file_path,
            language=language,
            lines_of_code=len(code.split("\n")),
            status="Analysis complete",
        )

        # Analyze based on language
        if language == "python":
            analysis = analyze_python_code(file_path, code)
            result.issues = analysis["issues"]
            result.metrics = analysis["metrics"]
        elif language == "java":
            analysis = analyze_java_code(file_path, code)
            result.issues = analysis["issues"]
            result.metrics = analysis["metrics"]
        elif language == "go":
            analysis = analyze_go_code(file_path, code)
            result.issues = analysis["issues"]
            result.metrics = analysis["metrics"]
        elif language in ["javascript", "typescript"]:
            analysis = analyze_javascript_code(file_path, code)
            result.issues = analysis["issues"]
            result.metrics = analysis["metrics"]
        else:
            result.issues.append(
                CodeIssue(
                    severity=AnalysisSeverity.INFO,
                    message=f"Analysis for {language} is not yet supported",
                    source="analyzer",
                )
            )

        # Store analysis issues in state for other tools to use
        tool_context.state["analysis_issues"] = [issue.dict() for issue in result.issues]

        # Generate summary statistics
        issue_counts = {
            "critical": sum(1 for i in result.issues if i.severity == AnalysisSeverity.CRITICAL),
            "error": sum(1 for i in result.issues if i.severity == AnalysisSeverity.ERROR),
            "warning": sum(1 for i in result.issues if i.severity == AnalysisSeverity.WARNING),
            "info": sum(1 for i in result.issues if i.severity == AnalysisSeverity.INFO),
        }
        result.metrics["issue_summary"] = issue_counts

        return result.dict()
    except Exception as e:
        return {"error": f"Error analyzing file: {e!s}", "status": "Failed"}


# Define the tool using FunctionTool
analyze_code_tool = FunctionTool(func=_analyze_code)


def get_issues_by_severity(
    tool_context: ToolContext, severity: Optional[str] = None
) -> dict[str, Any]:
    """
    Retrieves code analysis issues filtered by severity.

    Args:
        tool_context: The tool context from ADK.
        severity: Optional severity level to filter by (critical, error, warning, info)

    Returns:
        Dict containing filtered issues list.
    """
    # Get all issues
    issues = tool_context.state.get("analysis_issues", [])

    # If no severity specified, return all issues
    if not severity:
        return {"issues": issues}

    # Filter by severity
    filtered_issues = [
        issue for issue in issues if issue.get("severity", "").lower() == severity.lower()
    ]

    return {
        "issues": filtered_issues,
        "count": len(filtered_issues),
        "total_issues": len(issues),
        "severity": severity,
    }


# Define additional tools to work with analysis results
get_analysis_issues_by_severity_tool = FunctionTool(func=get_issues_by_severity)


def suggest_fixes(tool_context: ToolContext) -> dict[str, Any]:
    """
    Analyzes issues and suggests fixes based on common patterns.

    Args:
        tool_context: The tool context from ADK.

    Returns:
        Dict containing suggested fixes for detected issues.
    """
    issues = tool_context.state.get("analysis_issues", [])

    suggested_fixes = []

    # Common patterns and their fixes
    for issue in issues:
        code = issue.get("code", "")
        message = issue.get("message", "")
        source = issue.get("source", "")
        suggestion = None

        # Python-specific suggestions
        if source in ["ruff", "pylint", "flake8"]:
            # Unused import suggestions
            if "unused import" in message.lower():
                suggestion = f"Remove the unused import at line {issue.get('line')}"

            # Undefined variable suggestions
            elif "undefined variable" in message.lower():
                var_name = message.split("'")[1] if "'" in message else ""
                suggestion = f"Define variable '{var_name}' before use or check for typo"

            # Line too long
            elif code == "E501" or "line too long" in message.lower():
                suggestion = f"Break the long line at {issue.get('line')} into multiple lines"

        # Java-specific suggestions
        elif source in ["pmd", "checkstyle", "spotbugs"]:
            if "unused" in message.lower():
                suggestion = f"Remove unused code at line {issue.get('line')}"
            elif "magic number" in message.lower():
                suggestion = (
                    f"Replace magic number with a named constant at line {issue.get('line')}"
                )

        # Go-specific suggestions
        elif source in ["go vet", "staticcheck", "golint"]:
            if "not formatted" in message.lower():
                analyzed_file = tool_context.state.get("analyzed_file")
                suggestion = f"Run 'go fmt {analyzed_file}' to format the file"
            elif "exported" in message.lower() and "comment" in message.lower():
                suggestion = (
                    f"Add a comment for the exported function/type at line {issue.get('line')}"
                )

        # Complexity suggestions (universal)
        if "complexity" in message.lower():
            suggestion = (
                f"Refactor the complex function at line {issue.get('line')} into smaller functions"
            )

        if suggestion:
            suggested_fixes.append({"issue": issue, "suggestion": suggestion})

    return {
        "suggested_fixes": suggested_fixes,
        "count": len(suggested_fixes),
        "analyzed_file": tool_context.state.get("analyzed_file"),
    }


# Define a tool for suggesting fixes
suggest_code_fixes_tool = FunctionTool(func=suggest_fixes)
