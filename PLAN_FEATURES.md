# PLAN_FEATURES.md - Enhanced Agentic CLI Tool Feature Development Plan

## Introduction

This document outlines a detailed development plan for integrating new, highly requested features into our agentic CLI tool. The goal is to significantly enhance the developer and user experience by making the tool more intelligent, proactive, and collaborative.

The plan is structured into features, each containing multiple milestones. Every milestone is designed to be independently testable and verifiable, ensuring a clear path for development and quality assurance. This document is intended to be accessible for junior developers, providing clear tasks and guidelines.

## General Implementation Guidelines

To ensure consistency, quality, and maintainability, all development efforts will adhere to the following guidelines:

### 1. ADK Best Practices

*   **Agent Design:** Adhere to the principles of modularity, single responsibility, and clear communication channels between agents.
*   **Tool Usage:** Utilize existing ADK tools efficiently and create new, atomic tools when necessary, following the established tool definition patterns.
*   **State Management:** Leverage `state_manager_tool` for sharing data between agents, ensuring data consistency and clear state transitions within workflows.
*   **Workflow Orchestration:** Utilize `workflow_selector_tool` to dynamically choose appropriate `SequentialAgent`, `ParallelAgent`, and `LoopAgent` patterns based on task characteristics.
*   **Error Handling:** Implement robust error handling and logging for all new components and modify existing ones as needed to prevent failures and provide informative feedback.

### 2. Testing Strategy

*   **Unit Tests:** Develop comprehensive unit tests for all new functions, classes, and components. Aim for high code coverage.
*   **Integration Tests:** Create integration tests for each milestone to verify the interaction between different components and agents. These tests should simulate end-user scenarios as much as possible.
*   **Regression Tests:** Ensure all existing tests (unit and integration) pass after implementing new features. Continuous integration will be used to enforce this.
*   **Test-Driven Development (TDD):** Where applicable, consider writing tests before writing the code to guide development.

### 3. Code Quality & Standards

*   **Linter & Code Style:** Adhere strictly to the project's defined code style guidelines (e.g., PEP 8 for Python). All code must pass linters (e.g., `uv run ruff check . --fix`, `uv run ruff format .`) without warnings or errors.
*   **Readability:** Write clean, self-documenting code with clear variable names, concise functions, and appropriate comments for complex logic.
*   **Performance:** Optimize code for performance where necessary, especially for operations involving file I/O or large data processing.

### 4. Documentation

*   **Inline Comments:** Use comments to explain non-obvious code sections.
*   **Docstrings:** Provide clear and concise docstrings for all functions, classes, and modules, describing their purpose, arguments, and return values.
*   **User Documentation:** Update `README.md` and other user-facing documentation to reflect new features and how to use them.
*   **Design Diagrams:** For new complex features or modifications to existing workflows, include design diagrams (e.g., sequence diagrams, architectural diagrams) to illustrate the flow and interaction of components. Utilize Mermaid syntax for consistency with existing documentation. Update any existing diagrams affected by the changes.

### 5. Version Control Best Practices

*   **Feature Branches:** All development for a new feature or milestone will be done on a dedicated feature branch.
*   **Atomic Commits:** Make small, focused commits with clear and descriptive commit messages.
*   **Code Reviews:** All pull requests will undergo code review by at least one other developer before merging into the main branch.

### 6. Milestone Completion & Verification

*   No milestone will be started until all prior milestones and their tasks are FULLY completed, pass all linters, and pass all existing and new tests.
*   Each milestone includes specific "User Verification Steps" that an end-user (or QA) can follow to confirm the successful implementation of the feature.

### 7. Security Considerations

*   **Input Validation:** Sanitize and validate all user inputs and external data to prevent injection attacks (e.g., prompt injection, shell command injection).
*   **Least Privilege:** Ensure the agent and its tools operate with the minimum necessary permissions.
*   **Sensitive Data Handling:** Define clear policies for handling sensitive information (e.g., API keys, user credentials) to prevent logging or exposure.
*   **Secure Defaults:** Prioritize secure configurations and behaviors by default, requiring explicit opt-in for less secure options.

---

## Feature 1: Enhanced Natural Language Interaction with Deeper Contextual Grounding

**Goal:** Transform the agent's understanding from basic command translation to a profound awareness of the developer's working context, enabling more intelligent and relevant responses.

### Milestone 1.1: Basic Contextual Awareness (File System & Open Files)

**Objective:** Enable the agent to understand the current directory, list files, and read content from specified files as implicit context.

**Tasks:**

*   - [x] **Task 1.1.1: Enhance Agent's Internal State for Current Directory:** ✅ **COMPLETED**
    *   Modify the `enhanced_software_engineer` agent's state management to persistently store and update the "current working directory" within `session.state`.
    *   **Implementation Note:** Utilize `state_manager_tool` with `action='set'` for `current_directory` key.
    *   **✅ Implementation:** Added `_update_current_directory()` and `_get_current_directory()` methods to both enhanced and base agents.
*   - [x] **Task 1.1.2: Implement Contextual File Listing:** ✅ **COMPLETED**
    *   When a user asks a question, if a directory is mentioned (e.g., "What's in the `src` folder?"), use `list_directory` (or `list_directory_contents`) implicitly on the relevant directory.
    *   **Implementation Note:** Develop a pre-processing step for user queries to identify potential directory references. This could involve keyword matching, regular expressions, or leveraging the LLM for entity extraction within the user's natural language query.
    *   **✅ Implementation:** Added `_preprocess_user_query()` method with sophisticated regex patterns to identify directory references and automatically trigger directory listing.
*   - [x] **Task 1.1.3: Implement Contextual File Reading:** ✅ **COMPLETED**
    *   If a user asks about a specific file's content (e.g., "Show me `main.py`"), implicitly use `read_file` (or `read_file_content`) to fetch and present the file's content.
    *   **Implementation Note:** Similar pre-processing to identify file names. Prioritize searching in the `current_directory`.
    *   **✅ Implementation:** Extended query preprocessing to identify file name references and automatically read file content with proper fallback mechanisms.
*   - [x] **Task 1.1.4: Integration Tests:** ✅ **COMPLETED**
    *   Write integration tests that simulate user queries involving listing directories and reading files, verifying the agent correctly uses the tools without explicit commands.
    *   Ensure existing `list_directory`, `read_file` tests still pass.
    *   **✅ Implementation:** Created comprehensive test suite `test_contextual_awareness_milestone_1_1.py` with 11 passing tests covering all functionality.

**User Verification Steps:**

1.  Ask the agent: "What files are in the current directory?"
2.  Ask the agent: "Can you show me the contents of `README.md`?" (Assuming a `README.md` exists).
3.  Navigate to a different directory (if possible within the sandbox environment) and repeat the above queries to see if the context updates.

### Milestone 1.2: Incorporating Recent Commands & Error Logs

**Objective:** Allow the agent to infer context from the history of executed shell commands and recent error logs.

**Tasks:**

*   - [x] **Task 1.2.1: Capture Shell Command History:** ✅ **COMPLETED**
    *   Modify the `execute_shell_command` tool to record the command and its output in a new `session.state` key, e.g., `command_history`. Limit history size to prevent state bloat.
    *   **Implementation Note:** Use `state_manager_tool` with `action='update'` to append to a list.
    *   **✅ Implementation:** Enhanced `execute_shell_command` tool to capture all command executions in `session.state['command_history']` with size limits (50 commands max).
*   - [x] **Task 1.2.2: Capture Error Log Context:** ✅ **COMPLETED**
    *   Integrate a mechanism to capture and store recent error messages from command outputs or `browser_console_messages` in `session.state` (e.g., `recent_errors`).
    *   **Implementation Note:** Parse command outputs for common error indicators.
    *   **✅ Implementation:** Added sophisticated error pattern detection (`_detect_error_patterns`) that identifies 10+ common error types and stores them in `session.state['recent_errors']` (20 errors max).
*   - [x] **Task 1.2.3: Agent Reasoning with Command History/Errors:** ✅ **COMPLETED**
    *   Develop a reasoning module that, when a new user query arrives, checks `command_history` and `recent_errors` for relevant context. For example, if a user asks "Why did that fail?", the agent should infer "that" refers to the last command that produced an error.
    *   **Implementation Note:** This might involve prompt engineering to include historical context or a small internal LLM call to interpret the current query in light of history.
    *   **✅ Implementation:** Enhanced both agents with `check_command_history_context()` function that detects 8+ query patterns referencing previous commands/errors and automatically includes relevant context.
*   - [x] **Task 1.2.4: Integration Tests:** ✅ **COMPLETED**
    *   Write integration tests that run commands (some failing) and then query the agent about the failures, verifying it uses the historical context.
    *   Ensure existing tests are unaffected.
    *   **✅ Implementation:** Created comprehensive test suite `test_contextual_awareness_milestone_1_2.py` with 13 passing tests covering command history capture, error detection, and agent reasoning.

**User Verification Steps:**

1.  Run a shell command that is expected to fail (e.g., `ls non_existent_dir`).
2.  Ask the agent: "Why did that fail?" or "What's wrong with the last command?"
3.  Run a series of successful commands. Then ask a question that relates to an earlier command (e.g., "What was the output of the `pwd` command I ran earlier?").

### Milestone 1.3: Advanced Project Context (Dependencies, Project Structure)

**Objective:** Enable the agent to build a rudimentary internal model of the project's structure and dependencies.

**Tasks:**

*   - [ ] **Task 1.3.1: Project Structure Mapping:**
    *   Implement a mechanism (possibly using `directory_tree` recursively on project root) to periodically or on demand map the project's file and directory structure. Store this in `session.state`.
    *   **Implementation Note:** Consider limitations for very large projects; focus on relevant sub-directories initially. Design should account for managing updates (e.g., event-driven or periodic polling) and resource consumption for large file trees.
*   - [ ] **Task 1.3.2: Dependency Inference (Basic):**
    *   For common project types (e.g., Python `requirements.txt`, Node.js `package.json`), develop a simple parser to extract dependencies and store them in `session.state`.
    *   **Implementation Note:** This can be done by reading specific files using `read_file`.
*   - [ ] **Task 1.3.3: Context-Aware Code Search & Navigation:**
    *   Modify the agent's code search logic (`ripgrep_code_search`) to prioritize searches within the identified project structure and use inferred dependencies to narrow down search scope or provide more relevant results.
    *   **Implementation Note:** When `ripgrep_code_search` is called, automatically add `target_directories` based on the project structure.
*   - [ ] **Task 1.3.4: Integration Tests:**
    *   Create a mock project structure with a `package.json` or `requirements.txt`.
    *   Write integration tests where the agent is asked about dependencies or to find a file related to a specific dependency, verifying its contextual search.
    *   Ensure existing `ripgrep_code_search` tests are unchanged.

**User Verification Steps:**

1.  Create a simple project with a few nested directories and a `package.json` (or `requirements.txt`).
2.  Ask the agent: "What are the dependencies for this project?"
3.  Ask the agent: "Where is the `utils` directory?" or "Find `helper.js` in the project."
4.  Ask the agent: "Show me files related to the `express` dependency."

---

## Feature 2: Proactive Assistance and Intelligent Suggestions

**Goal:** Enable the agent to actively monitor the development environment and offer intelligent, unsolicited suggestions.

### Milestone 2.1: Basic Proactive Error Detection

**Objective:** The agent will automatically detect common errors and suggest initial debugging steps.

**Tasks:**

*   - [ ] **Task 2.1.1: Integrate with Error Log Context:**
    *   Leverage the `recent_errors` state from Milestone 1.2.
*   - [ ] **Task 2.1.2: Implement Simple Error Pattern Matching:**
    *   Develop a module that, upon detecting a new entry in `recent_errors`, attempts to match it against a predefined list of common error patterns (e.g., "file not found," "permission denied," "syntax error").
    *   **Implementation Note:** Use regular expressions or string matching for pattern detection. For more robust and nuanced error detection, consider evolving this module to leverage the underlying LLM for semantic understanding of error messages.
*   - [ ] **Task 2.1.3: Suggest Basic Fixes:**
    *   For matched error patterns, automatically generate and suggest a simple fix or debugging command (e.g., "Check if the file exists using `ls -l <filename>`" or "Verify permissions with `chmod`").
    *   **Implementation Note:** Present suggestions clearly to the user, indicating it's a proactive suggestion.
*   - [ ] **Task 2.1.4: Integration Tests:**
    *   Write tests that simulate various error outputs from shell commands. Verify the agent correctly identifies the error type and suggests a relevant fix.
    *   Ensure `_analyze_code`, `get_issues_by_severity`, `suggest_fixes` still work as expected.

**User Verification Steps:**

1.  Execute a command that results in a "file not found" error (e.g., `cat non_existent_file.txt`). Observe if the agent proactively suggests checking file existence.
2.  Execute a command that results in a "permission denied" error. Observe if the agent suggests checking permissions.

### Milestone 2.2: Proactive Optimization Suggestions

**Objective:** The agent will identify simple code quality issues or inefficiencies and suggest improvements.

**Tasks:**

*   - [ ] **Task 2.2.1: Automatic Code Analysis Trigger:**
    *   Integrate a mechanism to automatically trigger `_analyze_code` when a file is modified (using a file system watch if available, or on a simple `edit_file` call).
    *   **Implementation Note:** This might require an internal polling mechanism or hooks into file modification tools.
*   - [ ] **Task 2.2.2: Filter and Prioritize Suggestions:**
    *   After `_analyze_code` runs, filter the results using `get_issues_by_severity` (e.g., focus on 'error' and 'warning' initially).
    *   Use `suggest_fixes` to get concrete recommendations.
*   - [ ] **Task 2.2.3: Present Optimization Suggestions:**
    *   Present these suggestions to the user in a non-intrusive way, perhaps after a brief pause following a file modification or when the user explicitly requests "suggestions."
    *   **Implementation Note:** Provide an option for the user to accept or reject the suggestions directly (a precursor to Milestone 3.1).
*   - [ ] **Task 2.2.4: Integration Tests:**
    *   Create a test file with a known, simple code quality issue (e.g., an unused variable).
    *   Write an integration test that "modifies" this file, verifies the agent triggers analysis, and suggests the correct fix.
    *   Ensure existing `_analyze_code` and `suggest_fixes` tests are unaffected.

**User Verification Steps:**

1.  Create a simple Python file (`test.py`) with a recognized code quality issue (e.g., `def my_func(): x = 1; return 2`).
2.  Modify the file (or have the agent modify it slightly).
3.  Observe if the agent proactively suggests a fix for the unused variable or other detected issues.
4.  Ask the agent: "Do you have any suggestions for my code?"

### Milestone 2.3: Workflow Guidance and Next Step Suggestions

**Objective:** The agent will anticipate logical next steps in common development workflows and offer guidance.

**Tasks:**

*   - [ ] **Task 2.3.1: Define Basic Workflow Patterns:**
    *   Identify common sequential patterns: "Code change -> Run tests," "New feature -> Create documentation."
    *   **Implementation Note:** These patterns can be simple state transitions or rules (e.g., "if `code_modified` and `tests_not_run`, suggest running tests"). Clarify how these patterns will be defined and managed (e.g., hardcoded rules, configurable templates, or an LLM-driven inference module).
*   - [ ] **Task 2.3.2: Suggest Next Actions:**
    *   Based on the current state and recognized workflow patterns, proactively suggest the next logical action to the user (e.g., "It looks like you've modified `main.py`. Would you like to run the tests?").
    *   **Implementation Note:** Integrate with `workflow_selector_tool` to recommend starting specific sub-workflows.
*   - [ ] **Task 2.3.3: User Opt-In/Out for Proactive Suggestions:**
    *   Provide a mechanism for users to enable/disable or configure the level of proactive suggestions.
    *   **Implementation Note:** Use `state_manager_tool` to store user preferences (e.g., `session.state['proactive_suggestions_enabled']`).
*   - [ ] **Task 2.3.4: Integration Tests:**
    *   Write integration tests that simulate a code change followed by the agent proactively suggesting to run tests.
    *   Verify the agent accurately recognizes the workflow state and offers the correct next step.

**User Verification Steps:**

1.  Make a small code change in a testable project. Observe if the agent suggests running tests.
2.  After creating a new function or module, observe if the agent suggests creating documentation or tests.
3.  Try enabling/disabling proactive suggestions to see if the agent's behavior changes accordingly.

---

## Feature 3: Robust Human-in-the-Loop Workflow Integration

**Goal:** Implement a clear, auditable, and user-friendly mechanism for human approval on critical agent-proposed actions.

### Milestone 3.1: Standardized Approval Interface for File Edits

**Objective:** Ensure all agent-initiated file modifications require explicit user approval with a clear presentation of proposed changes.

**Tasks:**

*   - [ ] **Task 3.1.1: Refactor `edit_file_content` for Mandatory Approval:**
    *   Ensure `edit_file_content` always returns `pending_approval` unless `session.state['require_edit_approval']` is explicitly set to `False` (for internal, non-user-facing automation).
    *   **Implementation Note:** The default should be `True`.
*   - [ ] **Task 3.1.2: Implement Approval/Rejection Mechanism:**
    *   When `pending_approval` is returned, the agent should present the `proposed_filepath` and `proposed_content` clearly to the user.
    *   Provide a simple, standardized way for the user to "approve" or "reject" the proposed edit (e.g., via a specific command or confirmation prompt).
    *   **Implementation Note:** This might involve a new internal `_handle_approval_request` function or a prompt-based loop.
*   - [ ] **Task 3.1.3: Audit Trail for Approvals:**
    *   Log all approval requests (proposed content, timestamp, outcome - approved/rejected, by whom) to a persistent log file or a dedicated `session.state` entry.
    *   **Implementation Note:** Use `state_manager_tool` to update an audit log list.
*   - [ ] **Task 3.1.4: Integration Tests:**
    *   Write integration tests where the agent proposes a file edit. Verify that it correctly enters a `pending_approval` state, presents the diff, and proceeds only upon simulated approval.
    *   Ensure existing `edit_file_content` tests still pass, especially the `dryRun` functionality of `edit_file`.

**User Verification Steps:**

1.  Ask the agent to make a simple, non-critical change to a file (e.g., "Add a comment to `main.py` saying 'Hello World!'").
2.  Observe that the agent shows you the proposed change (a diff or the full new content) and asks for your approval.
3.  Approve the change and verify the file is modified.
4.  Repeat, but reject the change, and verify the file is *not* modified.
5.  Check if a log of the approval request (and your decision) is accessible.

### Milestone 3.2: General Purpose Approval Workflow Pattern

**Objective:** Create a reusable workflow pattern for any critical action requiring human review, not just file edits.

**Tasks:**

*   - [ ] **Task 3.2.1: Define `HumanInLoopAgent` (or similar):**
    *   Create a new abstract agent or a specific workflow type (`HumanApprovalWorkflow`) that takes a proposed action (e.g., a function call, a multi-step plan) and routes it for human review.
    *   **Implementation Note:** This agent would pause execution, present the "payload" for approval, and resume/cancel based on human input.
*   - [ ] **Task 3.2.2: Standardized Proposal Presentation:**
    *   Develop a consistent way for `HumanInLoopAgent` to present diverse types of proposals (e.g., code refactors, deployment plans, architectural decisions). This might involve generating a markdown summary, code diffs, or step-by-step plans.
    *   **Implementation Note:** Consider leveraging markdown rendering for better readability.
*   - [ ] **Task 3.2.3: Integration with `workflow_selector_tool`:**
    *   Update `workflow_selector_tool` to recommend `HumanInLoopAgent` when `requires_approval=True` for complex `task_type` (e.g., "architecture_review," "deployment").
*   - [ ] **Task 3.2.4: Integration Tests:**
    *   Create a mock scenario where a "deployment" task is initiated with `requires_approval=True`.
    *   Write integration tests that verify the `HumanInLoopAgent` is invoked, presents the deployment plan for approval, and only proceeds upon simulated approval.

**User Verification Steps:**

1.  Ask the agent to perform a task explicitly marked as requiring approval (e.g., "Propose a new architecture for the database").
2.  Observe that the agent presents a detailed proposal and requests your explicit approval before proceeding.
3.  Approve, and observe the agent indicates it is proceeding with the approved plan.
4.  Reject, and observe the agent indicates the plan was cancelled.

### Milestone 3.3: Richer Diff Presentation and Annotation

**Objective:** Enhance the visual and interactive quality of proposed changes, allowing for better human review.

**Tasks:**

*   - [ ] **Task 3.3.1: Implement Unified Diff Generation:**
    *   For all code or text modifications, generate a standardized "unified diff" format.
    *   **Implementation Note:** Leverage a Python diffing library or `git diff` output if available and reliable.
*   - [ ] **Task 3.3.2: Allow In-line Commenting/Annotation (Future):**
    *   (Future stretch goal for this milestone or follow-up) Explore mechanisms for users to add comments or suggest small modifications *within* the diff before approving.
    *   **Implementation Note:** This is more complex and might require CLI parsing of user input on specific lines or a more advanced UI concept. Initially, focus on clear diff presentation.
*   - [ ] **Task 3.3.3: Improve Presentation Formatting:**
    *   Ensure diffs are presented clearly in the CLI, potentially with syntax highlighting (if supported by the terminal environment) and line numbers.
    *   **Implementation Note:** Use markdown code blocks and clear headings.
*   - [ ] **Task 3.3.4: Integration Tests:**
    *   Write tests that simulate a proposed multi-line code change. Verify that the agent generates and presents an accurate and readable diff.
    *   Ensure the approval/rejection mechanism still functions correctly with the richer diff.

**User Verification Steps:**

1.  Ask the agent to make a multi-line change to an existing code file.
2.  Observe that the proposed change is presented as a clear, easy-to-read diff.
3.  Verify that you can still approve or reject the change based on this improved presentation.

---

## Feature 4: Interactive Code Refinement and Live Feedback

**Goal:** Create a more dynamic and collaborative coding experience where the agent provides immediate feedback and helps iteratively refine code.

### Milestone 4.1: Real-time Syntax and Basic Style Feedback

**Objective:** The agent will provide immediate feedback on basic syntax errors or style violations as code is "written" or proposed.

**Tasks:**

*   - [ ] **Task 4.1.1: Integrate with Linting on Proposed Code:**
    *   Before proposing any code change or generating new code, run a quick syntax/basic style check using `_analyze_code` (or a more lightweight linter if possible).
    *   **Implementation Note:** This can be done as a pre-validation step within the agent's generation process.
*   - [ ] **Task 4.1.2: Instant Feedback Loop:**
    *   If basic issues are found, the agent should immediately highlight them and suggest corrections *before* committing the change or presenting it for full approval.
    *   **Implementation Note:** This might involve a sub-loop where the agent attempts to fix the issue automatically or asks the user for clarification.
*   - [ ] **Task 4.1.3: Integration Tests:**
    *   Write tests where the agent is instructed to generate syntactically incorrect code. Verify that the agent catches the error and provides immediate feedback or attempts a correction.
    *   Ensure `_analyze_code` still functions independently.

**User Verification Steps:**

1.  Ask the agent to write a simple code snippet with a deliberate syntax error (e.g., "Write a Python function `def foo:`").
2.  Observe if the agent immediately points out the syntax error and suggests a correction, rather than just proposing the incorrect code.
3.  Ask the agent to refactor a piece of code with a known style violation (e.g., incorrect indentation) and observe if it corrects it automatically or flags it.

### Milestone 4.2: Iterative Code Generation/Refinement with Agent Feedback

**Objective:** Enable a conversational and iterative process for generating and refining code.

**Tasks:**

*   - [ ] **Task 4.2.1: Implement `LoopAgent` for Code Refinement:**
    *   Design a specific `LoopAgent` workflow pattern, e.g., `code_refinement_loop`, that allows the agent to propose code, receive feedback (e.g., "make it more efficient," "add error handling"), and revise the code.
    *   **Implementation Note:** The loop continues until the user is satisfied or a maximum iteration count is reached.
*   - [ ] **Task 4.2.2: Contextual Revision based on User Feedback:**
    *   When the user provides feedback on generated/modified code, the agent should use this feedback along with the code context to make targeted revisions.
    *   **Implementation Note:** This will require careful prompt engineering to instruct the underlying LLM to incorporate specific revision requests.
*   - [ ] **Task 4.2.3: Integrate Code Quality & Testing Agents into Loop:**
    *   Within the `code_refinement_loop`, automatically run `_analyze_code` and potentially simple unit tests (`enhanced_testing_agent`) after each revision to provide comprehensive feedback.
    *   **Implementation Note:** This creates a mini "red-green-refactor" cycle within the refinement loop.
*   - [ ] **Task 4.2.4: Integration Tests:**
    *   Create a scenario where the agent generates initial code, then the test provides specific refinement requests (e.g., "add a loop," "handle an edge case").
    *   Verify the agent iterates, revises the code, and eventually produces the desired output based on the feedback.

**User Verification Steps:**

1.  Ask the agent to "write a Python function to calculate factorial."
2.  Once it provides the initial code, give feedback like: "Now, add input validation to handle negative numbers."
3.  Observe how the agent iteratively modifies the code and potentially suggests improvements or runs a quick check.
4.  Continue giving feedback until satisfied, then verify the final code.

---

## Feature 5: Integrated Test-Driven Development (TDD) Orchestration

**Goal:** Provide structured support for the TDD workflow, guiding the developer through test-first development.

### Milestone 5.1: Test Stub Generation & Basic Test Execution Integration

**Objective:** Automate the creation of test stubs and enable direct execution of tests.

**Tasks:**

*   - [ ] **Task 5.1.1: Test Stub Generator Tool:**
    *   Create a new internal tool (`_generate_test_stub`) that, given a function/method signature or a description, generates a basic test file with a placeholder test function.
    *   **Implementation Note:** This tool would likely use the underlying LLM with a specific prompt for test generation.
*   - [ ] **Task 5.1.2: Integrate `enhanced_testing_agent` for Execution:**
    *   Ensure the `enhanced_testing_agent` can be easily invoked to run specific test files or test suites from the CLI, with clear pass/fail output.
    *   **Implementation Note:** This might involve modifying `enhanced_testing_agent` to accept `test_file_path` as a parameter and explicitly using `uv run pytest`.
*   - [ ] **Task 5.1.3: Integration Tests:**
    *   Write tests to verify that `_generate_test_stub` correctly generates a test file for a given function.
    *   Write tests to ensure `enhanced_testing_agent` can run these generated test files and report results.

**User Verification Steps:**

1.  Ask the agent: "Generate a test stub for a Python function `add(a, b)`." Verify a new test file with a placeholder test is created.
2.  Create a simple function and a corresponding passing test. Ask the agent to "Run tests for `my_function`." Verify it reports success.
3.  Create a failing test for `my_function`. Ask the agent to run tests and verify it reports failure.

### Milestone 5.2: Automated Test Running and Reporting

**Objective:** Implement automated test execution after code changes and provide comprehensive test reports.

**Tasks:**

*   - [ ] **Task 5.2.1: Automatic Test Execution on Code Change (Opt-in):**
    *   Upon approval of a code modification (`edit_file_content`), if the `TDD_mode_enabled` flag is set in `session.state`, automatically trigger `enhanced_testing_agent` for relevant tests.
    *   **Implementation Note:** The agent needs to infer which tests are relevant to the modified code. Ensure `uv run pytest` is used for test execution.
*   - [ ] **Task 5.2.2: Enhanced Test Reporting:**
    *   Improve the output of `enhanced_testing_agent` to provide more detailed reports: number of tests run, passed, failed, error messages for failures, and possibly code coverage (if easily integrateable).
    *   **Implementation Note:** Parse test runner output (e.g., `pytest`, `jest`) to extract structured data.
*   - [ ] **Task 5.2.3: TDD Workflow Orchestration:**
    *   Implement a `TDD_workflow` using `SequentialAgent` and `LoopAgent` that guides the user: "Write failing test -> Write code to pass test -> Run tests -> Refactor -> Run tests."
    *   **Implementation Note:** This workflow would leverage `_generate_test_stub`, `edit_file_content` (with approval), and `enhanced_testing_agent`.
*   - [ ] **Task 5.2.4: Integration Tests:**
    *   Simulate a TDD cycle: generate a failing test, then have the agent modify code to make it pass. Verify automated test execution and reporting at each step.

**User Verification Steps:**

1.  Enable TDD mode (`set TDD_mode_enabled true` in session state).
2.  Ask the agent to "Start a TDD session for a new feature: a string reversal function."
3.  Observe the agent guides you to write a failing test, then to write the code.
4.  After you (or the agent) write the code, observe it automatically runs the tests and reports success/failure.
5.  Introduce a bug into the string reversal function. Observe the agent detects the failing test and guides you to fix it.

---

## Feature 6: Intelligent Version Control Integration

**Goal:** Move beyond basic `git` command execution to a more intelligent, context-aware interaction with version control.

### Milestone 6.1: Context-Aware Commit Message Generation

**Objective:** Automatically generate meaningful commit messages based on staged changes.

**Tasks:**

*   - [ ] **Task 6.1.1: Git Diff Analysis Tool:**
    *   Create an internal tool (`_get_staged_diff`) that executes `git diff --staged` and returns the output.
    *   **Implementation Note:** Use `execute_shell_command`.
*   - [ ] **Task 6.1.2: Commit Message Generation Logic:**
    *   When the user indicates a desire to commit, or a workflow reaches a commit point, use the staged diff output and the context (e.g., feature branch name, JIRA ticket ID if provided) to generate a concise and descriptive commit message using the LLM.
    *   **Implementation Note:** Design a robust prompt for the LLM that includes the diff and contextual information.
*   - [ ] **Task 6.1.3: User Review and Edit of Commit Message:**
    *   Present the generated commit message to the user for review and allow them to accept it or edit it before the `git commit` command is executed.
    *   **Implementation Note:** This can integrate with the Milestone 3.1 approval mechanism for text proposals.
*   - [ ] **Task 6.1.4: Integration Tests:**
    *   Create a mock Git repository with staged changes.
    *   Write tests where the agent is asked to commit, verifying it generates a relevant message and waits for user approval.

**User Verification Steps:**

1.  Make some small changes to a file in a Git repository and stage them (`git add .`).
2.  Ask the agent: "Commit these changes."
3.  Observe that the agent proposes a commit message based on your changes.
4.  Accept the message and verify the commit is made with the proposed message.
5.  Reject/edit the message and verify the commit is made with your edited message.

### Milestone 6.2: Intelligent Staging and Branching Assistance

**Objective:** Help developers intelligently stage changes and manage branches based on inferred intent.

**Tasks:**

*   - [ ] **Task 6.2.1: Intelligent Staging Suggestions:**
    *   When a user asks to "stage changes" or "add files," analyze the modified/untracked files (using `git status` via `execute_shell_command`).
    *   Propose logical groupings of files to stage (e.g., all files related to a specific feature, only bug fixes).
    *   **Implementation Note:** This involves mapping file paths to likely features/components.
*   - [ ] **Task 6.2.2: Branching Strategy Guidance:**
    *   When a user asks to "create a new branch" or "start a new feature," suggest a branch naming convention or ask clarifying questions about the feature to recommend a suitable branch type (e.g., `feature/`, `bugfix/`).
    *   **Implementation Note:** Leverage the LLM's ability to understand intent and knowledge of common Git workflows.
*   - [ ] **Task 6.2.3: Conflict Resolution Guidance (Basic):**
    *   If `git status` indicates merge conflicts, proactively identify the conflicting files and suggest basic steps for resolution (e.g., "Open `file.js` to resolve conflicts," "Use `git status` to see conflict markers").
    *   **Implementation Note:** This is basic guidance, not automated resolution.
*   - [ ] **Task 6.2.4: Integration Tests:**
    *   Create scenarios with un-staged changes and modified files. Verify the agent suggests intelligent staging.
    *   Test the branch creation guidance by asking the agent to "start a new feature" and verify its suggestions.

**User Verification Steps:**

1.  Modify several files in your repository, some for a new feature, some for a bug fix. Do not stage them.
2.  Ask the agent: "Can you help me stage these changes?" Observe if it suggests logical groupings.
3.  Ask the agent: "I want to start working on a new authentication feature. What's the best way to create a branch?" Observe its suggestions for naming and process.
4.  Simulate a merge conflict (e.g., create a conflict manually). Ask the agent: "What do I do now?" Observe its guidance.

---

## Feature 7: Unified and Persistent Contextual Memory Across Sessions

**Goal:** Allow the agent to retain and leverage a deep, structured understanding of past interactions, project state, and learned preferences across multiple development sessions.

### Milestone 7.1: Robust Session State Persistence and Loading

**Objective:** Ensure the full `session.state` can be reliably saved and loaded across agent invocations.

**Tasks:**

*   - [ ] **Task 7.1.1: Implement `_save_current_session_to_file_impl`:**
    *   Fully implement `_save_current_session_to_file_impl` to serialize the entire `session.state` (or a defined subset of it) into a JSON file at a specified `filepath`.
    *   **Implementation Note:** Handle potential serialization issues (e.g., non-serializable objects) by converting them to string representations if necessary. Clearly define which parts of `session.state` are intended for persistence and which are ephemeral.
*   - [ ] **Task 7.1.2: Implement `_load_memory_from_file_impl` for Session State:**
    *   Fully implement `_load_memory_from_file_impl` to deserialize the `session.state` from a JSON file.
    *   **Implementation Note:** Ensure proper error handling if the file is corrupted or not found.
*   - [ ] **Task 7.1.3: Automatic Session Persistence (Opt-in):**
    *   Implement an optional feature to automatically save the session state at regular intervals or upon graceful exit of the agent.
    *   **Implementation Note:** Use `state_manager_tool` to manage a `session_auto_save_enabled` flag and `last_save_time`.
*   - [ ] **Task 7.1.4: Integration Tests:**
    *   Set various values in `session.state`.
    *   Call `_save_current_session_to_file_impl`, then `_load_memory_from_file_impl` (simulating a restart), and verify that the `session.state` is restored correctly.

**User Verification Steps:**

1.  Set some custom values in the session state (e.g., `set my_pref "dark_mode"`).
2.  Ask the agent to "Save my current session to `my_session.json`."
3.  Restart the agent (or simulate a restart).
4.  Ask the agent to "Load session from `my_session.json`."
5.  Verify that your custom preference (`my_pref`) is still set.

### Milestone 7.2: Structured Knowledge Graph for Project Context

**Objective:** Store derived project knowledge (e.g., function relationships, architectural decisions, design patterns used) in a structured, queryable knowledge graph.

**Tasks:**

*   - [ ] **Task 7.2.1: Populate Knowledge Graph with Code Analysis Results:**
    *   Whenever `_analyze_code` is run or `enhanced_code_quality_agent` provides insights, extract entities (e.g., functions, classes, modules) and relations (e.g., "uses," "inherits from") and add them to the knowledge graph using `create_entities` and `create_relations`.
    *   **Implementation Note:** Focus on extracting key information like function definitions, class structures, and inter-file dependencies. A clear and extensible schema for the knowledge graph (defining entity types, properties, and relationships) should be designed as a critical prerequisite.
*   - [ ] **Task 7.2.2: Store Design Patterns & Decisions:**
    *   When `enhanced_design_pattern_agent` is used, store identified design patterns (e.g., "Factory Method") and relevant architectural decisions as entities in the knowledge graph.
    *   **Implementation Note:** Use `create_entities` for the pattern name and `add_observations` for its context/location in the codebase.
*   - [ ] **Task 7.2.3: Query Knowledge Graph for Context:**
    *   Modify the agent's reasoning process to query the knowledge graph (`search_nodes`, `open_nodes`, `read_graph`) when answering complex questions about project structure, code relationships, or design choices.
    *   **Implementation Note:** This allows the agent to answer questions like "Where is the `Logger` class used?" or "What design patterns are applied in `auth.py`?"
*   - [ ] **Task 7.2.4: Integration Tests:**
    *   Create a simple code file with a class and a function that uses it.
    *   Run code analysis via the agent.
    *   Write tests to verify that the knowledge graph contains entities for the class and function and a relation indicating usage.
    *   Query the agent about these relationships and verify it uses the knowledge graph.

**User Verification Steps:**

1.  Provide the agent with a small, well-defined code snippet that uses a common design pattern (e.g., Singleton, Observer).
2.  Ask the agent to analyze the code for design patterns.
3.  Once the analysis is complete, ask: "What design patterns are used in this project?" or "How is the `MyClass` related to `AnotherClass`?"
4.  Verify the agent can answer these questions based on its structured knowledge.

### Milestone 7.3: Agent Reasoning and Proactive Recall from Memory

**Objective:** Enable the agent to actively and intelligently retrieve and apply relevant information from its persistent memory without explicit user prompts.

**Tasks:**

*   - [ ] **Task 7.3.1: Context-Sensitive Memory Retrieval:**
    *   Before executing a complex task, the agent should automatically query its memory (`load_memory`, `search_nodes`) for relevant past discussions, architectural decisions, or known issues related to the current context (e.g., the files being modified, the type of task).
    *   **Implementation Note:** This involves an initial memory search phase in the agent's deliberation process.
*   - [ ] **Task 7.3.2: "Lessons Learned" Integration:**
    *   Whenever a bug is fixed or a complex problem is solved (`enhanced_debugging_agent`), encourage the user (or automate) the process of adding "lessons learned" or "solution patterns" to the knowledge graph or a dedicated memory store.
    *   **Implementation Note:** This involves creating specific entities/observations for "problem," "solution," "root cause."
*   - [ ] **Task 7.3.3: Proactive Suggestion based on Memory:**
    *   If a similar problem or context is encountered again, the agent should proactively recall the "lessons learned" from memory and suggest the past solution or approach.
    *   **Implementation Note:** This requires matching current context to stored memory patterns.
*   - [ ] **Task 7.3.4: Integration Tests:**
    *   Simulate a "known bug" scenario that has been previously documented in memory (e.g., a specific configuration issue and its fix).
    *   Introduce the same bug again.
    *   Write tests to verify the agent proactively suggests the known solution from its memory.

**User Verification Steps:**

1.  Simulate a bug fix: Ask the agent to debug a specific, simple problem and provide a solution. Once fixed, confirm with the agent that it has learned from this.
2.  Introduce the *exact same bug* again in the same project.
3.  Observe if the agent quickly recognizes the issue and proactively suggests the previous solution or points to the relevant "lesson learned" from its memory.
4.  Discuss a particular architectural decision with the agent. In a later, separate session, ask a question that implicitly requires recalling that decision. Verify the agent uses its memory.
