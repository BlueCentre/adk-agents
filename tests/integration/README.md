# Integration Tests

This directory contains comprehensive integration tests for the ADK Agents system, organized by feature and component categories for improved maintainability and clarity.

## Directory Structure

The integration tests are organized into logical subdirectories based on the features and components they test:

### 📁 Test Categories

#### **`agents/`** - Agent Lifecycle and Behavior Tests
Tests that focus on individual agents, their loading, lifecycle, and core behaviors:
- `test_agent_lifecycle.py` - Complete agent conversation turns and lifecycle management
- `test_agent_loading_real.py` - Real agent loading with API integration
- `test_enhanced_agent_feature_parity.py` - Enhanced agent feature validation
- `test_single_agent_patterns.py` - Single agent workflow patterns
- `test_sub_agent_delegation.py` - Sub-agent delegation and coordination
- `test_sub_agent_mcp_loading.py` - MCP (Model Context Protocol) loading for sub-agents
- `test_swe_agent_callbacks.py` - Software engineering agent callback systems

#### **`context_management/`** - Context Awareness and Management Tests
Tests that verify contextual awareness features and context management systems:
- `test_context_management_advanced.py` - Advanced context management with RAG integration
- `test_contextual_awareness_basic_integration.py` - Basic contextual awareness (file system & open files)
- `test_contextual_awareness_shell_integration.py` - Shell command history & error log context
- `test_contextual_awareness_advanced_integration.py` - Advanced project context (dependencies, project structure)
- `test_contextual_awareness_real_agent_invocation.py` - Real agent invocation with context
- `test_real_agent_contextual_behavior.py` - Real agent contextual behavior validation

#### **`workflows/`** - Workflow Orchestration Tests
Tests for workflow guidance, orchestration, and step-by-step process management:
- `test_workflow_integration.py` - Sequential, parallel, iterative, and human-in-loop workflow patterns
- `test_workflow_guidance_integration.py` - Basic workflow guidance and next step suggestions  
- `test_workflow_guidance_end_to_end.py` - End-to-end workflow guidance validation
- `test_workflow_guidance_real_agent_behavior.py` - Real agent workflow behavior testing

#### **`optimization/`** - Performance and Proactive Optimization Tests
Tests for optimization systems, token management, and proactive suggestions:
- `test_proactive_error_detection_integration.py` - Proactive error detection and fix suggestions
- `test_proactive_optimization_integration.py` - Proactive code optimization suggestions
- `test_proactive_optimization_ux_integration.py` - UX-focused optimization workflow testing
- `test_advanced_token_optimization_integration.py` - Advanced token usage optimization
- `test_token_optimization_integration.py` - Basic token optimization and budget management

#### **`tools_system/`** - Tool Orchestration and System Integration Tests
Tests for tool coordination, system instructions, callbacks, and retry mechanisms:
- `test_tool_orchestration_advanced.py` - Advanced tool coordination with error handling
- `test_system_instruction_compliance.py` - System instruction adherence validation
- `test_callback_return_values_integration.py` - Callback system return value handling
- `test_retry_system_integration.py` - Retry mechanism and error recovery

#### **`performance/`** - Performance and Load Testing
Tests focused on performance validation, load testing, and stress testing:
- `test_performance_verification.py` - Comprehensive performance and load testing suite

#### **`evaluation_tests/`** - ADK Evaluation Framework
Behavioral testing using evaluation scenarios for real-world validation:
- Contains `.evalset.json` files with evaluation scenarios
- See `tests/integration/test_adk_evaluation_patterns.py` for evaluation test execution

## Naming Conventions

### Integration Test File Naming
All integration test files follow the pattern: `test_<feature>_integration.py`

**Examples:**
- `test_contextual_awareness_basic_integration.py` - Tests basic contextual awareness features
- `test_proactive_error_detection_integration.py` - Tests proactive error detection systems
- `test_workflow_guidance_integration.py` - Tests workflow guidance functionality

### Test Class and Method Naming
- **Test Classes**: `TestFeatureNameIntegration` or `TestFeatureNameBehavior`
- **Test Methods**: `test_<specific_functionality>_<test_scenario>`

**Examples:**
```python
class TestContextualAwarenessIntegration:
    def test_file_system_context_capture_with_agent_query(self):
    def test_shell_command_history_integration_with_callbacks(self):
```

## Running Tests

### Run All Integration Tests
```bash
# Run all integration tests with coverage
uv run pytest tests/integration/ --cov=src --cov-config=pyproject.toml --cov-report=term -v

# Run integration tests with the comprehensive runner
./tests/integration/run_integration_tests.py --verbose
```

### Run Tests by Category
```bash
# Run agent-related tests only
uv run pytest tests/integration/agents/ -v

# Run context management tests only  
uv run pytest tests/integration/context_management/ -v

# Run workflow tests only
uv run pytest tests/integration/workflows/ -v

# Run optimization tests only
uv run pytest tests/integration/optimization/ -v

# Run tool and system tests only
uv run pytest tests/integration/tools_system/ -v

# Run performance tests only
uv run pytest tests/integration/performance/ -v
```

### Run Specific Test Files
```bash
# Run a specific test file
uv run pytest tests/integration/agents/test_agent_lifecycle.py -v

# Run specific test classes or methods
uv run pytest tests/integration/context_management/test_contextual_awareness_basic_integration.py::TestContextualAwarenessIntegration::test_file_system_context_capture -v
```

### Real Integration Tests (Requires API Keys)
Some tests require actual API keys for real agent invocation:
```bash
# Set API key for real integration tests
export GEMINI_API_KEY="your_api_key_here"

# Run real integration tests
uv run pytest tests/integration/context_management/test_contextual_awareness_real_agent_invocation.py -v
```

## Test Suite Features

### Comprehensive Coverage
- **Agent Lifecycle Testing**: Complete conversation turns with context management  
- **Workflow Orchestration**: Sequential, parallel, iterative, and human-in-loop patterns
- **Context Management**: Smart prioritization, cross-turn correlation, and RAG integration
- **Tool Orchestration**: Advanced tool coordination with error handling
- **Performance Validation**: Load testing, optimization validation, and stress testing
- **Behavioral Testing**: Real agent behavior validation using evaluation scenarios

### Testing Approaches
1. **Traditional Integration Testing** - Component interaction validation
2. **Real Agent Testing** - Actual API calls without mocking  
3. **ADK Evaluation Framework** - Behavioral testing with evaluation scenarios
4. **Performance Testing** - Load testing and resource usage validation

## Contributing New Tests

### Adding Tests to Existing Categories
1. Choose the appropriate subdirectory based on the feature being tested
2. Follow the naming convention: `test_<feature>_integration.py`
3. Use appropriate fixtures from `conftest.py`
4. Include comprehensive docstrings describing test purpose

### Creating New Test Categories
If your tests don't fit existing categories:
1. Create a new subdirectory with a descriptive name
2. Add an `__init__.py` file to make it a Python package
3. Update this README to document the new category
4. Follow the established patterns for test organization

### Test Quality Guidelines
- **Clear Purpose**: Each test should have a single, well-defined purpose
- **Comprehensive Coverage**: Test both success and failure scenarios
- **Real Integration**: Prefer real integration over mocking where feasible
- **Performance Awareness**: Consider performance implications of test execution
- **Documentation**: Include clear docstrings and comments

## Fixtures and Utilities

### Global Fixtures (`conftest.py`)
The root-level `conftest.py` provides shared fixtures for:
- Mock agent creation and configuration
- Session state management
- API key validation and setup
- Test environment preparation

### Shared Utilities  
For reusable test utilities and helpers, see the main `tests/` directory structure.

## Related Documentation

- **[Integration Testing Guide](../../docs/tests/integration-testing.md)** - Comprehensive testing approach overview
- **[ADK Evaluation Framework](../../docs/tests/adk-evaluation-framework.md)** - Behavioral testing patterns
- **[Test Patterns Guide](../../docs/tests/test-patterns.md)** - Architectural testing decisions
- **[Performance Testing Guide](../../docs/tests/performance-testing.md)** - Performance testing specifics

## Troubleshooting

### Common Issues
1. **Missing API Keys**: Real integration tests require `GEMINI_API_KEY` or `GOOGLE_API_KEY`
2. **Import Errors**: Ensure you're running tests from the project root directory
3. **Timeout Errors**: Expected behavior for tests with timeout protection
4. **Path Issues**: Verify that subdirectory imports are working correctly

### Test Execution Tips
- Use `-v` flag for verbose output to understand test execution flow
- Run specific categories when debugging to isolate issues
- Check fixture availability if tests fail with fixture not found errors
- Use `--pdb` flag to drop into debugger on test failures 