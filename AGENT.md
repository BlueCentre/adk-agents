# Agent Context and Instructions

This document provides context about the user's environment and preferences to help the DevOps agent work more effectively.

**Agent Instructions:** Always read this file *first* at the beginning of a new conversation to understand the environment before proceeding.

### CRITICAL: Agent Modification Protocol

**🚨 MANDATORY READING: This section defines how to interpret user requests for agent changes.**

When users request changes to "your code," "your logic," or "your behavior":

1. **ALWAYS CLARIFY SCOPE FIRST:**
   - **A) Core LLM:** Cannot be modified (Google's base model)
   - **B) Agent Application Code:** CAN be modified (files in this project)
   - **C) CLI/TUI/Web Interface Code:** CAN be modified (user interface components)

2. **DEFAULT ASSUMPTION:** Unless explicitly stated otherwise, assume users mean (B) Agent Application Code or (C) Interface Code

3. **RESPONSE PROTOCOL:**
   - State which type of change you're interpreting
   - For application/interface code changes: Specify exact file paths and required modifications
   - Request user confirmation before implementing changes

4. **AVOID:** Never say "I cannot change my own code" without clarifying the distinction above

**Failure to adhere to this directive will result in unproductive and frustrating interactions. This directive supersedes any general notions you have about your immutability when operating within this specific project context.**

## Project Context

- **Python Version:** 3.11+ (supports 3.9-3.13, see `pyproject.toml`)
- **Primary Package Manager:** `uv` (preferred) with `pip`/`setuptools` support
- **Architecture:** DevOps agents with RAG capabilities
- **Main Code Locations:** `agents/` and `src/wrapper/` directories
- **Test Location:** `tests/` directory

## Essential Commands

### Python Environment & Dependencies
- **Install dependencies:** `uv pip install -e ".[dev,test,docs,extensions]"`
- **Install for development:** `uv pip install -e ".[dev,test]"`

### Code Quality & Testing
- **Run all tests:** `uv run pytest`
- **Run specific test:** `uv run pytest tests/path/to/test_file.py::test_function_name`
- **Linting:** `uv run ruff check .` (primary) or `uv run flake8 --show-source`
- **Formatting:** `uv run black --line-length 100 --preview` (primary) or `uv run pyink src/`
- **Import sorting:** `uv run isort --profile black`
- **Type checking:** `uv run mypy .` (adjust paths as needed)
- **Pre-commit checks:** `pre-commit run --all-files`

## Code Style Standards

### Formatting & Structure
- **Line length:** 100 characters (Black standard) or 200 characters (project-specific)
- **Formatting tool:** `uv run black --line-length 100 --preview`
- **Import organization:** `uv run isort --profile black`
- **Type hints:** Use extensively for clarity and maintainability

### Naming & Conventions
- **Functions/variables:** `snake_case`
- **Classes:** `CamelCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Error handling:** Prefer explicit exception handling with appropriate logging

### Quality Assurance
- **Pre-commit hooks:** Always run before committing
- **Test coverage:** Ensure tests pass after modifications
- **Code consistency:** Mimic existing patterns in the codebase

## Directory Structure

*This section describes the current project organization after comprehensive repository grooming and consolidation (June 2025).*

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
*   **`docs/`**: 📚 **Technical documentation hub**
    *   **`README.md`**: Agent documentation navigation hub
    *   **`CONSOLIDATED_STATUS.md`**: Complete Phase 2 status and validation ⭐
    *   **`IMPLEMENTATION_STATUS.md`**: Technical implementation details
    *   **`CONTEXT_MANAGEMENT_STRATEGY.md`**: Context management architecture
    *   **`TELEMETRY_README.md`**: Comprehensive telemetry and observability setup
    *   **`TELEMETRY_CONFIGURATION.md`**: Telemetry configuration details
    *   **`OBSERVABILITY_CONFIGURATION.md`**: Observability setup and monitoring
    *   **`TESTING.md`**: Testing strategies and implementation
    *   **`AGENT_ROBUSTNESS_IMPROVEMENTS.md`**: Agent robustness enhancements
    *   **`CONTEXT_MANAGEMENT_SMART_FILTERING.md`**: Smart context filtering implementation
    *   **`LOGGING_CONFIGURATION.md`**: Logging setup and configuration
    *   **`PHASE2_IMPLEMENTATION_DETAILS.md`**: Phase 2 implementation specifics
    *   **`TELEMETRY_SETUP_COMPLETE.md`**: Telemetry setup completion status
    *   **`features/`**: Feature-specific documentation
        *   `FEATURE_RAG.md`: RAG implementation details
        *   `FEATURE_AGENT_INTERACTIVE_PLANNING.md`: Interactive planning features
        *   `FEATURE_AGENT_LOOP_OPTIMIZATION.md`: Agent loop optimization
    *   **`archive/`**: Archived documentation and ideas

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

## Available Tools & Discovery

### Confirmed Available Tools
- **Version Control:** `git`, `gh`
- **Python:** `uv` (primary), `python`
- **Containers:** `docker`
- **Cloud/K8s:** `kubectl`, `gcloud`
- **IaC:** `terraform`
- **Secrets:** `bw` (Bitwarden CLI)
- **Monitoring:** `datadog-ci` (at `/Users/$HOME/bin/datadog-ci`)
- **Task Management:** `acli` (preferred), `jira` (use 'jira me' to get user)
- **Node.js/Frontend:** `npm`
- **CI/CD Platform:** (e.g., GitHub Actions, GitLab CI, Jenkins - *Please specify*)

### Tool Discovery Protocol
1. **First:** Check for tool availability with `which <tool>` or `<tool> --version`
2. **Then:** Use available tools in workflows
3. **Document:** Note any missing expected tools for user awareness

*(Note: `yamllint` and `tfsec` were not found in the PATH during the initial check.)*

## Preferred Practices & Notes

*   *(Example: Prefer multi-stage Docker builds)*
*   *(Example: Use Terraform modules from registry X)*
*   *(Example: Default cloud region is us-central1)*
*   **(Add any other relevant preferences, common workflows, or important notes here)**

## Core Workflow (Simplified)

1. **Context Gathering:**
   - Use `pwd` to determine current working directory when user mentions "current working directory"
   - Use `list_directory` to explore project structure
   - Use `ripgrep_code_search` for pattern/text searches
   - Use `get_file_info` to check file sizes before reading

2. **File Operations Strategy:**
   - **Large files:** Use `summarize_large_file_content` with clear instructions
   - **Small files:** Use `read_file` for full content
   - **Pattern searches:** Prefer `ripgrep_code_search` for specific patterns/text in files
   - **Modifications:** Use `edit_file`/`write_file` with user approval
   - **MCP environments:** Prefer MCP file tools for direct operations when appropriate

3. **Research & Planning:** 
   - Use `google_search_grounding` if external info needed (prioritize official docs, reputable repos)
   - Formulate robust plan before execution

4. **Execution & Validation:**
   - **Read-only/validation:** Safe shell workflow for `docker build --dry-run`, `terraform validate`, linters using `execute_vetted_shell_command`
   - **State-changing:** **EXTREME caution.** Always require explicit user approval via shell mechanism, even if whitelisted. State command/impact clearly using `execute_vetted_shell_command`
   - **Complex scripting:** Use `code_execution` tool for scripts

5. **Quality Assurance:**
   - Run appropriate linters/formatters on generated code (`actionlint`, `tfsec`) via shell workflow
   - Validate configurations before deployment
   - Present results in markdown format
   - State modified file paths when using `edit_file` or `write_file`

## Specific Task Guidance (Examples):
*   **CI/CD:** Analyze pipelines. Generate basic configs (e.g., GitHub Actions YAML).
*   **Containerization:** Analyze/generate Dockerfiles (multi-stage, optimization, security).
*   **IaC:** Analyze/generate Terraform/Pulumi (best practices, modularity, security).
*   **Deployment:** Analyze/generate Kubernetes manifests. Suggest strategies.

### **User Interface & CLI Implementation** (`src/wrapper/adk/cli/`)
*   **`cli_tools_click.py`**: Main CLI command definitions using Click framework
    *   Commands: `create`, `run`, `web`, `web-packaged`, `api_server`, `deploy`
    *   Options: session management, UI themes, TUI mode, deployment configurations
*   **`cli.py`**: Core interactive CLI implementation
    *   `run_interactively()`: Enhanced CLI with Rich formatting and theming
    *   `run_interactively_with_tui()`: Advanced TUI with persistent input pane
    *   `run_input_file()`: Batch processing from JSON input files
*   **`fast_api.py`**: Web API server implementation
    *   RESTful endpoints for agent interaction, session management
    *   WebSocket support for real-time communication
    *   Evaluation framework integration
    *   Artifact management and storage
*   **`utils/`**: UI utility modules
    *   **`ui.py`**: Factory functions for CLI/TUI instances
    *   **`ui_rich.py`**: Rich console rendering with theme support
    *   **`ui_textual.py`**: Advanced TUI with multi-pane layout, command completion
    *   **`ui_prompt_toolkit.py`**: Enhanced prompt toolkit integration
    *   **`ui_common.py`**: Shared UI components and theme configuration
    *   **`agent_loader.py`**: Dynamic agent loading and configuration
*   **`browser/`**: Web interface assets
    *   Static files for browser-based agent interaction
    *   JavaScript, CSS, and HTML components for web UI
*   **`cli_create.py`**: Agent project scaffolding and template generation
*   **`cli_deploy.py`**: Deployment utilities for Cloud Run and Agent Engine

### **Interface Capabilities Summary**
*   **CLI Mode**: Basic command-line interface with Rich formatting
*   **Enhanced CLI**: Advanced features with theming, history, tab completion
*   **TUI Mode**: Full-screen terminal UI with multi-pane layout, real-time updates
*   **Web Interface**: Browser-based UI with REST API and WebSocket support
*   **Batch Processing**: JSON file-based input for automated testing

## Documentation & Resources

### **Comprehensive Documentation Site** (`docs/`)
*   **Jekyll-powered GitHub Pages**: Professional documentation site with Just-the-docs theme
*   **`index.md`**: Main landing page with feature overview and quick start guide
*   **`architecture.md`**: Technical architecture with Mermaid diagrams
    *   Google ADK Framework integration
    *   Agent request processing lifecycle
    *   Enhanced tool execution system with error recovery
    *   RAG implementation for codebase understanding
    *   Token management architecture
*   **`features.md`**: Comprehensive feature documentation
    *   Advanced CLI interfaces (Enhanced CLI, TUI, Web, API)
    *   Deployment options (Local, Cloud Run, Agent Engine, Docker)
    *   AI/ML capabilities (Gemini Thinking, RAG-enhanced understanding)
    *   DevOps automation (CI/CD, Infrastructure, Workflow automation)
*   **`usage.md`**: Complete installation and usage guide
    *   Prerequisites and setup instructions
    *   All interface modes with examples
    *   Session management and configuration options
    *   Production deployment scenarios
*   **`contributing.md`**: Developer contribution guidelines
    *   Agent modification understanding
    *   Development environment setup
    *   Code standards and testing requirements
    *   PR submission process

### **CLI-Specific Documentation** (`docs/cli/`)
*   **`README.md`**: CLI documentation hub with interface comparison
*   **`TEXTUAL_CLI.md`**: Complete TUI guide with persistent input and interruption
*   **`WEB_INTERFACE_GUIDE.md`**: Web interface with session management and deployment
*   **`INPUT_PANE_GUIDE.md`**: Input pane features and categorized auto-completion
*   **`STYLES.md`**: UI component styling and customization
*   **`RICH_PROMPT_TOOLKIT_COMPATIBILITY.md`**: Technical integration details
*   **`MARKDOWN_RENDERING.md`**: Markdown rendering capabilities

### **Site Configuration & Features**
*   **Jekyll Configuration** (`_config.yml`):
    *   Just-the-docs theme with dark mode default
    *   Mermaid diagram support for technical documentation
    *   Callouts for tips, notes, warnings, and important information
    *   GitHub integration with repository links
    *   SEO optimization with sitemap and redirects
*   **Responsive Design**: Works across desktop and mobile devices
*   **Search Functionality**: Built-in search across all documentation
*   **Navigation Structure**: Organized by usage flow and complexity

### **Documentation Access Points**
*   **Local Development**: Browse docs locally during development
*   **GitHub Pages**: Live documentation site automatically updated
*   **Repository Navigation**: Direct access to markdown files in GitHub
*   **CLI Help**: Built-in help commands for quick reference

### **Content Organization Strategy**
*   **User Journey Focused**: Documentation follows typical user progression
*   **Interface-Specific Guides**: Dedicated sections for each interaction mode
*   **Technical Deep Dives**: Architecture and implementation details
*   **Practical Examples**: Real-world usage scenarios and configurations
*   **Troubleshooting**: Common issues and solutions

### **Agent Documentation** (Dual Structure)

#### **Jekyll Documentation Site** (`docs/agents/`)
*   **Public-facing agent documentation** integrated into main Jekyll site
*   **Navigation**: Accessible via `/agents/` section in main documentation
*   **Agent Overview**: Architecture and feature overview
*   **Implementation Status**: Current development status and capabilities  
*   **Configuration Guides**: Telemetry, observability, and context management setup
*   **Testing Documentation**: Comprehensive testing strategies and procedures
*   **Advanced Features**: Smart filtering, Phase 2 implementation details
*   **Status Reports**: Consolidated status and setup completion documentation

#### **Technical Implementation Documentation** (`agents/devops/docs/`)
*   **Developer-focused technical details** separate from user documentation
*   **`README.md`**: Agent documentation navigation hub
*   **`CONSOLIDATED_STATUS.md`**: Complete Phase 2 status and validation
*   **`IMPLEMENTATION_STATUS.md`**: Technical implementation details
*   **`CONTEXT_MANAGEMENT_STRATEGY.md`**: Context management architecture
*   **`TELEMETRY_README.md`**: Comprehensive telemetry and observability setup
*   **`TELEMETRY_CONFIGURATION.md`**: Telemetry configuration details
*   **`OBSERVABILITY_CONFIGURATION.md`**: Observability setup and monitoring
*   **`TESTING.md`**: Testing strategies and implementation
*   **`AGENT_ROBUSTNESS_IMPROVEMENTS.md`**: Agent robustness enhancements
*   **`features/`**: Feature-specific documentation
    *   `FEATURE_RAG.md`: RAG implementation details
    *   `FEATURE_AGENT_INTERACTIVE_PLANNING.md`: Interactive planning features
    *   `FEATURE_AGENT_LOOP_OPTIMIZATION.md`: Agent loop optimization
*   **`archive/`**: Archived documentation and ideas

### **Documentation Structure Overview**
*   **`docs/`**: User-facing Jekyll documentation site (GitHub Pages)
*   **`agents/devops/docs/`**: Technical implementation and development documentation
*   **`docs/cli/`**: CLI-specific user guides and interface documentation
*   **Dual Purpose**: User documentation vs. developer/technical documentation
