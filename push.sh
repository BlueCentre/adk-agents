#!/usr/bin/env bash

clear
echo 'Please stage the repo changes, create a commit with a summarized message of what changed, and then push to main branch\nexit' |
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
