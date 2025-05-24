#!/usr/bin/env bash

clear
echo -e "Please clean up and consolidate our repository to make it cohesive and well-organized. Follow this systematic approach with robust error handling:

## 📁 Repository Grooming Strategy

### 1. Documentation Audit & Consolidation
- **Identify Redundancies**: Look for duplicate, overlapping, or outdated documentation files
- **Consolidate Similar Content**: Merge related documents that cover the same topics
- **Remove Outdated Files**: Delete files that describe completed work, old approaches, or obsolete information
- **Organize by Purpose**: Create logical subdirectories (like docs/features/, docs/archive/) for better organization

### 2. Directory Structure Optimization
- **Clean Up Empty Directories**: Remove any empty folders left after file moves
- **Improve Naming**: Rename files/folders for clarity and consistency
- **Create Index Files**: Add README.md files in key directories for navigation
- **Update References**: Fix any broken links or references after reorganization

### 3. Documentation Quality & Currency
- **Update Main README**: Ensure it reflects the current state, features, and directory structure
- **Consolidate Implementation Status**: Create comprehensive status documents that replace scattered reports
- **Improve Navigation**: Add clear navigation paths for different user types (developers, users, contributors)
- **Remove Redundant Content**: Eliminate duplicate information across multiple files

### 4. Consistency & Standards
- **Standardize Formatting**: Ensure consistent markdown formatting, headers, and structure
- **Update Timestamps**: Refresh last-updated dates on modified documents
- **Verify Accuracy**: Ensure all documentation reflects the actual current codebase
- **Cross-Reference Validation**: Check that file references and links are correct

### 5. Final Verification
- **Structure Validation**: Verify the new organization makes logical sense
- **Completeness Check**: Ensure no important information was lost during consolidation
- **User Experience**: Test navigation flows for different user personas
- **Clean Commit**: Stage and commit all changes with a clear summary

## ⚡ Error Handling Guidelines

**When shell commands fail:**
1. **For git commit issues**: If commit messages have quote problems, try:
   - Using simpler commit messages without complex formatting
   - Breaking multi-line messages into separate commits
   - Using 'git commit' without -m to open an editor
2. **For parsing errors**: Try alternative command formats or break complex operations into simpler steps
3. **For permission errors**: Verify file permissions and working directory
4. **For command not found**: Check if tools are installed and accessible

**Recovery strategies:**
- If a command fails with parsing errors, use the 'execute_vetted_shell_command_with_retry' tool if available
- Break complex operations into multiple simpler commands
- Use file operations (read/write) instead of complex shell commands when possible
- Provide clear status updates on what worked and what needs manual intervention

## 🎯 Expected Outcomes
- Consolidated documentation with no redundancies
- Clear directory structure that's easy to navigate
- Updated README that accurately reflects current capabilities
- Organized feature documentation in logical subdirectories
- Improved discoverability and user experience

## 🚨 Important Instructions

**Error Resilience**: If any command fails:
1. Log the specific error clearly
2. Try an alternative approach when possible
3. Continue with other tasks that don't depend on the failed operation
4. Provide a summary of what was completed and what requires manual attention
5. Do NOT terminate the entire process due to a single command failure

**Commit Strategy**: If git operations fail:
1. First try staging and committing with a simple message
2. If that fails, stage files individually
3. As a last resort, provide clear instructions for manual commit

Execute this comprehensive cleanup with robust error handling, ensuring the process completes even if individual operations encounter issues.

approve
exit" | \
  PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python uvx \
    --with extensions \
    --with google-genai \
    --with google-api-core \
    --with chromadb \
    --with protobuf \
    --with openai \
    --with tiktoken \
    --python 3.13 \
    --from git+https://github.com/BlueCentre/adk-python.git@feat/rich-click \
    adk run devops || echo "🙈 Ignore the error above. It's caused by Google ADK."