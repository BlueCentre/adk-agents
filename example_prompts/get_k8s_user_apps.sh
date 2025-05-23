#!/usr/bin/env bash

clear
echo -e "What user applications are running in the current k8s cluster?\nexit" | \
  PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx \
    --with extensions \
    --with google-genai \
    --with google-api-core \
    --with chromadb \
    --with protobuf \
    --with openai \
    --with tiktoken \
    --python 3.13 \
    --from git+https://github.com/BlueCentre/adk-python.git@feat/rich-click \
    adk run devops
