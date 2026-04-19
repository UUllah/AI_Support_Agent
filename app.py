import os
import logging
from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import json
import aiofiles
from pathlib import Path

from loader import loader
from db import db_manager
from llm import llm_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Support Agent",
    description="Local AI-powered support system for banking tickets and database queries",
    version="2.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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

class SchemaUpload(BaseModel):
    name: str
    category: str
    schema_data: str

# Schema storage
SCHEMA_DIR = Path("schemas")
SCHEMA_DIR.mkdir(exist_ok=True)

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

# Main UI
@app.get("/", response_class=HTMLResponse)
async def main_ui():
    """Serve the main user interface."""
    return FileResponse("static/index.html")

# Admin UI
@app.get("/admin", response_class=HTMLResponse)
async def admin_ui():
    """Serve the admin interface."""
    return FileResponse("static/admin.html")

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

# Schema Management Endpoints
@app.post("/api/schemas/upload")
async def upload_schema(
    name: str = Form(...),
    category: str = Form(...),
    schema_file: UploadFile = File(...)
):
    """Upload a schema file for a specific category."""
    try:
        # Read file content
        content = await schema_file.read()
        schema_data = content.decode('utf-8')

        # Validate JSON if it's JSON format
        try:
            json.loads(schema_data)
            file_extension = ".json"
        except json.JSONDecodeError:
            file_extension = ".txt"

        # Save schema file
        filename = f"{category}_{name}{file_extension}"
        schema_path = SCHEMA_DIR / filename

        async with aiofiles.open(schema_path, 'w') as f:
            await f.write(schema_data)

        return {
            "message": "Schema uploaded successfully",
            "filename": filename,
            "category": category,
            "name": name
        }
    except Exception as e:
        logger.error(f"Schema upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/schemas")
async def list_schemas():
    """List all uploaded schemas."""
    try:
        schemas = []
        for schema_file in SCHEMA_DIR.glob("*"):
            if schema_file.is_file():
                # Parse filename: category_name.extension
                filename = schema_file.name
                parts = filename.rsplit('.', 1)
                name_part = parts[0]
                extension = parts[1] if len(parts) > 1 else ""

                # Split category and name
                if '_' in name_part:
                    category, name = name_part.split('_', 1)
                else:
                    category = "general"
                    name = name_part

                schemas.append({
                    "name": name,
                    "category": category,
                    "filename": filename,
                    "extension": extension
                })

        return {"schemas": schemas}
    except Exception as e:
        logger.error(f"Failed to list schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list schemas: {str(e)}")

@app.get("/api/schemas/{category}/{name}")
async def get_schema_content(category: str, name: str):
    """Get the content of a specific schema."""
    try:
        filename = f"{category}_{name}"
        # Try both .json and .txt extensions
        for ext in ['.json', '.txt']:
            schema_path = SCHEMA_DIR / f"{filename}{ext}"
            if schema_path.exists():
                async with aiofiles.open(schema_path, 'r') as f:
                    content = await f.read()
                return {
                    "name": name,
                    "category": category,
                    "filename": f"{filename}{ext}",
                    "content": content
                }

        raise HTTPException(status_code=404, detail="Schema not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")

@app.delete("/api/schemas/{category}/{name}")
async def delete_schema(category: str, name: str):
    """Delete a specific schema."""
    try:
        filename = f"{category}_{name}"
        deleted = False

        # Try both .json and .txt extensions
        for ext in ['.json', '.txt']:
            schema_path = SCHEMA_DIR / f"{filename}{ext}"
            if schema_path.exists():
                schema_path.unlink()
                deleted = True

        if not deleted:
            raise HTTPException(status_code=404, detail="Schema not found")

        return {"message": f"Schema {category}/{name} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schema: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)