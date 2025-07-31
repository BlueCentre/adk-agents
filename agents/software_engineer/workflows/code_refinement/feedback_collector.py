"""Code refinement feedback collector agent for iterative workflows."""

import asyncio
from collections.abc import AsyncGenerator
import logging
import re

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from ... import config as agent_config

logger = logging.getLogger(__name__)


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
        feedback_data = await self._process_feedback(user_feedback, current_iteration)

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

    async def _categorize_feedback_enhanced(self, feedback: str) -> str:
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
                return await self._categorize_feedback_with_llm(feedback, tied_categories)

        # No clear keyword matches, use LLM for categorization
        return await self._categorize_feedback_with_llm(
            feedback, list(categorization_patterns.keys())
        )

    async def _categorize_feedback_with_llm(
        self, feedback: str, candidate_categories: list[str]
    ) -> str:
        """Use LLM to categorize feedback, with a keyword-based fallback."""
        max_retries = 3
        retry_delay_seconds = 1

        for attempt in range(max_retries):
            try:
                # Create structured prompt for LLM categorization
                categorization_prompt = self._create_categorization_prompt(
                    feedback, candidate_categories
                )

                # Make LLM call using genai types
                llm_request = genai_types.GenerateContentRequest(
                    contents=[
                        genai_types.Content(
                            role="user", parts=[genai_types.Part(text=categorization_prompt)]
                        )
                    ]
                )

                # Call the LLM model
                logger.debug(
                    "Making LLM call for feedback categorization (attempt %d/%d)",
                    attempt + 1,
                    max_retries,
                )
                response_stream = self.model.generate_content_async(llm_request)

                # Collect response content
                response_text = ""
                async for response in response_stream:
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.text:
                                response_text += part.text

                # Parse and validate the LLM response
                if response_text.strip():
                    categorization = self._parse_llm_categorization_response(
                        response_text, candidate_categories
                    )
                    if categorization:
                        logger.info(
                            "LLM categorization successful on attempt %d: %s",
                            attempt + 1,
                            categorization,
                        )
                        return categorization
                    logger.warning("LLM returned invalid category on attempt %d", attempt + 1)
                else:
                    logger.warning("LLM returned empty response on attempt %d", attempt + 1)

            except Exception as e:
                logger.warning(
                    "LLM categorization attempt %d/%d failed: %s",
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay_seconds)  # Wait before retrying
                continue  # Go to the next retry attempt

        # Fallback to a keyword matching algorithm if the LLM fails after all retries
        logger.warning("LLM categorization failed. Falling back to keyword matching.")
        feedback_lower = feedback.lower()

        # Define keyword patterns for each category
        patterns = {
            "efficiency": ["faster", "speed", "memory", "optimize"],
            "error_handling": ["error", "exception", "crash", "handle"],
            "readability": ["comment", "naming", "format", "style"],
            "testing": ["test", "coverage", "assert", "verify"],
            "functionality": ["add", "feature", "change", "implement"],
        }

        # Score categories based on keyword matches
        scores = {
            cat: sum(1 for p in patterns.get(cat, []) if p in feedback_lower)
            for cat in candidate_categories
        }

        # Return the category with the highest score
        if any(scores.values()):
            return max(scores, key=scores.get)

        # If no keywords match, return the first candidate or 'other'
        return candidate_categories[0] if candidate_categories else "other"

    async def _process_feedback(self, user_feedback: str, iteration: int) -> dict:
        """Process and categorize user feedback using enhanced logic."""
        feedback_lower = user_feedback.lower()

        # Determine if user is satisfied
        satisfaction_words = ["satisfied", "good", "done", "finished", "perfect", "complete"]
        user_satisfied = any(word in feedback_lower for word in satisfaction_words)

        # Enhanced categorization with better pattern matching
        category = await self._categorize_feedback_enhanced(user_feedback)

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

    def _create_categorization_prompt(self, feedback: str, candidate_categories: list[str]) -> str:
        """Create a structured prompt for LLM-based feedback categorization."""
        categories_str = "\n".join([f"- {cat}" for cat in candidate_categories])

        return f"""You are an expert code reviewer analyzing user feedback about code.

Your task is to categorize the following feedback into one of the provided categories.

FEEDBACK TO CATEGORIZE:
"{feedback}"

AVAILABLE CATEGORIES:
{categories_str}

INSTRUCTIONS:
1. Analyze the feedback content carefully
2. Choose the MOST APPROPRIATE category from the list above
3. Respond with ONLY the category name, no additional text
4. If the feedback doesn't clearly fit any category, choose the closest match

CATEGORY:"""

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

    def _parse_llm_categorization_response(
        self, response_text: str, candidate_categories: list[str]
    ) -> str | None:
        """Parse and validate LLM categorization response."""
        # Clean the response text
        cleaned_response = response_text.strip().lower()

        # Try direct match first
        for category in candidate_categories:
            if category.lower() == cleaned_response:
                return category

        # Try partial match (in case LLM adds extra text)
        for category in candidate_categories:
            if category.lower() in cleaned_response:
                return category

        # Try fuzzy matching for common variations
        category_variations = {
            "error_handling": ["error", "exception", "handling", "try", "catch"],
            "efficiency": ["performance", "speed", "optimization", "memory", "time"],
            "readability": ["readable", "clarity", "clean", "documentation", "comments"],
            "testing": ["test", "testing", "coverage", "assert", "verification"],
            "functionality": ["feature", "function", "behavior", "logic", "implementation"],
        }

        for category in candidate_categories:
            variations = category_variations.get(category, [])
            for variation in variations:
                if variation in cleaned_response:
                    return category

        # No valid category found
        return None
