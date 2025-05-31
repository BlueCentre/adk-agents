#!/usr/bin/env bash
# quick_token_test.sh - Quick token usage test (10 turns)

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_LOG="/tmp/quick_token_test_$(date +%s).log"

echo "=== QUICK TOKEN USAGE TEST ===" | tee "$TEST_LOG"
echo "Start Time: $(date)" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"

# Start token monitoring
source "$SCRIPT_DIR/token_monitor.sh"

# Quick test prompts - focused on token growth
PROMPTS=(
    "What is this project about?"
    "Show me the main agent implementation files."
    "Analyze all Python files in the devops/ directory."
    "Go through each tool and explain what it does."
    "Read through all documentation files."
    "Analyze the project's dependencies and architecture."
    "I have a Kubernetes cluster with multiple applications. Help me understand what's deployed."
    "Check the status of all pods and investigate any issues."
    "Analyze resource usage and look for constraints."
    "Provide a comprehensive performance optimization plan for the entire cluster."
)

echo "Starting quick token test (${#PROMPTS[@]} turns)..." | tee -a "$TEST_LOG"

for i in "${!PROMPTS[@]}"; do
    turn_number=$((i + 1))
    prompt="${PROMPTS[$i]}"
    
    echo "" | tee -a "$TEST_LOG"
    echo "=== TURN $turn_number ===" | tee -a "$TEST_LOG"
    echo "Prompt: $prompt" | tee -a "$TEST_LOG"
    echo "Time: $(date)" | tee -a "$TEST_LOG"
    
    # Run the prompt
    cd "$PROJECT_ROOT"
    echo "$prompt" | timeout 300 ./prompt.sh "$(cat)" 2>&1 | tee -a "$TEST_LOG" || echo "Turn $turn_number timed out or failed" | tee -a "$TEST_LOG"
    
    # Monitor tokens
    monitor_tokens "$turn_number"
    
    # Quick metrics check
    echo "--- Turn $turn_number Token Metrics ---" | tee -a "$TEST_LOG"
    tail -50 /var/folders/*/T/agents_log/agent.latest.log | grep -E "(Total Used|Token Utilization)" | tail -2 | tee -a "$TEST_LOG"
    
    # Check for issues
    if tail -30 /var/folders/*/T/agents_log/agent.latest.log | grep -q "token limit exceeded"; then
        echo "🚨 Token limit exceeded in turn $turn_number!" | tee -a "$TEST_LOG"
    fi
    
    sleep 1
done

echo "" | tee -a "$TEST_LOG"
echo "=== QUICK TEST COMPLETE ===" | tee -a "$TEST_LOG"
echo "End Time: $(date)" | tee -a "$TEST_LOG"

# Quick analysis
if [ -f "$TOKEN_LOG" ]; then
    echo "" | tee -a "$TEST_LOG"
    echo "=== QUICK ANALYSIS ===" | tee -a "$TEST_LOG"
    "$SCRIPT_DIR/analyze_token_usage.sh" "$TOKEN_LOG" | tee -a "$TEST_LOG"
fi

echo "" | tee -a "$TEST_LOG"
echo "Test log: $TEST_LOG" | tee -a "$TEST_LOG"
echo "Token log: $TOKEN_LOG" | tee -a "$TEST_LOG" 