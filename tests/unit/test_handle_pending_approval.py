"""Unit tests for _handle_pending_approval function to prevent FunctionTool invocation bugs."""

from unittest.mock import MagicMock, patch

from google.adk.tools import FunctionTool, ToolContext
import pytest

from agents.software_engineer.enhanced_agent import _handle_pending_approval


class TestHandlePendingApproval:
    """Test the _handle_pending_approval function directly."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a real ToolContext mock
        self.tool_context = MagicMock(spec=ToolContext)
        self.tool_context.state = {}

        # Create test arguments
        self.args = {"test_arg": "test_value", "content": "Hello World!"}

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    def test_handle_pending_approval_with_function_tool_approved(self, mock_approval):
        """Test that FunctionTool is properly invoked when approval is given."""
        # Arrange
        mock_approval.return_value = True

        # Create a real FunctionTool with a mock function
        mock_function = MagicMock()
        mock_function.return_value = {"status": "success", "message": "Tool executed successfully"}
        function_tool = FunctionTool(func=mock_function)

        # Create tool response that triggers approval workflow
        tool_response = {
            "status": "pending_approval",
            "message": "This action requires approval",
            "proposed_content": "Hello World!",
        }

        # Act
        result = _handle_pending_approval(
            function_tool, self.args, self.tool_context, tool_response
        )

        # Assert
        mock_approval.assert_called_once()

        # Verify that the underlying function was called correctly
        mock_function.assert_called_once_with(tool_context=self.tool_context, **self.args)

        # Verify force_edit flag was set and reset
        assert self.tool_context.state.get("force_edit") is False  # Should be reset after execution

        # Verify the result is the re-executed tool response
        assert result["status"] == "success"
        assert result["message"] == "Tool executed successfully"

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    def test_handle_pending_approval_with_function_tool_rejected(self, mock_approval):
        """Test that FunctionTool is NOT invoked when approval is denied."""
        # Arrange
        mock_approval.return_value = False

        # Create a real FunctionTool with a mock function
        mock_function = MagicMock()
        function_tool = FunctionTool(func=mock_function)

        # Create tool response that triggers approval workflow
        tool_response = {
            "status": "pending_approval",
            "message": "This action requires approval",
            "proposed_content": "Hello World!",
        }

        # Act
        result = _handle_pending_approval(
            function_tool, self.args, self.tool_context, tool_response
        )

        # Assert
        mock_approval.assert_called_once()

        # Verify that the underlying function was NOT called
        mock_function.assert_not_called()

        # Verify the rejection message
        assert result["message"] == "File edit rejected by user."

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    def test_handle_pending_approval_with_non_function_tool_approved(self, mock_approval):
        """Test that non-FunctionTool objects are called directly when approved."""
        # Arrange
        mock_approval.return_value = True

        # Create a mock tool that's not a FunctionTool (explicitly no func attribute)
        mock_tool = MagicMock()
        # Explicitly remove the func attribute to simulate a non-FunctionTool
        del mock_tool.func
        mock_tool.return_value = {"status": "success", "message": "Non-FunctionTool executed"}

        # Create tool response that triggers approval workflow
        tool_response = {"status": "pending_approval", "message": "This action requires approval"}

        # Act
        result = _handle_pending_approval(mock_tool, self.args, self.tool_context, tool_response)

        # Assert
        mock_approval.assert_called_once()

        # Verify that the tool was called directly (fallback behavior)
        mock_tool.assert_called_once_with(tool_context=self.tool_context, **self.args)

        # Verify the result
        assert result["status"] == "success"
        assert result["message"] == "Non-FunctionTool executed"

    def test_handle_pending_approval_no_approval_needed(self):
        """Test that no approval processing occurs when status is not 'pending_approval'."""
        # Arrange
        mock_tool = MagicMock()
        tool_response = {
            "status": "success",  # Not pending approval
            "message": "Tool executed successfully",
        }

        # Act
        result = _handle_pending_approval(mock_tool, self.args, self.tool_context, tool_response)

        # Assert
        # Tool should not be called at all
        mock_tool.assert_not_called()

        # Result should be unchanged
        assert result == tool_response

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    def test_handle_pending_approval_force_edit_flag_cleanup_on_exception(self, mock_approval):
        """Test that force_edit flag is properly cleaned up even if tool execution fails."""
        # Arrange
        mock_approval.return_value = True

        # Create a FunctionTool that raises an exception
        def failing_function(tool_context, **args):  # noqa: ARG001
            raise RuntimeError("Tool execution failed")

        function_tool = FunctionTool(func=failing_function)

        tool_response = {"status": "pending_approval", "message": "This action requires approval"}

        # Act & Assert
        with pytest.raises(RuntimeError, match="Tool execution failed"):
            _handle_pending_approval(function_tool, self.args, self.tool_context, tool_response)

        # Verify force_edit flag was properly reset even after exception
        assert self.tool_context.state.get("force_edit") is False

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    def test_handle_pending_approval_preserves_original_response_structure(self, mock_approval):
        """Test that the original response structure is preserved when approval is needed."""
        # Arrange
        mock_approval.return_value = True

        mock_function = MagicMock()
        mock_function.return_value = {
            "status": "completed",
            "filepath": "/test/path.py",
            "content": "Updated content",
            "changes_made": True,
        }
        function_tool = FunctionTool(func=mock_function)

        original_response = {
            "status": "pending_approval",
            "message": "Edit requires approval",
            "proposed_filepath": "/test/path.py",
            "proposed_content": "Updated content",
        }

        # Act
        result = _handle_pending_approval(
            function_tool, self.args, self.tool_context, original_response
        )

        # Assert
        # Result should be the new tool response, not the original
        assert result != original_response
        assert result["status"] == "completed"
        assert result["filepath"] == "/test/path.py"
        assert result["content"] == "Updated content"
        assert result["changes_made"] is True
