"""Dynamic context expansion for automatic discovery and gathering of relevant context."""

import logging
import os
import re
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import subprocess
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ExpansionContext:
    """Context information for dynamic expansion."""
    current_task: str = ""
    error_context: bool = False
    file_context: Set[str] = None
    keywords: List[str] = None
    max_files_to_explore: int = 20
    max_depth: int = 3
    current_working_directory: str = ""

    def __post_init__(self):
        if self.file_context is None:
            self.file_context = set()
        if self.keywords is None:
            self.keywords = []

@dataclass
class DiscoveredContent:
    """Container for discovered content during expansion."""
    file_path: str
    content_type: str  # 'code', 'config', 'documentation', 'dependency'
    relevance_score: float
    summary: str
    full_path: str
    size_bytes: int

class DynamicContextExpander:
    """Implements dynamic context expansion through intelligent exploration."""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        
        # File patterns for different types of relevant files
        self.patterns = {
            'config': [
                r'.*\.json$', r'.*\.yaml$', r'.*\.yml$', r'.*\.toml$', 
                r'.*\.ini$', r'.*\.cfg$', r'.*\.conf$', r'.*\.env$',
                r'^\..*rc$', r'Dockerfile', r'docker-compose.*\.yml',
                r'Makefile', r'.*\.mk$'
            ],
            'python_code': [
                r'.*\.py$', r'.*\.pyx$', r'.*\.pyi$'
            ],
            'js_code': [
                r'.*\.js$', r'.*\.jsx$', r'.*\.ts$', r'.*\.tsx$',
                r'.*\.vue$', r'.*\.mjs$'
            ],
            'documentation': [
                r'README.*', r'.*\.md$', r'.*\.rst$', r'.*\.txt$',
                r'CHANGELOG.*', r'LICENSE.*', r'CONTRIBUTING.*'
            ],
            'dependency': [
                r'requirements.*\.txt$', r'package\.json$', r'package-lock\.json$',
                r'yarn\.lock$', r'Pipfile', r'poetry\.lock$', r'pyproject\.toml$',
                r'setup\.py$', r'setup\.cfg$', r'Cargo\.toml$', r'go\.mod$'
            ]
        }
        
        # Ignore patterns for files/directories to skip
        self.ignore_patterns = [
            r'__pycache__', r'\.pyc$', r'\.git', r'node_modules',
            r'\.venv', r'venv', r'\.env', r'build', r'dist',
            r'\.DS_Store', r'\.cache', r'\.pytest_cache',
            r'\.coverage', r'htmlcov', r'\.tox'
        ]
        
        # Error pattern recognition
        self.error_patterns = {
            'import_error': [
                r'ImportError:', r'ModuleNotFoundError:', r'No module named',
                r'import\s+(\w+)', r'from\s+(\w+)\s+import'
            ],
            'file_error': [
                r'FileNotFoundError:', r'No such file or directory',
                r'Permission denied', r'file.*not found'
            ],
            'syntax_error': [
                r'SyntaxError:', r'IndentationError:', r'TabError:',
                r'invalid syntax', r'unexpected token'
            ],
            'dependency_error': [
                r'package.*not found', r'dependency.*missing',
                r'version.*conflict', r'incompatible.*version'
            ]
        }
    
    def expand_context(
        self,
        expansion_context: ExpansionContext,
        current_files: Set[str] = None,
        current_errors: List[str] = None
    ) -> List[DiscoveredContent]:
        """Main entry point for dynamic context expansion."""
        
        if current_files is None:
            current_files = set()
        if current_errors is None:
            current_errors = []
        
        logger.info("DYNAMIC CONTEXT EXPANSION: Starting intelligent context discovery...")
        logger.info(f"  Working Directory: {expansion_context.current_working_directory or self.workspace_root}")
        logger.info(f"  Current Files in Context: {len(current_files)}")
        logger.info(f"  Keywords: {expansion_context.keywords}")
        logger.info(f"  Error Context: {expansion_context.error_context}")
        
        discovered_content = []
        
        # 1. Error-driven expansion
        if expansion_context.error_context and current_errors:
            logger.info("  🔍 PHASE 1: Error-driven context expansion...")
            error_discovered = self._expand_from_errors(current_errors, expansion_context)
            discovered_content.extend(error_discovered)
            logger.info(f"    Found {len(error_discovered)} error-related files")
        
        # 2. File dependency expansion
        if current_files:
            logger.info("  🔍 PHASE 2: File dependency expansion...")
            dependency_discovered = self._expand_from_file_dependencies(current_files, expansion_context)
            discovered_content.extend(dependency_discovered)
            logger.info(f"    Found {len(dependency_discovered)} dependency-related files")
        
        # 3. Directory structure exploration
        logger.info("  🔍 PHASE 3: Directory structure exploration...")
        structure_discovered = self._explore_directory_structure(expansion_context)
        discovered_content.extend(structure_discovered)
        logger.info(f"    Found {len(structure_discovered)} structurally relevant files")
        
        # 4. Keyword-based discovery
        if expansion_context.keywords:
            logger.info("  🔍 PHASE 4: Keyword-based discovery...")
            keyword_discovered = self._discover_by_keywords(expansion_context.keywords, expansion_context)
            discovered_content.extend(keyword_discovered)
            logger.info(f"    Found {len(keyword_discovered)} keyword-related files")
        
        # 5. Deduplicate and score
        unique_discovered = self._deduplicate_and_score(discovered_content, current_files)
        
        # 6. Sort by relevance and limit results
        unique_discovered.sort(key=lambda x: x.relevance_score, reverse=True)
        final_results = unique_discovered[:expansion_context.max_files_to_explore]
        
        # Log final results
        logger.info(f"  📊 FINAL RESULTS: {len(final_results)} files discovered")
        for i, content in enumerate(final_results[:5]):
            logger.info(f"    {i+1}. {content.file_path} ({content.content_type}, score: {content.relevance_score:.2f})")
        
        return final_results
    
    def _expand_from_errors(
        self, 
        errors: List[str], 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Expand context based on error messages."""
        
        discovered = []
        
        for error in errors:
            error_type = self._classify_error(error)
            logger.debug(f"    Analyzing {error_type} error: {error[:100]}...")
            
            if error_type == 'import_error':
                discovered.extend(self._find_import_related_files(error, context))
            elif error_type == 'file_error':
                discovered.extend(self._find_file_error_related_files(error, context))
            elif error_type == 'syntax_error':
                discovered.extend(self._find_syntax_error_related_files(error, context))
            elif error_type == 'dependency_error':
                discovered.extend(self._find_dependency_error_related_files(error, context))
        
        return discovered
    
    def _expand_from_file_dependencies(
        self, 
        current_files: Set[str], 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Expand context by analyzing dependencies of current files."""
        
        discovered = []
        
        for file_path in current_files:
            if not os.path.exists(file_path):
                continue
            
            logger.debug(f"    Analyzing dependencies for: {file_path}")
            
            # Analyze based on file type
            if file_path.endswith('.py'):
                discovered.extend(self._analyze_python_dependencies(file_path, context))
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                discovered.extend(self._analyze_js_dependencies(file_path, context))
            elif file_path.endswith(('.json', '.yaml', '.yml', '.toml')):
                discovered.extend(self._analyze_config_dependencies(file_path, context))
        
        return discovered
    
    def _explore_directory_structure(self, context: ExpansionContext) -> List[DiscoveredContent]:
        """Explore directory structure to find relevant files."""
        
        discovered = []
        working_dir = Path(context.current_working_directory) if context.current_working_directory else self.workspace_root
        
        # Start from current working directory and explore key directories
        key_directories = [
            working_dir,
            working_dir / 'src',
            working_dir / 'lib',
            working_dir / 'app',
            working_dir / 'config',
            working_dir / 'docs',
            working_dir / 'scripts',
            working_dir / 'tests'
        ]
        
        for directory in key_directories:
            if directory.exists() and directory.is_dir():
                discovered.extend(self._scan_directory(directory, context, max_depth=context.max_depth))
        
        return discovered
    
    def _discover_by_keywords(self, keywords: List[str], context: ExpansionContext) -> List[DiscoveredContent]:
        """Discover files based on keyword matching."""
        
        discovered = []
        working_dir = Path(context.current_working_directory) if context.current_working_directory else self.workspace_root
        
        try:
            # Use grep-like search for keyword discovery
            for keyword in keywords[:5]:  # Limit to first 5 keywords
                matches = self._search_files_for_keyword(keyword, working_dir, context)
                discovered.extend(matches)
        except Exception as e:
            logger.warning(f"    Error during keyword search: {e}")
        
        return discovered
    
    def _classify_error(self, error: str) -> str:
        """Classify error type based on error message."""
        
        error_lower = error.lower()
        
        for error_type, patterns in self.error_patterns.items():
            if any(re.search(pattern, error, re.IGNORECASE) for pattern in patterns):
                return error_type
        
        return 'unknown'
    
    def _find_import_related_files(
        self, 
        error: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Find files related to import errors."""
        
        discovered = []
        
        # Extract module names from import error
        import_patterns = [
            r'No module named [\'"]([^\'"]+)[\'"]',
            r'ImportError:.*[\'"]([^\'"]+)[\'"]',
            r'from\s+([^\s]+)\s+import',
            r'import\s+([^\s,]+)'
        ]
        
        modules = []
        for pattern in import_patterns:
            matches = re.findall(pattern, error)
            modules.extend(matches)
        
        # Search for files that might contain these modules
        for module in modules[:3]:  # Limit to first 3 modules
            module_parts = module.split('.')
            
            # Look for Python files with matching names
            for part in module_parts:
                potential_files = [
                    f"{part}.py",
                    f"{part}/__init__.py",
                    f"src/{part}.py",
                    f"lib/{part}.py",
                    f"app/{part}.py"
                ]
                
                for potential_file in potential_files:
                    full_path = self.workspace_root / potential_file
                    if full_path.exists():
                        discovered.append(self._create_discovered_content(
                            str(full_path), 'python_code', 0.8, f"Potential fix for import error: {module}"
                        ))
        
        return discovered
    
    def _find_file_error_related_files(
        self, 
        error: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Find files related to file not found errors."""
        
        discovered = []
        
        # Extract file paths from error messages
        file_patterns = [
            r'[\'"]([^\'\"]+\.[a-zA-Z0-9]+)[\'"]',
            r'No such file or directory: [\'"]([^\'"]+)[\'"]',
            r'FileNotFoundError:.*[\'"]([^\'"]+)[\'"]'
        ]
        
        files = []
        for pattern in file_patterns:
            matches = re.findall(pattern, error)
            files.extend(matches)
        
        # Look for similar files or directory structure that might help
        for file_path in files[:3]:
            # Try to find files with similar names
            file_name = os.path.basename(file_path)
            file_stem = os.path.splitext(file_name)[0]
            
            similar_files = self._find_similar_files(file_stem, context)
            discovered.extend(similar_files)
        
        return discovered
    
    def _find_syntax_error_related_files(
        self, 
        error: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Find files related to syntax errors."""
        
        discovered = []
        
        # Extract file information from syntax errors
        file_pattern = r'File "([^"]+)"'
        matches = re.findall(file_pattern, error)
        
        for file_path in matches:
            if os.path.exists(file_path):
                # Look for related files in the same directory
                directory = os.path.dirname(file_path)
                related_files = self._scan_directory(Path(directory), context, max_depth=1)
                discovered.extend(related_files[:5])  # Limit to 5 related files
        
        return discovered
    
    def _find_dependency_error_related_files(
        self, 
        error: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Find files related to dependency errors."""
        
        discovered = []
        
        # Look for dependency files
        dependency_files = [
            'requirements.txt', 'requirements-dev.txt', 'pyproject.toml',
            'package.json', 'package-lock.json', 'yarn.lock',
            'Pipfile', 'poetry.lock', 'setup.py', 'setup.cfg'
        ]
        
        for dep_file in dependency_files:
            full_path = self.workspace_root / dep_file
            if full_path.exists():
                discovered.append(self._create_discovered_content(
                    str(full_path), 'dependency', 0.9, f"Dependency configuration file"
                ))
        
        return discovered
    
    def _analyze_python_dependencies(
        self, 
        file_path: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Analyze Python file dependencies."""
        
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract imports
            import_patterns = [
                r'^\s*import\s+([^\s,#]+)',
                r'^\s*from\s+([^\s,#]+)\s+import'
            ]
            
            imports = []
            for pattern in import_patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                imports.extend(matches)
            
            # Look for corresponding files
            for imp in imports[:10]:  # Limit to first 10 imports
                if imp.startswith('.'):  # Relative import
                    base_dir = os.path.dirname(file_path)
                    potential_file = os.path.join(base_dir, f"{imp[1:]}.py")
                else:
                    potential_files = [
                        f"{imp}.py",
                        f"{imp}/__init__.py",
                        f"src/{imp}.py",
                        f"lib/{imp}.py"
                    ]
                    
                    for pot_file in potential_files:
                        full_path = self.workspace_root / pot_file
                        if full_path.exists():
                            discovered.append(self._create_discovered_content(
                                str(full_path), 'python_code', 0.6, f"Imported by {os.path.basename(file_path)}"
                            ))
                            break
        
        except Exception as e:
            logger.debug(f"    Error analyzing Python dependencies in {file_path}: {e}")
        
        return discovered
    
    def _analyze_js_dependencies(
        self, 
        file_path: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Analyze JavaScript/TypeScript file dependencies."""
        
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract imports/requires
            import_patterns = [
                r'import.*from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
                r'import\([\'"]([^\'"]+)[\'"]\)'
            ]
            
            imports = []
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
            
            # Look for corresponding files
            for imp in imports[:10]:
                if imp.startswith('./') or imp.startswith('../'):
                    # Relative import
                    base_dir = os.path.dirname(file_path)
                    potential_files = [
                        os.path.join(base_dir, f"{imp}.js"),
                        os.path.join(base_dir, f"{imp}.ts"),
                        os.path.join(base_dir, f"{imp}/index.js"),
                        os.path.join(base_dir, f"{imp}/index.ts")
                    ]
                    
                    for pot_file in potential_files:
                        if os.path.exists(pot_file):
                            discovered.append(self._create_discovered_content(
                                pot_file, 'js_code', 0.6, f"Imported by {os.path.basename(file_path)}"
                            ))
                            break
        
        except Exception as e:
            logger.debug(f"    Error analyzing JS dependencies in {file_path}: {e}")
        
        return discovered
    
    def _analyze_config_dependencies(
        self, 
        file_path: str, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Analyze configuration file dependencies."""
        
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for file references in config
            file_patterns = [
                r'[\'"]([^\'\"]+\.[a-zA-Z0-9]+)[\'"]',  # General file references
                r'"file":\s*"([^"]+)"',                  # JSON file references
                r'file:\s*([^\s]+)',                     # YAML file references
            ]
            
            referenced_files = []
            for pattern in file_patterns:
                matches = re.findall(pattern, content)
                referenced_files.extend(matches)
            
            # Check if referenced files exist
            for ref_file in referenced_files[:5]:
                potential_paths = [
                    ref_file,
                    os.path.join(os.path.dirname(file_path), ref_file),
                    os.path.join(self.workspace_root, ref_file)
                ]
                
                for pot_path in potential_paths:
                    if os.path.exists(pot_path):
                        file_type = self._classify_file_type(pot_path)
                        discovered.append(self._create_discovered_content(
                            pot_path, file_type, 0.5, f"Referenced by {os.path.basename(file_path)}"
                        ))
                        break
        
        except Exception as e:
            logger.debug(f"    Error analyzing config dependencies in {file_path}: {e}")
        
        return discovered
    
    def _scan_directory(
        self, 
        directory: Path, 
        context: ExpansionContext, 
        max_depth: int = 2, 
        current_depth: int = 0
    ) -> List[DiscoveredContent]:
        """Scan directory for relevant files."""
        
        if current_depth >= max_depth:
            return []
        
        discovered = []
        
        try:
            for item in directory.iterdir():
                # Skip ignored patterns
                if any(re.search(pattern, str(item)) for pattern in self.ignore_patterns):
                    continue
                
                if item.is_file():
                    file_type = self._classify_file_type(str(item))
                    if file_type != 'unknown':
                        relevance_score = self._calculate_file_relevance(str(item), context)
                        if relevance_score > 0.1:  # Only include files with some relevance
                            discovered.append(self._create_discovered_content(
                                str(item), file_type, relevance_score, f"Found in {directory.name}/"
                            ))
                elif item.is_dir() and current_depth < max_depth - 1:
                    # Recursively scan subdirectories
                    sub_discovered = self._scan_directory(item, context, max_depth, current_depth + 1)
                    discovered.extend(sub_discovered)
        
        except PermissionError:
            logger.debug(f"    Permission denied scanning directory: {directory}")
        except Exception as e:
            logger.debug(f"    Error scanning directory {directory}: {e}")
        
        return discovered
    
    def _search_files_for_keyword(
        self, 
        keyword: str, 
        directory: Path, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Search files for keyword using grep-like functionality."""
        
        discovered = []
        
        try:
            # Use subprocess to run grep for efficiency
            result = subprocess.run(
                ['grep', '-r', '-l', '--include=*.py', '--include=*.js', '--include=*.md', 
                 '--include=*.json', '--include=*.yaml', '--include=*.yml', keyword, str(directory)],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                for file_path in files[:10]:  # Limit results
                    if os.path.exists(file_path):
                        file_type = self._classify_file_type(file_path)
                        discovered.append(self._create_discovered_content(
                            file_path, file_type, 0.7, f"Contains keyword: {keyword}"
                        ))
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to Python-based search
            logger.debug(f"    Grep not available, using Python search for: {keyword}")
            discovered.extend(self._python_keyword_search(keyword, directory, context))
        
        return discovered
    
    def _python_keyword_search(
        self, 
        keyword: str, 
        directory: Path, 
        context: ExpansionContext
    ) -> List[DiscoveredContent]:
        """Python-based keyword search fallback."""
        
        discovered = []
        search_extensions = ['.py', '.js', '.md', '.json', '.yaml', '.yml', '.txt']
        
        try:
            for item in directory.rglob('*'):
                if item.is_file() and item.suffix in search_extensions:
                    try:
                        with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if keyword.lower() in content.lower():
                                file_type = self._classify_file_type(str(item))
                                discovered.append(self._create_discovered_content(
                                    str(item), file_type, 0.6, f"Contains keyword: {keyword}"
                                ))
                                
                                if len(discovered) >= 10:  # Limit results
                                    break
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"    Error in Python keyword search: {e}")
        
        return discovered
    
    def _find_similar_files(self, file_stem: str, context: ExpansionContext) -> List[DiscoveredContent]:
        """Find files with similar names."""
        
        discovered = []
        
        try:
            # Search for files with similar names
            for item in self.workspace_root.rglob('*'):
                if item.is_file():
                    item_stem = item.stem.lower()
                    if (file_stem.lower() in item_stem or 
                        item_stem in file_stem.lower() or
                        any(part in item_stem for part in file_stem.lower().split('_'))):
                        
                        file_type = self._classify_file_type(str(item))
                        if file_type != 'unknown':
                            discovered.append(self._create_discovered_content(
                                str(item), file_type, 0.4, f"Similar to: {file_stem}"
                            ))
                            
                            if len(discovered) >= 5:  # Limit results
                                break
        except Exception as e:
            logger.debug(f"    Error finding similar files: {e}")
        
        return discovered
    
    def _classify_file_type(self, file_path: str) -> str:
        """Classify file type based on patterns."""
        
        file_name = os.path.basename(file_path).lower()
        
        for file_type, patterns in self.patterns.items():
            if any(re.match(pattern, file_name) for pattern in patterns):
                return file_type
        
        return 'unknown'
    
    def _calculate_file_relevance(self, file_path: str, context: ExpansionContext) -> float:
        """Calculate relevance score for a file."""
        
        score = 0.0
        file_name = os.path.basename(file_path).lower()
        
        # Base score by file type
        file_type = self._classify_file_type(file_path)
        type_scores = {
            'config': 0.8,
            'dependency': 0.9,
            'python_code': 0.7,
            'js_code': 0.7,
            'documentation': 0.5
        }
        score += type_scores.get(file_type, 0.3)
        
        # Keyword matching bonus
        for keyword in context.keywords:
            if keyword.lower() in file_name:
                score += 0.3
        
        # Error context bonus
        if context.error_context:
            error_keywords = ['error', 'exception', 'test', 'debug', 'log']
            if any(keyword in file_name for keyword in error_keywords):
                score += 0.2
        
        # File context proximity bonus
        if context.file_context:
            for existing_file in context.file_context:
                if os.path.dirname(file_path) == os.path.dirname(existing_file):
                    score += 0.3
                    break
        
        return min(score, 1.0)
    
    def _create_discovered_content(
        self, 
        file_path: str, 
        content_type: str, 
        relevance_score: float, 
        summary: str
    ) -> DiscoveredContent:
        """Create a DiscoveredContent object."""
        
        try:
            size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except:
            size_bytes = 0
        
        return DiscoveredContent(
            file_path=os.path.relpath(file_path, self.workspace_root),
            content_type=content_type,
            relevance_score=relevance_score,
            summary=summary,
            full_path=file_path,
            size_bytes=size_bytes
        )
    
    def _deduplicate_and_score(
        self, 
        discovered_content: List[DiscoveredContent], 
        current_files: Set[str]
    ) -> List[DiscoveredContent]:
        """Remove duplicates and adjust scores."""
        
        # Deduplicate by file path
        seen_files = set()
        unique_content = []
        
        for content in discovered_content:
            if content.full_path not in seen_files and content.full_path not in current_files:
                seen_files.add(content.full_path)
                unique_content.append(content)
        
        return unique_content 