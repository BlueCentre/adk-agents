# Example Prompts Directory

This directory contains test prompts and validation scenarios for the DevOps Agent, organized by relevance and completion status.

## 📁 Directory Structure

### 🔄 **current/** - Active Test Prompts
Test prompts for ongoing features and current functionality:

- **`test_gemini_thinking_feature.md`** - Validation prompts for Gemini's advanced thinking capabilities
- **`test_dynamic_discovery.md`** - Test scenarios for dynamic tool and environment discovery
- **`test_context_diagnostics.md`** - Context management diagnostic and troubleshooting prompts
- **`test_planning_heuristics.md`** - Interactive planning workflow validation scenarios
- **`test_prompt_engineering.md`** - Prompt optimization and engineering test cases

### 📦 **archive/** - Completed Test Prompts
Test prompts for completed features (Phase 2 and earlier):

- **`test_phase2_remaining_features.md`** - Phase 2 feature validation (COMPLETED)
- **`test_phase2_validation.md`** - Comprehensive Phase 2 testing (COMPLETED)

## 🧪 Usage Guidelines

### Running Test Prompts

1. **Start the DevOps Agent**:
   ```bash
   ./scripts/execution/run.sh
   ```

2. **Copy and paste prompts** from the relevant test files into the agent interface

3. **Validate expected behaviors** as described in each test file

### Test Categories

#### **Feature Validation**
- Test specific features like Gemini thinking, dynamic discovery
- Validate expected outputs and behaviors
- Check error handling and edge cases

#### **Integration Testing**
- Test feature interactions and workflows
- Validate end-to-end scenarios
- Check context management across multiple turns

#### **Performance Testing**
- Validate token utilization improvements
- Test context prioritization effectiveness
- Check response times and resource usage

## 📋 Test Prompt Structure

Each test prompt file typically contains:

1. **Feature Overview** - What's being tested
2. **Test Scenarios** - Specific prompts and expected behaviors
3. **Validation Criteria** - How to determine success
4. **Edge Cases** - Boundary conditions and error scenarios
5. **Performance Expectations** - Token usage, timing, etc.

## 🔧 Contributing Test Prompts

### Adding New Test Prompts

1. **Create descriptive filename**: `test_[feature_name].md`
2. **Place in appropriate directory**:
   - `current/` for active features
   - `archive/` for completed features
3. **Follow the standard structure** outlined above
4. **Update this README** with the new test description

### Test Prompt Best Practices

- **Be specific** about expected behaviors
- **Include edge cases** and error scenarios
- **Provide clear validation criteria**
- **Test both positive and negative cases**
- **Include performance expectations** where relevant

## 🎯 Quick Reference

### Current Priority Tests
1. **Gemini Thinking** - Advanced reasoning capabilities
2. **Dynamic Discovery** - Environment adaptation
3. **Context Diagnostics** - Context management troubleshooting
4. **Planning Heuristics** - Interactive planning accuracy
5. **Prompt Engineering** - Instruction optimization

### Archived (Completed)
- **Phase 2 Features** - All Phase 2 functionality validated ✅
- **Phase 2 Validation** - Comprehensive testing completed ✅

## 📊 Test Results Tracking

For systematic testing:

1. **Document results** in the agent's docs directory
2. **Update validation status** in relevant documentation
3. **Archive completed tests** when features are finalized
4. **Create new tests** for emerging features and improvements

---

**Last Updated**: December 2024  
**Organization**: Test prompts organized by completion status and relevance 