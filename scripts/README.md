# Scripts Directory

This directory contains utility scripts organized by purpose for the DevOps Agent project.

## 📁 Directory Structure

### 🚀 **execution/** - Agent Execution & Deployment
Scripts for running, testing, and deploying the DevOps agent:

- **`run.sh`** - Run the DevOps agent locally with standard configuration
- **`run_adk.sh`** - Run the agent with ADK-specific settings
- **`eval.sh`** - Execute evaluation tests for the agent
- **`eval_adk.sh`** - Execute ADK-specific evaluation tests
- **`prompt.sh`** - Interactive prompt testing utility
- **`prompt_adk.sh`** - ADK-specific prompt testing
- **`web_adk.sh`** - Web interface for ADK agent
- **`push.sh`** - Deployment and push automation
- **`mcp.sh`** - Model Context Protocol integration
- **`fix_rate_limits.sh`** - Rate limiting configuration and fixes
- **`groom.sh`** - Repository grooming and maintenance automation

### 📊 **monitoring/** - Telemetry & Performance
Scripts for monitoring agent performance and telemetry:

- **`telemetry_check.py`** - Telemetry system health checks and validation
- **`telemetry_dashboard.py`** - Interactive telemetry dashboard and visualization
- **`metrics_overview.py`** - Comprehensive metrics analysis and reporting
- **`metrics_status.py`** - Real-time metrics status monitoring
- **`tracing_overview.py`** - Distributed tracing analysis and insights

### ✅ **validation/** - Testing & Validation
Scripts for validating agent functionality and performance:

- **`validate_smart_prioritization_simple.py`** - Smart prioritization algorithm validation and testing

## 🔧 Usage Guidelines

### Quick Start
```bash
# Run the agent locally
./scripts/execution/run.sh

# Check telemetry status
uv run python scripts/monitoring/telemetry_check.py

# Validate smart prioritization
uv run python scripts/validation/validate_smart_prioritization_simple.py
```

### Environment Requirements
- **Python 3.13+** for Python scripts (managed via uv)
- **uv** package manager for Python dependencies and execution
- **Google API Key** set in environment variables
- **ADK dependencies** for ADK-specific scripts

### Script Dependencies
Most scripts require:
- Active virtual environment (`.venv`)
- Google API key configuration
- Project dependencies installed via `uv`

## 📋 Maintenance

### Adding New Scripts
1. Place scripts in the appropriate category directory
2. Update this README with script descriptions
3. Ensure scripts follow the project's coding standards
4. Add appropriate error handling and logging

### Script Naming Convention
- Use descriptive names indicating purpose
- Use `.sh` extension for shell scripts
- Use `.py` extension for Python scripts
- Prefix with category when ambiguous (e.g., `monitoring_dashboard.py`)

---

**Last Updated**: December 2024  
**Organization**: Scripts organized by purpose for better maintainability 