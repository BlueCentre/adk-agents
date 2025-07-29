import difflib


def generate_unified_diff(
    old_content: str, new_content: str, old_filename: str = "old", new_filename: str = "new"
) -> str:
    """
    Generates a unified diff between two strings.

    Args:
        old_content: The original content.
        new_content: The new content.
        old_filename: The name of the old file.
        new_filename: The name of the new file.

    Returns:
        A string containing the unified diff.
    """
    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=old_filename,
        tofile=new_filename,
    )
    return "".join(diff)
