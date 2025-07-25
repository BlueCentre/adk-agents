#!/usr/bin/env python3
"""
Comprehensive Integration Test Runner

This script runs all integration tests for the ADK agents system in the correct
order and provides detailed reporting of test results, performance metrics,
and coverage analysis.
"""

import argparse
import asyncio
from asyncio import subprocess
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import time

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestResult:
    """Container for test execution results."""

    def __init__(
        self,
        name: str,
        passed: bool,
        duration: float,
        output: str = "",
        error: str = "",
    ):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.output = output
        self.error = error

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "passed": self.passed,
            "duration": self.duration,
            "output": self.output,
            "error": self.error,
        }


class TestSuite:
    """Container for a group of related tests."""

    def __init__(self, name: str, description: str, tests: list[str]):
        self.name = name
        self.description = description
        self.tests = tests
        self.results: list[TestResult] = []
        self.total_duration = 0.0
        self.passed_count = 0
        self.failed_count = 0

    def add_result(self, result: TestResult):
        """Add a test result to this suite."""
        self.results.append(result)
        self.total_duration += result.duration
        if result.passed:
            self.passed_count += 1
        else:
            self.failed_count += 1

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.passed_count + self.failed_count
        return (self.passed_count / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "tests": self.tests,
            "results": [r.to_dict() for r in self.results],
            "total_duration": self.total_duration,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "success_rate": self.success_rate(),
        }


class IntegrationTestRunner:
    """Comprehensive integration test runner."""

    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.project_root = Path(__file__).parent.parent.parent
        self.test_suites: list[TestSuite] = []
        self.start_time = None
        self.end_time = None

        # Define test suites in execution order
        self._define_test_suites()

    def _define_test_suites(self):
        """Define all test suites and their execution order."""

        # Phase 1: Foundation Tests
        self.test_suites.append(
            TestSuite(
                name="Foundation Tests",
                description="Basic agent lifecycle and workflow orchestration tests",
                tests=[
                    "tests/integration/test_agent_lifecycle.py::TestAgentLifecycle::test_complete_turn_execution",
                    "tests/integration/test_agent_lifecycle.py::TestAgentLifecycle::test_multi_turn_context_flow",
                    "tests/integration/test_agent_lifecycle.py::TestAgentLifecycle::test_context_prioritization",
                    "tests/integration/test_agent_lifecycle.py::TestAgentLifecycle::test_token_budget_management",
                    "tests/integration/test_workflow_integration.py::TestSequentialWorkflows::test_feature_development_workflow",
                    "tests/integration/test_workflow_integration.py::TestParallelWorkflows::test_concurrent_analysis_workflow",
                    "tests/integration/test_workflow_integration.py::TestIterativeWorkflows::test_quality_refinement_workflow",
                    "tests/integration/test_workflow_integration.py::TestHumanInLoopWorkflows::test_approval_workflow",
                ],
            )
        )

        # Phase 1.5: Core ADK Pattern Tests
        self.test_suites.append(
            TestSuite(
                name="Core ADK Pattern Tests",
                description="Google ADK-style integration tests for core agent patterns",
                tests=[
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_single_agent_basic_response_structure",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_single_agent_instruction_structure",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_single_agent_tool_availability",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_single_agent_model_configuration",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_single_agent_sub_agent_structure",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_agent_class_structure",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_agent_output_capabilities",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_agent_role_consistency_structure",
                    "tests/integration/test_single_agent_patterns.py::TestSingleAgentPatterns::test_agent_boundary_and_scope_structure",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_software_engineer_agent_has_sub_agents",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_sub_agents_have_correct_structure",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_sub_agents_have_specialized_tools",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_sub_agents_have_specialized_instructions",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_devops_agent_class_structure",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_agent_hierarchy_structure",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_agent_model_consistency",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_agent_communication_structure",
                    "tests/integration/test_sub_agent_delegation.py::TestSubAgentDelegation::test_delegation_readiness_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_role_based_behavior_consistency",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_constraint_enforcement_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_output_format_compliance_capability",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_context_aware_instruction_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_multi_turn_instruction_consistency_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_conditional_instruction_following_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_instruction_priority_resolution_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_instruction_interpretation_edge_cases_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_system_instruction_inheritance_structure",
                    "tests/integration/test_system_instruction_compliance.py::TestSystemInstructionCompliance::test_instruction_validation_and_compliance_readiness",
                ],
            )
        )

        # Phase 1.6: ADK Evaluation Pattern Tests
        self.test_suites.append(
            TestSuite(
                name="ADK Evaluation Pattern Tests",
                description="Official Google ADK evaluation-based integration tests",
                tests=[
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_agent_structure_evaluation",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_test_files_exist",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_test_structure",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_config_validation",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_scenarios_content",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_tool_names_match_agent_tools",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_evaluation_pattern_completeness",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_adk_evaluation_framework_readiness",
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_future_evaluation_expansion_points",
                ],
            )
        )

        # Phase 1.7: Multi-Agent Coordination Evaluation Tests
        self.test_suites.append(
            TestSuite(
                name="Multi-Agent Coordination Evaluation Tests",
                description="Evaluation-based tests for multi-agent coordination patterns following ADK evaluation framework",  # noqa: E501
                tests=[
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_multi_agent_coordination_evaluation",
                ],
            )
        )

        # Phase 1.8: Agent Memory and Persistence Evaluation Tests
        self.test_suites.append(
            TestSuite(
                name="Agent Memory and Persistence Evaluation Tests",
                description="Evaluation-based tests for agent memory and persistence mechanisms following ADK evaluation framework",  # noqa: E501
                tests=[
                    "tests/integration/test_adk_evaluation_patterns.py::TestADKEvaluationPatterns::test_agent_memory_persistence_evaluation",
                ],
            )
        )

        # Phase 2: Core Integration Tests
        self.test_suites.append(
            TestSuite(
                name="Core Integration Tests",
                description="Advanced context management, retry system, callback handling, and RAG integration tests",  # noqa: E501
                tests=[
                    # Retry system tests (error recovery and resilience)
                    "tests/integration/test_retry_system_integration.py::TestRetryCallbackCreation::test_create_retry_callbacks_default_config",
                    "tests/integration/test_retry_system_integration.py::TestRetryHandlerLogic::test_retry_handler_success_after_failure",
                    "tests/integration/test_retry_system_integration.py::TestRetryHandlerLogic::test_retry_handler_exhaustion",
                    "tests/integration/test_retry_system_integration.py::TestRetrySystemIntegration::test_enhanced_agent_has_retry_capabilities",
                    "tests/integration/test_retry_system_integration.py::TestRetrySystemIntegration::test_enhanced_agent_model_method_wrapped",
                    "tests/integration/test_retry_system_integration.py::TestRetrySystemPerformance::test_retry_exponential_backoff_timing",
                    "tests/integration/test_retry_system_integration.py::TestEnhancedAgentRetryIntegration::test_enhanced_agent_full_loading_with_retry",
                    # End-to-end retry tests (verify actual retry behavior)
                    "tests/integration/test_retry_system_integration.py::TestEnhancedAgentEndToEndRetry::test_enhanced_agent_actual_retry_on_model_failure",
                    "tests/integration/test_retry_system_integration.py::TestEnhancedAgentEndToEndRetry::test_enhanced_agent_retry_exhaustion_end_to_end",
                    "tests/integration/test_retry_system_integration.py::TestEnhancedAgentEndToEndRetry::test_enhanced_agent_non_retryable_error_end_to_end",
                    "tests/integration/test_retry_system_integration.py::TestEnhancedAgentEndToEndRetry::test_enhanced_agent_streaming_wrapper_behavior",
                    # Callback return value handling tests (regression prevention)
                    "tests/integration/test_callback_return_values_integration.py::TestCallbackReturnValueHandling::test_list_callbacks_first_returns_value",
                    "tests/integration/test_callback_return_values_integration.py::TestCallbackReturnValueHandling::test_list_callbacks_first_none_second_value",
                    "tests/integration/test_callback_return_values_integration.py::TestCallbackReturnValueRegressionPrevention::test_callback_return_value_not_discarded",
                    "tests/integration/test_callback_return_values_integration.py::TestCallbackReturnValueRegressionPrevention::test_callback_execution_order_matters",
                    # Tool-specific callback return value tests (before_tool and after_tool)
                    "tests/integration/test_callback_return_values_integration.py::TestToolCallbackReturnValueHandling::test_before_tool_callback_list_returns_first_non_none",
                    "tests/integration/test_callback_return_values_integration.py::TestToolCallbackReturnValueHandling::test_after_tool_callback_list_returns_first_non_none",
                    "tests/integration/test_callback_return_values_integration.py::TestToolCallbackReturnValueHandling::test_before_and_after_tool_callback_consistency",
                    # Context management tests
                    "tests/integration/test_context_management_advanced.py::TestSmartPrioritization::test_prioritize_code_snippets_by_relevance",
                    "tests/integration/test_context_management_advanced.py::TestSmartPrioritization::test_prioritize_tool_results_by_error_priority",
                    "tests/integration/test_context_management_advanced.py::TestCrossTurnCorrelation::test_identify_related_conversations",
                    "tests/integration/test_context_management_advanced.py::TestIntelligentSummarization::test_context_aware_summarization",
                    "tests/integration/test_context_management_advanced.py::TestDynamicContextExpansion::test_discover_relevant_files",
                    "tests/integration/test_context_management_advanced.py::TestContextManagerIntegration::test_comprehensive_context_assembly",
                ],
            )
        )

        # Phase 3: Tool Orchestration Tests
        self.test_suites.append(
            TestSuite(
                name="Tool Orchestration Tests",
                description="Advanced tool orchestration with error handling and state management",
                tests=[
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_sequential_tool_execution",
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_parallel_tool_execution",
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_tool_dependency_management",
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_error_handling_and_recovery",
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_context_integration",
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_rag_tool_integration",
                    "tests/integration/test_tool_orchestration_advanced.py::TestAdvancedToolOrchestration::test_complex_workflow_scenario",
                    "tests/integration/test_tool_orchestration_advanced.py::TestToolStateManagement::test_tool_state_sharing",
                ],
            )
        )

        # Phase 4: Performance Verification Tests
        self.test_suites.append(
            TestSuite(
                name="Performance Verification Tests",
                description="Performance, load testing, and optimization validation",
                tests=[
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_context_assembly_performance",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_parallel_vs_sequential_performance",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_token_optimization_performance",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_smart_prioritization_performance",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_cross_turn_correlation_performance",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_load_testing_simulation",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_memory_usage_optimization",
                    "tests/integration/test_performance_verification.py::TestPerformanceVerification::test_comprehensive_performance_suite",
                ],
            )
        )

        # Phase 5: Stress Tests (Optional)
        self.test_suites.append(
            TestSuite(
                name="Stress Tests",
                description="Extreme scenario and stress testing",
                tests=[
                    "tests/integration/test_performance_verification.py::TestStressTests::test_extreme_context_size_stress",
                    "tests/integration/test_performance_verification.py::TestStressTests::test_rapid_fire_operations_stress",
                    "tests/integration/test_performance_verification.py::TestStressTests::test_memory_exhaustion_recovery",
                ],
            )
        )

    async def run_all_tests(self) -> dict:
        """Run all integration tests and return comprehensive results."""
        logger.info("🚀 Starting comprehensive integration test suite")
        self.start_time = time.time()

        # Run test suites
        if self.parallel:
            await self._run_suites_parallel()
        else:
            await self._run_suites_sequential()

        self.end_time = time.time()
        total_duration = self.end_time - self.start_time

        # Generate comprehensive report
        report = self._generate_comprehensive_report(total_duration)

        # Save report
        self._save_report(report)

        # Print summary
        self._print_summary(report)

        return report

    async def _run_suites_sequential(self):
        """Run test suites sequentially."""
        for suite in self.test_suites:
            logger.info(f"📋 Running {suite.name}")
            await self._run_test_suite(suite)

    async def _run_suites_parallel(self):
        """Run test suites in parallel where possible."""
        # Foundation tests must run first
        foundation_suite = self.test_suites[0]
        logger.info(f"📋 Running {foundation_suite.name} (sequential)")
        await self._run_test_suite(foundation_suite)

        # Core integration tests can run in parallel
        core_suite = self.test_suites[1]
        logger.info(f"📋 Running {core_suite.name} (parallel)")
        await self._run_test_suite(core_suite)

        # Tool orchestration and performance tests can run in parallel
        remaining_suites = self.test_suites[2:]
        logger.info(f"📋 Running remaining {len(remaining_suites)} suites in parallel")

        tasks = []
        for suite in remaining_suites:
            task = asyncio.create_task(self._run_test_suite(suite))
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def _run_test_suite(self, suite: TestSuite):
        """Run a single test suite."""
        logger.info(f"  📝 {suite.description}")

        for test in suite.tests:
            result = await self._run_single_test(test)
            suite.add_result(result)

            if result.passed:
                logger.info(f"    ✅ {result.name} ({result.duration:.2f}s)")
            else:
                logger.error(f"    ❌ {result.name} ({result.duration:.2f}s)")
                if self.verbose:
                    logger.error(f"       Error: {result.error}")

    async def _run_single_test(self, test_path: str) -> TestResult:
        """Run a single test and return result."""
        test_name = test_path.split("::")[-1]

        try:
            # Run pytest for the specific test
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "-x",  # Stop on first failure
            ]

            if not self.verbose:
                cmd.append("-q")

            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test
            )
            duration = time.time() - start_time

            # Parse result
            passed = result.returncode == 0
            output = result.stdout
            error = result.stderr if result.stderr else ""

            return TestResult(
                name=test_name,
                passed=passed,
                duration=duration,
                output=output,
                error=error,
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                name=test_name,
                passed=False,
                duration=300.0,
                error="Test timeout (5 minutes)",
            )
        except Exception as e:
            return TestResult(
                name=test_name,
                passed=False,
                duration=0.0,
                error=f"Test execution error: {e!s}",
            )

    def _generate_comprehensive_report(self, total_duration: float) -> dict:
        """Generate comprehensive test report."""
        # Calculate overall statistics
        total_tests = sum(len(suite.tests) for suite in self.test_suites)
        total_passed = sum(suite.passed_count for suite in self.test_suites)
        total_failed = sum(suite.failed_count for suite in self.test_suites)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

        # Get system information
        system_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "parallel_execution": self.parallel,
            "verbose": self.verbose,
        }

        # Generate report
        return {
            "system_info": system_info,
            "summary": {
                "total_duration": total_duration,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "overall_success_rate": overall_success_rate,
                "test_suites_count": len(self.test_suites),
            },
            "test_suites": [suite.to_dict() for suite in self.test_suites],
            "performance_metrics": self._extract_performance_metrics(),
            "recommendations": self._generate_recommendations(),
        }

    def _extract_performance_metrics(self) -> dict:
        """Extract performance metrics from test results."""
        metrics = {
            "fastest_test": None,
            "slowest_test": None,
            "average_test_duration": 0.0,
            "suite_performance": {},
        }

        all_results = []
        for suite in self.test_suites:
            all_results.extend(suite.results)

        if all_results:
            # Find fastest and slowest tests
            fastest = min(all_results, key=lambda r: r.duration)
            slowest = max(all_results, key=lambda r: r.duration)

            metrics["fastest_test"] = {
                "name": fastest.name,
                "duration": fastest.duration,
            }
            metrics["slowest_test"] = {
                "name": slowest.name,
                "duration": slowest.duration,
            }

            # Calculate average duration
            total_duration = sum(r.duration for r in all_results)
            metrics["average_test_duration"] = total_duration / len(all_results)

            # Suite performance
            for suite in self.test_suites:
                metrics["suite_performance"][suite.name] = {
                    "duration": suite.total_duration,
                    "avg_test_duration": suite.total_duration / len(suite.tests)
                    if suite.tests
                    else 0.0,
                    "success_rate": suite.success_rate(),
                }

        return metrics

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Check for failed tests
        for suite in self.test_suites:
            if suite.failed_count > 0:
                recommendations.append(
                    f"❌ {suite.name} has {suite.failed_count} failed tests - investigate and fix"
                )

        # Check for slow tests
        slow_threshold = 10.0  # seconds
        for suite in self.test_suites:
            slow_tests = [r for r in suite.results if r.duration > slow_threshold]
            if slow_tests:
                recommendations.append(
                    f"⏱️ {suite.name} has {len(slow_tests)} slow tests (>{slow_threshold}s) - "
                    "consider optimization"
                )

        # Check overall success rate
        total_tests = sum(len(suite.tests) for suite in self.test_suites)
        total_passed = sum(suite.passed_count for suite in self.test_suites)
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

        if success_rate < 95.0:
            recommendations.append(
                f"🎯 Overall success rate is {success_rate:.1f}% - aim for >95% for production "
                "readiness"
            )
        elif success_rate == 100.0:
            recommendations.append("🎉 Perfect test suite! All tests passing - excellent work!")

        if not recommendations:
            recommendations.append(
                "✅ All tests are performing well - no immediate issues detected"
            )

        return recommendations

    def _save_report(self, report: dict):
        """Save comprehensive report to file."""
        reports_dir = self.project_root / "test_reports"
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"integration_test_report_{timestamp}.json"

        with Path.open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Comprehensive report saved to: {report_file}")

    def _print_summary(self, report: dict):
        """Print comprehensive test summary."""
        summary = report["summary"]

        print("\n" + "=" * 80)
        print("🧪 INTEGRATION TEST SUITE SUMMARY")
        print("=" * 80)
        print(f"Total Duration: {summary['total_duration']:.1f}s")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['total_passed']} ✅")
        print(f"Failed: {summary['total_failed']} ❌")
        print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"Test Suites: {summary['test_suites_count']}")

        print("\n📋 TEST SUITE BREAKDOWN:")
        for suite_data in report["test_suites"]:
            status = "✅" if suite_data["failed_count"] == 0 else "❌"
            print(
                f"  {status} {suite_data['name']}:"
                f" {suite_data['passed_count']}/{len(suite_data['tests'])} passed"
                f" ({suite_data['success_rate']:.1f}%)"
            )

        print("\n⚡ PERFORMANCE METRICS:")
        perf = report["performance_metrics"]
        if perf.get("fastest_test"):
            print(
                f"  Fastest Test: {perf['fastest_test']['name']}"
                f" ({perf['fastest_test']['duration']:.3f}s)"
            )
        if perf.get("slowest_test"):
            print(
                f"  Slowest Test: {perf['slowest_test']['name']}"
                f" ({perf['slowest_test']['duration']:.3f}s)"
            )
        if perf.get("average_test_duration"):
            print(f"  Average Test Duration: {perf['average_test_duration']:.3f}s")

        print("\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"  {rec}")

        print("\n" + "=" * 80)


async def main():
    """Main entry point for the integration test runner."""
    parser = argparse.ArgumentParser(description="Run comprehensive integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        help="Run tests in parallel where possible",
    )
    parser.add_argument("--suite", "-s", type=str, help="Run specific test suite only")
    parser.add_argument("--stress", action="store_true", help="Include stress tests")

    args = parser.parse_args()

    # Create test runner
    runner = IntegrationTestRunner(verbose=args.verbose, parallel=args.parallel)

    # Filter test suites if requested
    if args.suite:
        runner.test_suites = [s for s in runner.test_suites if args.suite.lower() in s.name.lower()]
        if not runner.test_suites:
            logger.error(f"No test suites found matching '{args.suite}'")
            return 1

    # Remove stress tests if not requested
    if not args.stress:
        runner.test_suites = [s for s in runner.test_suites if s.name != "Stress Tests"]

    # Run tests
    try:
        report = await runner.run_all_tests()

        # Return appropriate exit code
        if report["summary"]["total_failed"] == 0:
            logger.info("🎉 All integration tests passed!")
            return 0
        logger.error(f"❌ {report['summary']['total_failed']} integration tests failed")
        return 1

    except KeyboardInterrupt:
        logger.info("Integration tests interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Integration test runner failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
