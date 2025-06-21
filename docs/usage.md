---
layout: default
title: Usage Guide
nav_order: 3
description: "Learn how to install, configure, and use the DevOps Agent."
---

# Usage Guide

This guide will walk you through getting started with and effectively using the DevOps Agent.

## Quickstart

To get started with the DevOps Agent, ensure you have Python 3.13 (or a compatible version) and `uvx` (the Universal Virtualenv Executer from the Google ADK) installed.

### 1. Set Google API Key
*Important:* Make sure you have set the `GOOGLE_API_KEY` environment variable:
```bash
export GOOGLE_API_KEY=your_api_key_here
```
This is required for the agent to create a GenAI client when running with the ADK.

### 2. Run the Agent Locally
Use the following command from the root of the repository:
```bash
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx --with extensions --with google-generativeai --with google-api-core --with chromadb --with protobuf --with openai --with tiktoken --no-cache --python 3.13 --from git+https://github.com/BlueCentre/adk-python.git@main adk run agents/devops
```
Alternatively, use the convenience script:
```bash
./scripts/execution/run.sh
```
This sets up a virtual environment and starts an interactive CLI session.
{% include callout.html type="note" content="The `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` part is a workaround for a compatibility issue between recent `protobuf` versions and older pre-compiled code in some dependencies." %}

### 3. Deploy to Google Cloud Run (Optional)
The agent can be deployed as a service to Google Cloud Run:
```bash
adk deploy cloud_run --project=[YOUR_GCP_PROJECT] --region=[YOUR_GCP_REGION] agents/devops/
```
Replace `[YOUR_GCP_PROJECT]` and `[YOUR_GCP_REGION]` with your details.

## Advanced Configuration

### Gemini Thinking Feature
Enhance reasoning for complex tasks using Gemini 2.5 series models.

**Supported Models:**
- `gemini-2.5-flash-preview-05-20`
- `gemini-2.5-pro-preview-06-05`

**Configuration:**
Create or update your `.env` file in the project root:
```ini
# Enable Gemini thinking (default: false)
GEMINI_THINKING_ENABLE=true

# Include thought summaries in responses (default: true)
GEMINI_THINKING_INCLUDE_THOUGHTS=true

# Set thinking budget (tokens for reasoning, default: 8192)
GEMINI_THINKING_BUDGET=8192

# Use a 2.5 series model
AGENT_MODEL=gemini-2.5-pro-preview-06-05
# or
# AGENT_MODEL=gemini-2.5-flash-preview-05-20

# Your Google API key (required)
GOOGLE_API_KEY=your_api_key_here
```
{% include callout.html type="tip" title="Performance" content="Higher thinking budgets (e.g., 16384+) allow more complex reasoning but increase costs. Complex reasoning may take longer but can produce higher quality results." %}

## Interacting with the Agent: Enhanced CLI

The DevOps Agent features an advanced command-line interface:

**Key Features:**
- **Multi-line Input:** Use `Alt+Enter` to submit complex, multi-line requests.
- **Mouse Support:** Click to position cursor, drag to select text, scroll menus.
- **Smart Auto-completion:** `Tab` completion for 50+ common DevOps commands.
- **Command History:** Navigate with `↑/↓` keys, with auto-suggestions.
- **Visual Enhancements:** Styled prompts, continuation indicators (`    >`), contextual help.

**Keyboard Shortcuts:**
- `Alt+Enter`: Submit multi-line input
- `Ctrl+D`: Exit
- `Ctrl+L`: Clear screen
- `Ctrl+C`: Cancel current input
- `Tab`: Show command completions
- `↑/↓`: Navigate command history

**Example Interactions:**

1.  **Multi-line Complex Request:**
    ```
    Create a Kubernetes deployment that:
    - Uses a multi-container pod setup
    - Includes health checks and resource limits
    - Has proper security contexts
    - Implements horizontal pod autoscaling
    [Alt+Enter to submit]
    ```

2.  **Quick Commands with Completion:**
    ```
    setup monitoring for[Tab] # Shows completion options
    ```
For more examples, refer to the prompts in the `example_prompts/` directory of the repository.
