#!/usr/bin/env bash

uv --no-cache run agent web agents/ --reload --reload_agents --session_service_uri "sqlite:///sessions.db" --host 0.0.0.0
