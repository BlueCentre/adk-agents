# /Users/james/Agents/devops_v2/rag_components/retriever.py
import logging
import os

# Import agent configuration
from ...config import GOOGLE_API_KEY

# Attempt to import components from the sibling indexing module
# This allows sharing the initialized chroma_client and embedding_model_instance
# when used as part of the larger agent.
try:
    from .indexing import get_chroma_collection, embed_chunks_batch, CHROMA_COLLECTION_NAME
    logger = logging.getLogger(__name__)
    logger.info("Retriever: Successfully imported from .indexing")
except ImportError:
    # Fallback for standalone execution or if imports fail (e.g., during direct testing)
    # This will re-initialize, which is fine for testing but less efficient in production.
    # Ensure GOOGLE_API_KEY is set if running this way.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning("Retriever: Could not import from .indexing, attempting standalone initialization.")
    from indexing import get_chroma_collection, embed_chunks_batch, CHROMA_COLLECTION_NAME


def retrieve_relevant_chunks(query_text: str, top_k: int = 5, collection_name: str = CHROMA_COLLECTION_NAME) -> list[dict] | None:
    """
    Retrieves the top_k most relevant chunks for a given query from ChromaDB.

    Args:
        query_text: The user's query string.
        top_k: The number of most relevant chunks to retrieve.
        collection_name: The name of the ChromaDB collection to query.

    Returns:
        A list of dictionaries, where each dictionary contains the retrieved chunk's
        metadata and content ('document'), or None if an error occurs.
        Example: [{'id': str, 'metadata': dict, 'document': str, 'distance': float}, ...]
    """
    collection = get_chroma_collection() # Uses the shared or re-initialized client
    if not collection:
        logger.error(f"Failed to get ChromaDB collection '{collection_name}' for retrieval.")
        return None

    if not query_text:
        logger.warning("Empty query text provided for retrieval.")
        return []

    logger.info(f"Generating embedding for query: \"{query_text}\"")
    # Embed the query using the same model, but with RETRIEVAL_QUERY task type
    query_embedding_list = embed_chunks_batch([query_text], task_type="RETRIEVAL_QUERY")

    if not query_embedding_list or not query_embedding_list[0]:
        logger.error("Failed to generate embedding for the query.")
        return None
    
    query_embedding = query_embedding_list[0] # embed_chunks_batch returns a list of embeddings

    try:
        logger.info(f"Querying collection '{collection.name}' for top {top_k} relevant chunks.")
        results = collection.query(
            query_embeddings=[query_embedding], # Must be a list of embeddings
            n_results=top_k,
            include=['metadatas', 'documents', 'distances'] # Specify what to include in results
        )
        
        retrieved_chunks = []
        # ChromaDB query results are structured with lists for each included field,
        # corresponding to each query embedding (we only have one here).
        if results and results['ids'] and results['ids'][0]: # Check if results['ids'][0] is not empty
            for i in range(len(results['ids'][0])):
                chunk_info = {
                    "id": results['ids'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else None,
                    "document": results['documents'][0][i] if results['documents'] and results['documents'][0] else None,
                    "distance": results['distances'][0][i] if results['distances'] and results['distances'][0] else None,
                }
                retrieved_chunks.append(chunk_info)
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks.")
        else:
            logger.info("No relevant chunks found for the query.")
            
        return retrieved_chunks

    except Exception as e:
        logger.error(f"An error occurred during ChromaDB query: {e}")
        return None

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    # Note: logging is configured in the import fallback if this is run standalone.
    # If run via an agent that already configures logging, this basicConfig might not run or might conflict.
    if "indexing" not in globals(): # A proxy to see if we are in fallback mode
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


    # This requires GOOGLE_API_KEY to be set in the environment if .indexing is not found
    if not GOOGLE_API_KEY and "indexing" not in globals():
         logger.error("Please set the GOOGLE_API_KEY environment variable to run this example if .indexing is not found.")
    else:
        logger.info("Attempting to retrieve chunks. Make sure you have indexed some data first (e.g., by running indexing.py example).")
        
        sample_query = "How does MyClass work?"
        retrieved = retrieve_relevant_chunks(sample_query, top_k=3)

        if retrieved is not None:
            if retrieved:
                print(f"\n--- Top {len(retrieved)} relevant chunks for query: \"{sample_query}\" ---")
                for i, chunk_dict in enumerate(retrieved):
                    print(f"\nChunk {i+1} (ID: {chunk_dict['id']}, Distance: {chunk_dict['distance']:.4f}):")
                    print("Metadata:", chunk_dict['metadata'])
                    print("Content:\n", chunk_dict['document'])
            else:
                print(f"No chunks found for query: \"{sample_query}\"")
        else:
            print("Failed to retrieve chunks.")

        another_query = "tell me about helpers"
        retrieved_again = retrieve_relevant_chunks(another_query, top_k=2)
        if retrieved_again is not None:
            if retrieved_again:
                print(f"\n--- Top {len(retrieved_again)} relevant chunks for query: \"{another_query}\" ---")
                for i, chunk_dict in enumerate(retrieved_again):
                    print(f"\nChunk {i+1} (ID: {chunk_dict['id']}, Distance: {chunk_dict['distance']:.4f}):")
                    print("Metadata:", chunk_dict['metadata'])
                    print("Content:\n", chunk_dict['document'])
            else:
                print(f"No chunks found for query: \"{another_query}\"")
