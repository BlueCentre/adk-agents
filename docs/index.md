---
layout: default
title: Home
nav_order: 1
description: "Welcome to the documentation for the DevOps Agent, a sophisticated AI assistant for developers and DevOps engineers."
permalink: /
---

# Welcome to the DevOps Agent Documentation

The **DevOps Agent** is a sophisticated AI assistant engineered to empower developers and DevOps engineers across the full software development lifecycle, from infrastructure management to operational excellence. Built on the Google Agent Development Kit (ADK) foundation with Google Gemini LLMs providing advanced reasoning capabilities, the agent utilizes ChromaDB for semantic code search and incorporates cutting-edge context management.

## 🚀 Latest Features

### Advanced CLI Interfaces
- **Enhanced CLI**: Rich interactive interface with multi-line input, mouse support, and smart auto-completion
- **Textual TUI**: Full-featured terminal user interface with persistent input panes and agent interruption capabilities
- **Web UI**: Modern web-based interface for browser-based interactions
- **API Server**: RESTful API for programmatic access and integration

### Deployment Options
- **Local Development**: Run directly with `uv` package manager
- **Google Cloud Run**: One-command deployment to serverless containers
- **Agent Engine**: Deploy to Google Cloud's managed agent infrastructure
- **Docker**: Containerized deployment with auto-generated Dockerfiles

This site provides comprehensive documentation for the DevOps Agent. Here you will find:

- **[Features](./features.md):** Discover the wide range of capabilities offered by the agent
- **[Usage Guide](./usage.md):** Learn how to install, configure, and interact with the agent
- **[CLI Documentation](./cli/):** Detailed guides for all CLI interfaces and features
- **[Contributing](./contributing.md):** Find out how you can contribute to the development of the DevOps Agent

## Quick Overview

The DevOps Agent is designed to assist with:
- **CI/CD Automation**: Pipeline generation, troubleshooting, and optimization
- **Infrastructure Management**: IaC generation, cloud resource management, and cost optimization
- **Deep Codebase Understanding**: RAG-powered semantic search and code analysis
- **Workflow Automation**: Task automation, compliance checks, and incident response
- **Interactive Task Planning**: Collaborative planning with review and approval workflows
- **Multi-Modal Interactions**: CLI, TUI, Web, and API interfaces

## Getting Started

Choose your preferred interface:

```bash
# Enhanced CLI with rich features
adk run agents/devops

# Full-featured TUI with persistent input
adk run agents/devops --tui

# Web interface for browser-based interaction
adk web agents/

# API server for programmatic access
adk api_server agents/
```

Dive into the documentation to explore how the DevOps Agent can streamline your workflows and enhance your productivity.

We hope you find this documentation helpful!
