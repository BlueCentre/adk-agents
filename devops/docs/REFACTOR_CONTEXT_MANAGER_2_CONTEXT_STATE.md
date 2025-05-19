# Refactoring `devops/devops_agent.py` to Leverage `context.state`

This document outlines the refactoring process undertaken in `devops/devops_agent.py` to align with the ADK best practice of using `context.state` for managing conversational memory and data flow.

## Summary of Changes

The primary goal of this refactoring was to replace the custom `_context_manager` class with the built-in `context.state` provided by the ADK framework. This involves storing conversation history, tool calls, tool results, and other relevant context information directly within the state object accessible via `InvocationContext`, `CallbackContext`, and `ToolContext`.

Key changes include:

1.  **Removal of `_context_manager`:** The instance and related logic of the custom context manager were removed from the `MyDevopsAgent` class.
2.  **Migration to `context.state`:** All logic for storing and retrieving conversation turns, tool calls, and tool results was moved to use `context.state`.
3.  **State Structure Definition:** A structure was defined within `context.state` to organize the data.
4.  **State Initialization and Cleanup:** Logic was added to initialize state for new conversations and clear temporary state for each invocation.
5.  **Integration of Tool Data:** Tool calls and results from a turn are now integrated into the main conversation history stored in state.
6.  **Placeholder Context Assembly:** Placeholder methods were introduced for assembling the context from state for LLM prompts and estimating token counts.

## Decisions and Code Details

### State Key Naming Convention

Following ADK recommendations, we used prefixes for state keys:

*   `user:`: For data that should persist across invocations within the same user session (e.g., conversation history).
*   `temp:`: For temporary data relevant only to the current invocation or turn (e.g., tool calls/results within a turn, flags like `is_new_conversation`).
*   `app:`: For application-level data (e.g., stored code snippets).

### Storing Conversation History (`user:conversation_history`)

The conversation history is stored as a list of dictionaries under the key `user:conversation_history`. Each dictionary represents a turn and can contain:

*   `user_message` (string): The user's message for that turn.
*   `agent_message` (string): The agent's response for that turn.
*   `system_message` (string): System messages, like the approved plan.
*   `tool_calls` (list of dicts): Tool calls made during the turn.
*   `tool_results` (list of dicts): Results from tool calls during the turn.

Example Structure:

```json
{
  "user:conversation_history": [
    {
      "user_message": "How do I list files?"
    },
    {
      "agent_message": "I can list files for you.",
      "tool_calls": [
        {
          "tool_name": "list_dir",
          "args": {"relative_workspace_path": "."}
        }
      ],
      "tool_results": [
        {
          "tool_name": "list_dir",
          "response": {"files": ["file1.txt", "file2.py"]}
        }
      ]
    },
    {
        "user_message": "Great, what about file2.py?"
    }
    // ... more turns
  ]
  // ... other state keys
}
```

Code Snippets for Conversation History Management:

In `handle_before_model`, logic was added to append new user messages to `user:conversation_history`:

```python
        conversation_history = callback_context.state.get('user:conversation_history', [])
        current_turn = callback_context.state.get('temp:current_turn', {})

        if user_message_content:
             # Check if the last turn in history is complete or if this is the first message of a new turn
             if not conversation_history or conversation_history[-1].get('agent_message') is not None:
                  logger.debug(f"Starting new turn in context.state with user message: {user_message_content[:100]}")
                  current_turn = {'user_message': user_message_content}
                  conversation_history.append(current_turn)
             # If the last turn exists but has no user message yet (e.g., previous tool output only), update it.
             elif conversation_history[-1].get('user_message') is None:
                  logger.debug(f"Updating current turn in context.state with user message: {user_message_content[:100]}")
                  conversation_history[-1]['user_message'] = user_message_content
                  current_turn = conversation_history[-1] # Ensure current_turn points to the updated entry
             else:
                  # Appending to the last user message
                   logger.debug(f"Appending to last user message in context.state: {user_message_content[:100]}")
                   last_user_msg = conversation_history[-1].get('user_message', '')
                   conversation_history[-1]['user_message'] = last_user_msg + "\n" + user_message_content
                   current_turn = conversation_history[-1]

        callback_context.state['user:conversation_history'] = conversation_history
        callback_context.state['temp:current_turn'] = current_turn # Store current turn state
```

In `handle_after_model`, the agent's response is added to the last turn:

```python
                conversation_history = callback_context.state.get('user:conversation_history', [])
                if conversation_history:
                    # Assuming the last turn is the current one to update
                    last_turn = conversation_history[-1]
                    if last_turn.get('agent_message') is None: # Only update if agent hasn't responded in this turn yet
                        last_turn['agent_message'] = extracted_text
                        callback_context.state['user:conversation_history'] = conversation_history
                    else:
                         last_turn['agent_message'] += "\n" + extracted_text
                         callback_context.state['user:conversation_history'] = conversation_history
                    logger.debug(f"Updated agent response in context.state for last turn: {extracted_text[:100]}")
```

### Storing Tool Calls and Results (`temp:tool_calls_current_turn`, `temp:tool_results_current_turn`)

Tool calls and their results are temporarily stored for the current turn under `temp:tool_calls_current_turn` and `temp:tool_results_current_turn` as lists of dictionaries.

Code Snippets for Tool Data Management:

In `handle_before_tool`, a tool call is added to the temporary list:

```python
            if tool_context is not None:
                tool_calls = tool_context.state.get('temp:tool_calls_current_turn', [])
                tool_calls.append({'tool_name': tool.name, 'args': args})
                tool_context.state['temp:tool_calls_current_turn'] = tool_calls
```

In `handle_after_tool`, a tool result is added to the temporary list:

```python
            if tool_context is not None:
                tool_results = tool_context.state.get('temp:tool_results_current_turn', [])
                tool_results.append({'tool_name': tool.name, 'response': tool_response})
                tool_context.state['temp:tool_results_current_turn'] = tool_results
```

After the main `_run_async_impl` loop, these temporary tool calls and results are moved into the `user:conversation_history` for persistence:

```python
            current_turn_tool_calls = ctx.state.pop('temp:tool_calls_current_turn', [])
            current_turn_tool_results = ctx.state.pop('temp:tool_results_current_turn', [])
            current_turn_data = ctx.state.pop('temp:current_turn', {})

            conversation_history = ctx.state.get('user:conversation_history', [])
            if conversation_history:
                last_turn = conversation_history[-1]
                if current_turn_tool_calls:
                    last_turn['tool_calls'] = last_turn.get('tool_calls', []) + current_turn_tool_calls
                if current_turn_tool_results:
                    last_turn['tool_results'] = last_turn.get('tool_results', []) + current_turn_tool_results
                last_turn.update({k: v for k, v in current_turn_data.items() if k not in ['user_message', 'agent_message', 'tool_calls', 'tool_results']})
                ctx.state['user:conversation_history'] = conversation_history
```

### Managing New Conversations (`temp:is_new_conversation`)

A temporary flag `temp:is_new_conversation` is used to track if the current invocation is the start of a new conversation. This is initialized to `True` by default and set to `False` after the first invocation in `_run_async_impl`.

Code Snippets:

Checking the flag at the start of `_run_async_impl`:

```python
            is_new_conversation = ctx.state.get('temp:is_new_conversation', True)

            if is_new_conversation:
                logger.info(f"Agent {self.name}: New conversation detected (based on context.state), resetting planning state.")
                # ... initialization logic ...
                ctx.state['temp:is_new_conversation'] = False
```

### Placeholder Context Assembly and Token Counting

Placeholder methods `_assemble_context_from_state`, `_count_tokens`, and `_count_context_tokens` were added. `_assemble_context_from_state` demonstrates how to retrieve data from state (history, code snippets) to build a context dictionary. The token counting methods are simple estimates and need to be replaced.

Code Snippets:

Structure of `_assemble_context_from_state`:

```python
    def _assemble_context_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder: Assembles context dictionary from state for LLM injection."""
        context_dict = {}

        # Include recent conversation history, formatted for the LLM
        history = state.get('user:conversation_history', [])
        # Limit history by number of turns (needs token logic for proper limit)
        recent_history = history[-agent_config.CONTEXT_TARGET_RECENT_TURNS:]

        formatted_history = []
        for turn in recent_history:
            # ... formatting logic for user, agent, system, tool_code, tool_result messages ...
            pass # Placeholder

        context_dict['conversation_history'] = formatted_history

        # Include code snippets (if stored in state)
        code_snippets = state.get('app:code_snippets', [])
        # Limit code snippets by number (needs token logic)
        context_dict['code_snippets'] = code_snippets[-agent_config.TARGET_CODE_SNIPPETS:]

        # TODO: Implement token limit management here.
        # You need to iteratively add components and check token count.

        return context_dict
```

Placeholder token counting methods:

```python
    def _count_tokens(self, text: str) -> int:
        """Placeholder: Counts tokens for a given text using the LLM client."""
        # TODO: Replace with actual token counting logic using self.llm_client.
        logger.warning("Using placeholder token counting. Replace with actual LLM client token counter.")
        return len(text) // 4 # Rough estimate

    def _count_context_tokens(self, context_dict: Dict[str, Any]) -> int:
        """Placeholder: Counts tokens for the assembled context dictionary."""
        # TODO: Replace with actual token counting logic using self.llm_client.
        logger.warning("Using placeholder context token counting. Replace with actual LLM client token counter.")
        return len(json.dumps(context_dict)) // 4 # Rough estimate
```

## What is Left to Do (DONE)

This refactoring provides the foundation for using `context.state`, but the following crucial steps need to be completed:

1.  **Implement Actual Token Counting:** Replace the placeholder logic in `_count_tokens` and `_count_context_tokens` with calls to your specific LLM client's tokenization method (e.g., `self.llm_client.count_tokens`). Accurate token counting is essential for effective context management.
2.  **Implement Robust Token Limit Management:** Enhance the `_assemble_context_from_state` method to respect the `self._actual_llm_token_limit`. This involves prioritizing and potentially truncating context elements (like conversation history or code snippets) based on their token cost to ensure the total context size stays within the model's limit.
3.  **Refine Context Formatting for LLM:** Adjust the formatting of the `conversation_history`, `tool_calls`, `tool_results`, and `code_snippets` within `_assemble_context_from_state` to match the specific input format expected by the LLM you are using. This might involve different message roles or structures.
4.  **Update Custom Tool Processors:** Modify any custom tool processing functions in `TOOL_PROCESSORS` to accept and interact with the `context.state` object (or relevant parts of it) instead of the old `_context_manager`.
5.  **Implement Artifact Management (if needed):** If your original context manager handled file artifacts, integrate the use of `context.save_artifact` and `context.load_artifact`. Store references to these artifacts (paths or URIs) in `context.state` under an appropriate key (e.g., `app:artifacts`).
6.  **Review and Refine Turn Management:** The current turn management logic assumes a relatively simple turn structure. Review if this is sufficient for your agent's needs or if more complex state transitions or turn tracking are required.

Completing these steps will ensure that your agent fully leverages the capabilities of `context.state` for state management and context assembly in an efficient and ADK- idiomatic way. 