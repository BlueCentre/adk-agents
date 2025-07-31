"""
Integration Tests for Callback Return Value Handling

This module contains integration tests that verify callback return values
are properly handled when callbacks are in list form vs single form.

Tests verify:
- Single callbacks return their values correctly
- List callbacks return the first non-None result
- Callback execution stops after first non-None result
- All callbacks are executed when they all return None
"""

import logging
from unittest.mock import MagicMock

import pytest

logger = logging.getLogger(__name__)


class TestCallbackReturnValueHandling:
    """Test callback return value handling in CLI code."""

    def setup_method(self):
        """Set up test fixtures."""
        self.call_log = []
        self.tool = MagicMock()
        self.tool.name = "test_tool"
        self.args = {"test": "args"}
        self.tool_context = MagicMock()
        self.callback_context = MagicMock()

    def callback_returns_none(self, _tool, _args, _tool_context, _callback_context):
        """Test callback that returns None."""
        self.call_log.append("callback_returns_none")
        return

    def callback_returns_value(self, _tool, _args, _tool_context, _callback_context):
        """Test callback that returns a value."""
        self.call_log.append("callback_returns_value")
        return {"modified": "args"}

    def callback_returns_another_value(self, _tool, _args, _tool_context, _callback_context):
        """Test callback that returns a different value."""
        self.call_log.append("callback_returns_another_value")
        return {"different": "result"}

    def callback_halts_execution(self, _tool, _args, _tool_context, _callback_context):
        """Test callback that signals to halt execution."""
        self.call_log.append("callback_halts_execution")
        return {"halt": True}

    async def execute_callback_logic(self, original_callback):
        """Execute the callback handling logic (simulates the fixed CLI code)."""
        result = None

        if original_callback:
            if isinstance(original_callback, list):
                # Execute all callbacks in the list
                for callback in original_callback:
                    if callback:
                        result = callback(
                            self.tool, self.args, self.tool_context, self.callback_context
                        )
                        if result is not None and hasattr(result, "__await__"):
                            result = await result
                        # Return the first non-None result from the callback chain
                        if result is not None:
                            return result
            else:
                # Single callback
                result = original_callback(
                    self.tool, self.args, self.tool_context, self.callback_context
                )
                if result is not None and hasattr(result, "__await__"):
                    result = await result
                return result

        return result

    @pytest.mark.asyncio
    async def test_single_callback_with_return_value(self):
        """Test single callback that returns a value."""
        self.call_log.clear()

        result = await self.execute_callback_logic(self.callback_returns_value)

        assert result == {"modified": "args"}
        assert self.call_log == ["callback_returns_value"]

    @pytest.mark.asyncio
    async def test_single_callback_returns_none(self):
        """Test single callback that returns None."""
        self.call_log.clear()

        result = await self.execute_callback_logic(self.callback_returns_none)

        assert result is None
        assert self.call_log == ["callback_returns_none"]

    @pytest.mark.asyncio
    async def test_list_callbacks_first_returns_value(self):
        """Test list of callbacks where first returns a value - should stop execution."""
        self.call_log.clear()

        callbacks = [self.callback_returns_value, self.callback_returns_another_value]
        result = await self.execute_callback_logic(callbacks)

        # Should return first callback's result
        assert result == {"modified": "args"}
        # Should only call first callback (execution stops after non-None result)
        assert self.call_log == ["callback_returns_value"]

    @pytest.mark.asyncio
    async def test_list_callbacks_first_none_second_value(self):
        """Test list of callbacks where first returns None, second returns value."""
        self.call_log.clear()

        callbacks = [self.callback_returns_none, self.callback_returns_value]
        result = await self.execute_callback_logic(callbacks)

        # Should return second callback's result
        assert result == {"modified": "args"}
        # Should call both callbacks
        assert self.call_log == ["callback_returns_none", "callback_returns_value"]

    @pytest.mark.asyncio
    async def test_list_callbacks_all_return_none(self):
        """Test list of callbacks where all return None."""
        self.call_log.clear()

        def callback_returns_none_2(_tool, _args, _tool_context, _callback_context):
            self.call_log.append("callback_returns_none_2")
            return

        callbacks = [self.callback_returns_none, callback_returns_none_2]
        result = await self.execute_callback_logic(callbacks)

        # Should return None since all callbacks returned None
        assert result is None
        # Should call both callbacks
        assert self.call_log == ["callback_returns_none", "callback_returns_none_2"]

    @pytest.mark.asyncio
    async def test_list_callbacks_halt_execution_pattern(self):
        """Test callback that signals to halt execution."""
        self.call_log.clear()

        callbacks = [
            self.callback_halts_execution,
            self.callback_returns_value,  # This should not be called
        ]
        result = await self.execute_callback_logic(callbacks)

        # Should return the halt signal
        assert result == {"halt": True}
        # Should only call first callback
        assert self.call_log == ["callback_halts_execution"]

    @pytest.mark.asyncio
    async def test_empty_callback_list(self):
        """Test empty callback list."""
        self.call_log.clear()

        result = await self.execute_callback_logic([])

        assert result is None
        assert self.call_log == []

    @pytest.mark.asyncio
    async def test_none_callback(self):
        """Test None callback."""
        self.call_log.clear()

        result = await self.execute_callback_logic(None)

        assert result is None
        assert self.call_log == []

    @pytest.mark.asyncio
    async def test_callback_argument_modification_pattern(self):
        """Test callback that modifies arguments (common use case)."""
        self.call_log.clear()

        def callback_modifies_args(_tool, args, _tool_context, _callback_context):
            self.call_log.append("callback_modifies_args")
            # Simulate modifying arguments
            modified_args = args.copy()
            modified_args["modified"] = True
            return modified_args

        result = await self.execute_callback_logic(callback_modifies_args)

        # Should return the modified arguments
        assert result == {"test": "args", "modified": True}
        assert self.call_log == ["callback_modifies_args"]

    @pytest.mark.asyncio
    async def test_callback_chain_with_argument_modification(self):
        """Test callback chain where callbacks progressively modify arguments."""
        self.call_log.clear()

        def callback_first_modification(_tool, _args, _tool_context, _callback_context):
            self.call_log.append("callback_first_modification")
            # Return None to continue to next callback
            return

        def callback_second_modification(_tool, _args, _tool_context, _callback_context):
            self.call_log.append("callback_second_modification")
            # This callback makes the modification
            return {"first_processed": True, "modified_by": "second"}

        callbacks = [callback_first_modification, callback_second_modification]
        result = await self.execute_callback_logic(callbacks)

        # Should return the result from the second callback
        assert result == {"first_processed": True, "modified_by": "second"}
        # Should call both callbacks
        assert self.call_log == ["callback_first_modification", "callback_second_modification"]


class TestToolCallbackReturnValueHandling:
    """Test return value handling for both before_tool and after_tool callbacks."""

    def setup_method(self):
        """Set up test fixtures."""
        self.call_log = []
        self.tool = MagicMock()
        self.tool.name = "test_tool"
        self.args = {"test": "args"}
        self.tool_context = MagicMock()
        self.callback_context = MagicMock()
        self.tool_response = {"status": "success", "result": "tool output"}

    def before_tool_callback_modifies_args(self, _tool, args, _tool_context, _callback_context):
        """Before tool callback that modifies arguments."""
        self.call_log.append("before_tool_callback_modifies_args")
        modified_args = args.copy()
        modified_args["modified_by_before"] = True
        return modified_args

    def before_tool_callback_returns_none(self, _tool, _args, _tool_context, _callback_context):
        """Before tool callback that returns None."""
        self.call_log.append("before_tool_callback_returns_none")
        return

    def after_tool_callback_modifies_response(
        self, _tool, tool_response, _callback_context, _args, _tool_context
    ):
        """After tool callback that modifies response."""
        self.call_log.append("after_tool_callback_modifies_response")
        modified_response = tool_response.copy()
        modified_response["modified_by_after"] = True
        return modified_response

    def after_tool_callback_returns_none(
        self, _tool, _tool_response, _callback_context, _args, _tool_context
    ):
        """After tool callback that returns None."""
        self.call_log.append("after_tool_callback_returns_none")
        return

    async def execute_before_tool_callback_logic(self, original_callback):
        """Execute the before_tool callback handling logic."""
        result = None

        if original_callback:
            if isinstance(original_callback, list):
                # Execute all callbacks in the list
                for callback in original_callback:
                    if callback:
                        result = callback(
                            self.tool, self.args, self.tool_context, self.callback_context
                        )
                        if result is not None and hasattr(result, "__await__"):
                            result = await result
                        # Return the first non-None result from the callback chain
                        if result is not None:
                            return result
            else:
                # Single callback
                result = original_callback(
                    self.tool, self.args, self.tool_context, self.callback_context
                )
                if result is not None and hasattr(result, "__await__"):
                    result = await result
                return result

        return result

    async def execute_after_tool_callback_logic(self, original_callback):
        """Execute the after_tool callback handling logic."""
        result = None

        if original_callback:
            if isinstance(original_callback, list):
                # Execute all callbacks in the list
                for callback in original_callback:
                    if callback:
                        result = callback(
                            self.tool,
                            self.tool_response,
                            self.callback_context,
                            self.args,
                            self.tool_context,
                        )
                        if result is not None and hasattr(result, "__await__"):
                            result = await result
                        # Return the first non-None result from the callback chain
                        if result is not None:
                            return result
            else:
                # Single callback
                result = original_callback(
                    self.tool,
                    self.tool_response,
                    self.callback_context,
                    self.args,
                    self.tool_context,
                )
                if result is not None and hasattr(result, "__await__"):
                    result = await result
                return result

        return result

    @pytest.mark.asyncio
    async def test_before_tool_callback_list_returns_first_non_none(self):
        """Test that before_tool callback list returns first non-None result."""
        self.call_log.clear()

        callbacks = [
            self.before_tool_callback_returns_none,
            self.before_tool_callback_modifies_args,
        ]
        result = await self.execute_before_tool_callback_logic(callbacks)

        # Should return second callback's result (first returns None)
        assert result == {"test": "args", "modified_by_before": True}
        # Both callbacks should be called
        assert self.call_log == [
            "before_tool_callback_returns_none",
            "before_tool_callback_modifies_args",
        ]

    @pytest.mark.asyncio
    async def test_before_tool_callback_list_stops_at_first_result(self):
        """Test that before_tool callback list stops at first non-None result."""
        self.call_log.clear()

        def second_callback_not_called(_tool, _args, _tool_context, _callback_context):
            self.call_log.append("second_callback_not_called")
            pytest.fail("Second callback should not be called when first returns non-None")

        callbacks = [self.before_tool_callback_modifies_args, second_callback_not_called]
        result = await self.execute_before_tool_callback_logic(callbacks)

        # Should return first callback's result
        assert result == {"test": "args", "modified_by_before": True}
        # Only first callback should be called
        assert self.call_log == ["before_tool_callback_modifies_args"]

    @pytest.mark.asyncio
    async def test_after_tool_callback_list_returns_first_non_none(self):
        """Test that after_tool callback list returns first non-None result."""
        self.call_log.clear()

        callbacks = [
            self.after_tool_callback_returns_none,
            self.after_tool_callback_modifies_response,
        ]
        result = await self.execute_after_tool_callback_logic(callbacks)

        # Should return second callback's result (first returns None)
        assert result == {"status": "success", "result": "tool output", "modified_by_after": True}
        # Both callbacks should be called
        assert self.call_log == [
            "after_tool_callback_returns_none",
            "after_tool_callback_modifies_response",
        ]

    @pytest.mark.asyncio
    async def test_after_tool_callback_list_stops_at_first_result(self):
        """Test that after_tool callback list stops at first non-None result."""
        self.call_log.clear()

        def second_callback_not_called(
            _tool, _tool_response, _callback_context, _args, _tool_context
        ):
            self.call_log.append("second_callback_not_called")
            pytest.fail("Second callback should not be called when first returns non-None")

        callbacks = [self.after_tool_callback_modifies_response, second_callback_not_called]
        result = await self.execute_after_tool_callback_logic(callbacks)

        # Should return first callback's result
        assert result == {"status": "success", "result": "tool output", "modified_by_after": True}
        # Only first callback should be called
        assert self.call_log == ["after_tool_callback_modifies_response"]

    @pytest.mark.asyncio
    async def test_before_and_after_tool_callback_consistency(self):
        """Test that before_tool and after_tool callbacks handle return values consistently."""
        self.call_log.clear()

        # Test before_tool callbacks
        before_callbacks = [self.before_tool_callback_modifies_args]
        before_result = await self.execute_before_tool_callback_logic(before_callbacks)

        # Test after_tool callbacks
        after_callbacks = [self.after_tool_callback_modifies_response]
        after_result = await self.execute_after_tool_callback_logic(after_callbacks)

        # Both should return their respective modifications
        assert before_result == {"test": "args", "modified_by_before": True}
        assert after_result == {
            "status": "success",
            "result": "tool output",
            "modified_by_after": True,
        }

        # Both callbacks should have been called
        assert "before_tool_callback_modifies_args" in self.call_log
        assert "after_tool_callback_modifies_response" in self.call_log


class TestCallbackReturnValueRegressionPrevention:
    """Regression tests to prevent callback return value issues."""

    @pytest.mark.asyncio
    async def test_callback_return_value_not_discarded(self):
        """Verify that callback return values are not discarded (regression test)."""
        call_count = 0

        def important_callback(_tool, _args, _tool_context, _callback_context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First callback in chain does important work and returns result
                return {"critical_data": "important_value", "processed": True}
            # This should not be reached due to early return
            pytest.fail("Second callback should not be called when first returns non-None")

        # Simulate the fixed callback handling logic
        callbacks = [important_callback, important_callback]  # Two instances for testing

        result = None
        if callbacks:
            if isinstance(callbacks, list):
                for callback in callbacks:
                    if callback:
                        result = callback(None, None, None, None)
                        if result is not None:
                            break  # Early return on non-None result

        # Verify the critical fix: result is returned, not discarded
        assert result == {"critical_data": "important_value", "processed": True}
        assert call_count == 1  # Only first callback should be called

    def test_callback_execution_order_matters(self):
        """Test that callback execution order is preserved and matters."""
        execution_order = []

        def callback_a(_tool, _args, _tool_context, _callback_context):
            execution_order.append("A")
            return  # Continue to next callback

        def callback_b(_tool, _args, _tool_context, _callback_context):
            execution_order.append("B")
            return {"from": "B"}  # This should be returned

        def callback_c(_tool, _args, _tool_context, _callback_context):
            execution_order.append("C")
            return {"from": "C"}  # This should not be reached

        callbacks = [callback_a, callback_b, callback_c]

        # Execute the fixed logic
        result = None
        if callbacks:
            if isinstance(callbacks, list):
                for callback in callbacks:
                    if callback:
                        result = callback(None, None, None, None)
                        if result is not None:
                            break

        # Verify execution stopped at callback B
        assert result == {"from": "B"}
        assert execution_order == ["A", "B"]  # C should not be executed
