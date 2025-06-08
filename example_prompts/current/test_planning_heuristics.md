# Planning Heuristics Precision - Validation Test

**Date:** December 2024  
**Feature:** Refined interactive planning heuristics to reduce false positives  
**Goal:** Verify that simple exploration tasks proceed without unnecessary planning friction

## 🎯 Test Overview

Previously, the planning system triggered on simple requests like "read file X then Y", creating unnecessary friction. We implemented sophisticated pattern recognition to distinguish between exploration and implementation complexity.

## 🧪 Test Sequence

### **Test 1: Simple Exploration Tasks (Should NOT Trigger Planning)**
**Objective:** Verify these simple tasks proceed directly without planning prompts

#### Test 1.1: File Reading
```bash
./prompt.sh "Read the agents/devops/devops_agent.py file and tell me what it does"
```
**Expected:** Direct file reading, no planning prompt

#### Test 1.2: Directory Listing  
```bash
./prompt.sh "List the contents of the agents/devops/components directory"
```
**Expected:** Direct listing, no planning prompt

#### Test 1.3: Code Search
```bash
./prompt.sh "Search for any TODO comments in the codebase"
```
**Expected:** Direct search execution, no planning prompt

#### Test 1.4: Status Check
```bash
./prompt.sh "Check the status of the git repository"
```
**Expected:** Direct git status, no planning prompt

#### Test 1.5: Simple Explanation
```bash
./prompt.sh "Explain what the context_manager.py file does"
```
**Expected:** Direct explanation, no planning prompt

### **Test 2: Complex Implementation Tasks (Should Trigger Planning)**
**Objective:** Verify these complex tasks properly trigger planning

#### Test 2.1: Multi-step Implementation
```bash
./prompt.sh "Implement a new caching mechanism for the context manager and then add comprehensive tests for it"
```
**Expected:** Planning prompt with structured plan

#### Test 2.2: Refactoring Request
```bash
./prompt.sh "Refactor the entire planning system to support custom heuristics and add configuration options"
```
**Expected:** Planning prompt with refactoring plan

#### Test 2.3: Migration Task
```bash
./prompt.sh "Migrate the tool discovery system from static definitions to a plugin-based architecture"
```
**Expected:** Planning prompt with migration plan

#### Test 2.4: Build and Deploy
```bash
./prompt.sh "Create a new Docker deployment configuration and then set up automated testing for it"
```
**Expected:** Planning prompt with deployment plan

### **Test 3: Edge Cases and Ambiguous Requests**
**Objective:** Test borderline cases to verify heuristic precision

#### Test 3.1: Sequential Read Operations (Should NOT Trigger)
```bash
./prompt.sh "Read the prompt.sh file then read the README.md file and compare them"
```
**Expected:** Direct execution, no planning (this is exploration)

#### Test 3.2: Analysis Then Action (Should Trigger)
```bash
./prompt.sh "Analyze the current error handling patterns then implement improved error handling across the codebase"
```
**Expected:** Planning prompt (analysis + implementation)

#### Test 3.3: Simple Then Complex (Should Trigger)
```bash
./prompt.sh "Check what Python packages are installed then upgrade the project to use the latest dependency management best practices"
```
**Expected:** Planning prompt (starts simple but becomes complex)

#### Test 3.4: Multiple Deliverables (Should Trigger)
```bash
./prompt.sh "Create a comprehensive analysis report and implementation plan for improving the agent's performance"
```
**Expected:** Planning prompt (multiple deliverables)

### **Test 4: Plan-Related Feedback Handling**
**Objective:** Test plan feedback vs new request detection

#### Test 4.1: Plan Approval
```bash
# First trigger planning with a complex request
./prompt.sh "Implement comprehensive logging across the entire agent system and add monitoring dashboards"

# Then approve the plan
./prompt.sh "approve"
```
**Expected:** First triggers planning, second approves and starts execution

#### Test 4.2: Plan Modification
```bash
# First trigger planning
./prompt.sh "Refactor the context management system to support multiple context sources"

# Then provide feedback
./prompt.sh "Make the plan shorter and focus only on the core context manager changes"
```
**Expected:** First triggers planning, second recognized as plan feedback

#### Test 4.3: New Request After Plan
```bash
# First trigger planning
./prompt.sh "Create a new authentication system for the agent"

# Then ask completely different question
./prompt.sh "What's the current time?"
```
**Expected:** First triggers planning, second recognized as new request

## 📊 Expected Log Patterns

### **For Simple Exploration (No Planning):**
```
PlanningManager: Simple exploration detected (read\s+.*file), skipping planning.
PlanningManager: No complex task patterns detected, proceeding without planning.
```

### **For Complex Implementation (Planning Triggered):**
```
PlanningManager: Complex implementation task detected, triggering planning.
PlanningManager: Multi-step implementation task detected (indicators: [...], verbs: [...]), triggering planning.
PlanningManager: Heuristic triggered. Preparing for plan generation.
```

### **For Plan Feedback:**
```
PlanningManager: User approved the plan.
PlanningManager: User provided feedback on the plan. Resetting planning state.
PlanningManager: User message appears to be a new request, not plan feedback.
```

## 📈 Success Criteria

### **Precision Metrics:**
- ✅ Simple exploration tasks (Tests 1.1-1.5): 0% planning trigger rate
- ✅ Complex implementation tasks (Tests 2.1-2.4): 100% planning trigger rate  
- ✅ Edge cases (Tests 3.1-3.4): Correct classification based on complexity
- ✅ Plan feedback (Tests 4.1-4.3): Proper feedback vs new request detection

### **User Experience:**
- ✅ No unnecessary friction for simple tasks
- ✅ Helpful planning for genuinely complex requests
- ✅ Smooth plan approval/feedback workflow
- ✅ Quick task execution for exploration

### **Pattern Recognition:**
- ✅ Exploration patterns correctly detected
- ✅ Implementation patterns correctly identified
- ✅ Multi-step sequences properly classified
- ✅ Plan feedback accurately distinguished from new requests

## 🔍 Log Analysis Commands

```bash
# Monitor planning decisions
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "PlanningManager:"

# Check planning trigger patterns
grep "PlanningManager.*detected" /var/folders/*/T/agents_log/agent.latest.log | tail -20

# Analyze planning state changes
grep "PlanningManager.*state" /var/folders/*/T/agents_log/agent.latest.log | tail -10
```

## 🚨 Failure Indicators

**False Positives (Bad):**
- Simple file reading triggers planning
- Basic git status checks require plans
- Directory listings prompt for planning
- Quick explanations need approval

**False Negatives (Bad):**
- Complex refactoring requests proceed without planning
- Multi-step implementation starts immediately
- Large migration tasks skip planning
- Multiple deliverable requests bypass planning

**Edge Case Failures:**
- Sequential simple operations trigger planning
- Ambiguous requests misclassified
- Plan feedback treated as new requests
- New requests treated as plan feedback

## 🛠️ Troubleshooting

If tests fail:

1. **Check Pattern Matching:**
   ```bash
   grep "exploration detected" /var/folders/*/T/agents_log/agent.latest.log
   grep "implementation task detected" /var/folders/*/T/agents_log/agent.latest.log
   ```

2. **Verify Heuristic Updates:**
   - Ensure `planning_manager.py` has the updated `_should_trigger_heuristic` method
   - Check that regex patterns are working correctly
   - Validate keyword detection logic

3. **Test Plan Feedback Logic:**
   ```bash
   grep "_is_plan_related_feedback" /var/folders/*/T/agents_log/agent.latest.log
   ``` 