# Real Integration Tests

This directory contains real integration tests that actually invoke the agents with API calls, not just mocked unit tests. These tests are critical for catching runtime issues that mocked tests might miss.

## Purpose

The real integration tests in `test_contextual_awareness_real_agent_invocation.py` serve to:

1. **Catch Runtime Issues**: Test actual agent invocation to catch callback errors, import issues, and other runtime problems
2. **Validate End-to-End Functionality**: Ensure the contextual awareness system works in production conditions
3. **Test Real API Integration**: Verify that agents work correctly with actual LLM API calls
4. **Prevent Regression**: Catch issues that mocked tests might miss due to incomplete mocking

## Requirements

### API Keys
These tests require a valid API key:
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable must be set

### Dependencies
- All standard project dependencies
- Internet connection for API calls

## Running the Tests

### Run All Real Integration Tests
```bash
# Set your API key first
export GEMINI_API_KEY="your_api_key_here"

# Run only the real integration tests
uv run pytest tests/integration/test_contextual_awareness_real_agent_invocation.py -v
```

### Run Specific Test Categories
```bash
# Test contextual callback initialization
uv run pytest tests/integration/test_contextual_awareness_real_agent_invocation.py::TestRealContextualAwarenessIntegration::test_contextual_callback_initialization_with_real_agent -v

# Test shell command execution
uv run pytest tests/integration/test_contextual_awareness_real_agent_invocation.py::TestRealContextualAwarenessIntegration::test_shell_command_execution_with_real_agent -v

# Test enhanced agent
uv run pytest tests/integration/test_contextual_awareness_real_agent_invocation.py::TestRealContextualAwarenessIntegration::test_enhanced_agent_contextual_awareness -v
```

### Skip Real Integration Tests
If you don't have an API key or want to skip these tests:
```bash
# These tests are automatically skipped if no API key is found
uv run pytest tests/integration/ -v
# Real integration tests will show as "SKIPPED" with reason
```

## Test Categories

### 1. Contextual Callback Tests
- `test_contextual_callback_initialization_with_real_agent`: Tests that the contextual awareness callback is properly executed and initializes session state
- `test_contextual_awareness_across_multiple_messages`: Tests persistence across multiple agent interactions

### 2. Shell Command Tests  
- `test_shell_command_execution_with_real_agent`: Tests shell command execution and history capture
- `test_error_pattern_detection_with_real_commands`: Tests error pattern detection with actual failing commands

### 3. Agent Loading Tests
- `test_software_engineer_agent_loads_with_callbacks`: Verifies the basic agent loads with contextual callbacks
- `test_enhanced_agent_loads_with_callbacks`: Verifies the enhanced agent loads with contextual callbacks
- `test_enhanced_agent_contextual_awareness`: Tests the enhanced agent with contextual awareness features

## Expected Behavior

### Successful Tests
When running with a valid API key, you should see:
```
tests/integration/test_contextual_awareness_real_agent_invocation.py::TestRealContextualAwarenessIntegration::test_contextual_callback_initialization_with_real_agent PASSED
tests/integration/test_contextual_awareness_real_agent_invocation.py::TestRealContextualAwarenessIntegration::test_shell_command_execution_with_real_agent PASSED
...
```

### Skipped Tests
When running without an API key:
```
tests/integration/test_contextual_awareness_real_agent_invocation.py::TestRealContextualAwarenessIntegration::test_contextual_callback_initialization_with_real_agent SKIPPED (GEMINI_API_KEY or GOOGLE_API_KEY required)
```

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```
   SKIPPED - GEMINI_API_KEY or GOOGLE_API_KEY required
   ```
   **Solution**: Set your API key: `export GEMINI_API_KEY="your_key"`

2. **Agent Loading Failures**
   ```
   ImportError: No module named 'agents.software_engineer.agent'
   ```
   **Solution**: Ensure you're running from the project root directory

3. **Timeout Errors**
   ```
   asyncio.TimeoutError
   ```
   **Solution**: Expected behavior - tests use timeouts to prevent infinite loops

4. **Callback Not Found**
   ```
   AssertionError: Expected contextual callback in []
   ```
   **Solution**: This indicates the contextual awareness callback isn't properly registered

## Integration with CI/CD

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Real Integration Tests
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  run: |
    if [ -n "$GEMINI_API_KEY" ]; then
      uv run pytest tests/integration/test_contextual_awareness_real_agent_invocation.py -v
    else
      echo "Skipping real integration tests - no API key"
    fi
```

## Why These Tests Matter

The contextual awareness issue we recently fixed (callback using wrong session state access pattern) would have been caught immediately by these real integration tests, rather than requiring manual testing to discover the runtime error.

These tests ensure that:
- Callbacks are properly executed
- Session state is correctly accessed
- Import paths are valid
- Data formats match between components
- Agents actually work in production conditions 