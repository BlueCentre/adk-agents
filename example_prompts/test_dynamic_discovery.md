# Dynamic Tool Discovery - Validation Test

**Date:** December 2024  
**Feature:** Dynamic environment capability discovery framework  
**Goal:** Validate that the agent can discover and adapt to available DevOps tools

## 🎯 Test Overview

We created a dynamic discovery framework that scans the environment for available tools and adapts recommendations based on what's actually installed. This replaces static tool definitions with real-time capability detection.

## 🧪 Test Sequence

### **Test 1: Environment Capability Discovery**
**Objective:** Verify the dynamic discovery system can detect available tools

**Command:**
```bash
./prompt.sh "What DevOps tools are available in this environment? Can you show me a summary of the environment capabilities?"
```

**Expected Response Should Include:**
- List of detected tools with versions
- Shell and OS information
- Available package managers
- Tool availability status (✅/❌)

**Expected Logs:**
```
DISCOVERY: Starting environment capability discovery...
DISCOVERY: ✅ git v2.49.0 available at /usr/bin/git
DISCOVERY: ✅ docker v28.1.1 available at /usr/local/bin/docker
DISCOVERY: ❌ kubectl not available
DISCOVERY: Environment discovery complete. Found X available tools.
```

### **Test 2: Tool-Specific Capability Detection**
**Objective:** Test detection of specific tool capabilities and common commands

**Command:**
```bash
./prompt.sh "I want to work with Git. What Git capabilities do you detect in this environment and what common operations can I perform?"
```

**Expected Response:**
- Git version and installation path
- List of common Git commands available
- Specific capabilities based on version

### **Test 3: Task-Based Tool Suggestions**
**Objective:** Verify the system can suggest appropriate tools for specific tasks

#### Test 3.1: Container Task
```bash
./prompt.sh "I need to containerize an application. What tools do you recommend based on what's available in this environment?"
```
**Expected:** Should suggest Docker (if available) or provide alternatives

#### Test 3.2: Kubernetes Task
```bash
./prompt.sh "I want to deploy to Kubernetes. What tools are available for K8s management?"
```
**Expected:** Should check for kubectl, helm, and suggest based on availability

#### Test 3.3: Infrastructure Task
```bash
./prompt.sh "I need to manage cloud infrastructure. What infrastructure-as-code tools are available?"
```
**Expected:** Should check for terraform, ansible, cloud CLIs

### **Test 4: Dynamic Adaptation**
**Objective:** Test that the agent adapts its behavior based on discovered tools

**Command:**
```bash
./prompt.sh "I want to check the status of my application deployment. What tools should I use and how, based on what's available in this environment?"
```

**Expected Behavior:**
- Should only suggest tools that are actually available
- Should provide specific commands using detected tool versions
- Should offer alternatives if preferred tools aren't available

### **Test 5: Missing Tool Guidance**
**Objective:** Test handling when required tools are not available

**Command:**
```bash
./prompt.sh "I want to manage Kubernetes clusters but I don't have kubectl installed. What should I do?"
```

**Expected Response:**
- Should detect kubectl is missing
- Should provide installation guidance
- Should suggest alternatives if any exist

### **Test 6: Tool Version Awareness**
**Objective:** Verify the system can provide version-specific guidance

**Command:**
```bash
./prompt.sh "I want to use advanced Docker features. What capabilities are available based on my Docker version?"
```

**Expected Response:**
- Should reference the specific detected Docker version
- Should provide version-appropriate feature recommendations
- Should warn about version limitations if applicable

## 📊 Expected Discovery Results

Based on the test environment, we should see:

### **Likely Available Tools:**
- ✅ git (version control)
- ✅ uv (Python package manager)
- ✅ python3 (runtime)

### **Possibly Available Tools:**
- ✅ docker (if Docker Desktop installed)
- ✅ gh (GitHub CLI)
- ✅ gcloud (Google Cloud SDK)

### **Likely Unavailable Tools:**
- ❌ kubectl (Kubernetes CLI)
- ❌ terraform (Infrastructure as Code)
- ❌ ansible (Configuration management)
- ❌ helm (Kubernetes package manager)

## 📋 Integration Test

**Command:**
```bash
./prompt.sh "I'm starting a new Python project that will be deployed to the cloud. Based on the tools available in this environment, what's the recommended development and deployment workflow?"
```

**Expected Comprehensive Response:**
1. **Environment Analysis:** What tools were detected
2. **Workflow Recommendations:** Based on available tools
3. **Missing Tool Suggestions:** What should be installed
4. **Specific Commands:** Using detected tool versions
5. **Alternative Approaches:** If preferred tools unavailable

## 📈 Success Criteria

### **Discovery Accuracy:**
- ✅ Correctly identifies installed vs missing tools
- ✅ Accurately reports tool versions
- ✅ Provides correct installation paths
- ✅ Detects common commands for each tool

### **Adaptive Behavior:**
- ✅ Suggests only available tools
- ✅ Provides version-appropriate guidance
- ✅ Offers alternatives for missing tools
- ✅ Adapts workflows to environment constraints

### **User Experience:**
- ✅ Clear indication of what's available vs missing
- ✅ Helpful installation guidance for missing tools
- ✅ Practical commands using detected tools
- ✅ Realistic workflow recommendations

## 🔍 Log Analysis Commands

```bash
# Monitor tool discovery
tail -f /var/folders/*/T/agents_log/agent.latest.log | grep -E "DISCOVERY:"

# Check specific tool detection
grep "available at" /var/folders/*/T/agents_log/agent.latest.log | tail -20

# Analyze tool suggestions
grep "suggest.*tool" /var/folders/*/T/agents_log/agent.latest.log | tail -10
```

## 🔧 Manual Discovery Validation

You can also manually test the discovery system:

```bash
# Test the discovery module directly
python3 -c "
from devops.tools.dynamic_discovery import tool_discovery
capabilities = tool_discovery.discover_environment_capabilities()
print(tool_discovery.generate_environment_summary())
"

# Test tool suggestions
python3 -c "
from devops.tools.dynamic_discovery import tool_discovery
suggestions = tool_discovery.suggest_tools_for_task('deploy to kubernetes')
print('Kubernetes deployment suggestions:', suggestions)
"
```

## 🚨 Failure Indicators

**Discovery Failures:**
- No tools detected despite installations
- Incorrect version information
- False positives (reporting unavailable tools as available)
- Missing common tools (git, python)

**Suggestion Failures:**
- Suggesting unavailable tools
- Missing obvious tool suggestions
- Inappropriate tool recommendations
- Ignoring task context

**Integration Failures:**
- Agent not using discovery results
- Static tool assumptions despite dynamic discovery
- Inconsistent behavior between discovery and usage
- Performance issues from repeated discovery

## 🛠️ Troubleshooting

If discovery fails:

1. **Check Discovery Module:**
   ```bash
   python3 -c "from devops.tools.dynamic_discovery import tool_discovery; print(tool_discovery.discover_environment_capabilities())"
   ```

2. **Verify PATH Detection:**
   ```bash
   echo $PATH
   which git docker kubectl
   ```

3. **Test Tool Execution:**
   ```bash
   git --version
   docker --version
   ```

4. **Check Agent Integration:**
   ```bash
   grep "tool_discovery" /var/folders/*/T/agents_log/agent.latest.log
   ``` 