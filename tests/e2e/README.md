# End-to-End Tests

This directory contains the comprehensive end-to-end (e2e) test suite for the ADK agents project.

## 📁 Test Organization

### CLI Tests (`tests/e2e/cli/`)
Comprehensive test coverage for all CLI functionality, organized by function:

- **`test_cli_commands.py`** - CLI command interface tests (help, create commands)
- **`test_run_cli.py`** - Tests for the `run_cli` function (5 tests)
  - Input file processing
  - Saved session loading
  - Interactive mode
  - TUI mode activation  
  - Session persistence
- **`test_run_interactively.py`** - Tests for the `run_interactively` function (4 tests)
  - Enhanced UI flow
  - Fallback mode handling
  - Special commands (help, clear, theme)
  - Thought content processing
- **`test_run_interactively_with_tui.py`** - Tests for the `run_interactively_with_tui` function (4 tests)
  - TUI initialization
  - Tool callback setup
  - Input callback registration
  - Error handling
- **`conftest.py`** - Shared fixtures for consistent mocking across CLI tests

**Total CLI Coverage**: 15 tests covering all three main CLI functions

## 🚀 Running Tests

### Local Testing
```bash
# Run all e2e tests
uv run pytest tests/e2e/ -v

# Run CLI tests only
uv run pytest tests/e2e/cli/ -v

# Run with coverage
uv run pytest tests/e2e/cli/ --cov=src.wrapper.adk --cov-report=term
```

### Using the E2E Script
```bash
# Run the comprehensive e2e test suite
./scripts/run_e2e_tests.sh
```

This script will:
- ✅ Install dependencies
- ✅ Run all organized CLI tests
- ✅ Generate JUnit XML reports
- ✅ Provide detailed logging and status

## 📊 Coverage

The e2e tests provide coverage for:
- **`src.wrapper.adk.cli`** - CLI functionality (66%+ coverage)
- **`agents.devops`** - Agent implementation 
- Integration points between components

## 🔧 GitHub Workflows

The following workflows have been updated to use our organized tests:

- **`test-e2e.yml`** - Runs the e2e script for comprehensive testing
- **`test-coverage.yml`** - Generates coverage reports with correct module paths
- **`pr-workflow.yml`** - Runs tests with coverage on pull requests

All workflows now:
- ✅ Use correct module paths (`agents`, `src.wrapper.adk`)
- ✅ Include our organized CLI tests
- ✅ Generate proper coverage reports
- ✅ Support both specific module testing and full test suite runs

## 📋 Test Structure Standards

When adding new e2e tests:

1. **Organize by functionality** - Group related tests in focused files
2. **Use descriptive names** - `test_[function_name].py` format
3. **Share fixtures** - Use `conftest.py` for common mocking patterns
4. **Mock appropriately** - Use `MagicMock` for sync methods, `AsyncMock` for async
5. **Test coverage** - Include both happy path and error scenarios
