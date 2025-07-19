#!/usr/bin/env python3
"""
DevOps Agent Metrics Overview
Shows all available metrics without requiring complex dependencies.
"""

import os


def show_openlit_metrics():
    """Show OpenLIT metrics that are automatically collected."""
    print("🤖 OpenLIT Auto-Instrumentation Metrics")
    print("=" * 50)
    
    print("📊 LLM/GenAI Metrics (Automatic):")
    llm_metrics = [
        "gen_ai.total.requests - Number of LLM requests",
        "gen_ai.usage.input_tokens - Input tokens processed",
        "gen_ai.usage.output_tokens - Output tokens processed",
        "gen_ai.usage.total_tokens - Total tokens processed", 
        "gen_ai.usage.cost - Cost distribution of LLM requests"
    ]
    for metric in llm_metrics:
        print(f"  • {metric}")
    
    print("\n🗄️  VectorDB Metrics (Automatic):")
    vectordb_metrics = [
        "db.total.requests - Number of VectorDB requests (ChromaDB)"
    ]
    for metric in vectordb_metrics:
        print(f"  • {metric}")
    
    # Check GPU configuration
    gpu_enabled = os.getenv('OPENLIT_COLLECT_GPU_STATS', 'true').lower() in ('true', '1', 'yes')
    print(f"\n🖥️  GPU Metrics ({'✅ Enabled' if gpu_enabled else '❌ Disabled'}):")
    
    if gpu_enabled:
        gpu_metrics = [
            "gpu.utilization - GPU utilization percentage",
            "gpu.memory.used - Used GPU memory in MB",
            "gpu.memory.available - Available GPU memory in MB", 
            "gpu.memory.total - Total GPU memory in MB",
            "gpu.memory.free - Free GPU memory in MB",
            "gpu.temperature - GPU temperature in Celsius",
            "gpu.power.draw - GPU power draw in Watts",
            "gpu.power.limit - GPU power limit in Watts",
            "gpu.fan_speed - GPU fan speed (0-100)"
        ]
        for metric in gpu_metrics:
            print(f"  • {metric}")
    else:
        print("  • Set OPENLIT_COLLECT_GPU_STATS=true to enable")
    
    print()

def show_custom_metrics():
    """Show custom agent metrics."""
    print("🔧 Custom DevOps Agent Metrics")
    print("=" * 50)
    
    print("📈 Counters:")
    counters = [
        "devops_agent_operations_total - Total operations by type and status",
        "devops_agent_errors_total - Total errors by operation and error type",
        "devops_agent_tokens_total - Total tokens consumed by model and type",
        "devops_agent_tool_usage_total - Total tool executions by tool type",
        "devops_agent_context_operations_total - Total context management operations"
    ]
    for metric in counters:
        print(f"  • {metric}")
    
    print("\n📊 Histograms:")
    histograms = [
        "devops_agent_operation_duration_seconds - Operation execution times",
        "devops_agent_llm_response_time_seconds - LLM response times by model",
        "devops_agent_context_size_tokens - Context sizes in tokens",
        "devops_agent_tool_execution_seconds - Tool execution times",
        "devops_agent_file_operation_bytes - File operation sizes"
    ]
    for metric in histograms:
        print(f"  • {metric}")
    
    print("\n📏 Gauges:")
    gauges = [
        "devops_agent_active_tools - Currently active tool executions",
        "devops_agent_context_cache_items - Number of items in context cache",
        "devops_agent_memory_usage_mb - Current memory usage",
        "devops_agent_cpu_usage_percent - Current CPU usage",
        "devops_agent_disk_usage_mb - Current disk usage",
        "devops_agent_avg_response_time - Rolling average response time"
    ]
    for metric in gauges:
        print(f"  • {metric}")
    
    print()

def show_configuration():
    """Show current configuration."""
    print("⚙️  Current Configuration")
    print("=" * 50)
    
    # OpenLIT Configuration
    print("🔍 OpenLIT Settings:")
    print(f"  Environment: {os.getenv('OPENLIT_ENVIRONMENT', 'Production')}")
    print(f"  GPU Monitoring: {os.getenv('OPENLIT_COLLECT_GPU_STATS', 'true')}")
    print(f"  Metrics Disabled: {os.getenv('OPENLIT_DISABLE_METRICS', 'false')}")
    
    # Grafana Cloud Configuration
    print("\n☁️  Grafana Cloud Export:")
    endpoint = os.getenv('GRAFANA_OTLP_ENDPOINT')
    token = os.getenv('GRAFANA_OTLP_TOKEN')
    export_disabled = os.getenv('DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT', 'false')
    
    if export_disabled.lower() in ('true', '1', 'yes'):
        print("  Status: ❌ Disabled via DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT")
    elif endpoint and token:
        print("  Status: ✅ Configured")
        print(f"  Endpoint: {endpoint}")
        print(f"  Export Interval: {os.getenv('GRAFANA_EXPORT_INTERVAL_SECONDS', '120')}s")
        print(f"  Export Timeout: {os.getenv('GRAFANA_EXPORT_TIMEOUT_SECONDS', '30')}s")
    else:
        print("  Status: ⚠️  Not configured (local metrics only)")
    
    print()

def show_total_metrics_count():
    """Show total number of metrics available."""
    print("📊 Metrics Summary")
    print("=" * 50)
    
    # Count OpenLIT metrics
    openlit_llm = 5  # gen_ai metrics
    openlit_vectordb = 1  # db.total.requests
    openlit_gpu = 9 if os.getenv('OPENLIT_COLLECT_GPU_STATS', 'true').lower() in ('true', '1', 'yes') else 0
    
    # Count custom metrics
    custom_counters = 5
    custom_histograms = 5
    custom_gauges = 6
    
    total_openlit = openlit_llm + openlit_vectordb + openlit_gpu
    total_custom = custom_counters + custom_histograms + custom_gauges
    total_all = total_openlit + total_custom
    
    print(f"🤖 OpenLIT Metrics: {total_openlit}")
    print(f"  • LLM/GenAI: {openlit_llm}")
    print(f"  • VectorDB: {openlit_vectordb}")
    print(f"  • GPU: {openlit_gpu}")
    
    print(f"\n🔧 Custom Agent Metrics: {total_custom}")
    print(f"  • Counters: {custom_counters}")
    print(f"  • Histograms: {custom_histograms}")
    print(f"  • Gauges: {custom_gauges}")
    
    print(f"\n🎯 Total Available Metrics: {total_all}")
    
    print()

def main():
    """Main function."""
    print("📊 DevOps Agent Metrics Overview")
    print("=" * 60)
    print()
    
    show_total_metrics_count()
    show_openlit_metrics()
    show_custom_metrics()
    show_configuration()
    
    print("🔗 Next Steps:")
    print("  • Check detailed status: python scripts/metrics_status.py")
    print("  • Fix rate limits: ./scripts/fix_rate_limits.sh")
    print("  • View documentation: agents/devops/docs/TELEMETRY_CONFIGURATION.md")
    print("  • Run agent: ./run.sh")

if __name__ == "__main__":
    main() 