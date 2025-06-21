---
layout: default
title: Input Pane Guide
parent: CLI Documentation
nav_order: 2
description: "Complete guide to using the input pane in the Textual CLI with categorized auto-completion."
---

# Input Pane Usage Guide

## How to Type in the Textual CLI

The Textual CLI provides a **persistent input pane** at the bottom of the screen where you can always type, even while the agent is responding. This guide covers all input features and capabilities.

## 🎯 Interface Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│          🤖 Agent Output (🟢 Ready)                                         │  ← Agent responses
│                                                                             │
│  [10:30:45] 🤖 Agent: I'll help you create that Kubernetes deployment.     │
│  Let me analyze your requirements...                                        │
│                                                                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│          🧑 User Input                                                      │  ← You type here
│                                                                             │
│  > create a kubernetes deployment for[█]                                   │  ← Active cursor
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🤖 DevOps Agent | 🧑 Session: abc123... | 💡 Tab:complete Enter:submit     │  ← Status bar
└─────────────────────────────────────────────────────────────────────────────┘
```

## ⌨️ Input Methods

### Basic Input
1. **Start typing immediately** - The input pane is **always focused and ready**
2. **Type your message** - All keyboard input goes to the input pane by default
3. **Press Enter** - Submit your message to the agent
4. **Alt+Enter** - Add a new line for multi-line messages

### Multi-line Input
For complex requests, use multi-line input:

```
> Create a comprehensive CI/CD pipeline that includes:
[Alt+Enter]
> - GitHub Actions workflow
[Alt+Enter]  
> - Docker containerization
[Alt+Enter]
> - Kubernetes deployment
[Alt+Enter]
> - Monitoring and alerting
[Enter to submit]
```

## 🚀 Auto-completion Features

### Categorized Commands

Press `Tab` to access categorized command completions organized by functional areas:

#### 🚀 Infrastructure & DevOps
- `create a dockerfile`
- `create docker-compose.yml` 
- `write kubernetes manifests`
- `create helm chart for`
- `write terraform code for`
- `setup CI/CD pipeline`
- `configure github actions`
- `setup monitoring for`
- `add logging to`
- `create health checks`
- `setup load balancer`
- `configure autoscaling`
- `list the k8s clusters and indicate the current one`
- `list all the user applications in the qa- namespaces`

#### 🔍 Code Analysis
- `analyze this code`
- `review the codebase`
- `find security vulnerabilities`
- `optimize performance of`
- `refactor this function`
- `add error handling to`
- `add type hints to`
- `add documentation for`
- `write unit tests for`
- `write integration tests for`
- `fix the bug in`
- `debug this issue`

#### 📦 Deployment & Operations
- `deploy to production`
- `deploy to staging`
- `rollback deployment`
- `check service status`
- `troubleshoot deployment`
- `scale the service`
- `update dependencies`
- `backup the database`
- `restore from backup`

#### 🔧 Development Workflow
- `create new feature branch`
- `merge pull request`
- `tag new release`
- `update changelog`
- `bump version number`
- `execute regression tests`
- `run security scan`
- `run performance tests`
- `generate documentation`
- `summarize, commit, and push changes to main using https://www.conventionalcommits.org/en/v1.0.0/#specification`

#### ⚙️ CLI Commands
- `exit`, `quit`, `bye`
- `help`
- `clear`
- `theme toggle`, `theme dark`, `theme light`

### Completion Interface

When you press `Tab`, a modal completion interface appears:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Command Completions                         │
├─────────────────────────────────────────────────────────────────┤
│ 🚀 Infrastructure & DevOps                                     │
│   • create a dockerfile                                        │
│   • create docker-compose.yml                                  │
│   • write kubernetes manifests                                 │
│                                                                 │
│ 🔍 Code Analysis                                               │
│   • analyze this code                                          │
│   • review the codebase                                        │
│                                                                 │
│ 📦 Deployment & Operations                                     │
│   • deploy to production                                       │
│   • deploy to staging                                          │
├─────────────────────────────────────────────────────────────────┤
│ ↑/↓ Navigate | Enter Select | Esc Cancel                      │
└─────────────────────────────────────────────────────────────────┘
```

**Navigation:**
- `↑/↓` or `j/k`: Navigate through options
- `Enter`: Select highlighted option
- `Esc`: Cancel completion
- Type to filter options

## 📋 Keyboard Shortcuts

### Essential Input Controls
| Key Combination | Action | Description |
|-----------------|--------|-------------|
| **Enter** | Submit input | Send your command to the agent |
| **Alt+Enter** | Insert newline | Add line break for multi-line input |
| **Tab** | Auto-complete | Show categorized command completions |
| **↑/↓** | History navigation | Navigate through command history |
| **Ctrl+P/N** | History navigation | Alternative history navigation |

### Agent Control
| Key Combination | Action | Description |
|-----------------|--------|-------------|
| **Ctrl+C** | Interrupt agent | Stop running agent operations |
| **Ctrl+D** | Exit CLI | Quit the application |
| **Ctrl+L** | Clear output | Clear the output pane |

### Interface Control
| Key Combination | Action | Description |
|-----------------|--------|-------------|
| **Ctrl+T** | Toggle theme | Switch between dark/light themes |
| **Ctrl+Y** | Toggle thoughts | Show/hide agent thought pane |

## 🎯 Usage Patterns

### Interactive Development
```bash
# Start with partial command
> create dockerfile[Tab]
# Select from completions
> create a dockerfile

# Add context
> create a dockerfile for my python web application

# Submit and continue
[Enter]

# While agent responds, prepare next command
> now create docker-compose.yml[Tab]
```

### Complex Multi-step Requests
```bash
# Use structured input for complex tasks
> I need help setting up a complete DevOps pipeline:
[Alt+Enter]
> 
[Alt+Enter]
> 1. Create Dockerfile for my Python FastAPI app
[Alt+Enter]
> 2. Set up GitHub Actions for CI/CD
[Alt+Enter]
> 3. Configure Kubernetes deployment
[Alt+Enter]
> 4. Add monitoring and logging
[Alt+Enter]
> 
[Alt+Enter]
> Please create each component step by step.
[Enter to submit]
```

### Quick Commands
```bash
# Use completions for quick access
> setup monitoring[Tab]
# Select: "setup monitoring for"
> setup monitoring for my microservices
[Enter]

# Chain related commands
> check service status[Tab]
> troubleshoot deployment[Tab]
> scale the service[Tab]
```

## 💡 Advanced Features

### Command History
- **Persistent History**: Commands saved across sessions
- **Smart Suggestions**: Recent commands appear in completions
- **Navigation**: Use `↑/↓` to browse history
- **Search**: Type partial command to filter history

### Context-Aware Completions
The completion system adapts to your project:
- **Project Detection**: Discovers your project type and suggests relevant commands
- **File Context**: Suggests commands based on files in your project
- **Git Integration**: Includes git-aware suggestions
- **Environment Detection**: Adapts to your development environment

### Intelligent Filtering
- **Fuzzy Matching**: Type partial words to find commands
- **Category Filtering**: Focus on specific functional areas
- **Recent Commands**: Prioritizes recently used commands
- **Project Context**: Shows project-specific suggestions

## 🎨 Visual Feedback

### Input States
The interface provides clear visual cues about the current state:

**Ready State:**
```
🧑 User Input (Enter to send, Alt+Enter for newline)
> █
```

**Agent Running:**
```
💭 User Input (Ctrl+C to interrupt agent)
> your next command here█
```

**Multi-line Mode:**
```
🧑 User Input (Alt+Enter for more lines, Enter to send)
> line 1
> line 2█
```

### Status Indicators
- **🟢 Ready**: Agent waiting for input
- **🟡 Thinking**: Agent processing with thinking animation
- **⚡ Running**: Agent executing tools or operations
- **🔴 Error**: Error state requiring attention

## 🔧 Customization

### Theme Support
- **Dark Theme**: Professional interface with syntax highlighting
- **Light Theme**: Clean interface for bright environments
- **Dynamic Switching**: Use `Ctrl+T` to toggle themes instantly

### Input Behavior
- **Auto-focus**: Input pane automatically receives focus
- **Persistent State**: Input state maintained during agent operations
- **Smart Clearing**: Input cleared after successful submission
- **Error Recovery**: Input preserved on errors for easy correction

## 🐛 Troubleshooting

### Common Issues

**Can't Type:**
1. Check that the TUI started successfully
2. Press `Tab` to ensure focus is on input pane
3. Verify terminal compatibility

**Completions Not Showing:**
1. Press `Tab` explicitly to trigger completions
2. Ensure you have typing focus in input pane
3. Try typing a few characters before pressing `Tab`

**Enter Not Working:**
- Enter only submits when agent is ready (🟢)
- If agent is running, press `Ctrl+C` first to interrupt
- Use `Alt+Enter` for newlines, not `Enter`

**History Not Working:**
- Use `↑/↓` arrows to navigate history
- Try `Ctrl+P/N` as alternative
- Ensure commands were successfully submitted

### Debug Tips
```bash
# Enable debug mode for troubleshooting
adk run agents/devops --tui --log_level DEBUG

# Check terminal capabilities
echo $TERM
echo $COLORTERM

# Test with explicit theme
adk run agents/devops --tui --ui_theme dark
```

## 🎯 Best Practices

### Efficient Workflows
1. **Use Tab Completion**: Discover available commands quickly
2. **Multi-line Planning**: Structure complex requests clearly
3. **Command Chaining**: Prepare next commands while agent responds
4. **History Navigation**: Reuse and modify previous commands
5. **Interrupt Wisely**: Use `Ctrl+C` when needed, then continue

### Performance Tips
- **Categorized Approach**: Use functional categories to find commands faster
- **Partial Typing**: Type partial commands before Tab for better filtering
- **History Usage**: Leverage command history for repeated tasks
- **Multi-line Structure**: Break complex requests into clear sections

---

The input pane transforms the CLI from a simple command interface into a powerful, responsive workspace that adapts to your DevOps workflow patterns and keeps you productive at all times. 