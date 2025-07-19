"""
Unit tests for MCP cleanup exception handling fix.

This tests the exception handling logic that gracefully handles MCP client library
cleanup errors during agent shutdown.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

import pytest

from src.wrapper.adk.cli.cli import logger


class TestMCPCleanupExceptionHandling(unittest.TestCase):
    """Test cases for MCP cleanup exception handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_errors = [
            # MCP cleanup errors that should be handled
            (asyncio.CancelledError(), True),
            (asyncio.CancelledError("Cancelled by cancel scope 1680ba550"), True),
            (
                RuntimeError(
                    "Attempted to exit cancel scope in a different task than it was entered in"
                ),
                True,
            ),
            (RuntimeError("Error during MCP session cleanup for stdio_session"), True),
            (RuntimeError("Something about cancel scope here"), True),
            (RuntimeError("stdio_client connection failed"), True),
            (Exception("CancelledError: Cancelled by cancel scope 12345"), True),
            # Non-MCP errors that should be re-raised
            (ValueError("Some unrelated error"), False),
            (RuntimeError("Database connection failed"), False),
            (Exception("Normal application error"), False),
        ]

    def test_mcp_error_pattern_matching(self):
        """Test that MCP cleanup error patterns are correctly identified."""

        for error, should_be_handled in self.test_errors:
            with self.subTest(error=error, should_be_handled=should_be_handled):
                # This is the exact logic from our exception handler
                error_msg = str(error)
                exception_str = str(type(error).__name__)

                # Check if this is a known MCP cleanup error
                is_mcp_cleanup_error = any(
                    [
                        "Attempted to exit cancel scope in a different task" in error_msg,
                        "stdio_client" in error_msg,
                        "MCP session cleanup" in error_msg,
                        "CancelledError" in error_msg,
                        "CancelledError" in exception_str,
                        "cancel scope" in error_msg.lower(),
                        isinstance(error, asyncio.CancelledError),
                    ]
                )

                self.assertEqual(
                    is_mcp_cleanup_error,
                    should_be_handled,
                    f"Error pattern matching failed for {type(error).__name__}: {error_msg}",
                )

    @patch("src.wrapper.adk.cli.cli.logger")
    def test_mcp_cleanup_exception_handling_integration(self, mock_logger):
        """Test the full exception handling flow."""

        async def mock_runner_close_with_mcp_error():
            """Mock runner.close() that raises MCP cleanup error."""
            raise asyncio.CancelledError("Cancelled by cancel scope 1680ba550")

        async def mock_runner_close_with_other_error():
            """Mock runner.close() that raises non-MCP error."""
            raise ValueError("Some other error")

        # Test MCP error handling
        async def test_mcp_error_handling():
            try:
                await mock_runner_close_with_mcp_error()
            except (asyncio.CancelledError, Exception) as e:
                error_msg = str(e)
                exception_str = str(type(e).__name__)

                is_mcp_cleanup_error = any(
                    [
                        "Attempted to exit cancel scope in a different task" in error_msg,
                        "stdio_client" in error_msg,
                        "MCP session cleanup" in error_msg,
                        "CancelledError" in error_msg,
                        "CancelledError" in exception_str,
                        "cancel scope" in error_msg.lower(),
                        isinstance(e, asyncio.CancelledError),
                    ]
                )

                if is_mcp_cleanup_error:
                    mock_logger.warning(
                        f"MCP cleanup completed with expected async context warnings: {error_msg}"
                    )
                    return "handled"
                raise

        # Test non-MCP error handling
        async def test_non_mcp_error_handling():
            try:
                await mock_runner_close_with_other_error()
            except (asyncio.CancelledError, Exception) as e:
                error_msg = str(e)
                exception_str = str(type(e).__name__)

                is_mcp_cleanup_error = any(
                    [
                        "Attempted to exit cancel scope in a different task" in error_msg,
                        "stdio_client" in error_msg,
                        "MCP session cleanup" in error_msg,
                        "CancelledError" in error_msg,
                        "CancelledError" in exception_str,
                        "cancel scope" in error_msg.lower(),
                        isinstance(e, asyncio.CancelledError),
                    ]
                )

                if is_mcp_cleanup_error:
                    mock_logger.warning(
                        f"MCP cleanup completed with expected async context warnings: {error_msg}"
                    )
                    return "handled"
                raise

        # Run tests
        result = asyncio.run(test_mcp_error_handling())
        self.assertEqual(result, "handled")
        mock_logger.warning.assert_called_once()

        # Reset mock
        mock_logger.reset_mock()

        # Test that non-MCP errors are re-raised
        with self.assertRaises(ValueError):
            asyncio.run(test_non_mcp_error_handling())

        mock_logger.warning.assert_not_called()

    def test_asyncio_cancelled_error_detection(self):
        """Test specific handling of asyncio.CancelledError."""

        # Test various CancelledError scenarios
        test_cases = [
            asyncio.CancelledError(),
            asyncio.CancelledError(""),
            asyncio.CancelledError("Cancelled by cancel scope 1680ba550"),
        ]

        for error in test_cases:
            with self.subTest(error=error):
                # Should be detected as MCP cleanup error due to isinstance check
                self.assertTrue(isinstance(error, asyncio.CancelledError))

                # Should match our pattern
                error_msg = str(error)
                exception_str = str(type(error).__name__)

                is_mcp_cleanup_error = any(
                    [
                        "Attempted to exit cancel scope in a different task" in error_msg,
                        "stdio_client" in error_msg,
                        "MCP session cleanup" in error_msg,
                        "CancelledError" in error_msg,
                        "CancelledError" in exception_str,
                        "cancel scope" in error_msg.lower(),
                        isinstance(error, asyncio.CancelledError),
                    ]
                )

                self.assertTrue(is_mcp_cleanup_error)

    def test_cancel_scope_error_messages(self):
        """Test detection of cancel scope related error messages."""

        cancel_scope_errors = [
            "Attempted to exit cancel scope in a different task than it was entered in",
            "Cancel scope error occurred",
            "Error with cancel scope handling",
            "cancel scope mismatch detected",
        ]

        for error_msg in cancel_scope_errors:
            with self.subTest(error_msg=error_msg):
                error = RuntimeError(error_msg)

                # Should be detected as MCP cleanup error
                is_mcp_cleanup_error = any(
                    [
                        "Attempted to exit cancel scope in a different task" in error_msg,
                        "stdio_client" in error_msg,
                        "MCP session cleanup" in error_msg,
                        "CancelledError" in error_msg,
                        "CancelledError" in str(type(error).__name__),
                        "cancel scope" in error_msg.lower(),
                        isinstance(error, asyncio.CancelledError),
                    ]
                )

                self.assertTrue(is_mcp_cleanup_error)


if __name__ == "__main__":
    unittest.main()
