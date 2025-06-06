# DevOps Agent

## Overview

The DevOps Agent is a sophisticated AI assistant engineered to empower developers and DevOps engineers across the full software development lifecycle, from infrastructure management to operational excellence. This production-ready agent represents the culmination of comprehensive Phase 2 development, featuring advanced context management, intelligent planning workflows, and RAG-enhanced codebase understanding.

Built on the **Google Agent Development Kit (ADK)** foundation with **Google Gemini LLMs** providing advanced reasoning capabilities, the agent utilizes **ChromaDB** for semantic code search and incorporates cutting-edge context management with multi-factor relevance scoring, automatic content discovery, and intelligent summarization. The result is an agent that provides contextually-aware assistance while maintaining optimal performance and user experience.

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
*   **Advanced Context Management:** Features intelligent multi-factor relevance scoring, automatic content discovery, cross-turn correlation, and intelligent summarization. The system achieves 244x improvement in token utilization while maintaining context quality through smart prioritization algorithms.
*   **Interactive Planning:** Collaborative workflow for complex tasks with plan generation, user review, and iterative refinement before implementation. Improves task accuracy and reduces rework through upfront alignment.
*   **RAG-Enhanced Codebase Understanding:** Deep semantic search and retrieval using ChromaDB vector storage with Google embeddings. Enables automatic project context gathering from README files, package configurations, Git history, and documentation.
*   **Comprehensive Tool Integration:** Versatile suite including file operations, code search, vetted shell execution, codebase indexing/retrieval, and intelligent tool discovery with safety-first approach and user approval workflows.
*   **Proactive Context Addition:** Automatically discovers and includes project files, Git history, documentation, and configuration files with zero manual intervention. Enhanced support for modern Python packaging with `uv` detection.
*   **Token Optimization & Transparency:** Dynamic token limit determination, usage transparency with detailed breakdowns, accurate counting methods, and context optimization strategies to maximize relevance within limits.
*   **Production-Ready Architecture:** Built on Google ADK with robust error handling, comprehensive logging, full type annotations, and enterprise-grade deployment capabilities via Google Cloud Run.
*   **Enhanced User Experience:** Rich interactive CLI, detailed execution feedback, granular error reporting, and intelligent status indicators providing clear insight into agent operations and decision-making processes.

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

## Advanced Configuration

### Gemini Thinking Feature

The DevOps Agent supports **Gemini's advanced thinking capabilities** for enhanced reasoning and complex problem-solving. This feature leverages Gemini 2.5 series models' internal reasoning process to provide better results for complex DevOps tasks.

**Supported Models:**
- `gemini-2.5-flash-preview-05-20` (Gemini 2.5 Flash with thinking)
- `gemini-2.5-pro-preview-06-05` (Gemini 2.5 Pro with thinking)

**Configuration:**

Create or update your `.env` file in the project root with these settings:

```bash
# Enable Gemini thinking (default: false)
GEMINI_THINKING_ENABLE=true

# Include thought summaries in responses (default: true)  
GEMINI_THINKING_INCLUDE_THOUGHTS=true

# Set thinking budget (tokens allocated for reasoning, default: 8192)
GEMINI_THINKING_BUDGET=8192

# Use a 2.5 series model that supports thinking
AGENT_MODEL=gemini-2.5-pro-preview-06-05
# or
AGENT_MODEL=gemini-2.5-flash-preview-05-20

# Your Google API key (required)
GOOGLE_API_KEY=your_api_key_here
```

**What Thinking Enables:**

- **Enhanced Problem Solving:** The model can "think through" complex DevOps scenarios step-by-step before responding
- **Better Planning:** Improved analysis and planning for multi-step operations 
- **Debugging Assistance:** More thorough reasoning when troubleshooting issues
- **Code Analysis:** Deeper understanding when analyzing complex codebases

**Usage Transparency:**

When thinking is enabled, you'll see:
- 🧠 **Enhanced usage display** showing thinking tokens separately from output tokens
- **Thought summaries** (when `GEMINI_THINKING_INCLUDE_THOUGHTS=true`) providing insight into the model's reasoning process
- **Detailed token breakdown** including thinking costs in logs

**Example with thinking enabled:**

1. **Create/update your `.env` file:**
   ```bash
   GEMINI_THINKING_ENABLE=true
   AGENT_MODEL=gemini-2.5-pro-preview-06-05
   GOOGLE_API_KEY=your_api_key_here
   ```

2. **Run the agent:**
   ```bash
   PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx --with extensions --with google-generativeai --with google-api-core --with chromadb --with protobuf --with openai --with tiktoken --no-cache --python 3.13 --from git+https://github.com/BlueCentre/adk-python.git@main adk run devops
   ```

   Or use the convenience script:
   ```bash
   ./run.sh
   ```

**Performance Considerations:**

- **Thinking Budget:** Higher values (16384+) enable more complex reasoning but increase costs
- **Token Usage:** Thinking tokens are charged in addition to input/output tokens
- **Response Time:** Complex reasoning may take longer but produces higher quality results
- **Model Selection:** Gemini 2.5 Pro generally provides deeper reasoning than Flash for complex tasks

**Best Use Cases for Thinking:**

- Complex infrastructure planning and design
- Multi-step deployment troubleshooting  
- Advanced code refactoring and optimization
- System architecture analysis and recommendations
- Security analysis and compliance checks

## Core Technologies / Stack

The DevOps Agent leverages a powerful stack of technologies to deliver its capabilities:

*   **Google Agent Development Kit (ADK):** The foundational framework that provides core agent capabilities, including LLM integration, tool management, and execution lifecycle.
*   **Google Gemini Large Language Models:** The advanced AI models (specifically Gemini Pro and Gemini Flash) that power the agent's understanding, reasoning, planning, and code generation abilities.
*   **ChromaDB:** A vector database used to store embeddings of codebases, enabling powerful semantic search and retrieval (RAG) for codebase understanding features.
*   **Python:** The primary programming language used to develop the agent and its tools.

## Directory Structure

```
devops/
├── devops_agent.py           # Main agent implementation (ADK LlmAgent)
├── agent.py                  # Agent entry point and configuration  
├── prompts.py                # Core agent instructions and persona
├── config.py                 # Configuration management and environment setup
├── components/               # Core agent components
│   ├── planning_manager.py   # Interactive planning workflow management
│   └── context_management/   # Advanced context management system
│       ├── context_manager.py           # Main context orchestration
│       ├── smart_prioritization.py     # Multi-factor relevance scoring
│       ├── cross_turn_correlation.py   # Turn relationship detection  
│       ├── intelligent_summarization.py # Content-aware compression
│       └── dynamic_context_expansion.py # Automatic content discovery
├── tools/                    # Comprehensive tool suite
│   ├── __init__.py          # Tool registration and exports
│   ├── rag_tools.py         # RAG indexing and retrieval tools
│   ├── rag_components/      # ChromaDB and embedding components
│   │   ├── chunking.py      # AST-based code chunking
│   │   ├── indexing.py      # Vector embedding and storage  
│   │   └── retriever.py     # Semantic similarity search
│   ├── filesystem.py        # File system operations
│   ├── shell_command.py     # Vetted command execution
│   ├── code_analysis.py     # Static code analysis capabilities
│   ├── code_search.py       # Code pattern search utilities
│   ├── project_context.py   # Project-level context gathering
│   └── [additional tools]   # Memory, analysis, and utility tools
├── shared_libraries/         # Shared utilities and common functions
├── docs/                     # Documentation and specifications
│   ├── IMPLEMENTATION_STATUS.md     # Current implementation status
│   ├── CONTEXT_MANAGEMENT_STRATEGY.md # Context management approach
│   └── features/            # Feature-specific documentation
│       ├── FEATURE_AGENT_INTERACTIVE_PLANNING.md
│       ├── FEATURE_RAG.md
│       ├── PHASE2_IMPLEMENTATION_DETAILS.md
│       └── [other features]
└── .indexignore             # RAG indexing exclusion rules
```

## Technical Design

The DevOps Agent is architected as an `LlmAgent` within the Google ADK framework. Its core components are:

*   **`devops_agent.py` (`MyDevopsAgent`):** The heart of the DevOps Agent, defining the `MyDevopsAgent` class which inherits from the **Google ADK's** `LlmAgent`. This class orchestrates all agent capabilities through custom ADK callback handlers (`handle_before_model`, `handle_after_model`, etc.) that manage state, integrate planning workflows, and optimize context delivery. It seamlessly coordinates the `PlanningManager` and advanced `ContextManager` to enable sophisticated, context-aware operations with **Gemini LLM** integration.

*   **`prompts.py`:** Contains the static core instructions and persona definition for the **Gemini LLM**, establishing the agent's foundational behavior, expertise areas, and interaction patterns with users and tools.

*   **Advanced Context Management (`components/context_management/`):** A comprehensive system featuring:
    - **Smart Prioritization:** Multi-factor relevance scoring with content, recency, frequency, error priority, and coherence weighting
    - **Cross-Turn Correlation:** Relationship detection and pattern recognition across conversation turns  
    - **Intelligent Summarization:** Content-aware compression with 8 content type detection and keyword preservation
    - **Dynamic Context Expansion:** 4-phase discovery process for automatic content discovery and file classification

*   **Interactive Planning (`components/planning_manager.py`):** Drives collaborative workflows through complexity assessment, multi-step plan generation, user review cycles, and plan refinement. Integrates seamlessly with context management for plan-guided execution.

*   **RAG Components (`tools/rag_components/`):** Production-ready retrieval system with AST-based code chunking, ChromaDB vector storage, Google embedding integration, and semantic similarity search for deep codebase understanding.

*   **Comprehensive Tool Suite (`tools/`):** Feature-rich collection including file operations, vetted shell execution, code analysis, project context gathering, memory management, and intelligent tool discovery with safety-first design patterns.

*   **Google ADK Framework:** Provides the robust foundation for agent execution, tool management, LLM interaction, state management, and enterprise deployment capabilities.

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

In essence, the ADK provides the "operating system" for the agent, while `devops_agent.py`, `prompts.py`, `config.py`, and the custom tools define the specific "application" logic and capabilities of the DevOps Agent. This separation allows developers to focus on the unique aspects of their agent without needing to rebuild common agent infrastructure.

## Agent Architecture Overview

The DevOps Agent follows a sophisticated multi-layered architecture that integrates seamlessly with the Google ADK framework while providing advanced capabilities through custom components.

### Google ADK Framework Integration

```mermaid
graph LR
    subgraph GoogleADKFramework
        ADK_Core[Core Engine]
        ADK_Tools[Tool Management]
        ADK_LLM[LLM Integration]
        ADK_CLI[CLI Deployment]
    end

    subgraph DevOpsAgentApplication
        DevOpsAgent[devops_agent.py]
        PromptPy[prompts.py]
        ConfigPy[config.py]
        CustomTools[Custom Tools]
        ContextMgmt[Context Management]
        PlanningMgr[Planning Manager]
    end

    DevOpsAgent --> ADK_Core
    DevOpsAgent --> ADK_Tools
    DevOpsAgent --> ADK_LLM
    PromptPy --> DevOpsAgent
    ConfigPy --> DevOpsAgent
    ContextMgmt --> DevOpsAgent
    PlanningMgr --> DevOpsAgent
    CustomTools --> ADK_Tools
    ADK_CLI --> DevOpsAgent
```

### Agent Request Processing Lifecycle

The agent processes requests through a sophisticated callback-driven lifecycle that enables advanced planning, context management, and error handling:

```mermaid
graph TD
    UserReq[User Request] --> ADK[ADK Framework]
    ADK --> BeforeModel[handle_before_model]
    
    subgraph "Before Model Processing"
        BeforeModel --> StateInit[Initialize State]
        StateInit --> PlanCheck{Planning Needed?}
        PlanCheck -- Yes --> PlanGen[Generate Plan]
        PlanCheck -- No --> CtxAssembly[Assemble Context]
        PlanGen --> PlanReview[Present to User]
        PlanReview --> PlanApproval{User Approval?}
        PlanApproval -- No --> PlanRefine[Refine Plan]
        PlanRefine --> PlanReview
        PlanApproval -- Yes --> CtxAssembly
        CtxAssembly --> CtxInject[Inject Context into LLM Request]
    end
    
    CtxInject --> LLMCall[LLM Processing]
    LLMCall --> AfterModel[handle_after_model]
    
    subgraph "After Model Processing"
        AfterModel --> ExtractResp[Extract Response]
        ExtractResp --> FuncCalls{Function Calls?}
        FuncCalls -- Yes --> BeforeTool[handle_before_tool]
        FuncCalls -- No --> UpdateState[Update Conversation State]
    end
    
    BeforeTool --> ToolExec[Tool Execution]
    ToolExec --> AfterTool[handle_after_tool]
    
    subgraph "Tool Processing"
        AfterTool --> ErrorCheck{Tool Error?}
        ErrorCheck -- Yes --> ErrorHandler[Enhanced Error Handling]
        ErrorCheck -- No --> ToolSuccess[Process Success]
        ErrorHandler --> RetryLogic{Retry Available?}
        RetryLogic -- Yes --> RetryTool[Execute Retry Tool]
        RetryLogic -- No --> UserGuidance[Provide User Guidance]
        RetryTool --> ToolSuccess
        ToolSuccess --> StateUpdate[Update Tool Results]
    end
    
    StateUpdate --> MoreTools{More Tools?}
    MoreTools -- Yes --> BeforeTool
    MoreTools -- No --> FinalResp[Final Response]
    UpdateState --> FinalResp
    UserGuidance --> FinalResp
    FinalResp --> UserOutput[User Output]
```

## Advanced Context Management Architecture

Our Phase 2 context management system features a sophisticated multi-component architecture that achieves 244x improvement in token utilization while maintaining context quality:

```mermaid
graph TD
    subgraph "Context Manager Core"
        CM[Context Manager] --> SP[Smart Prioritization]
        CM --> CTC[Cross-Turn Correlation]
        CM --> IS[Intelligent Summarization]
        CM --> DCE[Dynamic Context Expansion]
    end

    subgraph "Smart Prioritization Engine"
        SP --> CF[Content Factor]
        SP --> RF[Recency Factor] 
        SP --> FF[Frequency Factor]
        SP --> EF[Error Priority Factor]
        SP --> CHF[Coherence Factor]
        CF --> RS[Relevance Score]
        RF --> RS
        FF --> RS
        EF --> RS
        CHF --> RS
    end

    subgraph "Content Discovery"
        DCE --> PF[Project Files]
        DCE --> GH[Git History]
        DCE --> DOC[Documentation]
        DCE --> CFG[Configuration]
        PF --> FC[File Classification]
        GH --> FC
        DOC --> FC
        CFG --> FC
    end

    subgraph "Intelligent Processing"
        IS --> CT1[Code Detection]
        IS --> CT2[Error Detection]
        IS --> CT3[Config Detection]
        IS --> CT4[Documentation Detection]
        IS --> KP[Keyword Preservation]
        CT1 --> CS[Compressed Summary]
        CT2 --> CS
        CT3 --> CS
        CT4 --> CS
        KP --> CS
    end

    subgraph "State Integration"
        ConvHistory[Conversation History] --> CM
        CodeSnippets[Code Snippets] --> CM
        ToolResults[Tool Results] --> CM
        ProjectContext[Project Context] --> CM
    end

    subgraph "LLM Integration"
        CM --> OptCtx[Optimized Context]
        OptCtx --> TokenLimit{Within Token Limit?}
        TokenLimit -- Yes --> LLMReq[LLM Request]
        TokenLimit -- No --> Compress[Further Compression]
        Compress --> OptCtx
        LLMReq --> LLM[Gemini LLM]
    end

    CTC --> TurnRel[Turn Relationships]
    TurnRel --> CM
```

## Enhanced Tool Execution System

Our robust tool execution system includes comprehensive error handling, automatic retry capabilities, and safety-first design:

```mermaid
graph TD
    ToolCall[Tool Call Request] --> SafetyCheck[Safety Check]
    SafetyCheck --> Whitelisted{Whitelisted?}
    Whitelisted -- Yes --> DirectExec[Direct Execution]
    Whitelisted -- No --> ApprovalCheck{Approval Required?}
    ApprovalCheck -- Yes --> UserApproval[Request User Approval]
    ApprovalCheck -- No --> DirectExec
    UserApproval --> Approved{User Approves?}
    Approved -- No --> Denied[Execution Denied]
    Approved -- Yes --> DirectExec
    
    DirectExec --> ParseStrategy[Select Parsing Strategy]
    
    subgraph "Multi-Strategy Execution"
        ParseStrategy --> Shlex[1. shlex.split]
        Shlex --> ShlexResult{Success?}
        ShlexResult -- No --> Shell[2. shell=True]
        ShlexResult -- Yes --> Success[Execution Success]
        Shell --> ShellResult{Success?}
        ShellResult -- No --> SimpleSplit[3. Simple Split]
        ShellResult -- Yes --> Success
        SimpleSplit --> SimpleResult{Success?}
        SimpleResult -- Yes --> Success
        SimpleResult -- No --> AllFailed[All Strategies Failed]
    end
    
    Success --> ResultProcess[Process Result]
    AllFailed --> ErrorAnalysis[Error Pattern Analysis]
    
    subgraph "Error Recovery"
        ErrorAnalysis --> ErrorType{Error Type}
        ErrorType -- Parsing --> QuoteError[Quote/Parsing Error]
        ErrorType -- Command Not Found --> MissingCmd[Missing Command]
        ErrorType -- Timeout --> TimeoutError[Timeout Error]
        ErrorType -- Permission --> PermError[Permission Error]
        
        QuoteError --> RetryTool[execute_vetted_shell_command_with_retry]
        MissingCmd --> InstallGuide[Installation Guidance]
        TimeoutError --> TimeoutSuggestion[Timeout/Splitting Suggestions]
        PermError --> PermissionGuide[Permission Fix Guidance]
        
        RetryTool --> AltStrategies[Try Alternative Formats]
        AltStrategies --> AltResult{Alternative Success?}
        AltResult -- Yes --> Success
        AltResult -- No --> ManualSuggestions[Manual Intervention Suggestions]
    end
    
    ResultProcess --> UpdateContext[Update Context State]
    InstallGuide --> UserGuidance[Enhanced User Guidance]
    TimeoutSuggestion --> UserGuidance
    PermissionGuide --> UserGuidance
    ManualSuggestions --> UserGuidance
    Denied --> UserGuidance
    
    UpdateContext --> Complete[Tool Execution Complete]
    UserGuidance --> Complete
```

## Codebase Understanding with RAG

A key feature of this DevOps agent is its ability to understand and interact with codebases through Retrieval-Augmented Generation:

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

### RAG Implementation Details

1.  **`index_directory_tool`:** This tool is used to scan a specified directory (e.g., a Git repository). It processes supported file types, breaks them into manageable chunks, generates vector embeddings for these chunks, and stores them in a vector database (ChromaDB). This creates a semantic index of the codebase.
2.  **`retrieve_code_context_tool`:** When the agent needs to understand a part of the codebase to answer a question or perform a task, it uses this tool. It takes a natural language query, converts it to an embedding, and searches the vector database for the most similar (relevant) code chunks.

This RAG (Retrieval Augmented Generation) approach allows the agent to ground its responses and actions in the actual content of the codebase, leading to more accurate and context-aware assistance.
*Note: To ensure the codebase understanding remains accurate, the indexed directory should be re-indexed using `index_directory_tool` with `force_reindex=True` after any significant code modifications.*

## Token Counting and Management

Managing token usage is essential for efficient and cost-effective interactions with Large Language Models. The DevOps Agent implements several strategies to handle this:

1.  **Dynamic Token Limit Determination:** The agent attempts to dynamically fetch the actual token limit for the configured LLM model using the LLM client's capabilities. If this fails, it falls back to predefined limits based on common model types (e.g., Gemini Flash, Gemini Pro).
2.  **Token Usage Transparency:** For each model response, the agent displays detailed token usage statistics (prompt, candidate, and total tokens) using the `ui_utils.display_model_usage` function, providing users with insight into the cost of interactions.
3.  **Context Token Counting:** The `context_management/context_manager.py` component is designed to accurately count tokens for the conversation history and injected context. It includes logic to utilize native LLM client counting methods or the `tiktoken` library if available.
4.  **Context Optimization:** The context management logic aims to optimize the information sent to the LLM to stay within token limits while retaining relevant conversation history and code snippets. This now primarily leverages the `context.state` mechanism provided by the ADK for storing and retrieving this information.

The goal is to ensure token usage is transparent, context is managed effectively to avoid exceeding limits, and the most accurate available counting methods are utilized.

```mermaid
graph TD
    subgraph "Token Limit Determination"
        Agent[DevOps Agent] --> TLD[Determine Token Limit]
        TLD --> ClientAPI{LLM Client API Available?}
        ClientAPI -- Yes --> DynamicLimit[Get Dynamic Limit]
        ClientAPI -- No --> FallbackLimit[Use Model-Specific Fallback]
        DynamicLimit --> TokenLimit[Actual Token Limit]
        FallbackLimit --> TokenLimit
    end
    
    subgraph "Context Assembly & Optimization"
        TokenLimit --> CM[Context Manager]
        CM --> StateSync[Sync with ADK State]
        StateSync --> Prioritize[Smart Prioritization]
        Prioritize --> Correlate[Cross-Turn Correlation]
        Correlate --> Summarize[Intelligent Summarization]
        Summarize --> Expand[Dynamic Context Expansion]
        Expand --> OptContext[Optimized Context]
    end
    
    subgraph "Token Counting & Validation"
        OptContext --> CountTokens[Count Context Tokens]
        CountTokens --> CountMethod{Counting Method}
        CountMethod -- LLM Client --> AccurateCount[Native API Count]
        CountMethod -- tiktoken --> TiktokenCount[tiktoken Count]
        CountMethod -- Fallback --> EstimateCount[Character/4 Estimate]
        AccurateCount --> TotalTokens[Total Token Count]
        TiktokenCount --> TotalTokens
        EstimateCount --> TotalTokens
    end
    
    subgraph "Context Optimization Loop"
        TotalTokens --> WithinLimit{Within Token Limit?}
        WithinLimit -- No --> Compress[Further Compression]
        Compress --> OptContext
        WithinLimit -- Yes --> LLMRequest[Inject into LLM Request]
    end
    
    subgraph "Response Processing"
        LLMRequest --> LLM[Gemini LLM]
        LLM --> Response[LLM Response]
        Response --> Usage{Has Usage Metadata?}
        Usage -- Yes --> ExtractUsage[Extract Token Usage]
        Usage -- No --> NoUsage[No Usage Data]
        ExtractUsage --> DisplayUsage[Display to User]
        NoUsage --> DisplayUsage
        DisplayUsage --> Console[Rich Console Output]
    end
    
    subgraph "Performance Analytics"
        TotalTokens --> Utilization[Calculate Utilization %]
        TokenLimit --> Utilization
        Utilization --> LowUtil{< 20% Utilization?}
        LowUtil -- Yes --> Warning[Low Utilization Warning]
        LowUtil -- No --> OptimalUtil[Optimal Utilization]
        Warning --> Analytics[Log Analytics]
        OptimalUtil --> Analytics
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