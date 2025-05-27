# DevOps Agent Test Suite

This directory contains the comprehensive test suite for the DevOps Agent project, organized into a clear hierarchy for maintainability and ease of use.

## 📁 Directory Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and shared fixtures
├── pytest.ini                 # Pytest settings and configuration
├── README.md                   # This file - test suite documentation
├── unit/                       # Unit tests for individual components
│   ├── __init__.py
│   ├── test_state_management.py    # StateManager and TurnState tests
│   └── test_retry_logic.py         # Error classification and retry tests
├── integration/                # Integration tests for component interactions
│   ├── __init__.py
│   └── test_agent_lifecycle.py     # Complete agent execution flow tests
├── e2e/                        # End-to-end tests for complete workflows
│   └── __init__.py
└── fixtures/                   # Test data and utilities
    ├── __init__.py
    ├── test_helpers.py             # Common test utilities and fixtures
    ├── mock_data.py                # Sample data for testing (future)
    ├── mock_tools.py               # Mock tool implementations (future)
    └── mock_llm.py                 # Mock LLM client for testing (future)
```

## 🧪 Test Categories

### Unit Tests (`unit/`)
Test individual components and functions in isolation:

- **`test_state_management.py`**: Comprehensive tests for StateManager, TurnState, and related classes
  - Basic functionality and lifecycle
  - Error handling and validation
  - Concurrent access protection
  - State transitions and validation

- **`test_retry_logic.py`**: Tests for error classification and retry mechanisms
  - Error classification (retryable vs non-retryable)
  - Context optimization strategies
  - Exponential backoff with jitter
  - Circuit breaker mechanisms

### Integration Tests (`integration/`)
Test interactions between different components:

- **`test_agent_lifecycle.py`**: Complete agent execution flow tests
  - Complete conversation turns
  - Tool execution flow
  - State persistence across turns
  - Error recovery mechanisms
  - Performance characteristics

### End-to-End Tests (`e2e/`)
Test complete workflows and user scenarios (future expansion):

- Conversation flows
- Error recovery workflows
- Performance testing
- Real-world scenarios

### Test Fixtures (`fixtures/`)
Shared utilities and mock objects:

- **`test_helpers.py`**: Common utilities, mock classes, and helper functions
  - Mock objects for all major components
  - Sample data generators
  - Assertion helpers for validation
  - Performance measurement utilities

## 🚀 Quick Start

### Running Tests

```bash
# From the project root directory

# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only

# Run specific test files
uv run pytest tests/unit/test_state_management.py
uv run pytest tests/integration/test_agent_lifecycle.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=devops --cov-report=html
```

### Test Structure Verification

```bash
# Verify test structure is working by running a simple test
uv run pytest tests/unit/test_state_management.py::test_basic_functionality -v
```

## 🔧 Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Custom markers for categorization
- Async test support
- Timeout protection
- Warning filters

### Shared Fixtures (`conftest.py`)
- `state_manager`: Fresh StateManager instance
- `populated_state_manager`: StateManager with sample data
- `mock_agent`: Mock DevOps agent for testing
- `mock_llm_request/response`: Mock LLM interactions
- `test_metrics`: Performance metrics collection

## 📊 Current Test Coverage

### Implemented Tests

✅ **State Management** (Comprehensive)
- 15+ test cases covering StateManager and TurnState
- Error handling and validation
- Concurrent access protection
- Legacy state format compatibility

✅ **Retry Logic** (Comprehensive)  
- 10+ test cases for error classification
- Context optimization strategies
- Retry mechanism testing
- Performance characteristics

✅ **Agent Lifecycle** (Integration)
- 8+ test cases for complete workflows
- Tool execution integration
- Error recovery testing
- Performance benchmarks

### Test Metrics
- **Total Test Cases**: 35+ across all categories
- **Coverage Goal**: >90% for critical components
- **Test Types**: Unit (60%), Integration (30%), E2E (10%)

## 🛠️ Writing New Tests

### Unit Test Template

```python
import pytest
from tests.fixtures.test_helpers import StateManager, TurnPhase

class TestNewFeature:
    def setup_method(self):
        self.state_manager = StateManager()
    
    def test_new_functionality(self):
        # Arrange
        turn = self.state_manager.start_new_turn("Test message")
        
        # Act
        result = self.state_manager.some_new_method()
        
        # Assert
        assert result is not None
        assert turn.phase == TurnPhase.PROCESSING_USER_INPUT
```

### Integration Test Template

```python
import pytest
from tests.fixtures.test_helpers import MockCallbackContext, create_sample_legacy_state

class TestNewIntegration:
    @pytest.mark.asyncio
    async def test_component_interaction(self):
        # Setup
        context = MockCallbackContext(create_sample_legacy_state())
        
        # Test interaction
        result = await some_async_operation(context)
        
        # Verify
        assert result is not None
```

## 📈 Best Practices

1. **Test Organization**: Keep tests organized by component and functionality
2. **Descriptive Names**: Use clear, descriptive test names
3. **AAA Pattern**: Follow Arrange, Act, Assert structure
4. **Mock External Dependencies**: Use mocks for LLM calls, file operations
5. **Test Error Conditions**: Include tests for error scenarios
6. **Use Fixtures**: Leverage shared fixtures for common setup
7. **Add Markers**: Use pytest markers for categorization

## 🐛 Debugging Tests

### Common Issues
- **Import Errors**: Ensure proper path setup for devops_agent imports
- **Async Test Failures**: Use `@pytest.mark.asyncio` for async tests
- **State Pollution**: Use fresh fixtures to avoid interdependencies
- **Mock Issues**: Verify mocks are properly configured

### Debugging Commands
```bash
# Run with debugger
uv run pytest --pdb

# Detailed logging
uv run pytest --log-cli-level=DEBUG

# Single test with max verbosity
uv run pytest -vvv --tb=long tests/path/to/test.py::test_function
```

## 🔄 Continuous Integration

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync --dev
      - name: Run tests
        run: uv run pytest --cov=devops
```

## 📚 Additional Resources

- **Main Testing Guide**: [../docs/TESTING.md](../docs/TESTING.md)
- **Pytest Documentation**: https://docs.pytest.org/
- **Pytest-asyncio**: https://pytest-asyncio.readthedocs.io/

## 🤝 Contributing

When adding new tests:

1. **Choose the Right Category**: Unit, Integration, or E2E
2. **Follow Naming Conventions**: `test_*.py` files, `Test*` classes, `test_*` methods
3. **Add Appropriate Markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
4. **Update Documentation**: Add test descriptions to this README
5. **Run Full Suite**: Ensure all tests pass before submitting

---

**Last Updated**: December 24, 2024  
**Test Structure Version**: 1.0  
**Total Test Files**: 4 (2 unit, 1 integration, 1 fixtures) 