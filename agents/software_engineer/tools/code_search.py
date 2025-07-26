"""Code search functionality for software engineer agents using ripgrep."""

import json
import logging
from pathlib import Path
import subprocess
from typing import Any, Optional

from google.adk.tools import FunctionTool, ToolContext

logger = logging.getLogger(__name__)


def ripgrep_code_search(
    query: str,
    target_directories: Optional[list[str]] = None,
    explanation: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """
    Perform a context-aware code search using ripgrep (rg) and return the results.

    Enhanced with project structure awareness and dependency-based prioritization.

    Args:
        query: The search query to find relevant code
        target_directories: Optional list of directories to search in (glob patterns supported)
        explanation: Optional explanation of why this search is being performed
        tool_context: ADK tool context for accessing session state

    Returns:
        Dictionary containing search results with snippets and file information
    """
    try:
        # Get context-aware search paths
        search_paths = _get_context_aware_search_paths(target_directories, query, tool_context)

        logger.info(f"Context-aware code search in paths: {search_paths}")

        results = []
        for path in search_paths:
            # Build the ripgrep command with enhanced options
            cmd = [
                "rg",
                "--json",
                "--context",
                "2",  # Show 2 lines before and after matches
                "--max-columns",
                "1000",  # Reasonable line length limit
                "--type-add",
                "config:*.{toml,json,yaml,yml,ini,cfg}",  # Include config files
                "--smart-case",  # Smart case sensitivity
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
                        match_content = (
                            data.get("data", {}).get("lines", {}).get("text", "").strip()
                        )

                        # Add relevance scoring based on project context
                        relevance_score = _calculate_relevance_score(file_path, query, tool_context)

                        results.append(
                            {
                                "file": file_path,
                                "line": line_number,
                                "content": match_content,
                                "relevance_score": relevance_score,
                                "search_path": path,
                            }
                        )
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue

        # Sort results by relevance score (highest first)
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Add context summary to results
        context_summary = _generate_search_context_summary(query, search_paths, tool_context)

        return {
            "snippets": results,
            "status": "success",
            "query": query,
            "explanation": explanation or "Context-aware code search results",
            "search_paths_used": search_paths,
            "context_summary": context_summary,
            "total_results": len(results),
        }

    except Exception as e:
        logger.error(f"Error in ripgrep_code_search: {e}")
        return {
            "snippets": [],
            "status": "error",
            "error_message": str(e),
            "query": query,
        }


def _get_context_aware_search_paths(
    target_directories: Optional[list[str]], query: str, tool_context: Optional[ToolContext]
) -> list[str]:
    """
    Determine optimal search paths based on project context and query.

    Args:
        target_directories: User-specified directories
        query: Search query for context hints
        tool_context: ADK tool context for session state

    Returns:
        List of optimized search paths
    """
    # Start with user-specified directories if provided
    if target_directories:
        return target_directories

    search_paths = ["."]  # Default fallback

    try:
        if not tool_context or not hasattr(tool_context, "state") or not tool_context.state:
            return search_paths

        session_state = tool_context.state
        project_structure = session_state.get("project_structure", {})
        project_dependencies = session_state.get("project_dependencies", {})

        if not project_structure or project_structure.get("error"):
            return search_paths

        # Get project-specific search paths
        prioritized_paths = []

        # 1. Check if query relates to dependencies
        dependency_paths = _get_dependency_related_paths(
            query, project_dependencies, project_structure
        )
        prioritized_paths.extend(dependency_paths)

        # 2. Get paths based on file types and project structure
        structure_paths = _get_structure_based_paths(query, project_structure)
        prioritized_paths.extend(structure_paths)

        # 3. Add common important directories
        current_dir = session_state.get("current_directory", ".")
        current_path = Path(current_dir)

        common_dirs = ["src", "lib", "app", "components", "utils", "tools", "agents"]
        for dir_name in common_dirs:
            dir_path = current_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                prioritized_paths.append(str(dir_path))

        # Remove duplicates while preserving order
        seen = set()
        final_paths = []
        for path in prioritized_paths:
            if path not in seen:
                final_paths.append(path)
                seen.add(path)

        # If we have specific paths, use them; otherwise fall back to current directory
        search_paths = final_paths if final_paths else [current_dir]

    except Exception as e:
        logger.debug(f"Error determining context-aware search paths: {e}")

    return search_paths


def _get_dependency_related_paths(
    query: str, dependencies: dict[str, Any], _structure: dict[str, Any]
) -> list[str]:
    """Get search paths related to project dependencies."""
    paths = []

    try:
        query_lower = query.lower()

        # Check if query mentions any dependencies
        all_deps = []
        for dep_type in ["python", "javascript", "rust", "go"]:
            all_deps.extend(dependencies.get(dep_type, []))

        # Look for dependency names in query
        for dep in all_deps:
            # Extract package name (remove version specifiers)
            package_name = dep.split(">=")[0].split("==")[0].split("~=")[0].split("@")[0]
            package_name = package_name.strip("\"'")

            if package_name.lower() in query_lower:
                # This query relates to a dependency, prioritize certain paths
                if dependencies.get("python"):
                    paths.extend(["src", "lib", ".", "agents", "tests"])
                elif dependencies.get("javascript"):
                    paths.extend(["src", "lib", "components", "utils", "."])
                break

    except Exception as e:
        logger.debug(f"Error getting dependency-related paths: {e}")

    return paths


def _get_structure_based_paths(query: str, structure: dict[str, Any]) -> list[str]:
    """Get search paths based on project structure and query keywords."""
    paths = []

    try:
        query_lower = query.lower()
        directory_tree = structure.get("directory_tree", {})

        # Keywords that suggest specific directory types
        path_keywords = {
            "test": ["tests", "test", "__tests__", "spec"],
            "config": ["config", "conf", "settings"],
            "util": ["utils", "util", "helpers", "shared"],
            "component": ["components", "widgets", "ui"],
            "agent": ["agents", "agent"],
            "tool": ["tools", "tool"],
            "src": ["src", "source"],
            "lib": ["lib", "library", "libraries"],
            "doc": ["docs", "doc", "documentation"],
        }

        # Check query for keywords and add corresponding paths
        for keyword, dir_names in path_keywords.items():
            if keyword in query_lower:
                for dir_name in dir_names:
                    if _directory_exists_in_structure(dir_name, directory_tree):
                        paths.append(dir_name)

        # Add paths based on file extensions mentioned in query
        file_extensions = {
            ".py": ["src", "agents", "tools", "tests"],
            ".js": ["src", "components", "utils"],
            ".ts": ["src", "components", "utils"],
            ".md": ["docs", ".", "README"],
            ".toml": [".", "config"],
            ".json": [".", "config"],
        }

        for ext, ext_paths in file_extensions.items():
            if ext in query_lower:
                paths.extend(ext_paths)
                break

    except Exception as e:
        logger.debug(f"Error getting structure-based paths: {e}")

    return paths


def _directory_exists_in_structure(dir_name: str, directory_tree: dict[str, Any]) -> bool:
    """Check if a directory exists in the project structure."""
    try:
        children = directory_tree.get("children", {})
        for name, info in children.items():
            if name.lower() == dir_name.lower() and info.get("type") == "directory":
                return True
            # Recursively check subdirectories
            if info.get("type") == "directory":
                if _directory_exists_in_structure(dir_name, info):
                    return True
        return False
    except Exception:
        return False


def _calculate_relevance_score(
    file_path: str, query: str, tool_context: Optional[ToolContext]
) -> float:
    """
    Calculate relevance score for a search result based on project context.

    Args:
        file_path: Path to the file containing the match
        query: Original search query
        tool_context: ADK tool context for session state

    Returns:
        Relevance score (0.0 to 1.0)
    """
    score = 0.5  # Base score

    try:
        if not tool_context or not hasattr(tool_context, "state"):
            return score

        session_state = tool_context.state
        project_structure = session_state.get("project_structure", {})

        path_lower = file_path.lower()
        query_lower = query.lower()

        # Boost score for key project files
        key_files = project_structure.get("key_files", [])
        if any(key_file in file_path for key_file in key_files):
            score += 0.2

        # Boost score for source directories
        if any(src_dir in path_lower for src_dir in ["src/", "lib/", "agents/", "tools/"]):
            score += 0.15

        # Boost score for files matching project type
        file_types = project_structure.get("file_types", {})
        file_ext = Path(file_path).suffix.lower()
        if file_ext in file_types and file_types[file_ext] > 1:  # Common file type
            score += 0.1

        # Boost score for recent files (if we tracked modification times)
        current_dir = session_state.get("current_directory", ".")
        try:
            full_path = Path(current_dir) / file_path
            if full_path.exists():
                # Simple proximity boost - files closer to root get slight boost
                depth = len(Path(file_path).parts)
                if depth <= 3:  # Shallow files get boost
                    score += 0.05
        except Exception:
            pass

        # Penalize deeply nested files more aggressively
        depth_count = file_path.count("/")
        if depth_count > 3:
            score -= 0.11 * (depth_count - 3)  # -0.11 for each level beyond 3

        # Boost for exact query matches in file name
        file_name = Path(file_path).name.lower()
        if query_lower in file_name:
            score += 0.1

        # Ensure score stays in valid range
        score = max(0.0, min(1.0, score))

    except Exception as e:
        logger.debug(f"Error calculating relevance score: {e}")

    return score


def _generate_search_context_summary(
    query: str, search_paths: list[str], tool_context: Optional[ToolContext]
) -> str:
    """Generate a summary of the search context for user information."""
    try:
        if not tool_context or not hasattr(tool_context, "state"):
            return f"Searched for '{query}' in {len(search_paths)} paths"

        session_state = tool_context.state
        project_structure = session_state.get("project_structure", {})
        project_dependencies = session_state.get("project_dependencies", {})

        parts = [f"Searched for '{query}'"]

        # Add project type info
        project_type = project_dependencies.get("dependency_files_found", [])
        if project_type:
            parts.append(f"Project type: {', '.join(project_type)}")

        # Add search scope info
        total_files = project_structure.get("total_files", 0)
        if total_files > 0:
            parts.append(f"Project has {total_files} files")

        parts.append(f"Searched {len(search_paths)} priority paths")

        return " | ".join(parts)

    except Exception as e:
        logger.debug(f"Error generating search context summary: {e}")
        return f"Searched for '{query}'"


# Create FunctionTool wrapper for ripgrep code search
codebase_search_tool = FunctionTool(func=ripgrep_code_search)
