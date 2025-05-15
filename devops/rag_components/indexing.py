# /Users/james/Agents/devops_v2/rag_components/indexing.py
import os
import logging
import chromadb
from google import genai as google_genai_sdk # Renamed to avoid conflict with a potential genai client instance
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv # Added import

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv() # Added call

# --- Configuration ---
CHROMA_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "chroma_data"))
CHROMA_COLLECTION_NAME = "devops_codebase_index_v2" # Changed name to reflect new library
EMBEDDING_MODEL_NAME = "models/text-embedding-004"

# --- Google AI Client ---
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set.")
        raise ValueError("GOOGLE_API_KEY not found in environment.")
    # Instantiate the client
    genai_client = google_genai_sdk.Client(api_key=api_key)
    logger.info("Google GenAI client instantiated.")
except ValueError as ve:
    logger.error(ve)
    genai_client = None # Set client to None if API key is missing
except Exception as e:
    logger.error(f"Failed to instantiate Google GenAI client: {e}")
    genai_client = None # Set client to None on other errors


# --- ChromaDB Client and Collection ---
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB client at {CHROMA_DATA_PATH}: {e}")
    chroma_client = None

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

def embed_chunks_batch(chunks_content: list[str], task_type="RETRIEVAL_DOCUMENT") -> list[list[float]] | None:
    if not chunks_content:
        logger.warning("No content provided to embed_chunks_batch.")
        return []

    # Ensure the GenAI client is available
    if not genai_client:
        logger.error("Google GenAI client not initialized. Cannot generate embeddings.")
        return None

    embeddings_list = []
    try:
        logger.info(f"Requesting embeddings for {len(chunks_content)} chunks using {EMBEDDING_MODEL_NAME}...")
        # Use the client instance to call embed_content
        result = genai_client.models.embed_content(
            model=EMBEDDING_MODEL_NAME, 
            contents=chunks_content, 
            config=google_genai_sdk.types.EmbedContentConfig(task_type=task_type)
        )
        raw_embeddings = result.embeddings
        if raw_embeddings:
            embeddings_list = [embedding.values for embedding in raw_embeddings]
        else:
            embeddings_list = []
        logger.info(f"Successfully generated {len(embeddings_list)} embeddings.")
        return embeddings_list
    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Google API error during embedding: {e}")
    except AttributeError as ae:
        logger.error(f"Attribute error during embedding (check SDK setup or API changes for embed_content): {ae}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during embedding: {e}")
    return None

def index_file_chunks(collection, file_chunks_data: list[dict]):
    if not collection:
        logger.error("ChromaDB collection not available. Cannot index chunks.")
        return False
    if not file_chunks_data:
        logger.info("No chunks provided to index.")
        return True

    contents_to_embed = [chunk['content'] for chunk in file_chunks_data]
    
    # Check if file_chunks_data is not empty before accessing its first element
    file_path_logging = file_chunks_data[0]['file_path'] if file_chunks_data else "unknown file"
    logger.info(f"Generating embeddings for {len(contents_to_embed)} chunks from {file_path_logging}...")
    embeddings = embed_chunks_batch(contents_to_embed, task_type="RETRIEVAL_DOCUMENT")

    if embeddings is None or len(embeddings) != len(file_chunks_data):
        logger.error(f"Failed to generate embeddings or mismatch in count for {file_path_logging}. Aborting indexing for this file.")
        return False

    ids = []
    metadatas = []
    documents = []

    for i, chunk_data in enumerate(file_chunks_data):
        chunk_id = f"{chunk_data['file_path']}_{chunk_data['type']}_{chunk_data['name']}_{chunk_data['start_line']}-{chunk_data['end_line']}"
        ids.append(chunk_id)
        
        metadata = {
            "file_path": str(chunk_data['file_path']),
            "chunk_name": str(chunk_data['name']),
            "type": str(chunk_data['type']),
            "start_line": int(chunk_data['start_line']),
            "end_line": int(chunk_data['end_line'])
        }
        metadatas.append(metadata)
        documents.append(chunk_data['content'])

    try:
        logger.info(f"Adding {len(ids)} documents to ChromaDB collection '{collection.name}'...")
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        logger.info(f"Successfully added {len(ids)} documents to collection for file {file_path_logging}.")
        return True
    except Exception as e:
        logger.error(f"Failed to add documents to ChromaDB for {file_path_logging}: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("Please set the GOOGLE_API_KEY environment variable to run this example.")
    else:
        collection = get_chroma_collection()
        if collection:
            logger.info(f"Using collection: {collection.name} with {collection.count()} items.")
            sample_chunks_data = [
                {'file_path': 'example.py', 'name': 'MyClass', 'type': 'class', 'content': 'class MyClass:\n    def __init__(self):\n        pass', 'start_line': 1, 'end_line': 3},
                {'file_path': 'example.py', 'name': 'my_function', 'type': 'function', 'content': 'def my_function(a, b):\n    return a + b', 'start_line': 5, 'end_line': 6}
            ]
            success = index_file_chunks(collection, sample_chunks_data)
            if success:
                logger.info("Sample chunks indexed successfully.")
                logger.info(f"Collection now has {collection.count()} items.")
            else:
                logger.error("Failed to index sample chunks.")
