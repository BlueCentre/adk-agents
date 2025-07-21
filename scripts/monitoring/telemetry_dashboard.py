#!/usr/bin/env python3
"""
DevOps Agent Telemetry Dashboard

A development tool for monitoring telemetry when not using Grafana Cloud.
For production environments, telemetry data is automatically exported to Grafana Cloud.

Usage:
    uv run scripts/telemetry_dashboard.py live
    uv run scripts/telemetry_dashboard.py summary
    uv run scripts/telemetry_dashboard.py export
"""

import os
from pathlib import Path
import sys

# Add the project root to the path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from datetime import datetime
import json
from typing import Any, Optional

try:
    # Rich console for beautiful output
    from rich import box
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print("⚠️ Rich not available - install with: uv add rich")
    sys.exit(1)

# Import our telemetry components (conditional for dev environments)
try:
    # Try to import telemetry directly without going through devops.__init__
    import importlib.util

    # Import telemetry module directly
    telemetry_spec = importlib.util.spec_from_file_location(
        "telemetry", "agents/devops/telemetry.py"
    )
    telemetry_module = importlib.util.module_from_spec(telemetry_spec)
    telemetry_spec.loader.exec_module(telemetry_module)

    telemetry = telemetry_module.telemetry
    OperationType = telemetry_module.OperationType

    # Try to import other modules
    try:
        logging_spec = importlib.util.spec_from_file_location(
            "logging_config", "agents/devops/disabled/logging_config.py"
        )
        logging_module = importlib.util.module_from_spec(logging_spec)
        logging_spec.loader.exec_module(logging_module)
        log_performance_metrics = logging_module.log_performance_metrics
        log_business_event = logging_module.log_business_event
    except Exception:
        log_performance_metrics = None
        log_business_event = None

    try:
        analytics_spec = importlib.util.spec_from_file_location(
            "analytics", "agents/devops/tools/disabled/analytics.py"
        )
        analytics_module = importlib.util.module_from_spec(analytics_spec)
        analytics_spec.loader.exec_module(analytics_module)
        tool_analytics = analytics_module.tool_analytics
    except Exception:
        tool_analytics = None

    TELEMETRY_AVAILABLE = True
    print("✅ Telemetry modules loaded successfully")

except Exception as e:
    print(f"⚠️ Telemetry modules not available: {e}")
    print("This dashboard is for development use when telemetry modules are present.")
    TELEMETRY_AVAILABLE = False
    telemetry = None
    OperationType = None
    log_performance_metrics = None
    log_business_event = None
    tool_analytics = None

console = Console()


class TelemetryDashboard:
    """Development telemetry dashboard for local monitoring."""

    def __init__(self):
        self.console = console
        self.refresh_interval = 5.0  # seconds
        self.running = False

        if not TELEMETRY_AVAILABLE:
            self.console.print("[red]❌ Telemetry modules not available[/red]")
            self.console.print("This dashboard requires the DevOps agent telemetry modules.")
            return

        # Check if Grafana Cloud is configured
        grafana_endpoint = os.getenv("GRAFANA_OTLP_ENDPOINT")
        if grafana_endpoint:
            self.console.print(f"[green]✅ Grafana Cloud configured: {grafana_endpoint}[/green]")
            self.console.print("[dim]Production metrics are being exported to Grafana Cloud[/dim]")
        else:
            self.console.print(
                "[yellow]📊 Local development mode - no Grafana Cloud export[/yellow]"
            )

    def display_header(self) -> Panel:
        """Create the dashboard header."""
        grafana_status = (
            "🌐 Grafana Cloud" if os.getenv("GRAFANA_OTLP_ENDPOINT") else "🏠 Local Dev Mode"
        )

        title = Text("🔍 DevOps Agent Telemetry Dashboard", style="bold blue")
        subtitle = Text(f"Development Monitoring Tool | {grafana_status}", style="dim")

        header_text = Align.center(f"{title}\n{subtitle}")

        return Panel(
            header_text,
            box=box.DOUBLE,
            style="bright_blue",
            title="[bold white]Local Development Dashboard[/bold white]",
            title_align="center",
        )

    def get_grafana_info(self) -> dict[str, Any]:
        """Get Grafana Cloud configuration info."""
        endpoint = os.getenv("GRAFANA_OTLP_ENDPOINT")
        if endpoint:
            return {
                "status": "✅ Configured",
                "endpoint": endpoint,
                "note": "Production metrics exported to Grafana Cloud",
            }
        return {
            "status": "📊 Local Only",
            "endpoint": "Not configured",
            "note": "Set GRAFANA_OTLP_ENDPOINT and GRAFANA_OTLP_TOKEN for production export",
        }

    def create_metrics_table(self) -> Table:
        """Create table showing current metrics."""
        if not TELEMETRY_AVAILABLE:
            table = Table(title="❌ Telemetry Not Available")
            table.add_column("Info")
            table.add_row("Telemetry modules not imported")
            return table

        table = Table(title="📊 Current Telemetry Metrics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")

        try:
            summary = telemetry.get_performance_summary()
            current_metrics = summary.get("current_metrics", {})

            table.add_row(
                "Memory Usage",
                f"{current_metrics.get('memory_usage_mb', 0):.1f} MB",
                "Current process memory",
            )

            table.add_row(
                "Operations",
                f"{current_metrics.get('total_operations', 0):,}",
                "Total operations tracked",
            )

            table.add_row(
                "Error Rate", f"{summary.get('error_rate', 0):.2%}", "Operation failure rate"
            )

            table.add_row(
                "Response Time",
                f"{current_metrics.get('average_response_time', 0):.3f}s",
                "Average operation duration",
            )

        except Exception as e:
            table.add_row("Error", str(e), "Failed to fetch metrics")

        return table

    def create_grafana_panel(self) -> Panel:
        """Create Grafana Cloud status panel."""
        grafana_info = self.get_grafana_info()

        content = f"[bold]Status:[/bold] {grafana_info['status']}\n"
        content += f"[bold]Endpoint:[/bold] {grafana_info['endpoint']}\n\n"
        content += f"[dim]{grafana_info['note']}[/dim]"

        style = "bright_green" if "✅" in grafana_info["status"] else "yellow"

        return Panel(content, title="🌐 Grafana Cloud Integration", box=box.ROUNDED, style=style)

    def display_static_summary(self):
        """Display a static summary for development."""
        if not TELEMETRY_AVAILABLE:
            console.print("[red]Telemetry modules not available for summary[/red]")
            return

        console.print(self.display_header())
        console.print()
        console.print(self.create_metrics_table())
        console.print()
        console.print(self.create_grafana_panel())

    def export_dev_metrics(self, filename: Optional[str] = None):
        """Export development metrics to file."""
        if not TELEMETRY_AVAILABLE:
            console.print("[red]Cannot export - telemetry not available[/red]")
            return None

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dev_metrics_{timestamp}.json"

        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "mode": "development",
                "grafana_cloud": self.get_grafana_info(),
                "telemetry_summary": telemetry.get_performance_summary()
                if TELEMETRY_AVAILABLE
                else {},
            }

            with Path(filename).open("w") as f:
                json.dump(report, f, indent=2, default=str)

            console.print(f"[green]✅ Development metrics exported: {filename}[/green]")
            return filename

        except Exception as e:
            console.print(f"[red]❌ Export failed: {e}[/red]")
            return None


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="DevOps Agent Development Dashboard")
    parser.add_argument(
        "command", choices=["summary", "export", "grafana-check"], help="Command to run"
    )
    parser.add_argument("--output", help="Output filename for export command")

    args = parser.parse_args()

    dashboard = TelemetryDashboard()

    try:
        if args.command == "summary":
            dashboard.display_static_summary()

        elif args.command == "export":
            dashboard.export_dev_metrics(args.output)

        elif args.command == "grafana-check":
            info = dashboard.get_grafana_info()
            console.print(f"Grafana Cloud Status: {info['status']}")
            console.print(f"Endpoint: {info['endpoint']}")
            console.print(f"Note: {info['note']}")

    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Dashboard stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == "__main__":
    main()
