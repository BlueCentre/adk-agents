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
  --from git+https://github.com/google/adk-python.git@main \
  adk web
