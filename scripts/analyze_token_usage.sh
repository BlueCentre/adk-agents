#!/usr/bin/env bash
# analyze_token_usage.sh - Analyze token usage patterns from logs

TOKEN_LOG="$1"
if [ -z "$TOKEN_LOG" ]; then
    echo "Usage: $0 <token_log_file>"
    echo "Available token logs:"
    ls -la /tmp/token_usage_*.log 2>/dev/null || echo "  No token logs found"
    exit 1
fi

if [ ! -f "$TOKEN_LOG" ]; then
    echo "Error: Token log file '$TOKEN_LOG' not found"
    exit 1
fi

echo "=== TOKEN USAGE ANALYSIS ==="
echo "Log file: $TOKEN_LOG"
echo "Analysis time: $(date)"
echo ""

# Extract basic session info
echo "Session Information:"
head -5 "$TOKEN_LOG"
echo ""

# Extract token usage trends
echo "Token Usage Trends:"
grep -n "Total Used:" "$TOKEN_LOG" | while read line; do
    turn=$(echo "$line" | grep -o "Turn [0-9]*" | head -1)
    tokens=$(echo "$line" | awk '{print $5}' | tr -d ',')
    limit=$(echo "$line" | awk '{print $7}' | tr -d ',')
    
    if [ ! -z "$tokens" ] && [ ! -z "$limit" ]; then
        utilization=$(echo "scale=1; $tokens * 100 / $limit" | bc -l 2>/dev/null || echo "N/A")
        echo "  $turn: $tokens tokens (${utilization}%)"
    fi
done

echo ""
echo "Token Trend Summary:"
trend_count=$(grep -c "INCREASE:" "$TOKEN_LOG")
decrease_count=$(grep -c "DECREASE:" "$TOKEN_LOG")
stable_count=$(grep -c "STABLE:" "$TOKEN_LOG")
echo "  Increases: $trend_count"
echo "  Decreases: $decrease_count"  
echo "  Stable: $stable_count"

echo ""
echo "Context Optimization Events:"
compression_count=$(grep -c "Further Compression" "$TOKEN_LOG")
low_util_count=$(grep -c "LOW UTILIZATION" "$TOKEN_LOG")
budget_exceed_count=$(grep -c "EXCLUDED.*Exceeds available budget" "$TOKEN_LOG")

echo "  Compression triggered: $compression_count times"
echo "  Low utilization warnings: $low_util_count times"
echo "  Budget exceeded events: $budget_exceed_count times"

echo ""
echo "Error Indicators:"
limit_exceeded_count=$(grep -c "token limit exceeded" "$TOKEN_LOG")
critical_count=$(grep -c "CRITICAL.*exceeds token limit" "$TOKEN_LOG")

echo "  Token limit exceeded errors: $limit_exceeded_count"
echo "  Critical token limit warnings: $critical_count"

echo ""
echo "Peak Token Usage:"
max_tokens=$(grep "Total Used:" "$TOKEN_LOG" | awk '{print $5}' | tr -d ',' | sort -n | tail -1)
echo "  Maximum tokens used: $max_tokens"

# Look for optimization failure patterns
echo ""
echo "Optimization Health Check:"
if [ "$decrease_count" -eq 0 ] && [ "$trend_count" -gt 5 ]; then
    echo "  ⚠️  WARNING: No token decreases detected despite $trend_count increases"
    echo "  This suggests token optimization may not be working properly"
elif [ "$decrease_count" -gt 0 ]; then
    echo "  ✅ Token optimization appears to be working ($decrease_count decreases detected)"
fi

if [ "$critical_count" -gt 0 ] || [ "$limit_exceeded_count" -gt 0 ]; then
    echo "  🚨 CRITICAL: Token limit issues detected!"
    echo "  Review the logs for token limit exceeded errors"
fi

echo ""
echo "Detailed Token Flow:"
grep -E "(INCREASE:|DECREASE:|STABLE:)" "$TOKEN_LOG" | head -10

echo ""
echo "=== ANALYSIS COMPLETE ===" 