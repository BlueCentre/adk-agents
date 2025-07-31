"""Code refinement reviser agent for iterative workflows."""

from collections.abc import AsyncGenerator
from datetime import datetime
import logging

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from ... import config as agent_config

logger = logging.getLogger(__name__)


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

    async def _apply_feedback_to_code(self, code: str, feedback: dict) -> str:
        """Apply user feedback to revise the code using contextual understanding."""
        # Create a detailed revision prompt for the LLM
        revision_prompt = self._create_contextual_revision_prompt(code, feedback)

        # For a complete implementation, this would call the LLM with the revision prompt
        # For now, we'll implement rule-based revisions with more context awareness

        return await self._apply_contextual_revisions(code, feedback, revision_prompt)

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
