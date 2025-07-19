#!/usr/bin/env python3
"""
DevOps Agent Tracing Overview
Shows all available tracing capabilities including OpenLIT and custom tracing.
"""

import os


def show_openlit_tracing_features():
    """Show OpenLIT tracing features that are automatically available."""
    print("🔍 OpenLIT Auto-Instrumentation Tracing")
    print("=" * 50)

    print("📊 Automatic Trace Collection:")
    auto_traces = [
        "LLM Request/Response Traces - Complete request lifecycle",
        "Token Usage Tracking - Input/output/total tokens per request",
        "Model Performance - Response times and success rates",
        "Cost Tracking - USD cost per LLM request",
        "VectorDB Operations - ChromaDB query/insert/update operations",
        "Exception Monitoring - Automatic error capture with context",
    ]
    for trace in auto_traces:
        print(f"  • {trace}")

    print("\n🏷️  Semantic Conventions (OpenTelemetry Standard):")
    semantic_attrs = [
        "gen_ai.system - LLM provider (openai, anthropic, google, etc.)",
        "gen_ai.request.model - Model name (gemini-1.5-flash, gpt-4, etc.)",
        "gen_ai.operation.name - Operation type (chat, embedding, etc.)",
        "gen_ai.request.temperature - Model temperature setting",
        "gen_ai.usage.input_tokens - Prompt tokens consumed",
        "gen_ai.usage.output_tokens - Completion tokens generated",
        "gen_ai.usage.cost - Request cost in USD",
        "db.system - Database type (chroma, pinecone, etc.)",
        "db.operation - Database operation (query, insert, update)",
    ]
    for attr in semantic_attrs:
        print(f"  • {attr}")

    print()


def show_manual_tracing_capabilities():
    """Show manual tracing capabilities."""
    print("🛠️  Manual Tracing Capabilities")
    print("=" * 50)

    print("🎯 OpenLIT Manual Tracing:")
    manual_features = [
        "@openlit.trace - Decorator for automatic function tracing",
        "openlit.start_trace() - Context manager for complex operations",
        "trace.set_result() - Set final operation result",
        "trace.set_metadata() - Add custom metadata to traces",
        "Grouped Operations - Multiple LLM calls in single trace",
        "Custom Span Attributes - Add business context to traces",
    ]
    for feature in manual_features:
        print(f"  • {feature}")

    print("\n🔧 Custom Agent Tracing:")
    custom_features = [
        "Agent Lifecycle Tracing - Initialization, planning, execution",
        "Tool Execution Tracing - Individual tool performance",
        "Context Management Tracing - Memory and state operations",
        "User Interaction Tracing - Request/response cycles",
        "Error Handling Tracing - Exception context and recovery",
        "Planning Operations - Multi-step plan execution",
        "File Operations - Read/write/modify operations",
        "Shell Commands - Command execution and results",
    ]
    for feature in custom_features:
        print(f"  • {feature}")

    print()


def show_trace_configuration():
    """Show current tracing configuration."""
    print("⚙️  Tracing Configuration")
    print("=" * 50)

    # OpenLIT Configuration
    print("🔍 OpenLIT Tracing Settings:")
    print(f"  Content Capture: {os.getenv('OPENLIT_CAPTURE_CONTENT', 'true')}")
    print(f"  Batch Processing: {os.getenv('OPENLIT_DISABLE_BATCH', 'false')}")
    print(f"  Disabled Instrumentors: {os.getenv('OPENLIT_DISABLED_INSTRUMENTORS', 'none')}")
    print(f"  Environment: {os.getenv('OPENLIT_ENVIRONMENT', 'Production')}")

    # Custom Tracing Configuration
    print("\n🛠️  Custom Tracing Settings:")
    print(f"  Sampling Rate: {os.getenv('TRACE_SAMPLING_RATE', '1.0')} (0.0-1.0)")
    print(f"  Resource Attributes: {os.getenv('OTEL_RESOURCE_ATTRIBUTES', 'auto-generated')}")

    # Export Configuration
    print("\n☁️  Trace Export:")
    endpoint = os.getenv("GRAFANA_OTLP_ENDPOINT")
    token = os.getenv("GRAFANA_OTLP_TOKEN")
    export_disabled = os.getenv("DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT", "false")

    if export_disabled.lower() in ("true", "1", "yes"):
        print("  Status: ❌ Disabled via DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT")
    elif endpoint and token:
        print("  Status: ✅ Configured for Grafana Cloud")
        print(f"  Endpoint: {endpoint}")
        print(f"  Export Interval: {os.getenv('GRAFANA_EXPORT_INTERVAL_SECONDS', '120')}s")
    else:
        print("  Status: ⚠️  Local traces only (no export configured)")

    print()


def show_trace_examples():
    """Show examples of how to use tracing."""
    print("💡 Tracing Usage Examples")
    print("=" * 50)

    print("🎯 OpenLIT Manual Tracing:")
    print("""
# Decorator approach
@openlit.trace
def generate_response(prompt):
    response = llm.generate(prompt)
    return response

# Context manager approach
with openlit.start_trace("complex_operation") as trace:
    result = perform_complex_task()
    trace.set_result(f"Processed {len(result)} items")
    trace.set_metadata({
        "input_size": len(input_data),
        "processing_time": duration,
        "success_rate": success_count / total_count
    })
""")

    print("\n🔧 Custom Agent Tracing:")
    print("""
# Agent lifecycle tracing
@trace_agent_lifecycle("user_request_processing")
async def handle_user_request(request):
    return await process_request(request)

# Tool execution tracing
with trace_tool_execution("shell_command", command=cmd) as trace:
    result = execute_command(cmd)
    trace.set_metadata({
        "exit_code": result.exit_code,
        "output_size": len(result.stdout)
    })

# LLM interaction tracing
with trace_llm_request("gemini-1.5-flash", "chat") as trace:
    response = await llm.chat(messages)
    trace.set_metadata({
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    })
""")

    print()


def show_trace_benefits():
    """Show benefits of comprehensive tracing."""
    print("🎯 Tracing Benefits")
    print("=" * 50)

    print("📊 Observability Benefits:")
    benefits = [
        "End-to-End Visibility - Complete request flow from user to response",
        "Performance Analysis - Identify bottlenecks and optimization opportunities",
        "Error Debugging - Detailed context for failures and exceptions",
        "Cost Optimization - Track LLM usage and costs per operation",
        "User Experience - Monitor response times and success rates",
        "Capacity Planning - Understand resource usage patterns",
    ]
    for benefit in benefits:
        print(f"  • {benefit}")

    print("\n🔧 Development Benefits:")
    dev_benefits = [
        "Debugging - Trace execution flow through complex operations",
        "Testing - Verify tool interactions and data flow",
        "Optimization - Identify slow operations and inefficiencies",
        "Monitoring - Real-time visibility into agent behavior",
        "Analytics - Historical analysis of agent performance",
        "Compliance - Audit trail for sensitive operations",
    ]
    for benefit in dev_benefits:
        print(f"  • {benefit}")

    print()


def show_trace_data_flow():
    """Show how trace data flows through the system."""
    print("🔄 Trace Data Flow")
    print("=" * 50)

    print("📈 Data Collection:")
    print("  1. OpenLIT Auto-Instrumentation → LLM/VectorDB traces")
    print("  2. Custom Decorators → Agent operation traces")
    print("  3. Context Managers → Complex operation traces")
    print("  4. Manual Spans → Custom business logic traces")

    print("\n📤 Data Export:")
    print("  1. OpenTelemetry SDK → Standardized trace format")
    print("  2. OTLP Exporter → Grafana Cloud / Jaeger / Zipkin")
    print("  3. Local Storage → Development debugging")
    print("  4. Structured Logs → Correlation with log data")

    print("\n📊 Data Analysis:")
    print("  1. Grafana Cloud → Production monitoring dashboards")
    print("  2. Jaeger UI → Distributed trace visualization")
    print("  3. Custom Analytics → Agent-specific insights")
    print("  4. OpenLIT Dashboard → LLM cost and performance analysis")

    print()


def main():
    """Main function."""
    print("🔍 DevOps Agent Tracing Overview")
    print("=" * 60)
    print()

    show_openlit_tracing_features()
    show_manual_tracing_capabilities()
    show_trace_configuration()
    show_trace_examples()
    show_trace_benefits()
    show_trace_data_flow()

    print("🔗 Next Steps:")
    print("  • View trace status: python scripts/tracing_status.py")
    print("  • Check metrics: python scripts/metrics_overview.py")
    print("  • View documentation: agents/devops/docs/TELEMETRY_CONFIGURATION.md")
    print("  • Run agent with tracing: ./run.sh")


if __name__ == "__main__":
    main()
