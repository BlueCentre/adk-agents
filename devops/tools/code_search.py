"""Code search functionality for software engineer agents using ripgrep."""

import json
import subprocess
from typing import Any, Dict, List, Optional

from google.adk.tools import FunctionTool


def ripgrep_code_search(query: str, target_directories: Optional[List[str]] = None, explanation: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a code search using ripgrep (rg) and return the results.

    Args:
        query: The search query to find relevant code
        target_directories: Optional list of directories to search in (glob patterns supported)
        explanation: Optional explanation of why this search is being performed

    Returns:
        Dictionary containing search results with snippets and file information
    """
    try:
        # Default to search in current directory if none specified
        search_paths = target_directories or ["."]

        results = []
        for path in search_paths:
            # Build the ripgrep command
            # Using --json for structured output
            # --context for showing surrounding lines
            cmd = [
                "rg",
                "--json",
                "--context",
                "2",  # Show 2 lines before and after matches
                "--max-columns",
                "1000",  # Reasonable line length limit
                query,
            ]

            # Add path to search
            cmd.append(path)

            # Execute the search
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't raise exception if nothing found
            )

            # Process the output - each line is a JSON object
            for line in process.stdout.strip().split("\n"):
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Only process match data
                    if data.get("type") == "match":
                        file_path = data.get("data", {}).get("path", {}).get("text", "")
                        line_number = data.get("data", {}).get("line_number", 0)
                        match_content = data.get("data", {}).get("lines", {}).get("text", "").strip()

                        results.append({"file": file_path, "line": line_number, "content": match_content})
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue

        return {"snippets": results, "status": "success", "query": query, "explanation": explanation or "Code search results"}

    except Exception as e:
        return {"snippets": [], "status": "error", "error_message": str(e), "query": query}


# Create FunctionTool wrapper for ripgrep code search
codebase_search_tool = FunctionTool(func=ripgrep_code_search)
