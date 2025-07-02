---
layout: default
title: Getting Started
nav_order: 2
description: "A step-by-step tutorial to get the DevOps Agent up and running with its core features."
---

# Getting Started: A Quick Start Guide

Welcome to the DevOps Agent! This guide will walk you through the essential first steps to configure the agent and use its powerful codebase understanding features.

## Step 1: Installation

First, ensure you have followed the installation instructions in the main [README.md](https://github.com/BlueCentre/adk-agents/blob/main/README.md) file of the project repository. This will set up the agent and its dependencies.

## Step 2: Essential Configuration

The agent is configured using environment variables. The easiest way to manage these is by creating a `.env` file in the root of the project directory.

1.  **Create a file named `.env`** in the root of the `adk-agents` repository.
2.  **Copy and paste** the following content into the file:

    ```sh
    # Required: Your API key for Google AI services
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"

    # Required for Codebase Understanding (RAG): The local path to store the vector database
    # Make sure this directory exists or the agent has permission to create it.
    CHROMA_DATA_PATH="./rag_database"
    ```

3.  **Replace `"YOUR_GOOGLE_API_KEY_HERE"`** with your actual Google API key.
4.  The `CHROMA_DATA_PATH` tells the agent where to save the knowledge it builds about your code. The example `rag_database` is a good default.

For a full list of all possible settings, see the [[Configuration Reference|configuration]].

## Step 3: Indexing Your First Project

To enable the agent to answer questions about your code, you first need to **index** it. This process scans your project files and stores them in the ChromaDB vector database you configured in the previous step.

Let's say you want to index the agent's own core logic. You would run the agent and give it the following instruction:

> **User Prompt:**
> `index_directory_tool(directory_path="/Users/james/Workspace/gh/lab/adk-agents/agents/devops/")`

The agent will use the `index_directory_tool` to scan the specified directory and create the index. You only need to do this once per project, or whenever you want to update the index with major code changes.

## Step 4: Asking a Question About Your Code

Once your project is indexed, you can ask the agent questions about it using the `retrieve_code_context_tool`. The agent will perform a semantic search on the indexed data to find the most relevant code snippets to answer your question.

> **User Prompt:**
> `retrieve_code_context_tool(query="How is the PlanningManager implemented?")`

The agent will return the most relevant code chunks related to the `PlanningManager`, giving you instant insight into the codebase.

## What's Next?

You've successfully set up and used the core features of the DevOps Agent!

*   To explore all configuration options, see the **[[Configuration Reference|configuration]]**.
*   To learn about other features like Interactive Planning, browse the rest of our documentation.
