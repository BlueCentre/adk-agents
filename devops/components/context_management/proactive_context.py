"""Proactive context gathering for enhanced agent understanding."""

import os
import subprocess
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class ProactiveContextGatherer:
    """Gathers proactive context from project files, Git history, and documentation."""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.max_file_size = 50000  # Max chars per file to avoid token bloat
        self.max_git_commits = 10   # Max recent commits to include
        
    def gather_all_context(self) -> Dict[str, Any]:
        """Gather all available proactive context."""
        context = {}
        
        # Gather project files
        project_files = self._gather_project_files()
        if project_files:
            context["project_files"] = project_files
            logger.info(f"Gathered {len(project_files)} project files for proactive context")
            
        # Gather Git history
        git_history = self._gather_git_history()
        if git_history:
            context["git_history"] = git_history
            logger.info(f"Gathered {len(git_history)} Git commits for proactive context")
            
        # Gather documentation
        documentation = self._gather_documentation()
        if documentation:
            context["documentation"] = documentation
            logger.info(f"Gathered {len(documentation)} documentation files for proactive context")
            
        return context
    
    def _gather_project_files(self) -> List[Dict[str, Any]]:
        """Gather key project configuration and metadata files."""
        project_files = []
        
        # Define important project files to look for
        important_files = [
            "README.md", "readme.md", "README.txt", "README.rst",
            "package.json", "package-lock.json",
            "requirements.txt", "requirements-dev.txt", 
            "pyproject.toml", "setup.py", "setup.cfg", "uv.lock",  # uv.lock for uv projects
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            ".env.example", ".env.template",
            "Makefile", "makefile",
            "CHANGELOG.md", "CHANGES.md", "HISTORY.md",
            "LICENSE", "LICENSE.txt", "LICENSE.md",
            "CONTRIBUTING.md", "CONTRIBUTING.txt",
            ".gitignore", ".dockerignore",
            "tsconfig.json", "webpack.config.js",
            "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
            "composer.json", "Gemfile",
        ]
        
        for filename in important_files:
            file_path = self.workspace_root / filename
            if file_path.exists() and file_path.is_file():
                try:
                    content = self._read_file_safely(file_path)
                    if content:
                        project_files.append({
                            "file_path": str(file_path.relative_to(self.workspace_root)),
                            "content": content,
                            "file_type": self._get_file_type(filename),
                            "size": len(content)
                        })
                        logger.debug(f"Added project file: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to read project file {filename}: {e}")
                    
        return project_files
    
    def _gather_git_history(self) -> List[Dict[str, Any]]:
        """Gather recent Git commit history for context."""
        git_history = []
        
        try:
            # Check if we're in a Git repository
            if not (self.workspace_root / ".git").exists():
                logger.debug("No Git repository found, skipping Git history")
                return git_history
                
            # Get recent commits
            cmd = [
                "git", "log", 
                f"--max-count={self.max_git_commits}",
                "--pretty=format:%H|%an|%ad|%s",
                "--date=short"
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.workspace_root,
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|', 3)
                        if len(parts) == 4:
                            commit_hash, author, date, message = parts
                            git_history.append({
                                "commit_hash": commit_hash[:8],  # Short hash
                                "author": author,
                                "date": date,
                                "message": message,
                            })
                            
        except subprocess.TimeoutExpired:
            logger.warning("Git log command timed out")
        except Exception as e:
            logger.warning(f"Failed to gather Git history: {e}")
            
        return git_history
    
    def _gather_documentation(self) -> List[Dict[str, Any]]:
        """Gather documentation files for context."""
        documentation = []
        
        # Look for common documentation directories and files
        doc_patterns = [
            "docs/", "doc/", "documentation/",
            "*.md", "*.rst", "*.txt"
        ]
        
        doc_dirs = ["docs", "doc", "documentation", "wiki"]
        
        # Check for documentation directories
        for doc_dir in doc_dirs:
            doc_path = self.workspace_root / doc_dir
            if doc_path.exists() and doc_path.is_dir():
                try:
                    for file_path in doc_path.rglob("*"):
                        if file_path.is_file() and self._is_documentation_file(file_path):
                            content = self._read_file_safely(file_path)
                            if content:
                                documentation.append({
                                    "file_path": str(file_path.relative_to(self.workspace_root)),
                                    "content": content,
                                    "file_type": file_path.suffix.lower(),
                                    "size": len(content)
                                })
                                logger.debug(f"Added documentation file: {file_path.relative_to(self.workspace_root)}")
                except Exception as e:
                    logger.warning(f"Failed to scan documentation directory {doc_dir}: {e}")
                    
        # Also look for standalone documentation files in root
        for pattern in ["*.md", "*.rst", "*.txt"]:
            for file_path in self.workspace_root.glob(pattern):
                if file_path.is_file() and self._is_documentation_file(file_path):
                    # Skip if already included in project_files
                    if file_path.name.upper() in ["README.MD", "CHANGELOG.MD", "CONTRIBUTING.MD", "LICENSE.MD"]:
                        continue
                        
                    try:
                        content = self._read_file_safely(file_path)
                        if content:
                            documentation.append({
                                "file_path": str(file_path.relative_to(self.workspace_root)),
                                "content": content,
                                "file_type": file_path.suffix.lower(),
                                "size": len(content)
                            })
                            logger.debug(f"Added standalone documentation: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"Failed to read documentation file {file_path.name}: {e}")
                        
        return documentation
    
    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Safely read a file with size limits and encoding handling."""
        try:
            # Check file size first
            if file_path.stat().st_size > self.max_file_size:
                logger.debug(f"Skipping {file_path.name} - too large ({file_path.stat().st_size} bytes)")
                return None
                
            # Try to read with UTF-8, fall back to latin-1 if needed
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    
            # Truncate if too long
            if len(content) > self.max_file_size:
                content = content[:self.max_file_size] + "\n... [TRUNCATED]"
                
            return content
            
        except Exception as e:
            logger.debug(f"Failed to read {file_path.name}: {e}")
            return None
    
    def _get_file_type(self, filename: str) -> str:
        """Determine the type of project file."""
        filename_lower = filename.lower()
        
        if filename_lower.startswith("readme"):
            return "readme"
        elif filename_lower in ["package.json", "package-lock.json"]:
            return "nodejs"
        elif filename_lower in ["requirements.txt", "requirements-dev.txt"]:
            return "python_legacy"  # Legacy pip requirements
        elif filename_lower in ["pyproject.toml", "setup.py", "setup.cfg"]:
            return "python_modern"  # Modern Python packaging (uv compatible)
        elif filename_lower in ["uv.lock"]:
            return "python_uv_lock"  # uv lockfile
        elif filename_lower in ["dockerfile", "docker-compose.yml", "docker-compose.yaml"]:
            return "docker"
        elif filename_lower in ["makefile"]:
            return "build"
        elif filename_lower.startswith("changelog") or filename_lower.startswith("history"):
            return "changelog"
        elif filename_lower in ["license", "license.txt", "license.md"]:
            return "license"
        elif filename_lower.startswith("contributing"):
            return "contributing"
        elif filename_lower.endswith("ignore"):
            return "ignore_file"
        else:
            return "config"
    
    def _is_documentation_file(self, file_path: Path) -> bool:
        """Check if a file is likely documentation."""
        name_lower = file_path.name.lower()
        suffix_lower = file_path.suffix.lower()
        
        # Skip binary files and very large files
        if suffix_lower in ['.exe', '.bin', '.so', '.dll', '.img', '.iso']:
            return False
            
        # Skip hidden files
        if name_lower.startswith('.'):
            return False
            
        # Include common documentation extensions
        if suffix_lower in ['.md', '.rst', '.txt', '.adoc', '.asciidoc']:
            return True
            
        # Include files with documentation-like names
        doc_keywords = ['readme', 'changelog', 'history', 'guide', 'tutorial', 'manual', 'doc', 'documentation']
        if any(keyword in name_lower for keyword in doc_keywords):
            return True
            
        return False 