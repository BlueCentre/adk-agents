# Token Usage Tracking - Long Conversation Test

**Date:** December 2024  
**Feature:** Token usage tracking and optimization during extended conversations  
**Goal:** Identify issues with token optimization and potential problems when approaching max input token limits

## 🎯 Test Overview

This test simulates a long conversation while meticulously tracking token usage to identify potential issues:
1. **Token optimization failures** - input tokens not being reduced over time
2. **Max token limit problems** - behavior when approaching/exceeding token limits
3. **K8s troubleshooting scenarios** - complex scenarios that tend to hit token limits

## 📊 Token Tracking Script

Create this monitoring script to track token usage in real-time:

```bash
#!/usr/bin/env bash
# token_monitor.sh - Real-time token usage monitoring

LOG_FILE="/var/folders/*/T/agents_log/agent.latest.log"
TOKEN_LOG="/tmp/token_usage_$(date +%s).log"

echo "=== TOKEN USAGE MONITORING SESSION ===" > "$TOKEN_LOG"
echo "Start Time: $(date)" >> "$TOKEN_LOG"
echo "Session ID: token_test_$(date +%s)" >> "$TOKEN_LOG"
echo "" >> "$TOKEN_LOG"

monitor_tokens() {
    echo "Turn $1 - $(date)" >> "$TOKEN_LOG"
    
    # Extract latest token usage data
    tail -50 $LOG_FILE | grep -E "(Base Prompt Tokens|Total Context Tokens|Final prompt validation|Available for Context|Token Usage)" | tail -10 >> "$TOKEN_LOG"
    
    # Calculate and log token trends
    if [ "$1" -gt 1 ]; then
        echo "--- Token Trend Analysis ---" >> "$TOKEN_LOG"
        grep "Total Used:" "$TOKEN_LOG" | tail -2 | awk '{print $3}' | paste -sd',' | awk -F',' '{
            if ($2 && $1) {
                diff = $2 - $1
                if (diff > 0) print "INCREASE: +" diff " tokens"
                else if (diff < 0) print "DECREASE: " diff " tokens" 
                else print "STABLE: no change"
            }
        }' >> "$TOKEN_LOG"
    fi
    
    echo "---" >> "$TOKEN_LOG"
}

echo "Token monitoring started. Log file: $TOKEN_LOG"
echo "Run your conversation test, then call 'monitor_tokens <turn_number>' after each interaction"
```

## 🧪 Progressive Token Load Test

### **Phase 1: Baseline Conversation (Turns 1-5)**
Test basic conversation without hitting limits

#### Turn 1: Simple Query
```bash
./prompt.sh "What is this project about? Give me a high-level overview."
```

#### Turn 2: Code Analysis Request  
```bash
./prompt.sh "Show me the main agent implementation files and explain how they work together."
```

#### Turn 3: Configuration Details
```bash
./prompt.sh "What configuration options are available for this DevOps agent?"
```

#### Turn 4: Error Handling Review
```bash
./prompt.sh "How does error handling work throughout the codebase? Show me the key error handling patterns."
```

#### Turn 5: Context Management Deep Dive
```bash
./prompt.sh "Explain in detail how the context management system works, including token optimization strategies."
```

**Expected Token Behavior:**
- Input tokens should remain stable or decrease as context gets optimized
- Total prompt tokens should not continuously increase
- Available context capacity should be managed efficiently

### **Phase 2: Context Accumulation Test (Turns 6-12)**
Build up context to test optimization

#### Turn 6: Multiple File Analysis
```bash
./prompt.sh "Analyze the implementation of all Python files in the devops/ directory. What are the key components and how do they interact?"
```

#### Turn 7: Tool Integration Review
```bash
./prompt.sh "Go through each tool in the tools/ directory and explain what it does, how it's integrated, and any performance considerations."
```

#### Turn 8: Dependencies and Architecture
```bash
./prompt.sh "Examine the pyproject.toml, requirements, and overall project architecture. What are the main dependencies and how is the project structured?"
```

#### Turn 9: Testing Infrastructure
```bash
./prompt.sh "Look at the testing setup in tests/ directory and pytest.ini. How comprehensive is the test coverage and what testing strategies are used?"
```

#### Turn 10: Documentation Analysis
```bash
./prompt.sh "Read through all the markdown files and documentation. What's documented well and what might be missing?"
```

#### Turn 11: Configuration Management
```bash
./prompt.sh "Analyze all configuration files (.gitignore, .indexignore, config files) and explain the project's configuration strategy."
```

#### Turn 12: Integration Points
```bash
./prompt.sh "How does this agent integrate with external systems? Look for API integrations, external tool usage, and deployment configurations."
```

**Expected Token Behavior:**
- Context optimization should prevent unlimited token growth
- Input tokens should stabilize as older context gets compressed/removed
- Warning logs if approaching token limits

### **Phase 3: High-Load Scenarios (Turns 13-20)**
Test scenarios that typically hit token limits

#### Turn 13: K8s Cluster Overview
```bash
./prompt.sh "I have a Kubernetes cluster with multiple applications running. Help me understand what's deployed and the current cluster health."
```

#### Turn 14: Pod Status Investigation
```bash
./prompt.sh "Check the status of all pods across all namespaces. Identify any that are not in Running state and investigate why."
```

#### Turn 15: Resource Usage Analysis
```bash
./prompt.sh "Analyze resource usage across the cluster - CPU, memory, storage. Are there any resource constraints or inefficiencies?"
```

#### Turn 16: Service Mesh Investigation
```bash
./prompt.sh "If there's a service mesh (Istio, Linkerd) deployed, analyze its configuration and health. Check for any networking issues."
```

#### Turn 17: Multi-Application Debugging
```bash
./prompt.sh "I'm seeing issues with several applications: authentication service intermittent failures, database connectivity problems, and slow API responses. Help me troubleshoot systematically."
```

#### Turn 18: Log Analysis Request
```bash
./prompt.sh "Analyze logs from the last hour across all applications. Look for error patterns, warnings, and any correlation between issues in different services."
```

#### Turn 19: Configuration Audit
```bash
./prompt.sh "Perform a comprehensive audit of all ConfigMaps, Secrets, and environment variables across the cluster. Check for security issues and configuration drift."
```

#### Turn 20: Performance Optimization
```bash
./prompt.sh "Based on everything we've discovered, provide a comprehensive performance optimization plan for the entire cluster and applications."
```

**Expected Token Behavior:**
- System should handle large amounts of data without failing
- Token optimization should prevent exceeding max limits
- Graceful degradation if context must be heavily compressed

### **Phase 4: Stress Test (Turns 21-30)**
Push the system to its limits

#### Turn 21: Full Cluster Deep Dive
```bash
./prompt.sh "I need a complete analysis of my production Kubernetes cluster including: all workloads, networking configuration, security policies, monitoring setup, backup strategies, disaster recovery procedures, resource utilization patterns, cost optimization opportunities, compliance status, and operational procedures. Be extremely thorough."
```

#### Turn 22: Historical Analysis Request
```bash
./prompt.sh "Look at the change history for the past month across all applications and infrastructure. Correlate any changes with performance issues or incidents. Provide a detailed timeline and impact analysis."
```

#### Turn 23: Multi-Environment Comparison
```bash
./prompt.sh "Compare configurations between development, staging, and production environments. Identify any drift, security differences, or potential issues. Recommend standardization strategies."
```

#### Turn 24: Security Comprehensive Audit
```bash
./prompt.sh "Perform a complete security audit of the entire infrastructure and applications. Check for vulnerabilities, misconfigurations, exposed secrets, network security issues, RBAC problems, and compliance gaps."
```

#### Turn 25: Incident Response Simulation
```bash
./prompt.sh "Simulate a major incident where multiple services are failing. Walk through the complete incident response process including detection, investigation, mitigation, communication, and post-incident analysis."
```

**Critical Token Monitoring Points:**
- Turn 21+ should trigger aggressive context optimization
- Monitor for token limit exceeded errors
- Check if input tokens decrease despite conversation length
- Verify context compression is working

## 📋 Token Usage Analysis Script

```bash
#!/usr/bin/env bash
# analyze_token_usage.sh

TOKEN_LOG="$1"
if [ -z "$TOKEN_LOG" ]; then
    echo "Usage: $0 <token_log_file>"
    exit 1
fi

echo "=== TOKEN USAGE ANALYSIS ==="
echo "Log file: $TOKEN_LOG"
echo ""

# Extract token usage trends
echo "Token Usage Trends:"
grep -n "Total Used:" "$TOKEN_LOG" | while read line; do
    turn=$(echo "$line" | grep -o "Turn [0-9]*" | head -1)
    tokens=$(echo "$line" | awk '{print $5}' | tr -d ',')
    limit=$(echo "$line" | awk '{print $7}' | tr -d ',')
    
    if [ ! -z "$tokens" ] && [ ! -z "$limit" ]; then
        utilization=$(echo "scale=1; $tokens * 100 / $limit" | bc -l)
        echo "  $turn: $tokens tokens (${utilization}%)"
    fi
done

echo ""
echo "Context Optimization Events:"
grep -c "Further Compression" "$TOKEN_LOG" && echo "  Compression triggered"
grep -c "LOW UTILIZATION" "$TOKEN_LOG" && echo "  Low utilization warnings"
grep -c "EXCLUDED.*Exceeds available budget" "$TOKEN_LOG" && echo "  Budget exceeded events"

echo ""
echo "Error Indicators:"
grep -c "token limit exceeded" "$TOKEN_LOG" && echo "  Token limit exceeded errors"
grep -c "CRITICAL.*exceeds token limit" "$TOKEN_LOG" && echo "  Critical token limit warnings"

echo ""
echo "Max Token Usage:"
grep "Total Used:" "$TOKEN_LOG" | awk '{print $5}' | tr -d ',' | sort -n | tail -1
```

## 🚨 Success/Failure Criteria

### **Healthy Token Optimization:**
- ✅ Input tokens stabilize after initial context building (turns 1-8)
- ✅ Total token usage stays well below max limits (< 80%)
- ✅ Context compression triggers before hitting limits
- ✅ No "token limit exceeded" errors in any scenario
- ✅ Context quality maintained despite optimization

### **Token Optimization Failures:**
- ❌ Input tokens continuously increase throughout conversation
- ❌ Total tokens approach 100% of limit without optimization
- ❌ Context compression never triggers despite high usage
- ❌ Frequent "budget exceeded" warnings without resolution
- ❌ Context gets completely stripped in later turns

### **Critical Issues:**
- 🚨 Token limit exceeded errors cause conversation failure
- 🚨 Context optimization doesn't work during K8s troubleshooting
- 🚨 Input tokens never decrease even in long conversations
- 🚨 System crashes or becomes unresponsive under token pressure

## 🔍 Monitoring Commands

Run these commands during the test to monitor real-time behavior:

```bash
# Monitor token usage in real-time
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "(Total Used|Available for Context|Token Utilization)"

# Check for context optimization events
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "(Further Compression|Context Assembly|EXCLUDED)"

# Monitor for error conditions
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "(token limit exceeded|CRITICAL|ERROR)"

# Track context component breakdown
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "(INCLUDED|EXCLUDED)" | head -20
```

## 📊 Expected Results

**Healthy System Behavior:**
1. **Turns 1-5**: Token usage increases as context builds
2. **Turns 6-12**: Token optimization begins, input tokens stabilize
3. **Turns 13-20**: Heavy optimization, context compression active
4. **Turns 21+**: Aggressive optimization, older context removed

**Warning Signs:**
- Input tokens never decrease despite conversation length
- Context gets completely stripped (empty context blocks)
- Frequent compression but tokens still increase
- System unresponsive during high-token scenarios

**Critical Failures:**
- "Token limit exceeded" errors terminate conversations
- System crashes during K8s troubleshooting scenarios
- Context optimization completely fails
- Response quality severely degraded due to context loss

## 🛠️ Debugging Failed Optimization

If token optimization fails:

```bash
# Check context manager configuration
grep -A 10 "ContextManager.*initialized" /var/folders/*/T/agents_log/agent.latest.log

# Verify token counting strategy
grep "Using.*token.*counter" /var/folders/*/T/agents_log/agent.latest.log

# Check optimization triggers
grep -B 5 -A 5 "Further Compression" /var/folders/*/T/agents_log/agent.latest.log

# Analyze context component sizes
grep -A 20 "CONTEXT ASSEMBLY COMPLETE" /var/folders/*/T/agents_log/agent.latest.log | tail -1
```

This comprehensive test should reveal any issues with token optimization during longer conversations and help identify where the system might fail when approaching token limits. 