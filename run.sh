#!/usr/bin/env bash

clear
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx \
  --with extensions \
  --with google-api-core \
  --with chromadb \
  --with protobuf \
  --with openai \
  --with tiktoken \
  --no-cache \
  --python 3.13 \
  --from git+https://github.com/BlueCentre/adk-python.git@feat/rich-click \
  adk run "${1:-devops}" || echo "🙈 Ignore the error above. It's caused by Google ADK."
