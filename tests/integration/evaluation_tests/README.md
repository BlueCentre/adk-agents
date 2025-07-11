# ADK Evaluation Tests

This directory contains evaluation test scenarios for the ADK Agents system using the ADK Evaluation Framework.

## Overview

Evaluation tests validate **agent behavior** rather than just system structure. They use natural language queries and expect specific tool usage patterns, agent responses, and outcomes.

## File Structure

```
evaluation_tests/
├── simple_code_analysis.evalset.json      # Basic agent functionality (3 scenarios)
├── sub_agent_delegation.evalset.json      # Agent hierarchy patterns (3 scenarios)
├── tool_usage.evalset.json                # Tool usage validation (3 scenarios)
├── multi_agent_coordination.evalset.json  # Multi-agent coordination (6 scenarios)
├── agent_memory_persistence.evalset.json  # Memory & persistence (7 scenarios)
├── test_config.json                       # Configuration settings
└── README.md                              # This file
```

## Test Scenarios

### Simple Code Analysis
- Basic code analysis capabilities
- Error detection and recommendations
- Code quality assessment

### Sub-Agent Delegation
- Hierarchical agent communication
- Task delegation patterns
- Parent-child agent relationships

### Tool Usage
- Tool selection and parameter validation
- Correct tool usage in context
- Tool coordination patterns

### Multi-Agent Coordination
- Workflow orchestration between agents
- Parallel and sequential coordination
- Conflict resolution and result aggregation
- Shared state management

### Agent Memory & Persistence
- Session continuity across interactions
- Cross-conversation memory retention
- Knowledge evolution and learning
- Context awareness and retrieval

## Running Evaluation Tests

```bash
# Run all evaluation tests
uv run pytest tests/integration/test_adk_evaluation_patterns.py -v

# Run specific evaluation categories
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_multi_agent_coordination_evaluation -v

# Validate test file structure
uv run pytest tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_test_files_exist -v
```

## JSON File Format

Each `.evalset.json` file follows this structure:

```json
{
  "test_name": "Descriptive name",
  "description": "What this test validates",
  "version": "1.0.0",
  "test_scenarios": [
    {
      "scenario_id": "unique_identifier",
      "description": "What this scenario tests",
      "query": "Natural language user query",
      "expected_tool_use": [
        {
          "tool_name": "specific_tool",
          "inputs": {
            "parameter": "expected_value"
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
      "reference": "Expected outcome description"
    }
  ],
  "evaluation_criteria": {
    "criterion1": "What this measures",
    "criterion2": "What this measures"
  }
}
```

## Configuration

The `test_config.json` file contains:
- Evaluation criteria thresholds
- Timeout settings
- Quality requirements
- Performance parameters

## Best Practices

1. **Natural Language Queries** - Write queries as users would ask them
2. **Specific Tool Expectations** - Define exact tool names and parameters
3. **Realistic Scenarios** - Mirror actual user interactions
4. **Clear Outcomes** - Define measurable success criteria
5. **Edge Cases** - Include error conditions and boundary cases

## Adding New Evaluation Tests

1. Create a new `.evalset.json` file following the format above
2. Add validation for your new file in `test_adk_evaluation_patterns.py`
3. Update the integration test runner to include your new test
4. Test your scenarios thoroughly before committing

## Documentation

For complete documentation on the ADK Evaluation Framework, see:
- [ADK Evaluation Framework Guide](../../../docs/tests/adk-evaluation-framework.md)
- [Integration Testing Guide](../../../docs/tests/integration-testing.md)
- [Test Patterns Guide](../../../docs/tests/test-patterns.md)

## Contributing

When adding new evaluation scenarios:
1. Follow the established JSON format
2. Use meaningful scenario IDs and descriptions
3. Include realistic user queries
4. Define specific tool expectations
5. Test thoroughly before submitting 