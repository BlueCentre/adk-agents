import logging
import os
from pathlib import Path
import tempfile
import time

import chromadb
from dotenv import load_dotenv  # Added import
from google import (
    genai as google_genai_sdk,  # Renamed to avoid conflict with a potential genai client instance
)
from google.api_core import exceptions as google_exceptions

# Import agent configuration
from ...config import CHROMA_DATA_PATH as CONFIGURED_CHROMA_DATA_PATH, GOOGLE_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()  # Added call


# --- Configuration ---
def get_chroma_data_path():
    """Get a writable path for ChromaDB data with fallbacks."""
    # Try multiple potential locations in order of preference
    potential_paths = [
        # 1. Environment variable (highest priority)
        CONFIGURED_CHROMA_DATA_PATH,
        # 2. Current working directory + .index_data subfolder
        Path.joinpath(Path.cwd(), ".index_data", "chroma_data"),
        # 3. Home directory + .adk/devops_agent subfolder
        Path.joinpath(Path.home(), ".adk", "devops_agent", "chroma_data"),
        # 4. Original path from __file__ (kept for backward compatibility)
        Path.absolute(Path.joinpath(Path(__file__).parent, "chroma_data")),
        # 5. System temp directory (final fallback)
        Path.joinpath(Path(tempfile.gettempdir()), "devops_agent_chroma_data"),
    ]

    # Try each path until we find one that's writable
    for path in potential_paths:
        if not path:
            continue

        try:
            # Create the directory if it doesn't exist
            Path(path).mkdir(parents=True, exist_ok=True)

            # Test if we can write to it
            test_file = Path.joinpath(Path(path), ".write_test")
            with test_file.open("w") as f:
                f.write("test")
            test_file.unlink()

            logger.info(f"Using ChromaDB data path: {path}")
            return path
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot use path {path} for ChromaDB data: {e}")

    # If all paths fail, create a new directory in the temp folder with a unique name
    fallback_path = Path.joinpath(Path(tempfile.gettempdir()), f"devops_agent_chroma_{os.getpid()}")
    fallback_path.mkdir(parents=True, exist_ok=True)
    logger.warning(f"Using fallback temp directory for ChromaDB: {fallback_path}")
    return fallback_path


CHROMA_DATA_PATH = get_chroma_data_path()
CHROMA_COLLECTION_NAME = "devops_codebase_index_v2"  # Changed name to reflect new library
EMBEDDING_MODEL_NAME = "models/text-embedding-004"

# --- Google AI Client ---
try:
    api_key = GOOGLE_API_KEY
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set.")
        raise ValueError("GOOGLE_API_KEY not found in environment.")
    # Instantiate the client
    genai_client = google_genai_sdk.Client(api_key=api_key)
    logger.info("Google GenAI client instantiated.")
except ValueError as ve:
    logger.error(ve)
    genai_client = None  # Set client to None if API key is missing
except Exception as e:
    logger.error(f"Failed to instantiate Google GenAI client: {e}")
    genai_client = None  # Set client to None on other errors


# --- ChromaDB Client and Collection ---
def create_chroma_client():
    """Create a ChromaDB client with robust error handling and fallbacks."""
    global CHROMA_DATA_PATH

    try:
        client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        # Test if we can create a collection to verify it's working
        client.get_or_create_collection(name="test_write_access")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize writable ChromaDB client at {CHROMA_DATA_PATH}: {e}")

        # If the database exists but is read-only, try to create a fresh database in a new location
        logger.warning("Attempting to create a fresh database in an alternate location...")

        # Pick a new temp directory path
        new_path = Path.joinpath(
            Path(tempfile.gettempdir()), f"devops_agent_chroma_new_{os.getpid()}"
        )
        new_path.mkdir(parents=True, exist_ok=True)

        try:
            # Update the global path
            CHROMA_DATA_PATH = new_path
            logger.info(f"Using new ChromaDB data path: {CHROMA_DATA_PATH}")
            return chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        except Exception as e2:
            logger.error(f"Failed to create alternative ChromaDB client: {e2}")

            # Last resort: try in-memory client
            logger.warning("Falling back to in-memory ChromaDB client. Data will not persist!")
            try:
                return chromadb.Client()
            except Exception as e3:
                logger.error(f"Failed to create in-memory ChromaDB client: {e3}")
                return None


chroma_client = create_chroma_client()


def get_chroma_collection():
    if not chroma_client:
        logger.error("ChromaDB client not initialized. Cannot get collection.")
        return None
    try:
        collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        logger.info(f"Successfully got or created ChromaDB collection: {CHROMA_COLLECTION_NAME}")
        return collection
    except Exception as e:
        logger.error(f"Failed to get or create ChromaDB collection '{CHROMA_COLLECTION_NAME}': {e}")
        return None


def embed_chunks_batch(
    chunks_content: list[str], task_type="RETRIEVAL_DOCUMENT", max_retries=3
) -> list[list[float]] | None:
    if not chunks_content:
        logger.warning("No content provided to embed_chunks_batch.")
        return []

    # Ensure the GenAI client is available
    if not genai_client:
        logger.error("Google GenAI client not initialized. Cannot generate embeddings.")
        return None

    embeddings_list = []

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Requesting embeddings for {len(chunks_content)} chunks using "
                f"{EMBEDDING_MODEL_NAME}..."
            )
            # Use the client instance to call embed_content
            result = genai_client.models.embed_content(
                model=EMBEDDING_MODEL_NAME,
                contents=chunks_content,
                config=google_genai_sdk.types.EmbedContentConfig(task_type=task_type),
            )
            raw_embeddings = result.embeddings
            if raw_embeddings:
                embeddings_list = [embedding.values for embedding in raw_embeddings]
            else:
                embeddings_list = []
            logger.info(f"Successfully generated {len(embeddings_list)} embeddings.")
            return embeddings_list

        except google_exceptions.GoogleAPIError as e:
            error_str = str(e)

            # Check if this is a rate limit error
            if (
                ("429" in error_str and "RESOURCE_EXHAUSTED" in error_str)
                or ("quota" in error_str.lower())
                or ("rate limit" in error_str.lower())
            ):
                if attempt < max_retries:
                    # Calculate exponential backoff delay (60s, 120s, 240s)
                    delay = 60 * (2**attempt)
                    logger.warning(
                        f"Rate limit hit during embedding (attempt {attempt + 1}/"
                        f"{max_retries + 1}). "
                        f"Waiting {delay} seconds before retry..."
                    )
                    time.sleep(delay)
                    continue
                logger.error(
                    f"Rate limit exceeded after {max_retries + 1} attempts during embedding. "
                    f"Skipping this batch of {len(chunks_content)} chunks."
                )
                return None
            logger.error(f"Google API error during embedding: {e}")
            return None

        except AttributeError:
            logger.error(
                "Attribute error during embedding (check SDK setup or API changes for "
                "embed_content): {ae}"
            )
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during embedding: {e}")
            return None

    return None


def index_file_chunks(collection, file_chunks_data: list[dict]):
    if not collection:
        logger.error("ChromaDB collection not available. Cannot index chunks.")
        return False
    if not file_chunks_data:
        logger.info("No chunks provided to index.")
        return True

    contents_to_embed = [chunk["content"] for chunk in file_chunks_data]

    # Check if file_chunks_data is not empty before accessing its first element
    file_path_logging = file_chunks_data[0]["file_path"] if file_chunks_data else "unknown file"
    logger.info(
        f"Generating embeddings for {len(contents_to_embed)} chunks from {file_path_logging}..."
    )
    embeddings = embed_chunks_batch(contents_to_embed, task_type="RETRIEVAL_DOCUMENT")

    if embeddings is None or len(embeddings) != len(file_chunks_data):
        logger.error(
            f"Failed to generate embeddings or mismatch in count for {file_path_logging}. "
            "Aborting indexing for this file."
        )
        return False

    ids = []
    metadatas = []
    documents = []

    for _i, chunk_data in enumerate(file_chunks_data):
        chunk_id = f"{chunk_data['file_path']}_{chunk_data['type']}_{chunk_data['name']}_{chunk_data['start_line']}-{chunk_data['end_line']}"  # noqa: E501
        ids.append(chunk_id)

        metadata = {
            "file_path": str(chunk_data["file_path"]),
            "chunk_name": str(chunk_data["name"]),
            "type": str(chunk_data["type"]),
            "start_line": int(chunk_data["start_line"]),
            "end_line": int(chunk_data["end_line"]),
        }
        metadatas.append(metadata)
        documents.append(chunk_data["content"])

    try:
        logger.info(f"Adding {len(ids)} documents to ChromaDB collection '{collection.name}'...")
        collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        logger.info(
            f"Successfully added {len(ids)} documents to collection for file {file_path_logging}."
        )
        return True
    except Exception as e:
        logger.error(f"Failed to add documents to ChromaDB for {file_path_logging}: {e}")

        # Special case for readonly database error
        if "readonly database" in str(e).lower():
            logger.warning(
                "Detected readonly database issue. Attempting to recreate the client in a "
                "writable location..."
            )
            global chroma_client, CHROMA_DATA_PATH

            # Try to force recreation of the client in a new location
            new_path = Path.joinpath(
                Path(tempfile.gettempdir()), f"devops_agent_chroma_retry_{os.getpid()}"
            )
            new_path.mkdir(parents=True, exist_ok=True)
            CHROMA_DATA_PATH = new_path

            try:
                logger.info(f"Creating new ChromaDB client at {CHROMA_DATA_PATH}")
                chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
                new_collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

                # Try indexing again with the new collection
                return index_file_chunks(new_collection, file_chunks_data)
            except Exception as e2:
                logger.error(f"Failed to recover from readonly database error: {e2}")

        return False


def clear_index():
    """Clear the entire index to start fresh."""
    collection = get_chroma_collection()
    if not collection:
        logger.error("Cannot clear index: ChromaDB collection not available.")
        return False

    try:
        collection.delete(where={})  # Delete all documents
        logger.info(f"Successfully cleared all documents from collection {collection.name}.")
        return True
    except Exception as e:
        logger.error(f"Failed to clear index: {e}")

        # Special handling for readonly database errors
        if "readonly database" in str(e).lower():
            global chroma_client, CHROMA_DATA_PATH
            logger.warning(
                "Detected readonly database issue during clear operation. Recreating client..."
            )

            # Create a completely new database
            new_path = Path.joinpath(
                Path(tempfile.gettempdir()), f"devops_agent_chroma_new_{os.getpid()}"
            )
            new_path.mkdir(parents=True, exist_ok=True)
            CHROMA_DATA_PATH = new_path

            try:
                chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
                # Getting a new collection in a new DB means it will be empty
                get_chroma_collection()
                logger.info(f"Successfully created new empty database at {CHROMA_DATA_PATH}")
                return True
            except Exception as e2:
                logger.error(f"Failed to create new database during clear operation: {e2}")

        return False


def get_index_stats():
    """Get statistics about the current index."""
    collection = get_chroma_collection()
    if not collection:
        return {"status": "error", "message": "ChromaDB collection not available."}

    try:
        count = collection.count()
        return {
            "status": "success",
            "count": count,
            "collection_name": CHROMA_COLLECTION_NAME,
            "data_path": CHROMA_DATA_PATH,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "data_path": CHROMA_DATA_PATH}


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    if not GOOGLE_API_KEY:
        logger.error("Please set the GOOGLE_API_KEY environment variable to run this example.")
    else:
        # Print out the data path being used
        logger.info(f"ChromaDB data path: {CHROMA_DATA_PATH}")

        collection = get_chroma_collection()
        if collection:
            logger.info(f"Using collection: {collection.name} with {collection.count()} items.")
            # Try to clear the index for demonstration purposes
            logger.info("Testing index operations...")

            # Test clearing
            clear_result = clear_index()
            logger.info(f"Clear index test result: {clear_result}")

            # Test adding sample data
            sample_chunks_data = [
                {
                    "file_path": "example.py",
                    "name": "MyClass",
                    "type": "class",
                    "content": "class MyClass:\n    def __init__(self):\n        pass",
                    "start_line": 1,
                    "end_line": 3,
                },
                {
                    "file_path": "example.py",
                    "name": "my_function",
                    "type": "function",
                    "content": "def my_function(a, b):\n    return a + b",
                    "start_line": 5,
                    "end_line": 6,
                },
            ]
            success = index_file_chunks(collection, sample_chunks_data)
            if success:
                logger.info("Sample chunks indexed successfully.")
                stats = get_index_stats()
                logger.info(f"Index stats: {stats}")
            else:
                logger.error("Failed to index sample chunks.")
        else:
            logger.error("Failed to get a working ChromaDB collection.")
