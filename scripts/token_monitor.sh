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

# Export the function so it can be used from other shells
export -f monitor_tokens
export TOKEN_LOG
export LOG_FILE

# If a turn number is provided, run monitoring immediately
if [ ! -z "$1" ]; then
    monitor_tokens "$1"
fi 