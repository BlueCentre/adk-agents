# Feature: Enhanced Interactive Planning and Refinement for Agent

## 1. Why Implement This Solution?

Implementing "Enhanced Interactive Planning and Refinement" will significantly improve the agent's ability to collaborate on complex coding tasks, leading to higher fidelity and better code quality. The key benefits include:

*   **Improved Fidelity (Accuracy to User Intent):**
    *   **Early Misunderstanding Detection:** By presenting a plan before generating code, the agent can catch misinterpretations of user requirements early in the process. Correcting a plan is far more efficient than refactoring large amounts of incorrect code.
    *   **Shared Understanding:** The planning phase ensures both the user and the agent are aligned on the scope, approach, and expected outcome of a task.
    *   **Reduced Ambiguity:** The process encourages clearer articulation of needs from the user and allows the agent to seek clarification on the plan itself.

*   **Enhanced Code Quality:**
    *   **More Structured and Modular Output:** Thinking in terms of a plan encourages the agent to generate code that is better organized, more modular, and easier to maintain.
    *   **Better Integration with Existing Code:** When the agent considers the existing codebase (using retrieval tools) during planning, the generated code is more likely to integrate smoothly with the existing architecture and patterns.
    *   **Proactive Problem Solving:** The agent can anticipate potential issues or dependencies during the planning phase.

*   **Increased Efficiency and Reduced Rework:**
    *   By getting the approach right upfront, we minimize the need for extensive rework and debugging later in the development cycle.
    *   User's time is respected by focusing agent effort on viable, agreed-upon solutions.

*   **Improved User Experience:**
    *   Users gain more control and visibility into the agent's process.
    *   Collaboration feels more like working with a thoughtful partner rather than just a code generator.

## 2. How to Implement (Step-by-Step)

The implementation will involve modifying the agent's core interaction loop to introduce a planning phase for tasks deemed sufficiently complex or when explicitly requested.

**Phase 1: Core Logic and Feature Flag**

1.  **Introduce a Feature Flag/Configuration:**
    *   Add a configuration setting (e.g., `ENABLE_INTERACTIVE_PLANNING` in a config file or as a session-level toggle) that defaults to `false` initially. This allows for controlled rollout and testing.
    *   The agent's main loop will check this flag before initiating the planning phase.

2.  **Complexity Assessment (Heuristic):**
    *   Develop a simple heuristic to determine if a user's request warrants a planning phase. This could be based on:
        *   Keywords in the request (e.g., "implement feature," "refactor module," "design a new class").
        *   Estimated length or scope of changes.
        *   Explicit user request (e.g., "Plan this for me first").
    *   Initially, this can be a simple trigger, refined over time.

3.  **Planning Prompt Engineering:**
    *   Develop specific prompts for the LLM to generate a plan. These prompts will instruct the LLM to:
        *   Analyze the user's request.
        *   If applicable, consider relevant context retrieved from the codebase (using `retrieve_code_context_tool`).
        *   Outline the steps involved: files to create/modify, functions/classes to define, core logic.
        *   Keep the plan concise and easy to understand.
        *   Phrase the output as a proposal for user review.

4.  **Interaction Flow for Planning:**
    *   **If planning is triggered:**
        *   **Agent:** "Okay, I understand you want to [reiterate request]. Before I generate the code, here's my proposed plan:
            1.  [Step 1]
            2.  [Step 2]
            3.  ...
            Does this look correct? You can approve, suggest changes, or ask for clarification."
        *   **User:** Provides feedback (approve, modify, clarify).
        *   **Agent:**
            *   If approved: "Great! I'll proceed with implementing this plan." -> Move to code generation.
            *   If modifications suggested: "Thanks for the feedback. How about this revised plan: [New Plan]?" -> Iterate until approval.
            *   If clarification asked: Provide details and re-present plan or ask for user input to refine plan.
    *   **If planning is NOT triggered (or disabled):**
        *   Proceed with the existing direct code generation/action flow.

5.  **Integrating Plan into Code Generation:**
    *   Once a plan is approved, the agent uses this plan as a more detailed and structured input for the subsequent code generation phase. The plan acts as a set of sub-tasks.

**Phase 2: Enhancements (Future Iterations)**

1.  **More Sophisticated Complexity Assessment:** Use ML techniques or more detailed request analysis to better decide when planning is most beneficial.
2.  **Visual Plan Representation:** For very complex plans, explore ways to present them more visually (e.g., simple diagrams, flowcharts if feasible via text).
3.  **Saving/Revisiting Plans:** Allow users to save, name, and revisit plans.

## 3. How to Validate the Implementation

Validation will be multi-faceted, focusing on functionality, usability, and impact on output quality.

1.  **Unit/Component Tests:**
    *   Test the feature flag logic: ensure planning is skipped when disabled and triggered when enabled.
    *   Test the interaction flow: simulate user responses (approve, modify, clarify) and verify the agent behaves correctly.
    *   Test prompt outputs for plan generation (qualitative assessment of plan clarity and relevance for predefined scenarios).

2.  **Scenario-Based Testing (Qualitative):**
    *   Define a set of representative coding tasks of varying complexity (e.g., "add a new API endpoint," "refactor a utility function," "implement a small new feature").
    *   **With Feature Disabled:** Execute these tasks and record the interaction, generated code, and any issues.
    *   **With Feature Enabled:** Execute the same tasks.
        *   Assess the quality and relevance of the generated plan.
        *   Evaluate the ease of interaction during the planning phase.
        *   Compare the final generated code (fidelity, structure, correctness) against the non-planning version and the user's original intent.
        *   Measure the time/effort taken by the user to guide the agent.

3.  **User Feedback (Qualitative):**
    *   Engage a small group of internal users (or the primary user) to test the feature.
    *   Collect feedback on:
        *   Clarity of the proposed plans.
        *   Usefulness of the planning step.
        *   Impact on their ability to guide the agent effectively.
        *   Perceived improvement in code quality or fidelity.
        *   Any friction points in the interaction.

4.  **Metrics (Quantitative - Long-term):**
    *   **Task Completion Rate:** Does planning lead to a higher success rate for complex tasks?
    *   **Rework Reduction:** (Harder to measure directly) Can we infer a reduction in back-and-forth or error correction cycles?
    *   **Fidelity Score (Subjective):** For a set of benchmark tasks, score how well the final output matches the original intent, with and without planning.
    *   **Plan Acceptance Rate:** How often are initial plans accepted versus needing multiple revisions? (Indicates quality of initial plan generation).

**Initial Success Criteria (Degree of Certainty):**

*   The feature flag correctly enables/disables the planning flow.
*   For a set of simple-to-moderate test cases, the agent can generate a coherent plan.
*   The user can successfully approve or suggest modifications to the plan, and the agent responds appropriately.
*   For at least 2-3 test scenarios, qualitative assessment shows that using the planning feature leads to a final code output that is either:
    *   More aligned with the intended solution than without planning, OR
    *   Achieved with less corrective effort from the user.

This iterative approach to validation will allow us to build confidence in the feature and refine it based on empirical evidence and user feedback.


---Gemini 2.5 Pro---
🤖 devops_agent >
I have now applied the extensive changes for Step 4: Interaction Flow for Planning to Agents/devops/agent.py.

Key modifications include:

 • Added _pending_plan_text and _is_awaiting_plan_approval as PrivateAttr to MyDevopsAgent.
 • In handle_before_model:
    • Logic to check if awaiting plan approval. If user types "approve", the plan is stored in the ContextManager as a system message, and states are reset for normal execution. If other feedback, a message is sent, and planning state is reset.
    • If the planning heuristic is met (and not awaiting approval):
       • The llm_request.contents is replaced with the formatted PLANNING_PROMPT_TEMPLATE.
       • Tools are disabled for this planning LLM call.
       • callback_context.custom_data["is_plan_generation_turn_for_after_model"] is set to True.
       • Status indicator is set to "Agent is drafting a plan...".
       • Normal context processing/injection is skipped for this planning turn.
 • In handle_after_model:
    • If is_plan_generation_turn_for_after_model is true:
       • The LLM's response (the plan) is extracted.
       • _pending_plan_text is set, _is_awaiting_plan_approval is set to True.
       • An LlmResponse is constructed and returned, presenting the plan to the user and asking for approval.
       • The "drafting plan" status indicator is stopped.
    • Normal handle_after_model logic (token logging, context manager update) only runs if it wasn't an intercepted plan generation turn.
 • In _run_async_impl: Added resetting of _pending_plan_text and _is_awaiting_plan_approval when a new conversation starts.
 • Updated _extract_response_text to be a bit more robust in finding text parts.
 • Adjusted status indicator logic throughout to better reflect planning states.

This completes the initial implementation of Phase 1, Step 4.

The next logical step is Phase 1, Step 5: Integrating Plan into Code Generation. This involves ensuring that when a plan is approved:

 1 The approved plan (which is now added as a system message to the ContextManager by handle_before_model upon approval) is effectively used by the main LLM call for code generation.
 2 The main agent instruction (prompt.DEVOPS_AGENT_INSTR) might need to be aware or be slightly adjusted if the presence of an "approved plan" in the context should change how it interprets its task.

For Step 5, the main work has already been partially done: the approved plan is injected into the ContextManager with a clear instruction: "The user has approved the following plan. Proceed with implementation based on this plan: ...".

The ContextManager.assemble_context() method should naturally pick this up as part of the conversation history/system messages it provides to the LLM. The inject_structured_context function then places this assembled context into the llm_request.

Therefore, the primary mechanism for Step 5 is already in place. The main DEVOPS_AGENT_INSTR is general enough that it should be able to follow the more specific instruction provided by the "approved plan" system message.

What's left for Phase 1:

 • Testing and Refinement (Implicit throughout, but especially now):
    • We need to test this entire flow:
       1 User makes a request that triggers planning (e.g., "implement a new feature to...")
       2 Agent proposes a plan.
       3 User types "approve".
       4 Agent proceeds to (attempt to) implement the plan.
    • We also need to test the feedback loop (user provides feedback instead of "approve").
    • Check log messages for clarity.
    • Verify status indicators behave as expected.
 • Minor prompt adjustments if needed: After testing, we might find that DEVOPS_AGENT_INSTR or the system message for the approved plan needs slight tweaks for better LLM adherence.

Validation (from our original document): We should now focus on the "Initial Success Criteria" we defined:

 • The feature flag correctly enables/disables the planning flow. (We can test this by setting ENABLE_INTERACTIVE_PLANNING to false in .env).
 • For simple-to-moderate test cases, the agent can generate a coherent plan.
 • The user can successfully approve or suggest modifications to the plan, and the agent responds appropriately.
 • For at least 2-3 test scenarios, qualitative assessment shows that using the planning feature leads to a final code output that is either more aligned with the intended solution or achieved with less corrective effort.

At this point, we've implemented the core mechanics of Phase 1. The next actions would be to run the agent and test these scenarios.

Do you want to proceed with defining some test scenarios, or is there any part of the implementation you'd like to review or discuss further before testing?
