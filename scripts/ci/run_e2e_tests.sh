#!/bin/bash

# End-to-End Test Runner Script
# This script runs the comprehensive e2e test suite for the ADK agents project

set -euo pipefail  # Exit on errors, undefined vars, and pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting E2E test suite..."
log_info "Project root: $PROJECT_ROOT"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    log_error "uv is not installed or not in PATH"
    exit 1
fi

# Check if we're in a virtual environment or if dependencies are installed
log_info "Installing/checking dependencies..."
uv sync --all-extras --dev

# Create test-reports directory if it doesn't exist
mkdir -p test-reports
mkdir -p logs

# Run the organized CLI tests
log_info "Running organized CLI end-to-end tests..."

# Run CLI tests with verbose output and JUnit XML reporting
log_info "Running CLI tests in tests/e2e/cli/..."
uv run pytest tests/e2e/cli/ \
    -v \
    --tb=short \
    --junitxml=test-reports/cli-e2e-results.xml \
    --durations=10 \
    --color=yes

if [ $? -eq 0 ]; then
    log_success "CLI e2e tests passed!"
else
    log_error "CLI e2e tests failed!"
    exit 1
fi

# Run any other e2e tests that exist
log_info "Running other e2e tests..."
if find tests/e2e -name "test_*.py" ! -path "tests/e2e/cli/*" | grep -q .; then
    log_info "Found additional e2e tests, running them..."
    uv run pytest tests/e2e/ \
        --ignore=tests/e2e/cli \
        -v \
        --tb=short \
        --junitxml=test-reports/other-e2e-results.xml \
        --durations=10 \
        --color=yes

    if [ $? -eq 0 ]; then
        log_success "Additional e2e tests passed!"
    else
        log_error "Additional e2e tests failed!"
        exit 1
    fi
else
    log_info "No additional e2e tests found outside of CLI tests"
fi

# Generate a summary
log_info "E2E Test Summary:"
log_success "✅ CLI tests completed successfully"

if [ -d "test-reports" ] && [ "$(ls -A test-reports)" ]; then
    log_info "Test reports generated in: test-reports/"
    ls -la test-reports/
fi

log_success "All E2E tests completed successfully! 🎉"
