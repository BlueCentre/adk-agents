# Tech Stack

This project leverages a modern and robust tech stack built primarily around **Python** and its extensive ecosystem. Key areas of focus include AI/LLM orchestration, observability, and development tooling.

## Core Technologies:

*   **Programming Language:** Python (supported versions: 3.9 - 3.13)
*   **Agent Development Framework:** `google-adk` (Google Agent Development Kit) - The foundational framework for building and managing agents.

## AI & Language Models (LLMs):

*   **LLM Orchestration:** `litellm` - Abstracts and simplifies interactions with various Language Model providers.
*   **LLM Integrations:**
    *   `openai` - Direct integration with OpenAI models.
    *   `anthropic` - Support for Anthropic models.
*   **Agent Workflow Management:** `langgraph` - Used for building complex, graph-based agent workflows, enabling multi-step AI reasoning.
*   **Retrieval Augmented Generation (RAG):**
    *   `chromadb` - A vector database used for storing and retrieving external knowledge to augment LLM responses.
    *   `llama-index-readers-file` - Provides retrieval capabilities using LlamaIndex for RAG implementations.

## Observability & Monitoring:

*   **OpenTelemetry:** `openlit`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` - For distributed tracing and metrics, enabling data export to platforms like Grafana Cloud.
*   **System Monitoring:** `psutil` - For gathering system-level information and monitoring.

## User Interface & Interaction:

*   **Command-Line Interface (CLI) & Text User Interface (TUI):**
    *   `rich` - Enhances console output with rich text and formatting.
    *   `prompt_toolkit` - Provides advanced features for command-line input.
    *   `textual` - Used for building interactive Text User Interfaces.

## Development & Automation:

*   **Code Execution:** `docker` - Utilized for `ContainerCodeExecutor`, suggesting isolated and consistent code execution environments.
*   **Process Automation:** `pexpect` - For interacting with and automating child processes, such as shell commands.
*   **Web Scraping/Parsing:**
    *   `beautifulsoup4`
    *   `lxml`
    *   These libraries are used in conjunction for web page parsing, likely for a `load_web_page` tool.
*   **Tokenization:** `tiktoken` - Essential for managing and calculating token counts for LLM inputs and outputs.

## Testing:

*   **Unit & Integration Testing:** `pytest`, `pytest-asyncio`, `pytest-mock`, `pytest-xdist` - Comprehensive suite for testing Python code, executed via `uv run pytest`.

## Development Tools:

*   **Packaging:** `setuptools` - The primary build backend for creating distributable packages.
*   **Dependency Management & Command Runner:** `uv` - Used for fast and reliable dependency resolution, package installation, and locking (`uv.lock`). Crucially, it acts as the primary command runner for most development tools (e.g., `uv run pytest`, `uv run pylint`, `uv run pyink`, `uv run mypy`, `uv run isort`).
*   **Code Formatting:**
    *   `isort` (for sorting imports, run via `uv run isort` and integrated as a pre-commit hook).
    *   `pyink` (Google style-guide formatter, run via `uv run pyink`).
*   **Code Quality:**
    *   `pylint` (linting, run via `uv run pylint`).
    *   `flake8` (additional linting, run via `uv run flake8`).
    *   `mypy` (static type checking, run via `uv run mypy`).
*   **Other Development Dependencies:** `flit` (listed as a development dependency, but not the primary packaging tool or command runner for this project).

## Continuous Integration/Continuous Delivery (CI/CD):

*   **GitHub Actions:** Used for automating build, test, and deployment workflows.
