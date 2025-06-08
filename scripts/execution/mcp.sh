#!/usr/bin/env bash


#  NOTE: Comments will not work in mcp.json!
#  https://modelcontextprotocol.io/tutorials/building-mcp-with-llms
#  MCP LLM:
#     "mcp-docs": {
#       "url": "https://modelcontextprotocol.io/llms-full.txt"
#     },
#  Agent Prompt:
#  Build an MCP server that:
#  - Connects to my company's PostgreSQL database
#  - Exposes table schemas as resources
#  - Provides tools for running read-only SQL queries
#  - Includes prompts for common data analysis tasks

#  https://modelcontextprotocol.io/docs/tools/inspector#npm-package
#  MCP Inspect:
#  npx -y @modelcontextprotocol/inspector
#  npx -y @modelcontextprotocol/inspector rust-mcp-filesystem --allow-write /tmp
#  npx -y @modelcontextprotocol/inspector npx @modelcontextprotocol/server-filesystem /tmp
#  npx -y @modelcontextprotocol/inspector npx @winor30/mcp-server-datadog
#  npx -y @modelcontextprotocol/inspector -e DATADOG_API_KEY=$DATADOG_API_KEY -e DATADOG_APP_KEY=$DATADOG_APP_KEY --config mcp.json --server datadog

#  https://github.com/f/mcptools
#  MCP CLI:
#  brew tap f/mcptools
#  brew install mcp
#  go install github.com/f/mcptools/cmd/mcptools@latest
#  mcp tools npx -y @modelcontextprotocol/server-filesystem ~
#  mcp call read_file --params '{"path":"README.md"}' npx -y @modelcontextprotocol/server-filesystem ~
#  mcp shell npx -y @modelcontextprotocol/server-filesystem ~

#npx -y @modelcontextprotocol/inspector -e DATADOG_API_KEY=$DATADOG_API_KEY -e DATADOG_APP_KEY=$DATADOG_APP_KEY --config .agent/mcp.json.example --server datadog
#npx -y @modelcontextprotocol/inspector uvx mcp-atlassian --confluence-url=$CONFLUENCE_URL --confluence-username=$CONFLUENCE_USERNAME --confluence-token=$CONFLUENCE_TOKEN --jira-url=$JIRA_URL --jira-username=$JIRA_USERNAME --jira-token=$JIRA_TOKEN
