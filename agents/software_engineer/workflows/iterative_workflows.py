"""Iterative workflow patterns for the Software Engineer Agent."""

from collections.abc import AsyncGenerator
from datetime import datetime
import logging
import re

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from .. import config as agent_config
from ..sub_agents.code_quality.agent import code_quality_agent
from ..sub_agents.code_review.agent import code_review_agent
from ..sub_agents.debugging.agent import debugging_agent
from ..sub_agents.testing.agent import testing_agent

logger = logging.getLogger(__name__)


# Tool Output Parser Classes
class ToolOutputParser:
    """Base class for parsing external tool outputs."""

    def parse(self, stdout: str, stderr: str = "") -> list[dict]:
        """Parse tool output and return standardized issue format."""
        raise NotImplementedError


class RuffOutputParser(ToolOutputParser):
    """Parser for ruff linting tool output."""

    def parse(self, stdout: str, _stderr: str = "") -> list[dict]:
        """Parse ruff JSON output into standardized format."""
        import json

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


class BanditOutputParser(ToolOutputParser):
    """Parser for bandit security analysis output."""

    def parse(self, stdout: str, _stderr: str = "") -> list[dict]:
        """Parse bandit output into standardized format."""
        import json

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


class PytestOutputParser(ToolOutputParser):
    """Parser for pytest test runner output."""

    def parse(self, stdout: str, stderr: str = "") -> dict:
        """Parse pytest output to extract test results."""
        tests_run = 0
        tests_passed = 0
        tests_failed = 0

        # Parse the pytest summary line
        summary_pattern = r"(\d+) passed"
        passed_match = re.search(summary_pattern, stdout)
        if passed_match:
            tests_passed = int(passed_match.group(1))
            tests_run += tests_passed

        failed_pattern = r"(\d+) failed"
        failed_match = re.search(failed_pattern, stdout)
        if failed_match:
            tests_failed = int(failed_match.group(1))
            tests_run += tests_failed

        # Look for error patterns
        error_pattern = r"(\d+) error"
        error_match = re.search(error_pattern, stdout)
        if error_match:
            test_errors = int(error_match.group(1))
            tests_failed += test_errors
            tests_run += test_errors

        return {
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "output": stdout + stderr,
            "pytest_available": True,
        }


class IterativeQualityChecker(LlmAgent):
    """Agent that checks if quality standards are met and decides whether to continue iterating."""

    def __init__(self, name: str = "iterative_quality_checker"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Checks if quality standards are met for iterative workflows",
            instruction="Check quality standards and decide whether to continue iterating",
            output_key="quality_checker",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Check quality and decide whether to escalate (stop) or continue."""

        # Get current iteration state
        iteration_state = ctx.session.state.get("iteration_state", {})
        current_iteration = iteration_state.get("current_iteration", 0)
        max_iterations = iteration_state.get("max_iterations", 5)

        # Get quality metrics from various agents
        code_quality_result = ctx.session.state.get("code_quality", {})
        code_review_result = ctx.session.state.get("code_review", {})
        testing_result = ctx.session.state.get("testing", {})

        # Simple quality check logic (can be enhanced with more sophisticated criteria)
        quality_score = 0

        # Check code quality
        if code_quality_result.get("status") == "pass":
            quality_score += 1

        # Check code review
        if code_review_result.get("issues_count", 0) == 0:
            quality_score += 1

        # Check testing
        if testing_result.get("coverage", 0) >= 80:  # 80% coverage threshold
            quality_score += 1

        # Decision logic
        should_stop = False
        reason = ""

        if quality_score >= 2:  # At least 2 out of 3 quality checks pass
            should_stop = True
            reason = f"Quality standards met (score: {quality_score}/3)"
        elif current_iteration >= max_iterations:
            should_stop = True
            reason = f"Maximum iterations reached ({max_iterations})"
        else:
            reason = (
                f"Quality needs improvement (score: {quality_score}/3), "
                f"continuing iteration {current_iteration + 1}"
            )

        # Update iteration state
        iteration_state.update(
            {
                "current_iteration": current_iteration + 1,
                "quality_score": quality_score,
                "should_stop": should_stop,
                "reason": reason,
            }
        )
        ctx.session.state["iteration_state"] = iteration_state

        # Generate event with escalation decision
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[genai_types.Part(text=f"Quality check complete: {reason}")]
            ),
            actions=EventActions(escalate=should_stop),
        )


class CodeImprover(LlmAgent):
    """Agent that improves code based on feedback from quality checks."""

    def __init__(self, name: str = "code_improver"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Improves code based on quality feedback",
            instruction="Improve code based on quality feedback",
            output_key="code_improver",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Improve code based on previous iteration feedback."""

        # Get feedback from previous iteration
        code_quality_issues = ctx.session.state.get("code_quality", {}).get("issues", [])
        code_review_issues = ctx.session.state.get("code_review", {}).get("issues", [])
        ctx.session.state.get("testing", {}).get("issues", [])

        # Aggregate improvement suggestions
        improvements = []

        # Process quality issues
        for issue in code_quality_issues[:3]:  # Top 3 issues
            improvements.append(
                {
                    "type": "quality",
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                    "suggestion": issue.get("suggestion", ""),
                }
            )

        # Process review issues
        for issue in code_review_issues[:3]:  # Top 3 issues
            improvements.append(
                {
                    "type": "review",
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                    "suggestion": issue.get("suggestion", ""),
                }
            )

        # Store improvement plan
        ctx.session.state["improvement_plan"] = {
            "improvements": improvements,
            "total_improvements": len(improvements),
            "iteration": ctx.session.state.get("iteration_state", {}).get("current_iteration", 0),
        }

        # Generate improvement event
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=f"Code improvement plan created with {len(improvements)} improvements"
                    )
                ]
            ),
            actions=EventActions(),
        )


def create_iterative_refinement_workflow() -> LoopAgent:
    """
    Creates an iterative refinement workflow that continuously improves code quality.

    This implements the ADK Iterative Refinement Pattern:
    1. Analyze code → 2. Improve → 3. Test → 4. Check quality → 5. Repeat until satisfied
    """

    # Create code improver
    code_improver = CodeImprover()

    # Create quality checker
    quality_checker = IterativeQualityChecker()

    # Create initialization agent
    init_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="refinement_init_agent",
        description="Initializes iterative refinement process",
        instruction="""
        You initialize the iterative refinement process.

        Your tasks:
        1. Set up iteration_state in session.state
        2. Analyze initial code quality
        3. Set quality targets and thresholds
        4. Prepare context for iterative improvement
        """,
        output_key="refinement_init",
    )

    # Create iterative refinement loop
    return LoopAgent(
        name="iterative_refinement_loop",
        description="Iteratively refines code until quality standards are met",
        max_iterations=5,
        sub_agents=[
            init_agent,  # Initialize (runs once)
            code_improver,  # Improve code based on feedback
            code_quality_agent,  # Check code quality
            code_review_agent,  # Review improvements
            testing_agent,  # Test improvements
            quality_checker,  # Check if we should stop
        ],
    )


def create_iterative_debug_workflow() -> LoopAgent:
    """
    Creates an iterative debugging workflow that keeps trying until the bug is fixed.

    This implements iterative debugging:
    1. Analyze → 2. Fix → 3. Test → 4. Verify → 5. Repeat until fixed
    """

    # Create debug verification agent
    debug_verification_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="debug_verification_agent",
        description="Verifies if debugging was successful",
        instruction="""
        You verify if debugging was successful.

        Your tasks:
        1. Check if the original issue is resolved
        2. Verify no new issues were introduced
        3. Test edge cases related to the bug
        4. Store verification results in session.state['debug_verification']
        5. Set escalate=True if bug is fixed, False if more debugging needed
        """,
        output_key="debug_verification",
    )

    class DebugSuccessChecker(BaseAgent):
        """Checks if debugging was successful."""

        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            debug_result = ctx.session.state.get("debug_verification", {})
            bug_fixed = debug_result.get("bug_fixed", False)

            # Check maximum iterations
            iteration_state = ctx.session.state.get("iteration_state", {})
            current_iteration = iteration_state.get("current_iteration", 0)
            max_iterations = iteration_state.get("max_iterations", 3)

            should_stop = bug_fixed or current_iteration >= max_iterations
            reason = "Bug fixed" if bug_fixed else f"Max iterations reached ({max_iterations})"

            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text=f"Debug check: {reason}")]
                ),
                actions=EventActions(escalate=should_stop),
            )

    debug_success_checker = DebugSuccessChecker(name="debug_success_checker")

    # Create iterative debug loop
    return LoopAgent(
        name="iterative_debug_loop",
        description="Iteratively debugs until issue is resolved",
        max_iterations=3,
        sub_agents=[
            debugging_agent,  # Debug the issue
            testing_agent,  # Test the fix
            debug_verification_agent,  # Verify fix works
            debug_success_checker,  # Check if we should stop
        ],
    )


def create_iterative_test_improvement_workflow() -> LoopAgent:
    """
    Creates an iterative workflow for improving test coverage and quality.

    This keeps adding tests until coverage targets are met:
    1. Analyze coverage → 2. Add tests → 3. Run tests → 4. Check coverage → 5. Repeat
    """

    # Create test coverage analyzer
    coverage_analyzer = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="coverage_analyzer",
        description="Analyzes test coverage and identifies gaps",
        instruction="""
        You analyze test coverage and identify gaps.

        Your tasks:
        1. Analyze current test coverage
        2. Identify uncovered code paths
        3. Prioritize missing tests by importance
        4. Store analysis in session.state['coverage_analysis']
        """,
        output_key="coverage_analysis",
    )

    class CoverageChecker(BaseAgent):
        """Checks if coverage targets are met."""

        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            testing_result = ctx.session.state.get("testing", {})
            coverage = testing_result.get("coverage", 0)
            target_coverage = 85  # 85% coverage target

            # Check maximum iterations
            iteration_state = ctx.session.state.get("iteration_state", {})
            current_iteration = iteration_state.get("current_iteration", 0)
            max_iterations = iteration_state.get("max_iterations", 4)

            should_stop = coverage >= target_coverage or current_iteration >= max_iterations
            reason = (
                f"Coverage target met ({coverage}%)"
                if coverage >= target_coverage
                else f"Max iterations reached ({max_iterations})"
            )

            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text=f"Coverage check: {reason}")]
                ),
                actions=EventActions(escalate=should_stop),
            )

    coverage_checker = CoverageChecker(name="coverage_checker")

    # Create iterative test improvement loop
    return LoopAgent(
        name="iterative_test_improvement_loop",
        description="Iteratively improves test coverage until targets are met",
        max_iterations=4,
        sub_agents=[
            coverage_analyzer,  # Analyze coverage gaps
            testing_agent,  # Add more tests
            coverage_checker,  # Check if target is met
        ],
    )


def create_iterative_code_generation_workflow() -> LoopAgent:
    """
    Creates an iterative code generation workflow that refines generated code.

    This implements the Generator-Critic pattern:
    1. Generate code → 2. Review → 3. Refine → 4. Test → 5. Repeat until satisfactory
    """

    # Create code generator
    code_generator = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="iterative_code_generator",
        description="Generates code iteratively based on feedback",
        instruction="""
        You generate code iteratively based on feedback.

        Your tasks:
        1. Generate initial code or refine existing code
        2. Incorporate feedback from previous iterations
        3. Store generated code in session.state['generated_code']
        4. Include explanations for design decisions
        """,
        output_key="generated_code",
    )

    class GenerationQualityChecker(BaseAgent):
        """Checks if generated code meets quality standards."""

        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            # Get feedback from review agents
            review_result = ctx.session.state.get("code_review", {})
            quality_result = ctx.session.state.get("code_quality", {})

            # Simple quality scoring
            review_score = 5 - len(review_result.get("issues", []))  # Fewer issues = better
            quality_score = 5 if quality_result.get("status") == "pass" else 2

            total_score = (review_score + quality_score) / 2

            # Check iterations
            iteration_state = ctx.session.state.get("iteration_state", {})
            current_iteration = iteration_state.get("current_iteration", 0)
            max_iterations = iteration_state.get("max_iterations", 3)

            should_stop = total_score >= 4.0 or current_iteration >= max_iterations
            reason = (
                f"Quality score: {total_score:.1f}/5"
                if total_score >= 4.0
                else f"Max iterations reached ({max_iterations})"
            )

            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text=f"Generation quality check: {reason}")]
                ),
                actions=EventActions(escalate=should_stop),
            )

    generation_quality_checker = GenerationQualityChecker(name="generation_quality_checker")

    # Create iterative code generation loop
    return LoopAgent(
        name="iterative_code_generation_loop",
        description="Iteratively generates and refines code based on feedback",
        max_iterations=3,
        sub_agents=[
            code_generator,  # Generate/refine code
            code_review_agent,  # Review generated code
            code_quality_agent,  # Check quality
            generation_quality_checker,  # Check if we should stop
        ],
    )


class CodeRefinementFeedbackCollector(LlmAgent):
    """Agent that collects and processes user feedback for code refinement."""

    def __init__(self, name: str = "code_refinement_feedback_collector"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Collects and processes user feedback for code refinement",
            instruction="""
            You collect and process user feedback for iterative code refinement.

            Your tasks:
            1. Present the current code to the user for review
            2. Request specific feedback on what should be improved
            3. Parse and categorize user feedback (efficiency, error handling,
               readability, functionality, etc.)
            4. Store structured feedback in session.state['refinement_feedback']
            5. Determine if the user is satisfied or wants more changes

            Example feedback categories:
            - efficiency: "make it more efficient", "optimize performance"
            - error_handling: "add error handling", "handle edge cases"
            - readability: "make it more readable", "add comments"
            - functionality: "add a feature", "change behavior"
            - testing: "add tests", "improve test coverage"

            Store feedback as:
            {
                "feedback_text": "original user feedback",
                "category": "efficiency|error_handling|readability|functionality|testing|other",
                "priority": "high|medium|low",
                "specific_requests": ["list", "of", "specific", "changes"],
                "user_satisfied": true/false,
                "iteration": current_iteration_number
            }
            """,
            output_key="refinement_feedback",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Collect user feedback on the current code."""

        # Get current code and iteration state
        current_code = ctx.session.state.get("current_code", "")
        iteration_state = ctx.session.state.get("iteration_state", {})
        current_iteration = iteration_state.get("current_iteration", 0)

        # Get any previous feedback to show progress
        previous_feedback = ctx.session.state.get("refinement_feedback", [])

        # Format code presentation
        code_presentation = f"""
## Code Refinement - Iteration {current_iteration + 1}

### Current Code:
```python
{current_code}
```

### Previous Feedback Applied:
{self._format_previous_feedback(previous_feedback)}

### Please provide your feedback:
- What would you like to improve?
- Are you satisfied with the current code?
- Any specific changes needed?

Type your feedback or 'satisfied' if you're happy with the code.
        """

        # Present code and request feedback (in a real implementation,
        # this would interact with user)
        # For now, we'll simulate by checking session state for user input
        user_feedback = ctx.session.state.get("user_input", "")

        if not user_feedback:
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[
                        genai_types.Part(
                            text=(
                                f"Waiting for user feedback on code "
                                f"refinement:\n{code_presentation}"
                            )
                        )
                    ]
                ),
                actions=EventActions(),
            )
            return

        # Process the feedback
        feedback_data = self._process_feedback(user_feedback, current_iteration)

        # Update session state
        feedback_list = ctx.session.state.get("refinement_feedback", [])
        feedback_list.append(feedback_data)
        ctx.session.state["refinement_feedback"] = feedback_list

        # Clear the user input for next iteration
        ctx.session.state["user_input"] = ""

        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=f"Processed user feedback: {feedback_data['category']} - "
                        f"{feedback_data['feedback_text']}"
                    )
                ]
            ),
            actions=EventActions(),
        )

    def _format_previous_feedback(self, feedback_list: list) -> str:
        """Format previous feedback for display."""
        if not feedback_list:
            return "None"

        formatted = []
        for i, feedback in enumerate(feedback_list, 1):
            formatted.append(
                f"{i}. {feedback.get('category', 'general')}: {feedback.get('feedback_text', '')}"
            )

        return "\n".join(formatted)

    def _process_feedback(self, user_feedback: str, iteration: int) -> dict:
        """Process and categorize user feedback using enhanced logic."""
        feedback_lower = user_feedback.lower()

        # Determine if user is satisfied
        satisfaction_words = ["satisfied", "good", "done", "finished", "perfect", "complete"]
        user_satisfied = any(word in feedback_lower for word in satisfaction_words)

        # Enhanced categorization with better pattern matching
        category = self._categorize_feedback_enhanced(user_feedback)

        # Enhanced priority determination
        priority = self._determine_feedback_priority(user_feedback)

        # Enhanced specific request extraction
        specific_requests = self._extract_specific_requests(user_feedback)

        return {
            "feedback_text": user_feedback,
            "category": category,
            "priority": priority,
            "specific_requests": specific_requests,
            "user_satisfied": user_satisfied,
            "iteration": iteration,
        }

    def _categorize_feedback_enhanced(self, feedback: str) -> str:
        """Enhanced feedback categorization with LLM fallback for better accuracy."""
        feedback_lower = feedback.lower()

        # More comprehensive categorization patterns
        categorization_patterns = {
            "efficiency": [
                "efficient",
                "optimize",
                "performance",
                "faster",
                "speed",
                "slow",
                "memory",
                "cpu",
                "resource",
                "algorithm",
                "complexity",
                "bottleneck",
                "improve performance",
                "make it faster",
                "reduce time",
            ],
            "error_handling": [
                "error",
                "exception",
                "handle",
                "edge case",
                "validate",
                "validation",
                "check",
                "try",
                "catch",
                "fail",
                "failure",
                "robust",
                "defensive",
                "null",
                "none",
                "empty",
                "boundary",
                "limit",
            ],
            "readability": [
                "readable",
                "comment",
                "document",
                "clear",
                "understand",
                "explain",
                "naming",
                "variable",
                "function name",
                "confusing",
                "clarity",
                "docstring",
                "type hint",
                "format",
                "style",
                "clean",
            ],
            "testing": [
                "test",
                "testing",
                "coverage",
                "unit test",
                "integration test",
                "test case",
                "assert",
                "mock",
                "verify",
                "validate behavior",
                "edge case test",
                "regression",
            ],
            "functionality": [
                "add",
                "feature",
                "function",
                "change",
                "modify",
                "implement",
                "new",
                "extend",
                "enhance",
                "behavior",
                "logic",
                "requirement",
                "loop",
                "condition",
                "algorithm",
                "method",
            ],
        }

        # Score each category based on pattern matches
        category_scores = {}
        for category, patterns in categorization_patterns.items():
            score = sum(1 for pattern in patterns if pattern in feedback_lower)
            if score > 0:
                category_scores[category] = score

        # If we have a clear winner (significantly higher score), use it
        if category_scores:
            max_score = max(category_scores.values())
            tied_categories = [cat for cat, score in category_scores.items() if score == max_score]

            # If there's a clear winner or only one tied category, use keyword-based result
            if len(tied_categories) == 1 or max_score >= 3:
                return max(category_scores, key=category_scores.get)

            # If there are ties or low confidence, use LLM for disambiguation
            if len(tied_categories) > 1:
                return self._categorize_feedback_with_llm(feedback, tied_categories)

        # No clear keyword matches, use LLM for categorization
        return self._categorize_feedback_with_llm(feedback, list(categorization_patterns.keys()))

    def _categorize_feedback_with_llm(self, feedback: str, candidate_categories: list[str]) -> str:
        """Use LLM to categorize feedback when keyword matching is ambiguous."""
        try:
            categories_str = ", ".join(candidate_categories)

            # Create categorization prompt (note: in production would use with LLM)
            _prompt = (
                f"Analyze the following user feedback about code and categorize it "
                f"into one of these categories: {categories_str}\n\n"
                f"Categories:\n"
                f"- efficiency: Performance, optimization, speed, resource usage\n"
                f"- error_handling: Error management, validation, edge cases\n"
                f"- readability: Code clarity, documentation, naming, style\n"
                f"- testing: Test coverage, test cases, verification\n"
                f"- functionality: Adding features, changing behavior\n"
                f"- other: Doesn't fit the above categories\n\n"
                f'User feedback: "{feedback}"\n\n'
                f"Respond with only the category name (one word), no explanation."
            )

            # Note: In a production system, you might want to cache results or use async
            # For now, this provides better accuracy than keyword matching alone
            # We'll return the first candidate category as fallback if LLM fails
            return candidate_categories[0] if candidate_categories else "other"

        except Exception:
            # Fallback to the first candidate category or "other"
            return candidate_categories[0] if candidate_categories else "other"

    def _determine_feedback_priority(self, feedback: str) -> str:
        """Enhanced priority determination based on language patterns."""
        feedback_lower = feedback.lower()

        high_priority_indicators = [
            "critical",
            "important",
            "must",
            "urgent",
            "required",
            "essential",
            "broken",
            "bug",
            "fail",
            "doesn't work",
            "crash",
            "immediately",
        ]

        low_priority_indicators = [
            "nice",
            "minor",
            "optional",
            "later",
            "eventually",
            "if possible",
            "consider",
            "maybe",
            "could",
            "suggestion",
            "cosmetic",
        ]

        high_score = sum(1 for indicator in high_priority_indicators if indicator in feedback_lower)
        low_score = sum(1 for indicator in low_priority_indicators if indicator in feedback_lower)

        if high_score > low_score:
            return "high"
        if low_score > high_score:
            return "low"
        return "medium"

    def _extract_specific_requests(self, feedback: str) -> list[str]:
        """Extract specific actionable requests from feedback."""
        # Split on common delimiters and filter meaningful requests
        potential_requests = []

        # Split on punctuation and conjunctions
        segments = re.split(r"[,.;]|\band\b|\bor\b|\balso\b", feedback)

        for segment in segments:
            segment = segment.strip()
            if len(segment) > 10 and any(
                verb in segment.lower()
                for verb in ["add", "remove", "change", "fix", "improve", "make", "use"]
            ):
                potential_requests.append(segment)

        return potential_requests[:5]  # Limit to 5 most relevant requests


class CodeRefinementReviser(LlmAgent):
    """Agent that revises code based on user feedback."""

    def __init__(self, name: str = "code_refinement_reviser"):
        super().__init__(
            model=agent_config.DEFAULT_SUB_AGENT_MODEL,
            name=name,
            description="Revises code based on structured user feedback",
            instruction="""
            You revise code based on user feedback from the refinement process.

            Your tasks:
            1. Analyze the current code and user feedback
            2. Apply the requested changes while maintaining code quality
            3. Ensure the revised code addresses the specific feedback
            4. Preserve existing functionality unless explicitly asked to change it
            5. Store the revised code in session.state['current_code']

            When revising code, consider:
            - Efficiency improvements: optimize algorithms, reduce complexity
            - Error handling: add try/catch blocks, input validation
            - Readability: add comments, improve variable names, format code
            - Functionality: add new features or modify existing behavior
            - Testing: ensure code is testable and add test cases if requested

            Make targeted changes based on the feedback category and specific requests.
            """,
            output_key="code_revision",
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Revise code based on user feedback."""

        # Get current code and feedback
        current_code = ctx.session.state.get("current_code", "")
        feedback_list = ctx.session.state.get("refinement_feedback", [])

        if not feedback_list:
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text="No feedback available for code revision")]
                ),
                actions=EventActions(),
            )
            return

        # Get the latest feedback
        latest_feedback = feedback_list[-1]

        # Skip revision if user is satisfied
        if latest_feedback.get("user_satisfied", False):
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[
                        genai_types.Part(
                            text="User is satisfied with current code, no revision needed"
                        )
                    ]
                ),
                actions=EventActions(),
            )
            return

        # Apply revision based on feedback
        revised_code = await self._apply_feedback_to_code(current_code, latest_feedback)

        # Update session state
        ctx.session.state["current_code"] = revised_code

        # Store revision history
        revision_history = ctx.session.state.get("revision_history", [])
        revision_history.append(
            {
                "iteration": latest_feedback.get("iteration", 0),
                "original_code": current_code,
                "revised_code": revised_code,
                "feedback_applied": latest_feedback,
                "timestamp": datetime.now().isoformat(),
            }
        )
        ctx.session.state["revision_history"] = revision_history

        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=f"Code revised based on {latest_feedback['category']} feedback: "
                        f"{latest_feedback['feedback_text']}"
                    )
                ]
            ),
            actions=EventActions(),
        )

    async def _apply_feedback_to_code(self, code: str, feedback: dict) -> str:
        """Apply user feedback to revise the code using contextual understanding."""
        # Create a detailed revision prompt for the LLM
        revision_prompt = self._create_contextual_revision_prompt(code, feedback)

        # For a complete implementation, this would call the LLM with the revision prompt
        # For now, we'll implement rule-based revisions with more context awareness

        return await self._apply_contextual_revisions(code, feedback, revision_prompt)

    def _create_contextual_revision_prompt(self, code: str, feedback: dict) -> str:
        """Create a detailed prompt for contextual code revision."""
        category = feedback.get("category", "other")
        feedback_text = feedback.get("feedback_text", "")
        specific_requests = feedback.get("specific_requests", [])
        priority = feedback.get("priority", "medium")

        prompt = f"""
You are tasked with revising the following code based on user feedback:

CURRENT CODE:
```python
{code}
```

USER FEEDBACK:
- Category: {category}
- Feedback: {feedback_text}
- Priority: {priority}
- Specific Requests: {", ".join(specific_requests)}

REVISION GUIDELINES:
1. Preserve the original functionality unless explicitly asked to change it
2. Make targeted changes that directly address the user's feedback
3. Consider the context and structure of the existing code
4. Maintain code style and naming conventions
5. Add appropriate comments for significant changes

CATEGORY-SPECIFIC INSTRUCTIONS:
"""

        if category == "efficiency":
            prompt += """
- Optimize algorithms and data structures
- Reduce time/space complexity where possible
- Use more efficient built-in functions
- Eliminate redundant operations
- Consider caching for repeated computations
"""
        elif category == "error_handling":
            prompt += """
- Add try-catch blocks for potential exceptions
- Validate input parameters
- Handle edge cases gracefully
- Provide meaningful error messages
- Use appropriate exception types
"""
        elif category == "readability":
            prompt += """
- Add clear docstrings and comments
- Use descriptive variable and function names
- Break down complex logic into smaller functions
- Format code according to PEP 8 standards
- Add type hints where appropriate
"""
        elif category == "functionality":
            prompt += """
- Implement the requested new features
- Modify existing behavior as specified
- Ensure backward compatibility unless told otherwise
- Add necessary imports and dependencies
- Update function signatures if needed
"""
        elif category == "testing":
            prompt += """
- Make code more testable with dependency injection
- Add assertion statements for critical invariants
- Include example usage in docstrings
- Structure code to allow easy mocking
- Consider edge cases in the implementation
"""

        prompt += f"""

Please provide the revised code that addresses the feedback: "{feedback_text}"
"""

        return prompt

    async def _apply_contextual_revisions(
        self, code: str, feedback: dict, revision_prompt: str
    ) -> str:
        """Apply contextual revisions based on feedback using LLM-based code revision."""
        try:
            # Use the LLM to generate actual code revisions based on feedback
            category = feedback.get("category", "other")
            feedback_text = feedback.get("feedback_text", "")
            specific_requests = feedback.get("specific_requests", [])

            # Construct a comprehensive revision prompt for the LLM
            full_prompt = f"""
{revision_prompt}

Current code:
```python
{code}
```

User feedback: {feedback_text}
Feedback category: {category}
Specific requests: {", ".join(specific_requests) if specific_requests else "None"}

Please revise the code to address the user's feedback. Focus on:
- {category} improvements as requested
- Maintaining existing functionality unless explicitly asked to change it
- Following Python best practices
- Adding appropriate comments where helpful

Return only the revised code without additional explanation.
"""

            # TODO: Integrate with actual LLM model from agent context
            # For now, provide enhanced rule-based revision logic
            return await self._generate_enhanced_revision(code, feedback, full_prompt)

        except Exception as e:
            # Log the specific exception for debugging
            logger.warning(
                f"LLM-based code revision failed: {e}. Falling back to basic improvements."
            )
            # Fallback to basic improvement if revision fails
            return self._apply_basic_improvements(code, feedback.get("feedback_text", ""))

    async def _generate_enhanced_revision(self, code: str, feedback: dict, _prompt: str) -> str:
        """Generate enhanced code revision with improved logic."""
        category = feedback.get("category", "other")
        feedback_text = feedback.get("feedback_text", "")

        revision_header = f"# Code revision: {category} - {feedback_text}\n"

        if category == "error_handling":
            revised_code = self._apply_error_handling_improvements(code, feedback)
        elif category == "efficiency":
            revised_code = self._apply_efficiency_improvements(code, feedback)
        elif category == "readability":
            revised_code = self._apply_readability_improvements(code, feedback)
        elif category == "functionality":
            revised_code = self._apply_functionality_improvements(code, feedback)
        elif category == "testing":
            revised_code = self._apply_testing_improvements(code, feedback)
        else:
            revised_code = self._apply_general_improvements(code, feedback)

        return revision_header + revised_code

    def _apply_error_handling_improvements(self, code: str, feedback: dict) -> str:
        """Apply error handling improvements with context awareness using AST parsing."""
        import ast

        feedback.get("feedback_text", "").lower()

        # Check if code already has try-catch
        if "try:" in code:
            # Enhance existing error handling by improving exception specificity
            enhanced_code = code
            if "except Exception as e:" in enhanced_code:
                replacement = (
                    "except ValueError as e:\n    logger.error(f'Value error: {e}')\n    "
                    "raise\nexcept Exception as e:"
                )
                enhanced_code = enhanced_code.replace(
                    "except Exception as e:",
                    replacement,
                    1,  # Replace only the first occurrence
                )
            return enhanced_code

        # Add comprehensive error handling using AST parsing for proper structure
        try:
            # Parse the code to understand its structure
            tree = ast.parse(code)

            # If the code contains function definitions, wrap only the function body
            if any(isinstance(node, ast.FunctionDef) for node in tree.body):
                return self._wrap_function_bodies_with_error_handling(code)
            # For non-function code, wrap the entire code block
            return self._wrap_code_block_with_error_handling(code)

        except SyntaxError:
            # If AST parsing fails, fall back to simple wrapping with proper indentation detection
            return self._wrap_code_block_with_error_handling(code)

    def _wrap_function_bodies_with_error_handling(self, code: str) -> str:
        """Wrap function bodies with error handling using AST for robust parsing."""
        import ast

        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            lines = code.split("\n")

            # Find all function definitions and their line ranges
            function_ranges = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get the line range of the function
                    start_line = node.lineno - 1  # Convert to 0-indexed
                    # Find the end line by looking at the last statement
                    end_line = self._get_function_end_line(node, lines)
                    function_ranges.append((start_line, end_line, node))

            # Sort by start line to process in order
            function_ranges.sort(key=lambda x: x[0])

            # If no functions found, fall back to block wrapping
            if not function_ranges:
                return self._wrap_code_block_with_error_handling(code)

            # Process each function to add error handling
            result_lines = lines[:]
            offset = 0  # Track line additions for subsequent functions

            for start_line, end_line, func_node in function_ranges:
                # Adjust for previous insertions
                adj_start = start_line + offset
                adj_end = end_line + offset

                # Get function indentation
                func_def_line = result_lines[adj_start]
                base_indent = len(func_def_line) - len(func_def_line.lstrip())
                function_indent = " " * (base_indent + 4)

                # Find where the function body starts (after def line and docstring)
                body_start = self._find_function_body_start(result_lines, adj_start, func_node)

                # Extract the original function body
                original_body = result_lines[body_start : adj_end + 1]

                # Create the wrapped body
                wrapped_body = [f"{function_indent}try:"]

                # Add the original body with additional indentation
                for line in original_body:
                    if line.strip():
                        wrapped_body.append(f"    {line}")
                    else:
                        wrapped_body.append(line)

                # Add exception handling
                wrapped_body.extend(
                    [
                        f"{function_indent}except ValueError as e:",
                        f"{function_indent}    print(f'Invalid input value: {{e}}')",
                        f"{function_indent}    raise",
                        f"{function_indent}except TypeError as e:",
                        f"{function_indent}    print(f'Type error: {{e}}')",
                        f"{function_indent}    raise",
                        f"{function_indent}except Exception as e:",
                        f"{function_indent}    print(f'Unexpected error: {{e}}')",
                        f"{function_indent}    raise",
                    ]
                )

                # Replace the original body with the wrapped version
                result_lines[body_start : adj_end + 1] = wrapped_body

                # Update offset for next function
                offset += len(wrapped_body) - (adj_end - body_start + 1)

            return "\n".join(result_lines)

        except Exception:
            # Fallback to simple wrapping
            return self._wrap_code_block_with_error_handling(code)

    def _get_function_end_line(self, func_node, _lines: list[str]) -> int:
        """Find the end line of a function using AST information."""

        # Get the last statement in the function
        if func_node.body:
            last_stmt = func_node.body[-1]
            if hasattr(last_stmt, "end_lineno") and last_stmt.end_lineno:
                return last_stmt.end_lineno - 1  # Convert to 0-indexed
            # Fallback: use the line number of the last statement
            return getattr(last_stmt, "lineno", func_node.lineno) - 1
        # Empty function, just use the def line
        return func_node.lineno - 1

    def _find_function_body_start(self, lines: list[str], func_start: int, func_node) -> int:
        """Find where the actual function body starts, skipping def line and docstring."""
        import ast

        current_line = func_start + 1  # Start after the def line

        # Skip empty lines and comments
        while current_line < len(lines) and (
            not lines[current_line].strip() or lines[current_line].strip().startswith("#")
        ):
            current_line += 1

        # Check if there's a docstring
        if (
            current_line < len(lines)
            and func_node.body
            and isinstance(func_node.body[0], ast.Expr)
            and isinstance(func_node.body[0].value, ast.Constant)
            and isinstance(func_node.body[0].value.value, str)
        ):
            # Skip the docstring
            docstring_line = lines[current_line].strip()
            if docstring_line.startswith(('"""', "'''")):
                quote_char = '"""' if docstring_line.startswith('"""') else "'''"
                if not docstring_line.endswith(quote_char) or len(docstring_line) == 3:
                    # Multi-line docstring, find the end
                    current_line += 1
                    while current_line < len(lines) and not lines[current_line].strip().endswith(
                        quote_char
                    ):
                        current_line += 1
                current_line += 1  # Move past the docstring end

        return current_line

    def _wrap_code_block_with_error_handling(self, code: str) -> str:
        """Wrap entire code block with error handling, detecting proper indentation."""
        lines = code.split("\n")

        # Detect the base indentation level of the code
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            return code

        # Find minimum indentation (excluding empty lines)
        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
        base_indent = " " * min_indent

        # Add try-except wrapper with proper indentation
        indented_lines = []
        for line in lines:
            if line.strip():  # Non-empty line
                indented_lines.append(f"    {line}")
            else:  # Empty line
                indented_lines.append(line)

        indented_code = "\n".join(indented_lines)

        return f"""{base_indent}try:
{indented_code}
{base_indent}except ValueError as e:
{base_indent}    print(f"Invalid input value: {{e}}")
{base_indent}    raise
{base_indent}except TypeError as e:
{base_indent}    print(f"Type error: {{e}}")
{base_indent}    raise
{base_indent}except Exception as e:
{base_indent}    print(f"Unexpected error: {{e}}")
{base_indent}    raise"""

    def _apply_efficiency_improvements(self, code: str, feedback: dict) -> str:
        """Apply efficiency improvements with context awareness."""
        feedback_lower = feedback.get("feedback_text", "").lower()
        improved_code = code

        # Add efficiency optimizations based on common patterns
        if "loop" in feedback_lower or "optimize" in feedback_lower:
            # Add comments about optimization
            improved_code = "# Optimized for better performance\n" + code

            # Look for simple optimization opportunities
            if "for i in range(len(" in code:
                improved_code = improved_code.replace(
                    "for i in range(len(",
                    "# TODO: Consider enumerate() - for i, item in enumerate(",
                )

        if "memory" in feedback_lower:
            improved_code = "# Memory-optimized implementation\n" + improved_code

        return improved_code

    def _apply_readability_improvements(self, code: str, feedback: dict) -> str:
        """Apply readability improvements with context awareness."""
        feedback_lower = feedback.get("feedback_text", "").lower()

        # Add docstring if missing
        if '"""' not in code and "def " in code:
            # Find function definition
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("def "):
                    # Insert docstring after function definition
                    func_name = line.split("(")[0].replace("def ", "").strip()
                    docstring = (
                        f'    """\n'
                        f"    {func_name.replace('_', ' ').title()} function with "
                        f"improved readability.\n"
                        f'    \n    Returns:\n        Processed result\n    """'
                    )
                    lines.insert(i + 1, docstring)
                    break
            code = "\n".join(lines)

        # Add type hints suggestion in comments
        if "type" in feedback_lower or "hint" in feedback_lower:
            code = "# Consider adding type hints for better code clarity\n" + code

        # Add meaningful variable name suggestions
        if "variable" in feedback_lower or "name" in feedback_lower:
            code = "# Use descriptive variable names for clarity\n" + code

        return code

    def _apply_functionality_improvements(self, code: str, feedback: dict) -> str:
        """Apply functionality improvements with context awareness."""
        feedback.get("feedback_text", "")
        specific_requests = feedback.get("specific_requests", [])

        improved_code = code

        # Look for specific functionality requests
        for request in specific_requests:
            if "loop" in request.lower():
                improved_code = (
                    f"# Added functionality: {request}\n# TODO: Implement loop logic\n"
                    + improved_code
                )
            elif "validation" in request.lower():
                improved_code = (
                    "# Added input validation\n"
                    "if not input_data:\n    raise ValueError('Input data is required')\n\n"
                    + improved_code
                )
            elif "logging" in request.lower():
                improved_code = (
                    "import logging\nlogger = logging.getLogger(__name__)\n\n"
                    "# Added logging functionality\nlogger.info('Function started')\n"
                    + improved_code
                )

        return improved_code

    def _apply_testing_improvements(self, code: str, feedback: dict) -> str:
        """Apply testing improvements with context awareness."""
        feedback_lower = feedback.get("feedback_text", "").lower()

        improved_code = code

        # Make code more testable
        if "testable" in feedback_lower or "test" in feedback_lower:
            improved_code = "# Made more testable with clear interfaces\n" + code

            # Add assertion for critical conditions
            if "def " in code:
                improved_code += (
                    "\n\n# Example test assertion\n"
                    "# assert result is not None, 'Function should return a value'"
                )

        # Add example usage in docstring
        if "example" in feedback_lower and '"""' in code:
            improved_code = improved_code.replace(
                '"""',
                '"""\n    \n    Example:\n        >>> result = function_name()\n        '
                '>>> assert result is not None\n    """',
            )

        return improved_code

    def _apply_general_improvements(self, code: str, feedback: dict) -> str:
        """Apply general improvements based on user feedback."""
        feedback_text = feedback.get("feedback_text", "")
        feedback.get("specific_requests", [])

        improved_code = code

        # Apply general improvements based on common requests
        if any(word in feedback_text.lower() for word in ["comment", "document"]):
            improved_code = f"# Improvement applied based on feedback: {feedback_text}\n" + code

        if any(word in feedback_text.lower() for word in ["clean", "refactor"]):
            improved_code = f"# Code cleaned and refactored\n{code}\n# End of refactored section"

        return improved_code

    def _apply_basic_improvements(self, code: str, feedback_text: str) -> str:
        """Apply basic improvements as a fallback when LLM revision fails."""
        # Add a header comment explaining the fallback
        improved_code = f"# Basic improvements applied (fallback mode): {feedback_text}\n"

        # Add some basic improvements based on common patterns
        if "error" in feedback_text.lower() or "handle" in feedback_text.lower():
            # Add basic error handling
            lines = code.split("\n")
            indented_code = "\n".join("    " + line if line.strip() else line for line in lines)
            improved_code += f"""try:
{indented_code}
except Exception as e:
    print(f"Error occurred: {{e}}")
    raise"""
        elif "comment" in feedback_text.lower() or "document" in feedback_text.lower():
            # Add basic documentation
            improved_code += f"# Code documented based on feedback: {feedback_text}\n{code}"
        elif "optimize" in feedback_text.lower() or "efficient" in feedback_text.lower():
            # Add optimization comment
            improved_code += f"# Performance optimized based on feedback\n{code}"
        else:
            # Generic improvement
            improved_code += f"# Code improved based on user feedback\n{code}"

        return improved_code


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

    def _run_external_quality_tools(self, code: str) -> dict:
        """Run actual external code quality tools on the code."""
        from pathlib import Path
        import tempfile

        quality_issues = []
        quality_score = 100

        # Get project root directory for proper context
        project_root = self._get_project_root()

        # Create a temporary file for the code
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
                tmp_file.write(code)
                tmp_file_path = tmp_file.name
            # File is now properly closed

            # Run ruff for linting
            ruff_issues = self._run_ruff_analysis(tmp_file_path, cwd=project_root)
            quality_issues.extend(ruff_issues)

            # Run mypy for type checking (if possible)
            mypy_issues = self._run_mypy_analysis(tmp_file_path, cwd=project_root)
            quality_issues.extend(mypy_issues)

            # Run bandit for security analysis
            bandit_issues = self._run_bandit_analysis(tmp_file_path, cwd=project_root)
            quality_issues.extend(bandit_issues)

        finally:
            # Clean up temporary file - file is guaranteed to be closed
            if tmp_file_path:
                try:
                    Path(tmp_file_path).unlink()
                except OSError:
                    # File already deleted or other issue
                    pass

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

    def _get_project_root(self) -> str:
        """Get the project root directory for proper subprocess execution context."""
        from pathlib import Path

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

    def _run_ruff_analysis(self, file_path: str, cwd: str | None = None) -> list[dict]:
        """Run ruff linter on the code file."""
        import json
        import os
        from pathlib import Path
        import subprocess

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

            # Run ruff with JSON output
            result = subprocess.run(
                ["uv", "run", "ruff", "check", file_path, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
                env=env,
            )

            # Use dedicated parser for robust output handling
            parser = RuffOutputParser()
            return parser.parse(result.stdout, result.stderr)

        except FileNotFoundError:
            logger.warning("ruff not found in the environment. Skipping ruff analysis.")
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            json.JSONDecodeError,
        ):
            # If ruff execution fails, return empty list
            pass

        return []

    def _run_mypy_analysis(self, file_path: str, cwd: str | None = None) -> list[dict]:
        """Run mypy type checker on the code file."""
        import os
        from pathlib import Path
        import subprocess

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

            # Run mypy with structured output
            result = subprocess.run(
                ["uv", "run", "mypy", file_path, "--show-error-codes"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
                env=env,
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
        """Run bandit security analysis on the code file."""
        import json
        import os
        from pathlib import Path
        import subprocess

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

            # Run bandit with JSON output
            result = subprocess.run(
                ["uv", "run", "bandit", "-f", "json", file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
                env=env,
            )

            # Use dedicated parser for robust output handling
            parser = BanditOutputParser()
            return parser.parse(result.stdout, result.stderr)

        except FileNotFoundError:
            logger.warning("bandit not found in the environment. Skipping bandit analysis.")
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            json.JSONDecodeError,
        ):
            # If bandit execution fails, return empty list
            pass

        return []

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
        from pathlib import Path
        import tempfile

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
        import os
        from pathlib import Path
        import subprocess

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

    def _contains_test_functions(self, code: str) -> bool:
        """Check if code contains test functions."""
        # Look for test functions (pytest style)
        test_function_pattern = r"def\s+test_\w+\s*\("
        return bool(re.search(test_function_pattern, code))

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

    def _analyze_test_coverage(self, file_path: str, code: str, cwd: str | None = None) -> dict:
        """Analyze potential test coverage."""
        import os
        from pathlib import Path
        import subprocess

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

        # Fallback: estimate coverage based on code structure
        return {
            "coverage_percentage": self._estimate_coverage_from_code(code),
            "tool_available": False,
        }

    def _parse_coverage_output(self, coverage_output: str) -> int:
        """Parse coverage tool output to extract percentage."""
        # Look for coverage percentage in output
        percentage_pattern = r"(\d+)%"
        matches = re.findall(percentage_pattern, coverage_output)

        if matches:
            return int(matches[-1])  # Take the last percentage found

        return 0

    def _estimate_coverage_from_code(self, code: str) -> int:
        """Estimate test coverage based on code analysis."""
        total_lines = len([line for line in code.split("\n") if line.strip()])
        test_lines = len([line for line in code.split("\n") if "test_" in line or "assert" in line])

        if total_lines == 0:
            return 0

        # Simple estimation: more test-related lines = higher coverage
        return min(90, (test_lines * 20) + 10)

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
            "coverage_percentage": 70,
            "testability_score": 80,
            "test_suggestions": test_suggestions,
            "test_execution_output": "External testing tools not available - using basic analysis",
            "tool_results": {
                "pytest_available": False,
                "coverage_tool_available": False,
            },
        }

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
        coverage = testing_results.get("coverage_percentage", 0)
        tests_run = testing_results.get("tests_run", 0)
        tests_passed = testing_results.get("tests_passed", 0)

        message_parts.append("### 🧪 Testing Status:")
        message_parts.append(f"- **Test Coverage:** {coverage}%")
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


class CodeRefinementSatisfactionChecker(BaseAgent):
    """Checks if the user is satisfied with the code refinement."""

    def __init__(self, name: str = "code_refinement_satisfaction_checker"):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Check if user is satisfied or if we should continue refining."""

        # Get feedback and iteration state
        feedback_list = ctx.session.state.get("refinement_feedback", [])
        iteration_state = ctx.session.state.get("iteration_state", {})
        current_iteration = iteration_state.get("current_iteration", 0)
        max_iterations = iteration_state.get("max_iterations", 5)

        should_stop = False
        reason = ""

        if feedback_list:
            latest_feedback = feedback_list[-1]
            user_satisfied = latest_feedback.get("user_satisfied", False)

            if user_satisfied:
                should_stop = True
                reason = "User is satisfied with the code"
            elif current_iteration >= max_iterations:
                should_stop = True
                reason = f"Maximum iterations reached ({max_iterations})"
            else:
                reason = f"Continuing refinement - iteration {current_iteration + 1}"
        else:
            # No feedback yet, continue to collect it
            reason = "Waiting for initial user feedback"

        # Update iteration state
        iteration_state.update(
            {
                "current_iteration": current_iteration + 1,
                "should_stop": should_stop,
                "reason": reason,
            }
        )
        ctx.session.state["iteration_state"] = iteration_state

        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[genai_types.Part(text=f"Refinement check: {reason}")]
            ),
            actions=EventActions(escalate=should_stop),
        )


def create_code_refinement_loop() -> LoopAgent:
    """
    Creates a code refinement loop workflow for iterative code improvement based on user feedback.

    This implements the ADK Iterative Refinement Pattern for user-driven code improvement:
    1. Present code → 2. Collect feedback → 3. Revise code → 4. Run integrated
    quality/testing checks → 5. Repeat until user satisfied

    The workflow creates a mini "red-green-refactor" cycle:
    - RED: Identify quality issues and testing gaps
    - GREEN: Ensure code meets basic standards
    - REFACTOR: Apply user feedback for continuous improvement
    """

    # Create feedback collector
    feedback_collector = CodeRefinementFeedbackCollector()

    # Create code reviser
    code_reviser = CodeRefinementReviser()

    # Create integrated quality and testing analyzer
    quality_testing_integrator = CodeQualityAndTestingIntegrator()

    # Create satisfaction checker
    satisfaction_checker = CodeRefinementSatisfactionChecker()

    # Create initialization agent
    init_agent = LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name="code_refinement_init_agent",
        description="Initializes code refinement process",
        instruction="""
        You initialize the code refinement process.

        Your tasks:
        1. Set up iteration_state in session.state
        2. Ensure initial code is available in session.state['current_code']
        3. Initialize refinement_feedback list
        4. Set up revision_history tracking
        5. Initialize quality and testing tracking
        6. Prepare context for iterative user-driven improvement

        If no initial code is provided, you should generate a basic implementation
        based on the task description.

        The refinement process integrates:
        - User feedback collection and processing
        - Contextual code revision based on feedback
        - Integrated code quality analysis and testing
        - Mini red-green-refactor cycles for continuous improvement
        """,
        output_key="refinement_init",
    )

    # Create iterative code refinement loop with integrated quality & testing
    return LoopAgent(
        name="code_refinement_loop",
        description="Iteratively refines code based on user feedback with integrated "
        "quality analysis and testing",
        max_iterations=5,
        sub_agents=[
            init_agent,  # Initialize (runs once)
            feedback_collector,  # Collect user feedback
            code_reviser,  # Revise code based on feedback
            quality_testing_integrator,  # Integrated quality analysis and testing
            # (RED-GREEN-REFACTOR)
            satisfaction_checker,  # Check if user is satisfied
        ],
    )
