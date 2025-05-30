# Context Population Diagnostics - Validation Test

**Date:** December 2024  
**Feature:** Enhanced diagnostic logging for context management issues  
**Goal:** Validate that diagnostic logging helps identify context population problems

## 🎯 Test Overview

The context management system previously showed massive token budgets (1M+) but only 0.01-0.02% utilization with "SKIPPED: None available" messages. We added comprehensive diagnostic logging to identify why proactive context gathering fails.

## 🧪 Test Sequence

### **Test 1: Context Population Diagnostic Validation**
**Objective:** Verify enhanced diagnostic logging is working and providing useful information

**Command:**
```bash
./prompt.sh "Can you help me understand the current structure of this project? I want to see what files exist and how they're organized."
```

**Expected Diagnostic Logs to Look For:**
```
CONTEXTMANAGER CONFIGURATION LOADED
Max LLM Token Limit: 1,048,576
Available Tokens for Context: 1,047,XXX

PROACTIVE CONTEXT: Gathering project files, Git history, and documentation...
DIAGNOSTIC: Starting proactive context gathering...
DIAGNOSTIC: Current working directory: /Users/james/Workspace/gh/lab/adk-agents
DIAGNOSTIC: Workspace root: ...

DIAGNOSTIC: Proactive context keys: ['project_files', 'git_history', 'documentation']
DIAGNOSTIC: project_files: X items
DIAGNOSTIC: project_files sample: ...
```

**Context Budget Analysis to Verify:**
```
CONTEXT ASSEMBLY - TOKEN BUDGET ANALYSIS
Available Tokens for Context: 1,047,XXX
CONTEXT ASSEMBLY COMPLETE:
📊 Total Context Tokens: X,XXX
📊 Utilization: X.X%
```

### **Test 2: Context Starvation Detection**
**Objective:** Test the diagnostic logging when context gathering fails

**Command:**
```bash
# Change to a directory with no context to trigger diagnostic failures
cd /tmp && ./prompt.sh "Analyze this empty directory and tell me what development opportunities exist here"
```

**Expected Diagnostic Logs:**
```
DIAGNOSTIC: Exception during proactive context gathering: ...
DIAGNOSTIC: Proactive context gathering returned None/empty!
DIAGNOSTIC: No proactive context gathered - investigating...
DIAGNOSTIC: Checking proactive gatherer state...
```

### **Test 3: Successful Context Population Validation**
**Objective:** Verify diagnostic logging shows successful context gathering

**Command:**
```bash
./prompt.sh "I want to understand how the DevOps agent's context management works. Can you explain the architecture and show me the key components?"
```

**Expected Success Logs:**
```
PROACTIVE CONTEXT: Gathered context with X,XXX tokens
CONTEXT ASSEMBLY: Processing Code Snippets...
📝 Available: X code snippets - applying smart prioritization...
✅ INCLUDED: Code snippet 1 (X tokens)
📊 TOTAL: Included X/X code snippets (X,XXX tokens)
```

### **Test 4: Token Utilization Improvement**
**Objective:** Verify we're actually using more of the available token budget

**Command:**
```bash
./prompt.sh "Show me the most important files in this project and explain how they work together. I want a comprehensive overview of the architecture."
```

**Expected Utilization Logs:**
```
CONTEXT ASSEMBLY - FINAL SUMMARY
Total Context Tokens Used: X,XXX
Token Budget Utilization: X.X%
Context Components Included: ['core_goal', 'recent_conversation', 'relevant_code', 'recent_tool_results', ...]

TOKEN BREAKDOWN BY COMPONENT:
  relevant_code: X,XXX tokens (X%)
  recent_conversation: X,XXX tokens (X%)
  proactive_context: X,XXX tokens (X%)
```

## 📊 Success Criteria

### **Diagnostic Visibility:**
- ✅ Clear logging of proactive context gathering attempts
- ✅ Detailed breakdown of what context is available vs missing
- ✅ Workspace and environment validation logs
- ✅ Exception handling with specific error messages

### **Context Population:**
- ✅ Should see actual context being gathered (not empty)
- ✅ Token utilization should be >1% (vs previous 0.01-0.02%)
- ✅ Multiple context components should be populated
- ✅ Proactive context should include project files, git history, etc.

### **Problem Identification:**
- ✅ When context gathering fails, logs should clearly show why
- ✅ Environment issues should be logged with specific details
- ✅ Missing dependencies or permissions should be identified
- ✅ Workspace configuration problems should be highlighted

### **Performance Impact:**
- ✅ Diagnostic logging should not significantly slow down responses
- ✅ Context assembly should complete successfully
- ✅ Token budget calculations should be accurate

## 🔍 Log Analysis Commands

To monitor the diagnostic logging in real-time:

```bash
# Follow the agent logs during testing
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "(DIAGNOSTIC|PROACTIVE CONTEXT|CONTEXT ASSEMBLY|TOKEN BUDGET)"

# Check for specific diagnostic patterns
grep "DIAGNOSTIC:" /var/folders/*/T/agents_log/agent.latest.log | tail -20

# Analyze context utilization
grep "Token Budget Utilization:" /var/folders/*/T/agents_log/agent.latest.log | tail -10
```

## 🚨 Failure Indicators

**Red Flags to Watch For:**
- Still seeing "SKIPPED: None available" for all components
- Token utilization still <1%
- No proactive context being gathered
- Missing diagnostic logs entirely
- Context assembly failing silently

**If Diagnostics Fail:**
- Check if the enhanced logging code was properly deployed
- Verify the context manager is using the updated code
- Look for import errors or initialization failures
- Check file permissions and workspace accessibility 