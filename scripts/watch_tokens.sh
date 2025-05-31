#!/usr/bin/env bash
# watch_tokens.sh - Real-time token monitoring for manual testing

LOG_FILE="/var/folders/*/T/agents_log/agent.latest.log"
WATCH_LOG="/tmp/token_watch_$(date +%s).log"

echo "=== REAL-TIME TOKEN MONITORING ===" | tee "$WATCH_LOG"
echo "Start Time: $(date)" | tee -a "$WATCH_LOG"
echo "Monitoring: $LOG_FILE" | tee -a "$WATCH_LOG"
echo "Watch Log: $WATCH_LOG" | tee -a "$WATCH_LOG"
echo "" | tee -a "$WATCH_LOG"
echo "Press Ctrl+C to stop monitoring" | tee -a "$WATCH_LOG"
echo "" | tee -a "$WATCH_LOG"

# Track previous token count to detect changes
PREV_TOKENS=""

while true; do
    # Get latest token metrics
    CURRENT_METRICS=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -E "(Total Used|Token Utilization|Available for Context)" | tail -3)
    
    if [ ! -z "$CURRENT_METRICS" ]; then
        # Extract current token count
        CURRENT_TOKENS=$(echo "$CURRENT_METRICS" | grep "Total Used" | awk '{print $5}' | tr -d ',' | tail -1)
        
        # Only log if tokens changed
        if [ "$CURRENT_TOKENS" != "$PREV_TOKENS" ] && [ ! -z "$CURRENT_TOKENS" ]; then
            echo "$(date) - Token Change Detected:" | tee -a "$WATCH_LOG"
            echo "$CURRENT_METRICS" | tee -a "$WATCH_LOG"
            echo "" | tee -a "$WATCH_LOG"
            
            # Check for warnings/errors
            RECENT_LOGS=$(tail -50 "$LOG_FILE" 2>/dev/null)
            if echo "$RECENT_LOGS" | grep -q "token limit exceeded"; then
                echo "🚨 TOKEN LIMIT EXCEEDED!" | tee -a "$WATCH_LOG"
            fi
            if echo "$RECENT_LOGS" | grep -q "CRITICAL.*exceeds token limit"; then
                echo "⚠️  TOKEN LIMIT WARNING!" | tee -a "$WATCH_LOG"
            fi
            if echo "$RECENT_LOGS" | grep -q "Further Compression"; then
                echo "🔧 Context compression triggered" | tee -a "$WATCH_LOG"
            fi
            
            PREV_TOKENS="$CURRENT_TOKENS"
        fi
    fi
    
    sleep 2
done 