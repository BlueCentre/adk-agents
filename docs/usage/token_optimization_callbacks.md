---
layout: default
title: Token Optimization Callbacks
parent: "Usage"
nav_order: 3
description: "How to use the token optimization callback feature for the software engineer agent."
---

# Token Optimization Callbacks

The Software Engineer Agent includes a powerful token optimization feature that helps to reduce the number of tokens sent to the language model. This can lead to significant cost savings and faster response times.

## How it Works

The token optimization feature is implemented as a series of callbacks that are executed before the agent sends a request to the language model. These callbacks perform a variety of optimizations, including:

*   **Conversation Filtering:** The agent intelligently filters the conversation history to only include the most relevant messages.
*   **Context Pruning:** The agent removes unnecessary information from the context, such as redundant code snippets or irrelevant file contents.
*   **Intelligent Summarization:** The agent summarizes long pieces of text to reduce the number of tokens without losing important information.

## Enabling and Disabling Token Optimization

Token optimization is enabled by default. You can disable it by setting the `ENABLE_TOKEN_OPTIMIZATION` environment variable to `false`.

## Monitoring Token Optimization

You can monitor the effectiveness of the token optimization feature by viewing the agent's logs. The logs contain detailed information about the optimizations that were performed, including the number of tokens that were saved.
