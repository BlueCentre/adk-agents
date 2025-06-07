# Feature: Prioritized and Structured Context Management for Agent Loop

## Problem
The current agent loop implementation can suffer from increasing input token counts in the language model prompts as the conversation and tool interactions grow. This is due to the accumulation of conversation history and detailed tool outputs, potentially exceeding the model's context window limits and degrading performance or failing.

## Proposed Solution: Prioritized and Structured Context Management
To address the growing token issue while maintaining high fidelity for both conversation and code understanding, we propose implementing a **Prioritized and Structured Context Management** strategy. This approach involves carefully selecting, organizing, and summarizing information before it is included in the language model's input prompt.

## Why this approach?
This strategy was chosen to provide the language model with the best possible quality context by:

1.  **Preserving Fidelity:** Instead of aggressively truncating or over-summarizing, we retain key information like recent conversation turns and relevant code snippets verbatim, which is crucial for accurate code understanding and natural conversation flow.
2.  **Targeted Information:** By prioritizing and structuring the context, we ensure the model receives the most relevant information needed for the current task and decision-making, avoiding noise from less important details.
3.  **Token Efficiency:** Summarizing verbose outputs and only including necessary code snippets significantly reduces the overall token count compared to including raw, complete history or files.
4.  **Improved Performance:** A focused and relevant context allows the model to perform more effectively within its token limits, leading to higher quality code suggestions and user responses.

## Implementation Plan
Implementing the Prioritized and Structured Context Management will involve modifications primarily within the `devops/agent.py` file and potentially interaction with the underlying `LlmAgent`'s context management:

1.  **Context Structure Definition:** Define distinct categories for context information (e.g., Core Goal, Recent Conversation, Relevant Code, Summarized Tool Results, Key Decisions/State).
2.  **Core Goal and State Tracking:** Implement logic to maintain a concise, continuously updated summary of the main task/goal and the current state/phase of the work. This will be a high-priority, always-included piece of context.
3.  **Recent Conversation Buffer:** Modify the mechanism that builds the conversation history to include only the last N turns verbatim. The value of N will be a configurable parameter.
4.  **Relevant Code Identification and Inclusion:** Develop logic (potentially within or alongside tool handling) to identify code snippets (functions, classes, blocks) that are relevant to the current discussion or task based on user messages and tool interactions (e.g., `read_file`, `edit_file`, `codebase_search`). These snippets will be dynamically included in the context, perhaps with markers indicating their file and line numbers.
5.  **Tool Output Summarization:** Enhance the `handle_after_tool` callback in `devops/agent.py` to generate concise, structured summaries for the outputs of various tools, especially those returning large amounts of data (like `read_file`, `grep_search`, `run_terminal_cmd` stdout/stderr). The full raw output can be stored but not necessarily included in the prompt unless specifically requested or deemed critical.
6.  **Context Assembly Logic:** Create or modify a function responsible for assembling the final prompt for the language model in each turn. This function will gather information from the different structured context categories, prioritize their inclusion based on predefined rules, and ensure the total token count stays within the model's limit. If the limit is approached, older or less critical information will be trimmed or further summarized.
7.  **Integration with `LlmAgent`:** Understand how `LlmAgent` handles message history and context internally. The implementation may involve overriding methods related to prompt construction or history management if the base class provides extension points.

By implementing these steps, the agent will be able to maintain a rich, relevant, and token-efficient context, leading to more accurate code interactions and higher quality responses for the user throughout the conversation. 


---Claude 3.7---
Great! I've implemented a comprehensive solution to address the growing token issue in the agent loop while maintaining high fidelity in code understanding and conversation quality. Here's a summary of what I've created:
1. Core Context Management Module (context_manager.py):
- Implements the prioritized context structure with distinct categories
- Manages conversation turns, code snippets, and tool results
- Provides a method to assemble and optimize the context for each LLM call
2. Tool Result Processing (tool_hooks.py):
- Specialized processors for different tool types (read_file, edit_file, etc.)
- Extracts and stores relevant code snippets from tool results
- Summarizes verbose tool outputs to reduce token usage
3. File Change Tracking (file_tracker.py):
- Keeps track of file modifications throughout the conversation
- Identifies modified functions to prioritize relevant code snippets
- Helps maintain recency and relevance information for context prioritization
4. LLM Request Modification (llm_injection.py):
- Injects the structured context into LLM requests
- Positions context information optimally within the prompt structure
5. Agent Integration (modified agent.py):
- Integrated the context manager into the agent's lifecycle
- Added hooks to process user messages and extract goals
- Modified callback handlers to leverage the context management system

This implementation follows the plan outlined in the feature document, with each component directly addressing one of the key aspects of prioritized and structured context management. The system should now:
1. Maintain high-quality context information about the conversation and codebase
2. Prioritize the most relevant information based on recency and importance
3. Summarize verbose outputs to reduce token usage
4. Manage token growth over time through intelligent context selection

The agent should now be able to maintain longer, more productive conversations without hitting token limits, while preserving the high-quality context needed for accurate code understanding and natural conversation flow.

## New Feature: API Error Handling with Retries and Input Optimization

To enhance the agent's resilience against transient API errors and resource limitations, a retry mechanism with dynamic input optimization has been implemented.

**Problem:** LLM requests can occasionally fail due to API errors such as `429 RESOURCE_EXHAUSTED` (rate limits, quotas) or `500 INTERNAL` errors. These failures interrupt the agent's workflow and can be frustrating for the user.

**Solution:** Implement a retry strategy specifically for these identified API errors. On retry, the agent will attempt to reduce the size and complexity of the input context provided to the LLM, increasing the likelihood of a successful request within resource constraints.

**Implementation Details:**

1.  **Error Interception:** LLM calls within the agent's core execution loop (`_run_async_impl`) are wrapped in a retry mechanism.
2.  **Target Errors:** The retry is specifically triggered by errors containing "429" and "RESOURCE_EXHAUSTED" or "500" and "INTERNAL"/"ServerError".
3.  **Retry Attempts:** Up to 2 retry attempts are made for a failing request.
4.  **Exponential Backoff:** A short exponential backoff (e.g., 1 second initially) is introduced between retries to allow temporary resource issues to resolve.
5.  **Input Optimization (`_optimize_input_for_retry`):** Before each retry, a dedicated method `_optimize_input_for_retry` is called to modify the `InvocationContext` (`ctx.state`) used for the LLM request:
    *   **Retry Attempt 1:** Reduces the number of recent conversation history turns included in the context (e.g., to the last 2 turns) and limits the number of code snippets.
    *   **Retry Attempt 2:** Further reduces history (e.g., to the last 1 turn) and removes code snippets and potentially verbose tool results.
    *   Additionally, the ContextManager's target limits for history and snippets are temporarily adjusted for that retry attempt.
6.  **User Feedback:** If all retry attempts fail for an API error, a specific user-facing message is provided indicating the type of error and the actions taken (retries, context reduction).

**Benefits:**

*   **Increased Robustness:** The agent is less likely to fail due to transient API issues.
*   **Improved User Experience:** Fewer interruptions and the agent attempts to self-recover.
*   **Efficient Resource Usage:** By reducing context on retry, the agent is more likely to succeed within resource limits without requiring user intervention to shorten the prompt.

This feature complements the existing context management strategies by providing a dynamic response to specific API constraints, ensuring the agent can complete tasks even under challenging conditions.