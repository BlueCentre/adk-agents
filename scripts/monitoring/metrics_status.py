#!/usr/bin/env python3
"""
DevOps Agent Metrics Status Checker
Shows the status of all available metrics including OpenLIT and custom metrics.
"""

import os
import sys
sys.path.insert(0, '.')

def check_openlit_status():
    """Check OpenLIT configuration status."""
    print("🔍 OpenLIT Configuration Status")
    print("=" * 40)
    
    # Check environment variables
    environment = os.getenv('OPENLIT_ENVIRONMENT', 'Production')
    gpu_stats = os.getenv('OPENLIT_COLLECT_GPU_STATS', 'true').lower() in ('true', '1', 'yes')
    metrics_disabled = os.getenv('OPENLIT_DISABLE_METRICS', 'false').lower() in ('true', '1', 'yes')
    
    print(f"Environment: {environment}")
    print(f"GPU Monitoring: {'✅ Enabled' if gpu_stats else '❌ Disabled'}")
    print(f"Metrics Collection: {'❌ Disabled' if metrics_disabled else '✅ Enabled'}")
    
    # Check GPU availability
    try:
        import nvidia_ml_py3 as nvml
        nvml.nvmlInit()
        gpu_count = nvml.nvmlDeviceGetCount()
        print(f"GPU Devices Found: {gpu_count}")
        
        if gpu_count > 0 and gpu_stats:
            print("📊 Available GPU Metrics:")
            gpu_metrics = [
                "gpu.utilization", "gpu.memory.used", "gpu.memory.available",
                "gpu.memory.total", "gpu.memory.free", "gpu.temperature",
                "gpu.power.draw", "gpu.power.limit", "gpu.fan_speed"
            ]
            for metric in gpu_metrics:
                print(f"  • {metric}")
    except ImportError:
        print("GPU Monitoring: ⚠️  nvidia-ml-py3 not available")
    except Exception as e:
        print(f"GPU Monitoring: ⚠️  Error checking GPU: {e}")
    
    print()

def check_custom_metrics_status():
    """Check custom metrics configuration."""
    print("🛠️  Custom Agent Metrics Status")
    print("=" * 40)
    
    try:
        from agents.devops.telemetry import get_openlit_metrics_status
        status = get_openlit_metrics_status()
        
        print("📈 Available Metric Categories:")
        
        # LLM Metrics
        print("\n🤖 LLM/GenAI Metrics (OpenLIT):")
        for metric in status["available_metrics"]["llm_metrics"]:
            print(f"  • {metric}")
        
        # VectorDB Metrics  
        print("\n🗄️  VectorDB Metrics (OpenLIT):")
        for metric in status["available_metrics"]["vectordb_metrics"]:
            print(f"  • {metric}")
        
        # GPU Metrics
        if status["available_metrics"]["gpu_metrics"]:
            print("\n🖥️  GPU Metrics (OpenLIT):")
            for metric in status["available_metrics"]["gpu_metrics"]:
                print(f"  • {metric}")
        else:
            print("\n🖥️  GPU Metrics: ❌ Disabled or unavailable")
        
        # Custom Agent Metrics
        print("\n🔧 Custom Agent Metrics:")
        for metric in status["available_metrics"]["custom_agent_metrics"]:
            print(f"  • {metric}")
            
    except ImportError as e:
        print(f"❌ Error importing telemetry module: {e}")
        print("💡 Make sure you're running from the project root directory")
    
    print()

def check_grafana_cloud_status():
    """Check Grafana Cloud export configuration."""
    print("☁️  Grafana Cloud Export Status")
    print("=" * 40)
    
    endpoint = os.getenv('GRAFANA_OTLP_ENDPOINT')
    token = os.getenv('GRAFANA_OTLP_TOKEN')
    export_disabled = os.getenv('DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT', '').lower() in ('true', '1', 'yes')
    export_interval = os.getenv('GRAFANA_EXPORT_INTERVAL_SECONDS', '120')
    export_timeout = os.getenv('GRAFANA_EXPORT_TIMEOUT_SECONDS', '30')
    
    if export_disabled:
        print("Status: ❌ Export disabled via DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT")
    elif endpoint and token:
        print("Status: ✅ Configured for Grafana Cloud export")
        print(f"Endpoint: {endpoint}")
        print(f"Token: {'Set (hidden)' if token else 'Not set'}")
        print(f"Export Interval: {export_interval} seconds")
        print(f"Export Timeout: {export_timeout} seconds")
    else:
        print("Status: ⚠️  Not configured (local metrics only)")
        print("Missing: GRAFANA_OTLP_ENDPOINT and/or GRAFANA_OTLP_TOKEN")
    
    print()

def show_recommendations():
    """Show recommendations based on current configuration."""
    print("💡 Recommendations")
    print("=" * 40)
    
    recommendations = []
    
    # Check for rate limiting risk
    export_interval = int(os.getenv('GRAFANA_EXPORT_INTERVAL_SECONDS', '120'))
    if export_interval < 300:
        recommendations.append("Consider increasing GRAFANA_EXPORT_INTERVAL_SECONDS to 300+ for rate limiting")
    
    # Check GPU monitoring
    gpu_stats = os.getenv('OPENLIT_COLLECT_GPU_STATS', 'true').lower() in ('true', '1', 'yes')
    if not gpu_stats:
        recommendations.append("Enable GPU monitoring with OPENLIT_COLLECT_GPU_STATS=true if you have GPU")
    
    # Check environment
    environment = os.getenv('OPENLIT_ENVIRONMENT', 'Production')
    if environment == 'Production':
        recommendations.append("Consider setting OPENLIT_ENVIRONMENT=Development for local development")
    
    # Check export status
    export_disabled = os.getenv('DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT', '').lower() in ('true', '1', 'yes')
    endpoint = os.getenv('GRAFANA_OTLP_ENDPOINT')
    if not export_disabled and not endpoint:
        recommendations.append("Set up Grafana Cloud credentials or disable export for development")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("✅ Configuration looks good!")
    
    print()

def main():
    """Main function to run all checks."""
    print("📊 DevOps Agent Metrics Status Report")
    print("=" * 50)
    print()
    
    check_openlit_status()
    check_custom_metrics_status()
    check_grafana_cloud_status()
    show_recommendations()
    
    print("🔗 For more information:")
    print("  • Documentation: agents/devops/docs/TELEMETRY_CONFIGURATION.md")
    print("  • Rate limit fixes: ./scripts/fix_rate_limits.sh")
    print("  • Local dashboard: uvx --with rich --with psutil python scripts/telemetry_dashboard.py")

if __name__ == "__main__":
    main() 