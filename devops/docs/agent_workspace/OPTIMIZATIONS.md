# Prompt Optimization Analysis and Recommendations

This document outlines the analysis of the agent's prompt construction and context management, along with recommendations for further optimization.

## Implementation Status Update (Based on Real Log Analysis)

### ✅ Section 4: Comprehensive Logging - IMPLEMENTED
**Status**: Complete and operational
**Files Modified**: 
- `devops/components/context_management/context_manager.py`
- `devops/devops_agent.py`  
- `OPTIMIZATION_LOGGING_SUMMARY.md` (documentation)

**Real Usage Analysis**: Log analysis from `/var/folders/cr/4ch4t4hd0nd1t8tk23km89h80000gn/T/agents_log/agent.latest.log` revealed:
- Available tokens: 1,048,497 / 1,048,576 (99.99% available)
- Actual usage: 30-206 tokens (0.01-0.02% utilization) 
- Most context components: "SKIPPED: None available"
- **Key insight**: Context **population gaps**, not optimization needs

### 🔄 STRATEGY REVISION: Context Population Priority

Based on real data analysis, **original Sections 1-3 recommendations were DEPRIORITIZED** as premature optimization for non-existent problems.

**New Priority**: **CONTEXT POPULATION & UTILIZATION** (see `REVISED_STRATEGY_IMPLEMENTATION.md`)

#### ✅ Phase 1: IMPLEMENTED (December 2024)
**Priority**: IMMEDIATE - Address actual bottleneck

1. **Increased Context Targets** (5x-6x increases)
   - Conversation turns: 5 → 20
   - Code snippets: 5 → 25  
   - Tool results: 5 → 30
   - Storage limits: 20-30 → 100-150

2. **Reduced Aggressive Summarization** (3x-4x increases)
   - Summary lengths: 500 → 2000 chars
   - File previews: 150 → 500 chars
   - Content limits: 100-200 → 300-800 chars

3. **Enhanced Tool Processing**
   - Full file chunking for better context
   - Before/after edit tracking
   - Proactive snippet generation
   - Enhanced function modification detection

4. **Agent-Level Improvements**
   - Real-time utilization monitoring
   - Low-utilization warnings
   - Enhanced context synchronization
   - Comprehensive state diagnostics

**Expected Impact**: 20-30% token utilization vs current <1%

#### 🔮 Phase 2: FUTURE (After Phase 1 validation)
**Priority**: SHORT-TERM - Once context population is proven

1. **Proactive Context Addition**
   - Include project files proactively  
   - Add Git history for context
   - Include documentation snippets

2. **Dynamic Context Expansion**
   - File tree exploration
   - Dependency analysis
   - Error pattern recognition

#### 📋 Phase 3: THEORETICAL (Only if high utilization achieved)
**Priority**: LONG-TERM - Original optimization recommendations

Implementation of original Sections 1-3 recommendations, **only after** achieving consistent high context utilization:

## Original Recommendations (Now Phase 3)

### Section 1: Current Optimizations Analysis
**Status**: ✅ CONFIRMED WORKING - No immediate changes needed
**Files**: `devops/components/context_management/context_manager.py`
**Assessment**: Token counting, context assembly, and component management are working correctly. The issue was not optimization but **context population**.

### Section 2: Further Improvements  
**Status**: 📋 DEFERRED - Premature optimization
**Original recommendations now considered lower priority**:

1. **Dynamic Summarization** - Not needed with <1% utilization
2. **Tiered Context Management** - Unnecessary with massive available capacity  
3. **Tool Output Condensation** - Counterproductive when we need MORE context
4. **Conversation Compression** - Not relevant with current usage patterns
5. **Smart Context Switching** - Premature until we utilize available capacity

### Section 3: Text Format Optimizations
**Status**: 📋 LOWEST PRIORITY - Negligible impact
**Assessment**: JSON overhead is negligible when using <1% of 1M+ token capacity

**Original recommendations**:
1. Structured text over JSON - Minimal benefit at current usage
2. Abbreviated keys - Unnecessary optimization  
3. Compression techniques - Not needed with current capacity
4. Contextual abbreviations - Lower priority

## Summary of Strategic Pivot

**Before**: Focus on theoretical efficiency optimizations
**After**: Focus on practical context enrichment and utilization

**Rationale**: Real log data showed the system was dramatically **under-utilizing** available capacity due to context integration gaps, not over-utilizing due to inefficiency.

**Validation**: Enhanced logging will continue monitoring utilization improvements from Phase 1 implementations.

For detailed implementation specifics, see `REVISED_STRATEGY_IMPLEMENTATION.md`.

## 1. Evidence of Current ContextManager Optimizations

Based on the provided logs (`agent.latest.log`), there is evidence that the `ContextManager` is performing some level of prompt optimization:

*   **Token Counting and Budgeting:**
    *   Log entries such as `INFO - context_manager.py:466 - Assembled context with X tokens for context block. Available budget was Y. Keys: [list of keys]` and `INFO - devops_agent.py:269 - Total tokens for prompt (base + context_block): Z` clearly indicate that the system is aware of token limits and is actively managing the size of the context block to fit within an available budget.
*   **Selective Key Inclusion:**
    *   The `Keys: ['recent_conversation']` part of the `ContextManager` log suggests that it doesn't just include all possible context but selects specific parts. In the observed instances, it prioritizes recent conversation history.
*   **New Conversation Detection:**
    *   The log line `INFO - devops_agent.py:206 - Agent devops_agent: New conversation detected (based on context.state), initializing state.` shows that the agent can differentiate between new and ongoing conversations. This is an optimization as it prevents irrelevant past history from polluting the context of a new interaction.

**Areas for Deeper Insight (Not Fully Evident from Current Logs):**

*   **Specific Optimization Strategies:** While size management is evident, the exact methods used (e.g., simple truncation of older turns, summarization of tool outputs or conversation history) are not detailed in the current logs.
*   **Prioritization Logic:** If various context elements (e.g., multiple tool outputs, older messages) compete for limited token space, the rules governing which information is prioritized are not explicitly logged.

## 2. Potential Further Improvements for Prompt Optimization

Several strategies could be implemented to further optimize input prompts while maintaining high-fidelity context:

*   **Dynamic Summarization:**
    *   For lengthy conversation turns or verbose tool outputs, employ a secondary, possibly smaller LLM to generate concise summaries. This would preserve essential information while reducing token count.
*   **Tiered Context Management:**
    *   Implement a strategy where the most recent 1-2 turns are kept in full detail.
    *   Summarize turns 3-5.
    *   For older turns, retain only a list of key topics or entities.
*   **Advanced Contextual Relevance Filtering:**
    *   Utilize embedding-based similarity: Embed the current user query and compare its vector similarity against embeddings of past conversation turns and tool outputs. This would allow the system to dynamically include only the most semantically relevant historical context, leading to more focused and efficient prompts.
*   **Tool Output Condensation/Summarization:**
    *   Tools returning large outputs (e.g., `browser_snapshot` YAML, full file contents) should have a built-in or `ContextManager`-triggered step to condense or summarize their output before it's added to the prompt context. For instance, instead of a full browser snapshot, extract key interactive elements or a textual summary of the page content.
*   **Knowledge Graph Integration for Context Enrichment:**
    *   When the conversation references entities or concepts present in the knowledge graph, the `ContextManager` could fetch concise, relevant facts from the KG. This can provide rich, factual context more efficiently than relying solely on conversational recall.
*   **User-Defined Context Importance:**
    *   Consider allowing a mechanism for users (or the agent itself based on strong signals) to mark specific past interactions or pieces of information as "critical" or "sticky" to ensure they are prioritized in the context if token limits allow.
*   **Instructional Compression for the Model:**
    *   Experiment with system prompt instructions that guide the model on how to best interpret and utilize the provided context, potentially encouraging it to be more concise in its internal reasoning if that contributes to token usage in multi-turn scenarios.

## 3. Optimal Text Formats for Model Input

The current format uses a JSON structure for conversation history and tool interactions, which is generally robust and well-handled by models, especially for structured data like function calls.

*   **JSON (Current):**
    *   **Pros:** Structured, machine-readable, good for complex data (roles, function calls/responses). Models are often trained on this format.
    *   **Cons:** Can be verbose due to structural characters (`{}`, `[]`, `""`, `,`).
*   **Potential Alternatives/Refinements:**
    *   **Markdown:**
        *   **Pros:** Can be more token-efficient for simple text exchanges due to less structural overhead. Widely understood by LLMs.
        *   **Cons:** Might be less ideal for deeply nested or highly structured data compared to JSON.
        *   *Example:*
            ```markdown
            [SYSTEM]
            Your instructions...
            [USER]
            User's message.
            [MODEL]
            Model's response.
            [TOOL_CALL]
            tool_name(arg1="value1")
            [TOOL_RESPONSE]
            tool_name -> {"status": "success", "output": "..."}
            ```
    *   **Custom Delimiters/Minimalist Formats:**
        *   **Pros:** Potentially the most token-efficient for pure text.
        *   **Cons:** Less standard, might require more careful parsing by the model, and could be brittle for complex interactions.
    *   **Conciseness within JSON:** Ensure field names are short but descriptive, and avoid unnecessary nesting. The current JSON structure appears reasonable in this regard.

**Recommendation:** The most significant token savings usually come from *what* content is included and *how it's summarized or filtered*, rather than minor changes to the top-level wrapper format (JSON, Markdown), assuming the format is standard. However, for very long conversations, even small per-turn savings from a more compact format like Markdown could add up. A hybrid approach might also be viable (e.g., JSON for tool calls, Markdown for conversation).

## 4. Additional Logs for Deeper Analysis ✅ IMPLEMENTED

The following comprehensive logging has been implemented for optimization analysis:

### ✅ **`ContextManager` - Detailed Inputs**
- **Location**: `devops/components/context_management/context_manager.py` - `_log_detailed_inputs()` method
- **Implementation**: Logs the full `context.state` including conversation history, code snippets, tool results, and context state details
- **Trigger**: Called at the beginning of every context assembly process
- **Content**: 
  - Complete conversation history with token counts and content previews
  - All available code snippets with relevance scores and file locations
  - Tool results with summaries and full result type information
  - Context state including core goal, current phase, key decisions, and modified files

### ✅ **`ContextManager` - Decision-Making Logic**
- **Location**: `devops/components/context_management/context_manager.py` - `assemble_context()` method
- **Implementation**: Comprehensive logging of which context pieces are included/excluded and why
- **Content**:
  - ✅ INCLUDED items with token counts and reasons
  - ❌ EXCLUDED items with token counts and specific reasons (budget exceeded, target limits, etc.)
  - ⚠️ SKIPPED items when not available
  - 📊 Summary statistics for each component type

### ✅ **`ContextManager` - Transformations**
- **Location**: `devops/components/context_management/context_manager.py` - `_generate_tool_result_summary()` method
- **Implementation**: Logs content before and after transformation for tool result summarization
- **Content**:
  - Original content size and type
  - Transformation type applied (truncation, summarization, key extraction)
  - Final summary size and transformation ratio
  - Detailed breakdown of what was kept vs. discarded

### ✅ **Token Counts per Prompt Component**
- **Location**: `devops/devops_agent.py` - `_log_final_prompt_analysis()` method
- **Implementation**: Detailed token breakdown for every component of the final prompt
- **Content**:
  - Individual message token counts with role identification
  - System context block with per-component token analysis
  - Tools definition tokens (total and per-tool)
  - System instruction tokens
  - Function call tokens
  - Token utilization percentage and remaining capacity

### ✅ **Final Assembled Prompt String**
- **Location**: `devops/devops_agent.py` - `_log_final_prompt_analysis()` method
- **Implementation**: Complete raw prompt reconstruction for exact inspection
- **Usage**: Set environment variable `LOG_FULL_PROMPTS=true` to enable
- **Content**: Full prompt string exactly as sent to the LLM

### ✅ **Loaded `ContextManager` Configurations**
- **Location**: `devops/components/context_management/context_manager.py` - `_log_configuration()` method
- **Implementation**: Logs all configuration values at ContextManager initialization
- **Content**:
  - Model name and token limits
  - Target counts for different context types
  - Storage limits for code snippets and tool results
  - LLM client type and token counting strategy

## Usage Instructions

### Standard Logging
All logging except the raw prompt is enabled by default and will appear in the agent logs during operation.

### Raw Prompt Logging
To enable complete prompt logging (can be verbose):
```bash
export LOG_FULL_PROMPTS=true
```

### Log Analysis
The logs provide comprehensive data for:
1. **Context Budget Analysis**: Understanding how token budget is allocated
2. **Component Performance**: Identifying which components consume the most tokens
3. **Decision Tracking**: Seeing why specific context is included or excluded
4. **Transformation Impact**: Understanding how content is summarized or truncated
5. **Prompt Composition**: Analyzing the final prompt structure and token distribution

### Example Log Sections
- `CONTEXTMANAGER CONFIGURATION LOADED` - Startup configuration
- `CONTEXTMANAGER DETAILED INPUT STATE` - Available data before processing
- `CONTEXT ASSEMBLY - TOKEN BUDGET ANALYSIS` - Budget allocation and decision-making
- `CONTEXT ASSEMBLY - FINAL SUMMARY` - Token utilization summary
- `TOOL RESULT TRANSFORMATION` - Content transformation details
- `FINAL ASSEMBLED PROMPT ANALYSIS` - Complete prompt breakdown
- `RAW FINAL PROMPT STRING` - Exact prompt content (if enabled)
