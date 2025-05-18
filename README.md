# DevOps Agent

## Overview

The DevOps Agent is a sophisticated AI assistant built using the Google Agent Development Kit (ADK). It is designed to help developers and DevOps engineers with a wide range of tasks related to software development lifecycle, infrastructure management, and operational excellence. The agent leverages Large Language Models (LLMs) and a suite of specialized tools to understand user requests, interact with codebases, execute commands, and automate complex workflows.

## Features

*   **CI/CD Automation:** Assists in setting up, managing, and troubleshooting continuous integration and continuous delivery pipelines.
*   **Infrastructure Management:** Helps with provisioning, configuring, and managing infrastructure resources.
*   **Codebase Understanding:** Can index and analyze code repositories to answer questions about functionality, find relevant snippets, and assist with refactoring.
*   **Workflow Automation:** Automates repetitive DevOps tasks through a combination of LLM reasoning and tool execution.
*   **Interactive Planning:** Supports an interactive planning workflow for complex tasks, allowing users to review and approve the agent's proposed approach before execution. See the [Interactive Planning Workflow](#interactive-planning-workflow) section for details.
*   **Comprehensive Tool Integration:** Equipped with a versatile suite of tools enabling interaction with the environment. This includes core file system operations (reading, writing, listing, editing), powerful code search capabilities (`grep_search` for patterns, `file_search` for paths), secure shell command execution (`execute_vetted_shell_command` with vetting and user approval), codebase indexing and retrieval (`index_directory_tool`, `retrieve_code_context_tool` for RAG), and web research (`google_search_grounding`). The agent can intelligently utilize common DevOps command-line tools found in the user's environment (like `git`, `docker`, `kubectl`, `terraform`) based on availability and context.
*   **Context Management and Token Optimization:** Implements a structured approach to managing conversation history, relevant code snippets, and tool outputs. This system prioritizes key information and employs token counting strategies (including leveraging the LLM client's capabilities, `tiktoken` if available, and fallback methods) to stay within model context limits while maintaining high-quality context for the LLM.
*   **LLM Usage Transparency:** Displays and logs token usage for each model interaction (prompt, candidate, total), providing clear insight into the cost and complexity of agent responses.
*   **Proactive & Safe Tool Usage:** Intelligently discovers available command-line tools and executes shell commands with a strong emphasis on safety, including pre-vetting and user approval for state-changing operations.
*   **Rich Interactive Loop:** Powered by the ADK's `LlmAgent`, enabling complex, multi-turn conversations and sophisticated tool usage.
*   **Enhanced Tool Execution Feedback:** Provides clear console output detailing tool arguments, execution status (success/failure), duration, and results or errors.
*   **Granular Error Reporting:** Offers detailed error messages for failed tool executions and unhandled agent exceptions, including relevant context like command executed, return codes, and stderr/stdout for shell commands.
*   **Robust Agent Lifecycle:** The ADK provides a stable framework for agent execution, state management, and error handling.
*   **Interactive CLI:** Allows users to interact with the agent through a command-line interface.
*   **Cloud Deployment:** Can be deployed as a service on Google Cloud Run.
*   **Extensible:** Built on the Google ADK, allowing for customization and extension with new tools and capabilities.

## Quickstart

To get started with the DevOps Agent, you can use `uvx` to handle dependencies and run the agent without needing to install the Google ADK globally.

1.  **Run the Agent Locally:**
    *Important:* Make sure you have set the `GOOGLE_API_KEY` environment variable with your Google API key:

    ```bash
    export GOOGLE_API_KEY=your_api_key_here
    ```

    This is required for the agent to create a GenAI client when running with the ADK. The key is loaded via the configuration system in `config.py`.

    Use the following command from the root of the repository to run the agent locally with the necessary dependencies and a workaround for a compatibility issue:
    
    ```bash
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx --with extensions --with google-generativeai --with google-api-core --with chromadb --with protobuf --with openai --with tiktoken --no-cache --python 3.13 --from git+https://github.com/BlueCentre/adk-python.git@main adk run devops
    ```
    
    *Note:* The `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` part is a workaround for a compatibility issue between recent `protobuf` versions and older pre-compiled code in some dependencies (`chromadb` via `opentelemetry` components).

    This command will set up a virtual environment with the required packages and start an interactive CLI session with the DevOps agent.

2.  **Deploy to Google Cloud Run:**
    The agent can be deployed as a service to Google Cloud Run.

    ```bash
    adk deploy cloud_run --project=[YOUR_GCP_PROJECT] --region=[YOUR_GCP_REGION] Agents/devops/
    ```
    Replace `[YOUR_GCP_PROJECT]` and `[YOUR_GCP_REGION]` with your Google Cloud project ID and desired region. This command packages the agent and deploys it, making it accessible via an HTTP endpoint.

## Technical Design

The DevOps Agent is architected as an `LlmAgent` within the Google ADK framework. Its core components are:

*   **`agent.py`:** This is the main file that defines the agent class (`MyDevopsAgent`), inheriting from the ADK's `LlmAgent`. It initializes the agent with the LLM model, instructions, and tools. Crucially, it integrates the `PlanningManager` to handle interactive planning and utilizes the context management system to prepare relevant input for the LLM. It also defines custom callback handlers (`handle_before_model`, `handle_after_model`, etc.) to manage the agent's state, process tool outputs, and provide interactive feedback, including handling the planning workflow and integrating with context management.
*   **`prompts.py`:** Contains the core instructions and persona definition for the LLM, guiding its behavior, capabilities, and how it should interact with users and tools. It works in conjunction with `AGENT.md` (located in the agent's operational directory, e.g., `./devops/AGENT.md`) which provides detailed operational context, tool availability, and workflow procedures.
*   **Tools:** A collection of Python functions that the agent can invoke to perform specific actions. These tools are the agent's interface to the external world (e.g., reading files, running commands, searching code).
*   **Context Management (`context_management/`):** This module is responsible for maintaining a rich and optimized context for the LLM. It manages the history of the conversation, tracks relevant code snippets identified during interactions (e.g., via file reads or edits), and processes tool outputs to include key information concisely. It incorporates logic for accurate token counting and prioritizes information to ensure the context stays within model context limits. See the [Token Counting and Management](#token-counting-and-management) section for details on token handling.
*   **Planning Manager (`components/planning_manager.py`):** This component orchestrates the interactive planning process. Based on the user's request and the agent's state, it can trigger the generation of a proposed plan by the LLM. It then manages the interaction with the user for plan approval or refinement before allowing the agent to proceed with the implementation phase. See the [Interactive Planning Workflow](#interactive-planning-workflow) section for a detailed explanation of the workflow.
*   **Google ADK Framework:** Provides the underlying machinery for agent execution, tool management, LLM interaction, session management, and deployment.

### Relation to Google ADK Framework

The DevOps Agent is fundamentally an application built *on top of* the Google ADK. The ADK provides the core capabilities that make the agent functional:

*   **Agent Abstraction (`LlmAgent`):** This is a cornerstone of the ADK. It's a high-level class for creating LLM-powered agents, handling the complexities of LLM interaction, prompt construction, tool dispatch, and managing the state of the conversation. This abstraction is key to enabling a **rich and robust interactive agent loop**, allowing for sophisticated multi-turn dialogues and intelligent tool chaining.
*   **Tool Management:** A system for defining, registering, and securely invoking tools that the agent can use.
*   **LLM Integration:** Connectors and configurations for various LLMs, allowing developers to choose the model that best suits their needs.
*   **CLI and Deployment:** Utilities for running agents locally (`adk run`) and deploying them to cloud environments like Google Cloud Run (`adk deploy cloud_run`).
*   **Session Management:** (Optional) Capabilities to persist and resume agent conversations.
*   **Observability:** (Optional) Integration with tracing and logging for monitoring agent behavior. This agent leverages this by logging detailed information about tool execution (including duration) and LLM token usage.

```mermaid
graph LR
    subgraph GoogleADKFramework
        ADK_Core[Core Engine]
        ADK_Tools[Tool Management]
        ADK_LLM[LLM Integration]
        ADK_CLI[CLI Deployment]
    end

    subgraph DevOpsAgentApplication
        AgentPy[LlmAgent]
        PromptPy[prompts.py]
        AgentMD[AGENT.md]
        CustomTools[Custom Tools]
    end

    AgentPy --> ADK_Core
    AgentPy --> ADK_Tools
    AgentPy --> ADK_LLM
    PromptPy --> AgentPy
    AgentMD --> AgentPy
    CustomTools --> ADK_Tools
    ADK_CLI --> AgentPy
```

In essence, the ADK provides the "operating system" for the agent, while `agent.py`, `prompts.py`, `AGENT.md`, and the custom tools define the specific "application" logic and capabilities of the DevOps Agent. This separation allows developers to focus on the unique aspects of their agent without needing to rebuild common agent infrastructure.

## Codebase Indexing and Retrieval

A key feature of this DevOps agent is its ability to understand and interact with codebases:

1.  **`index_directory_tool`:** This tool is used to scan a specified directory (e.g., a Git repository). It processes supported file types, breaks them into manageable chunks, generates vector embeddings for these chunks, and stores them in a vector database (ChromaDB). This creates a semantic index of the codebase.
2.  **`retrieve_code_context_tool`:** When the agent needs to understand a part of the codebase to answer a question or perform a task, it uses this tool. It takes a natural language query, converts it to an embedding, and searches the vector database for the most similar (relevant) code chunks.

This RAG (Retrieval Augmented Generation) approach allows the agent to ground its responses and actions in the actual content of the codebase, leading to more accurate and context-aware assistance.
*Note: To ensure the codebase understanding remains accurate, the indexed directory should be re-indexed using `index_directory_tool` with `force_reindex=True` after any significant code modifications.*

```mermaid
graph TD
    U[User Input Query] --> DA{DevOps Agent}
    DA -- Understand auth module --> RCT{retrieve_code_context_tool};
    RCT -- Query --> VDB[(Vector Database - Indexed Code)];
    VDB -- Relevant Code Chunks --> RCT;
    RCT -- Code Snippets --> DA;
    DA -- Combines snippets with LLM reasoning --> LR[LLM Response];
    LR --> O[Agent provides explanation based on code];

    subgraph "Initial Indexing (One-time or on update)"
      CI[Codebase Files] --> IDT{index_directory_tool};
      IDT --> VDB;
    end
```

This mechanism significantly enhances the agent's ability to act as a knowledgeable assistant for development-related queries.

## Token Counting and Management

Managing token usage is essential for efficient and cost-effective interactions with Large Language Models. The DevOps Agent implements several strategies to handle this:

1.  **Dynamic Token Limit Determination:** The agent attempts to dynamically fetch the actual token limit for the configured LLM model using the LLM client's capabilities. If this fails, it falls back to predefined limits based on common model types (e.g., Gemini Flash, Gemini Pro).
2.  **Token Usage Transparency:** For each model response, the agent displays detailed token usage statistics (prompt, candidate, and total tokens) using the `ui_utils.display_model_usage` function, providing users with insight into the cost of interactions.
3.  **Context Token Counting:** The `context_management/context_manager.py` component is designed to accurately count tokens for the conversation history and injected context. It includes logic to utilize native LLM client counting methods or the `tiktoken` library if available.
4.  **Context Optimization:** The context management logic aims to optimize the information sent to the LLM to stay within token limits while retaining relevant conversation history and code snippets.
5.  **Placeholder/Fallback Counters:** Basic placeholder token counting methods are available in `devops_agent.py` (`_count_tokens`, `_count_context_tokens`). These are used as a fallback if the more sophisticated counting mechanisms are not fully functional, ensuring the agent can still operate and provide some level of token estimation, albeit less accurate.

The goal is to ensure token usage is transparent, context is managed effectively to avoid exceeding limits, and the most accurate available counting methods are utilized.

```mermaid
graph TD
    A[LLM Response] --> B{Has Usage Metadata?};
    B -- Yes --> C[Extract Token Counts];
    C --> D[Display Usage];
    D --> E[User Console];

    Agent --> F[Context Management];
    F --> G{Count Tokens};
    G -- using LLM Client API --> H[Accurate Count];
    G -- using tiktoken --> I[More Accurate Count];
    G -- using Fallback --> J[Estimated Count];

    F -- Context --> K[LLM Request];
    K --> LLM[LLM];

    Agent --> L[Determine Token Limit];
    L -- using LLM Client API --> M[Dynamic Limit];
    L -- using Fallback Constants --> N[Fallback Limit];
    L --> F;

    subgraph Token Handling Flow
        A --> B;
        B --> C;
        C --> D;
        D --> E;
        Agent --> F;
        F --> G;
        G --> H;
        G --> I;
        G --> J;
        F --> K;
        K --> LLM;
        Agent --> L;
        L --> M;
        L --> N;
    end
```

## Interactive Planning Workflow

The DevOps Agent includes an interactive planning phase to improve collaboration and the quality of output for complex tasks. This workflow is triggered for requests deemed sufficiently complex or when the user explicitly asks for a plan.

**Workflow Steps:**

1.  **Task Assessment:** Upon receiving a user request, the agent assesses its complexity to determine if a planning phase is beneficial.
2.  **Plan Proposal:** If planning is needed, the agent uses the LLM to generate a detailed, multi-step plan outlining the proposed approach to fulfill the request.
3.  **User Review:** The agent presents the generated plan to the user.
4.  **Approval or Refinement:** The user can review the plan and either approve it to proceed or provide feedback for refinement. The agent can iterate on the plan based on user feedback.
5.  **Implementation:** Once the plan is approved by the user, the agent proceeds with executing the steps outlined in the plan, leveraging its tools and context management.

This interactive approach ensures that the agent and the user are aligned on the strategy before significant work is performed, reducing rework and improving the final outcome.

### Agent Interaction Flow

```mermaid
graph TD
    User --> Agent;
    Agent --> Planning{Planning Needed?};
    Planning -- Yes --> ProposePlan[Propose Plan];
    ProposePlan --> User[Review Plan];
    User --> Agent[Approve Plan];
    Agent -- Plan Approved --> ContextMgt[Context Management];
    Planning -- No --> ContextMgt;
    ContextMgt --> LLM[LLM];
    LLM -- Tool Calls --> Agent[Execute Tools];
    Agent[Execute Tools] --> Tools[Tools];
    Tools --> Agent[Process Tool Output];
    Agent[Process Tool Output] --> ContextMgt;
    LLM -- Response --> User;

    subgraph Agent Components
        Planning
        ContextMgt
        Tools
    end
```

**Explanation:**

1.  **User Input:** The user interacts with the agent, typically via the ADK CLI (`adk run`) or an API endpoint if deployed.
2.  **Agent Decision:** The agent determines if a planning step is needed based on the complexity of the task.
3.  **Propose Plan:** If planning is needed, the agent generates a detailed plan.
4.  **Review Plan:** The user reviews the proposed plan.
5.  **Approve Plan:** The user approves the plan.
6.  **Context Management:** The agent prepares the context for the LLM, including relevant code snippets and tool outputs.
7.  **LLM:** The LLM processes the input, "thinks" about the request, and decides if a tool needs to be used. It might select one or more tools from the agent's toolset.
8.  **Tool Invocation:** If a tool is selected, the `LlmAgent` invokes the corresponding Python function (e.g., `read_file_content`, `execute_vetted_shell_command`).
9.  **Tool Output:** The tool executes and returns its output to the `LlmAgent`.
10. **Process Tool Output:** The agent processes the tool output and integrates it with the context.
11. **LLM Response Generation:** The agent sends the processed output back to the LLM, which then formulates the final response to the user.
12. **User Output:** The ADK framework delivers the agent's response to the user.

## Agent Interaction Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant ADK
    participant Agent
    participant Planning
    participant Context
    participant LLM
    participant Tools

    User->>ADK: Query
    ADK->>Agent: Query
    Agent->>Planning: Assess Need
    alt Planning Needed
        Planning->>LLM: Request Plan
        LLM-->>Planning: Proposed Plan
        Planning->>Agent: Forward Plan
        Agent->>User: Present Plan
        User->>Agent: Approve
        Agent->>Planning: Approval Status
    end
    Agent->>Context: Prepare Context
    Context-->>Agent: Optimized Context
    Agent->>LLM: Process Request
    LLM-->>Agent: Thought Selection
    Agent->>Tools: Invoke Tool
    Tools-->>Agent: Tool Output
    Agent->>Context: Update Context
    Agent->>LLM: Generate Response
    LLM-->>Agent: Final Response
    Agent->>ADK: Send Output
    ADK-->>User: Display Output
```