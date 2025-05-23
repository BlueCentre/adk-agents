# DevOps Agent

## Overview

The DevOps Agent is a sophisticated AI assistant engineered to empower developers and DevOps engineers across the full software development lifecycle, from infrastructure management to operational excellence. This intelligent agent is built using the **Google Agent Development Kit (ADK)**, which provides the foundational framework for its operations. Its advanced reasoning and understanding capabilities are powered by **Google's Gemini family of Large Language Models (LLMs)**, enabling it to comprehend complex user requests and automate intricate workflows. For efficient codebase interaction, the agent utilizes **ChromaDB** as a vector store, facilitating rapid semantic search and retrieval of relevant code segments. Together, these technologies allow the DevOps Agent to seamlessly interact with codebases, execute commands, and provide insightful assistance.

## Features

*   **CI/CD Automation:** Streamlines your software delivery process.
    *   **For Developers:** Accelerate your development cycles. The agent can help generate pipeline configurations, troubleshoot failing builds, and automate deployment steps, getting your code to production faster.
    *   **For Platform Engineers:** Standardize and manage CI/CD pipelines with ease. The agent can assist in creating robust, reusable pipeline templates, monitoring pipeline health, and ensuring consistent deployment practices across services.
*   **Infrastructure Management:** Simplify your cloud and on-premise infrastructure operations.
    *   **For Developers:** Quickly provision development and testing environments that mirror production. Ask the agent to generate Infrastructure-as-Code (IaC) scripts (e.g., Terraform, Ansible) for your application's needs.
    *   **For Platform Engineers:** Automate complex infrastructure tasks. The agent can assist in generating IaC for various resources, managing configurations, and providing insights into resource utilization and cost optimization.
*   **Codebase Understanding (via RAG with ChromaDB):** Unlock deep insights into your code repositories (see [Codebase Indexing and Retrieval](#codebase-indexing-and-retrieval) for details on RAG).
    *   **For Developers:** Onboard to new projects faster by asking the agent about specific functionalities or module dependencies. Debug complex issues by quickly locating relevant code sections and understanding their purpose. Confidently refactor code with the agent's help in identifying usages and potential impacts.
    *   **For Platform Engineers:** Gain clarity on legacy systems for modernization projects. Identify areas for performance optimization or security hardening by analyzing code patterns and configurations. Ensure compliance by asking the agent to find specific configurations or code related to regulatory requirements.
*   **Workflow Automation:** Reclaim time by automating routine and complex DevOps tasks.
    *   **For Developers:** Automate common tasks like generating boilerplate code, running linters/formatters, or creating pull request summaries.
    *   **For Platform Engineers:** Automate incident response procedures (e.g., log collection, service restarts), compliance checks, or resource cleanup tasks.
*   **Interactive Planning:** Tackle complex tasks with confidence through collaborative planning.
    *   **For Developers:** Before the agent refactors a large module or implements a new feature, review and approve its proposed plan, ensuring alignment and catching potential issues early.
    *   **For Platform Engineers:** For intricate infrastructure changes or multi-step deployment processes, vet the agent's plan to ensure safety, compliance, and operational best practices are followed. See the [Interactive Planning Workflow](#interactive-planning-workflow) section for details.
*   **Comprehensive Tool Integration:** Equipped with a versatile suite of tools enabling interaction with the environment. This includes core file system operations (reading, writing, listing, editing), powerful code search capabilities (`grep_search` for patterns, `file_search` for paths), secure shell command execution (`execute_vetted_shell_command` with vetting and user approval), codebase indexing and retrieval (`index_directory_tool`, `retrieve_code_context_tool` for RAG - see [Codebase Indexing and Retrieval](#codebase-indexing-and-retrieval)), and web research (`google_search_grounding`). The agent can intelligently utilize common DevOps command-line tools found in the user's environment (like `git`, `docker`, `kubectl`, `terraform`) based on availability and context.
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
*   **API Error Handling with Retries:** Automatically retries LLM requests encountering `429 RESOURCE_EXHAUSTED` or `500 INTERNAL` errors, optimizing input context on subsequent attempts to improve success rate.
*   **Agent and Runner Cleanup:** Includes logic for cleaning up resources after agent execution. Agent-level cleanup is currently temporarily disabled due to ongoing work on handling cancellation scope issues during shutdown, with runner-level cleanup as a fallback.

## Quickstart

To get started with the DevOps Agent, ensure you have Python 3.13 (or a compatible version) and `uvx` (the Universal Virtualenv Executer from the Google ADK) installed on your system. You can use `uvx` to handle dependencies and run the agent without needing to install the Google ADK globally.

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

## Core Technologies / Stack

The DevOps Agent leverages a powerful stack of technologies to deliver its capabilities:

*   **Google Agent Development Kit (ADK):** The foundational framework that provides core agent capabilities, including LLM integration, tool management, and execution lifecycle.
*   **Google Gemini Large Language Models:** The advanced AI models (specifically Gemini Pro and Gemini Flash) that power the agent's understanding, reasoning, planning, and code generation abilities.
*   **ChromaDB:** A vector database used to store embeddings of codebases, enabling powerful semantic search and retrieval (RAG) for codebase understanding features.
*   **Python:** The primary programming language used to develop the agent and its tools.

## Technical Design

The DevOps Agent is architected as an `LlmAgent` within the Google ADK framework. Its core components are:

*   **`agent.py` (`MyDevopsAgent`):** This is the heart of the DevOps Agent, defining the `MyDevopsAgent` class which inherits from the **Google ADK's** `LlmAgent`. This class initializes the agent with the **Gemini LLM**, defining its core instructions and available tools. It leverages the ADK for orchestrating LLM interactions and tool usage. Crucially, it integrates the `PlanningManager` (which uses the Gemini LLM for plan generation) and the `ContextManager` (which prepares data for the Gemini LLM) to enable sophisticated, context-aware operations. Custom ADK callback handlers (`handle_before_model`, `handle_after_model`, etc.) are used to manage state, process tool outputs, and facilitate interactive workflows.
*   **`prompts.py`:** This file contains the static, core instructions and persona definition for the **Gemini LLM**. These prompts establish the agent's foundational behavior, its areas of expertise, and how it should generally interact with users and tools.
*   **`AGENT.md`:** Working in tandem with `prompts.py`, this file (located in the agent's operational directory, e.g., `./devops/AGENT.md`) provides dynamic, instance-specific operational context to the **Gemini LLM** at runtime. This can include details about the current workspace (like directory structures), discovered tools available in the environment, user preferences, or specific operational parameters. This mechanism, facilitated by the **Google ADK**, allows the agent to tailor its **Gemini LLM's** behavior and responses to the specific environment it's operating in, complementing the static instructions from `prompts.py`.
*   **Tools:** A collection of Python functions, managed and invoked by the **Google ADK**, that the agent can use to perform specific actions. These tools are the agent's interface to the external world (e.g., reading files, running commands, searching code).
*   **Context Management (`context_management/`):** This module, utilizing **Google ADK** state management features, is responsible for maintaining a rich and optimized context for the **Gemini LLM**. It manages conversation history, tracks relevant code snippets (e.g., from file reads or RAG via ChromaDB), and processes tool outputs to include key information concisely. It incorporates logic for accurate token counting (leveraging **Gemini LLM** specifics where possible) and prioritizes information to ensure the context stays within the LLM's token limits, optimizing performance and relevance. See the [Token Counting and Management](#token-counting-and-management) section for details.
*   **Planning Manager (`components/planning_manager.py`):** This component, orchestrated via **Google ADK's** callback system, drives the interactive planning process. It leverages the **Gemini LLM's** advanced reasoning capabilities to generate detailed, multi-step plans based on user requests and the current context. It then manages user interaction for plan approval or refinement before the agent proceeds with implementation. See the [Interactive Planning Workflow](#interactive-planning-workflow) section for a detailed explanation.
*   **Google ADK Framework:** Provides the underlying machinery for agent execution, tool management, LLM interaction, session management, and deployment.

### Relation to Google ADK Framework

The DevOps Agent is fundamentally an application built *on top of* the Google ADK. The ADK provides the core capabilities that make the agent functional:

*   **Agent Abstraction (`LlmAgent`):** This is a cornerstone of the ADK. It's a high-level class for creating LLM-powered agents, handling the complexities of LLM interaction, prompt construction, tool dispatch, and managing the state of the conversation. This abstraction is key to enabling a **rich and robust interactive agent loop**, allowing for sophisticated multi-turn dialogues and intelligent tool chaining.
*   **Tool Management:** A system for defining, registering, and securely invoking tools that the agent can use.
*   **LLM Integration:** Connectors and configurations for various LLMs, allowing developers to choose the model that best suits their needs.
*   **CLI and Deployment:** Utilities for running agents locally (`adk run`) and deploying them to cloud environments like Google Cloud Run (`adk deploy cloud_run`).
*   **Session Management:** (Optional) Capabilities to persist and resume agent conversations.
*   **Observability:** (Optional) Integration with tracing and logging for monitoring agent behavior. This agent leverages this by logging detailed information about tool execution (including duration) and LLM token usage.

### Callback Usage in `MyDevopsAgent`

The `MyDevopsAgent` class, which inherits from the ADK's `LlmAgent`, makes extensive use of the ADK's callback mechanism to customize its behavior at specific points in the agent's execution lifecycle. This is a core aspect of its integration with the ADK framework.

**How it Works:**

1.  **Callback Registration:** In its `__init__` method, `MyDevopsAgent` assigns its own custom methods (e.g., `self.handle_before_model`, `self.handle_after_model`, `self.handle_before_tool`, `self.handle_after_tool`) to the corresponding callback attributes provided by the `LlmAgent` base class (e.g., `self.before_model_callback`, `self.after_model_callback`). This is the standard and recommended way to register callbacks in ADK.

2.  **Custom Logic in Callback Handlers:** These custom handler methods contain the specialized logic for `MyDevopsAgent`, including:
    *   **State Management:** Interacting with `callback_context.state` and `tool_context.state` to manage conversation history, tool invocation details, and other contextual information.
    *   **Planning Integration:** The `PlanningManager` is invoked within these callbacks (primarily `handle_before_model` and `handle_after_model`) to interject planning steps. This manager can return specific ADK objects (like `LlmResponse`) to control the execution flow, such as skipping an LLM call if a plan is being presented or replacing an LLM response if the output is a plan.
    *   **Context Manipulation:** Modifying the `LlmRequest` object in `handle_before_model` to inject assembled context before it's sent to the LLM.
    *   **UI Feedback:** Interacting with UI components (console, status spinners) to provide real-time feedback to the user.

**Alignment with ADK Recommendations:**

This approach is well-aligned with the ADK framework's design for callbacks. The ADK allows any callable (standalone functions or instance methods) to be registered as a callback. For a complex and stateful agent like `MyDevopsAgent`, defining callbacks as methods within the agent's own class offers several advantages:

*   **Encapsulation:** Keeps agent-specific logic contained within the agent class.
*   **State Access:** Allows callbacks to easily access and modify the agent's internal state and components (like `_planning_manager`).
*   **Organization:** Groups related pre-processing and post-processing logic with the agent definition.

Instead of being an abstraction *diverging* from ADK's callback system, `MyDevopsAgent` *leverages* the callback system by providing its own sophisticated implementations for the callback hooks. This demonstrates a robust use of the ADK's extensibility points to build a specialized agent.

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
4.  **Context Optimization:** The context management logic aims to optimize the information sent to the LLM to stay within token limits while retaining relevant conversation history and code snippets. This now primarily leverages the `context.state` mechanism provided by the ADK for storing and retrieving this information.

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