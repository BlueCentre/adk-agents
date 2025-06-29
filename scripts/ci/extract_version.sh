#!/bin/bash
# extract_version.sh - Extracts version from project files without requiring package installation

# Function to extract version from Python file
extract_python_version() {
    local file="$1"
    awk -F'"' '/__version__/ {print $2; exit}' "$file" 2>/dev/null | head -1
}

# Try git-based versioning first (for dynamic versioning)
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    # Check if we're on a tagged commit
    GIT_TAG=$(git describe --exact-match --tags HEAD 2>/dev/null | sed 's/^v//')
    if [ ! -z "$GIT_TAG" ]; then
        echo $GIT_TAG
        exit 0
    fi
    
    # Try to get version from most recent tag with commit info
    GIT_DESCRIBE=$(git describe --tags --always --dirty 2>/dev/null)
    if [ ! -z "$GIT_DESCRIBE" ] && [[ "$GIT_DESCRIBE" == *"v"* ]]; then
        # Clean up the version string (remove 'v' prefix, convert to PEP440 format)
        VERSION=$(echo "$GIT_DESCRIBE" | sed 's/^v//' | sed 's/-\([0-9]\+\)-g\([a-f0-9]\+\)/.\1+\2/' | sed 's/-dirty/+dirty/')
        echo $VERSION
        exit 0
    fi
fi

# Try reading from src/wrapper/adk/version.py (project-specific)
if [ -f src/wrapper/adk/version.py ]; then
    VERSION=$(extract_python_version "src/wrapper/adk/version.py")
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
fi

# Try reading from pyproject.toml first (most reliable for Poetry projects)
if [ -f pyproject.toml ]; then
    # More robust extraction using awk
    VERSION=$(awk -F'"' '/^version = / {print $2}' pyproject.toml)
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
fi

# Try reading from setup.py
if [ -f setup.py ]; then
    VERSION=$(grep -E "version\s*=\s*[\"']([^\"']+)[\"']" setup.py | head -1 | sed -E "s/.*version\s*=\s*[\"']([^\"']+)[\"'].*/\1/")
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
fi

# Try reading from package __init__.py files
for init_file in $(find . -name "__init__.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*"); do
    VERSION=$(extract_python_version "$init_file")
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
done

# Try to extract from installed package (if available)
if command -v python >/dev/null 2>&1; then
    # Try to get version from installed package
    for pkg_name in $(grep -E '^name = ' pyproject.toml 2>/dev/null | awk -F'"' '{print $2}'); do
        VERSION=$(python -c "import importlib.metadata; print(importlib.metadata.version('$pkg_name'))" 2>/dev/null)
        if [ ! -z "$VERSION" ] && [ "$VERSION" != "0.0.0" ]; then
            echo $VERSION
            exit 0
        fi
    done
fi

# Try reading package name from pyproject.toml (for fallback if version not found)
if [ -f pyproject.toml ]; then
    PACKAGE_NAME=$(awk -F'"' '/^name = / {print $2}' pyproject.toml)
    if [ ! -z "$PACKAGE_NAME" ]; then
        # Try to create a development version based on git info
        if command -v git >/dev/null 2>&1 && [ -d .git ]; then
            GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null)
            GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
            if [ ! -z "$GIT_HASH" ]; then
                echo "0.1.0.dev0+${GIT_HASH}"
                exit 0
            fi
        fi
        echo "0.1.0-$PACKAGE_NAME" # Fallback with package name as suffix
        exit 0
    fi
fi

# Ultimate fallback
echo "0.1.0"
