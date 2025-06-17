# UI Component Styling in ADK CLI

This document outlines where and how the various UI components of the ADK Command Line Interface are styled. The styling is distributed across several key files, utilizing Textual CSS, `prompt_toolkit` for interactive elements, and `rich` for rich content rendering.

## Styling Architecture Diagram

```mermaid
   info
```

```mermaid
graph TD;
    subgraph CLI Application
        A[CLI Application] --> B(Main Content Area);
        B --> C{Panes};
        C --> D[Output Pane];
        C --> E[Thought Pane];
        C --> F[Input Area];
        A --> G[Footer];
    end

    subgraph Key CLI Classes
        P[cli.py] --> Q[EnhancedCLI - ui_prompt_toolkit.py];
        P --> R[InterruptibleCLI - ui_prompt_toolkit.py];
        P --> S[AgentTUI - ui_textual.py];
    end

    subgraph Styling Definitions
        H[ui_textual.tcss] --> D;
        H --> E;
        H --> F;
        H --> G;
        Q --> I[ui_prompt_toolkit.py];
        R --> I;
        S --> H;
        S --> J[ui_rich.py];
        Q --> J;
        R --> J;
        K[ui_common.py] --> I;
        K --> J;
    end

    D -- "Styled by: .output-pane, .light/.dark .output-pane" --> H;
    E -- "Styled by: .thought-pane, .light/.dark .thought-pane" --> H;
    F -- "Styled by: #input-area, .light/.dark .input-pane" --> H;
    G -- "Styled by: Footer, .light/.dark Footer" --> H;
    D -- "Content rendered by: Markdown, Panels" --> J;
    E -- "Content rendered by: Markdown, Panels" --> J;
    I -- "Manages: Theme config, Prompt styles, Completion menu, Toolbar" --> K;
    J -- "Uses: Rich Theme for borders/titles" --> K;
    K -- "Defines: UITheme, ThemeConfig (DARK_THEME, LIGHT_THEME), get_rich_theme, StatusBar" --> A;
    K -- "Defines: Generic message styles (.info, .warning, etc.)" --> H;
    K -- "Defines: Border colors for Rich panels" --> J;

    Q -- "Orchestrates interactive CLI with prompt_toolkit" --> D;
    Q -- "Orchestrates interactive CLI with prompt_toolkit" --> E;
    Q -- "Orchestrates interactive CLI with prompt_toolkit" --> F;
    R -- "Manages persistent input/output panes in a Textual app" --> D;
    R -- "Manages persistent input/output panes in a Textual app" --> E;
    R -- "Manages persistent input/output panes in a Textual app" --> F;
    S -- "Textual Application responsible for TUI layout" --> D;
    S -- "Textual Application responsible for TUI layout" --> E;
    S -- "Textual Application responsible for TUI layout" --> F;
```

## Key CLI Classes and their Role in UI Styling

The ADK CLI leverages several key Python classes to construct and manage its user interface, each playing a specific role in how components are styled and rendered.

*   **`EnhancedCLI`** (found in `src/wrapper/adk/cli/utils/ui_prompt_toolkit.py`): This class is responsible for setting up and managing the interactive prompt session using the `prompt_toolkit` library. It integrates the `ThemeConfig` from `ui_common.py` to apply dynamic styling based on the selected theme (light/dark). It also uses `RichRenderer` (from `ui_rich.py`) for formatting agent responses and other rich content within the standard prompt-based CLI.

*   **`InterruptibleCLI`** (also in `src/wrapper/adk/cli/utils/ui_prompt_toolkit.py`): This class extends `EnhancedCLI` to provide an interruptible CLI experience. It manages the layout of the UI components (input, output, and thought panes) within a `prompt_toolkit` application. While it doesn't directly handle the low-level styling of elements like borders or backgrounds (that's left to Textual CSS), it orchestrates their placement and ensures they use the correct `Rich` console for output.

*   **`AgentTUI`** (found in `src/wrapper/adk/cli/utils/ui_textual.py`): This class is a `Textual` application that defines the overall layout and behavior of the terminal user interface. It is responsible for composing the various panes (output, thought, input) and applying the CSS rules defined in `ui_textual.tcss`. `AgentTUI` utilizes the `Rich` library's `Console` and `Panel` components, often in conjunction with `RichRenderer`, to display formatted text, agent responses, and tool outputs within its panes. It leverages `ui_common.py` for theme-specific `Rich` styling.

## UI Component Styling Summary

| UI Component(s)         | Styling File(s)                                   | Description                                                                                                                                                                                                                                                                          |
|-------------------------|---------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Overall Layout & Panes** | `src/wrapper/adk/cli/utils/ui_textual.tcss`       | Defines the visual appearance of the main UI elements using Textual CSS. This includes:<ul><li>`Screen`: overall background.</li><li>`.light` and `.dark` classes: define background and text colors for light and dark themes.</li><li>`.output-pane`, `.thought-pane`, `#input-area`: define dimensions, borders, margins, padding, background, and scroll behavior for these main display areas.</li><li>`Footer`: styles the bottom status bar.</li><li>Generic message styles: `.info`, `.warning`, `.error`, `.success`, `.accent`, `.highlight`, `.user`, `.agent`, and `.welcome` for various types of text messages. These styles are used by `AgentTUI` and `RichRenderer`.</li></ul> |
| **Interactive CLI Elements** | `src/wrapper/adk/cli/utils/ui_prompt_toolkit.py` | Manages the interactive command-line interface using `prompt_toolkit`. The `EnhancedCLI` and `InterruptibleCLI` classes apply styles dynamically using a `Style` object created from a `theme_config`. This includes styling for:<ul><li>The prompt itself (`prompt`).</li><li>User input (`user-input`).</li><li>Completion menus (`completion-menu`, `completion-menu.completion`, `completion-menu.completion.current`, `completion-menu.category`).</li><li>Auto-suggestions (`auto-suggestion`).</li><li>The bottom toolbar (`bottom-toolbar` and its variations like `bottom-toolbar.accent`, `bottom-toolbar.info`, etc.).</li><li>Status indicators within the toolbar (`status.active`, `status.inactive`, `status.time`, `status.session`, `status.agent`).</li></ul> |
| **Rich Content Rendering** | `src/wrapper/adk/cli/utils/ui_rich.py`            | Acts as a `RichRenderer` (used by `EnhancedCLI`, `InterruptibleCLI`, and `AgentTUI`) and is responsible for displaying richer content such as agent responses, thoughts, and tool outputs. It uses the `rich` library's `Panel` and `Markdown` components, and the border colors for these are pulled from the `rich_theme` defined in `ui_common.py`.                                                                         |
| **Theme Definitions & Colors** | `src/wrapper/adk/cli/utils/ui_common.py`          | Central file that defines the `UITheme` enum (DARK/LIGHT) and the `ThemeConfig` class. This includes:<ul><li>`DARK_THEME` and `LIGHT_THEME` dictionaries: These define the specific color palettes for different UI elements, including prompt, input, output, completion menus, auto-suggestions, and toolbar segments. These configurations are used by `EnhancedCLI` and `InterruptibleCLI`.</li><li>`get_rich_theme()`: This static method returns a `rich.theme.Theme` object based on the current UI theme, which then dictates the colors for elements rendered by `ui_rich.py` (e.g., `agent.border_color` and `thought.border_color`).</li><li>`StatusBar` class: This class is responsible for formatting the content and styles of the segments displayed in the bottom toolbar (e.g., agent name, session ID, uptime, current time).</li></ul> | 