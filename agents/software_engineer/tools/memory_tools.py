"""Memory tools for the Software Engineer Agent."""

import logging
from typing import Any, Dict, List, Optional

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Simple in-memory storage for the session
_memory_store: Dict[str, Any] = {}


class AddMemoryFactInput(BaseModel):
    """Input model for adding memory facts."""
    
    key: str = Field(..., description="A unique identifier for this memory")
    value: str = Field(..., description="The information to store")
    category: str = Field(default="general", description="Category to organize memories")


class AddMemoryFactOutput(BaseModel):
    """Output model for adding memory facts."""
    
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human readable message")
    key: str = Field(..., description="The key that was used")
    category: str = Field(..., description="The category used")


def add_memory_fact_func(args: dict, tool_context: ToolContext) -> AddMemoryFactOutput:
    """
    Add a fact to memory for later retrieval.
    """
    key = args.get("key")
    value = args.get("value") 
    category = args.get("category", "general")
    
    try:
        if category not in _memory_store:
            _memory_store[category] = {}
            
        _memory_store[category][key] = value
        
        logger.info(f"Added memory fact: {key} in category {category}")
        
        return AddMemoryFactOutput(
            status="success",
            message=f"Memory fact '{key}' added to category '{category}'",
            key=key,
            category=category
        )
        
    except Exception as e:
        error_msg = f"Error adding memory fact: {str(e)}"
        logger.error(error_msg)
        return AddMemoryFactOutput(
            status="error",
            message=error_msg,
            key=key,
            category=category
        )


class SearchMemoryFactsInput(BaseModel):
    """Input model for searching memory facts."""
    
    query: Optional[str] = Field(None, description="Optional text to search for in memory values")
    category: Optional[str] = Field(None, description="Optional category to filter by")


class SearchMemoryFactsOutput(BaseModel):
    """Output model for searching memory facts."""
    
    status: str = Field(..., description="Status of the operation")
    query: Optional[str] = Field(None, description="The search query used")
    category: Optional[str] = Field(None, description="The category filter used")
    results: Dict[str, Any] = Field(..., description="The search results")
    total_categories: int = Field(..., description="Number of categories with results")


def search_memory_facts_func(args: dict, tool_context: ToolContext) -> SearchMemoryFactsOutput:
    """
    Search for facts in memory.
    """
    query = args.get("query")
    category = args.get("category")
    
    try:
        results = {}
        
        # If no category specified, search all categories
        categories_to_search = [category] if category else list(_memory_store.keys())
        
        for cat in categories_to_search:
            if cat not in _memory_store:
                continue
                
            category_results = {}
            
            for key, value in _memory_store[cat].items():
                # If no query, return all facts in category
                if not query:
                    category_results[key] = value
                # If query specified, search in key and value
                elif query.lower() in key.lower() or query.lower() in str(value).lower():
                    category_results[key] = value
                    
            if category_results:
                results[cat] = category_results
        
        logger.info(f"Memory search completed. Query: '{query}', Category: '{category}', Results: {len(results)} categories")
        
        return SearchMemoryFactsOutput(
            status="success",
            query=query,
            category=category,
            results=results,
            total_categories=len(results)
        )
        
    except Exception as e:
        error_msg = f"Error searching memory: {str(e)}"
        logger.error(error_msg)
        return SearchMemoryFactsOutput(
            status="error",
            query=query,
            category=category,
            results={},
            total_categories=0
        )


# Create the tools using FunctionTool wrapper
add_memory_fact = FunctionTool(add_memory_fact_func)
search_memory_facts = FunctionTool(search_memory_facts_func)
