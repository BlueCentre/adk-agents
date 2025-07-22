# Per-Sub-Agent MCP Tool Loading Guide

## Overview

The Enhanced Software Engineer Agent now supports per-sub-agent MCP (Model Context Protocol) tool loading, allowing you to configure different sets of MCP tools for each sub-agent. This provides fine-grained control over tool access and enables specialized tooling for different sub-agents.

## Key Features

- **Per-Sub-Agent Configuration**: Each sub-agent can have its own MCP tool configuration
- **Hierarchical Configuration**: Combine global and sub-agent specific MCP servers
- **Server Filtering**: Include/exclude specific MCP servers per sub-agent
- **Configuration Overrides**: Customize MCP server parameters per sub-agent
- **Backward Compatibility**: Existing profiles continue to work unchanged

## Architecture

```
Global MCP Config (.agent/mcp.json)
├── Core Tools (filesystem, code_analysis, etc.)
├── Global MCP Servers (available to all sub-agents)
└── Per-Sub-Agent MCP Configs (.agent/sub-agents/*.mcp.json)
    ├── Sub-Agent Specific MCP Servers
    ├── Server Filtering & Overrides
    └── Security & Environment Policies
```

## Configuration Structure

### Global MCP Configuration
```json
// .agent/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/project"]
    },
    "memory": {
      "command": "npx", 
      "args": ["@modelcontextprotocol/server-memory"]
    }
  }
}
```

### Enhanced Agent Fallback
Enhanced agents (with names starting with `enhanced_`) automatically fall back to base agent configurations:
- `enhanced_debugging_agent` uses `debugging_agent.mcp.json`
- `enhanced_devops_agent` uses `devops_agent.mcp.json`
- `enhanced_testing_agent` uses `testing_agent.mcp.json`

This eliminates the need to duplicate configuration files for enhanced variants.

### Per-Sub-Agent MCP Configuration
```json
// .agent/sub-agents/debugging_agent.mcp.json
{
  "mcpServers": {
    "debugger": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-debugger"],
      "env": {
        "DEBUG_MODE": "1",
        "VERBOSE": "1"
      }
    },
    "profiler": {
      "command": "python",
      "args": ["-m", "profiler_mcp_server"],
      "env": {
        "PROFILER_OUTPUT_DIR": "/tmp/profiler"
      }
    }
  },
  "globalServers": ["filesystem"],
  "excludedServers": ["production-db"],
  "serverOverrides": {
    "filesystem": {
      "env": {"DEBUG_FS": "1"}
    }
  }
}
```

## Usage Examples

### 1. Basic Per-Sub-Agent Tool Loading

```python
from agents.software_engineer.tools import load_tools_for_sub_agent

# Load tools for debugging agent with per-sub-agent MCP configuration
debugging_tools = load_tools_for_sub_agent(
    profile_name='debugging',
    sub_agent_name='debugging_agent'
)

# Load tools for testing agent with per-sub-agent MCP configuration
testing_tools = load_tools_for_sub_agent(
    profile_name='testing',
    sub_agent_name='testing_agent'
)
```

### 2. Custom MCP Configuration

```python
from agents.software_engineer.tools import (
    load_tools_for_sub_agent,
    create_sub_agent_mcp_config
)

# Create custom MCP configuration for debugging agent
debugging_mcp_servers = {
    "debugger": {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-debugger"],
        "env": {"DEBUG_MODE": "1", "VERBOSE": "1"}
    },
    "profiler": {
        "command": "python",
        "args": ["-m", "profiler_mcp_server"],
        "env": {"PROFILER_OUTPUT_DIR": "/tmp/profiler"}
    }
}

create_sub_agent_mcp_config(
    sub_agent_name="debugging_agent",
    mcp_servers=debugging_mcp_servers,
    global_servers=["filesystem"],
    excluded_servers=["production-db"],
    server_overrides={
        "filesystem": {"env": {"DEBUG_FS": "1"}}
    }
)

# Load tools with the custom configuration
tools = load_tools_for_sub_agent(
    profile_name='debugging',
    sub_agent_name='debugging_agent'
)
```

### 3. Runtime Configuration

```python
# Load tools with runtime MCP configuration
custom_config = {
    'include_mcp_tools': True,
    'mcp_server_filter': ['debugger', 'profiler'],
    'include_global_servers': False,
    'server_overrides': {
        'debugger': {'env': {'CUSTOM_DEBUG': '1'}}
    }
}

tools = load_tools_for_sub_agent(
    profile_name='debugging',
    custom_config=custom_config,
    sub_agent_name='debugging_agent'
)
```

### 4. Environment-Specific Configurations

```python
import os

# Get environment
env = os.getenv('ENVIRONMENT', 'development')

if env == 'development':
    # Development: Full debugging tools
    config = {
        'include_mcp_tools': True,
        'mcp_server_filter': ['debugger', 'profiler', 'monitoring'],
        'include_global_servers': True,
        'server_overrides': {
            'debugger': {'env': {'DEBUG_LEVEL': 'verbose'}}
        }
    }
elif env == 'production':
    # Production: Minimal tools for security
    config = {
        'include_mcp_tools': True,
        'mcp_server_filter': ['monitoring'],
        'include_global_servers': False,
        'excluded_servers': ['debugger', 'profiler']
    }

tools = load_tools_for_sub_agent(
    profile_name='debugging',
    custom_config=config,
    sub_agent_name=f'debugging_agent_{env}'
)
```

## Sub-Agent Implementation

### Updating Existing Sub-Agents

```python
# agents/software_engineer/sub_agents/debugging/agent.py
from google.adk.agents import LlmAgent
from ... import config as agent_config
from ...tools import load_tools_for_sub_agent
from . import prompt

# Load tools with per-sub-agent MCP configuration
base_config = {
    'include_mcp_tools': True,
    'mcp_server_filter': ['filesystem', 'debugger', 'profiler'],
    'include_global_servers': True,
    'excluded_servers': ['production-db'],
    'server_overrides': {
        'debugger': {'env': {'DEBUG_MODE': '1'}},
        'profiler': {'args': ['--memory-profiling']}
    }
}

tools = load_tools_for_sub_agent('debugging', base_config, sub_agent_name='debugging_agent')

debugging_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="debugging_agent",
    description="Agent specialized in debugging and troubleshooting",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    tools=tools,
    output_key="debugging",
)
```

### Creating New Sub-Agents

```python
# agents/software_engineer/sub_agents/custom/agent.py
from google.adk.agents import LlmAgent
from ... import config as agent_config
from ...tools import load_tools_for_sub_agent
from . import prompt

# Custom tool configuration for specialized sub-agent
custom_config = {
    'included_categories': ['filesystem', 'code_analysis'],
    'include_mcp_tools': True,
    'mcp_server_filter': ['custom-analyzer', 'monitoring'],
    'include_global_servers': True,
    'server_overrides': {
        'custom-analyzer': {
            'env': {'ANALYSIS_DEPTH': 'deep'}
        }
    }
}

tools = load_tools_for_sub_agent('minimal', custom_config, sub_agent_name='custom_agent')

custom_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="custom_agent",
    description="Custom specialized agent",
    instruction=prompt.CUSTOM_AGENT_INSTR,
    tools=tools,
    output_key="custom",
)
```

## Configuration Management

### Listing Available MCP Servers

```python
from agents.software_engineer.tools import list_available_mcp_servers

# List all available MCP servers for a sub-agent
available_servers = list_available_mcp_servers('debugging_agent')
print(f"Global servers: {available_servers['global']}")
print(f"Sub-agent servers: {available_servers['sub_agent']}")
```

### Getting Current Configuration

```python
from agents.software_engineer.tools import get_sub_agent_mcp_config

# Get current MCP configuration for a sub-agent
config = get_sub_agent_mcp_config('debugging_agent')
print(f"MCP servers: {list(config.get('mcpServers', {}).keys())}")
print(f"Global servers: {config.get('globalServers', [])}")
print(f"Excluded servers: {config.get('excludedServers', [])}")
```

### Working with Configuration Files

```python
from agents.software_engineer.tools import SubAgentMCPConfig

# Create configuration manager
config_manager = SubAgentMCPConfig('debugging_agent')

# Load configuration
config = config_manager.load_config()

# Modify configuration
config['mcpServers']['new-server'] = {
    'command': 'python',
    'args': ['-m', 'my_server']
}

# Save configuration
config_manager.save_config(config)
```

## Security and Environment Policies

### Security Levels

The system supports different security levels for MCP tools:

```python
from agents.software_engineer.tools.sub_agent_tool_config import SecurityLevel

# Apply security policy
config = {
    'include_mcp_tools': True,
    'mcp_server_filter': ['debugger'],
    'security_level': SecurityLevel.RESTRICTED  # Applies security constraints
}
```

### Environment-Specific Policies

```python
from agents.software_engineer.tools.sub_agent_tool_config import EnvironmentType

# Get environment-specific configuration
env_config = get_environment_config(EnvironmentType.PRODUCTION)
# Automatically applies production security constraints
```

## Best Practices

### 1. Naming Conventions

- Use descriptive names for sub-agents: `debugging_agent`, `testing_agent`
- Use consistent naming for MCP servers: `debugger`, `profiler`, `test-runner`

### 2. Configuration Organization

```
.agent/
├── mcp.json                           # Global MCP servers
└── sub-agents/
    ├── debugging_agent.mcp.json       # Debugging-specific MCP tools
    ├── testing_agent.mcp.json         # Testing-specific MCP tools
    ├── devops_agent.mcp.json          # DevOps-specific MCP tools
    └── security_agent.mcp.json        # Security-specific MCP tools
```

### 3. Security Considerations

- Use `excluded_servers` to prevent access to sensitive servers
- Apply appropriate security levels for different environments
- Use `server_overrides` to customize security parameters

### 4. Performance Optimization

- Use `mcp_server_filter` to load only necessary MCP servers
- Set `include_global_servers: false` when sub-agent doesn't need global tools
- Consider caching for frequently used configurations

## Migration Guide

### From Existing Profiles

```python
# Before (existing approach)
tools = load_tools_for_sub_agent('debugging')

# After (with per-sub-agent MCP support)
tools = load_tools_for_sub_agent('debugging', sub_agent_name='debugging_agent')
```

### From Hardcoded Tool Lists

```python
# Before
tools = [
    read_file_tool,
    edit_file_tool,
    execute_shell_command_tool,
    # ... hardcoded list
]

# After
tools = load_tools_for_sub_agent('debugging', sub_agent_name='debugging_agent')
```

## Troubleshooting

### Common Issues

1. **MCP Server Not Found**
   ```
   MCP server 'debugger' not found in configuration
   ```
   **Solution**: Add the server to `.agent/sub-agents/{sub_agent_name}.mcp.json`

2. **Configuration File Not Found**
   ```
   Configuration file not found: .agent/sub-agents/debugging_agent.mcp.json
   ```
   **Solution**: Create the configuration file using `create_sub_agent_mcp_config()`

3. **Server Override Not Applied**
   ```
   Server override for 'debugger' not applied
   ```
   **Solution**: Ensure the server is in `mcp_server_filter` and not in `excluded_servers`

4. **Enhanced Agent Configuration Issues**
   ```
   Enhanced agent not loading expected MCP tools
   ```
   **Solution**: 
   - Check that base configuration file exists (e.g., `devops_agent.mcp.json` for `enhanced_devops_agent`)
   - Verify fallback logic is working by checking logs for messages like:
     ```
     INFO: Using fallback config file for enhanced_devops_agent: /path/devops_agent.mcp.json
     ```

### Debug Mode

Enable debug logging to see detailed MCP loading information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Load tools with debug information
tools = load_tools_for_sub_agent('debugging', sub_agent_name='debugging_agent')
```

## Examples and Templates

See the following files for comprehensive examples:

- `agents/software_engineer/examples/per_sub_agent_mcp_example.py`
- `agents/software_engineer/examples/selective_tool_loading_example.py`
- `agents/software_engineer/sub_agents/debugging/agent.py`

## API Reference

### Functions

- `load_tools_for_sub_agent(profile_name, custom_config, sub_agent_name)`
- `create_sub_agent_mcp_config(sub_agent_name, mcp_servers, ...)`
- `get_sub_agent_mcp_config(sub_agent_name)`
- `list_available_mcp_servers(sub_agent_name)`
- `load_sub_agent_mcp_tools(sub_agent_name, ...)`

### Classes

- `SubAgentMCPConfig`: Configuration management for sub-agent MCP tools
- `SecurityLevel`: Security policy enumeration
- `EnvironmentType`: Environment type enumeration

For detailed API documentation, see the docstrings in the respective modules. 