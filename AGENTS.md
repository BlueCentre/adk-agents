# Agent Guidelines for adk-agents Repository

This document outlines essential commands and code style guidelines for agents operating in this repository.

## Build, Lint, and Test Commands

-   **Install dependencies:** `uv pip install -e ".[dev,test]"`
-   **Run all tests:** `uv run pytest`
-   **Run a single test:** `uv run pytest tests/path/to/your_test_file.py::test_function_name`
-   **Linting (Python):** `uv run pylint src/` or `uv run flake8 src/` (max line length 200)
-   **Formatting (Python):** `uv run pyink src/`
-   **Type Checking (Python):** `uv run mypy src/`

## Code Style Guidelines

-   **Imports:** Use `uv run isort` for sorting imports.
-   **Formatting:** Adhere to `uv run pyink` formatting standards. Max line length is 200 characters.
-   **Types:** Use Python type hints extensively for clarity and maintainability.
-   **Naming Conventions:** Follow standard Python naming conventions (e.g., `snake_case` for functions/variables, `CamelCase` for classes).
-   **Error Handling:** Prefer explicit exception handling over silent failures. Log errors appropriately.
-   **General:** Mimic existing code style and patterns within the codebase. Avoid adding comments unless explici