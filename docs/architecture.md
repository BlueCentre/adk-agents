---
layout: default
title: Architecture
nav_order: 2
description: "Technical architecture and design of the DevOps Agent system."
mermaid: true
---

# Architecture Overview

The DevOps Agent implements a sophisticated multi-layered architecture that integrates with the Google ADK framework while providing advanced capabilities through custom components.

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

## Agent Request Processing Lifecycle

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

A key feature of the DevOps agent is its ability to understand and interact with codebases through Retrieval-Augmented Generation:

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

1. **`index_directory_tool`**: Scans directories, processes supported file types, breaks them into manageable chunks, generates vector embeddings, and stores them in ChromaDB
2. **`retrieve_code_context_tool`**: Takes natural language queries, converts them to embeddings, and searches the vector database for relevant code chunks
3. **Semantic Search**: Uses Google embeddings for high-quality semantic understanding of code structure and relationships

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

### Performance Optimizations
- **244x improvement** in token utilization through smart context management
- **Dynamic context expansion** for relevant information discovery
- **Multi-strategy parsing** for robust command execution

### Safety & Reliability
- **Safety-first tool execution** with user approval workflows
- **Comprehensive error handling** with automatic retry capabilities
- **Multi-layered validation** for command parsing and execution

### Scalability
- **Serverless deployment** options with Google Cloud Run
- **Managed infrastructure** with Agent Engine
- **Container-native** design for flexible deployment

### Developer Experience
- **Multiple interface options** (CLI, TUI, Web, API)
- **Session management** for continuous workflows
- **Real-time monitoring** and token tracking
- **Rich debugging** and tracing capabilities 