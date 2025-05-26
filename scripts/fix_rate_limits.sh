#!/bin/bash

# DevOps Agent Rate Limit Fix Script
# This script helps resolve Grafana Cloud rate limiting issues

echo "🔧 DevOps Agent Rate Limit Fix"
echo "================================"

# Check current configuration
echo "📊 Current Configuration:"
echo "  GRAFANA_OTLP_ENDPOINT: ${GRAFANA_OTLP_ENDPOINT:-'Not set'}"
echo "  GRAFANA_OTLP_TOKEN: ${GRAFANA_OTLP_TOKEN:+'Set (hidden)'}"
echo "  GRAFANA_EXPORT_INTERVAL_SECONDS: ${GRAFANA_EXPORT_INTERVAL_SECONDS:-'120 (default)'}"
echo "  DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT: ${DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT:-'false (default)'}"
echo ""

# Offer solutions
echo "🚨 Rate Limiting Solutions:"
echo ""
echo "1. Disable telemetry export (recommended for development)"
echo "   export DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true"
echo ""
echo "2. Increase export interval to 5 minutes"
echo "   export GRAFANA_EXPORT_INTERVAL_SECONDS=300"
echo ""
echo "3. Increase export interval to 10 minutes"
echo "   export GRAFANA_EXPORT_INTERVAL_SECONDS=600"
echo ""
echo "4. Remove Grafana Cloud credentials temporarily"
echo "   unset GRAFANA_OTLP_ENDPOINT"
echo "   unset GRAFANA_OTLP_TOKEN"
echo ""

# Interactive fix
read -p "🤔 Which solution would you like to apply? (1-4, or 'q' to quit): " choice

case $choice in
    1)
        echo "✅ Disabling telemetry export..."
        export DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true
        echo "   Set DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true"
        echo "   Add this to your shell profile to make it permanent:"
        echo "   echo 'export DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true' >> ~/.bashrc"
        ;;
    2)
        echo "✅ Setting export interval to 5 minutes..."
        export GRAFANA_EXPORT_INTERVAL_SECONDS=300
        echo "   Set GRAFANA_EXPORT_INTERVAL_SECONDS=300"
        echo "   Add this to your shell profile to make it permanent:"
        echo "   echo 'export GRAFANA_EXPORT_INTERVAL_SECONDS=300' >> ~/.bashrc"
        ;;
    3)
        echo "✅ Setting export interval to 10 minutes..."
        export GRAFANA_EXPORT_INTERVAL_SECONDS=600
        echo "   Set GRAFANA_EXPORT_INTERVAL_SECONDS=600"
        echo "   Add this to your shell profile to make it permanent:"
        echo "   echo 'export GRAFANA_EXPORT_INTERVAL_SECONDS=600' >> ~/.bashrc"
        ;;
    4)
        echo "✅ Removing Grafana Cloud credentials..."
        unset GRAFANA_OTLP_ENDPOINT
        unset GRAFANA_OTLP_TOKEN
        echo "   Unset GRAFANA_OTLP_ENDPOINT and GRAFANA_OTLP_TOKEN"
        echo "   This is temporary - credentials will be restored when you restart your shell"
        ;;
    q|Q)
        echo "👋 No changes made. Exiting..."
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. No changes made."
        exit 1
        ;;
esac

echo ""
echo "🎉 Configuration updated! You can now run the agent:"
echo "   ./run.sh"
echo ""
echo "📚 For more information, see: devops/docs/TELEMETRY_CONFIGURATION.md" 