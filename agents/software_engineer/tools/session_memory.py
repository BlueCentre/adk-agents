"""Session memory snapshot/restore tools aligned with ADK memory services.

These tools implement snapshotting selected keys from `tool_context.state` and
restoring them later. When available, they attempt to leverage ADK memory tools
(`preload_memory_tool`, `load_memory_tool`). Otherwise, they fall back to in-state
storage to preserve behavior without external dependencies.
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

logger = logging.getLogger(__name__)


# Best-effort imports of ADK memory tools. These may not be available in all environments.
try:
    from google.adk.tools.preload_memory_tool import (  # type: ignore[attr-defined]
        preload_memory_tool as _adk_preload_memory_tool,
    )
except Exception:  # pragma: no cover - optional
    _adk_preload_memory_tool = None  # type: ignore[assignment]

try:
    from google.adk.tools.load_memory_tool import (  # type: ignore[attr-defined]
        load_memory_tool as _adk_load_memory_tool,
    )
except Exception:  # pragma: no cover - optional
    _adk_load_memory_tool = None  # type: ignore[assignment]


def _get_default_snapshot_keys(state: dict[str, Any]) -> list[str]:
    """Return a sensible default list of keys to persist if none provided."""
    default_candidates = [
        "user_preferences",
        "project_structure",
        "project_dependencies",
        "workflow_state",
        "approval_audit_trail",
        "command_history",
        "recent_errors",
    ]
    return [k for k in default_candidates if k in state]


def snapshot_session_to_memory_func(args: dict, tool_context: ToolContext) -> dict[str, Any]:
    """Snapshot selected `tool_context.state` keys to ADK memory (best-effort).

    Args (via args dict):
      - include_keys: Optional[List[str]]
      - labels: Optional[List[str]]
    """
    if not tool_context or not hasattr(tool_context, "state") or tool_context.state is None:
        return {"status": "error", "message": "No tool context state available"}

    include_keys = args.get("include_keys")
    labels = args.get("labels")

    state: dict[str, Any] = tool_context.state
    keys_to_save = include_keys or state.get("snapshot_include_keys")
    if not keys_to_save:
        keys_to_save = _get_default_snapshot_keys(state)

    snapshot: dict[str, Any] = {
        "_meta": {
            "created_at": datetime.now().isoformat(),
            "labels": list(labels or []),
        },
    }
    for key in keys_to_save:
        try:
            value = state.get(key)
            if value is not None:
                snapshot[key] = value
        except Exception as e:  # pragma: no cover - safety
            logger.debug(f"Skipping key '{key}' due to error: {e}")

    # Try ADK preload memory tool first (best-effort)
    adk_success = False
    if _adk_preload_memory_tool is not None:
        try:
            # Conservative, generic args shape to maximize compatibility
            _adk_preload_memory_tool.func(  # type: ignore[attr-defined]
                args={
                    "documents": [
                        {
                            "text": json.dumps(snapshot, ensure_ascii=False),
                            "labels": list(labels or ["agent_session_snapshot"]),
                        }
                    ]
                },
                tool_context=tool_context,
            )
            adk_success = True
        except Exception as e:  # pragma: no cover - optional best-effort
            logger.debug(f"ADK preload_memory_tool invocation failed (ignored): {e}")

    # Always keep a local fallback snapshot for reliability
    try:
        state["__last_session_snapshot"] = snapshot
        history = state.get("__session_snapshot_history") or []
        if not isinstance(history, list):
            history = []
        history.append({"saved_at": snapshot["_meta"]["created_at"], "keys": list(snapshot.keys())})
        state["__session_snapshot_history"] = history
    except Exception as e:  # pragma: no cover - safety
        logger.debug(f"Failed to record local snapshot (ignored): {e}")

    return {
        "status": "success",
        "adk_memory_used": adk_success,
        "keys_saved": [k for k in snapshot.keys() if k != "_meta"],
        "labels": list(labels or []),
    }


def restore_session_from_memory_func(args: dict, tool_context: ToolContext) -> dict[str, Any]:
    """Restore `tool_context.state` from ADK memory or local fallback snapshot.

    Args (via args dict):
      - filter_query: Optional[str]
      - include_labels: Optional[List[str]]
    """
    if not tool_context or not hasattr(tool_context, "state") or tool_context.state is None:
        return {"status": "error", "message": "No tool context state available"}

    filter_query = args.get("filter_query")
    include_labels = args.get("include_labels")

    state: dict[str, Any] = tool_context.state

    # Attempt ADK load memory tool (best-effort)
    restored_from_adk = False
    if _adk_load_memory_tool is not None:
        try:
            result = _adk_load_memory_tool.func(  # type: ignore[attr-defined]
                args={
                    "query": filter_query or "agent_session_snapshot",
                    "labels": list(include_labels or []),
                },
                tool_context=tool_context,
            )
            candidates: list[str] = []
            if isinstance(result, dict):
                for key in ("results", "items", "documents", "entries"):
                    entries = result.get(key)
                    if isinstance(entries, list):
                        for entry in entries:
                            if isinstance(entry, dict):
                                text = entry.get("text") or entry.get("content")
                                if isinstance(text, str):
                                    candidates.append(text)
            for text in candidates:
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and any(k for k in parsed.keys() if k != "_meta"):
                        for k, v in parsed.items():
                            if k == "_meta":
                                continue
                            state[k] = v
                        restored_from_adk = True
                        break
                except Exception:  # pragma: no cover - best-effort parsing
                    continue
        except Exception as e:  # pragma: no cover - optional best-effort
            logger.debug(f"ADK load_memory_tool invocation failed (ignored): {e}")

    if restored_from_adk:
        return {"status": "success", "source": "adk_memory"}

    # Fallback: restore from local snapshot
    snapshot = state.get("__last_session_snapshot")
    if isinstance(snapshot, dict):
        for k, v in snapshot.items():
            if k == "_meta":
                continue
            try:
                state[k] = v
            except Exception as e:  # pragma: no cover - safety
                logger.debug(f"Failed to restore key '{k}' from snapshot: {e}")
        return {"status": "success", "source": "local_snapshot"}

    return {"status": "skipped", "message": "No snapshot available to restore"}


# Export tools using ADK-compatible signatures
snapshot_session_to_memory_tool = FunctionTool(snapshot_session_to_memory_func)
restore_session_from_memory_tool = FunctionTool(restore_session_from_memory_func)
