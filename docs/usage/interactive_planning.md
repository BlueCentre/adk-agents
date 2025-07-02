---
layout: default
title: Interactive Planning
parent: Usage
nav_order: 1
description: "A deep-dive guide into the Interactive Planning feature for collaborative task execution."
---

# Usage Guide: Interactive Planning

The Interactive Planning feature is one of the most powerful capabilities of the DevOps Agent, allowing you to collaborate on complex tasks, review the proposed approach, and approve it before execution begins. This guide provides a detailed walkthrough of how to use this feature effectively.

## What is Interactive Planning?

For complex or multi-step tasks, the agent can generate a detailed, step-by-step plan and present it to you for approval. This ensures that you agree with the agent's approach before any actions are taken.

The key capabilities of this feature include:
- **AI-Generated Plans**: The agent analyzes your request and creates a logical sequence of tool calls to achieve the goal.
- **Interactive Review**: You can review the plan and either approve it or provide feedback for revisions.
- **Step-by-Step Execution**: Once approved, the agent executes the plan one step at a time, showing its progress.

## How to Enable Interactive Planning

This feature is **disabled by default** to ensure a streamlined experience for simple, single-shot commands.

To enable it, you must set the following environment variable:

```sh
ENABLE_INTERACTIVE_PLANNING="true"
```

You can set this in your shell or add it to your `.env` file. For more information on configuration, see the [[Configuration Reference|../configuration]].

## The Planning Workflow

The interactive planning process follows a clear, three-step workflow: **Trigger -> Review -> Execute**.

### 1. Triggering a Plan

The agent uses an internal heuristic to decide when a task is complex enough to require a plan. You don't need to explicitly ask for a plan. The heuristic looks for keywords and patterns that suggest a multi-step process.

**Examples of prompts that will likely trigger a plan:**

> "Implement a new feature to handle user authentication."
> "Refactor the `main.py` file to improve its structure and add error handling."
> "Design and create a new CI/CD pipeline for the project."

**Examples of prompts that will likely NOT trigger a plan:**

> "read the file `config.py`"
> "list all the files in the current directory"
> "what is the current time"

### 2. Reviewing and Approving the Plan

When a plan is triggered, the agent will present it to you in a structured format and pause execution, awaiting your input.

To approve the plan and begin execution, you must type the specific keyword:

```
approve
```

If you provide any other feedback, the agent will interpret it as a request for revision. It will take your feedback, amend the plan, and present the new version to you for approval.

**Example Interaction:**

> **Agent:**
> I have created a plan to address your request:
> 1.  `read_file(path=\"src/auth.py\")`
> 2.  `edit_file(path=\"src/auth.py\", ...)`
> 3.  `execute_shell_command(command=\"pytest tests/test_auth.py\")`
>
> Please type `approve` to execute this plan, or provide feedback to revise it.

> **User:**
> `approve`

### 3. Execution

Once you approve the plan, the agent will begin executing the steps in order. It will provide real-time updates as each step is completed.

## Best Practices

- **Be Specific in Your Initial Prompt**: A more detailed initial request will help the agent create a more accurate and effective plan.
- **Provide Clear Feedback for Revisions**: If you don't like the plan, clearly state what you want to be changed. For example, "Instead of editing the file directly, first create a backup."
- **Use for Complex Tasks**: This feature is most valuable for tasks that involve multiple steps, file modifications, or command executions.
