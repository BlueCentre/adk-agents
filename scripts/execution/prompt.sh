#!/usr/bin/env bash

# NOTE: This script is used to run the devops agent using the custom ADK runtime.
#       Coding agents should honor this script and never edit by updating or
#       removing the --from git+https://github.com/BlueCentre/adk-python.git@feat/click-rich
#       line.

clear
(
  echo "${1:-'Tell the user to run prompt.sh script with a prompt'}"
  echo "approve"
  # sleep 2  # Allow time for agent to complete processing
  echo "exit"
) | \
  uv run agent run agents.devops
