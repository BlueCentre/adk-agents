---
layout: default
title: Usage Guide
nav_order: 4
description: "Learn how to install, configure, and use the DevOps Agent with all available interfaces."
mermaid: true
---

# Usage Guide

This comprehensive guide covers all aspects of using the DevOps Agent, from basic setup to advanced deployment scenarios.

## Installation & Setup

### Prerequisites
- Python 3.11+ (3.13 recommended)
- `uv` package manager (recommended) or `pip`
- Google API Key or Google Cloud Project access

### 1. Set Google API Key
**Important:** Configure your Google API access:

```bash
export GOOGLE_API_KEY=your_api_key_here
```

Or for Google Cloud Vertex AI:
```bash
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=your_project_id
export GOOGLE_CLOUD_LOCATION=your_region
```

### 2. Install ADK
```bash
# Using uv (recommended)
uv add google-adk

# Or using pip
pip install google-adk
```

## Usage Modes

The DevOps Agent supports multiple interaction modes to suit different workflows and preferences.

```mermaid
journey
    title DevOps Agent User Journey
    section Setup
      Install ADK: 5: User
      Set API Key: 4: User
      Choose Interface: 5: User
    section Development
      Enhanced CLI: 5: User
      Multi-line Input: 4: User
      Command History: 4: User
      Auto-completion: 5: User
    section Advanced Usage
      TUI Mode: 5: User
      Agent Interruption: 4: User
      Session Management: 4: User
      Web Interface: 3: User
    section Production
      API Server: 3: User
      Cloud Deployment: 4: User
      Session Persistence: 4: User
      Monitoring: 3: User
```

### 🖥️ Enhanced CLI (Default)

The enhanced CLI provides a rich interactive experience with advanced features:

```bash
# Basic usage
adk run agents/devops

# With session management
adk run agents/devops --save_session --session_id my_session

# With theme selection
adk run agents/devops --ui_theme dark
```

**Features:**
- **Multi-line Input**: Use `Alt+Enter` for complex, multi-line requests
- `Ctrl+D`: Exit
- `Ctrl+L`: Clear screen
- `Ctrl+C`: Cancel current input
- `Tab`: Show command completions
- `↑/↓`: Navigate command history

### 🎯 Textual TUI (Terminal User Interface)

The TUI provides a persistent, split-pane interface with agent interruption capabilities:

```bash
# Enable TUI mode
adk run agents/devops --tui

# With theme selection
adk run agents/devops --tui --ui_theme dark
```

**Features:**
- **Persistent Input Pane**: Type while agent is responding
- **Agent Interruption**: `Ctrl+C` to stop long-running operations
- **Split-Pane Layout**: Output above, input below
- **Real-time Status**: Visual indicators for agent state
- **Agent Thoughts**: Optional side pane showing reasoning process

**TUI-Specific Shortcuts:**
- `Ctrl+C`: Interrupt running agent
- `Ctrl+T`: Toggle theme
- `Ctrl+Y`: Toggle agent thought display
- `Enter`: Submit input (when agent ready)
- `Alt+Enter`: Insert newline

### 🌐 Web Interface

Launch a web-based interface for browser interaction:

```bash
# Basic web interface
adk web agents/

# With custom configuration
adk web agents/ --host 0.0.0.0 --port 8080 --allow_origins "https://mydomain.com"

# With session persistence
adk web agents/ --session_db_url "sqlite:///sessions.db"

# With cloud tracing
adk web agents/ --trace_to_cloud
```

**Features:**
- Modern web-based UI
- Session management
- Artifact storage support
- CORS configuration
- Auto-reload for development

### 🔌 API Server

Run as a RESTful API server for programmatic access:

```bash
# Basic API server
adk api_server agents/

# Production configuration
adk api_server agents/ \
  --host 0.0.0.0 \
  --port 8000 \
  --session_db_url "sqlite:///sessions.db" \
  --artifact_storage_uri "gs://my-bucket" \
  --trace_to_cloud
```

**API Endpoints:**
- `GET /list-apps`: List available agents
- `POST /apps/{app_name}/users/{user_id}/sessions`: Create session
- `POST /run`: Execute agent with streaming support
- `GET /apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts`: Manage artifacts

## Session Management

```mermaid
flowchart TD
    A[Start Agent] --> B{Save Session?}
    B -->|Yes| C[Create Session ID]
    B -->|No| D[Ephemeral Session]
    C --> E[Interactive Session]
    D --> E
    E --> F[Commands & Responses]
    F --> G[Session Data Stored]
    G --> H{Continue?}
    H -->|Yes| F
    H -->|No| I[End Session]
    I --> J[Session Saved to File]
    
    K[Resume Session] --> L[Load Session File]
    L --> M[Restore Context]
    M --> N[Continue from Last State]
    
    O[Replay Session] --> P[Load Session File]
    P --> Q[Execute Commands Sequentially]
    Q --> R[Show Results]
    
    style C fill:#e1f5fe
    style G fill:#e8f5e8
    style J fill:#fff3e0
    style M fill:#f3e5f5
```

### Save and Resume Sessions

```bash
# Save session on exit
adk run agents/devops --save_session --session_id my_work_session

# Resume previous session
adk run agents/devops --resume saved_session.json

# Replay session commands
adk run agents/devops --replay session_replay.json
```

### Session Files
Sessions are saved as JSON files containing:
- Conversation history
- Agent state
- Context information
- Timestamps

## Advanced Configuration

### Gemini Thinking Feature

Enable enhanced reasoning with Gemini 2.5 models:

```bash
# Set environment variables
export GEMINI_THINKING_ENABLE=true
export GEMINI_THINKING_INCLUDE_THOUGHTS=true
export GEMINI_THINKING_BUDGET=8192
export AGENT_MODEL=gemini-2.5-pro-preview-06-05
```

**Supported Models:**
- `gemini-2.5-flash-preview-05-20`
- `gemini-2.5-pro-preview-06-05`

{: .tip }
> **Performance:** Higher thinking budgets (e.g., 16384+) allow more complex reasoning but increase costs. Complex reasoning may take longer but can produce higher quality results.

### Database Configuration

Configure persistent session storage:

```bash
# SQLite (local)
--session_db_url "sqlite:///path/to/sessions.db"

# Agent Engine (managed)
--session_db_url "agentengine://your_agent_engine_resource_id"

# PostgreSQL
--session_db_url "postgresql://user:pass@host:port/db"
```

### Artifact Storage

Configure artifact storage for file handling:

```bash
# Google Cloud Storage
--artifact_storage_uri "gs://your-bucket-name"

# Local storage (development)
# Uses in-memory storage by default
```

## Deployment

### 🏗️ Create New Agent

Generate a new agent project:

```bash
# Interactive creation
adk create my_agent

# With specific model
adk create my_agent --model gemini-2.0-flash-001

# With Google Cloud configuration
adk create my_agent \
  --project my-gcp-project \
  --region us-central1 \
  --api_key $GOOGLE_API_KEY
```

### ☁️ Deploy to Google Cloud Run

Deploy your agent to Google Cloud Run:

```bash
# Basic deployment
adk deploy cloud_run agents/devops \
  --project my-gcp-project \
  --region us-central1

# With web UI
adk deploy cloud_run agents/devops \
  --project my-gcp-project \
  --region us-central1 \
  --with_ui \
  --service_name my-devops-agent

# With session persistence
adk deploy cloud_run agents/devops \
  --project my-gcp-project \
  --region us-central1 \
  --session_db_url "agentengine://my-resource-id" \
  --artifact_storage_uri "gs://my-artifacts-bucket"
```

### 🤖 Deploy to Agent Engine

Deploy to Google Cloud's managed Agent Engine:

```bash
adk deploy agent_engine agents/devops \
  --project my-gcp-project \
  --region us-central1 \
  --staging_bucket my-staging-bucket
```

## Common Usage Patterns

### Multi-line Requests

Use the enhanced CLI for complex requests:

```
Create a Kubernetes deployment that:
- Uses a multi-container pod setup
- Includes health checks and resource limits
- Has proper security contexts
- Implements horizontal pod autoscaling
[Alt+Enter to submit]
```

### Interactive Commands

```bash
# Start interactive session
adk run agents/devops

# Common commands with tab completion
setup monitoring for[Tab]  # Shows completion options
create dockerfile for[Tab]  # Shows project-specific completions
analyze this codebase[Enter]  # Immediate execution
```

### Session Workflow

```bash
# Start named session
adk run agents/devops --save_session --session_id infrastructure_review

# Work on tasks...
# Session automatically saved on exit

# Resume later
adk run agents/devops --resume infrastructure_review.json
```

## Troubleshooting

### Common Issues

**CLI Not Responding:**
- Try `Ctrl+C` to interrupt current operation
- Use `--tui` flag for better control
- Check terminal compatibility

**Session Errors:**
- Verify database URL format
- Check permissions for SQLite files
- Ensure network connectivity for remote databases

**Deployment Issues:**
- Verify Google Cloud authentication: `gcloud auth list`
- Check project permissions
- Ensure required APIs are enabled

### Debug Mode

Enable verbose logging:

```bash
# Enhanced logging
adk run agents/devops --log_level DEBUG

# With cloud tracing
adk run agents/devops --trace_to_cloud
```

{: .note }
> For more detailed examples and advanced usage patterns, refer to the `example_prompts/` directory in the repository.

## Next Steps

- Explore the [CLI Documentation](./cli/) for detailed interface guides
- Check out [Features](./features.md) for comprehensive capability overview
- Review [Contributing](./contributing.md) to help improve the agent
