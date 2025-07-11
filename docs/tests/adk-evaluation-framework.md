---
title: ADK Evaluation Framework
layout: default
nav_order: 5
parent: Testing
---

# ADK Evaluation Framework

The ADK Evaluation Framework provides **behavioral testing** for multi-agent systems, validating how agents actually behave in real-world scenarios rather than just testing structural components.

## Overview

### What is Evaluation Testing?

Evaluation testing focuses on **agent behavior** rather than system structure:

- **Traditional Testing**: "Does the agent have the right components?"
- **Evaluation Testing**: "Does the agent behave correctly when users interact with it?"

### Key Benefits

- **Real Behavior Validation** - Tests actual agent responses to natural language queries
- **User-Centric Testing** - Scenarios mirror actual user interactions
- **Tool Usage Validation** - Ensures agents use tools correctly in context
- **Multi-Agent Coordination** - Validates communication and workflow between agents
- **Response Quality Assurance** - Tests the quality and relevance of agent responses
- **Future-Proof Integration** - Ready for official ADK evaluation module

## Architecture

### File Structure

```
tests/integration/evaluation_tests/
├── simple_code_analysis.evalset.json      # Basic agent functionality
├── sub_agent_delegation.evalset.json      # Agent hierarchy patterns
├── tool_usage.evalset.json                # Tool usage validation
├── multi_agent_coordination.evalset.json  # Coordination patterns
├── agent_memory_persistence.evalset.json  # Memory & persistence
└── test_config.json                       # Configuration
```

### Test Validation

```
tests/integration/test_adk_evaluation_patterns.py
├── TestADKEvaluationPatterns
│   ├── test_evaluation_test_files_exist()
│   ├── test_evaluation_test_structure()
│   ├── test_multi_agent_coordination_evaluation()
│   ├── test_agent_memory_persistence_evaluation()
│   └── test_adk_evaluation_framework_readiness()
```

## Creating Evaluation Tests

### Basic Evaluation File Format

```json
{
  "test_name": "Agent Behavior Evaluation",
  "description": "Tests agent responses to real-world scenarios",
  "version": "1.0.0",
  "test_scenarios": [
    {
      "scenario_id": "unique_scenario_identifier",
      "description": "What this scenario tests",
      "query": "Natural language user query",
      "expected_tool_use": [
        {
          "tool_name": "specific_tool_name",
          "inputs": {
            "parameter1": "expected_value",
            "parameter2": "expected_value"
          }
        }
      ],
      "expected_intermediate_agent_responses": [
        {
          "agent_type": "agent_name",
          "response_pattern": "expected_response_content",
          "coordination_actions": ["action1", "action2"]
        }
      ],
      "reference": "Expected outcome and behavior description"
    }
  ],
  "evaluation_criteria": {
    "criterion1": "What this criterion measures",
    "criterion2": "What this criterion measures"
  }
}
```

### Pattern Examples

#### 1. Simple Code Analysis Pattern

```json
{
  "scenario_id": "basic_code_analysis",
  "description": "Test basic code analysis capabilities",
  "query": "Analyze this Python code for potential issues: def calculate(x, y): return x/y",
  "expected_tool_use": [
    {
      "tool_name": "code_analyzer",
      "inputs": {
        "code": "def calculate(x, y): return x/y",
        "language": "python"
      }
    }
  ],
  "expected_intermediate_agent_responses": [
    {
      "agent_type": "code_quality_agent",
      "response_pattern": "division by zero vulnerability",
      "coordination_actions": ["risk_assessment", "recommendation_generation"]
    }
  ],
  "reference": "Agent should identify division by zero risk and suggest input validation"
}
```

#### 2. Multi-Agent Coordination Pattern

```json
{
  "scenario_id": "feature_development_coordination",
  "description": "Test coordination between multiple agents for feature development",
  "query": "I need to implement a new user authentication feature. Please coordinate between design, development, and testing teams.",
  "expected_tool_use": [
    {
      "tool_name": "workflow_orchestrator",
      "inputs": {
        "workflow_type": "feature_development",
        "agents_required": ["design_pattern_agent", "code_review_agent", "testing_agent"],
        "coordination_strategy": "sequential_with_feedback"
      }
    }
  ],
  "expected_intermediate_agent_responses": [
    {
      "agent_type": "design_pattern_agent",
      "response_pattern": "authentication architecture design",
      "coordination_actions": ["state_update", "next_agent_notification"]
    },
    {
      "agent_type": "code_review_agent",
      "response_pattern": "implementation review feedback",
      "coordination_actions": ["quality_validation", "testing_handoff"]
    },
    {
      "agent_type": "testing_agent",
      "response_pattern": "test strategy and execution",
      "coordination_actions": ["validation_complete", "workflow_finalization"]
    }
  ],
  "reference": "Workflow should demonstrate proper agent handoffs, state sharing, and collaborative completion"
}
```

#### 3. Memory & Persistence Pattern

```json
{
  "scenario_id": "session_continuity_test",
  "description": "Test session continuity across multiple interactions",
  "query": "Remember that I'm working on a Flask web application. We discussed implementing user authentication. Now I need to add password reset functionality.",
  "expected_tool_use": [
    {
      "tool_name": "session_memory_manager",
      "inputs": {
        "operation": "retrieve_session_context",
        "session_id": "user_session_123",
        "context_keys": ["project_type", "framework", "previous_features"]
      }
    },
    {
      "tool_name": "persistent_memory_tool",
      "inputs": {
        "operation": "load_memory",
        "memory_type": "project_context",
        "filters": ["flask_authentication", "web_development"]
      }
    }
  ],
  "expected_intermediate_agent_responses": [
    {
      "agent_type": "memory_retrieval_agent",
      "response_pattern": "retrieved context about Flask project and authentication work",
      "coordination_actions": ["context_validation", "memory_integration", "continuity_establishment"]
    },
    {
      "agent_type": "development_agent",
      "response_pattern": "password reset implementation building on previous authentication work",
      "coordination_actions": ["context_utilization", "feature_integration", "knowledge_application"]
    }
  ],
  "reference": "Agent should demonstrate clear continuity from previous conversation, referencing Flask project and authentication implementation"
}
```

## Running Evaluation Tests

### Command Line Usage

```bash
# Run all evaluation tests
uv run pytest tests/integration/test_adk_evaluation_patterns.py -v

# Run specific evaluation categories
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_multi_agent_coordination_evaluation -v

# Run with integration suite
./tests/integration/run_integration_tests.py --suite "ADK Evaluation"

# Validate test files structure
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_test_files_exist -v
```

### Integration Test Runner

```bash
# Run complete test suite (traditional + evaluation)
./tests/integration/run_integration_tests.py

# Run only evaluation tests
./tests/integration/run_integration_tests.py --suite "Multi-Agent Coordination Evaluation Tests"
./tests/integration/run_integration_tests.py --suite "Agent Memory and Persistence Evaluation Tests"
```

## Test Configuration

### Configuration File (`test_config.json`)

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.8,
    "response_match_score": 0.7
  },
  "evaluation_settings": {
    "timeout_seconds": 30,
    "max_retries": 3,
    "parallel_execution": true,
    "cache_results": true
  },
  "quality_thresholds": {
    "minimum_scenarios_per_file": 3,
    "maximum_scenario_runtime": 60,
    "required_coverage_patterns": [
      "simple_analysis",
      "multi_agent_coordination",
      "memory_persistence"
    ]
  }
}
```

## Best Practices

### Writing Effective Scenarios

#### 1. Natural Language Queries
```json
// ✅ Good: Natural, realistic user query
{
  "query": "Help me optimize this slow database query that's affecting our user dashboard"
}

// ❌ Bad: Technical, unrealistic query
{
  "query": "Execute SQL optimization algorithm on provided query string"
}
```

#### 2. Specific Tool Expectations
```json
// ✅ Good: Specific tool with clear parameters
{
  "tool_name": "database_query_analyzer",
  "inputs": {
    "query": "SELECT * FROM users WHERE active = 1",
    "database_type": "postgresql"
  }
}

// ❌ Bad: Vague tool expectation
{
  "tool_name": "optimizer",
  "inputs": {
    "data": "some_query"
  }
}
```

#### 3. Realistic Response Patterns
```json
// ✅ Good: Specific, measurable response pattern
{
  "response_pattern": "query performance analysis with specific bottleneck identification",
  "coordination_actions": ["performance_measurement", "optimization_recommendations"]
}

// ❌ Bad: Vague response expectation
{
  "response_pattern": "good response",
  "coordination_actions": ["does_something"]
}
```

### Scenario Categories

#### Core Functionality Tests
- **Basic agent capabilities** - Simple queries and responses
- **Tool usage validation** - Correct tool selection and parameter passing
- **Error handling** - Graceful handling of edge cases

#### Multi-Agent Coordination Tests
- **Workflow orchestration** - Sequential and parallel agent coordination
- **State sharing** - Consistent state management across agents
- **Conflict resolution** - Handling conflicting agent recommendations

#### Memory & Persistence Tests
- **Session continuity** - Maintaining context across interactions
- **Cross-conversation memory** - Retaining information between sessions
- **Knowledge evolution** - Learning and improving over time

### Quality Assurance

#### Scenario Quality Checklist
- [ ] **Clear User Intent** - Query represents realistic user need
- [ ] **Specific Tools** - Expected tools are precisely defined
- [ ] **Measurable Outcome** - Success criteria are clearly defined
- [ ] **Realistic Context** - Scenario reflects actual usage patterns
- [ ] **Coordination Tested** - Multi-agent interactions are validated

#### Common Pitfalls
1. **Overly Technical Queries** - Use natural language, not technical jargon
2. **Vague Expectations** - Be specific about expected tools and responses
3. **Unrealistic Scenarios** - Ensure scenarios mirror actual user interactions
4. **Missing Edge Cases** - Include error conditions and boundary cases
5. **Incomplete Coordination** - Test full agent workflows, not just individual responses

## Maintenance

### Regular Updates

#### Monthly Reviews
1. **Validate tool names** - Ensure tool expectations match current implementations
2. **Update response patterns** - Reflect improvements in agent capabilities
3. **Add new scenarios** - Cover new features and user patterns
4. **Review test results** - Identify degradation or improvement trends

#### Quarterly Assessments
1. **Scenario coverage analysis** - Identify gaps in test coverage
2. **Performance benchmarking** - Track response quality over time
3. **User feedback integration** - Add scenarios based on user issues
4. **Tool usage analysis** - Ensure all critical tools are tested

### Version Control

#### Semantic Versioning
- **Major versions** - Significant changes to evaluation framework
- **Minor versions** - New evaluation scenarios or patterns
- **Patch versions** - Bug fixes and minor updates

#### Change Documentation
```json
{
  "version": "1.2.0",
  "changelog": {
    "added": ["multi_agent_coordination scenarios", "memory_persistence patterns"],
    "modified": ["tool_usage validation criteria"],
    "deprecated": ["legacy_analysis_pattern"],
    "removed": ["outdated_coordination_scenario"]
  }
}
```

## Future Roadmap

### Official ADK Integration
- **Evaluation Module** - Integration with official ADK evaluation when available
- **Standardized Metrics** - Adoption of official ADK evaluation metrics
- **Automated Scoring** - Integration with ADK scoring mechanisms

### Advanced Features
- **Dynamic Scenario Generation** - AI-generated test scenarios
- **Continuous Learning** - Self-improving evaluation criteria
- **Performance Benchmarking** - Automated performance comparison
- **Quality Regression Detection** - Automatic detection of capability degradation

### Community Contribution
- **Scenario Sharing** - Community-contributed evaluation scenarios
- **Pattern Libraries** - Reusable evaluation patterns
- **Best Practice Documentation** - Community-driven best practices

## Troubleshooting

### Common Issues

#### Test Files Not Found
```bash
# Check file existence
ls tests/integration/evaluation_tests/

# Validate JSON structure
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_test_files_exist -v
```

#### Invalid JSON Format
```bash
# Validate JSON syntax
python -m json.tool tests/integration/evaluation_tests/my_test.evalset.json

# Check test structure
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_test_structure -v
```

#### Tool Name Mismatches
```bash
# Validate tool names
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_tool_names_match_agent_tools -v
```

### Debug Mode

Enable verbose logging:
```bash
# Run with debug output
uv run pytest tests/integration/test_adk_evaluation_patterns.py -v -s --log-cli-level=DEBUG
```

## Related Documentation

- [Integration Testing Guide](integration-testing.md) - Complete integration testing overview
- [Test Patterns Guide](test-patterns.md) - Detailed patterns and examples
- [Performance Testing Guide](performance-testing.md) - Performance testing specifics
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions 