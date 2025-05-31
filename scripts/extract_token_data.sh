#!/usr/bin/env bash
# extract_token_data.sh - Extract token usage from agent logs

LOG_FILE="/var/folders/cr/4ch4t4hd0nd1t8tk23km89h80000gn/T/agents_log/agent.latest.log"

echo "=== TOKEN USAGE ANALYSIS FROM CAPTURED DATA ==="
echo "Extracting token data from: $LOG_FILE"
echo ""

# Extract token usage patterns
echo "Token Usage Data:"
grep -o '"prompt_token_count":[0-9]*,"prompt_tokens_details":\[{"modality":"TEXT","token_count":[0-9]*}\],"thoughts_token_count":[0-9]*,"total_token_count":[0-9]*' "$LOG_FILE" | \
while IFS= read -r line; do
    prompt_tokens=$(echo "$line" | grep -o '"prompt_token_count":[0-9]*' | cut -d':' -f2)
    total_tokens=$(echo "$line" | grep -o '"total_token_count":[0-9]*' | cut -d':' -f2)
    thoughts_tokens=$(echo "$line" | grep -o '"thoughts_token_count":[0-9]*' | cut -d':' -f2)
    
    echo "  Prompt: $prompt_tokens, Total: $total_tokens, Thoughts: $thoughts_tokens"
done

echo ""
echo "=== DETAILED ANALYSIS ==="

# Extract specific values for analysis
TURN1_PROMPT=$(grep -o '"prompt_token_count":2294' "$LOG_FILE" | head -1 | cut -d':' -f2)
TURN1_TOTAL=$(grep -o '"total_token_count":3820' "$LOG_FILE" | head -1 | cut -d':' -f2)

TURN2_PROMPT=$(grep -o '"prompt_token_count":7859' "$LOG_FILE" | head -1 | cut -d':' -f2)
TURN2_TOTAL=$(grep -o '"total_token_count":8231' "$LOG_FILE" | head -1 | cut -d':' -f2)

if [ ! -z "$TURN1_PROMPT" ] && [ ! -z "$TURN2_PROMPT" ]; then
    echo "Turn 1: Prompt=$TURN1_PROMPT, Total=$TURN1_TOTAL"
    echo "Turn 2: Prompt=$TURN2_PROMPT, Total=$TURN2_TOTAL"
    echo ""
    
    # Calculate increases
    PROMPT_INCREASE=$((TURN2_PROMPT - TURN1_PROMPT))
    PROMPT_PERCENT=$((PROMPT_INCREASE * 100 / TURN1_PROMPT))
    
    TOTAL_INCREASE=$((TURN2_TOTAL - TURN1_TOTAL))
    TOTAL_PERCENT=$((TOTAL_INCREASE * 100 / TURN1_TOTAL))
    
    echo "🚨 TOKEN ANALYSIS RESULTS:"
    echo "  Prompt Token Increase: +$PROMPT_INCREASE tokens ($PROMPT_PERCENT%)"
    echo "  Total Token Increase: +$TOTAL_INCREASE tokens ($TOTAL_PERCENT%)"
    echo ""
    
    if [ "$PROMPT_PERCENT" -gt 200 ]; then
        echo "❌ CRITICAL ISSUE: Prompt tokens increased by $PROMPT_PERCENT%!"
        echo "   This suggests input tokens are NOT being optimized between turns."
    elif [ "$PROMPT_PERCENT" -gt 100 ]; then
        echo "⚠️  WARNING: Significant prompt token increase ($PROMPT_PERCENT%)"
        echo "   Token optimization may not be working effectively."
    else
        echo "✅ Prompt token increase within reasonable range."
    fi
fi 