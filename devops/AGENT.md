# Agent Context and Instructions

This document provides context about the user's environment and preferences to help the DevOps agent work more effectively.

**Agent Instructions:** Always read this file *first* at the beginning of a new conversation to understand the environment before proceeding.

## Directory Structure

*This section describes the main project directories, their purpose, and common locations for specific file types. It's based on a scan of `/Users/james`.*

*   `/Users/james/Desktop/`: Standard desktop folder.
*   `/Users/james/Documents/`: Standard documents folder.
*   `/Users/james/Downloads/`: Standard downloads folder.
*   `/Users/james/bin/`: Contains user-specific scripts and binaries (e.g., `datadog-ci`).
*   `/Users/james/Agents/`: Contain configurations, code and prompts related to the current AI agent runtime.
    *   *(Consider listing key sub-project folders here if any)*
*   `/Users/james/Workspace/`: Appears to be a primary development/projects directory.
    *   *(Consider listing key sub-project folders here if any, e.g., `Workspace/project-alpha/`, `Workspace/my-utils/`)*
*   `/Users/james/.config/`: Common location for user-specific application configurations.
*   `/Users/james/.docker/`: Docker client configuration files.
*   `/Users/james/.kube/`: Kubernetes configuration files (e.g., `config`).

**(Please review this refined list. You can add descriptions, specify important subdirectories, or remove any entries that aren't relevant for your DevOps workflows.)**

## Common Tools Available

*   **Version Control:** `git`
*   **Containerization:** `docker`
*   **Orchestration:** `kubectl`
*   **IaC:** `terraform`
*   **Scripting/Languages:** `python`
*   **Python Env/Pkg Mgmt:** `uv`
*   **Node.js/Frontend:** `npm`
*   **CI/CD Platform:** (e.g., GitHub Actions, GitLab CI, Jenkins - *Please specify*)
*   **Cloud Provider CLI:** (e.g., `gcloud`, `aws`, `az` - *Please specify if used*)
*   **Task Management:** `jira` (Confirmed available)
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
    *   **Probe for tools:** `check_command_exists` for common tools (e.g., `bw`, `jira`, `gh`, `gcloud`, `git`, `kubectl`, `docker`, `terraform`, `uv`, `npm`, `yamllint`, `tfsec`).
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
