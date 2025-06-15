# Input Pane Usage Guide

## How to Type in the Interruptible CLI

The interruptible CLI provides a **persistent input pane** at the bottom of the screen where you can always type, even while the agent is responding.

### 🎯 Interface Layout

```
┌─────────────────────────────────────────┐
│          🤖 Agent Output                │  ← Agent responses appear here
│                                         │
│  [10:30:45] 🤖 Agent: Hello! How can    │
│  I help you today?                      │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│          😎 User Input                  │  ← You type here
│                                         │
│  > your message here...█                │  ← Cursor active
│                                         │
├─────────────────────────────────────────┤
│ 🟢 Ready | Theme: 🌒 Dark | 10:30:45   │  ← Status bar
└─────────────────────────────────────────┘
```

### ⌨️ How to Type

1. **Start typing immediately** - The input pane is **always focused and ready**
2. **Type your message** - All keyboard input goes to the input pane by default
3. **Press Enter** - Submit your message to the agent
4. **Alt+Enter** - Add a new line for multi-line messages

### 🚀 Key Features

#### **Persistent Input**
- ✅ **Type while agent is responding** - No need to wait
- ✅ **Input remains active** - Always ready for your next command
- ✅ **Multi-line support** - Use Alt+Enter for longer messages

#### **Agent Interruption**
- 🛑 **Ctrl+C** - Interrupt long-running agent operations
- ⚡ **Immediate responsiveness** - Continue typing after interruption
- 🔄 **Clean recovery** - System returns to ready state

### 📋 Keyboard Shortcuts

| Key Combination | Action |
|-----------------|--------|
| **Enter** | Submit your input to the agent |
| **Alt+Enter** | Insert newline (for multi-line input) |
| **Ctrl+C** | Interrupt running agent |
| **Ctrl+D** | Exit the CLI |
| **Ctrl+L** | Clear the output pane |
| **Ctrl+T** | Toggle theme (dark/light) |
| **Tab** | Keep focus on input pane |

### 💡 Usage Tips

#### **While Agent is Thinking**
```
🟡 Thinking... | Theme: 🌒 Dark | 10:30:45
```
- ✅ You can still type your next question
- ✅ Input accumulates in the input pane
- ✅ Press Ctrl+C to interrupt if needed

#### **When Agent is Ready**
```
🟢 Ready | Theme: 🌒 Dark | 10:30:45
```
- ✅ Type and press Enter to submit
- ✅ Agent will process immediately
- ✅ Your input is cleared after submission

### 🎨 Visual Feedback

The interface provides clear visual cues:

- **Input Pane Title Changes**:
  - `😎 User Input (Enter to send, Alt+Enter for newline)` - When ready
  - `💭 User Input (Ctrl+C to interrupt agent)` - When agent is running

- **Status Bar Updates**:
  - `🟢 Ready` - Agent waiting for input
  - `🟡 Thinking...` - Agent processing your request

### 🔧 Technical Details

#### **Focus Management**
- Input buffer **automatically receives focus** on startup
- Focus **remains on input pane** during normal operation
- **Tab key** ensures focus returns to input if lost

#### **Buffer Management**
- **Input buffer**: Where you type (editable)
- **Output buffer**: Agent responses (read-only, programmatically updated)
- **Status buffer**: Real-time status (auto-updated)

#### **Editing Mode**
- Uses **Emacs editing mode** for familiar keyboard shortcuts
- Supports standard text editing operations
- Multi-line editing with proper line handling

### 🐛 Troubleshooting

#### **Can't Type?**
1. Make sure the CLI started without errors
2. Try pressing **Tab** to ensure focus is on input pane
3. Check that your terminal supports the interface

#### **Enter Not Working?**
- Enter only works when agent is **not running**
- If agent is running, press **Ctrl+C** first to interrupt
- Use **Alt+Enter** for newlines, not Enter

#### **Missing Cursor?**
- The cursor should be visible in the input pane
- Try pressing any key to activate input
- Terminal compatibility may affect cursor display

### 🎯 Example Workflow

1. **Start the CLI**:
   ```bash
   uv run agent run agents.devops --interruptible
   ```

2. **See the interface load** with input pane ready

3. **Type your first message**:
   ```
   > hello agent, can you help me?
   ```

4. **Press Enter** - Message sent to agent

5. **While agent responds, type your next question**:
   ```
   > what kubernetes clusters are available?
   ```

6. **Press Ctrl+C if needed** to interrupt long operations

7. **Continue the conversation** seamlessly

The input pane transforms the CLI from a **sequential** question-answer pattern to a **dynamic**, **always-ready** interface that puts you in complete control! 🎉 