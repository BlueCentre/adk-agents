# uv Best Practices Guide

This document outlines the comprehensive best practices for using `uv` consistently across the entire adk-agents project.

## 🎯 Core Principle

**Use `uv` for ALL Python-related operations** - This ensures complete consistency across development, testing, and deployment environments.

## 📋 Command Reference

### Package Management
```bash
# ✅ Install dependencies
uv sync --dev

# ✅ Add new dependencies
uv add package-name
uv add --dev pytest-package  # Development dependencies

# ✅ Remove dependencies
uv remove package-name

# ✅ List installed packages
uv pip list

# ✅ Install project in development mode
uv pip install -e .
```

### Python Execution
```bash
# ✅ Run Python scripts
uv run python script.py

# ✅ Run Python modules
uv run python -m module.name

# ✅ Interactive Python shell
uv run python

# ✅ Run one-liners
uv run python -c "import sys; print(sys.version)"
```

### Testing
```bash
# ✅ Run all tests
uv run pytest

# ✅ Run specific test files
uv run pytest tests/unit/test_file.py

# ✅ Run with coverage
uv run pytest --cov=src --cov-report=html

# ✅ Run integration tests
uv run pytest tests/integration/ -m integration
```

### Development Tools
```bash
# ✅ Code formatting
uv run pyink .
uv run isort .

# ✅ Type checking
uv run mypy src/

# ✅ Linting
uv run pylint src/
uv run ruff check src/

# ✅ Security scanning
uv run bandit -r src/
```

## 🚫 What NOT to Do

### ❌ Avoid Direct Python Commands
```bash
# ❌ Don't use these
python script.py
python -m module
pytest
pip install package
```

### ❌ Avoid System Package Managers
```bash
# ❌ Don't use these
pip install package
pip3 install package
conda install package
```

## 📁 File-Specific Guidelines

### Shell Scripts (*.sh)
```bash
# ✅ Use uv run for Python execution
uv run python scripts/monitoring/telemetry_check.py

# ✅ Use uv for package management
uv add --dev pytest-package
```

### Documentation (*.md)
```markdown
# ✅ In code examples
```bash
uv run python script.py
uv run pytest tests/
```

# ✅ In installation instructions
```bash
uv sync --dev
uv pip install -e .
```
```

### Python Files (*.py)
```python
# ✅ For subprocess calls
import subprocess
result = subprocess.run(['uv', 'run', 'python', '--version'], capture_output=True, text=True)

# ✅ Fallback pattern for compatibility
try:
    python_version = subprocess.check_output(['uv', 'run', 'python', '--version'], 
                                           stderr=subprocess.STDOUT, text=True).strip()
except (subprocess.CalledProcessError, FileNotFoundError):
    # Fallback to system python if uv is not available
    try:
        python_version = subprocess.check_output(['python3', '--version'], 
                                               stderr=subprocess.STDOUT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        python_version = subprocess.check_output(['python', '--version'], 
                                               stderr=subprocess.STDOUT, text=True).strip()
```

### CI/CD Workflows (*.yml)
```yaml
# ✅ Use uv run for test execution
- name: Run tests
  run: uv run pytest tests/

# ✅ Use uv for package management
- name: Install dependencies
  run: uv sync --dev

# ✅ Use uv pip for special cases
- name: Install build tools
  run: uv pip install build wheel setuptools
```

## 🔧 Environment Setup

### Project Initialization
```bash
# ✅ Initialize new project
uv init

# ✅ Sync dependencies
uv sync --dev

# ✅ Verify setup
uv run python --version
```

### Development Environment
```bash
# ✅ Check Python version
uv run python --version

# ✅ Verify virtual environment
uv run which python  # Should show .venv/bin/python

# ✅ Check installed packages
uv pip list
```

## 🎯 Special Cases

### Virtual Environment Creation
```bash
# ✅ For troubleshooting isolated environments
python -m venv test_env  # OK - Creating new env from outside project
source test_env/bin/activate
uv sync --dev  # Use uv once inside the environment
```

### System Python Checks
```bash
# ✅ For system comparison
which python  # OK - Checking system Python location
uv run which python  # Compare with project Python
```

### Legacy Scripts
```bash
# ✅ Migration pattern
# Old: python script.py
# New: uv run python script.py

# ✅ Subprocess migration
# Old: subprocess.run(['python', 'script.py'])
# New: subprocess.run(['uv', 'run', 'python', 'script.py'])
```

## 📊 Benefits of Consistent uv Usage

### ✅ Reproducible Environments
- Same Python version across all environments
- Consistent package versions
- Isolated dependencies

### ✅ Better Performance
- Faster package installation
- Optimized dependency resolution
- Reduced environment conflicts

### ✅ Enhanced Security
- Locked dependency versions
- Vulnerability scanning
- Isolated execution environments

### ✅ Developer Experience
- Single tool for all Python operations
- Clear dependency management
- Consistent workflows

## 🔍 Verification Commands

### Check uv Usage
```bash
# Check if all Python commands use uv
grep -r "python " --include="*.sh" --include="*.md" scripts/ docs/
grep -r "pytest " --include="*.sh" --include="*.md" scripts/ docs/
grep -r "pip install" --include="*.sh" --include="*.md" scripts/ docs/
```

### Verify Environment Consistency
```bash
# Check Python versions
python --version
uv run python --version

# Check installed packages
pip list | head -5
uv pip list | head -5

# Check virtual environment
which python
uv run which python
```

## 📋 Migration Checklist

### For New Team Members
- [ ] Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Clone repository: `git clone <repo-url>`
- [ ] Install dependencies: `uv sync --dev`
- [ ] Verify setup: `uv run python --version`
- [ ] Run tests: `uv run pytest`

### For Existing Projects
- [ ] Update all shell scripts to use `uv run`
- [ ] Update all documentation examples
- [ ] Update CI/CD pipelines
- [ ] Update Python subprocess calls
- [ ] Test all workflows with uv

### For Documentation
- [ ] Update installation instructions
- [ ] Update development setup guides
- [ ] Update testing instructions
- [ ] Update troubleshooting guides
- [ ] Add uv best practices section

## 🎯 Common Patterns

### Script Headers
```bash
#!/bin/bash
# Example script using uv best practices

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is required but not installed"
    exit 1
fi

# Run Python with uv
uv run python script.py
```

### Python Module Templates
```python
"""
Example Python module using uv best practices
"""
import subprocess
import sys

def run_with_uv(command):
    """Run a command with uv run prefix"""
    return subprocess.run(['uv', 'run'] + command, 
                         capture_output=True, text=True)

def check_python_version():
    """Check Python version using uv"""
    result = run_with_uv(['python', '--version'])
    return result.stdout.strip()
```

## 🔧 Troubleshooting

### Common Issues

#### uv not found
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

#### Wrong Python version
```bash
# Check uv Python version
uv run python --version

# Sync dependencies
uv sync --dev
```

#### Package conflicts
```bash
# Clear cache and reinstall
rm -rf .venv
uv sync --dev
```

### Environment Debugging
```bash
# Check uv installation
which uv
uv --version

# Check Python installation
uv run python --version
uv run which python

# Check virtual environment
ls -la .venv/
```

---

**Remember**: Consistency is key! Always use `uv` for all Python operations across the entire project. 