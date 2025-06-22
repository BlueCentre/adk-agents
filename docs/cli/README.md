---
layout: default
title: CLI Documentation
nav_order: 4
has_children: true
description: "Comprehensive documentation for all DevOps Agent CLI interfaces and capabilities."
---

# CLI Documentation

Welcome to the comprehensive CLI documentation for the DevOps Agent. This section covers all available command-line interfaces, from basic usage to advanced deployment scenarios.

## 🚀 Available Interfaces

The DevOps Agent provides multiple CLI interfaces to suit different workflows and preferences:

### Enhanced CLI (Default)
Rich interactive command-line interface with professional-grade features:
- Multi-line input support with `Alt+Enter`
- Smart auto-completion for 50+ DevOps commands
- Command history with intelligent suggestions
- Mouse interaction and visual enhancements
- Dynamic theme switching

### Textual TUI (Terminal User Interface)
Full-featured terminal interface with persistent interaction capabilities:
- Persistent input pane for continuous typing
- Agent interruption with `Ctrl+C`
- Split-pane layout with dedicated areas
- Real-time status and token tracking
- Agent thoughts display

### Web Interface
Modern browser-based interface for web-native interactions:
- Responsive design accessible at `http://localhost:8000`
- Automatic session recovery for interrupted conversations
- Persistent session storage with database support
- Artifact upload, download, and management
- CORS support for cross-origin integration
- Built-in error handling and graceful degradation

### API Server
RESTful API for programmatic access and integration:
- OpenAPI specification
- Streaming support via Server-Sent Events
- Session and artifact management
- WebSocket support for real-time communication

## 📚 Documentation Sections

### [Textual CLI Guide](./TEXTUAL_CLI.md)
Complete guide to the Textual CLI with persistent input panes and agent interruption capabilities.

### [Web Interface Guide](./WEB_INTERFACE_GUIDE.md)
Comprehensive guide to the web interface with session management, troubleshooting, and deployment options.

### [Input Pane Guide](./INPUT_PANE_GUIDE.md)
Detailed guide to using the input pane with categorized auto-completion and advanced features.

### [Styling Guide](./STYLES.md)
Technical documentation on UI component styling and customization.

### [Rich & Prompt Toolkit Compatibility](./RICH_PROMPT_TOOLKIT_COMPATIBILITY.md)
Technical details on Rich library and prompt_toolkit integration.

### [Markdown Rendering](./MARKDOWN_RENDERING.md)
Guide to markdown rendering capabilities in the CLI interfaces.

## 🎯 Quick Start

### Basic Usage
```bash
# Enhanced CLI (default)
adk run agents/devops

# Textual TUI with persistent input
adk run agents/devops --tui

# Web interface
adk web agents/

# API server
adk api_server agents/
```

### Common Options
```bash
# Theme selection
adk run agents/devops --ui_theme dark
adk run agents/devops --ui_theme light

# Session management
adk run agents/devops --save_session --session_id my_session
adk run agents/devops --resume my_session.json
adk run agents/devops --replay session_replay.json

# Debug mode
adk run agents/devops --log_level DEBUG --trace_to_cloud
```

## 🛠️ Command Reference

### Core Commands

#### `adk run`
Run an agent interactively with various interface options.

```bash
adk run AGENT_MODULE [OPTIONS]
```

**Options:**
- `--tui`: Enable Textual TUI interface
- `--ui_theme {dark,light}`: Set UI theme
- `--save_session`: Save session on exit
- `--session_id TEXT`: Specify session ID
- `--resume PATH`: Resume from saved session
- `--replay PATH`: Replay session commands

#### `adk create`
Create a new agent project with intelligent scaffolding.

```bash
adk create APP_NAME [OPTIONS]
```

**Options:**
- `--model TEXT`: Specify the model to use
- `--api_key TEXT`: Google API key
- `--project TEXT`: Google Cloud project
- `--region TEXT`: Google Cloud region

#### `adk web`
Launch web interface for browser-based interaction using local agents directory.

```bash
adk web AGENTS_DIR [OPTIONS]
```

**Examples:**
```bash
# Basic web interface (in-memory sessions)
adk web agents/

# With persistent sessions (recommended)
adk web agents/ --session_db_url "sqlite:///sessions.db"

# Production configuration
adk web agents/ \
  --host 0.0.0.0 \
  --port 8080 \
  --session_db_url "postgresql://user:pass@host:port/db" \
  --artifact_storage_uri "gs://my-bucket"
```

#### `adk web-packaged`
Launch web interface using packaged agents (no local setup required).

```bash
adk web-packaged [OPTIONS]
```

**Examples:**
```bash
# Zero-setup web interface (recommended for quick start)
adk web-packaged --session_db_url "sqlite:///sessions.db"

# With custom configuration
adk web-packaged \
  --host 0.0.0.0 \
  --port 8080 \
  --session_db_url "sqlite:///sessions.db" \
  --no-reload

# Production setup with packaged agents
adk web-packaged \
  --session_db_url "postgresql://user:pass@host:port/db" \
  --artifact_storage_uri "gs://my-bucket" \
  --allow_origins "https://mydomain.com"
```

**Shared Options (both commands):**
- `--host TEXT`: Binding host (default: 127.0.0.1)
- `--port INTEGER`: Server port (default: 8000)
- `--session_db_url TEXT`: Database URL for persistent sessions
  - `sqlite:///sessions.db` - Local SQLite (recommended for development)
  - `postgresql://...` - PostgreSQL for production
  - `agentengine://resource_id` - Google Cloud managed sessions
- `--artifact_storage_uri TEXT`: Artifact storage URI (`gs://bucket-name`)
- `--allow_origins TEXT`: CORS origins (can be specified multiple times)
- `--trace_to_cloud`: Enable cloud tracing for debugging
- `--reload/--no-reload`: Auto-reload for development (default: enabled)

#### `adk api_server`
Run as RESTful API server for programmatic access.

```bash
adk api_server AGENTS_DIR [OPTIONS]
```

**Options:** Same as `adk web` command.

### Deployment Commands

#### `adk deploy cloud_run`
Deploy to Google Cloud Run with auto-generated containers.

```bash
adk deploy cloud_run AGENT [OPTIONS]
```

**Options:**
- `--project TEXT`: Google Cloud project (required)
- `--region TEXT`: Google Cloud region (required)
- `--service_name TEXT`: Cloud Run service name
- `--with_ui`: Deploy with web UI
- `--session_db_url TEXT`: Session database URL
- `--artifact_storage_uri TEXT`: Artifact storage URI
- `--trace_to_cloud`: Enable cloud tracing
- `--adk_version TEXT`: ADK version to use

#### `adk deploy agent_engine`
Deploy to Google Cloud's managed Agent Engine.

```bash
adk deploy agent_engine AGENT [OPTIONS]
```

**Options:**
- `--project TEXT`: Google Cloud project (required)
- `--region TEXT`: Google Cloud region (required)
- `--staging_bucket TEXT`: GCS staging bucket (required)
- `--trace_to_cloud`: Enable cloud tracing
- `--adk_app TEXT`: Python file for ADK application
- `--env_file TEXT`: Environment file path
- `--requirements_file TEXT`: Requirements file path

## ⌨️ Keyboard Shortcuts

### Universal Shortcuts
| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+D` | Exit | All interfaces |
| `Ctrl+L` | Clear screen | All interfaces |
| `Ctrl+C` | Interrupt/Cancel | All interfaces |

### Enhanced CLI
| Shortcut | Action |
|----------|--------|
| `Alt+Enter` | Submit multi-line input |
| `Tab` | Show completions |
| `↑/↓` | Navigate history |

### Textual TUI
| Shortcut | Action |
|----------|--------|
| `Enter` | Submit input (when ready) |
| `Alt+Enter` | Insert newline |
| `Ctrl+T` | Toggle theme |
| `Ctrl+Y` | Toggle agent thoughts |
| `Tab` | Show categorized completions |

## 🎨 Themes and Customization

### Available Themes
- **Dark Theme**: Professional dark interface with syntax highlighting
- **Light Theme**: Clean light interface for bright environments
- **Auto-detection**: Respects system preferences

### Theme Control
```bash
# Set theme at startup
adk run agents/devops --ui_theme dark

# Toggle theme in TUI
Ctrl+T

# Environment variable
export ADK_CLI_THEME=dark
```

## 🔧 Configuration

### Environment Variables
```bash
# Google API Configuration
export GOOGLE_API_KEY=your_api_key
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=your_project
export GOOGLE_CLOUD_LOCATION=your_region

# Gemini Thinking Feature
export GEMINI_THINKING_ENABLE=true
export GEMINI_THINKING_INCLUDE_THOUGHTS=true
export GEMINI_THINKING_BUDGET=8192
export AGENT_MODEL=gemini-2.5-pro-preview-06-05

# CLI Configuration
export ADK_CLI_THEME=dark
```

### Session Storage
```bash
# SQLite (local)
--session_db_url "sqlite:///sessions.db"

# Agent Engine (managed)
--session_db_url "agentengine://resource_id"

# PostgreSQL
--session_db_url "postgresql://user:pass@host:port/db"
```

### Artifact Storage
```bash
# Google Cloud Storage
--artifact_storage_uri "gs://bucket-name"

# Local development (in-memory by default)
```

## 🐛 Troubleshooting

### Common Issues

**CLI Not Starting:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Verify ADK installation
adk --version

# Try with explicit theme
adk run agents/devops --ui_theme dark
```

**TUI Issues:**
```bash
# Check terminal compatibility
echo $TERM

# Fall back to regular CLI
adk run agents/devops  # Without --tui flag

# Enable debug logging
adk run agents/devops --tui --log_level DEBUG
```

**Web Interface Issues:**
```bash
# Session not found errors - use persistent storage
adk web agents/ --session_db_url "sqlite:///sessions.db"

# Port already in use
adk web agents/ --port 8080

# CORS errors for web integration
adk web agents/ --allow_origins "https://yourdomain.com"

# Auto-reload warnings (normal behavior)
adk web agents/ --no-reload  # Suppress message

# Static files not loading (restart server)
# Files are served automatically from built-in directory
```

**Session Problems:**
```bash
# Check database permissions
ls -la sessions.db

# Verify database URL format
--session_db_url "sqlite:///$(pwd)/sessions.db"

# Test with in-memory sessions (no --session_db_url)
```

**Deployment Issues:**
```bash
# Verify Google Cloud authentication
gcloud auth list
gcloud config get-value project

# Check required APIs
gcloud services list --enabled

# Test with minimal deployment
adk deploy cloud_run agents/devops --project PROJECT --region REGION
```

### Debug Mode
```bash
# Enhanced logging
adk run agents/devops --log_level DEBUG

# Cloud tracing
adk run agents/devops --trace_to_cloud

# Verbose deployment
adk deploy cloud_run agents/devops --verbosity debug
```

## 📊 Performance and Monitoring

### Token Tracking
The TUI provides real-time token usage monitoring:
- **Prompt Tokens**: Input processing
- **Thinking Tokens**: Gemini 2.5 reasoning
- **Output Tokens**: Response generation
- **Total Usage**: Cumulative consumption

### Tool Monitoring
Track tool usage and performance:
- **Execution Time**: Duration for each tool
- **Success/Failure**: Visual indication of results
- **Tool Categories**: Organized by functional area

### Session Analytics
- **Command History**: Track usage patterns
- **Session Duration**: Monitor session length
- **Error Rates**: Identify common issues
- **Performance Metrics**: Response times and efficiency

## 🚀 Advanced Usage

### Multi-Agent Workflows
```bash
# Different agents for different tasks
adk run agents/devops     # Infrastructure tasks
adk run agents/security   # Security analysis
adk run agents/frontend   # Frontend development
```

### Integration Patterns
```bash
# API integration
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"app_name": "devops", "user_id": "user1", "session_id": "session1", "new_message": {...}}'

# Webhook integration
adk api_server agents/ --host 0.0.0.0 --port 8080
```

### Custom Deployment
```bash
# Custom Docker deployment
adk deploy cloud_run agents/devops \
  --temp_folder ./custom_build \
  --adk_version 1.0.0 \
  --verbosity info

# Environment-specific deployment
adk deploy cloud_run agents/devops \
  --project prod-project \
  --region us-west1 \
  --service_name prod-devops-agent \
  --session_db_url "agentengine://prod-resource"
```

## 📚 Additional Resources

- **[Usage Guide](../usage.md)**: Complete setup and configuration guide
- **[Features](../features.md)**: Comprehensive feature overview
- **[Contributing](../contributing.md)**: How to contribute to the project
- **Example Prompts**: Check the `example_prompts/` directory for usage examples

---

The DevOps Agent CLI provides a comprehensive suite of interfaces and tools to support modern DevOps workflows, from local development to enterprise deployment. 