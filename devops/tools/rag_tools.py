# /Users/james/Agents/devops_v2/tools/rag_tools.py
import os
import logging
import fnmatch # Added for .indexignore
from pathlib import Path # Added for .indexignore and path manipulation
from typing import Optional # Added import

# from google.adk.tools.utils import tool_utils # For defining ADK tools
from google.adk.tools import FunctionTool, ToolContext # For defining ADK tools and accessing context
from ..rag_components import chunking, indexing # Relative import from parent dir

logger = logging.getLogger(__name__)

# --- Helper functions for .indexignore ---
def _load_ignore_patterns(base_dir: Path, ignore_filename: str = ".indexignore") -> list[str]:
    """Loads patterns from the ignore file, skipping comments and empty lines."""
    ignore_file = base_dir / ignore_filename
    patterns = []
    if ignore_file.is_file():
        try:
            with ignore_file.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
            logger.info(f"Loaded {len(patterns)} patterns from {ignore_filename}")
        except Exception as e:
            logger.error(f"Error reading {ignore_filename}: {e}")
    else:
        logger.info(f"{ignore_filename} not found in {base_dir}. No files will be ignored by it.")
    return patterns

def _is_path_ignored(relative_path_str: str, ignore_patterns: list[str], is_dir: bool) -> bool:
    """
    Checks if a given relative path string matches any ignore patterns.
    - relative_path_str: Path relative to the indexing root (e.g., "src/utils.py", "node_modules").
                         Uses POSIX-style separators ('/').
    - ignore_patterns: List of patterns from .indexignore.
    - is_dir: Boolean, true if the path is a directory.
    """
    # Ensure consistent path separator for matching (POSIX style)
    # Path objects from pathlib will produce OS-specific, convert to POSIX for matching
    # relative_path_str is already expected to be posix from .as_posix()

    for pattern in ignore_patterns:
        # Pattern normalization:
        # If pattern is "foo/", it should match a directory named "foo"
        # or anything under "foo/"
        # If pattern is "foo", it could match a file or directory named "foo"

        is_dir_pattern = pattern.endswith('/')
        normalized_pattern = pattern.rstrip('/')

        # 1. Direct match for directory patterns
        if is_dir_pattern:
            if is_dir and relative_path_str == normalized_pattern: # e.g. pattern "build/", path "build"
                # logger.debug(f"Ignoring dir '{relative_path_str}' due to dir pattern '{pattern}'")
                return True
            if (relative_path_str + '/').startswith(normalized_pattern + '/'): # e.g. pattern "build/", path "build/foo"
                # logger.debug(f"Ignoring path '{relative_path_str}' due to item under dir pattern '{pattern}'")
                return True
            # No else here, a dir pattern like "foo/" should not match a file "foo"

        # 2. fnmatch for glob patterns (files or directories if not a dir_pattern)
        # fnmatch matches the whole string against the pattern.
        # For a pattern like "*.log", relative_path_str must be "file.log", not "somedir/file.log"
        # For a pattern like "somedir/*.log", relative_path_str must be "somedir/file.log"
        
        # Check against the full relative path
        if fnmatch.fnmatch(relative_path_str, pattern):
            # logger.debug(f"Ignoring '{relative_path_str}' due to full match with pattern '{pattern}'")
            return True

        # 3. If pattern has no slashes, it can match a basename anywhere (like .gitignore)
        #    e.g. pattern "*.tmp" should match "foo.tmp" and "bar/baz.tmp"
        #    e.g. pattern "node_modules" (no trailing slash) should match a dir "node_modules" anywhere
        if '/' not in pattern:
            item_name = Path(relative_path_str).name
            if fnmatch.fnmatch(item_name, pattern):
                # logger.debug(f"Ignoring '{relative_path_str}' (basename '{item_name}') due to basename pattern '{pattern}'")
                return True
                
    return False
# --- End of helper functions ---

@FunctionTool # Assuming FunctionTool decorator or similar
def index_directory_tool(directory_path: str, file_extensions: Optional[list[str]] = None, force_reindex: bool = False) -> str:
    """
    Scans a directory for specified file types, chunks their content,
    generates embeddings, and indexes them into the ChromaDB vector store.
    Respects an .indexignore file in the root of directory_path.

    Args:
        directory_path: The absolute path to the directory to scan.
        file_extensions: Optional list of file extensions to process (e.g., ['.py', '.md']).
                         Defaults to ['.py', '.md', '.txt', '.sh', '.yaml', '.yml', '.json', '.tf', '.hcl', '.go'] if None.
        force_reindex: If True, existing entries for a file will be removed and re-indexed.
    Returns:
        A summary message of the indexing process.
    """
    if file_extensions is None:
        file_extensions = ['.py', '.md', '.txt', '.sh', '.yaml', '.yml', '.json', '.tf', '.hcl', '.go'] # Default to a wider set of extensions
    
    # Ensure file_extensions is a set for efficient lookup
    file_extensions_set = set(file_extensions)

    logger.info(f"Starting indexing for directory: {directory_path} with extensions: {file_extensions_set}")

    collection = indexing.get_chroma_collection()
    if not collection:
        return "Error: Failed to get ChromaDB collection. Indexing aborted."

    processed_files = 0
    total_chunks_indexed = 0
    errors = []
    ignored_files_count = 0
    ignored_dirs_count = 0

    root_scan_path = Path(directory_path).resolve()
    if not root_scan_path.is_dir():
        return f"Error: Directory not found at {root_scan_path}"

    # Load ignore patterns
    ignore_patterns = _load_ignore_patterns(root_scan_path)

    for current_root_str, dir_names, file_names in os.walk(str(root_scan_path), topdown=True):
        current_root_path = Path(current_root_str)
        
        # Filter directories (dir_names is modified in-place by os.walk when topdown=True)
        original_dir_names = list(dir_names) # Iterate over a copy
        dir_names[:] = [] # Clear and add back non-ignored ones
        for d_name in original_dir_names:
            dir_abs_path = current_root_path / d_name
            dir_rel_path_str = dir_abs_path.relative_to(root_scan_path).as_posix()
            if not _is_path_ignored(dir_rel_path_str, ignore_patterns, is_dir=True):
                dir_names.append(d_name)
            else:
                logger.info(f"Ignoring directory: {dir_rel_path_str} due to .indexignore rules.")
                ignored_dirs_count +=1
        
        for file_name in file_names:
            file_abs_path = current_root_path / file_name
            file_rel_path_str = file_abs_path.relative_to(root_scan_path).as_posix()

            # 1. Check if file itself is ignored by .indexignore
            if _is_path_ignored(file_rel_path_str, ignore_patterns, is_dir=False):
                logger.info(f"Ignoring file: {file_rel_path_str} due to .indexignore rules.")
                ignored_files_count += 1
                continue

            # 2. Check file extension
            if file_abs_path.suffix not in file_extensions_set:
                # This check is fine, but ensure file_extensions_set is correctly populated
                # logger.debug(f"Skipping file due to extension: {file_rel_path_str} (suffix: {file_abs_path.suffix})")
                continue
            
            logger.info(f"Processing file: {file_abs_path}")
            try:
                with open(file_abs_path, 'r', encoding='utf-8', errors='ignore') as f: # Added errors='ignore'
                    content = f.read()
                
                file_chunks_data = chunking.chunk_file_content(str(file_abs_path), content) # Ensure file_path is str
                
                if not file_chunks_data:
                    logger.warning(f"No chunks generated for {file_abs_path}. Skipping.")
                    continue

                if force_reindex:
                    logger.info(f"Force re-index: Attempting to delete existing chunks for {file_abs_path}")
                    try:
                        query_results = collection.get(where={"file_path": str(file_abs_path)}, include=[]) # Ensure str
                        if query_results and query_results['ids']:
                            existing_ids_to_delete = query_results['ids']
                            if existing_ids_to_delete:
                                logger.info(f"Deleting {len(existing_ids_to_delete)} existing chunks for {file_abs_path}.")
                                collection.delete(ids=existing_ids_to_delete)
                            # else:
                            #     logger.info(f"No existing chunks found to delete for {file_abs_path} during force_reindex.")
                        # else:
                        #     logger.info(f"No existing chunks found (or query failed) for {file_abs_path} during force_reindex attempt.")
                    except Exception as e_del:
                        logger.error(f"Error deleting existing chunks for {file_abs_path} during force_reindex: {e_del}")

                success = indexing.index_file_chunks(collection, file_chunks_data)
                if success:
                    processed_files += 1
                    total_chunks_indexed += len(file_chunks_data)
                    logger.info(f"Successfully indexed {len(file_chunks_data)} chunks from {file_abs_path}.")
                else:
                    logger.error(f"Failed to index chunks from {file_abs_path}.")
                    errors.append(str(file_abs_path))

            except Exception as e:
                logger.error(f"Error processing file {file_abs_path}: {e}")
                errors.append(str(file_abs_path))
    
    summary_message = (
        f"Indexing complete for directory: {root_scan_path}.\n"
        f"Processed {processed_files} files.\n"
        f"Indexed a total of {total_chunks_indexed} chunks.\n"
        f"Ignored {ignored_files_count} files and {ignored_dirs_count} directories based on .indexignore rules.\n"
        f"Current collection size: {collection.count()} items."
    )
    if errors:
        summary_message += f"\nEncountered errors with files: {', '.join(errors)}"
    
    return summary_message


@FunctionTool # Assuming FunctionTool decorator or similar
def retrieve_code_context_tool(query: str, top_k: int = 5) -> dict | str:
    """
    Retrieves relevant code chunks from the indexed codebase based on a natural language query.

    Args:
        query: The natural language query to search for.
        top_k: The number of top relevant chunks to retrieve. Defaults to 5.

    Returns:
        A dictionary containing the retrieved chunks with their metadata and content,
        or an error message string if retrieval fails.
        Structure: {
            "query": str,
            "retrieved_chunks": [
                {"id": str, "metadata": dict, "document": str, "distance": float}, ...
            ]
        }
    """
    logger.info(f"Retrieving context for query: \"{query}\", top_k={top_k}")
    
    from ..rag_components import retriever # Keep import here if it's heavy or has side effects

    retrieved_data = retriever.retrieve_relevant_chunks(query_text=query, top_k=top_k)

    if retrieved_data is None:
        return "Error: Failed to retrieve chunks from the vector store."
    
    if not retrieved_data: # Check if list is empty
        # Return a dict for consistency, even if no chunks found
        return {
            "query": query,
            "retrieved_chunks": [] 
        }
        
    return {
        "query": query,
        "retrieved_chunks": retrieved_data
    }

