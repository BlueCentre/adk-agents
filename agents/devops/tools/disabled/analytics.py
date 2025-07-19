"""Tool performance analytics for DevOps Agent."""

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple

from ...telemetry import telemetry

# from ..logging_config import log_tool_usage, log_performance_metrics


@dataclass
class ToolExecutionRecord:
    """Record of a tool execution."""

    tool_name: str
    start_time: float
    end_time: float
    duration: float
    input_size: int
    output_size: int
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    context_data: dict[str, Any] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class ToolPerformanceMetrics:
    """Performance metrics for a tool."""

    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration: float
    median_duration: float
    p95_duration: float
    p99_duration: float
    avg_input_size: float
    avg_output_size: float
    efficiency_score: float  # output/input ratio
    error_patterns: dict[str, int]
    usage_trend: list[int]  # executions per hour over last 24h


class ToolAnalytics:
    """Comprehensive tool analytics and performance monitoring."""

    def __init__(self, max_records: int = 10000):
        self.max_records = max_records
        self.execution_records: deque = deque(maxlen=max_records)
        self.tool_metrics: dict[str, ToolPerformanceMetrics] = {}
        self.usage_patterns: dict[str, list[float]] = defaultdict(list)
        self.error_analysis: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Performance baselines
        self.performance_baselines: dict[str, dict[str, float]] = {}

        # Load existing data if available
        self._load_analytics_data()

    def record_tool_execution(
        self,
        tool_name: str,
        start_time: float,
        end_time: float,
        input_size: int,
        output_size: int,
        success: bool,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """Record a tool execution for analytics."""

        duration = end_time - start_time

        record = ToolExecutionRecord(
            tool_name=tool_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            input_size=input_size,
            output_size=output_size,
            success=success,
            error_type=error_type,
            error_message=error_message,
            context_data=context_data or {},
            user_id=user_id,
            correlation_id=correlation_id,
        )

        self.execution_records.append(record)

        # Update real-time metrics
        self._update_tool_metrics(record)

        # Log for external systems
        log_tool_usage(
            tool_name=tool_name,
            input_size=input_size,
            output_size=output_size,
            duration=duration,
            success=success,
            error_type=error_type,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        # Send to telemetry
        telemetry.track_tool_execution(tool_name)

    def _update_tool_metrics(self, record: ToolExecutionRecord):
        """Update metrics for a specific tool."""
        tool_name = record.tool_name

        # Get recent records for this tool (last 1000)
        recent_records = [
            r for r in list(self.execution_records)[-1000:] if r.tool_name == tool_name
        ]

        if not recent_records:
            return

        # Calculate metrics
        total_executions = len(recent_records)
        successful_executions = sum(1 for r in recent_records if r.success)
        failed_executions = total_executions - successful_executions
        success_rate = successful_executions / total_executions if total_executions > 0 else 0

        durations = [r.duration for r in recent_records]
        input_sizes = [r.input_size for r in recent_records]
        output_sizes = [r.output_size for r in recent_records]

        avg_duration = statistics.mean(durations) if durations else 0
        median_duration = statistics.median(durations) if durations else 0
        p95_duration = self._percentile(durations, 95) if durations else 0
        p99_duration = self._percentile(durations, 99) if durations else 0

        avg_input_size = statistics.mean(input_sizes) if input_sizes else 0
        avg_output_size = statistics.mean(output_sizes) if output_sizes else 0

        # Calculate efficiency score
        total_input = sum(input_sizes)
        total_output = sum(output_sizes)
        efficiency_score = total_output / max(1, total_input)

        # Error patterns
        error_patterns = defaultdict(int)
        for r in recent_records:
            if not r.success and r.error_type:
                error_patterns[r.error_type] += 1

        # Usage trend (executions per hour over last 24h)
        now = time.time()
        usage_trend = []
        for i in range(24):
            hour_start = now - (i + 1) * 3600
            hour_end = now - i * 3600
            hour_count = sum(1 for r in recent_records if hour_start <= r.start_time < hour_end)
            usage_trend.append(hour_count)
        usage_trend.reverse()  # Chronological order

        # Update metrics
        self.tool_metrics[tool_name] = ToolPerformanceMetrics(
            tool_name=tool_name,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            success_rate=success_rate,
            avg_duration=avg_duration,
            median_duration=median_duration,
            p95_duration=p95_duration,
            p99_duration=p99_duration,
            avg_input_size=avg_input_size,
            avg_output_size=avg_output_size,
            efficiency_score=efficiency_score,
            error_patterns=dict(error_patterns),
            usage_trend=usage_trend,
        )

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        lower = sorted_data[int(index)]
        upper = sorted_data[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))

    def get_tool_performance_report(self, tool_name: str) -> Optional[dict[str, Any]]:
        """Get comprehensive performance report for a specific tool."""
        if tool_name not in self.tool_metrics:
            return None

        metrics = self.tool_metrics[tool_name]

        # Get baseline comparison if available
        baseline_comparison = {}
        if tool_name in self.performance_baselines:
            baseline = self.performance_baselines[tool_name]
            baseline_comparison = {
                "duration_change": (
                    (metrics.avg_duration - baseline.get("avg_duration", 0))
                    / max(baseline.get("avg_duration", 1), 0.001)
                )
                * 100,
                "success_rate_change": metrics.success_rate - baseline.get("success_rate", 0),
                "efficiency_change": (
                    (metrics.efficiency_score - baseline.get("efficiency_score", 0))
                    / max(baseline.get("efficiency_score", 1), 0.001)
                )
                * 100,
            }

        # Identify performance issues
        issues = []
        if metrics.success_rate < 0.95:
            issues.append(f"Low success rate: {metrics.success_rate:.1%}")
        if metrics.p95_duration > metrics.avg_duration * 3:
            issues.append("High latency variance")
        if metrics.efficiency_score < 0.5:
            issues.append("Low efficiency score")

        return {
            "tool_name": tool_name,
            "metrics": asdict(metrics),
            "baseline_comparison": baseline_comparison,
            "performance_issues": issues,
            "recommendations": self._generate_recommendations(metrics),
        }

    def _generate_recommendations(self, metrics: ToolPerformanceMetrics) -> list[str]:
        """Generate performance recommendations."""
        recommendations = []

        if metrics.success_rate < 0.9:
            recommendations.append("Investigate error patterns and implement retry logic")

        if metrics.p95_duration > metrics.avg_duration * 2:
            recommendations.append("Consider timeout optimization or caching")

        if metrics.efficiency_score < 1.0:
            recommendations.append("Review input processing to improve output quality")

        if len(metrics.error_patterns) > 3:
            recommendations.append("Consolidate error handling for better reliability")

        most_common_error = max(
            metrics.error_patterns.items(), key=lambda x: x[1], default=(None, 0)
        )
        if most_common_error[1] > metrics.total_executions * 0.1:
            recommendations.append(f"Address recurring error: {most_common_error[0]}")

        return recommendations

    def get_overall_analytics(self) -> dict[str, Any]:
        """Get overall tool analytics summary."""
        if not self.execution_records:
            return {"message": "No execution data available"}

        # Overall statistics
        total_executions = len(self.execution_records)
        successful_executions = sum(1 for r in self.execution_records if r.success)
        overall_success_rate = successful_executions / total_executions

        # Tool usage distribution
        tool_usage = defaultdict(int)
        tool_durations = defaultdict(list)

        for record in self.execution_records:
            tool_usage[record.tool_name] += 1
            tool_durations[record.tool_name].append(record.duration)

        # Top performing tools
        top_tools = sorted(
            self.tool_metrics.items(),
            key=lambda x: x[1].success_rate * x[1].total_executions,
            reverse=True,
        )[:10]

        # Performance trends
        recent_records = list(self.execution_records)[-1000:]
        hourly_performance = self._calculate_hourly_performance(recent_records)

        return {
            "summary": {
                "total_executions": total_executions,
                "overall_success_rate": overall_success_rate,
                "total_tools": len(self.tool_metrics),
                "avg_execution_time": statistics.mean([r.duration for r in self.execution_records]),
            },
            "tool_usage_distribution": dict(tool_usage),
            "top_performing_tools": [(name, asdict(metrics)) for name, metrics in top_tools],
            "hourly_performance": hourly_performance,
            "system_health": self._assess_system_health(),
        }

    def _calculate_hourly_performance(
        self, records: list[ToolExecutionRecord]
    ) -> dict[str, list[float]]:
        """Calculate performance metrics by hour."""
        now = time.time()
        hourly_data = {"executions": [], "success_rates": [], "avg_durations": []}

        for i in range(24):
            hour_start = now - (i + 1) * 3600
            hour_end = now - i * 3600

            hour_records = [r for r in records if hour_start <= r.start_time < hour_end]

            if hour_records:
                executions = len(hour_records)
                successes = sum(1 for r in hour_records if r.success)
                success_rate = successes / executions
                avg_duration = statistics.mean([r.duration for r in hour_records])
            else:
                executions = 0
                success_rate = 0
                avg_duration = 0

            hourly_data["executions"].append(executions)
            hourly_data["success_rates"].append(success_rate)
            hourly_data["avg_durations"].append(avg_duration)

        # Reverse to get chronological order
        for key in hourly_data:
            hourly_data[key].reverse()

        return hourly_data

    def _assess_system_health(self) -> dict[str, Any]:
        """Assess overall system health based on analytics."""
        if not self.tool_metrics:
            return {"status": "unknown", "message": "Insufficient data"}

        # Calculate health scores
        avg_success_rate = statistics.mean([m.success_rate for m in self.tool_metrics.values()])
        avg_efficiency = statistics.mean([m.efficiency_score for m in self.tool_metrics.values()])

        # Determine health status
        health_score = (avg_success_rate * 0.6 + min(avg_efficiency, 1.0) * 0.4) * 100

        if health_score >= 90:
            status = "excellent"
        elif health_score >= 80:
            status = "good"
        elif health_score >= 70:
            status = "fair"
        else:
            status = "poor"

        # Identify concerning trends
        concerns = []
        failing_tools = [
            name for name, metrics in self.tool_metrics.items() if metrics.success_rate < 0.8
        ]
        if failing_tools:
            concerns.append(f"Tools with low success rates: {', '.join(failing_tools)}")

        slow_tools = [
            name for name, metrics in self.tool_metrics.items() if metrics.p95_duration > 30.0
        ]  # 30 seconds
        if slow_tools:
            concerns.append(f"Slow-performing tools: {', '.join(slow_tools)}")

        return {
            "status": status,
            "health_score": health_score,
            "avg_success_rate": avg_success_rate,
            "avg_efficiency": avg_efficiency,
            "concerns": concerns,
        }

    def set_performance_baseline(self, tool_name: str):
        """Set current performance as baseline for a tool."""
        if tool_name in self.tool_metrics:
            metrics = self.tool_metrics[tool_name]
            self.performance_baselines[tool_name] = {
                "avg_duration": metrics.avg_duration,
                "success_rate": metrics.success_rate,
                "efficiency_score": metrics.efficiency_score,
                "baseline_date": time.time(),
            }

    def export_analytics_data(self, filepath: str):
        """Export analytics data to file."""
        data = {
            "export_time": time.time(),
            "tool_metrics": {name: asdict(metrics) for name, metrics in self.tool_metrics.items()},
            "performance_baselines": self.performance_baselines,
            "execution_records": [
                asdict(record) for record in list(self.execution_records)[-1000:]
            ],  # Last 1000
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_analytics_data(self):
        """Load existing analytics data."""
        try:
            analytics_file = Path("devops_agent_analytics.json")
            if analytics_file.exists():
                with open(analytics_file) as f:
                    data = json.load(f)

                # Load baselines
                self.performance_baselines = data.get("performance_baselines", {})

                # Load recent execution records
                records_data = data.get("execution_records", [])[-1000:]  # Last 1000
                for record_data in records_data:
                    record = ToolExecutionRecord(**record_data)
                    self.execution_records.append(record)

                # Rebuild metrics from loaded records
                for record in self.execution_records:
                    self._update_tool_metrics(record)

        except Exception as e:
            log_performance_metrics("analytics_load", 0, error=str(e))

    def save_analytics_data(self):
        """Save analytics data to file."""
        try:
            self.export_analytics_data("devops_agent_analytics.json")
        except Exception as e:
            log_performance_metrics("analytics_save", 0, error=str(e))


# Global analytics instance
tool_analytics = ToolAnalytics()


def track_tool_execution(tool_name: str):
    """Decorator to automatically track tool execution analytics."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            input_size = len(str(args) + str(kwargs))
            success = False
            error_type = None
            error_message = None

            try:
                result = func(*args, **kwargs)
                success = True
                output_size = len(str(result))
                return result
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                output_size = 0
                raise
            finally:
                end_time = time.time()
                tool_analytics.record_tool_execution(
                    tool_name=tool_name,
                    start_time=start_time,
                    end_time=end_time,
                    input_size=input_size,
                    output_size=output_size,
                    success=success,
                    error_type=error_type,
                    error_message=error_message,
                )

        return wrapper

    return decorator
