"""Project context loading for the Software Engineer Agent."""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def load_project_context(callback_context) -> Optional[dict[str, Any]]:
    """
    Load project context information before agent execution.

    Args:
        callback_context: The ADK callback context

    Returns:
        None - context loading completed without adding extra event content
    """
    try:
        # Get current working directory
        current_dir = Path.cwd()

        # Log project information without returning it in the event
        logger.info("Project context loaded:")
        logger.info(f"  Working directory: {current_dir}")
        logger.info(f"  Project name: {Path(current_dir).name}")

        # Detect project type
        project_files = (
            [str(p.name) for p in Path(current_dir).iterdir()] if Path(current_dir).exists() else []
        )
        if "pyproject.toml" in project_files:
            project_type = "python"
        elif "package.json" in project_files:
            project_type = "javascript"
        elif "Cargo.toml" in project_files:
            project_type = "rust"
        elif "go.mod" in project_files:
            project_type = "go"
        else:
            project_type = "unknown"

        logger.info(f"  Project type: {project_type}")
        logger.info(f"  Files found: {project_files[:10]}...")  # Log first 10 files

        # Store context information in the callback context for tools to use
        if hasattr(callback_context, "user_data"):
            callback_context.user_data["project_context"] = {
                "working_directory": current_dir,
                "project_name": Path(current_dir).name,
                "project_type": project_type,
                "files_found": project_files,
            }

        # Return None to avoid validation errors with Event content
        return None

    except Exception as e:
        logger.error(f"Error loading project context: {e}")
        return None


def map_project_structure(
    root_path: str, max_depth: int = 3, ignore_patterns: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Recursively map the project's file and directory structure.

    Args:
        root_path: The root directory path to start mapping from
        max_depth: Maximum depth for recursive traversal (default: 3)
        ignore_patterns: List of patterns to ignore (gitignore-style)

    Returns:
        Dictionary containing the project structure with metadata
    """
    if ignore_patterns is None:
        ignore_patterns = [
            "/.git/",
            "/node_modules/",
            "/__pycache__/",
            "/.pytest_cache/",
            "/venv/",
            "/.venv/",
            "/env/",
            "/.env/",
            "/.mypy_cache/",
            "/htmlcov/",
            "/.coverage",
            "/dist/",
            "/build/",
            "*.pyc",
            "*.pyo",
            "*.egg-info/",
            ".DS_Store",
            "/.idea/",
            "/.vscode/",
        ]

    try:
        root = Path(root_path).resolve()
        if not root.exists() or not root.is_dir():
            return {"error": f"Invalid root directory: {root_path}"}

        structure = {
            "root_path": str(root),
            "project_name": root.name,
            "total_files": 0,
            "total_directories": 0,
            "file_types": {},
            "directory_tree": {},
            "key_files": [],
            "generated_at": str(Path.cwd()),  # Timestamp-like
        }

        def _should_ignore(path: Path) -> bool:
            """Check if path should be ignored based on patterns"""
            path_str = str(path)
            for pattern in ignore_patterns:
                if pattern.startswith("*") and path_str.endswith(pattern[1:]):
                    return True
                if pattern.endswith("/") and (
                    pattern[1:-1] in path_str or path_str.endswith(pattern[:-1])
                ):
                    return True
                if pattern in path_str:
                    return True
            return False

        def _map_directory(dir_path: Path, current_depth: int = 0) -> dict[str, Any]:
            """Recursively map a directory"""
            if current_depth > max_depth or _should_ignore(dir_path):
                return {}

            dir_info = {
                "type": "directory",
                "children": {},
                "file_count": 0,
                "subdir_count": 0,
            }

            try:
                for item in sorted(dir_path.iterdir()):
                    if _should_ignore(item):
                        continue

                    item_name = item.name
                    if item.is_file():
                        # Track file information
                        file_ext = item.suffix.lower()
                        if file_ext:
                            structure["file_types"][file_ext] = (
                                structure["file_types"].get(file_ext, 0) + 1
                            )

                        dir_info["children"][item_name] = {
                            "type": "file",
                            "size": item.stat().st_size if item.exists() else 0,
                            "extension": file_ext,
                        }

                        # Track key project files
                        if item_name in [
                            "pyproject.toml",
                            "package.json",
                            "Cargo.toml",
                            "go.mod",
                            "requirements.txt",
                            "Dockerfile",
                            "docker-compose.yml",
                            "README.md",
                            "LICENSE",
                            "Makefile",
                            ".gitignore",
                        ]:
                            structure["key_files"].append(str(item.relative_to(root)))

                        structure["total_files"] += 1
                        dir_info["file_count"] += 1

                    elif item.is_dir() and current_depth < max_depth:
                        subdir_info = _map_directory(item, current_depth + 1)
                        if subdir_info:  # Only add if not empty
                            dir_info["children"][item_name] = subdir_info
                            structure["total_directories"] += 1
                            dir_info["subdir_count"] += 1

            except PermissionError:
                logger.debug(f"Permission denied accessing: {dir_path}")
            except Exception as e:
                logger.debug(f"Error processing directory {dir_path}: {e}")

            return dir_info

        # Start mapping from root
        structure["directory_tree"] = _map_directory(root)
        structure["total_directories"] += 1  # Count root directory

        logger.info(
            f"Mapped project structure: {structure['total_files']} files, "
            f"{structure['total_directories']} directories"
        )

        return structure

    except Exception as e:
        logger.error(f"Error mapping project structure: {e}")
        return {"error": str(e)}


def infer_project_dependencies(project_path: str) -> dict[str, Any]:
    """
    Infer project dependencies from common dependency files.

    Args:
        project_path: Path to the project root

    Returns:
        Dictionary containing dependency information by type
    """
    dependencies = {
        "python": [],
        "javascript": [],
        "rust": [],
        "go": [],
        "general": [],
        "dev_dependencies": [],
        "dependency_files_found": [],
    }

    try:
        root = Path(project_path).resolve()

        # Python dependencies
        pyproject_file = root / "pyproject.toml"
        requirements_file = root / "requirements.txt"

        if pyproject_file.exists():
            dependencies["dependency_files_found"].append("pyproject.toml")
            try:
                import tomllib

                with pyproject_file.open("rb") as f:
                    pyproject_data = tomllib.load(f)

                # Extract dependencies from pyproject.toml
                if "project" in pyproject_data and "dependencies" in pyproject_data["project"]:
                    dependencies["python"] = pyproject_data["project"]["dependencies"]

                # Extract optional dependencies
                if (
                    "project" in pyproject_data
                    and "optional-dependencies" in pyproject_data["project"]
                ):
                    for _group, deps in pyproject_data["project"]["optional-dependencies"].items():
                        dependencies["dev_dependencies"].extend(deps)

            except ImportError:
                # Fallback: read as text and parse basic patterns
                content = pyproject_file.read_text()
                dependencies["python"] = _extract_deps_from_text(content, "dependencies")
            except Exception as e:
                logger.debug(f"Error parsing pyproject.toml: {e}")

        if requirements_file.exists():
            dependencies["dependency_files_found"].append("requirements.txt")
            try:
                content = requirements_file.read_text()
                deps = [
                    line.strip()
                    for line in content.split("\n")
                    if line.strip() and not line.startswith("#")
                ]
                dependencies["python"].extend(deps)
            except Exception as e:
                logger.debug(f"Error reading requirements.txt: {e}")

        # JavaScript dependencies
        package_json_file = root / "package.json"
        if package_json_file.exists():
            dependencies["dependency_files_found"].append("package.json")
            try:
                import json

                content = package_json_file.read_text()
                package_data = json.loads(content)

                if "dependencies" in package_data:
                    dependencies["javascript"].extend(list(package_data["dependencies"].keys()))
                if "devDependencies" in package_data:
                    dependencies["dev_dependencies"].extend(
                        list(package_data["devDependencies"].keys())
                    )
            except Exception as e:
                logger.debug(f"Error parsing package.json: {e}")

        # Rust dependencies
        cargo_file = root / "Cargo.toml"
        if cargo_file.exists():
            dependencies["dependency_files_found"].append("Cargo.toml")
            try:
                import tomllib

                with cargo_file.open("rb") as f:
                    cargo_data = tomllib.load(f)

                if "dependencies" in cargo_data:
                    dependencies["rust"] = list(cargo_data["dependencies"].keys())

                if "dev-dependencies" in cargo_data:
                    dependencies["dev_dependencies"].extend(cargo_data["dev-dependencies"].keys())

            except ImportError:
                # Fallback parsing
                content = cargo_file.read_text()
                dependencies["rust"] = _extract_deps_from_text(content, "dependencies")
            except Exception as e:
                logger.debug(f"Error parsing Cargo.toml: {e}")

        # Go dependencies
        go_mod_file = root / "go.mod"
        if go_mod_file.exists():
            dependencies["dependency_files_found"].append("go.mod")
            try:
                content = go_mod_file.read_text()
                deps = []
                in_require = False
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("require"):
                        in_require = True
                        continue
                    if line == ")":
                        in_require = False
                        continue
                    if in_require and line and not line.startswith("//"):
                        # Extract module name from "module version" format
                        parts = line.split()
                        if parts:
                            deps.append(parts[0])
                dependencies["go"] = deps
            except Exception as e:
                logger.debug(f"Error parsing go.mod: {e}")

        # Remove duplicates and empty entries
        for key in dependencies:
            if isinstance(dependencies[key], list):
                dependencies[key] = list(set(filter(None, dependencies[key])))

        total_deps = (
            len(dependencies["python"])
            + len(dependencies["javascript"])
            + len(dependencies["rust"])
            + len(dependencies["go"])
        )

        dep_files_count = len(dependencies["dependency_files_found"])
        logger.info(f"Inferred {total_deps} dependencies from {dep_files_count} files")

        return dependencies

    except Exception as e:
        logger.error(f"Error inferring dependencies: {e}")
        return {"error": str(e)}


def _extract_deps_from_text(content: str, section: str) -> list[str]:
    """Fallback text-based dependency extraction"""
    deps = []
    try:
        lines = content.split("\n")
        in_section = False

        for line in lines:
            line = line.strip()
            if f"[{section}]" in line or f"{section} = [" in line:
                in_section = True
                continue
            if line.startswith("[") and in_section:
                in_section = False
                continue
            if in_section and line and not line.startswith("#"):
                # Extract dependency name from various formats
                if "=" in line:
                    dep = line.split("=")[0].strip().strip("\"'")
                    if dep:
                        deps.append(dep)

    except Exception as e:
        logger.debug(f"Error in text-based dependency extraction: {e}")

    return deps


def update_project_context_in_session(
    session_state: dict[str, Any], project_path: Optional[str] = None
) -> dict[str, Any]:
    """
    Update session state with comprehensive project context information.

    Args:
        session_state: The agent's session state dictionary
        project_path: Optional project path (defaults to current directory)

    Returns:
        Summary of the updated context
    """
    if project_path is None:
        project_path = str(Path.cwd())

    try:
        # Map project structure
        structure = map_project_structure(project_path)

        # Infer dependencies
        dependencies = infer_project_dependencies(project_path)

        # Store in session state
        session_state["project_structure"] = structure
        session_state["project_dependencies"] = dependencies
        session_state["project_context_updated"] = project_path  # Use actual project path

        # Also update current_directory if not set
        if "current_directory" not in session_state:
            session_state["current_directory"] = project_path

        summary = {
            "structure_mapped": not structure.get("error"),
            "dependencies_found": not dependencies.get("error"),
            "total_files": structure.get("total_files", 0),
            "total_directories": structure.get("total_directories", 0),
            "dependency_files": dependencies.get("dependency_files_found", []),
            "project_type": _detect_project_type(dependencies),
        }

        logger.info(f"Updated project context in session: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Error updating project context in session: {e}")
        return {"error": str(e)}


def _detect_project_type(dependencies: dict[str, Any]) -> str:
    """Detect primary project type based on dependencies"""
    if dependencies.get("python"):
        return "python"
    if dependencies.get("javascript"):
        return "javascript"
    if dependencies.get("rust"):
        return "rust"
    if dependencies.get("go"):
        return "go"
    return "unknown"


def memorize_context(key: str, value: str, context: dict):
    """
    Store information in the project context.

    Args:
        key: The key to store the value under.
        value: The value to store.
        context: The context dictionary to update.

    Returns:
        A status message.
    """
    context[key] = value
    return {"status": f'Stored "{key}": "{value}" in project context'}
