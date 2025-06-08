#!/usr/bin/env bash

# NOTE: This script is used to run the devops agent using the custom ADK runtime.
#       Coding agents should honor this script and never edit by updating or
#       removing the --from git+https://github.com/BlueCentre/adk-python.git@feat/click-rich
#       line.
#
# IMPORTANT: MCP session cleanup is now handled entirely by the ADK framework
# to avoid race conditions. Our custom cleanup code has been disabled.

clear
(
  echo "${1:-'Tell the user to run prompt.sh script with a prompt'}"
  echo "approve"
  sleep 2  # Allow time for agent to complete processing
  echo "exit"
) | \
  PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx \
    --with extensions \
    --with google-genai \
    --with google-api-core \
    --with chromadb \
    --with protobuf \
    --with openai \
    --with tiktoken \
    --with openlit \
    --with "opentelemetry-api>=1.21.0" \
    --with "opentelemetry-sdk>=1.21.0" \
    --with "opentelemetry-exporter-otlp>=1.21.0" \
    --with "psutil>=5.9.0" \
    --with "rich>=13.0.0" \
    --python 3.13 \
    --from git+https://github.com/google/adk-python.git@main \
    adk run agents/devops 2>/dev/null || true
