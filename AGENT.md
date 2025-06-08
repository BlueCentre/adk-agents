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

*This section describes the current project organization after comprehensive repository grooming and consolidation (December 2024).*

### **Core Agent Implementation** (`agents/devops/`)
*   **`devops_agent.py`**: Main DevOps agent implementation (ADK LlmAgent)
*   **`agent.py`**: Agent entry point and configuration
*   **`prompts.py`**: Core agent instructions and persona definition
*   **`config.py`**: Configuration management and environment setup
*   **`components/`**: Advanced agent components
    *   **`planning_manager.py`**: Interactive planning workflow management
    *   **`context_management/`**: Advanced context management system
        *   `context_manager.py`: Main context orchestration
        *   `smart_prioritization.py`: Multi-factor relevance scoring
        *   `cross_turn_correlation.py`: Turn relationship detection
        *   `intelligent_summarization.py`: Content-aware compression
        *   `dynamic_context_expansion.py`: Automatic content discovery
*   **`tools/`**: Comprehensive tool suite
    *   `rag_tools.py`: RAG indexing and retrieval tools
    *   `rag_components/`: ChromaDB and embedding components
    *   `filesystem.py`: File system operations
    *   `shell_command.py`: Vetted command execution
    *   `code_analysis.py`: Static code analysis capabilities
    *   `project_context.py`: Project-level context gathering
    *   `[additional tools]`: Memory, analysis, and utility tools
*   **`shared_libraries/`**: Shared utilities and common functions
*   **`docs/`**: 📚 **Consolidated documentation hub**
    *   **`README.md`**: Navigation hub and quick reference
    *   **`CONSOLIDATED_STATUS.md`**: Complete Phase 2 status and validation ⭐
    *   **`IMPLEMENTATION_STATUS.md`**: Technical implementation details
    *   **`CONTEXT_MANAGEMENT_STRATEGY.md`**: Context management architecture
    *   **`features/`**: Feature-specific documentation
    *   **`archive/`**: Archived documentation

### **Organized Utility Scripts** (`scripts/`)
*   **`README.md`**: Scripts documentation and usage guide
*   **`execution/`**: Agent execution and deployment scripts
    *   `run.sh`, `run_adk.sh`: Local agent execution
    *   `eval.sh`, `eval_adk.sh`: Evaluation and testing
    *   `prompt.sh`, `prompt_adk.sh`: Interactive prompt testing
    *   `push.sh`, `web_adk.sh`: Deployment and web interface
    *   `mcp.sh`, `fix_rate_limits.sh`, `groom.sh`: Utilities
*   **`monitoring/`**: Telemetry and performance monitoring
    *   `telemetry_check.py`, `telemetry_dashboard.py`: Health checks and dashboard
    *   `metrics_overview.py`, `metrics_status.py`: Metrics analysis
    *   `tracing_overview.py`: Distributed tracing analysis
*   **`validation/`**: Testing and validation scripts
    *   `validate_smart_prioritization_simple.py`: Smart prioritization validation

### **Organized Test Prompts** (`example_prompts/`)
*   **`README.md`**: Test prompt documentation and guidelines
*   **`current/`**: Active test prompts for ongoing features
    *   `test_gemini_thinking_feature.md`: Gemini thinking validation
    *   `test_dynamic_discovery.md`: Dynamic tool discovery testing
    *   `test_context_diagnostics.md`: Context management diagnostics
    *   `test_planning_heuristics.md`: Interactive planning validation
    *   `test_prompt_engineering.md`: Prompt optimization testing
*   **`archive/`**: Completed test prompts (Phase 2, etc.)

### **Additional Directories**
*   **`tests/`**: Test suite (unit, integration, e2e)
*   **`eval/`**: Evaluation datasets and results
*   **`src/`**: Source package structure
*   **Root files**: `AGENT.md`, `README.md`, `pyproject.toml`, etc.

**Key Organizational Benefits:**
- **Consolidated documentation** with clear navigation paths
- **Organized scripts** by purpose (execution, monitoring, validation)
- **Categorized test prompts** (current vs. archived)
- **Clean structure** with no build artifacts or duplicates

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
