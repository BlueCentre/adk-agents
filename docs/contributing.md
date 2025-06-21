---
layout: default
title: Contributing
nav_order: 4
description: "Learn how to contribute to the DevOps Agent project."
---

# Contributing to the DevOps Agent

We welcome contributions from the community to enhance the DevOps Agent! Whether you're interested in fixing bugs, adding new features, improving documentation, or refining the agent's logic, your help is appreciated.

## Understanding Agent Modification

A key aspect of contributing to this project is understanding how the agent's own code can be modified. The `AGENT.md` file in the repository root contains critical directives:

- **Core LLM vs. Application Code:** The agent differentiates between its core LLM architecture (provided by Google, not modifiable by users/contributors directly through this repo) and its **Application Code** (Python scripts, configs like `AGENT.md` itself, located within the project).
- **Modifiable Application Code:** When discussing changes to "the agent" or "its logic" in the context of this project, it typically refers to this modifiable application code.
- **File Editing Tools:** The agent can use its file editing tools to modify its own application code, with explicit user guidance and approval.

If you plan to contribute by modifying the agent's behavior or prompts, familiarize yourself with the `AGENT.md` file.

## Getting Started

1.  **Fork the Repository:** Start by forking the main DevOps Agent repository to your GitHub account.
2.  **Clone Your Fork:**
    ```bash
    git clone https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git # Replace with your fork's URL
    cd YOUR-REPO-NAME
    ```
3.  **Set Up Development Environment:**
    - The project uses Python (see `README.md` for version) and `uvx` for running.
    - Install any development dependencies (often found in `pyproject.toml` under `[project.optional-dependencies].dev` or similar).
    - Familiarize yourself with the `scripts/execution/run.sh` script for local execution.
4.  **Create a Branch:** Create a new branch for your feature or bug fix:
    ```bash
    git checkout -b your-feature-branch-name
    ```

## Development Guidelines

- **Directory Structure:** Understand the project's [directory structure as outlined in the README.md](./#directory-structure) to locate relevant files. Core agent logic is primarily within the `agents/devops/` directory.
- **Coding Standards:**
    - Follow existing code style and patterns.
    - The project uses `pre-commit` hooks (see `.pre-commit-config.yaml`) for linting and formatting. Ensure you have `pre-commit` installed and hooks set up (`pre-commit install`).
- **Testing:** (Details on testing infrastructure would ideally be here - e.g., "Run tests using `pytest`." or specific script commands from `scripts/validation/` or `tests/`). Add or update tests for your changes.
- **Documentation:** If you add or change features, update relevant documentation in the `docs/` directory.

## Submitting Changes

1.  **Commit Your Changes:** Make clear, atomic commits.
    ```bash
    git add .
    git commit -m "feat: Describe your feature or fix"
    ```
2.  **Push to Your Fork:**
    ```bash
    git push origin your-feature-branch-name
    ```
3.  **Create a Pull Request (PR):**
    - Go to the original DevOps Agent repository on GitHub.
    - You should see a prompt to create a PR from your new branch.
    - Fill out the PR template (from `.github/PULL_REQUEST_TEMPLATE.md`) with details about your changes.
    - Ensure your PR passes any automated checks or CI workflows.
4.  **Code Review:** Project maintainers will review your PR. Be prepared to discuss your changes and make adjustments.

## Reporting Bugs

- Use the GitHub Issues tab in the repository.
- Check if the bug has already been reported.
- Fill out the bug report template (from `.github/ISSUE_TEMPLATE.md`) with as much detail as possible, including:
    - Steps to reproduce the bug.
    - Expected behavior.
    - Actual behavior.
    - Your environment details (OS, Python version, agent version if applicable).

## Questions?

Feel free to ask questions by opening an issue or (if available) joining a community discussion forum/chat.

Thank you for your interest in contributing to the DevOps Agent!
