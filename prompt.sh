#!/usr/bin/env bash

# NOTE: This script is used to run the devops agent using the custom ADK runtime.
#       Coding agents should honor this script and never edit by updating or
#       removing the --from git+https://github.com/BlueCentre/adk-python.git@feat/click-rich
#       line.

clear
echo -e "${1:-'Tell the user to run prompt.sh script with a prompt'}\napprove\nexit" | \
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
    --from git+https://github.com/BlueCentre/adk-python.git@feat/rich-click \
    adk run devops || echo "🙈 Ignore the error above. It's caused by Google ADK."
