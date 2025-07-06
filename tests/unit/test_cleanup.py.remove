"""
Comprehensive tests for cleanup.py functionality.
This aims to increase coverage from 29% to near 100%.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.adk.runners import Runner

from src.wrapper.adk.cli.utils.cleanup import close_runner_gracefully, close_runners


class TestCloseRunners:
    """Test the close_runners function comprehensively."""

    @pytest.mark.asyncio
    async def test_close_runners_empty_list(self):
        """Test close_runners with empty list - should handle gracefully."""
        # Empty list should complete without error
        await close_runners([])
        # No assertions needed - just ensuring no exceptions

    @pytest.mark.asyncio
    async def test_close_runners_single_runner_success(self):
        """Test successful cleanup of a single runner."""
        runner = Mock(spec=Runner)
        runner.close = AsyncMock()
        
        await close_runners([runner])
        
        runner.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_runners_multiple_runners_success(self):
        """Test successful cleanup of multiple runners."""
        runner1 = Mock(spec=Runner)
        runner1.close = AsyncMock()
        runner2 = Mock(spec=Runner)
        runner2.close = AsyncMock()
        runner3 = Mock(spec=Runner)
        runner3.close = AsyncMock()
        
        runners = [runner1, runner2, runner3]
        
        await close_runners(runners)
        
        # Verify all runners were closed
        runner1.close.assert_called_once()
        runner2.close.assert_called_once()
        runner3.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_runners_timeout_scenario(self):
        """Test timeout handling in close_runners - critical uncovered path."""
        runner1 = Mock(spec=Runner)
        runner2 = Mock(spec=Runner)
        
        # runner1 completes quickly
        runner1.close = AsyncMock()
        
        # runner2 hangs and will timeout
        async def hanging_close():
            await asyncio.sleep(35)  # Longer than 30s timeout
            
        runner2.close = AsyncMock(side_effect=hanging_close)
        
        runners = [runner1, runner2]
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            await close_runners(runners)
            
            # Verify warning was logged about pending tasks
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0]
            assert "didn't complete in time" in warning_call[0]

    @pytest.mark.asyncio
    async def test_close_runners_partial_timeout_with_cancellation(self):
        """Test that pending tasks are cancelled after timeout."""
        runner1 = Mock(spec=Runner)
        runner2 = Mock(spec=Runner)
        
        # runner1 completes normally
        runner1.close = AsyncMock()
        
        # runner2 will be cancelled due to timeout
        hanging_future = asyncio.Future()
        runner2.close = AsyncMock(return_value=hanging_future)
        
        runners = [runner1, runner2]
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger'):
            # Mock asyncio.wait to simulate timeout scenario
            with patch('asyncio.wait') as mock_wait:
                # Simulate one task done, one pending
                done_task = Mock()
                pending_task = Mock()
                pending_task.cancel = Mock()
                
                mock_wait.return_value = ([done_task], [pending_task])
                
                await close_runners(runners)
                
                # Verify the pending task was cancelled
                pending_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_runners_exception_during_close(self):
        """Test handling of exceptions during runner.close()."""
        runner1 = Mock(spec=Runner)
        runner1.close = AsyncMock()
        
        runner2 = Mock(spec=Runner)
        runner2.close = AsyncMock(side_effect=Exception("Close failed"))
        
        runner3 = Mock(spec=Runner)
        runner3.close = AsyncMock()
        
        runners = [runner1, runner2, runner3]
        
        # Should not raise exception - cleanup should be resilient
        await close_runners(runners)
        
        # All runners should be attempted
        runner1.close.assert_called_once()
        runner2.close.assert_called_once()
        runner3.close.assert_called_once()


class TestCloseRunnerGracefully:
    """Test the close_runner_gracefully function comprehensively."""

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_success(self):
        """Test successful graceful cleanup."""
        runner = Mock(spec=Runner)
        runner.close = AsyncMock()
        
        await close_runner_gracefully(runner)
        
        runner.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_cancelled_error(self):
        """Test handling of CancelledError - this path is currently uncovered."""
        runner = Mock(spec=Runner)
        cancelled_error = asyncio.CancelledError("Operation was cancelled")
        runner.close = AsyncMock(side_effect=cancelled_error)
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            # Should not raise exception
            await close_runner_gracefully(runner)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "MCP session cleanup completed with cancellation" in warning_message
            assert "this is normal" in warning_message

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_mcp_cancel_scope_error(self):
        """Test handling of MCP cancel scope errors - uncovered path."""
        runner = Mock(spec=Runner)
        mcp_error = Exception("cancel scope error in MCP session")
        runner.close = AsyncMock(side_effect=mcp_error)
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            # Should not raise exception
            await close_runner_gracefully(runner)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "MCP session cleanup completed with warning" in warning_message
            assert "this is normal" in warning_message

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_mcp_keyword_error(self):
        """Test handling of errors containing 'mcp' keyword - uncovered path."""
        runner = Mock(spec=Runner)
        mcp_error = Exception("MCP connection failed during cleanup")
        runner.close = AsyncMock(side_effect=mcp_error)
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            # Should not raise exception
            await close_runner_gracefully(runner)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "MCP session cleanup completed with warning" in warning_message

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_non_mcp_error_reraises(self):
        """Test that non-MCP errors are re-raised - uncovered path."""
        runner = Mock(spec=Runner)
        system_error = Exception("Critical system error")
        runner.close = AsyncMock(side_effect=system_error)
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            # Should re-raise non-MCP errors
            with pytest.raises(Exception, match="Critical system error"):
                await close_runner_gracefully(runner)
            
            # Verify error was logged with exc_info
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "Runner cleanup error" in error_message
            # Verify exc_info=True was passed
            assert mock_logger.error.call_args[1]['exc_info'] is True

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_mixed_case_mcp_error(self):
        """Test MCP error detection is case-insensitive."""
        runner = Mock(spec=Runner)
        mcp_error = Exception("MCP Session Error in CANCEL SCOPE")
        runner.close = AsyncMock(side_effect=mcp_error)
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            # Should not raise exception
            await close_runner_gracefully(runner)
            
            # Verify warning was logged (not error)
            mock_logger.warning.assert_called_once()
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_empty_error_message(self):
        """Test handling of exception with empty error message."""
        runner = Mock(spec=Runner)
        empty_error = Exception("")
        runner.close = AsyncMock(side_effect=empty_error)
        
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            # Should re-raise since empty string doesn't contain MCP keywords
            with pytest.raises(Exception):
                await close_runner_gracefully(runner)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_runner_gracefully_logging_integration(self):
        """Test proper logger usage and message formatting."""
        runner = Mock(spec=Runner)
        
        # Test with a specific MCP error message
        mcp_error = Exception("cancel scope cleanup failed in mcp session")
        runner.close = AsyncMock(side_effect=mcp_error)
        
        # Use real logger to test message formatting
        with patch('src.wrapper.adk.cli.utils.cleanup.logger') as mock_logger:
            await close_runner_gracefully(runner)
            
            # Verify the exact format of the warning message
            expected_message = f"MCP session cleanup completed with warning (this is normal): {str(mcp_error)}"
            mock_logger.warning.assert_called_once_with(expected_message)
