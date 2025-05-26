#!/usr/bin/env python3
"""
Simple Telemetry Configuration Checker

A lightweight script to check telemetry configuration without external dependencies.
For full dashboard functionality, use telemetry_dashboard.py with uv.

Usage:
    python3 scripts/telemetry_check.py
    uv run scripts/telemetry_check.py
"""

import os
import sys
import json
from datetime import datetime

def check_grafana_config():
    """Check Grafana Cloud configuration."""
    endpoint = os.getenv('GRAFANA_OTLP_ENDPOINT')
    token = os.getenv('GRAFANA_OTLP_TOKEN')
    
    print("🔍 Grafana Cloud Configuration Check")
    print("=" * 40)
    
    if endpoint:
        print(f"✅ GRAFANA_OTLP_ENDPOINT: {endpoint}")
    else:
        print("❌ GRAFANA_OTLP_ENDPOINT: Not set")
    
    if token:
        print(f"✅ GRAFANA_OTLP_TOKEN: {'*' * 20} (hidden)")
    else:
        print("❌ GRAFANA_OTLP_TOKEN: Not set")
    
    print()
    
    if endpoint and token:
        print("🎉 Grafana Cloud is properly configured!")
        print("📊 Telemetry will be exported to Grafana Cloud when the agent runs.")
        return True
    else:
        print("⚠️  Grafana Cloud is not configured.")
        print("💡 Set GRAFANA_OTLP_ENDPOINT and GRAFANA_OTLP_TOKEN for production monitoring.")
        print("🏠 Local development mode will be used instead.")
        return False

def check_openlit_config():
    """Check OpenLIT configuration."""
    app_name = os.getenv('OPENLIT_APPLICATION_NAME', 'DevOps Agent')
    environment = os.getenv('OPENLIT_ENVIRONMENT', 'Production')
    
    print("🔍 OpenLIT Configuration")
    print("=" * 25)
    print(f"📱 Application Name: {app_name}")
    print(f"🌍 Environment: {environment}")
    print()

def check_telemetry_modules():
    """Check if telemetry modules are available."""
    print("🔍 Telemetry Module Check")
    print("=" * 25)
    
    try:
        # Check if telemetry.py exists
        if os.path.exists('devops/telemetry.py'):
            print("✅ devops/telemetry.py: Found")
        else:
            print("❌ devops/telemetry.py: Not found")
            return False
            
        # Check if logging_config.py exists
        if os.path.exists('devops/logging_config.py'):
            print("✅ devops/logging_config.py: Found")
        else:
            print("❌ devops/logging_config.py: Not found")
            
        # Check if analytics.py exists
        if os.path.exists('devops/tools/analytics.py'):
            print("✅ devops/tools/analytics.py: Found")
        else:
            print("❌ devops/tools/analytics.py: Not found")
            
        print("✅ Telemetry modules are available")
        return True
        
    except Exception as e:
        print(f"❌ Error checking telemetry modules: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are available."""
    print("🔍 Dependency Check")
    print("=" * 18)
    
    dependencies = [
        ('openlit', 'LLM observability'),
        ('opentelemetry', 'OpenTelemetry core'),
        ('psutil', 'System monitoring'),
        ('rich', 'Console output (optional)')
    ]
    
    available = []
    missing = []
    
    for dep, description in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}: Available ({description})")
            available.append(dep)
        except ImportError:
            print(f"❌ {dep}: Missing ({description})")
            missing.append(dep)
    
    print()
    
    if missing:
        print("⚠️  Some dependencies are missing.")
        print("💡 Install with: uv add " + " ".join(missing))
        if 'openlit' in missing or 'opentelemetry' in missing:
            print("🚨 Core telemetry dependencies missing - telemetry may not work properly.")
    else:
        print("🎉 All dependencies are available!")
    
    return len(missing) == 0

def export_config_summary():
    """Export configuration summary to JSON."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "grafana_cloud": {
            "configured": bool(os.getenv('GRAFANA_OTLP_ENDPOINT') and os.getenv('GRAFANA_OTLP_TOKEN')),
            "endpoint": os.getenv('GRAFANA_OTLP_ENDPOINT', 'Not set'),
            "token_set": bool(os.getenv('GRAFANA_OTLP_TOKEN'))
        },
        "openlit": {
            "application_name": os.getenv('OPENLIT_APPLICATION_NAME', 'DevOps Agent'),
            "environment": os.getenv('OPENLIT_ENVIRONMENT', 'Production')
        },
        "modules": {
            "telemetry_py": os.path.exists('devops/telemetry.py'),
            "logging_config_py": os.path.exists('devops/logging_config.py'),
            "analytics_py": os.path.exists('devops/tools/analytics.py')
        }
    }
    
    filename = f"telemetry_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"📄 Configuration summary exported: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Failed to export summary: {e}")
        return None

def check_run_sh_dependencies():
    """Check if run.sh includes the necessary telemetry dependencies."""
    print("🔍 run.sh Dependencies Check")
    print("=" * 28)
    
    try:
        with open('run.sh', 'r') as f:
            content = f.read()
        
        required_deps = [
            'openlit',
            'opentelemetry-api',
            'opentelemetry-sdk', 
            'opentelemetry-exporter-otlp',
            'psutil',
            'rich'
        ]
        
        missing_deps = []
        for dep in required_deps:
            if dep in content:
                print(f"✅ {dep}: Found in run.sh")
            else:
                print(f"❌ {dep}: Missing from run.sh")
                missing_deps.append(dep)
        
        print()
        
        if missing_deps:
            print("⚠️  Some telemetry dependencies missing from run.sh")
            print(f"💡 Missing: {', '.join(missing_deps)}")
            return False
        else:
            print("🎉 All telemetry dependencies found in run.sh!")
            return True
            
    except FileNotFoundError:
        print("❌ run.sh not found")
        return False
    except Exception as e:
        print(f"❌ Error checking run.sh: {e}")
        return False

def main():
    """Main function."""
    print("🔍 DevOps Agent Telemetry Configuration Check")
    print("=" * 45)
    print()
    
    # Check all components
    grafana_ok = check_grafana_config()
    check_openlit_config()
    modules_ok = check_telemetry_modules()
    deps_ok = check_dependencies()
    runsh_ok = check_run_sh_dependencies()
    
    print("📋 Summary")
    print("=" * 10)
    
    if grafana_ok:
        print("🌐 Grafana Cloud: Ready for production monitoring")
    else:
        print("🏠 Local Mode: Development monitoring only")
    
    if modules_ok:
        print("📦 Telemetry Modules: Available")
    else:
        print("📦 Telemetry Modules: Missing or incomplete")
    
    if deps_ok:
        print("🔧 Dependencies: All satisfied")
    else:
        print("🔧 Dependencies: Some missing")
    
    print()
    
    # Export summary
    if len(sys.argv) > 1 and sys.argv[1] == 'export':
        export_config_summary()
    
    if runsh_ok:
        print("🚀 run.sh: Telemetry dependencies configured")
    else:
        print("🚀 run.sh: Missing telemetry dependencies")
    
    print()
    
    # Overall status
    if modules_ok and runsh_ok:
        print("🎉 Telemetry system is ready!")
        if grafana_ok:
            print("📊 Run './run.sh' to start with Grafana Cloud monitoring")
        else:
            print("📊 Run './run.sh' to start with local telemetry (set Grafana Cloud env vars for production)")
        print("📊 Test dependencies: uv run scripts/test_run_sh_telemetry.py")
    else:
        print("⚠️  Telemetry system needs configuration.")
        print("📖 See devops/docs/TELEMETRY_CONFIGURATION.md for setup instructions")

if __name__ == "__main__":
    main() 