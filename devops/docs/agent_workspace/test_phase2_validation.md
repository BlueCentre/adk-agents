# Phase 2 Advanced Features - Validation Test Prompts

**Date:** December 23, 2024  
**Features to Test:** Smart Prioritization & Cross-turn Correlation  

## 🎯 Validation Goals

Validate that our new Phase 2 features work correctly:
1. **Smart Prioritization** - Better relevance ranking of context items
2. **Cross-turn Correlation** - Intelligent linking of related operations across turns
3. **Enhanced Context Intelligence** - Overall improvement in context quality

## 🧪 Test Sequence

### **Test 1: File-based Workflow Validation**
**Objective:** Test smart prioritization and cross-turn correlation for file operations

**Commands:**
```bash
# Step 1: Read a Python file to establish context
./prompt.sh "Please read the devops/components/context_management/smart_prioritization.py file and explain what it does"

# Step 2: Edit a related file (should show high correlation)
./prompt.sh "Now let's make a small improvement to the cross_turn_correlation.py file in the same directory"

# Step 3: Check for error handling (should prioritize error-related content)
./prompt.sh "Are there any potential error cases or edge conditions we should handle in these correlation algorithms?"
```

**Expected Behavior:**
- Smart prioritization should rank recent file operations highly
- Cross-turn correlation should link the two related files
- Context should show clear relationships between correlation modules
- Error-related content should be prioritized if any exists

### **Test 2: Configuration and Setup Context**
**Objective:** Test prioritization of high-value configuration files

**Commands:**
```bash
# Step 1: Ask about project setup
./prompt.sh "How do I configure and set up this project for development? What are the key configuration files?"

# Step 2: Ask about dependencies
./prompt.sh "What are the project's main dependencies and how should I manage them with uv?"

# Step 3: Ask about testing setup
./prompt.sh "How do I run tests for this project? Are there any testing frameworks configured?"
```

**Expected Behavior:**
- pyproject.toml should be highly prioritized (config file bonus)
- uv-related content should score highly (modern Python packaging)
- Configuration-related code snippets should rank above general code
- Cross-correlations between setup files should be detected

### **Test 3: Error Resolution Chain**
**Objective:** Test error prioritization and continuation tracking

**Commands:**
```bash
# Step 1: Introduce an intentional error
./prompt.sh "Let's try to run a command that will likely fail: python -c 'import nonexistent_module'"

# Step 2: Ask for help debugging (should prioritize error content)
./prompt.sh "That command failed. Can you help me understand what went wrong and how to fix it?"

# Step 3: Follow up with resolution (should show error continuation)
./prompt.sh "Now let's install the missing dependency using uv and try again"
```

**Expected Behavior:**
- Error content should receive high priority scores
- Cross-turn correlation should link error → debugging → resolution
- Tool sequence correlation should detect command → analysis → fix patterns
- Error continuation scoring should connect related error events

### **Test 4: Code Pattern Recognition**
**Objective:** Test content similarity and code pattern detection

**Commands:**
```bash
# Step 1: Ask about specific code patterns
./prompt.sh "Show me examples of class definitions and function definitions in this project"

# Step 2: Ask about related functionality (should correlate with step 1)
./prompt.sh "How do these classes and functions work together? What are the key relationships?"

# Step 3: Ask for improvements (should use correlated context)
./prompt.sh "Can we improve the code structure or add better error handling to these components?"
```

**Expected Behavior:**
- Code pattern recognition should identify class/function definitions
- Content similarity should rank related code snippets highly
- Cross-correlations should link functionally related code
- Context should show coherent code examples

### **Test 5: Tool Sequence Recognition**
**Objective:** Test tool operation sequence correlation

**Commands:**
```bash
# Step 1: Search for something
./prompt.sh "Search for any TODO comments or FIXME notes in the codebase"

# Step 2: Read a file that was found (should correlate with search)
./prompt.sh "Let's read one of those files and see what needs to be done"

# Step 3: Make improvements (should correlate with read operation)
./prompt.sh "Let's implement the needed changes or improvements to that file"
```

**Expected Behavior:**
- Tool sequence correlation should link search → read → edit
- Smart prioritization should rank recently accessed files highly
- Cross-correlations should connect search results to subsequent operations
- Context should maintain workflow coherence

### **Test 6: Context Intelligence Validation**
**Objective:** Overall validation of enhanced context intelligence

**Commands:**
```bash
# Step 1: Complex query requiring multiple context types
./prompt.sh "I want to understand how this project's context management system works, including the new smart prioritization and correlation features. Can you explain the architecture and implementation?"

# Step 2: Follow-up for specific details (should use correlated context)
./prompt.sh "How do the scoring algorithms work in the smart prioritization? Show me the specific calculations."

# Step 3: Implementation guidance (should prioritize relevant code)
./prompt.sh "If I wanted to add a new correlation type, what would be the best approach given the current architecture?"
```

**Expected Behavior:**
- Context should include relevant prioritized code snippets
- Cross-correlations should link related implementation details
- High-value content (config, main classes) should be prioritized
- Smart prioritization should surface the most relevant examples

## 📊 Log Analysis Instructions

After running each test, analyze the logs at:
```bash
tail -f /var/folders/cr/4ch4t4hd0nd1t8tk23km89h80000gn/T/agents_log/agent.latest.log
```

### **Look for Smart Prioritization Logs:**
```
SMART PRIORITIZATION: Ranking X code snippets...
📊 TOP 5 RANKED SNIPPETS:
  1. file.py:123 (score: 0.847)
🧠 Smart Priority Score: 0.847
  (Content: 0.65, Recency: 0.80, Error: 0.00)
```

### **Look for Cross-turn Correlation Logs:**
```
CROSS-TURN CORRELATION: Analyzing relationships between context items...
📊 CORRELATION ANALYSIS COMPLETE:
  Snippet-to-Snippet correlations: 12
  Cross-correlations (Snippet→Tool): 8
🔗 TOP CORRELATIONS:
  Snippet 1 (smart_prioritization.py): 3 correlations (max: 0.723)
```

### **Look for Enhanced Context Assembly:**
```
CONTEXT ASSEMBLY: Processing Code Snippets...
📝 Available: 15 code snippets - applying smart prioritization...
🔗 Applying cross-turn correlation analysis...
✅ INCLUDED: Code snippet 1 (1,245 tokens)
🧠 Smart Priority Score: 0.847
```

## ✅ Success Criteria

### **Token Utilization:**
- Should maintain ~1.7% token utilization
- Context should feel more relevant and coherent
- No significant performance degradation

### **Smart Prioritization:**
- Configuration files should score highly (0.7+)
- Error-related content should have high priority when relevant
- Recently accessed files should rank above old ones
- Content relevance should drive selection

### **Cross-turn Correlation:**
- File operations should show clear correlations
- Tool sequences (read→edit, search→read) should be detected
- Error→resolution chains should be linked
- Related code should be grouped together

### **Enhanced Intelligence:**
- Context should tell a coherent "story"
- Related operations should be obviously connected
- Error handling should be contextually aware
- Code examples should be functionally related

## 🚀 Expected Improvements

Based on validation results, we expect:
1. **Better Context Relevance:** More useful information in context
2. **Improved Workflow Understanding:** Clear operation sequences
3. **Enhanced Error Handling:** Better debugging context
4. **Smarter Code Selection:** More relevant code examples
5. **Maintained Performance:** No token budget degradation

---

**Validation Status:** 🔄 **READY FOR TESTING**  
**Next Step:** Execute test sequence and analyze results 