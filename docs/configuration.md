---
layout: default
title: Configuration
nav_order: 4
description: "A comprehensive reference for all environment variables used to configure the DevOps Agent."
---

# Configuration Reference

The DevOps Agent is configured primarily through environment variables. This allows for flexible deployment and easy management of settings. This page serves as the definitive reference for all available configuration options.

## Loading Configuration

Configuration variables can be set in your shell environment or stored in a `.env` file in the project's root directory.

## Core Agent Configuration

These variables control the fundamental behavior of the agent.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `DEVOPS_AGENT_INTERACTIVE` | Set to `true` to force interactive mode, which can change logging behavior. | `false` |
| `DEVOPS_AGENT_QUIET` | Set to `true` to suppress most logging output for cleaner integration with scripts. | `false` |
| `LOG_FULL_PROMPTS` | Set to `true` to log the complete prompts sent to the LLM. Useful for debugging. | `false` |

## Feature Flags

These flags enable or disable major agent features.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `ENABLE_INTERACTIVE_PLANNING` | Set to `true` to enable the interactive planning feature, where the agent proposes a plan for complex tasks and waits for user approval. | `false` |
| `ENABLE_CODE_EXECUTION` | Set to `true` to allow the agent to execute code. This is a powerful feature that should be used with caution. | `false` |

## LLM & Model Configuration

These variables control the language models used by the agent for different tasks.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | **Required.** Your API key for the Google AI services. | (None) |
| `AGENT_MODEL` | The primary model used for general agent reasoning and conversation. | `gemini-1.5-flash-latest` |
| `SUB_AGENT_MODEL` | The model used for specialized sub-agent tasks. | `gemini-1.5-flash-latest` |
| `CODE_EXECUTION_MODEL` | The model used for generating and understanding code to be executed. | `gemini-1.5-flash-latest` |
| `GOOGLE_SEARCH_MODEL` | The model used for processing search results. | `gemini-1.5-flash-latest` |
| `SUMMARIZER_MODEL` | The model used for summarizing large files or text. | `gemini-1.5-flash-latest` |

### Gemini Thinking Configuration

These settings control the "thinking" feature available in certain Gemini models.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `GEMINI_THINKING_ENABLE` | Set to `true` to allow the model to use its internal reasoning (thinking) capabilities. | `false` |
| `GEMINI_THINKING_INCLUDE_THOUGHTS` | Set to `true` to include the model's thought process in the output. | `true` |
| `GEMINI_THINKING_BUDGET` | The number of tokens allocated for the model's internal reasoning process. | `8192` |

## RAG & Codebase Understanding

These variables configure the Retrieval-Augmented Generation (RAG) feature, which allows the agent to understand your codebase.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `CHROMA_DATA_PATH` | **Required for RAG.** The local file path where the ChromaDB vector database will be stored. | (None) |
| `SOFTWARE_ENGINEER_CONTEXT` | The path to a JSON file containing context about the software project. | `eval/project_context_empty.json` |

## Observability, Metrics & Telemetry

These variables control the agent's ability to export telemetry data for monitoring and analysis. Observability is auto-enabled if any `GRAFANA` or `OPENLIT` variables are set.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `DEVOPS_AGENT_OBSERVABILITY_ENABLE` | Explicitly set to `true` to enable all observability features. | `false` |
| `DEVOPS_AGENT_ENABLE_LOCAL_METRICS` | Set to `true` to print metrics to the console, useful for local development without an external collector. | `false` |
| `DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT` | Set to `true` to prevent any telemetry data from being sent to an external endpoint, even if configured. | `false` |

### Grafana OTLP Export

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `GRAFANA_OTLP_ENDPOINT` | The OTLP endpoint for your Grafana Cloud instance. | (None) |
| `GRAFANA_OTLP_TOKEN` | The authentication token for the Grafana OTLP endpoint. | (None) |
| `GRAFANA_EXPORT_INTERVAL_SECONDS` | The interval, in seconds, at which telemetry data is exported. | `120` |
| `GRAFANA_EXPORT_TIMEOUT_SECONDS` | The timeout, in seconds, for the export request. | `30` |

### OpenLIT & Tracing Configuration

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `OPENLIT_ENVIRONMENT` | The environment name for OpenLIT (e.g., "Production", "Staging"). | `Production` |
| `OPENLIT_APPLICATION_NAME` | The name of the application as it will appear in your observability platform. | (None) |
| `OPENLIT_CAPTURE_CONTENT` | Set to `true` to capture the content of prompts and responses in traces. | `true` |
| `SERVICE_NAME` | The name of this service. | `devops-agent` |
| `SERVICE_VERSION` | The version of this service. | `1.0.0` |
| `SERVICE_INSTANCE_ID` | A unique identifier for this specific agent instance. | `devops-agent-<process_id>` |
| `TRACE_SAMPLING_RATE` | The sampling rate for traces (1.0 = 100%, 0.5 = 50%). | `1.0` |
