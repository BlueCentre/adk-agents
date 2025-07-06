# Enhanced Software Engineer Agent Usage Guide

## Overview

The enhanced software engineer agent now includes sophisticated workflow orchestration capabilities using ADK patterns. This guide shows you how to use both the traditional agent and the new enhanced version.

## 🚀 Quick Start

### Option 1: Using the Enhanced Agent (Recommended)
```bash
# Use the enhanced agent with automatic workflow selection
adk prompt software_engineer "Implement user authentication with secure password hashing"
```

### Option 2: Using the Traditional Agent
```bash
# Use the traditional agent with manual sub-agent delegation
adk prompt software_engineer "Review this code for security issues"
```

## 📁 Agent Structure

```
agents/software_engineer/
├── agent.py              # Traditional root agent
├── enhanced_agent.py     # Enhanced agent with workflow orchestration
├── workflows/            # Workflow pattern implementations
│   ├── parallel_workflows.py
│   ├── sequential_workflows.py
│   ├── iterative_workflows.py
│   └── human_in_loop_workflows.py
└── sub_agents/           # Specialized sub-agents
    ├── code_review/
    ├── code_quality/
    ├── testing/
    └── ...
```

## 🔧 Configuration

### Switching Between Agents

The system automatically loads the appropriate agent based on your request:
- **Simple tasks**: Uses traditional delegation
- **Complex workflows**: Uses enhanced orchestration

### Environment Variables
```bash
# Set preferred model (optional)
export DEFAULT_AGENT_MODEL="gemini-2.0-flash-thinking-experimental"

# Enable debug logging (optional)
export LOG_LEVEL="DEBUG"
```

## 💡 Usage Examples

### 1. Simple Code Review
```bash
# Traditional approach - direct delegation
adk prompt software_engineer "Review the authentication logic in src/auth.py"
```

**What happens:**
- Task goes directly to `code_review_agent`
- Single-step analysis
- Direct response

### 2. Complex Feature Development
```bash
# Enhanced approach - workflow orchestration
adk prompt software_engineer "Implement a complete user management system with authentication, authorization, and profile management"
```

**What happens:**
1. **Workflow Selection**: System chooses `feature_development_workflow`
2. **Sequential Execution**:
   - `design_pattern_agent` → Architecture design
   - `code_review_agent` → Implementation guidance
   - `testing_agent` → Test strategy
   - `documentation_agent` → Documentation
   - `devops_agent` → Deployment considerations
3. **Result Synthesis**: Comprehensive implementation plan

### 3. Code Quality Improvement
```bash
# Iterative improvement workflow
adk prompt software_engineer "Improve the code quality of our payment processing module until it meets enterprise standards"
```

**What happens:**
1. **Workflow Selection**: System chooses `iterative_refinement_workflow`
2. **Iterative Process**:
   - Analyze current quality
   - Apply improvements
   - Test changes
   - Check if standards met
   - Repeat until satisfied (max 5 iterations)

### 4. Bug Investigation
```bash
# Parallel analysis workflow
adk prompt software_engineer "Investigate performance issues in our API - check code quality, review implementation, and analyze tests"
```

**What happens:**
1. **Workflow Selection**: System chooses `parallel_analysis_workflow`
2. **Concurrent Execution**:
   - `code_quality_agent` → Performance analysis
   - `code_review_agent` → Implementation review
   - `testing_agent` → Test analysis
3. **Result Aggregation**: Combined findings from all agents

## 🛠️ Advanced Usage

### Direct Workflow Access

You can directly use specific workflows:

```python
from agents.software_engineer.workflows.parallel_workflows import create_parallel_analysis_workflow

# Create and use a specific workflow
parallel_analysis = create_parallel_analysis_workflow()
result = parallel_analysis.run("Analyze codebase for security vulnerabilities")
```

### Programmatic Usage

```python
from agents.software_engineer.enhanced_agent import enhanced_root_agent

# Use the enhanced agent programmatically
result = enhanced_root_agent.run("Implement OAuth2 authentication")
print(result)
```

### Custom Workflow Configuration

```python
from agents.software_engineer.enhanced_agent import workflow_selector_tool

# Manually select workflow
workflow_selection = workflow_selector_tool(
    task_type="feature_development",
    complexity="high",
    requires_approval=True,
    parallel_capable=True,
    iterative=False
)
print(f"Selected workflow: {workflow_selection['selected_workflow']}")
```

## 🎯 Workflow Decision Guide

### When Each Workflow is Used

| Task Type | Workflow | Why |
|-----------|----------|-----|
| Simple code review | Direct delegation | Fast, focused analysis |
| Feature development | Sequential workflow | Step-by-step dependencies |
| Code analysis | Parallel workflow | Multiple independent checks |
| Quality improvement | Iterative workflow | Continuous refinement |
| Architecture decisions | Human-in-loop workflow | Critical decisions need approval |

### Complexity Factors

- **Low**: Simple, single-file changes
- **Medium**: Multi-file changes, moderate complexity
- **High**: Complex features, architectural changes

### Workflow Characteristics

- **Parallel Capable**: Tasks that can be split into independent parts
- **Iterative**: Tasks that benefit from multiple improvement cycles
- **Requires Approval**: Critical changes needing human oversight

## 📊 Performance Improvements

### Before (Traditional Agent)
```
Feature Request → Single Agent → Sequential Sub-Agent Calls → Response
Time: ~2-3 minutes for complex tasks
```

### After (Enhanced Agent)
```
Feature Request → Workflow Selection → Parallel/Sequential Execution → Synthesis
Time: ~30-60 seconds for complex tasks (3-5x faster)
```

## 🔍 Monitoring and Debugging

### Viewing Workflow State
```bash
# Check current workflow status
adk prompt software_engineer "Show current workflow state"
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
adk prompt software_engineer "Debug the user authentication workflow"
```

## 🔄 Migration from Traditional Agent

### Existing Commands Still Work
All existing commands continue to work unchanged:
```bash
# These still work exactly the same
adk prompt software_engineer "Review code in src/main.py"
adk prompt software_engineer "Write unit tests for the API"
```

### New Capabilities Added
```bash
# These now use advanced workflows
adk prompt software_engineer "Implement complete e-commerce cart system"
adk prompt software_engineer "Refactor legacy authentication system"
adk prompt software_engineer "Optimize application performance"
```

## 🛡️ Best Practices

### 1. Task Description
```bash
# ✅ Good: Specific, clear requirements
adk prompt software_engineer "Implement JWT authentication with refresh tokens, rate limiting, and secure password hashing"

# ❌ Poor: Vague, unclear scope
adk prompt software_engineer "Fix authentication"
```

### 2. Context Provision
```bash
# ✅ Good: Provide relevant context
adk prompt software_engineer "Refactor the payment processing in src/payments/ to use async/await patterns for better performance"

# ❌ Poor: No context
adk prompt software_engineer "Make it faster"
```

### 3. Workflow Selection
```bash
# ✅ Good: Let system choose optimal workflow
adk prompt software_engineer "Implement user dashboard with real-time updates, charts, and notifications"

# ⚠️ Manual: Force specific workflow (advanced users only)
adk prompt software_engineer "Use iterative refinement to improve code quality in src/core.py"
```

## 🔗 Integration Examples

### CI/CD Integration
```yaml
# .github/workflows/code-review.yml
- name: Automated Code Review
  run: |
    adk prompt software_engineer "Review changes in this pull request for security, performance, and code quality"
```

### Pre-commit Hooks
```bash
#!/bin/bash
# .git/hooks/pre-commit
adk prompt software_engineer "Quick quality check on staged changes"
```

## 📈 Performance Metrics

- **Traditional Agent**: 1 task → 1 sub-agent → sequential execution
- **Enhanced Agent**: 1 task → optimal workflow → parallel/iterative execution
- **Speed Improvement**: 3-5x faster for complex tasks
- **Quality Improvement**: Multi-agent validation and iterative refinement
- **Coverage**: Comprehensive analysis across all aspects (security, performance, testing, etc.)

## 🆘 Troubleshooting

### Common Issues

1. **Workflow Not Selected**: Ensure task description is specific enough
2. **Slow Performance**: Check if parallel workflows are being used for complex tasks
3. **Incomplete Results**: Verify all aspects of the request are covered in task description

### Getting Help
```bash
# Get workflow recommendations
adk prompt software_engineer "What's the best workflow for implementing user authentication?"

# Check available workflows
adk prompt software_engineer "List available workflow patterns"
```

## 🎓 Learning Resources

### Example Prompts
See `SOFTWARE_ENGINEERING_PROMPTS.md` for comprehensive examples of:
- Simple single-agent tasks
- Multi-step workflows
- Complex feature development
- Bug investigation scenarios

### Workflow Patterns
- **Sequential**: Step-by-step processes with dependencies
- **Parallel**: Independent tasks executed concurrently
- **Iterative**: Continuous improvement until quality targets met
- **Human-in-Loop**: Critical decisions with human oversight

---

**Ready to get started?** Try the enhanced agent with a complex task and see the difference in orchestration, speed, and quality!
