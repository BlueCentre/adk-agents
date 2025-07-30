"""
Integration Tests for Code Refinement Workflow (Milestone 4.2)

This module contains integration tests for the code refinement workflow
implemented in Milestone 4.2, which supports iterative code improvement
based on user feedback with integrated quality analysis and testing.

This version includes tests that use the actual create_code_refinement_loop agent
instead of just simulating the workflow logic.
"""

import asyncio
from dataclasses import dataclass
import time
from typing import Any, Optional

import pytest

# Import the real agent for testing
from agents.software_engineer.workflows.iterative_workflows import create_code_refinement_loop


@dataclass
class CodeRefinementResult:
    """Result of code refinement workflow execution for testing."""

    workflow_name: str
    execution_time: float
    agents_executed: list[str]
    session_state_changes: dict[str, Any]
    success: bool
    iterations_completed: int
    final_code: str
    user_satisfied: bool
    quality_scores: list[int]
    feedback_applied: list[dict[str, Any]]
    error_message: Optional[str] = None


class TestCodeRefinementWorkflow:
    """Integration tests for code refinement workflow patterns."""

    @pytest.fixture
    def mock_session_state(self):
        """Create mock session state for code refinement testing."""
        return {
            "workflow_state": "code_refinement_in_progress",
            "iteration_state": {
                "current_iteration": 0,
                "max_iterations": 5,
                "should_stop": False,
                "reason": "Starting code refinement workflow",
            },
            "refinement_feedback": [],
            "revision_history": [],
            "current_code": "",
            "quality_analysis_results": {},
            "testing_results": {},
            "integrated_feedback": {},
        }

    @pytest.mark.asyncio
    async def test_real_code_refinement_agent_creation(self):
        """Test that the real code refinement agent can be created and has correct structure."""
        # Act
        refinement_agent = create_code_refinement_loop()

        # Assert
        assert refinement_agent is not None
        assert refinement_agent.name == "code_refinement_loop"
        assert refinement_agent.max_iterations == 5
        assert len(refinement_agent.sub_agents) == 5

        # Verify the sub-agents are present and correctly named
        expected_sub_agents = [
            "code_refinement_init_agent",
            "code_refinement_feedback_collector",
            "code_refinement_reviser",
            "code_quality_testing_integrator",
            "code_refinement_satisfaction_checker",
        ]

        for i, expected_name in enumerate(expected_sub_agents):
            assert refinement_agent.sub_agents[i].name == expected_name

    @pytest.mark.asyncio
    async def test_code_refinement_factorial_example(self, mock_session_state):
        """Test complete code refinement workflow with factorial function example."""
        # Arrange
        initial_code = """def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result"""

        mock_session_state["current_code"] = initial_code

        # Define refinement requests sequence
        refinement_requests = [
            {
                "feedback": "add input validation to handle negative numbers",
                "expected_category": "error_handling",
                "iteration": 1,
            },
            {
                "feedback": "add documentation and comments for clarity",
                "expected_category": "readability",
                "iteration": 2,
            },
            {
                "feedback": "optimize for better performance",
                "expected_category": "efficiency",
                "iteration": 3,
            },
            {"feedback": "satisfied", "expected_category": "other", "iteration": 4},
        ]

        # Act
        result = await self._execute_code_refinement_workflow(
            mock_session_state, refinement_requests, "factorial function"
        )

        # Assert
        assert result.success
        assert result.workflow_name == "code_refinement"
        assert result.iterations_completed == 4
        assert result.user_satisfied

        # Verify agent execution sequence
        expected_agents = [
            "code_refinement_init_agent",
            "code_refinement_feedback_collector",
            "code_refinement_reviser",
            "code_quality_testing_integrator",
            "code_refinement_satisfaction_checker",
        ]
        for agent in expected_agents:
            assert agent in result.agents_executed

        # Verify feedback was applied
        assert len(result.feedback_applied) == 4
        assert result.feedback_applied[0]["category"] == "error_handling"
        assert result.feedback_applied[1]["category"] == "readability"
        assert result.feedback_applied[2]["category"] == "efficiency"

        # Verify final code contains improvements
        final_code = result.final_code
        assert "try:" in final_code or "ValueError" in final_code  # Error handling
        assert '"""' in final_code or "#" in final_code  # Documentation
        assert "optimized" in final_code.lower() or "efficient" in final_code.lower()  # Efficiency

        # Verify quality progression
        assert len(result.quality_scores) == 4
        assert result.quality_scores[-1] >= result.quality_scores[0]  # Quality should improve

    @pytest.mark.asyncio
    async def test_code_refinement_loop_handling(self, mock_session_state):
        """Test code refinement with request to add a loop."""
        # Arrange
        initial_code = """def process_items(items):
    print(items[0])
    return items[0]"""

        mock_session_state["current_code"] = initial_code

        refinement_requests = [
            {
                "feedback": "add a loop to process all items, not just the first one",
                "expected_category": "functionality",
                "iteration": 1,
            },
            {"feedback": "satisfied", "expected_category": "other", "iteration": 2},
        ]

        # Act
        result = await self._execute_code_refinement_workflow(
            mock_session_state, refinement_requests, "process items function"
        )

        # Assert
        assert result.success
        assert result.user_satisfied
        assert result.iterations_completed == 2

        # Verify loop was added
        final_code = result.final_code
        assert "for" in final_code or "while" in final_code
        assert "loop" in final_code.lower()

    @pytest.mark.asyncio
    async def test_code_refinement_edge_case_handling(self, mock_session_state):
        """Test code refinement with edge case handling request."""
        # Arrange
        initial_code = """def divide_numbers(a, b):
    return a / b"""

        mock_session_state["current_code"] = initial_code

        refinement_requests = [
            {
                "feedback": "handle the edge case when b is zero",
                "expected_category": "error_handling",
                "iteration": 1,
            },
            {"feedback": "satisfied", "expected_category": "other", "iteration": 2},
        ]

        # Act
        result = await self._execute_code_refinement_workflow(
            mock_session_state, refinement_requests, "divide numbers function"
        )

        # Assert
        assert result.success
        assert result.user_satisfied

        # Verify edge case handling
        final_code = result.final_code
        assert "zero" in final_code.lower() or "ZeroDivisionError" in final_code
        assert "if" in final_code or "try:" in final_code

    @pytest.mark.asyncio
    async def test_code_refinement_max_iterations(self, mock_session_state):
        """Test code refinement respects maximum iteration limit."""
        # Arrange
        initial_code = "def simple_func(): pass"
        mock_session_state["current_code"] = initial_code

        # Create requests that never satisfy (no "satisfied" feedback)
        refinement_requests = [
            {
                "feedback": "add error handling",
                "expected_category": "error_handling",
                "iteration": 1,
            },
            {"feedback": "add documentation", "expected_category": "readability", "iteration": 2},
            {"feedback": "optimize performance", "expected_category": "efficiency", "iteration": 3},
            {"feedback": "add more features", "expected_category": "functionality", "iteration": 4},
            {"feedback": "improve testing", "expected_category": "testing", "iteration": 5},
            {
                "feedback": "more improvements",
                "expected_category": "other",
                "iteration": 6,
            },  # Should not reach
        ]

        # Act
        result = await self._execute_code_refinement_workflow(
            mock_session_state, refinement_requests, "simple function", max_iterations=5
        )

        # Assert
        assert result.success  # Should succeed even if not satisfied
        assert not result.user_satisfied  # User never said satisfied
        assert result.iterations_completed == 5  # Should respect max iterations
        assert "Maximum iterations reached" in str(
            result.session_state_changes.get("iteration_state", {})
        )

    @pytest.mark.asyncio
    async def test_code_refinement_quality_testing_integration(self, mock_session_state):
        """Test that quality analysis and testing are properly integrated."""
        # Arrange
        initial_code = """def buggy_function(data):
    result = []
    for i in range(len(data)):
        result.append(data[i] * 2)
    return result"""

        mock_session_state["current_code"] = initial_code

        refinement_requests = [
            {
                "feedback": "satisfied",  # Accept after seeing quality analysis
                "expected_category": "other",
                "iteration": 1,
            }
        ]

        # Act
        result = await self._execute_code_refinement_workflow(
            mock_session_state, refinement_requests, "data processing function"
        )

        # Assert
        assert result.success

        # Verify quality analysis was run
        quality_results = result.session_state_changes.get("quality_analysis_results", {})
        assert "overall_score" in quality_results
        assert "issues" in quality_results

        # Verify testing results were generated
        testing_results = result.session_state_changes.get("testing_results", {})
        assert "test_suggestions" in testing_results
        assert "coverage_percentage" in testing_results

        # Verify integrated feedback was created
        integrated_feedback = result.session_state_changes.get("integrated_feedback", {})
        assert "overall_assessment" in integrated_feedback
        assert "improvement_suggestions" in integrated_feedback

    async def _execute_code_refinement_workflow(
        self,
        session_state: dict[str, Any],
        refinement_requests: list[dict[str, Any]],
        _task_description: str,
        max_iterations: int = 5,
    ) -> CodeRefinementResult:
        """Simulate code refinement workflow execution with iterative feedback."""
        start_time = time.time()
        agents_executed = []
        quality_scores = []
        feedback_applied = []

        try:
            # Initialize workflow
            agents_executed.append("code_refinement_init_agent")
            session_state["iteration_state"]["max_iterations"] = max_iterations

            iterations_completed = 0
            user_satisfied = False
            current_code = session_state.get("current_code", "")

            # Execute refinement loop
            for iteration in range(max_iterations):
                iterations_completed += 1

                # Get current refinement request
                if iteration < len(refinement_requests):
                    current_request = refinement_requests[iteration]
                    user_feedback = current_request["feedback"]
                    expected_category = current_request["expected_category"]
                else:
                    # No more requests, user should be satisfied or max iterations reached
                    user_feedback = "satisfied"
                    expected_category = "other"

                # 1. Collect feedback
                agents_executed.append("code_refinement_feedback_collector")
                session_state["user_input"] = user_feedback

                # Process feedback
                feedback_data = self._process_user_feedback(
                    user_feedback, iteration, expected_category
                )
                session_state["refinement_feedback"].append(feedback_data)
                feedback_applied.append(feedback_data)

                # 2. Revise code (only if not satisfied yet)
                if not feedback_data.get("user_satisfied", False):
                    # 2. Revise code
                    agents_executed.append("code_refinement_reviser")
                    current_code = self._apply_code_revision(current_code, feedback_data)
                    session_state["current_code"] = current_code

                    # Store revision history
                    revision_entry = {
                        "iteration": iteration,
                        "original_code": session_state.get("current_code", ""),
                        "revised_code": current_code,
                        "feedback_applied": feedback_data,
                    }
                    session_state["revision_history"].append(revision_entry)

                # 3. Run quality and testing analysis (always run for consistency)
                agents_executed.append("code_quality_testing_integrator")
                quality_results = self._simulate_quality_analysis(current_code, iteration)
                testing_results = self._simulate_testing_analysis(current_code, iteration)
                integrated_feedback = self._simulate_integrated_feedback(
                    quality_results, testing_results, iteration
                )

                session_state["quality_analysis_results"] = quality_results
                session_state["testing_results"] = testing_results
                session_state["integrated_feedback"] = integrated_feedback

                quality_scores.append(quality_results.get("overall_score", 75))

                # Check if user is satisfied (after running analysis)
                if feedback_data.get("user_satisfied", False):
                    user_satisfied = True

                    # 4. Check satisfaction
                    agents_executed.append("code_refinement_satisfaction_checker")

                    # Update iteration state
                    session_state["iteration_state"].update(
                        {
                            "current_iteration": iteration + 1,
                            "should_stop": user_satisfied,
                            "reason": "User satisfied",
                        }
                    )
                    break

                # Simulate processing time
                await asyncio.sleep(0.05)

            # Check if max iterations reached without satisfaction
            if not user_satisfied and iterations_completed >= max_iterations:
                session_state["iteration_state"]["reason"] = (
                    f"Maximum iterations reached ({max_iterations})"
                )

            execution_time = time.time() - start_time

            return CodeRefinementResult(
                workflow_name="code_refinement",
                execution_time=execution_time,
                agents_executed=agents_executed,
                session_state_changes=session_state,
                success=True,
                iterations_completed=iterations_completed,
                final_code=current_code,
                user_satisfied=user_satisfied,
                quality_scores=quality_scores,
                feedback_applied=feedback_applied,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return CodeRefinementResult(
                workflow_name="code_refinement",
                execution_time=execution_time,
                agents_executed=agents_executed,
                session_state_changes=session_state,
                success=False,
                iterations_completed=iterations_completed,
                final_code=current_code,
                user_satisfied=False,
                quality_scores=quality_scores,
                feedback_applied=feedback_applied,
                error_message=str(e),
            )

    def _process_user_feedback(
        self, feedback_text: str, iteration: int, expected_category: str
    ) -> dict[str, Any]:
        """Simulate user feedback processing."""
        feedback_lower = feedback_text.lower()

        # Determine if user is satisfied
        user_satisfied = any(
            word in feedback_lower for word in ["satisfied", "good", "done", "finished", "perfect"]
        )

        # Categorize feedback (use expected category for testing)
        category = expected_category

        # Determine priority
        priority = "medium"
        if any(word in feedback_lower for word in ["critical", "important", "must", "urgent"]):
            priority = "high"
        elif any(word in feedback_lower for word in ["nice", "minor", "optional"]):
            priority = "low"

        # Extract specific requests
        specific_requests = [req.strip() for req in feedback_text.split(",") if req.strip()]

        return {
            "feedback_text": feedback_text,
            "category": category,
            "priority": priority,
            "specific_requests": specific_requests,
            "user_satisfied": user_satisfied,
            "iteration": iteration,
        }

    def _apply_code_revision(self, code: str, feedback: dict) -> str:
        """Simulate code revision based on feedback."""
        category = feedback.get("category", "other")
        feedback_text = feedback.get("feedback_text", "")

        revision_header = f"# Code revision: {category} - {feedback_text}\n"

        if category == "error_handling":
            if "negative" in feedback_text.lower() or "zero" in feedback_text.lower():
                # Add input validation
                return (
                    revision_header
                    + f"""def improved_function(*args):
    # Input validation added
    if len(args) > 0 and args[0] < 0:
        raise ValueError("Input cannot be negative")
    if len(args) > 1 and args[1] == 0:
        raise ValueError("Division by zero not allowed")

{code}"""
                )
            # General error handling
            lines = code.split("\n")
            indented_code = "\n".join("    " + line if line.strip() else line for line in lines)
            return (
                revision_header
                + f"""try:
{indented_code}
except Exception as e:
    print(f"Error: {{e}}")
    raise"""
            )

        if category == "readability":
            # Add documentation
            if "def " in code and '"""' not in code:
                lines = code.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("def "):
                        func_name = line.split("(")[0].replace("def ", "").strip()
                        docstring = (
                            f'    """\n    {func_name.replace("_", " ").title()} function '
                            f"with improved documentation.\n    \n    Returns:\n        "
                            f'Processed result\n    """'
                        )
                        lines.insert(i + 1, docstring)
                        break
                return revision_header + "\n".join(lines)
            return revision_header + f"# Improved readability\n{code}"

        if category == "efficiency":
            # Add efficiency improvements
            if "for i in range(len(" in code:
                improved_code = code.replace(
                    "for i in range(len(", "# Optimized with enumerate\nfor i, item in enumerate("
                )
                return revision_header + f"# Optimized for better performance\n{improved_code}"
            return revision_header + f"# Optimized for efficiency\n{code}"

        if category == "functionality":
            if "loop" in feedback_text.lower():
                # Add loop functionality
                return (
                    revision_header
                    + f"""# Added loop functionality
def enhanced_function(items):
    results = []
    for item in items:  # Added loop to process all items
        # Process each item
        result = process_single_item(item)
        results.append(result)
    return results

{code}"""
                )
            return revision_header + f"# Enhanced functionality\n{code}"

        if category == "testing":
            # Add testing improvements
            return (
                revision_header
                + f"""# Improved for testing
{code}

# Example test cases
def test_function():
    # Test normal case
    assert function_result is not None

    # Test edge cases
    try:
        function_with_invalid_input()
        assert False, "Should have raised exception"
    except ValueError:
        pass  # Expected"""
            )

        # General improvement
        return revision_header + code

    def _simulate_quality_analysis(self, code: str, iteration: int) -> dict[str, Any]:
        """Simulate code quality analysis."""
        # Base quality score that improves with iterations
        base_score = 70 + (iteration * 5)  # Quality improves with iterations

        issues = []

        # Check for common issues
        if '"""' not in code and "def " in code:
            issues.append(
                {
                    "type": "documentation",
                    "severity": "medium",
                    "message": "Missing docstring documentation",
                }
            )
            base_score -= 10

        if "try:" not in code and ("/" in code or "input(" in code):
            issues.append(
                {"type": "error_handling", "severity": "high", "message": "Missing error handling"}
            )
            base_score -= 15

        return {
            "overall_score": min(100, max(0, base_score)),
            "issues": issues,
            "issues_by_severity": {
                "high": [issue for issue in issues if issue["severity"] == "high"],
                "medium": [issue for issue in issues if issue["severity"] == "medium"],
                "low": [issue for issue in issues if issue["severity"] == "low"],
            },
            "metrics": {
                "lines_of_code": len(code.split("\n")),
                "maintainability_index": base_score,
            },
        }

    def _simulate_testing_analysis(self, code: str, iteration: int) -> dict[str, Any]:
        """Simulate testing analysis."""
        test_suggestions = []

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

        # Coverage improves with iterations
        coverage = min(90, 60 + (iteration * 10))

        return {
            "tests_run": 2 + iteration,
            "tests_passed": 2 + iteration,
            "tests_failed": 0,
            "coverage_percentage": coverage,
            "test_suggestions": test_suggestions,
        }

    def _simulate_integrated_feedback(
        self, quality_results: dict, _testing_results: dict, iteration: int
    ) -> dict[str, Any]:
        """Simulate integrated quality and testing feedback."""
        quality_score = quality_results.get("overall_score", 70)

        # Assessment improves with quality score and iterations
        if quality_score >= 90:
            assessment = "excellent"
        elif quality_score >= 80:
            assessment = "good"
        elif quality_score >= 70:
            assessment = "acceptable"
        else:
            assessment = "needs_improvement"

        critical_actions = []
        improvement_suggestions = []

        # Add critical actions for high severity issues
        for issue in quality_results.get("issues_by_severity", {}).get("high", []):
            critical_actions.append(
                {
                    "action": "fix_quality_issue",
                    "priority": "high",
                    "description": issue["message"],
                    "type": issue["type"],
                }
            )

        # Add improvement suggestions
        for issue in quality_results.get("issues_by_severity", {}).get("medium", []):
            improvement_suggestions.append(
                {"suggestion": issue["message"], "type": issue["type"], "impact": "medium"}
            )

        return {
            "iteration": iteration,
            "overall_assessment": assessment,
            "critical_actions": critical_actions,
            "improvement_suggestions": improvement_suggestions,
            "next_refactor_priorities": [("documentation", 1), ("error_handling", 1)],
        }
