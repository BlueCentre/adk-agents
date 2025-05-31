# Agent Context and Instructions

This document provides context about the user's environment and preferences to help the DevOps agent work more effectively.

**Agent Instructions:** Always read this file *first* at the beginning of a new conversation to understand the environment before proceeding.

### CRITICAL: Understanding Agent Modification Capabilities

**This is a non-negotiable directive for interpreting user requests regarding agent improvements or changes:**

1.  **Differentiate Scope:** When the user asks to "change your code," "improve your logic," "fix your prompts," or similar, you MUST first differentiate between:
    *   **A) Your Core LLM Architecture:** This is the fundamental AI model provided by your creators (Google). You CANNOT modify this yourself.
    *   **B) This Agent's Application Code:** This refers to the Python scripts, configuration files (including this `AGENT.MD` file), and other artifacts located within the user's project directory (e.g., the 'devops/' subdirectory within the project's Current Working Directory (CWD), or this `AGENT.MD` file itself). This code DEFINES THIS SPECIFIC AGENT'S BEHAVIOR and CAN BE MODIFIED using your file editing tools, with explicit user guidance and approval.

2.  **Default Interpretation for THIS Project:** Given the context of this project and the presence of modifiable application code (e.g., in `devops/`), if the user requests a change or improvement to "you" or "your logic," your **default assumption** should be that they are referring to **(B) This Agent's Application Code**, unless they explicitly state they mean your core LLM.

3.  **Communication Protocol:**
    *   If there is any ambiguity, explicitly state both A) and B) in your response to clarify the scope of potential changes.
    *   When discussing changes to this agent's application code, clearly state that these changes are to files within the project and require user guidance for implementation (e.g., specifying file paths and code edits).

4.  **Avoid Incorrect Denials:** DO NOT state that you "cannot change your own code" if the user is likely referring to this agent's modifiable application code within the project. This has been a significant point of friction and must be avoided.

**Failure to adhere to this directive will result in unproductive and frustrating interactions. This directive supersedes any general notions you have about your immutability when operating within this specific project context.**

## Directory Structure

*This section describes the main project directories, their purpose, and common locations for specific file types. It's based on an agent scan of the current working directory.*

*   `devops/`: Likely contains DevOps-related scripts, configurations, or source code.
    *   `docs/`: Documentation files.
        *   `FEATURE_RAG.md`: Documentation for RAG feature.
        *   `FEATURE_AGENT_LOOP_OPTIMIZATION.md`: Documentation for agent loop optimization.
        *   `REFACTOR_CONTEXT_MANAGER_2_CONTEXT_STATE.md`: Documentation for refactoring context manager.
        *   `FEATURE_AGENT_INTERACTIVE_PLANNING.md`: Documentation for interactive planning feature.
    *   `components/`: Various components of the agent.
        *   `__init__.py`: Python package indicator.
        *   `context_management/`: Components for context management.
        *   `planning_manager.py`: Manages agent planning.
    *   `shared_libraries/`: Shared Python libraries.
        *   `__init__.py`: Python package indicator.
        *   `ui.py`: UI-related library.
        *   `types.py`: Custom type definitions.
    *   `tools/`: Contains various tools used by the agent.
        *   `__init__.py`: Python package indicator.
        *   `setup.py`: Python package setup script.
        *   `shell_command.py`: Likely handles shell command execution.
        *   `persistent_memory_tool.py`: Tool for managing persistent memory.
        *   `memory_tools.py`: Tools related to memory management.
        *   `filesystem.py`: Filesystem interaction tools.
        *   `rag_tools.py`: Tools for Retrieval Augmented Generation.
        *   `file_summarizer_tool.py`: Tool for summarizing file content.
        *   `analysis_state.py`: Manages analysis state.
        *   `project_context.py`: Manages project context.
        *   `search.py`: Search-related tools.
        *   `code_analysis.py`: Tools for code analysis.
        *   `rag_components/`: Components for RAG.
        *   `code_search.py`: Tools for code search.
    *   `__init__.py`: Python package indicator.
    *   `.indexignore`: Specifies files to ignore during indexing.
    *   `config.py`: Configuration file for the DevOps agent.
    *   `prompts.py`: Contains prompts for the agent.
    *   `devops_agent.py`: Main DevOps agent script.
    *   `agent.py`: Core agent logic.
*   `.cache/`: Cache directory, likely for build artifacts or other temporary files.
*   `.env.example`: Example environment variable file.
*   `.env`: Environment variable file (typically for development, should not be committed).
*   `AGENT.md`: This file, containing agent context and instructions.
*   `README.md`: Project README file.
*   `pyproject.toml`: Python project configuration file (PEP 518).

**(Please review this refined list. You can add descriptions, specify important subdirectories, or remove any entries that aren't relevant for your DevOps workflows.)**

**IMPORTANT**: When the user mentions `current working directory`, you will use `pwd` to figure out the directory

## Common Tools Available

*   **Version Control:** `git`
*   **Source Code Management:** `gh`
*   **Containerization:** `docker`
*   **Orchestration:** `kubectl`
*   **IaC:** `terraform`
*   **Scripting/Languages:** `python`
*   **Python Env/Pkg Mgmt:** `uv`
*   **Node.js/Frontend:** `npm`
*   **CI/CD Platform:** (e.g., GitHub Actions, GitLab CI, Jenkins - *Please specify*)
*   **Cloud Provider CLI:** `gcloud`
*   **Task Management:** `jira` (**use** 'jira me' to get user)
*   **Secrets Management:** `bw` (Bitwarden CLI - Confirmed installed)
*   **Monitoring/Observability:** `datadog-ci` (Confirmed installed at `/Users/$HOME/bin/datadog-ci`)

*(Note: `yamllint` and `tfsec` were not found in the PATH during the initial check.)*

## Preferred Practices & Notes

*   *(Example: Prefer multi-stage Docker builds)*
*   *(Example: Use Terraform modules from registry X)*
*   *(Example: Default cloud region is us-central1)*
*   **(Add any other relevant preferences, common workflows, or important notes here)**

## Core DevOps Workflows:
1.  **Understand Request & Context:** Clarify user's goal (e.g., CI setup, Dockerfile, deployment issue). Identify relevant tech (cloud, CI, IaC) from `project_context`, existing config/code, or user (last resort).
    *   **Probe for tools:** Try to use these common tools (e.g., `bw`, `jira`, `gh`, `gcloud`, `git`, `kubectl`, `docker`, `terraform`, `pulumi`, `uvx`, `uv`, `npm`, `skaffold`, `bazel`, `yamllint`, `tfsec`).
2.  **Analyze Config & Code:**
    *   `list_directory`: Locate config files (e.g., `.github/workflows/`, `Dockerfile`, `terraform/`, `Makefile`).
    *   **File Operations Strategy:**
        *   To find specific patterns or text in files (especially code/config), prefer `ripgrep_code_search`.
        *   To understand the content of a file:
            *   First, consider using `get_file_info` to check its size.
            *   If the file is large and you need a summary or specific extractions, use the `summarize_large_file_content` tool. Provide clear `instructions` to this tool for best results.
            *   If the file is small, or you need its exact full content, use `read_file` (or your custom `read_file_tool`).
            *   For MCP-enabled environments, prefer MCP file tools for direct operations if appropriate.
        *   For modifications, use `edit_file`/`write_file` (or MCP equivalents), respecting approval workflows.
    *   Analyze build/task files (`Makefile`, `package.json` scripts) for existing build/test/deploy logic.
3.  **Research & Planning:** Use `google_search_grounding` if external info needed (prioritize official docs, reputable repos). Formulate robust plan.
4.  **Execute & Validate (Use Shell Workflow Cautiously):**
    *   Read-only/validation: Safe shell workflow for `docker build --dry-run`, `terraform validate`, linters using `execute_vetted_shell_command`.
    *   State-changing: **EXTREME caution.** Always require explicit user approval via shell mechanism, even if whitelisted. State command/impact clearly using `execute_vetted_shell_command`.
    *   Complex scripting: You can generate and execute scripts using the `code_execution` tool.
5.  **Generate/Modify Configs:** Output in **markdown**. Generate config files (Dockerfile, YAML, HCL) with best practices. Use `edit_file` or `write_file` (or MCP equivalent) for new/modified files (respects approval). Lint/format generated configs (e.g
`actionlint`, `tfsec`) via shell workflow using `execute_vetted_shell_command`.
6.  **Execution & Output:** Execute. Present results, logs, file paths in **markdown**. State modified file if `edit_file` or `write_file` used.

## Specific Task Guidance (Examples):
*   **CI/CD:** Analyze pipelines. Generate basic configs (e.g., GitHub Actions YAML).
*   **Containerization:** Analyze/generate Dockerfiles (multi-stage, optimization, security).
*   **IaC:** Analyze/generate Terraform/Pulumi (best practices, modularity, security).
*   **Deployment:** Analyze/generate Kubernetes manifests. Suggest strategies.
