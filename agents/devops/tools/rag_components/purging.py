import logging  # It's good practice to use logging
import os
import shutil

# Attempt to import CHROMA_DATA_PATH from indexing.py in the same directory
try:
    from .indexing import (  # Also get collection name for context
        CHROMA_COLLECTION_NAME,
        CHROMA_DATA_PATH,
    )
except ImportError as e:
    # This fallback is less likely to be needed if they are in the same directory
    # and the package structure is standard.
    logging.error(
        f"Failed to import CHROMA_DATA_PATH from .indexing: {e}. Purging tool may not work correctly."
    )
    # Define a plausible fallback or raise an error if critical
    # For now, let's make it so the script would fail loudly if CHROMA_DATA_PATH is not set.
    CHROMA_DATA_PATH = None
    CHROMA_COLLECTION_NAME = "Unknown"


def purge_rag_index_data():
    """
    Deletes the ChromaDB data directory where the persistent client stores its data.
    This is a destructive operation and will remove all indexed data for the configured
    CHROMA_DATA_PATH.
    """
    if not CHROMA_DATA_PATH:
        message = "Error: CHROMA_DATA_PATH is not configured. Aborting purge."
        logging.error(message)
        return {"status": "error", "message": message}

    if not os.path.isabs(CHROMA_DATA_PATH):
        message = f"Error: CHROMA_DATA_PATH ('{CHROMA_DATA_PATH}') is not an absolute path. Aborting purge for safety."
        logging.error(message)
        return {"status": "error", "message": message}

    logging.warning(f"Attempting to purge RAG index data directory: {CHROMA_DATA_PATH}")
    logging.warning(
        f"This will affect the collection: {CHROMA_COLLECTION_NAME if CHROMA_COLLECTION_NAME else 'Unknown'}"
    )

    if os.path.exists(CHROMA_DATA_PATH):
        if not os.path.isdir(CHROMA_DATA_PATH):
            message = f"Error: Target path {CHROMA_DATA_PATH} exists but is not a directory. Aborting purge."
            logging.error(message)
            return {"status": "error", "message": message}
        try:
            shutil.rmtree(CHROMA_DATA_PATH)
            message = f"Successfully deleted RAG index data directory: {CHROMA_DATA_PATH}"
            logging.info(message)
            return {"status": "success", "message": message}
        except Exception as e:
            message = f"Error deleting RAG index data directory {CHROMA_DATA_PATH}: {e}"
            logging.exception(message)  # Log with stack trace
            return {"status": "error", "message": message, "exception": str(e)}
    else:
        message = f"RAG index data directory {CHROMA_DATA_PATH} does not exist. No action taken."
        logging.info(message)
        return {"status": "success", "message": message, "details": "Directory not found."}


if __name__ == "__main__":
    # Setup basic logging for direct script execution
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not CHROMA_DATA_PATH:
        logging.error("CHROMA_DATA_PATH could not be determined. Exiting.")
    else:
        print("WARNING: This script will permanently delete the ChromaDB data directory.")
        print(f"The target directory is: {CHROMA_DATA_PATH}")
        print(
            f"This is expected to contain data for collection: {CHROMA_COLLECTION_NAME if CHROMA_COLLECTION_NAME else 'Unknown'}"
        )

        confirmation = (
            input("Are you absolutely sure you want to continue? (yes/no): ").strip().lower()
        )
        if confirmation == "yes":
            print("Proceeding with purge operation...")
            result = purge_rag_index_data()
            print(f"Operation result: {result.get('status')} - {result.get('message')}")
        else:
            print("Purge operation cancelled by user.")
