# /Users/james/Agents/devops_v2/rag_components/chunking.py
import ast
import logging

logger = logging.getLogger(__name__)


def chunk_python_code(file_path: str, code_content: str) -> list[dict]:
    """
    Chunks Python code into functions and classes.
    Each chunk includes the name, type (function/class), and the code block.
    Also includes 'module-level' code that is not part of any function/class.

    Args:
        file_path: The path to the Python file (for context in metadata).
        code_content: The string content of the Python file.

    Returns:
        A list of dictionaries, where each dictionary represents a chunk:
        {'file_path': str, 'name': str, 'type': str, 'content': str,
         'start_line': int, 'end_line': int}
    """
    chunks = []
    try:
        tree = ast.parse(code_content)
        lines = code_content.splitlines()

        current_pos = 0  # To track module-level code

        for node in tree.body:
            start_line = node.lineno
            # end_lineno might be None for some nodes or not precise enough for
            # ast.get_source_segment
            # We will rely on ast.get_source_segment for content, and calculate
            # end_line from it if possible

            # Capture module-level code before this node
            if start_line > current_pos + 1:
                module_level_code_chunk = "\n".join(lines[current_pos : start_line - 1]).strip()
                if module_level_code_chunk:
                    chunks.append(
                        {
                            "file_path": file_path,
                            "name": f"module-level_{current_pos + 1}-{start_line - 1}",
                            "type": "module-level",
                            "content": module_level_code_chunk,
                            "start_line": current_pos + 1,
                            "end_line": start_line - 1,
                        }
                    )

            chunk_content = ast.get_source_segment(code_content, node)
            if chunk_content is None:
                # Fallback if get_source_segment fails (e.g. older Python or complex cases)
                # Calculate end_line based on the node's reported end_lineno if available
                node_end_lineno = getattr(node, "end_lineno", start_line)
                chunk_content = (
                    "\n".join(lines[start_line - 1 : node_end_lineno])
                    if node_end_lineno
                    else lines[start_line - 1]
                )
                actual_end_line = start_line + len(chunk_content.splitlines()) - 1
            else:
                actual_end_line = start_line + len(chunk_content.splitlines()) - 1

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunks.append(
                    {
                        "file_path": file_path,
                        "name": node.name,
                        "type": "function",
                        "content": chunk_content,
                        "start_line": start_line,
                        "end_line": actual_end_line,
                    }
                )
            elif isinstance(node, ast.ClassDef):
                chunks.append(
                    {
                        "file_path": file_path,
                        "name": node.name,
                        "type": "class",
                        "content": chunk_content,
                        "start_line": start_line,
                        "end_line": actual_end_line,
                    }
                )
            else:
                # Other top-level statements (imports, assignments, etc.)
                # Group consecutive non-function/class nodes as a single chunk
                if (
                    not chunks
                    or chunks[-1]["type"] not in ["module-level-block"]
                    or chunks[-1]["end_line"] != start_line - 1
                ):
                    chunks.append(
                        {
                            "file_path": file_path,
                            "name": f"module-level-block_{start_line}-{actual_end_line}",
                            "type": "module-level-block",
                            "content": chunk_content,
                            "start_line": start_line,
                            "end_line": actual_end_line,
                        }
                    )
                else:  # Append to existing module-level-block
                    chunks[-1]["content"] += "\n" + chunk_content
                    chunks[-1]["end_line"] = actual_end_line
                    chunks[-1]["name"] = (
                        f"module-level-block_{chunks[-1]['start_line']}-{actual_end_line}"
                    )
            current_pos = actual_end_line

        # Capture any remaining module-level code after the last node
        if current_pos < len(lines):
            remaining_code_chunk = "\n".join(lines[current_pos:]).strip()
            if remaining_code_chunk:
                chunks.append(
                    {
                        "file_path": file_path,
                        "name": f"module-level_{current_pos + 1}-{len(lines)}",
                        "type": "module-level",
                        "content": remaining_code_chunk,
                        "start_line": current_pos + 1,
                        "end_line": len(lines),
                    }
                )

    except SyntaxError as e:
        logger.error(f"Syntax error parsing Python file {file_path}: {e}")
        return [
            {
                "file_path": file_path,
                "name": "file_content_fallback",
                "type": "file",
                "content": code_content,
                "start_line": 1,
                "end_line": len(code_content.splitlines()),
            }
        ]
    except Exception as e:
        logger.error(f"Error chunking Python file {file_path}: {e}")
        return [
            {
                "file_path": file_path,
                "name": "file_content_error_fallback",
                "type": "file",
                "content": code_content,
                "start_line": 1,
                "end_line": len(code_content.splitlines()),
            }
        ]

    return chunks


def chunk_file_content(file_path: str, content: str, strategy: str = "python_ast") -> list[dict]:
    """
    Chunks file content based on the specified strategy.
    Currently supports 'python_ast' for Python files.
    Other file types will be returned as a single chunk.

    Args:
        file_path: The path to the file.
        content: The string content of the file.
        strategy: The chunking strategy to use.

    Returns:
        A list of dictionaries, where each dictionary represents a chunk.
    """
    if strategy == "python_ast" and file_path.endswith(".py"):
        return chunk_python_code(file_path, content)
    # Fallback for non-Python files or other strategies
    logger.info(f"Using fallback chunking for {file_path} (strategy: {strategy})")
    return [
        {
            "file_path": file_path,
            "name": "file_content",
            "type": "file",  # General type for non-specific chunking
            "content": content,
            "start_line": 1,
            "end_line": len(content.splitlines()),
        }
    ]


if __name__ == "__main__":
    # Example Usage (for testing this module directly)
    logging.basicConfig(level=logging.INFO)
    sample_code = """
import os
import sys

# This is a module-level comment

MY_CONSTANT = 123

class MyClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"

def my_function(a, b):
    # A comment inside a function
    result = a + b
    return result

async def my_async_function():
    pass

another_var = "test"
# another comment
if MY_CONSTANT > 100:
    print("Big constant")

"""
    file_path_example = "example.py"
    chunks = chunk_file_content(file_path_example, sample_code, strategy="python_ast")
    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i + 1} ({chunk['type']}: {chunk['name']}) ---")
        print(f"Lines: {chunk['start_line']}-{chunk['end_line']}")
        print(chunk["content"])
        print("\\n")
