#!/usr/bin/env bash

uv --no-cache run agent api_server --reload_agents --allow_origins=http://james-macbook-pro:4200 --host 0.0.0.0 --session_db_url "sqlite:///sessions.db" ./agents
