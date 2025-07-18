---
layout: default
title: Architecture
nav_order: 2
description: "Technical architecture and design of the DevOps Agent system."
mermaid: true
---

# Architecture Overview

The DevOps Agent implements a sophisticated, multi-layered architecture that builds upon the Google ADK framework to deliver advanced planning, context management, and codebase understanding capabilities. This design emphasizes performance, safety, and a superior developer experience.

## Google ADK Framework Integration

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

The main components are organized as follows:

```
devops/
├── devops_agent.py           # Main agent implementation (ADK LlmAgent)
├── components/
│   ├── planning_manager.py   # Interactive planning workflow
│   └── context_management/   # Advanced context intelligence
│       ├── smart_prioritization.py     # Multi-factor relevance scoring
│       ├── cross_turn_correlation.py   # Turn relationship detection
│       ├── intelligent_summarization.py # Content-aware compression
│       └── dynamic_context_expansion.py # Automatic content discovery
├── tools/                    # Comprehensive tool suite
│   ├── rag_tools.py         # RAG integration tools
│   ├── rag_components/      # ChromaDB and embedding components
│   └── [additional tools]   # Filesystem, shell, code analysis
└── docs/                     # Consolidated documentation
```

## Agent Request Processing Lifecycle

The agent processes requests through a sophisticated, callback-driven lifecycle that enables advanced planning, context management, and error handling before and after interacting with the LLM.

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

## Per-Sub-Agent MCP Tool Loading System

The agent implements a sophisticated per-sub-agent MCP (Model Context Protocol) tool loading system that provides fine-grained control over tool access for different agents while maintaining security and performance.

```mermaid
graph TD
    subgraph "Global MCP Configuration"
        GMC[.agent/mcp.json] --> GS1[filesystem]
        GMC --> GS2[memory]
        GMC --> GS3[github]
        GMC --> GS4[sonarqube]
        GMC --> GS5[playwright]
    end
    
    subgraph "Root Agent"
        RA[Root Agent] --> RATL[Tool Loader]
        RATL --> GS1
        RATL --> GS2
        RATL --> GS3
        RATL --> GS4
        RATL --> GS5
        RATL --> CT[Core Tools]
    end
    
    subgraph "Sub-Agent Configurations"
        SAC1[.agent/sub-agents/testing_agent.mcp.json] --> DS1[datadog - Exclusive]
        SAC2[.agent/sub-agents/debugging_agent.mcp.json] --> DS2[debugger - Exclusive]
        SAC3[.agent/sub-agents/devops_agent.mcp.json] --> DS3[docker - Exclusive]
    end
    
    subgraph "Sub-Agents"
        TA[Testing Agent] --> TATL[Sub-Agent Tool Loader]
        DA[Debugging Agent] --> DATL[Sub-Agent Tool Loader]
        DEA[DevOps Agent] --> DEATL[Sub-Agent Tool Loader]
        
        TATL --> DS1
        TATL --> GS1
        TATL --> GS2
        TATL --> CT
        
        DATL --> DS2
        DATL --> GS1
        DATL --> CT
        
        DEATL --> DS3
        DEATL --> GS1
        DEATL --> GS3
        DEATL --> CT
    end
    
    style DS1 fill:#ffebee
    style DS2 fill:#e8f5e8
    style DS3 fill:#e3f2fd
    style RA fill:#fff3e0
    style TA fill:#ffebee
    style DA fill:#e8f5e8
    style DEA fill:#e3f2fd
```

### MCP Tool Loading Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant RA as Root Agent
    participant TA as Testing Agent
    participant GM as Global MCP Config
    participant SM as Sub-Agent MCP Config
    participant TL as Tool Loader
    
    Note over U,TL: Root Agent Tool Loading
    U->>RA: Load tools
    RA->>TL: load_all_tools_and_toolsets()
    TL->>GM: Read .agent/mcp.json
    GM-->>TL: Global MCP servers
    TL->>TL: Load core tools
    TL-->>RA: All tools (core + global MCP)
    
    Note over U,TL: Sub-Agent Tool Loading
    U->>TA: Load tools for testing
    TA->>TL: load_tools_for_sub_agent('testing', sub_agent_name='testing_agent')
    TL->>SM: Read .agent/sub-agents/testing_agent.mcp.json
    SM-->>TL: Sub-agent MCP config
    TL->>GM: Check globalServers list
    GM-->>TL: Selected global servers
    TL->>TL: Apply filters and overrides
    TL->>TL: Load exclusive + shared tools
    TL-->>TA: Filtered tools (core + exclusive MCP + selected global MCP)
    
    Note over TA,TL: Security Isolation
    Note right of TL: Testing agent gets datadog (exclusive)<br/>+ filesystem, memory (shared)<br/>Root agent has NO access to datadog
```

### Tool Loading Decision Flow

```mermaid
graph TD
    Start[Agent Requests Tools] --> AgentType{Agent Type?}
    
    AgentType -- Root Agent --> RootFlow[Root Agent Flow]
    AgentType -- Sub-Agent --> SubFlow[Sub-Agent Flow]
    
    subgraph "Root Agent Flow"
        RootFlow --> LoadCore1[Load Core Tools]
        LoadCore1 --> LoadGlobal[Load Global MCP Tools]
        LoadGlobal --> RootResult[Core + Global MCP Tools]
    end
    
    subgraph "Sub-Agent Flow"
        SubFlow --> HasConfig{Sub-Agent Config Exists?}
        HasConfig -- No --> DefaultConfig[Use Default Configuration]
        HasConfig -- Yes --> LoadConfig[Load Sub-Agent Configuration]
        
        DefaultConfig --> LoadCore2[Load Core Tools]
        LoadConfig --> LoadCore2
        
        LoadCore2 --> LoadExclusive[Load Exclusive MCP Tools]
        LoadExclusive --> FilterGlobal{Include Global Servers?}
        
        FilterGlobal -- Yes --> CheckIncludes[Check globalServers List]
        FilterGlobal -- No --> ApplyOverrides[Apply Server Overrides]
        
        CheckIncludes --> CheckExcludes[Check excludedServers List]
        CheckExcludes --> FilteredGlobal[Load Filtered Global MCP Tools]
        FilteredGlobal --> ApplyOverrides
        
        ApplyOverrides --> SubResult[Core + Exclusive MCP + Filtered Global MCP]
    end
    
    RootResult --> End[Return Tools]
    SubResult --> End
    
    style RootResult fill:#fff3e0
    style SubResult fill:#e8f5e8
```

## Codebase Understanding with RAG

A key feature of the DevOps agent is its ability to understand and interact with codebases through Retrieval-Augmented Generation (RAG). This allows the agent to answer detailed questions about your projects.

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

1.  **`index_directory_tool`**: Scans directories, processes supported file types, breaks them into manageable chunks, generates vector embeddings using Google's `text-embedding-004` model, and stores them in a local ChromaDB database.
2.  **`retrieve_code_context_tool`**: Takes natural language queries, converts them to embeddings, and searches the vector database for the most semantically relevant code chunks.
3.  **Contextual Integration**: The retrieved code snippets are automatically injected into the prompt context, giving the LLM the information it needs to answer accurately.

For a practical guide on using this feature, see the [[Usage Guide: Codebase Understanding (RAG)|usage/codebase_understanding_rag]].

## Token Management Architecture

The agent implements sophisticated token counting and management for efficient LLM interactions:

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
        AccurateCount --> Validate[Validate Against Limit]
        TiktokenCount --> Validate
        Validate --> WithinLimit{Within Limit?}
        WithinLimit -- Yes --> SendToLLM[Send to LLM]
        WithinLimit -- No --> Compress[Further Compression]
        Compress --> OptContext
    end
```

## Key Architectural Benefits

This architecture was designed to provide tangible benefits for both developers and platform engineers.

### Performance and Efficiency
- **Token Utilization**: A 244x improvement in token utilization was achieved through smart context management, ensuring that the most relevant information is sent to the LLM in the most compact format.
- **Dynamic Context**: The agent dynamically discovers and expands context, proactively gathering information as needed without user intervention.
- **Robust Execution**: A multi-strategy parsing system for shell commands ensures high reliability and resilience.

### Safety & Reliability
- **Safety-First Design**: Tool execution includes a safety check and requires user approval for a potentially sensitive operation.
- **Advanced Error Handling**: The system includes comprehensive error analysis and automatic retry capabilities for common issues.

### Developer Experience
- **Multiple Interfaces**: Choose between a standard CLI, a powerful Textual TUI, a web interface, or a REST API.
- **Interactive Planning**: For complex tasks, the agent generates a plan and waits for user approval, improving accuracy and collaboration. See the [[Usage Guide: Interactive Planning|usage/interactive_planning]] for more details.
- **Rich Debugging**: Structured logging, distributed tracing, and real-time performance monitoring are built-in.
