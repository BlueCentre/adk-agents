# DevOps Agent Test Suite

This directory contains the comprehensive test suite for the DevOps Agent project, organized into a clear hierarchy for maintainability and ease of use.

## Test Suite Overview

The test suite is designed to ensure the reliability, correctness, and performance of the DevOps Agent. It is divided into several categories, each serving a specific purpose.

- **Unit Tests (`unit/`)**: These tests focus on individual components in isolation, ensuring that each function, method, and class behaves as expected. They are fast, lightweight, and form the foundation of our testing strategy.
- **Integration Tests (`integration/`)**: These tests verify the interactions between different components of the agent, ensuring they work together correctly. They cover workflows, agent lifecycles, and interactions with external systems (in a mocked or real environment).
- **End-to-End (E2E) Tests (`e2e/`)**: E2E tests validate complete user workflows from start to finish, simulating real-world scenarios as closely as possible.
- **Performance Tests (`performance/`)**: These tests measure the agent's performance characteristics, including response time, resource usage, and scalability under load.

## 📁 Directory Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and global fixtures
├── pytest.ini                 # Pytest settings and configuration
├── README.md                   # This file - test suite documentation
├── unit/                       # Unit tests for individual components
│   └── ...
├── integration/                # Integration tests for component interactions
│   └── ...
├── e2e/                        # End-to-end tests for complete workflows
│   └── ...
├── performance/                # Performance and load tests
│   └── ...
└── utils/                      # Shared test utilities and helpers
    ├── __init__.py
    └── ...
```

## 🧪 Test Categories

## How to Run Tests

### Running All Tests
To run the entire test suite, use the following command from the project root:
```bash
uv run pytest
```

### Running Specific Test Types
You can run tests for a specific category by targeting the respective directory:
```bash
# Run all unit tests
uv run pytest tests/unit/

# Run all integration tests
uv run pytest tests/integration/

# Run all end-to-end tests
uv run pytest tests/e2e/
```

### Running a Specific File or Test
To run a specific test file or a single test function:
```bash
# Run a single test file
uv run pytest tests/unit/test_state_management.py

# Run a specific test class
uv run pytest tests/unit/test_state_management.py::TestStateManager

# Run a single test method
uv run pytest tests/unit/test_state_management.py::TestStateManager::test_basic_functionality
```

### Code Coverage
To generate a code coverage report, use the `--cov` flag. The report will be saved in an `htmlcov/` directory.
```bash
# Generate a coverage report for the `src` directory
uv run pytest --cov=src --cov-report=html

# View the report
open htmlcov/index.html
```

## Contributing to the Test Suite

We welcome contributions to improve the test suite. Please follow these guidelines to ensure consistency and quality.

### Writing New Tests

1.  **Choose the Right Location**: Place your test file in the appropriate directory (`unit`, `integration`, `e2e`, `performance`) based on its purpose.
2.  **Follow Naming Conventions**:
    *   Test files must be named `test_*.py`.
    *   Test classes should be named `Test<ComponentName>`.
    *   Test functions must be named `test_*`.
3.  **Use Fixtures for Setup**: Use `pytest` fixtures for any setup and teardown logic. Global fixtures are in `tests/conftest.py`, while directory-specific fixtures can be placed in a local `conftest.py`.
4.  **Leverage Shared Utilities**: Reusable test helpers and utilities are located in the `tests/utils/` directory. Use them to avoid code duplication.
5.  **Write Clear Assertions**: Ensure your tests have clear and specific assertions. Use `pytest`'s `assert` statement.
6.  **Mock External Dependencies**: For unit tests, mock all external dependencies, such as API calls, database connections, and file system operations.

### Best Practices

*   **Keep Tests Independent**: Tests should not depend on the state left by other tests. Each test should be able to run in isolation.
*   **Test One Thing at a Time**: Each test function should verify a single piece of functionality.
*   **Arrange, Act, Assert**: Structure your tests using the Arrange-Act-Assert pattern for clarity.
*   **Update Documentation**: If you add a new test file or a significant number of tests, update the relevant `README.md` to reflect the changes.

---

**Last Updated**: July 27, 2024