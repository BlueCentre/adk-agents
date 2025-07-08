#!/usr/bin/env bash

uv run --no-cache adk api_server --allow_origins=http://james-macbook-pro:4200 --host 0.0.0.0 --session_db_url "sqlite:///sessions.db" ./agents
