# Gemini Code Assist - Project Guide

This document provides guidance for Gemini Code Assist on how to best interact with the `adk-agents` project.

## Project Overview

The `adk-agents` project is a Python-based initiative focused on DevOps agents with RAG capabilities.

## Conventions and Standards

*   **Python Version:** The project uses Python 3.11.
*   **Dependency Management:** Dependencies are managed with `uv`. Install dependencies using `uv pip install -r requirements.txt` (if a `requirements.txt` is generated) or `uv pip install -e .[dev,test,docs,extensions]` for an editable install with all optional dependencies.
*   **Code Style:**
    *   Formatting: `uv run black --line-length 100 --preview`
    *   Import Sorting: `uv run isort --profile black`
    *   Linting: `uv run flake8 --show-source` and `uv run ruff check .`
*   **Pre-commit:** The project uses pre-commit hooks to enforce code style and linting. Run `pre-commit install` to set up the hooks locally. You can run all pre-commit checks with `pre-commit run --all-files`.
*   **Testing:** Tests are written using `pytest`. Run tests with `uv run pytest`.
*   **Type Checking:** Use `mypy .` for type checking (assuming `mypy` is configured and paths are set up appropriately, or specify relevant source directories).

## Common Commands

*   **Install Dependencies:** `uv pip install -e .[dev,test,docs,extensions]`
*   **Run Linters & Formatters (via pre-commit):** `pre-commit run --all-files`
*   **Run Linters (individually):**
    *   `uv run ruff check .`
    *   `uv run flake8`
*   **Format Code (individually):**
    *   `uv run black . --line-length 100 --preview`
    *   `uv run isort . --profile black`
*   **Run Tests:** `uv run pytest`
*   **Run Tests (individually):** `uv run pytest tests/path/to/test_file.py::test_function_name`
*   **Run Tests with Coverage:** `uv run pytest --cov --cov-fail-under=80`
*   **Run Type Checker:** `uv run mypy .` (adjust path if needed, e.g., `mypy src agents tests`)
*   **Run Agent:** `echo "What is the current time?" | uv run agent run agents.devops`

## Notes for Gemini

*   For specific project details, refer to `AGENT.md`. Always check `AGENT.md` before responding to the user about project specifics.
*   When making changes, please adhere to the existing code style and conventions.
*   Ensure that all tests pass after making modifications.
*   Run linters and formatters before committing changes.
*   If adding new dependencies, update `pyproject.toml` and regenerate lock files if necessary (though `uv` handles this more dynamically).
*   The main application code seems to be in the `agents` and `src/wrapper` directories.
*   Tests are located in the `tests` directory.
