#!/usr/bin/env bash
# run_token_test.sh - Execute comprehensive token usage test

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_LOG="/tmp/token_test_execution_$(date +%s).log"

echo "=== TOKEN USAGE TEST EXECUTION ===" | tee "$TEST_LOG"
echo "Start Time: $(date)" | tee -a "$TEST_LOG"
echo "Project Root: $PROJECT_ROOT" | tee -a "$TEST_LOG"
echo "Test Log: $TEST_LOG" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"

# Start token monitoring
echo "Starting token monitoring..." | tee -a "$TEST_LOG"
source "$SCRIPT_DIR/token_monitor.sh"

# Test phases
PROMPTS=(
    # Phase 1: Baseline (Turns 1-5)
    "What is this project about? Give me a high-level overview."
    "Show me the main agent implementation files and explain how they work together."
    "What configuration options are available for this DevOps agent?"
    "How does error handling work throughout the codebase? Show me the key error handling patterns."
    "Explain in detail how the context management system works, including token optimization strategies."
    
    # Phase 2: Context Accumulation (Turns 6-12)
    "Analyze the implementation of all Python files in the devops/ directory. What are the key components and how do they interact?"
    "Go through each tool in the tools/ directory and explain what it does, how it's integrated, and any performance considerations."
    "Examine the pyproject.toml, requirements, and overall project architecture. What are the main dependencies and how is the project structured?"
    "Look at the testing setup in tests/ directory and pytest.ini. How comprehensive is the test coverage and what testing strategies are used?"
    "Read through all the markdown files and documentation. What's documented well and what might be missing?"
    "Analyze all configuration files (.gitignore, .indexignore, config files) and explain the project's configuration strategy."
    "How does this agent integrate with external systems? Look for API integrations, external tool usage, and deployment configurations."
    
    # Phase 3: High-Load Scenarios (Turns 13-20)
    "I have a Kubernetes cluster with multiple applications running. Help me understand what's deployed and the current cluster health."
    "Check the status of all pods across all namespaces. Identify any that are not in Running state and investigate why."
    "Analyze resource usage across the cluster - CPU, memory, storage. Are there any resource constraints or inefficiencies?"
    "If there's a service mesh (Istio, Linkerd) deployed, analyze its configuration and health. Check for any networking issues."
    "I'm seeing issues with several applications: authentication service intermittent failures, database connectivity problems, and slow API responses. Help me troubleshoot systematically."
    "Analyze logs from the last hour across all applications. Look for error patterns, warnings, and any correlation between issues in different services."
    "Perform a comprehensive audit of all ConfigMaps, Secrets, and environment variables across the cluster. Check for security issues and configuration drift."
    "Based on everything we've discovered, provide a comprehensive performance optimization plan for the entire cluster and applications."
    
    # Phase 4: Stress Test (Turns 21-25)
    "I need a complete analysis of my production Kubernetes cluster including: all workloads, networking configuration, security policies, monitoring setup, backup strategies, disaster recovery procedures, resource utilization patterns, cost optimization opportunities, compliance status, and operational procedures. Be extremely thorough."
    "Look at the change history for the past month across all applications and infrastructure. Correlate any changes with performance issues or incidents. Provide a detailed timeline and impact analysis."
    "Compare configurations between development, staging, and production environments. Identify any drift, security differences, or potential issues. Recommend standardization strategies."
    "Perform a complete security audit of the entire infrastructure and applications. Check for vulnerabilities, misconfigurations, exposed secrets, network security issues, RBAC problems, and compliance gaps."
    "Simulate a major incident where multiple services are failing. Walk through the complete incident response process including detection, investigation, mitigation, communication, and post-incident analysis."
)

# Function to run a single test turn
run_test_turn() {
    local turn_number=$1
    local prompt="$2"
    
    echo "" | tee -a "$TEST_LOG"
    echo "========================================" | tee -a "$TEST_LOG"
    echo "TURN $turn_number" | tee -a "$TEST_LOG"
    echo "========================================" | tee -a "$TEST_LOG"
    echo "Prompt: $prompt" | tee -a "$TEST_LOG"
    echo "Time: $(date)" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    
    # Run the prompt
    cd "$PROJECT_ROOT"
    echo "$prompt" | ./prompt.sh "$(cat)" 2>&1 | tee -a "$TEST_LOG"
    
    # Monitor tokens after the turn
    echo "" | tee -a "$TEST_LOG"
    echo "--- TOKEN MONITORING FOR TURN $turn_number ---" | tee -a "$TEST_LOG"
    monitor_tokens "$turn_number"
    
    # Extract key metrics from the latest log
    echo "--- TURN $turn_number METRICS ---" | tee -a "$TEST_LOG"
    tail -100 /var/folders/*/T/agents_log/agent.latest.log | grep -E "(Total Used|Available for Context|Token Utilization)" | tail -3 | tee -a "$TEST_LOG"
    
    # Check for critical issues
    if tail -50 /var/folders/*/T/agents_log/agent.latest.log | grep -q "token limit exceeded"; then
        echo "🚨 CRITICAL: Token limit exceeded detected in turn $turn_number!" | tee -a "$TEST_LOG"
    fi
    
    if tail -50 /var/folders/*/T/agents_log/agent.latest.log | grep -q "CRITICAL.*exceeds token limit"; then
        echo "⚠️  WARNING: Token limit warning detected in turn $turn_number!" | tee -a "$TEST_LOG"
    fi
    
    echo "Turn $turn_number completed at $(date)" | tee -a "$TEST_LOG"
}

# Execute the test
echo "Starting comprehensive token usage test..." | tee -a "$TEST_LOG"
echo "Total prompts to execute: ${#PROMPTS[@]}" | tee -a "$TEST_LOG"

for i in "${!PROMPTS[@]}"; do
    turn_number=$((i + 1))
    prompt="${PROMPTS[$i]}"
    
    # Phase markers
    if [ "$turn_number" -eq 1 ]; then
        echo "" | tee -a "$TEST_LOG"
        echo "🔵 PHASE 1: BASELINE CONVERSATION (Turns 1-5)" | tee -a "$TEST_LOG"
    elif [ "$turn_number" -eq 6 ]; then
        echo "" | tee -a "$TEST_LOG"
        echo "🟡 PHASE 2: CONTEXT ACCUMULATION (Turns 6-12)" | tee -a "$TEST_LOG"
    elif [ "$turn_number" -eq 13 ]; then
        echo "" | tee -a "$TEST_LOG"
        echo "🟠 PHASE 3: HIGH-LOAD SCENARIOS (Turns 13-20)" | tee -a "$TEST_LOG"
    elif [ "$turn_number" -eq 21 ]; then
        echo "" | tee -a "$TEST_LOG"
        echo "🔴 PHASE 4: STRESS TEST (Turns 21-25)" | tee -a "$TEST_LOG"
    fi
    
    run_test_turn "$turn_number" "$prompt"
    
    # Wait a moment between turns to avoid overwhelming the system
    sleep 2
    
    # Option to pause between phases for analysis
    if [ "$turn_number" -eq 5 ] || [ "$turn_number" -eq 12 ] || [ "$turn_number" -eq 20 ]; then
        echo "" | tee -a "$TEST_LOG"
        echo "End of phase $((($turn_number-1)/5 + 1)). Press Enter to continue or Ctrl+C to stop..."
        read -r
    fi
done

# Final analysis
echo "" | tee -a "$TEST_LOG"
echo "========================================" | tee -a "$TEST_LOG"
echo "TEST EXECUTION COMPLETE" | tee -a "$TEST_LOG"
echo "========================================" | tee -a "$TEST_LOG"
echo "End Time: $(date)" | tee -a "$TEST_LOG"
echo "Test Log: $TEST_LOG" | tee -a "$TEST_LOG"
echo "Token Log: $TOKEN_LOG" | tee -a "$TEST_LOG"

# Run final analysis
if [ -f "$TOKEN_LOG" ]; then
    echo "" | tee -a "$TEST_LOG"
    echo "Running token usage analysis..." | tee -a "$TEST_LOG"
    "$SCRIPT_DIR/analyze_token_usage.sh" "$TOKEN_LOG" | tee -a "$TEST_LOG"
else
    echo "⚠️  Token log not found: $TOKEN_LOG" | tee -a "$TEST_LOG"
fi

echo "" | tee -a "$TEST_LOG"
echo "=== TEST SUMMARY ===" | tee -a "$TEST_LOG"
echo "Full test log: $TEST_LOG" | tee -a "$TEST_LOG"
echo "Token usage log: $TOKEN_LOG" | tee -a "$TEST_LOG"
echo "Agent logs: /var/folders/*/T/agents_log/agent.latest.log" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"
echo "To analyze results:" | tee -a "$TEST_LOG"
echo "  ./scripts/analyze_token_usage.sh $TOKEN_LOG" | tee -a "$TEST_LOG"
echo "  grep 'CRITICAL\\|WARNING\\|ERROR' $TEST_LOG" | tee -a "$TEST_LOG"
echo "  tail -100 /var/folders/*/T/agents_log/agent.latest.log" | tee -a "$TEST_LOG" 