import os
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

from loader import loader
from db import db_manager
from llm import llm_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Support Agent",
    description="Local AI-powered support system for banking tickets and database queries",
    version="1.0.0"
)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SQLQueryRequest(BaseModel):
    natural_language_query: str
    table_name: Optional[str] = None

class SummarizeRequest(BaseModel):
    query: str
    ticket_ids: List[str]

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup."""
    try:
        # Try to load existing index
        if not loader.load_index():
            # If no index exists, build it
            logger.info("No existing index found. Building new index...")
            tickets = loader.load_tickets()
            loader.build_index(tickets)
            loader.save_index()
        logger.info("System initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "AI Support Agent is running"}

# Ticket search endpoint
@app.post("/api/search-tickets")
async def search_tickets(request: SearchRequest):
    """Search for relevant tickets using semantic search."""
    try:
        results = loader.search(request.query, request.top_k)
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# SQL AI Agent endpoint
@app.post("/api/sql-query")
async def sql_query(request: SQLQueryRequest):
    """Generate and execute SQL query from natural language."""
    try:
        # Get schema info if table specified
        schema_info = None
        if request.table_name:
            schema_info = db_manager.get_table_schema(request.table_name)
        else:
            # Get all tables if no specific table
            tables = db_manager.get_available_tables()
            schema_info = {"available_tables": tables}

        # Generate SQL query
        sql_query = llm_manager.generate_sql_query(request.natural_language_query, schema_info)

        # Execute the query
        results = db_manager.execute_select_query(sql_query)

        return {
            "natural_language_query": request.natural_language_query,
            "generated_sql": sql_query,
            "results": results,
            "row_count": len(results)
        }
    except Exception as e:
        logger.error(f"SQL query failed: {e}")
        raise HTTPException(status_code=500, detail=f"SQL query failed: {str(e)}")

# RAG Summarization endpoint
@app.post("/api/summarize-tickets")
async def summarize_tickets(request: SummarizeRequest):
    """Summarize relevant tickets for the user's query."""
    try:
        # Get ticket details (simplified - in real implementation, fetch from DB)
        # For now, assume we have the ticket texts from search results
        # In production, you'd fetch full ticket details from database
        tickets = [
            {"ticket_id": tid, "text": f"Ticket {tid} content"}  # Placeholder
            for tid in request.ticket_ids
        ]

        summary = llm_manager.summarize_tickets(tickets, request.query)

        return {
            "query": request.query,
            "ticket_ids": request.ticket_ids,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

# Get available tables
@app.get("/api/tables")
async def get_tables():
    """Get list of available database tables."""
    try:
        tables = db_manager.get_available_tables()
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")

# Get table schema
@app.get("/api/schema/{table_name}")
async def get_schema(table_name: str):
    """Get schema for a specific table."""
    try:
        schema = db_manager.get_table_schema(table_name)
        return schema
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)