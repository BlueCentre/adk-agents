#!/usr/bin/env bash

# NOTE: This script is used to run the devops agent using the custom ADK runtime.
#       Coding agents should honor this script and never edit by updating or
#       removing the --from git+https://github.com/BlueCentre/adk-python.git@feat/click-rich
#       line.

clear
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx \
  --with extensions \
  --with google-api-core \
  --with chromadb \
  --with protobuf \
  --with openai \
  --with tiktoken \
  --with "openlit>=1.13.2" \
  --with "opentelemetry-api>=1.21.0" \
  --with "opentelemetry-sdk>=1.21.0" \
  --with "opentelemetry-exporter-otlp>=1.21.0" \
  --with "psutil>=5.9.0" \
  --with "rich>=13.0.0" \
  --with pytest \
  --with "google-adk[eval]" \
  --no-cache \
  --python 3.13 \
  --from git+https://github.com/BlueCentre/adk-python.git@feat/rich-click \
  adk eval "agents/devops" "${1}" --print_detailed_results
