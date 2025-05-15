# software_engineer/tools/analysis_state.py
"""Tool to access analysis results stored in session state."""

# TODO: This tool reads from tool_context.state['analysis_issues'].
# It requires another tool or agent (e.g., an enhanced analyze_code_tool or
# the code_review agent after running linters) to populate this state key
# with structured issue data (e.g., list of dicts) for this tool to be useful.

from typing import Any, Dict

from google.adk.tools import FunctionTool, ToolContext


def get_analysis_issues(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves code analysis issues stored under the key 'analysis_issues' in the session state.

    Args:
        tool_context: The tool context from ADK, providing access to session state.

    Returns:
        A dictionary containing the list of analysis issues under the key 'issues',
        or an empty list if the 'analysis_issues' key is not found or not a list.
    """
    # Get the issues list, default to empty list if key not found or value is None
    issues = tool_context.state.get("analysis_issues")
    # Ensure it's a list, return empty list otherwise
    if not isinstance(issues, list):
        issues = []
    return {"issues": issues}


# Define the tool using FunctionTool
get_analysis_issues_tool = FunctionTool(
    func=get_analysis_issues,
    # Description comes from func docstring
)
