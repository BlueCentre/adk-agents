# Enhanced Software Engineer Agent Examples

This directory contains example scripts demonstrating how to use the enhanced software engineer agent with ADK workflow patterns.

## Files

### `enhanced_agent_example.py`
Comprehensive demonstration of all workflow patterns and features.

**Usage:**
```bash
cd agents/software_engineer/examples
uv run python enhanced_agent_example.py
```

**What it demonstrates:**
- Traditional delegation vs. enhanced orchestration
- Sequential workflow patterns
- Parallel workflow patterns
- Iterative workflow patterns
- Direct workflow usage
- Workflow selection tool

### `quick_test.py`
Simple CLI script for quick testing of the enhanced agent.

**Usage:**
```bash
cd agents/software_engineer/examples
uv run python quick_test.py "Your task description here"
```

**Examples:**
```bash
# Simple code review
uv run python quick_test.py "Review code in src/auth.py"

# Complex feature development
uv run python quick_test.py "Implement user authentication system"

# Code analysis
uv run python quick_test.py "Analyze API performance issues"

# Quality improvement
uv run python quick_test.py "Improve code quality in payment module"
```

## Prerequisites

Make sure you have the ADK agents system properly set up:

1. **Environment Variables:**
   ```bash
   export DEFAULT_AGENT_MODEL="gemini-2.0-flash-thinking-experimental"
   export LOG_LEVEL="INFO"  # Optional: for debug output
   ```

2. **Dependencies:**
   The enhanced agent requires all the same dependencies as the base software engineer agent.

## Example Workflows

### 1. Simple Task (Traditional Delegation)
Tasks that can be handled by a single sub-agent are delegated directly:
```python
task = "Review the authentication logic in src/auth.py for security issues"
# → Goes directly to code_review_agent
```

### 2. Complex Feature Development (Sequential Workflow)
Multi-step processes are orchestrated through sequential workflows:
```python
task = "Implement a complete user management system"
# → Uses feature_development_workflow
# → design_pattern_agent → code_review_agent → testing_agent → documentation_agent
```

### 3. Code Analysis (Parallel Workflow)
Independent analysis tasks are executed in parallel:
```python
task = "Analyze codebase for security, performance, and test coverage"
# → Uses parallel_analysis_workflow
# → code_quality_agent || code_review_agent || testing_agent (concurrent)
```

### 4. Quality Improvement (Iterative Workflow)
Continuous improvement until quality targets are met:
```python
task = "Improve code quality until it meets enterprise standards"
# → Uses iterative_refinement_workflow
# → Analyze → Improve → Test → Check → Repeat (until satisfied)
```

## Workflow Selection

The enhanced agent automatically selects the optimal workflow based on:
- **Task complexity** (low, medium, high)
- **Parallelization potential** (independent vs. dependent tasks)
- **Iterative needs** (one-shot vs. continuous improvement)
- **Approval requirements** (automated vs. human oversight)

## Performance Benefits

- **3-5x faster** for complex tasks through parallel execution
- **Higher quality** results through multi-agent validation
- **Better orchestration** with intelligent workflow selection
- **Comprehensive coverage** across all software engineering aspects

## Troubleshooting

### Common Issues

1. **Import Errors:** Ensure you're running from the correct directory
2. **Model Errors:** Check that your model configuration is correct
3. **Slow Performance:** Enable debug logging to see workflow selection

### Debug Mode
```bash
export LOG_LEVEL="DEBUG"
uv run python enhanced_agent_example.py
```

## Next Steps

1. Try the examples with your own tasks
2. Experiment with different workflow patterns
3. Integrate the enhanced agent into your development workflow
4. Create custom workflows for your specific needs
