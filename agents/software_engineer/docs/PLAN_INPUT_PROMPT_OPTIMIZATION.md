# Software Engineer Agent - Input Token Optimization Implementation Plan

**Created**: July 21, 2025  
**Status**: Planning Phase  
**Target**: Callback-based token optimization without custom agent abstractions

## 🎯 Executive Summary

This implementation plan adapts the sophisticated token optimization strategies from the DevOps agent to work purely through the existing callback system. The approach leverages callbacks to implement intelligent context management, smart conversation filtering, and progressive token optimization while maintaining 100% compatibility with the ADK framework.

### Key Success Metrics
- **Token Growth Control**: Eliminate exponential token growth patterns
- **Message Optimization**: 70-90% conversation filtering while preserving tool chains
- **Tool Functionality**: 100% preservation of tool execution flows
- **Response Quality**: Maintained through intelligent context prioritization

## 📋 Problem Statement

The software engineer agent currently lacks input token optimization, leading to:
- **Exponential token growth** in long conversations
- **Context window saturation** affecting performance
- **Inefficient token usage** with redundant conversation history
- **Potential request failures** when approaching model limits

The DevOps agent successfully solved these issues using a custom agent abstraction with sophisticated context management. We need to achieve the same optimizations using only the callback system.

## 🏗️ Architecture Overview

### Core Components

1. **TokenOptimizedCallbackManager**: Central optimization orchestrator
2. **ConversationAnalyzer**: Smart conversation structure analysis
3. **ContextBudgetManager**: Token budget calculation and allocation
4. **ProgressiveOptimizer**: Multi-level optimization strategies
5. **QualityPreserver**: Tool chain and context integrity validation

### Integration Points

- **before_model_callback**: Primary optimization entry point
- **after_model_callback**: Usage tracking and telemetry
- **before_agent_callback**: Session initialization and state setup
- **after_agent_callback**: Session analysis and cleanup

## 📈 Implementation Phases

## Phase 1: Foundation & Core Token Management

**Duration**: 1-2 weeks  
**Priority**: Critical  
**Risk Level**: Low

### Phase 1.1: Token Counting Infrastructure

#### Task 1.1.1: Create Token Counting Framework
**File**: `agents/software_engineer/shared_libraries/token_optimization.py`

```python
class TokenCounter:
    def __init__(self, model_name: str, llm_client: Optional[genai.Client] = None)
    def _initialize_token_counting_strategy(self) -> Callable[[str], int]
    def count_tokens(self, text: str) -> int
    def count_llm_request_tokens(self, llm_request: LlmRequest) -> dict[str, int]
```

**Implementation Details**:
- **Strategy 1**: Native Google GenAI client's count_tokens API
- **Strategy 2**: Tiktoken library with model-specific encoding
- **Strategy 3**: Character-based fallback estimation (len // 4)
- **Error handling**: Graceful fallback with logging

**Success Criteria**:
- [ ] Accurate token counting for system instructions, tools, user messages
- [ ] Fallback strategies working correctly
- [ ] Performance benchmarks under 10ms per request
- [ ] Unit tests covering all counting strategies

#### Task 1.1.2: Context Budget Calculation
**File**: `agents/software_engineer/shared_libraries/token_optimization.py`

```python
class ContextBudgetManager:
    def calculate_base_prompt_tokens(self, llm_request: LlmRequest) -> int
    def determine_safety_margin(self, base_tokens: int) -> int
    def calculate_available_context_budget(self, llm_request: LlmRequest) -> int
```

**Implementation Details**:
- **Base prompt components**: System instructions + tool definitions + current user message
- **Progressive safety margins**: 2000 → 1000 → 500 → 200 → 50 tokens
- **Budget validation**: Ensure positive context budget available
- **Emergency allocation**: Minimal 50-token emergency budget

**Success Criteria**:
- [ ] Accurate base prompt token calculation
- [ ] Progressive safety margin implementation
- [ ] Edge case handling (negative budgets, oversized prompts)
- [ ] Integration tests with real LLM requests

#### Task 1.1.3: Enhanced Callback Factory
**File**: `agents/software_engineer/shared_libraries/callbacks.py`

```python
def create_token_optimized_callbacks(
    agent_name: str,
    model_name: str,
    max_token_limit: int = 1_000_000,
    enhanced_telemetry: bool = True
) -> dict[str, Callable]:
```

**Implementation Details**:
- **Extend existing callback factory** with token optimization
- **Embed TokenCounter and ContextBudgetManager**
- **Initialize optimization state** in callback context
- **Maintain backward compatibility** with existing callback usage

**Success Criteria**:
- [ ] Backward compatibility with existing callbacks
- [ ] Token optimization components properly initialized
- [ ] State management across callback invocations
- [ ] Integration with existing telemetry system

### Phase 1.2: Basic Conversation Filtering

#### Task 1.2.1: Conversation Structure Analysis
**File**: `agents/software_engineer/shared_libraries/conversation_analyzer.py`

```python
class ConversationAnalyzer:
    def analyze_conversation_structure(self, contents: list) -> dict[str, Any]
    def identify_tool_chains(self, contents: list) -> list[dict[str, Any]]
    def classify_message_types(self, contents: list) -> dict[str, list]
```

**Implementation Details**:
- **Message classification**: System, user, assistant, tool_result, context_injection
- **Tool chain detection**: Complete tool execution flows (user → assistant → tool_result → assistant)
- **Conversation segmentation**: Identify complete conversation segments
- **Active vs completed distinction**: Separate ongoing vs finished tool chains

**Success Criteria**:
- [ ] Accurate message type classification (>95% accuracy)
- [ ] Complete tool chain identification
- [ ] Conversation segment boundary detection
- [ ] Unit tests covering edge cases (malformed conversations, incomplete chains)

#### Task 1.2.2: Smart Conversation Filtering
**File**: `agents/software_engineer/shared_libraries/conversation_analyzer.py`

```python
class ConversationFilter:
    def apply_smart_filtering(self, llm_request: LlmRequest, user_message: str) -> int
    def preserve_critical_elements(self, analysis: dict[str, Any]) -> list
    def filter_completed_conversations(self, analysis: dict[str, Any], limit: int) -> list
```

**Implementation Details**:
- **Always preserve**: System messages, context injections, active tool chains, current user message
- **Prioritize**: Recent conversations with tool activity
- **Filter**: Old completed conversations (>2 turns ago), redundant history
- **Adaptive limits**: 2 recent segments for short conversations, 1-2 for long conversations

**Success Criteria**:
- [ ] 100% preservation of active tool chains
- [ ] 60-80% conversation filtering while maintaining coherence
- [ ] Zero tool execution breakage
- [ ] Comprehensive logging of filtering decisions

### Phase 1.3: Integration with Software Engineer Agent

#### Task 1.3.1: Update Main Agent Callback Integration
**File**: `agents/software_engineer/agent.py`

**Implementation Details**:
- **Replace existing callback factory** with `create_token_optimized_callbacks`
- **Pass model information** for token counting strategy selection
- **Configure optimization parameters** via environment variables or config
- **Maintain telemetry integration**

**Success Criteria**:
- [ ] Seamless integration with existing agent configuration
- [ ] Token optimization active in main software engineer agent
- [ ] No regression in existing functionality
- [ ] Telemetry data includes token optimization metrics

#### Task 1.3.2: Update Enhanced Agent Integration
**File**: `agents/software_engineer/enhanced_agent.py`

**Implementation Details**:
- **Update enhanced agent** to use token-optimized callbacks
- **Ensure compatibility** with workflow orchestration features
- **Test with sub-agent delegation** to verify optimization doesn't break sub-agent communication
- **Validate with thinking config** integration

**Success Criteria**:
- [ ] Enhanced agent functionality preserved
- [ ] Sub-agent delegation working correctly
- [ ] Workflow orchestration unaffected
- [ ] Thinking configuration compatibility verified

#### Task 1.3.3: Update Sub-Agent Integration
**Files**: `agents/software_engineer/sub_agents/*/agent.py`

**Implementation Details**:
- **Update factory functions** to use token-optimized callbacks
- **Test each sub-agent type** (code_review, debugging, testing, etc.)
- **Verify callback coordination** between parent and sub-agents
- **Ensure MCP tool loading compatibility**

**Success Criteria**:
- [ ] All sub-agents using token-optimized callbacks
- [ ] No regression in sub-agent specific functionality
- [ ] Parent-child agent communication preserved
- [ ] MCP tool loading unaffected

## Phase 2: Advanced Context Prioritization

**Duration**: 2-3 weeks  
**Priority**: High  
**Risk Level**: Medium

### Phase 2.1: Content Scoring and Prioritization

#### Task 2.1.1: Multi-Factor Content Scoring
**File**: `agents/software_engineer/shared_libraries/content_prioritizer.py`

```python
class ContentPrioritizer:
    def calculate_relevance_score(self, content: str, user_query: str) -> float
    def calculate_recency_score(self, timestamp: float, current_time: float) -> float
    def calculate_tool_activity_score(self, content: dict) -> float
    def calculate_error_priority_score(self, content: dict) -> float
    def calculate_composite_score(self, content: dict, context: dict) -> float
```

**Implementation Details**:
- **Relevance scoring**: Semantic similarity to user query using embeddings or keyword matching
- **Recency weighting**: Exponential decay based on age
- **Tool activity boost**: Higher scores for tool-heavy conversations
- **Error priority**: Critical errors get highest priority
- **Composite scoring**: Weighted combination of all factors

**Success Criteria**:
- [ ] Scoring algorithm produces intuitive rankings
- [ ] Performance under 100ms for typical conversation sizes
- [ ] A/B testing shows improved context quality vs. random selection
- [ ] Configurable scoring weights for different scenarios

#### Task 2.1.2: Priority-Based Context Assembly
**File**: `agents/software_engineer/shared_libraries/context_assembler.py`

```python
class ContextAssembler:
    def assemble_prioritized_context(self, budget: int, items: list) -> tuple[dict, int]
    def apply_budget_constraints(self, context: dict, budget: int) -> dict
    def create_emergency_context(self, budget: int) -> dict
```

**Implementation Details**:
- **Priority levels**: CRITICAL → HIGH → MEDIUM → LOW → MINIMAL
- **Budget allocation**: Reserve portions for each priority level
- **Progressive inclusion**: Fill highest priority first, then lower priorities
- **Emergency fallbacks**: Minimal context when budget severely constrained

**Success Criteria**:
- [ ] Context quality maintained under token pressure
- [ ] Budget constraints respected (±5% tolerance)
- [ ] Emergency modes preserve essential functionality
- [ ] Context assembly time under 50ms

### Phase 2.2: Cross-Turn Context Correlation

#### Task 2.2.1: Context Dependency Analysis
**File**: `agents/software_engineer/shared_libraries/context_correlator.py`

```python
class ContextCorrelator:
    def identify_context_dependencies(self, conversations: list) -> dict[str, list]
    def find_related_tool_chains(self, tool_results: list) -> dict[str, list]
    def detect_multi_turn_tasks(self, conversations: list) -> list[dict]
```

**Implementation Details**:
- **Tool result dependencies**: Identify when later tools depend on earlier results
- **Conversation continuity**: Detect ongoing multi-turn discussions
- **Reference tracking**: Track file, function, or concept references across turns
- **Task boundary detection**: Identify when new independent tasks begin

**Success Criteria**:
- [ ] Accurate dependency detection (>90% precision)
- [ ] Multi-turn task identification working correctly
- [ ] Context bridging preserves conversation coherence
- [ ] Performance suitable for real-time use

#### Task 2.2.2: Smart Context Bridging
**File**: `agents/software_engineer/shared_libraries/context_correlator.py`

```python
class ContextBridge:
    def create_context_bridges(self, filtered_context: dict, dependencies: dict) -> dict
    def add_essential_references(self, context: dict, references: list) -> dict
    def validate_context_completeness(self, context: dict) -> bool
```

**Implementation Details**:
- **Bridge creation**: Add minimal context to maintain coherence when filtering
- **Essential references**: Include critical file/function references even if not recent
- **Completeness validation**: Ensure context provides enough information for task completion
- **Context summarization**: Create brief summaries when full context too large

**Success Criteria**:
- [ ] Context bridges maintain conversation coherence
- [ ] Essential references preserved across filtering
- [ ] Validation prevents incomplete context scenarios
- [ ] Context quality metrics show improvement

### Phase 2.3: Progressive Optimization Strategies

#### Task 2.3.1: Multi-Level Optimization Framework
**File**: `agents/software_engineer/shared_libraries/progressive_optimizer.py`

```python
class ProgressiveOptimizer:
    def apply_optimization_level(self, level: int, context: dict, callback_context: CallbackContext) -> bool
    def calculate_optimization_level(self, retry_attempt: int, token_pressure: float) -> int
    def track_optimization_effectiveness(self, before: int, after: int, quality_metrics: dict) -> None
```

**Implementation Details**:
- **Level 1 (Moderate)**: Reduce conversation history to 2-3 recent turns
- **Level 2 (Aggressive)**: Keep only 1 recent turn, essential tool results
- **Level 3 (Emergency)**: Minimal context with current turn only
- **Dynamic level selection**: Based on retry attempts and token pressure
- **Effectiveness tracking**: Monitor optimization success rates

**Success Criteria**:
- [ ] Progressive optimization reduces token usage effectively
- [ ] Tool functionality preserved at all optimization levels
- [ ] Optimization effectiveness tracked and logged
- [ ] Graceful degradation under extreme token pressure

#### Task 2.3.2: Optimization State Management
**File**: `agents/software_engineer/shared_libraries/progressive_optimizer.py`

```python
class OptimizationState:
    def track_session_metrics(self, callback_context: CallbackContext) -> None
    def update_retry_state(self, callback_context: CallbackContext, retry_attempt: int) -> None
    def calculate_token_pressure(self, usage_history: list) -> float
```

**Implementation Details**:
- **Session tracking**: Monitor token usage patterns across conversation
- **Retry state persistence**: Remember optimization levels across retries
- **Pressure calculation**: Dynamic assessment of token constraint severity
- **Adaptive thresholds**: Adjust optimization triggers based on usage patterns

**Success Criteria**:
- [ ] State management persists across callback invocations
- [ ] Token pressure calculation accurately reflects constraints
- [ ] Adaptive optimization improves over session duration
- [ ] State cleanup on session completion

## Phase 3: Performance Monitoring & Quality Assurance

**Duration**: 1-2 weeks  
**Priority**: Medium  
**Risk Level**: Low

### Phase 3.1: Comprehensive Telemetry Integration

#### Task 3.1.1: Token Usage Analytics
**File**: `agents/software_engineer/shared_libraries/token_telemetry.py`

```python
class TokenTelemetry:
    def track_optimization_metrics(self, before: dict, after: dict, quality: dict) -> None
    def monitor_token_growth_patterns(self, session_data: list) -> dict
    def calculate_optimization_effectiveness(self, session_id: str) -> dict
```

**Implementation Details**:
- **Token usage tracking**: Before/after optimization metrics
- **Growth pattern analysis**: Detect exponential growth, optimization effectiveness
- **Quality preservation metrics**: Tool success rates, response coherence scores
- **Performance indicators**: Optimization latency, memory usage

**Success Criteria**:
- [ ] Comprehensive token usage analytics dashboard
- [ ] Growth pattern detection and alerting
- [ ] Optimization effectiveness quantified
- [ ] Performance regression detection

#### Task 3.1.2: Quality Assurance Metrics
**File**: `agents/software_engineer/shared_libraries/quality_assurance.py`

```python
class QualityAssurance:
    def validate_tool_chain_preservation(self, original: list, filtered: list) -> bool
    def calculate_context_coherence_score(self, context: dict, user_query: str) -> float
    def track_response_quality_indicators(self, response: str, context: dict) -> dict
```

**Implementation Details**:
- **Tool chain validation**: Ensure 100% preservation of active tool flows
- **Coherence scoring**: Measure context logical consistency
- **Response quality tracking**: Length, relevance, completeness metrics
- **Regression detection**: Alert on quality degradation

**Success Criteria**:
- [ ] Tool chain preservation validation (100% accuracy)
- [ ] Context coherence scoring operational
- [ ] Response quality trends tracked
- [ ] Quality regression alerts functional

### Phase 3.2: Testing & Validation Framework

#### Task 3.2.1: Unit Testing Suite
**File**: `tests/unit/test_token_optimization.py`

**Test Coverage**:
- [ ] Token counting accuracy (all strategies)
- [ ] Context budget calculation edge cases
- [ ] Conversation structure analysis
- [ ] Smart filtering preservation logic
- [ ] Progressive optimization levels
- [ ] Content scoring algorithms

#### Task 3.2.2: Integration Testing
**File**: `tests/integration/test_token_optimization_integration.py`

**Test Coverage**:
- [ ] End-to-end optimization in real agent conversations
- [ ] Sub-agent communication preservation
- [ ] Tool execution flow validation
- [ ] Multi-turn conversation optimization
- [ ] Error handling and fallback scenarios

#### Task 3.2.3: Performance Benchmarking
**File**: `tests/performance/test_token_optimization_performance.py`

**Benchmarks**:
- [ ] Token counting performance (<10ms per request)
- [ ] Context assembly time (<50ms)
- [ ] Memory usage under optimization
- [ ] Optimization overhead measurement

## 🚀 Rollout Strategy

### Development Environment Testing
1. **Unit tests** passing for all components
2. **Integration tests** with sample conversations
3. **Performance benchmarks** meeting targets
4. **Code review** and security validation

### Staging Environment Validation
1. **A/B testing** with subset of conversations
2. **Quality metrics** comparison vs. baseline
3. **Performance monitoring** under realistic load
4. **Error rate analysis** and debugging

### Production Rollout
1. **Feature flag controlled** rollout (10% → 50% → 100%)
2. **Real-time monitoring** of key metrics
3. **Rollback capability** if issues detected
4. **Documentation** and training completion

## 📊 Success Criteria & KPIs

### Performance Metrics
- **Token Growth Rate**: <5% per turn (vs. current exponential growth)
- **Message Filtering**: 70-90% reduction while preserving tool chains
- **Context Budget Utilization**: 60-80% optimal range
- **Optimization Latency**: <100ms per request

### Quality Metrics  
- **Tool Chain Preservation**: 100% (zero tool execution breaks)
- **Response Quality Score**: Maintain >90% of baseline
- **Context Coherence**: >85% coherence score
- **User Satisfaction**: No degradation in task completion rates

### Reliability Metrics
- **Optimization Success Rate**: >95% of requests optimized successfully
- **Error Rate**: <1% optimization-related errors
- **Fallback Effectiveness**: 100% graceful degradation in edge cases
- **Memory Usage**: <20% increase from baseline

## 🛡️ Risk Mitigation

### Technical Risks
- **Context Quality Degradation**: Comprehensive testing and validation
- **Tool Chain Breakage**: 100% preservation validation before release
- **Performance Overhead**: Benchmarking and optimization tuning
- **Memory Leaks**: Careful state management and cleanup

### Operational Risks
- **Regression Introduction**: Comprehensive test coverage and CI/CD
- **Monitoring Gaps**: Full telemetry and alerting implementation  
- **Rollback Complexity**: Feature flag controls and documented procedures
- **Training Needs**: Documentation and team knowledge transfer

### Mitigation Strategies
1. **Progressive rollout** with monitoring at each stage
2. **Automated testing** at multiple levels (unit, integration, performance)
3. **Real-time monitoring** with alerting and dashboards
4. **Rollback procedures** tested and documented
5. **Code reviews** by domain experts
6. **Documentation** for maintenance and troubleshooting

## 📅 Timeline & Milestones

### Week 1-2: Phase 1 Foundation
- [ ] Token counting infrastructure
- [ ] Basic conversation filtering
- [ ] Callback factory enhancement
- [ ] Initial integration testing

### Week 3-4: Phase 1 Integration
- [ ] Main agent integration
- [ ] Enhanced agent integration  
- [ ] Sub-agent integration
- [ ] End-to-end validation

### Week 5-6: Phase 2 Advanced Features
- [ ] Content scoring and prioritization
- [ ] Context correlation and bridging
- [ ] Progressive optimization framework
- [ ] Advanced integration testing

### Week 7-8: Phase 2 Completion
- [ ] Multi-level optimization
- [ ] State management
- [ ] Performance optimization
- [ ] Comprehensive testing

### Week 9-10: Phase 3 Quality Assurance
- [ ] Telemetry integration
- [ ] Quality assurance metrics
- [ ] Performance benchmarking
- [ ] Production readiness validation

### Week 11: Production Rollout
- [ ] Staging environment validation
- [ ] Production deployment
- [ ] Monitoring and optimization
- [ ] Documentation completion

## 📚 Documentation Deliverables

1. **Technical Documentation**:
   - API documentation for all new components
   - Configuration guide for optimization parameters
   - Integration guide for new agent implementations
   - Troubleshooting guide for common issues

2. **Operational Documentation**:
   - Monitoring and alerting runbook
   - Performance tuning guide
   - Rollback procedures
   - Capacity planning guidelines

3. **User Documentation**:
   - Feature overview and benefits
   - Configuration options for different use cases
   - Best practices for optimization
   - FAQ for common questions

## 🔄 Post-Implementation

### Monitoring & Maintenance
- **Weekly performance reviews** for first month
- **Monthly optimization effectiveness analysis**
- **Quarterly feature enhancement planning**
- **Continuous monitoring** of key metrics

### Future Enhancements
- **Machine learning optimization**: Adaptive threshold tuning
- **Semantic context scoring**: Embeddings-based relevance
- **Dynamic safety margins**: Model-specific optimization
- **Cross-agent optimization**: Shared context between agents

---

**This implementation plan provides a comprehensive roadmap for achieving DevOps-agent-level token optimization using only callbacks, ensuring maintainable, performant, and high-quality results.** 