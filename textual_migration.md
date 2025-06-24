# UI Migration Plan: prompt_toolkit to Textual

## ✅ MIGRATION COMPLETED SUCCESSFULLY!

**Status**: Both UI modes are now fully functional:
- **Basic CLI mode** (`uv run agent run agents.devops`) - Uses `prompt_toolkit` with enhanced features
- **Textual CLI mode** (`uv run agent run agents.devops --tui`) - Uses Textual with advanced multi-pane interface

**Key Achievements**:
- ✅ Created fully functional Textual-based `AgentTUI` with multi-pane interface
- ✅ Preserved existing `prompt_toolkit` functionality for basic CLI
- ✅ Fixed all color theme issues and CSS styling
- ✅ Implemented proper callback system for agent interaction
- ✅ Both UI modes load and run successfully
- ✅ Maintained code reuse and existing architecture

---

This document outlines a detailed plan for migrating the existing command-line interface (CLI) implementation from `prompt_toolkit` to `textual`, addressing current issues and leveraging `textual`'s strengths for advanced layouts and maintainability.

## Thorough Analysis of Current UI Implementation

The current UI is primarily built using `prompt_toolkit` for interactive shell aspects and `rich` for visually appealing output and theming.

### Core Components and Their Roles:

*   **`EnhancedCLI` (in `src/wrapper/adk/cli/utils/ui_prompt_toolkit.py`)**:
    *   Provides a traditional single-pane CLI experience.
    *   Uses `PromptSession` for input, history, auto-suggestion, and completion.
    *   Defines custom `KeyBindings` (e.g., `Alt+Enter`, `Ctrl+T`).
    *   Implements a `CategorizedCompleter` for organized auto-completion.
    *   Applies theming using `prompt_toolkit.styles.Style` and `ThemeConfig`.
    *   Displays dynamic status information via `bottom_toolbar`.
    *   Utilizes `rich.Console` for general formatted output.

*   **`TextualCLI` (in `src/wrapper/adk/cli/utils/ui_prompt_toolkit.py`)**:
    *   The more advanced UI for interactive agent sessions.
    *   Uses `HSplit` and `VSplit` for a multi-pane interface (input, output, optional agent thought).
    *   Manages separate `Buffer` objects for `input`, `output`, `status`, and `thought` content.
    *   Employs `Window`s and `Frame`s for borders and titles around panes.
    *   Supports floating `CompletionsMenu` using `FloatContainer` and `Float`.
    *   Dynamically adjusts pane titles based on agent status.
    *   Extends key bindings with `Ctrl+Y` (toggle agent thought), `Ctrl+L` (clear screen), and `Ctrl+C` (interrupt agent).
    *   Manages `asyncio.Task` for agent interruption.
    *   Formats agent responses into `rich.Panel`s via `RichRenderer` for consistent visual appeal.

*   **`RichRenderer` (in `src/wrapper/adk/cli/utils/ui_rich.py`)**:
    *   Handles rendering content using the `rich` library.
    *   Applies `rich.Theme` based on `UITheme`.
    *   Formats agent responses into `rich.Panel` objects and markdown.

*   **`UITheme` and `ThemeConfig` (in `src/wrapper/adk/cli/utils/ui_common.py`)**:
    *   Define color schemes and styling rules for both `prompt_toolkit` and `rich` components.

*   **`StatusBar` (in `src/wrapper/adk/cli/utils/ui_common.py`)**:
    *   Manages the content and formatting of the status bar.

*   **`cli.py`**:
    *   Orchestrates UI initialization, selecting between `EnhancedCLI` or `TextualCLI`.
    *   Includes a fallback mechanism if UI initialization fails.

### Advanced Layouts Being Implemented:

*   **Multi-pane display**: Clear separation of user input, agent output, and agent thoughts.
*   **Dynamic Pane Sizing**: Output and thought panes adjust width based on terminal size.
*   **Interactive Controls**: Custom key bindings for various actions.
*   **Enhanced Input**: Multi-line input, categorized auto-completion, and robust history navigation.
*   **Rich Visual Feedback**: `rich.Panel` and markdown for structured agent responses.
*   **Floating Overlays**: Completion menu appears as an overlay.

### Current Issues with `prompt_toolkit` (as per user query):

Common pain points when building complex UIs with `prompt_toolkit` often include:

1.  **Boilerplate for complex layouts**: Manual composition of `HSplit`, `VSplit`, `Window`, etc., becomes verbose.
2.  **State Management**: Synchronizing state across numerous `Buffer`s and UI elements is challenging.
3.  **Widget Reusability**: Building custom, interactive widgets requires significant manual effort.
4.  **Event Handling**: Managing many custom key bindings and application-level events can become complex.
5.  **Debugging Layouts**: Debugging visual glitches or miscalculations can be challenging due to the lower-level API.

## Plan to Migrate to `textual`

The migration will involve creating a new `textual` application that mirrors the functionality of your current `prompt_toolkit` implementation, while leveraging `textual`'s strengths for layout, widgets, and reactivity. The goal is to reuse existing code structures where possible.

### High-Level Strategy:

- [x] **Introduce `textual` Application**: Create a new `textual.app.App` subclass (`AgentTUI`).
- [x] **Map Layouts**: Translate `prompt_toolkit`'s layout to `textual`'s declarative system (`Vertical`, `Horizontal`, widgets).
- [x] **Port Input/Output**: Replace `prompt_toolkit` `Buffer`s with `textual` widgets like `TextArea` and `RichLog`.
- [x] **Re-implement Features**: Adapt custom completer, key bindings, theming, and agent interruption to `textual`'s event system.
- [x] **Reuse `rich` components**: Your `RichRenderer` and `UITheme`/`ThemeConfig` can be largely reused.
- [x] **Phased Migration**: Initially, keep both `prompt_toolkit` and `textual` paths for testing, then remove old code.

### Detailed Migration Steps and Component Mapping:

#### Step 0: Initial Setup and File Creation

- [x] Create a new file: `src/wrapper/adk/cli/utils/ui_textual.py`.
- [x] Create a new CSS file: `src/wrapper/adk/cli/utils/ui_textual.tcss`.
- [x] Update `src/wrapper/adk/cli/utils/ui.py` to ensure `get_cli_instance` returns an `EnhancedCLI` (prompt_toolkit) instance and `get_textual_cli_instance` returns an `AgentTUI` (Textual) instance.
- [x] Modify `src/wrapper/adk/cli/cli.py` to correctly use `get_cli_instance` for basic interactive mode and `get_textual_cli_instance` for the Textual-based interactive mode.

#### Step 1: Define the `AgentTUI` Application (`src/wrapper/adk/cli/utils/ui_textual.py`)

- [x] Create `AgentTUI` class inheriting from `textual.app.App`.
- [x] Define `CSS_PATH = "ui_textual.tcss"`.
- [x] Define `BINDINGS` for `alt+enter`, `ctrl+t`, `ctrl+y`, `ctrl+l`, `ctrl+d`, `ctrl+c`.
- [x] Define `reactive` attributes for `agent_running`, `agent_thought_enabled`, `agent_name`, `session_id`, `_uptime`, `_current_time`.
- [x] Initialize `theme`, `theme_config`, `rich_renderer`, `status_bar`, `current_agent_task`, `input_callback`, `interrupt_callback`, `command_history`, `history_index` in `__init__`.
- [x] Implement `compose()` method to define the UI layout using `Vertical`, `Horizontal`, `RichLog` (for output and thought panes), `TextArea` (for input), and `Footer`.
    - [x] `Horizontal` container for `output-log` and `thought-log` (conditional).
    - [x] `TextArea` for `input-area` with `max_height=5`.
    - [x] `Footer` for the status bar.
- [x] Implement `on_mount()` to set update interval, focus input, and apply initial theme.
- [x] Implement `_update_status()` to update reactive time and uptime variables.
- [x] Implement `action_insert_newline()` for `Alt+Enter`.
- [x] Implement `action_toggle_theme()` for `Ctrl+T`, handling class removal/addition for theme application.
- [x] Implement `action_toggle_agent_thought()` for `Ctrl+Y`, recomposing the layout dynamically.
- [x] Implement `action_clear_output()` for `Ctrl+L`.
- [x] Implement `action_quit()` for `Ctrl+D`.
- [x] Implement `action_interrupt_agent()` for `Ctrl+C`.
- [x] Implement `on_text_area_submitted()` to handle user input, clear input, update history, and call `input_callback`.
- [x] Implement `add_output()` to write text/Rich Renderables to the `output-log`.
- [x] Implement `add_thought()` to write text/Rich Renderables to the `thought-log` (if enabled).
- [x] Implement `display_agent_welcome()` to show the welcome message using `Textual`'s output methods.
- [x] Implement `set_agent_task()` to set the current agent task and update `agent_running` reactive.
- [x] Implement `register_input_callback()` and `register_interrupt_callback()`.
- [x] Implement `on_key()` for history navigation (`up`, `down`, `ctrl+p`, `ctrl+n`) on `TextArea`.
- [x] Implement `_navigate_history()` helper method for history navigation.

#### Step 2: Create Textual CSS for Theming and Layout (`src/wrapper/adk/cli/utils/ui_textual.tcss`)

- [x] Define base styles for `Screen`, `#main-content`, `.output-pane`, `.thought-pane`, `#input-area`, and `Footer`.
- [x] Define `.light` and `.dark` classes for theme-specific backgrounds and colors.
- [x] Add theme-specific overrides for pane backgrounds and borders (e.g., `.light .output-pane`, `.dark .input-pane`).
- [x] Define styles for `Footer`.
- [x] Map `rich` text styles (e.g., `.info`, `.warning`, `.accent`) to CSS properties for consistent rendering.

#### Step 3: Update `RichRenderer` (`src/wrapper/adk/cli/utils/ui_rich.py`)

- [x] Ensure `format_agent_response()` returns a `rich.Panel`.
- [x] Implement `format_agent_thought()` to return a `rich.Panel` for agent thoughts.
- [x] Verify `rich_renderer.console` initialization in `action_toggle_theme` in `AgentTUI`.

#### Step 4: Update `UITheme` and `ThemeConfig` (`src/wrapper/adk/cli/utils/ui_common.py`)

- [x] In `ThemeConfig.get_rich_theme()`, add new style definitions for `agent.border_color` and `thought.border_color`.
- [x] Review and adjust existing `rich.Theme` mappings to align with `textual`'s rendering.

#### Step 5: Update `ui.py` to Return Correct UI Instances

- [x] Ensure `get_cli_instance()` returns an `EnhancedCLI` (prompt_toolkit) instance.
- [x] Ensure `get_textual_cli_instance()` returns an `AgentTUI` (Textual) instance.
- [x] Remove/comment out old `prompt_toolkit` imports that are no longer needed due to the migration.

#### Step 6: Update `cli.py` to Use Correct UI Instances

- [x] Ensure `prompt_toolkit` imports are present for the `run_interactively` function.
- [x] Ensure `AgentTUI` is imported from `src.wrapper/adk/cli/utils/ui_textual.py`.
- [x] In `run_interactively()`:
    - [x] This function should use `get_cli_instance()` to get the `EnhancedCLI` (prompt_toolkit) instance.
    - [x] Retain its original logic for basic CLI operations, including prompt session creation, command handling (clear, help, theme), and `rich` console output for agent responses.
- [x] In `run_interactively_with_tui()`:
    - [x] This function should use `get_textual_cli_instance()` to get the `AgentTUI` (Textual) instance.
    - [x] Initialize `app_tui` as `AgentTUI`.
    - [x] Set `app_tui.agent_name` from `root_agent.name`.
    - [x] Register callback functions for user input and agent interruption.
    - [x] Implement proper agent output and thought handling.
    - [x] Call `app_tui.display_agent_welcome()` with `root_agent.name`, `root_agent.description`, and `getattr(root_agent, 'tools', [])`.
    - [x] Call `await app_tui.run_async()`.
- [x] Ensure the main `cli.main` function correctly calls `run_interactively` or `run_interactively_with_textual` based on the `tui` flag.

#### Step 7: Adapt `Runner` (Conceptual changes)

- [x] ~~Add `_output_handler`, `_thought_handler`, and `_agent_task_setter` attributes to `Runner`.~~
- [x] ~~Implement `set_output_handler()`, `set_thought_handler()`, and `set_agent_task_setter()` methods.~~
- [x] ~~Modify `handle_user_input()` to use `_output_handler` for user input messages.~~
- [x] ~~Update agent's internal thinking logic to use `_thought_handler`.~~
- [x] ~~Update agent's final response logic to use `_output_handler`.~~

**Note**: Instead of modifying the `Runner` class, we implemented the callback functionality directly in the `run_interactively_with_tui()` function, which works with the standard ADK `Runner` class.

#### Step 8: Implement Categorized Autocompletion for `textual.widgets.Input` or `TextArea`

- [x] **Option B (Advanced)**: Subclass `TextArea` to create `CategorizedTextArea`.
    - [x] Implement logic to filter suggestions based on current input.
    - [x] Implement tab completion to cycle through suggestions.
    - [x] ~~Consider how to display categorized suggestions (e.g., a custom overlay widget).~~

**Note**: We implemented a basic `CategorizedTextArea` with command categorization. The full floating menu feature was simplified for this migration.

#### Step 9: Review and Refine

- [x] Thoroughly test all functionalities: input, output, key bindings, theme toggle, thought pane toggle, agent interruption, welcome message, history, completions.
- [x] Monitor performance for large outputs or rapid updates.
- [x] Consider terminal accessibility features.
- [ ] **Cleanup**: Once the migration is stable, remove `src/wrapper/adk/cli/utils/ui_prompt_toolkit.py` and any other unused `prompt_toolkit` related code/imports.

**Note**: The cleanup step is left for future maintenance as the `prompt_toolkit` code is still being used for the basic CLI mode. 