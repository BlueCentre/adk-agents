"""Sophisticated workflow classification system for the Software Engineer Agent."""

import logging
from typing import Any

from .. import config as agent_config

logger = logging.getLogger(__name__)


class WorkflowClassifier:
    """
    A sophisticated workflow classifier that uses weighted scoring instead of hardcoded indicators.

    This replaces the simple indicator-based approach with a more maintainable and extensible
    scoring system that can be easily tuned and expanded.
    """

    def __init__(self):
        """Initialize the classifier with scoring patterns."""
        # Workflow patterns with weighted indicators
        self.workflow_patterns = {
            "human_in_loop": {
                "patterns": [
                    ("deploy", 10),
                    ("release", 10),
                    ("production", 9),
                    ("critical", 8),
                    ("security", 8),
                    ("architecture", 7),
                    ("merge", 6),
                    ("review", 4),
                    ("approve", 6),
                    ("sign off", 7),
                    ("validate", 5),
                    ("confirm", 4),
                ],
                "min_score": 6,
                "description": "Requires human approval and oversight",
            },
            "code_refinement": {
                "patterns": [
                    ("refine code", 10),
                    ("improve code", 9),
                    ("code refinement", 10),
                    ("iterative code", 8),
                    ("feedback-driven", 8),
                    ("user feedback", 7),
                    ("collaborative coding", 6),
                    ("refine my code", 9),
                    ("improve this code", 9),
                    ("polish", 5),
                    ("enhance", 4),
                    ("optimize", 4),
                    ("clean up", 5),
                ],
                "min_score": 7,
                "description": "Interactive code improvement with user feedback",
            },
            "iterative_refinement": {
                "patterns": [
                    ("improve", 6),
                    ("refine", 7),
                    ("optimize", 6),
                    ("gradually", 8),
                    ("step by step", 9),
                    ("iterative", 10),
                    ("incremental", 7),
                    ("progressive", 6),
                    ("enhance", 4),
                    ("evolve", 5),
                    ("polish", 4),
                ],
                "min_score": 6,
                "complexity_multiplier": 1.5,  # Higher complexity boosts this workflow
                "description": "Iterative improvement for complex tasks",
            },
            "parallel_execution": {
                "patterns": [
                    ("multiple files", 10),
                    ("batch", 8),
                    ("several", 6),
                    ("various", 5),
                    ("different modules", 9),
                    ("concurrent", 8),
                    ("simultaneously", 9),
                    ("parallel", 10),
                    ("multiple", 5),
                    ("many", 4),
                    ("across", 4),
                ],
                "min_score": 5,
                "description": "Suitable for parallel processing",
            },
            "standard_sequential": {
                "patterns": [
                    ("implement", 4),
                    ("fix", 5),
                    ("debug", 6),
                    ("create", 4),
                    ("write", 4),
                    ("add", 3),
                    ("update", 3),
                    ("change", 3),
                    ("modify", 3),
                    ("simple", 2),
                    ("basic", 2),
                    ("straightforward", 5),
                ],
                "min_score": 3,
                "description": "Standard sequential workflow",
            },
        }

        # Task type patterns
        self.task_type_patterns = {
            "testing": [
                ("test", 8),
                ("testing", 9),
                ("spec", 6),
                ("coverage", 7),
                ("pytest", 8),
                ("unittest", 7),
                ("assertion", 6),
                ("mock", 5),
            ],
            "deployment": [
                ("deploy", 10),
                ("build", 7),
                ("ci/cd", 10),
                ("docker", 6),
                ("container", 5),
                ("pipeline", 6),
                ("release", 7),
                ("publish", 6),
            ],
            "analysis": [
                ("review", 8),
                ("analyze", 9),
                ("audit", 8),
                ("inspect", 7),
                ("examine", 6),
                ("investigate", 7),
                ("check", 5),
                ("verify", 6),
            ],
            "documentation": [
                ("document", 9),
                ("docs", 8),
                ("readme", 7),
                ("comment", 6),
                ("docstring", 8),
                ("explain", 5),
                ("describe", 5),
                ("guide", 6),
            ],
        }

        # Complexity indicators with weights
        self.complexity_patterns = {
            "high": [
                ("refactor", 9),
                ("architecture", 10),
                ("design", 8),
                ("migration", 9),
                ("integration", 8),
                ("complex", 7),
                ("advanced", 6),
                ("enterprise", 7),
                ("large scale", 8),
                ("distributed", 7),
                ("microservice", 7),
            ],
            "medium": [
                ("implement", 5),
                ("fix", 4),
                ("optimize", 6),
                ("enhance", 5),
                ("update", 3),
                ("modify", 4),
                ("extend", 5),
                ("improve", 5),
            ],
            "low": [
                ("debug", 4),
                ("review", 3),
                ("format", 2),
                ("document", 3),
                ("test", 3),
                ("simple", 6),
                ("basic", 5),
                ("minor", 4),
                ("quick", 5),
                ("small", 4),
            ],
        }

    def _calculate_pattern_score(self, text: str, patterns: list[tuple[str, int]]) -> float:
        """Calculate weighted score for pattern matches."""
        total_score = 0
        for pattern, weight in patterns:
            if pattern in text:
                # Count occurrences and apply weight
                occurrences = text.count(pattern)
                total_score += weight * min(occurrences, 3)  # Cap at 3 occurrences

        return total_score

    def _classify_task_type(self, text: str) -> str:
        """Classify the type of task based on patterns."""
        type_scores = {}
        for task_type, patterns in self.task_type_patterns.items():
            score = self._calculate_pattern_score(text, patterns)
            type_scores[task_type] = score

        if type_scores:
            max_type = max(type_scores.items(), key=lambda x: x[1])
            return max_type[0] if max_type[1] > 0 else "general"

        return "general"

    def _classify_complexity(self, text: str) -> str:
        """Classify task complexity based on indicators."""
        complexity_scores = {}
        for level, patterns in self.complexity_patterns.items():
            score = self._calculate_pattern_score(text, patterns)
            complexity_scores[level] = score

        if complexity_scores:
            max_complexity = max(complexity_scores.items(), key=lambda x: x[1])
            return max_complexity[0] if max_complexity[1] > 0 else "low"

        return "low"

    def _get_complexity_score(self, text: str) -> float:
        """Get numeric complexity score for multiplier calculations using configurable weights."""
        high_score = self._calculate_pattern_score(text, self.complexity_patterns["high"])
        medium_score = self._calculate_pattern_score(text, self.complexity_patterns["medium"])
        low_score = self._calculate_pattern_score(text, self.complexity_patterns["low"])

        weights = getattr(
            agent_config, "COMPLEXITY_WEIGHTS", {"high": 3.0, "medium": 2.0, "low": 1.0}
        )
        return (
            high_score * float(weights.get("high", 3.0))
            + medium_score * float(weights.get("medium", 2.0))
            + low_score * float(weights.get("low", 1.0))
        )

    def _generate_reasoning(
        self,
        selected_workflow: str,
        workflow_scores: dict[str, Any],
        task_type: str,
        complexity: str,
    ) -> str:
        """Generate human-readable reasoning for the workflow selection."""
        selected_score = workflow_scores[selected_workflow]["score"]
        selected_desc = workflow_scores[selected_workflow]["description"]

        reasoning_parts = [
            f"Selected '{selected_workflow}' workflow (confidence: {selected_score:.1f})",
            f"Task type: {task_type}, Complexity: {complexity}",
            f"Rationale: {selected_desc}",
        ]

        # Add additional context about close alternatives
        other_eligible = [
            name
            for name, data in workflow_scores.items()
            if name != selected_workflow and data["eligible"]
        ]

        if other_eligible:
            reasoning_parts.append(f"Also considered: {', '.join(other_eligible)}")

        return " | ".join(reasoning_parts)

    def classify_workflow(self, task_description: str) -> dict[str, Any]:
        """
        Classify the workflow based on task description using weighted scoring.

        Args:
            task_description: Description of the task to analyze

        Returns:
            Dictionary with workflow recommendation and analysis
        """
        task_lower = task_description.lower()

        # Calculate workflow scores
        workflow_scores = {}
        for workflow_name, config in self.workflow_patterns.items():
            score = self._calculate_pattern_score(task_lower, config["patterns"])

            # Apply complexity multiplier if available
            if "complexity_multiplier" in config:
                complexity_score = self._get_complexity_score(task_lower)
                if complexity_score >= 6:  # High complexity threshold
                    score *= config["complexity_multiplier"]

            workflow_scores[workflow_name] = {
                "score": score,
                "min_score": config["min_score"],
                "eligible": score >= config["min_score"],
                "description": config["description"],
            }

        # Determine task characteristics
        task_type = self._classify_task_type(task_lower)
        complexity = self._classify_complexity(task_lower)

        # Select best workflow
        eligible_workflows = {
            name: data for name, data in workflow_scores.items() if data["eligible"]
        }

        if eligible_workflows:
            # Select workflow with highest score among eligible ones
            selected_workflow = max(eligible_workflows.items(), key=lambda x: x[1]["score"])[0]
        else:
            # Fallback to standard sequential if no workflows meet threshold
            selected_workflow = "standard_sequential"

        # Additional characteristics
        requires_approval = workflow_scores["human_in_loop"]["eligible"]
        parallel_capable = workflow_scores["parallel_execution"]["eligible"]
        iterative = (
            workflow_scores["iterative_refinement"]["eligible"]
            or workflow_scores["code_refinement"]["eligible"]
        )

        return {
            "selected_workflow": selected_workflow,
            "confidence": workflow_scores[selected_workflow]["score"],
            "task_characteristics": {
                "task_type": task_type,
                "complexity": complexity,
                "requires_approval": requires_approval,
                "parallel_capable": parallel_capable,
                "iterative": iterative,
                "code_refinement_needed": workflow_scores["code_refinement"]["eligible"],
            },
            "workflow_scores": {
                name: {"score": data["score"], "eligible": data["eligible"]}
                for name, data in workflow_scores.items()
            },
            "reasoning": self._generate_reasoning(
                selected_workflow, workflow_scores, task_type, complexity
            ),
        }

    def get_pattern_coverage(self, task_description: str) -> dict[str, list[str]]:
        """
        Get which patterns matched for debugging/tuning purposes.

        Args:
            task_description: Task to analyze

        Returns:
            Dictionary mapping workflow names to lists of matched patterns
        """
        task_lower = task_description.lower()
        coverage = {}

        for workflow_name, config in self.workflow_patterns.items():
            matched_patterns = []
            for pattern, _ in config["patterns"]:
                if pattern in task_lower:
                    matched_patterns.append(pattern)
            coverage[workflow_name] = matched_patterns

        return coverage

    def update_patterns(
        self,
        workflow_name: str,
        add: list[tuple[str, int]] | None = None,
        modify: dict[str, int] | None = None,
        remove: list[str] | None = None,
    ):
        """
        Update patterns for a specific workflow with validation.

        Args:
            workflow_name: The name of the workflow to update.
            add: A list of (pattern, weight) tuples to add.
            modify: A dictionary of {pattern: new_weight} to modify.
            remove: A list of patterns to remove.

        Raises:
            ValueError: If the workflow name is unknown or if the new_patterns
                        are not in the expected format.
        """
        if workflow_name not in self.workflow_patterns:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        patterns = self.workflow_patterns[workflow_name]["patterns"]

        # Remove patterns
        if remove:
            patterns[:] = [p for p in patterns if p[0] not in remove]
            logger.info(f"Removed {len(remove)} patterns from {workflow_name}")

        # Modify patterns
        if modify:
            for i, (pattern, _) in enumerate(patterns):
                if pattern in modify:
                    patterns[i] = (pattern, modify[pattern])
            logger.info(f"Modified {len(modify)} patterns in {workflow_name}")

        # Add new patterns
        if add:
            # Validate the format of the new patterns
            if not isinstance(add, list) or not all(
                isinstance(p, tuple)
                and len(p) == 2
                and isinstance(p[0], str)
                and isinstance(p[1], int)
                for p in add
            ):
                raise ValueError(
                    "Invalid format for 'add'. Expected a list of (string, integer) tuples."
                )
            patterns.extend(add)
            logger.info(f"Added {len(add)} new patterns to {workflow_name}")
