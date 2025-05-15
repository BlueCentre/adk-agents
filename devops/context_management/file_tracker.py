"""File change detection for improved context tracking."""

import os
import logging
from typing import List, Dict, Set, Optional, Tuple
import hashlib
import re

# Set up logging
logger = logging.getLogger(__name__)

class FileChangeTracker:
    """Tracks file changes to improve context management."""
    
    def __init__(self):
        """Initialize the file change tracker."""
        self.file_hashes: Dict[str, str] = {}
        self.recently_modified_files: List[str] = []
        self.file_changes: Dict[str, int] = {}  # file_path -> change count
        
    def hash_file_content(self, content: str) -> str:
        """Generate a hash of file content.
        
        Args:
            content: The file content
            
        Returns:
            A hash string
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def register_file_read(self, file_path: str, content: str) -> None:
        """Register a file being read to track its current state.
        
        Args:
            file_path: Path to the file
            content: Current content of the file
        """
        # Store the file's current hash
        content_hash = self.hash_file_content(content)
        self.file_hashes[file_path] = content_hash
        
    def register_file_edit(self, file_path: str, new_content: str) -> bool:
        """Register a file being edited and track if it changed.
        
        Args:
            file_path: Path to the file
            new_content: New content after edit
            
        Returns:
            True if the file actually changed, False otherwise
        """
        new_hash = self.hash_file_content(new_content)
        old_hash = self.file_hashes.get(file_path)
        
        # Check if this is a new file or an actual change
        if old_hash is None or old_hash != new_hash:
            # Update the hash
            self.file_hashes[file_path] = new_hash
            
            # Track as recently modified
            if file_path in self.recently_modified_files:
                self.recently_modified_files.remove(file_path)
            self.recently_modified_files.insert(0, file_path)
            
            # Keep only the 5 most recently modified files
            if len(self.recently_modified_files) > 5:
                self.recently_modified_files.pop()
                
            # Increment change count
            self.file_changes[file_path] = self.file_changes.get(file_path, 0) + 1
            
            return True
        return False
    
    def get_recently_modified_files(self, limit: int = 5) -> List[str]:
        """Get the most recently modified files.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of file paths
        """
        return self.recently_modified_files[:limit]
    
    def extract_modified_functions(self, old_content: str, new_content: str) -> List[str]:
        """Extract names of functions that were modified between versions.
        
        Args:
            old_content: Previous file content
            new_content: New file content
            
        Returns:
            List of modified function names
        """
        # Simple regex to find function definitions
        function_pattern = re.compile(r'(?:def|function|class)\s+([a-zA-Z0-9_]+)')
        
        # Extract all function names from each content
        old_functions = set(function_pattern.findall(old_content))
        new_functions = set(function_pattern.findall(new_content))
        
        # Find added or modified functions
        added_functions = new_functions - old_functions
        
        # For modified functions, we need to compare content
        # This is a simplified approach - we split the content by function
        # definitions and compare each function's content
        potentially_modified = new_functions.intersection(old_functions)
        modified_functions = []
        
        for func_name in potentially_modified:
            # Find function in old content
            old_func_match = re.search(f'(?:def|function|class)\\s+{func_name}[\\s\\(].*?(?=(?:def|function|class)\\s+|$)', 
                                      old_content, re.DOTALL)
            # Find function in new content
            new_func_match = re.search(f'(?:def|function|class)\\s+{func_name}[\\s\\(].*?(?=(?:def|function|class)\\s+|$)', 
                                      new_content, re.DOTALL)
            
            if old_func_match and new_func_match:
                old_func_content = old_func_match.group(0)
                new_func_content = new_func_match.group(0)
                if old_func_content != new_func_content:
                    modified_functions.append(func_name)
        
        # Return both added and modified functions
        return list(added_functions) + modified_functions
        
file_change_tracker = FileChangeTracker() 