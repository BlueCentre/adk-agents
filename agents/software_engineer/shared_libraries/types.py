"""Type definitions for the software engineer agent."""

from typing import List, Optional

from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field

# Configure JSON response format
json_response_config = GenerateContentConfig(
    temperature=0.2,
    top_p=0.95,
    candidate_count=1,
)


# https://google.github.io/adk-docs/agents/llm-agents/#structuring-data-input_schema-output_schema-output_key


# Define data models for agent responses
class CodeIssue(BaseModel):
    """Represents a code issue identified during code review."""

    issue_type: str = Field(description="Type of issue (bug, security, performance, style)")
    severity: str = Field(description="Severity of the issue (critical, high, medium, low)")
    location: str = Field(description="File and line number where the issue occurs")
    description: str = Field(description="Detailed description of the issue")
    recommendation: str = Field(description="Suggested fix or improvement")


class CodeReviewResponse(BaseModel):
    """Response model for code review analysis."""

    issues: List[CodeIssue] = Field(description="List of identified code issues")
    summary: str = Field(description="Overall summary of the code review")
    suggestions: List[str] = Field(description="General suggestions for improvement")


class DesignPattern(BaseModel):
    """Represents a design pattern recommendation."""

    pattern_name: str = Field(description="Name of the design pattern")
    category: str = Field(description="Category of the pattern (creational, structural, behavioral)")
    problem_solved: str = Field(description="What problem this pattern solves")
    benefits: List[str] = Field(description="Benefits of using this pattern")
    tradeoffs: List[str] = Field(description="Potential drawbacks or tradeoffs")
    example_code: str = Field(description="Example implementation code")


class DesignPatternResponse(BaseModel):
    """Response model for design pattern recommendations."""

    recommended_patterns: List[DesignPattern] = Field(description="List of recommended design patterns")
    explanation: str = Field(description="Explanation of why these patterns are recommended")


class TestCase(BaseModel):
    """Represents a test case."""

    name: str = Field(description="Name of the test case")
    description: str = Field(description="Description of what the test verifies")
    test_type: str = Field(description="Type of test (unit, integration, system)")
    prerequisites: List[str] = Field(description="Prerequisites for running the test")
    test_code: str = Field(description="The test code implementation")
    expected_outcome: str = Field(description="Expected outcome of the test")


class TestingResponse(BaseModel):
    """Response model for test generation."""

    test_cases: List[TestCase] = Field(description="List of generated test cases")
    testing_strategy: str = Field(description="Overall testing strategy")
    test_coverage: Optional[str] = Field(description="Expected test coverage")


class DebuggingStep(BaseModel):
    """Represents a debugging step."""

    step_number: int = Field(description="Step number in the debugging process")
    description: str = Field(description="Description of the debugging step")
    expected_outcome: str = Field(description="What to look for or expect from this step")
    code_example: Optional[str] = Field(description="Example code for this debugging step")


class DebuggingResponse(BaseModel):
    """Response model for debugging assistance."""

    problem_analysis: str = Field(description="Analysis of the problem")
    root_cause: Optional[str] = Field(description="Identified root cause")
    debugging_steps: List[DebuggingStep] = Field(description="Steps to debug the issue")
    solution: Optional[str] = Field(description="Proposed solution")


class DocumentationItem(BaseModel):
    """Represents a documentation item."""

    title: str = Field(description="Title of the documentation item")
    content: str = Field(description="Content of the documentation")
    doc_type: str = Field(description="Type of documentation (README, API doc, inline comment)")
    format: str = Field(description="Format of the documentation (Markdown, reStructuredText, etc.)")


class DocumentationResponse(BaseModel):
    """Response model for documentation generation."""

    documentation_items: List[DocumentationItem] = Field(description="List of documentation items")
    suggestions: Optional[List[str]] = Field(description="Suggestions for improving documentation")


class DevOpsComponent(BaseModel):
    """Represents a DevOps component recommendation."""

    component_name: str = Field(description="Name of the DevOps component")
    purpose: str = Field(description="Purpose of this component")
    implementation: str = Field(description="Implementation details or configuration")
    alternatives: Optional[List[str]] = Field(description="Alternative options")


class DevOpsResponse(BaseModel):
    """Response model for DevOps recommendations."""

    components: List[DevOpsComponent] = Field(description="List of DevOps components")
    implementation_plan: str = Field(description="Overall implementation plan")
    resources: Optional[List[str]] = Field(description="Helpful resources or documentation")
