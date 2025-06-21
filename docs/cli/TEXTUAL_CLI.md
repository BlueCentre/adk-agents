---
layout: default
title: Textual CLI Guide
parent: CLI Documentation
nav_order: 1
description: "Complete guide to the Textual CLI with persistent input panes and agent interruption capabilities."
---

# Textual CLI for ADK Agents

The ADK supports an advanced **Textual CLI** (TUI) that provides persistent input capabilities, real-time agent interaction, and comprehensive visual feedback. This interface transforms the traditional command-line experience into a dynamic, responsive environment.

## 🎯 Key Features

### Persistent Input Pane
- **Always-available input**: Type commands while the agent is processing
- **Multi-pane interface**: Dedicated output, thought, and input areas
- **Real-time typing**: Continue working without waiting for responses
- **Command categorization**: Organized auto-completion by functional areas

### Agent Interruption & Control
- **Ctrl+C interruption**: Stop long-running operations instantly
- **Graceful cancellation**: Clean agent task termination
- **Immediate responsiveness**: Continue with new queries after interruption
- **Task management**: Visual indication of agent state and progress

### Enhanced Visual Interface
- **Themed interface**: Dynamic dark and light themes with instant switching
- **Status indicators**: Real-time display of agent state, token usage, and tool activity
- **Agent thoughts display**: Optional side pane showing agent's reasoning process
- **Rich formatting**: Markdown rendering, syntax highlighting, and structured output
- **Token tracking**: Real-time display of prompt, thinking, and output tokens

## 🚀 Usage

### Command Line Options

```bash
# Enable Textual CLI
adk run agents/devops --tui

# With theme selection
adk run agents/devops --tui --ui_theme dark
adk run agents/devops --tui --ui_theme light

# With session management
adk run agents/devops --tui --save_session --session_id my_session

# Resume previous session
adk run agents/devops --tui --resume my_session.json
```

### Interface Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 Agent Output (🟢 Ready)          │  ℹ️ Events (Ctrl+Y to toggle)        │
│                                       │                                       │
│  Agent responses appear here in       │  • Tool: code_search                 │
│  real-time with rich formatting      │    Duration: 1.2s                    │
│  and syntax highlighting             │  • Model: gemini-2.0-flash-001       │
│                                       │    Tokens: 150 prompt, 300 output    │
│                                       │  • Agent thinking: 45 tokens         │
├───────────────────────────────────────┴───────────────────────────────────────┤
│  🧑 User Input                                                                │
│                                                                               │
│  > Type your commands here... Tab for completions                            │
│                                                                               │
├───────────────────────────────────────────────────────────────────────────────┤
│  🤖 DevOps Agent | 🧑 Session: abc123... | 💡 Enter:submit Alt+Enter:newline │
└───────────────────────────────────────────────────────────────────────────────┘
```

## ⌨️ Keyboard Shortcuts

### Essential Controls
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | Submit input | Send command to agent (when ready) |
| `Alt+Enter` | Insert newline | Add line break for multi-line input |
| `Ctrl+C` | Interrupt agent | Stop running agent operations |
| `Ctrl+D` | Exit application | Quit the CLI |
| `Ctrl+L` | Clear output | Clear the output pane |

### Interface Controls
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+T` | Toggle theme | Switch between dark/light themes |
| `Ctrl+Y` | Toggle thoughts | Show/hide agent thought pane |
| `Tab` | Auto-complete | Show categorized command completions |
| `↑/↓` | History navigation | Navigate command history |
| `Ctrl+P/N` | History navigation | Alternative history navigation |

### Command Categories

The TUI provides intelligent auto-completion organized by functional areas:

#### 🚀 Infrastructure & DevOps
- `create a dockerfile`
- `create docker-compose.yml`
- `write kubernetes manifests`
- `create helm chart for`
- `write terraform code for`
- `setup CI/CD pipeline`
- `configure github actions`
- `setup monitoring for`
- `list the k8s clusters and indicate the current one`

#### 🔍 Code Analysis
- `analyze this code`
- `review the codebase`
- `find security vulnerabilities`
- `optimize performance of`
- `refactor this function`
- `add error handling to`
- `write unit tests for`
- `debug this issue`

#### 📦 Deployment & Operations
- `deploy to production`
- `deploy to staging`
- `rollback deployment`
- `check service status`
- `troubleshoot deployment`
- `scale the service`

#### 🔧 Development Workflow
- `create new feature branch`
- `merge pull request`
- `tag new release`
- `update changelog`
- `execute regression tests`
- `summarize, commit, and push changes`

## 🎨 Visual Features

### Theme Support
- **Dark Theme**: Professional dark interface with syntax highlighting
- **Light Theme**: Clean light interface for bright environments
- **Dynamic Switching**: Instant theme changes with `Ctrl+T`
- **Auto-detection**: Respects system theme preferences

### Status Indicators
- **🟢 Ready**: Agent waiting for input
- **🟡 Thinking**: Agent processing with animated indicator
- **🔴 Error**: Error state with detailed information
- **⚡ Running**: Agent executing tools or operations

### Token Usage Display
Real-time tracking of:
- **Prompt Tokens**: Input processing tokens
- **Thinking Tokens**: Reasoning tokens (Gemini 2.5 models)
- **Output Tokens**: Response generation tokens
- **Total Usage**: Cumulative token consumption
- **Model Information**: Current model and configuration

### Tool Activity Monitoring
- **Tool Execution**: Real-time tool usage display
- **Duration Tracking**: Execution time for each tool
- **Success/Failure**: Visual indication of tool results
- **Tool Categories**: Organized display by tool type

## 🔧 Technical Architecture

### Async Task Management
```python
class AgentTUI(App):
    """Textual application with concurrent agent interaction."""
    
    # Reactive state management
    agent_running: reactive[bool] = reactive(False)
    agent_thinking: reactive[bool] = reactive(False)
    
    # Token and tool tracking
    _prompt_tokens: reactive[int] = reactive(0)
    _thinking_tokens: reactive[int] = reactive(0)
    _tools_used: reactive[int] = reactive(0)
```

### Interruption Mechanism
1. **Signal Detection**: `Ctrl+C` binding captures interrupt
2. **Task Cancellation**: Current agent task receives cancellation
3. **Cleanup**: Resources cleaned up gracefully
4. **State Recovery**: System returns to ready state

### Component Architecture
- **AgentTUI**: Main Textual application managing layout and state
- **CategorizedInput**: Enhanced input widget with auto-completion
- **CompletionWidget**: Modal completion selection interface
- **RichLog**: Output rendering with rich formatting support

## 📋 Usage Examples

### Basic Interaction
```bash
# Start TUI
adk run agents/devops --tui

# Type command
> create a kubernetes deployment for nginx

# While agent responds, type next command
> what are the current pods in default namespace?

# Interrupt if needed
[Ctrl+C]

# Continue with new command
> help me troubleshoot the failing pod
```

### Multi-line Commands
```bash
# Use Alt+Enter for complex requests
> Create a comprehensive monitoring setup that includes:
[Alt+Enter]
> - Prometheus for metrics collection
[Alt+Enter]
> - Grafana for visualization
[Alt+Enter]
> - AlertManager for notifications
[Alt+Enter]
> - Custom dashboards for our services
[Enter to submit]
```

### Session Management
```bash
# Start with session saving
adk run agents/devops --tui --save_session --session_id infrastructure_work

# Work on tasks...
# Session automatically saved on exit

# Resume later
adk run agents/devops --tui --resume infrastructure_work.json
```

## 🎯 Best Practices

### Efficient Workflows
1. **Use Tab Completion**: Leverage categorized commands for faster input
2. **Multi-line Planning**: Use `Alt+Enter` for complex, structured requests
3. **Interrupt Wisely**: Use `Ctrl+C` to stop long operations when needed
4. **Monitor Tokens**: Keep an eye on token usage for cost management
5. **Save Sessions**: Use session management for long-term projects

### Performance Tips
- **Theme Selection**: Choose theme based on environment and preference
- **Thought Display**: Toggle thoughts pane based on need for reasoning visibility
- **Command History**: Use `↑/↓` to quickly access recent commands
- **Categorized Completion**: Use Tab to discover available command patterns

## 🔍 Troubleshooting

### Common Issues

**TUI Not Starting:**
```bash
# Check terminal compatibility
echo $TERM

# Try with explicit theme
adk run agents/devops --tui --ui_theme dark

# Fall back to regular CLI
adk run agents/devops
```

**Input Not Responding:**
- Ensure agent is in ready state (🟢)
- Try `Ctrl+C` to interrupt if agent is running
- Check for terminal focus issues

**Theme Issues:**
- Use `Ctrl+T` to toggle themes
- Set explicit theme with `--ui_theme` flag
- Check terminal color support

**Completion Not Working:**
- Press `Tab` to trigger completions
- Ensure input focus is active
- Try typing partial command before Tab

### Debug Mode
```bash
# Enable enhanced logging
adk run agents/devops --tui --log_level DEBUG

# With cloud tracing
adk run agents/devops --tui --trace_to_cloud
```

## 🚀 Advanced Features

### Custom Styling
The TUI uses CSS-like styling defined in `ui_textual.tcss`:
- Customizable colors and themes
- Responsive layout adaptation
- Rich text formatting support

### Integration Points
- **Session Services**: SQLite, Agent Engine, PostgreSQL
- **Artifact Storage**: Google Cloud Storage, local storage
- **Monitoring**: Cloud Trace, structured logging
- **Authentication**: Configurable auth mechanisms

---

The Textual CLI transforms agent interaction from sequential Q&A to a dynamic, responsive interface that puts you in complete control of your DevOps workflows.
