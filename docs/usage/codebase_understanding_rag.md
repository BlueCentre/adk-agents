---
layout: default
title: Codebase Understanding (RAG)
parent: Usage
nav_order: 2
description: "A deep-dive guide into using the RAG feature for codebase understanding."
---

# Usage Guide: Codebase Understanding (RAG)

The DevOps Agent's ability to understand your codebase is powered by a Retrieval-Augmented Generation (RAG) system. This feature allows the agent to perform deep semantic searches on your project's files, providing it with the context needed to answer complex questions and perform sophisticated tasks.

This guide explains how to configure and use the RAG feature.

## How it Works

The RAG system works in two main stages:

1.  **Indexing**: The agent scans the files in a directory you specify, breaks them down into smaller, meaningful chunks, and converts those chunks into numerical representations (embeddings). These embeddings are stored in a local vector database (ChromaDB).
2.  **Retrieval**: When you ask a question, the agent converts your query into an embedding and uses it to find the most relevant code chunks from the vector database. These chunks are then provided to the language model as context, enabling it to answer questions with high accuracy.

## How to Configure the RAG Feature

This feature requires one essential piece of configuration.

You must set the following environment variable to tell the agent where to store the vector database:

```sh
# Required for Codebase Understanding (RAG): The local path to store the vector database
CHROMA_DATA_PATH="./rag_database"
```

You can set this in your shell or add it to your `.env` file. The path can be absolute or relative to the project root. Make sure the directory exists or that the agent has permission to create it. For more information on configuration, see the [[Configuration Reference|../configuration]].

## The RAG Workflow

Using the RAG feature involves two key tools: `index_directory_tool` and `retrieve_code_context_tool`.

### Step 1: Indexing a Directory

Before you can ask questions about a codebase, you must first index it. This is done using the `index_directory_tool`.

**When to Index:**
*   When you are setting up the agent with a new project for the first time.
*   When you have made significant changes to the codebase and want to update the agent's knowledge.

**How to Use:**

Provide the `directory_path` you want to index. For example, to index the agent's own source code, you would use the following prompt:

> **User Prompt:**
> `index_directory_tool(directory_path="/Users/james/Workspace/gh/lab/adk-agents/agents/devops/")`

The agent will scan the directory, process the files, and report its progress.

### Step 2: Retrieving Code Context

Once a directory is indexed, you can ask questions about it using the `retrieve_code_context_tool`. This tool takes a natural language `query` and returns the most relevant code snippets it can find.

**How to Use:**

Formulate a clear and specific question about the code.

> **User Prompt:**
> `retrieve_code_context_tool(query="How does the PlanningManager handle plan revisions?")`

The agent will perform a semantic search and return the code chunks that best answer your question, giving you instant insight into your project's implementation details.

## Best Practices

- **Be Specific in Your Queries**: Vague queries will yield vague results. The more specific your question, the more accurate the retrieved context will be.
- **Index Relevant Directories**: Only index the source code and documentation that is relevant to the tasks you want the agent to perform. Indexing unnecessary files can add noise to the search results.
- **Re-index After Major Changes**: If you've recently refactored a large part of your application, it's a good idea to re-index the directory to ensure the agent has the most up-to-date information. You can use the `force_reindex=True` parameter in the `index_directory_tool` to do this.
