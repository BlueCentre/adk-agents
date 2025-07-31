"""Tool output parsers for the Software Engineer Agent workflows."""

import json
import logging
import re

logger = logging.getLogger(__name__)


class ToolOutputParser:
    """Base class for parsing external tool outputs."""

    def parse(self, stdout: str, stderr: str = "") -> list[dict]:
        """Parse tool output and return standardized issue format."""
        raise NotImplementedError


class BanditOutputParser(ToolOutputParser):
    """Parser for bandit security analysis output."""

    def parse(self, stdout: str, _stderr: str = "") -> list[dict]:
        """Parse bandit output into standardized format."""
        issues = []
        if not stdout.strip():
            return issues

        try:
            bandit_output = json.loads(stdout)
            results = bandit_output.get("results", [])

            for issue in results:
                # Map bandit confidence and severity
                confidence = issue.get("issue_confidence", "MEDIUM").lower()
                issue_severity = issue.get("issue_severity", "MEDIUM").lower()

                # Combine confidence and severity for our severity mapping
                severity = "medium"
                if issue_severity == "high" or confidence == "high":
                    severity = "high"
                elif issue_severity == "low" and confidence == "low":
                    severity = "low"

                issues.append(
                    {
                        "type": "security",
                        "severity": severity,
                        "message": issue.get("issue_text", "Security issue detected"),
                        "line": issue.get("line_number"),
                        "column": issue.get("col_offset"),
                        "code": issue.get("test_id"),
                        "tool": "bandit",
                    }
                )
        except json.JSONDecodeError:
            logger.warning("Failed to parse bandit JSON output, attempting line parsing")
            issues = self._parse_line_format(stdout)

        return issues

    def _parse_line_format(self, output: str) -> list[dict]:
        """Fallback parser for bandit line format output."""
        issues = []
        current_issue = None

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Look for issue headers like ">> Issue: [B123:test_name]"
            issue_match = re.match(r">>\s*Issue:\s*\[([^\]]+)\]", line)
            if issue_match:
                if current_issue:
                    issues.append(current_issue)
                current_issue = {
                    "type": "security",
                    "severity": "medium",
                    "message": "Security issue detected",
                    "line": None,
                    "column": None,
                    "code": issue_match.group(1),
                    "tool": "bandit",
                }
            elif current_issue and line.startswith("Severity:"):
                severity_text = line.replace("Severity:", "").strip().lower()
                if severity_text == "high":
                    current_issue["severity"] = "high"
                elif severity_text == "low":
                    current_issue["severity"] = "low"
            elif current_issue and line.startswith("Location:"):
                # Try to extract line number from location
                location_match = re.search(r":(\d+):", line)
                if location_match:
                    current_issue["line"] = int(location_match.group(1))

        if current_issue:
            issues.append(current_issue)

        return issues


class MypyOutputParser(ToolOutputParser):
    """Parser for mypy type checker output."""

    def parse(self, stdout: str, _stderr: str = "") -> list[dict]:
        """Parse mypy output into standardized format."""
        issues = []
        for line in stdout.split("\n"):
            if line.strip() and ":" in line:
                # Parse mypy output format: file:line:column: severity: message [code]
                match = re.match(
                    r".*:(\d+):(\d*):?\s*(error|warning|note):\s*(.+?)(?:\s*\[([^\]]+)\])?$",
                    line,
                )
                if match:
                    line_num, column, severity_text, message = match.groups()[:4]
                    error_code = (
                        match.group(5) if len(match.groups()) > 4 and match.group(5) else None
                    )

                    # Map mypy severity to our levels
                    severity = "medium"
                    if severity_text == "error":
                        severity = "high"
                    elif severity_text == "note":
                        severity = "low"

                    issues.append(
                        {
                            "type": "type_checking",
                            "severity": severity,
                            "message": message,
                            "line": int(line_num) if line_num else None,
                            "column": int(column) if column else None,
                            "code": error_code,
                            "tool": "mypy",
                        }
                    )
        return issues


class PytestOutputParser:
    """Parser for pytest test runner output."""

    def parse(self, stdout: str, stderr: str = "") -> dict:
        """Parse pytest output to extract comprehensive test results."""

        def get_count(status: str, text: str) -> int:
            """Searches for patterns like '1 passed', '2 failed', etc."""
            match = re.search(rf"(\d+)\s+{status}", text)
            return int(match.group(1)) if match else 0

        full_output = stdout + "\n" + stderr

        # Extract counts for all relevant pytest statuses
        tests_passed = get_count("passed", full_output)
        tests_failed = get_count("failed", full_output)
        test_errors = get_count("error", full_output)
        tests_skipped = get_count("skipped", full_output)
        tests_xfailed = get_count("xfailed", full_output)
        tests_xpassed = get_count("xpassed", full_output)

        # Consolidate failures and errors into a single 'failed' count
        total_failed = tests_failed + test_errors

        # Calculate total tests run by summing all outcomes
        tests_run = tests_passed + total_failed + tests_skipped + tests_xfailed + tests_xpassed

        return {
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": total_failed,
            "tests_skipped": tests_skipped,
            "tests_xfailed": tests_xfailed,
            "tests_xpassed": tests_xpassed,
            "output": full_output,
            "pytest_available": True,
        }


class RuffOutputParser(ToolOutputParser):
    """Parser for ruff linting tool output."""

    def parse(self, stdout: str, _stderr: str = "") -> list[dict]:
        """Parse ruff JSON output into standardized format."""
        issues = []
        if not stdout.strip():
            return issues

        try:
            ruff_output = json.loads(stdout)
            for issue in ruff_output:
                # Map ruff severity to our severity levels
                severity = "medium"  # Default for ruff issues
                if issue.get("code", "").startswith("E"):
                    severity = "high"  # Error codes are high severity
                elif issue.get("code", "").startswith("W"):
                    severity = "low"  # Warning codes are low severity

                issues.append(
                    {
                        "type": "style",
                        "severity": severity,
                        "message": issue.get("message", "Ruff issue"),
                        "line": issue.get("location", {}).get("row"),
                        "column": issue.get("location", {}).get("column"),
                        "code": issue.get("code"),
                        "tool": "ruff",
                    }
                )
        except json.JSONDecodeError:
            logger.warning("Failed to parse ruff JSON output, attempting fallback parsing")
            # Fallback: try to parse line-by-line format
            issues = self._parse_line_format(stdout)

        return issues

    def _parse_line_format(self, output: str) -> list[dict]:
        """Fallback parser for ruff line format output."""
        issues = []
        for line in output.split("\n"):
            if ":" in line and line.strip():
                # Basic parsing for file:line:column: code message format
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    try:
                        line_num = int(parts[1])
                        column = int(parts[2]) if parts[2].isdigit() else None
                        message = parts[3].strip() if len(parts) > 3 else "Ruff issue"
                        issues.append(
                            {
                                "type": "style",
                                "severity": "medium",
                                "message": message,
                                "line": line_num,
                                "column": column,
                                "code": None,
                                "tool": "ruff",
                            }
                        )
                    except ValueError:
                        continue
        return issues
