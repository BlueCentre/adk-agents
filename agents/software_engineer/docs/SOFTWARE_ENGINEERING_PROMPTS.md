# Software Engineering Multi-Agent Prompts Guide

This guide demonstrates typical software engineering journeys using the multi-agent system. Each example shows how complex requests are broken down, delegated to specialized sub-agents, and orchestrated to provide comprehensive solutions.

## Table of Contents
- [Simple Single-Agent Tasks](#simple-single-agent-tasks)
- [Multi-Step Workflows](#multi-step-workflows)
- [Complete Feature Development](#complete-feature-development)
- [Bug Investigation & Resolution](#bug-investigation--resolution)
- [Code Quality & Refactoring](#code-quality--refactoring)
- [Architecture & Design](#architecture--design)
- [Testing & Validation](#testing--validation)
- [DevOps & Deployment](#devops--deployment)

---

## Simple Single-Agent Tasks

### Code Review Request
**Prompt:**
```
Please review the user authentication module in src/auth/user_auth.py. Focus on security vulnerabilities and performance issues.
```

**Expected Workflow:**
- **Root Agent** → Delegates to `code_review_agent`
- **code_review_agent** → Performs deep security and performance analysis
- **Result:** Detailed review with security recommendations and performance improvements

---

### Design Pattern Consultation  
**Prompt:**
```
I have a notification system that's becoming hard to maintain. Different parts of the app need to send emails, SMS, and push notifications. What design pattern would help organize this better?
```

**Expected Workflow:**
- **Root Agent** → Delegates to `design_pattern_agent`
- **design_pattern_agent** → Analyzes current code and recommends Observer or Strategy pattern
- **Result:** Architecture recommendation with implementation examples

---

### Test Generation
**Prompt:**
```
Generate comprehensive unit tests for the PaymentProcessor class in src/payments/processor.py. Include edge cases and error scenarios.
```

**Expected Workflow:**
- **Root Agent** → Delegates to `testing_agent`
- **testing_agent** → Analyzes code, creates comprehensive test suite
- **Result:** Complete test file with unit tests, edge cases, and mocking

---

## Multi-Step Workflows

### Code Review + Quality Improvement
**Prompt:**
```
Review the shopping cart implementation in src/cart/ and fix any quality issues you find. Make sure the code follows best practices.
```

**Expected Workflow:**
1. **Root Agent** → Plans multi-step workflow
2. **code_review_agent** → Reviews cart implementation, identifies issues
3. **code_quality_agent** → Analyzes code quality metrics, suggests improvements
4. **Root Agent** → Synthesizes findings and provides unified recommendations

**Result:** Comprehensive analysis with prioritized improvements and implementation guidance

---

### Debug + Test + Document
**Prompt:**
```
There's a memory leak in our image processing pipeline. Debug and fix it, then add tests to prevent regression and update the documentation.
```

**Expected Workflow:**
1. **Root Agent** → Analyzes complex request, plans 3-step workflow
2. **debugging_agent** → Investigates memory leak, identifies root cause, implements fix
3. **testing_agent** → Creates regression tests for the memory leak scenario
4. **documentation_agent** → Updates docs with fix details and prevention guidelines
5. **Root Agent** → Synthesizes complete solution

**Result:** Fixed code, regression tests, and updated documentation

---

### Architecture Review + Refactoring
**Prompt:**
```
Our user management system has grown complex and hard to test. Review the architecture and refactor it to be more maintainable.
```

**Expected Workflow:**
1. **Root Agent** → Plans architectural improvement workflow
2. **design_pattern_agent** → Analyzes current architecture, recommends improvements
3. **code_review_agent** → Reviews implementation details, identifies refactoring opportunities
4. **testing_agent** → Suggests testing strategies for refactored code
5. **Root Agent** → Creates unified refactoring plan

**Result:** Architecture improvement plan with step-by-step refactoring guidance

---

## Complete Feature Development

### E-commerce Search Feature
**Prompt:**
```
I need to implement a product search feature with filters, sorting, and pagination for our e-commerce site. The current codebase uses Python/Flask with PostgreSQL. Please design, implement, test, and document this feature.
```

**Expected Workflow:**
1. **Root Agent** → Recognizes complete feature request, plans full development lifecycle
2. **design_pattern_agent** → Designs search architecture with proper separation of concerns
3. **code_review_agent** → Reviews implementation approach, suggests best practices
4. **code_quality_agent** → Ensures code quality standards for new feature
5. **testing_agent** → Creates comprehensive test suite (unit, integration, performance)
6. **documentation_agent** → Documents API endpoints, usage examples, and architecture
7. **devops_agent** → Provides deployment considerations and database migration guidance
8. **Root Agent** → Synthesizes complete feature implementation plan

**Result:** Complete feature with architecture, implementation, tests, documentation, and deployment guidance

---

### API Integration Feature
**Prompt:**
```
Integrate Stripe payment processing into our subscription service. Ensure proper error handling, security, testing, and monitoring. Our stack is Node.js with MongoDB.
```

**Expected Workflow:**
1. **Root Agent** → Plans comprehensive integration workflow
2. **design_pattern_agent** → Designs payment service architecture with proper abstraction
3. **code_review_agent** → Reviews security considerations and error handling patterns
4. **debugging_agent** → Implements robust error handling and debugging capabilities
5. **testing_agent** → Creates tests including API mocking and edge cases
6. **documentation_agent** → Documents integration setup, configuration, and usage
7. **devops_agent** → Provides deployment, monitoring, and security recommendations
8. **Root Agent** → Delivers complete integration solution

**Result:** Secure, tested, and documented payment integration with deployment guidance

---

## Bug Investigation & Resolution

### Performance Degradation
**Prompt:**
```
Our API response times have increased from 200ms to 2s over the past month. The issue seems to be in the user dashboard endpoint. Investigate and fix the performance problem.
```

**Expected Workflow:**
1. **Root Agent** → Recognizes performance investigation need
2. **debugging_agent** → Analyzes performance bottlenecks, profiles code execution
3. **code_review_agent** → Reviews code for performance anti-patterns
4. **testing_agent** → Creates performance tests to prevent regression
5. **devops_agent** → Analyzes infrastructure and monitoring considerations
6. **Root Agent** → Provides complete performance optimization solution

**Result:** Performance fix with monitoring, tests, and prevention strategies

---

### Intermittent Authentication Failures
**Prompt:**
```
Users are reporting intermittent login failures that seem random. Debug this authentication issue and ensure it doesn't happen again.
```

**Expected Workflow:**
1. **Root Agent** → Plans systematic debugging approach
2. **debugging_agent** → Investigates authentication flow, analyzes logs, identifies race conditions
3. **code_review_agent** → Reviews auth code for thread safety and edge cases
4. **testing_agent** → Creates tests for concurrent authentication scenarios
5. **devops_agent** → Reviews deployment and load balancing configuration
6. **Root Agent** → Delivers comprehensive authentication fix

**Result:** Robust authentication system with concurrent testing and monitoring

---

## Code Quality & Refactoring

### Technical Debt Cleanup
**Prompt:**
```
The codebase has accumulated technical debt. Analyze the worst areas and create a refactoring plan to improve maintainability and reduce complexity.
```

**Expected Workflow:**
1. **Root Agent** → Plans comprehensive code quality improvement
2. **code_quality_agent** → Analyzes technical debt, identifies worst areas
3. **design_pattern_agent** → Suggests architectural improvements for complex areas
4. **code_review_agent** → Reviews specific code sections for refactoring opportunities
5. **testing_agent** → Ensures refactoring safety with comprehensive test coverage
6. **Root Agent** → Creates prioritized technical debt reduction plan

**Result:** Strategic refactoring plan with risk assessment and implementation priorities

---

### Security Hardening
**Prompt:**
```
Perform a comprehensive security review of our web application and implement necessary security improvements. Focus on authentication, data validation, and API security.
```

**Expected Workflow:**
1. **Root Agent** → Plans comprehensive security assessment
2. **code_review_agent** → Performs security-focused code review
3. **code_quality_agent** → Analyzes for security anti-patterns and vulnerabilities
4. **testing_agent** → Creates security test cases and penetration testing scenarios
5. **devops_agent** → Reviews deployment security and infrastructure hardening
6. **documentation_agent** → Documents security practices and incident response procedures
7. **Root Agent** → Delivers complete security hardening plan

**Result:** Comprehensive security improvements with testing and documentation

---

## Architecture & Design

### Microservices Migration
**Prompt:**
```
Our monolithic application needs to be split into microservices. Design a migration strategy that minimizes risk and maintains system reliability.
```

**Expected Workflow:**
1. **Root Agent** → Plans complex architectural transformation
2. **design_pattern_agent** → Designs microservices architecture and service boundaries
3. **code_review_agent** → Analyzes current codebase for service extraction opportunities
4. **testing_agent** → Designs testing strategy for distributed system
5. **devops_agent** → Plans deployment, monitoring, and service discovery infrastructure
6. **documentation_agent** → Documents migration plan and new architecture
7. **Root Agent** → Creates phased migration strategy

**Result:** Complete microservices migration plan with risk mitigation and phased approach

---

### Event-Driven Architecture
**Prompt:**
```
Implement an event-driven architecture for our order processing system to improve scalability and decouple services.
```

**Expected Workflow:**
1. **Root Agent** → Plans event-driven transformation
2. **design_pattern_agent** → Designs event sourcing and messaging architecture
3. **code_review_agent** → Reviews implementation approach for event handling
4. **testing_agent** → Creates testing strategy for asynchronous event processing
5. **devops_agent** → Plans message queue infrastructure and monitoring
6. **documentation_agent** → Documents event schemas and processing flows
7. **Root Agent** → Delivers complete event-driven implementation plan

**Result:** Event-driven architecture with implementation, testing, and operational guidance

---

## Testing & Validation

### Test Automation Strategy
**Prompt:**
```
Our testing is mostly manual and slowing down releases. Design and implement a comprehensive automated testing strategy for our web application.
```

**Expected Workflow:**
1. **Root Agent** → Plans comprehensive test automation transformation
2. **testing_agent** → Designs test pyramid strategy (unit, integration, e2e)
3. **code_quality_agent** → Ensures testable code structure and coverage metrics
4. **devops_agent** → Implements CI/CD pipeline with automated testing
5. **documentation_agent** → Documents testing practices and contribution guidelines
6. **Root Agent** → Creates complete test automation roadmap

**Result:** Comprehensive testing strategy with automation pipeline and team practices

---

### Load Testing & Performance
**Prompt:**
```
We're expecting 10x traffic growth. Implement load testing and optimize our application for high performance under load.
```

**Expected Workflow:**
1. **Root Agent** → Plans performance optimization strategy
2. **testing_agent** → Designs load testing scenarios and performance benchmarks
3. **code_review_agent** → Reviews code for performance bottlenecks
4. **debugging_agent** → Implements performance monitoring and profiling
5. **devops_agent** → Plans infrastructure scaling and load balancing
6. **Root Agent** → Delivers performance optimization plan

**Result:** Load testing implementation with performance optimization recommendations

---

## DevOps & Deployment

### CI/CD Pipeline Setup
**Prompt:**
```
Set up a complete CI/CD pipeline for our Django application with automated testing, security scanning, and deployment to staging and production environments.
```

**Expected Workflow:**
1. **Root Agent** → Plans comprehensive CI/CD implementation
2. **devops_agent** → Designs pipeline architecture with security and quality gates
3. **testing_agent** → Integrates automated testing into pipeline
4. **code_quality_agent** → Adds code quality and security scanning steps
5. **documentation_agent** → Documents deployment processes and runbooks
6. **Root Agent** → Delivers complete CI/CD solution

**Result:** Production-ready CI/CD pipeline with quality gates and documentation

---

### Containerization & Orchestration
**Prompt:**
```
Containerize our application stack and set up Kubernetes orchestration for better scalability and resource management.
```

**Expected Workflow:**
1. **Root Agent** → Plans containerization strategy
2. **devops_agent** → Designs Docker and Kubernetes architecture
3. **code_review_agent** → Reviews application code for container compatibility
4. **testing_agent** → Adapts testing strategy for containerized environment
5. **debugging_agent** → Implements logging and debugging for distributed containers
6. **documentation_agent** → Documents container operations and troubleshooting
7. **Root Agent** → Delivers complete containerization solution

**Result:** Containerized application with Kubernetes orchestration and operational documentation

---

## Advanced Scenarios

### Zero-Downtime Migration
**Prompt:**
```
Migrate our user database from MySQL to PostgreSQL with zero downtime. Our app serves 1M+ users continuously.
```

**Expected Workflow:**
1. **Root Agent** → Plans complex zero-downtime migration
2. **design_pattern_agent** → Designs dual-write migration pattern
3. **devops_agent** → Plans infrastructure and deployment strategy
4. **testing_agent** → Creates comprehensive migration testing scenarios
5. **debugging_agent** → Implements monitoring and rollback procedures
6. **documentation_agent** → Documents migration procedures and contingency plans
7. **Root Agent** → Creates detailed migration execution plan

**Result:** Risk-minimized migration plan with rollback strategies and comprehensive monitoring

---

### Multi-Region Deployment
**Prompt:**
```
Deploy our application across multiple AWS regions for disaster recovery and improved global performance.
```

**Expected Workflow:**
1. **Root Agent** → Plans multi-region architecture
2. **design_pattern_agent** → Designs distributed system architecture with data consistency
3. **devops_agent** → Plans infrastructure, networking, and deployment across regions
4. **testing_agent** → Creates disaster recovery and failover testing procedures
5. **debugging_agent** → Implements cross-region monitoring and alerting
6. **documentation_agent** → Documents operational procedures and disaster recovery playbooks
7. **Root Agent** → Delivers complete multi-region deployment strategy

**Result:** Global deployment architecture with disaster recovery and operational procedures

---

## Usage Tips

### Effective Prompt Structure
1. **Be Specific**: Include technology stack, constraints, and requirements
2. **Provide Context**: Mention existing codebase, team size, and business requirements
3. **Define Scope**: Clarify if you want design, implementation, testing, documentation, or all
4. **Include Goals**: Mention performance, security, maintainability, or other objectives

### Best Practices
- Start with specific questions for single-agent tasks
- Use comprehensive prompts for full feature development
- Mention your tech stack and constraints for better recommendations
- Ask for phased approaches for large migrations or refactoring
- Request documentation and testing as part of complex implementations

### Expected Response Quality
The multi-agent system will:
- Break down complex requests into logical steps
- Provide specialized expertise from each relevant sub-agent
- Synthesize results into coherent, actionable recommendations
- Include implementation guidance, testing strategies, and operational considerations
- Prioritize recommendations based on impact and feasibility 