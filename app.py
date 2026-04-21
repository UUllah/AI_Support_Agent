import os
import logging
import asyncio
from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import json
import aiofiles
from pathlib import Path
from contextlib import asynccontextmanager

from loader import loader
from db import db_manager
from llm import llm_manager
from hackathon_engine import build_solution, generate_ideas
from analytics_service import analytics_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class HackathonIdeaRequest(BaseModel):
    problem_statement: str

class HackathonRoadmapRequest(BaseModel):
    problem_statement: str
    selected_idea_id: str
    mode: str
    ideas: List[Dict[str, Any]]


def get_ticket_metadata() -> List[Dict[str, Any]]:
    if loader.metadata:
        return loader.metadata
    if loader.load_index():
        return loader.metadata
    raise RuntimeError("Ticket metadata is not available. Build or load the ticket index first.")

# Schema storage
SCHEMA_DIR = Path("schemas")
SCHEMA_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    app.state.capabilities = {
        "database_ready": False,
        "ticket_search_ready": False,
        "hackathon_engine_ready": True,
    }

    # Startup
    try:
        logger.info("Testing database connection...")
        test_database_connection()
        app.state.capabilities["database_ready"] = True
    except Exception as e:
        logger.warning("Database is unavailable, continuing in degraded mode: %s", e)

    try:
        if loader.load_index():
            app.state.capabilities["ticket_search_ready"] = True
            logger.info("Existing ticket index loaded")
        elif app.state.capabilities["database_ready"]:
            logger.info("No existing index found. Building new index...")
            tickets = loader.load_tickets()
            loader.build_index(tickets)
            loader.save_index()
            app.state.capabilities["ticket_search_ready"] = True
            logger.info("Ticket index built successfully")
        else:
            logger.warning("Skipping ticket index build because the database is unavailable")
        logger.info("System initialized successfully")
    except Exception as e:
        logger.warning("Ticket search is unavailable, continuing in degraded mode: %s", e)

    yield

    # Shutdown (if needed)
    logger.info("Application shutting down")

def test_database_connection():
    """Test database connection and throw error if unavailable."""
    try:
        # Use the same connection logic as loader
        import os
        import pyodbc

        db_config = {
            'server': '172.16.0.22',
            'database': 'jitbitHelpDesk',
            'username': 'ubaid',
            'password': 'Avanza@123',
            'driver': '{ODBC Driver 17 for SQL Server}'
        }

        conn_str = (
            f"DRIVER={db_config['driver']};"
            f"SERVER={db_config['server']};"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['username']};"
            f"PWD={db_config['password']};"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )

        # Test connection with a simple query
        with pyodbc.connect(conn_str, timeout=2) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            if result and result.test == 1:
                logger.info("Database connection test successful")
            else:
                raise Exception("Database test query failed")

    except pyodbc.Error as e:
        error_msg = f"Database connection failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(f"SQL Database unavailable: {str(e)}")
    except Exception as e:
        error_msg = f"Database connection test failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(f"SQL Database unavailable: {str(e)}")

app = FastAPI(
    title="AI Support Agent",
    description="Local AI-powered support system for banking tickets and database queries",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    capabilities = getattr(app.state, "capabilities", {})
    overall_status = "healthy" if capabilities.get("hackathon_engine_ready") else "degraded"
    return {
        "status": overall_status,
        "message": "AI Support Agent is running",
        "capabilities": capabilities,
    }

# Main UI
@app.get("/", response_class=HTMLResponse)
async def main_ui():
    """Serve the hackathon engine as the default landing page."""
    return FileResponse("static/hackathon-engine.html")


@app.get("/support-agent", response_class=HTMLResponse)
async def support_agent_ui():
    """Serve the main user interface."""
    return FileResponse("static/index.html")


@app.get("/hackathon-engine", response_class=HTMLResponse)
async def hackathon_engine_ui():
    """Serve the hackathon engine interface."""
    return FileResponse("static/hackathon-engine.html")

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
        if not getattr(app.state, "capabilities", {}).get("ticket_search_ready"):
            raise HTTPException(status_code=503, detail="Ticket search is not ready. Start the index or database services first.")
        results = loader.search(request.query, request.top_k)
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/analyze-tickets")
@app.post("/api/analyze-tickets")
async def analyze_tickets():
    """Analyze all loaded tickets and generate dashboard-ready intelligence."""
    try:
        summary = analytics_service.analyze_tickets(get_ticket_metadata())
        return summary
    except Exception as e:
        logger.error("Ticket analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ticket analysis failed: {str(e)}")


@app.get("/ticket-summary")
@app.get("/api/ticket-summary")
async def ticket_summary():
    """Return the latest ticket intelligence summary."""
    try:
        summary = analytics_service.get_ticket_summary()
        if summary is None:
            summary = analytics_service.analyze_tickets(get_ticket_metadata())
        return summary
    except Exception as e:
        logger.error("Failed to get ticket summary: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get ticket summary: {str(e)}")


@app.post("/upload-log")
@app.post("/api/upload-log")
async def upload_log(log_file: UploadFile = File(...)):
    """Upload and analyze access logs for API operations intelligence."""
    try:
        filename = log_file.filename or "uploaded.log"
        if not filename.lower().endswith((".log", ".txt")):
            raise HTTPException(status_code=400, detail="Only .log and .txt files are supported.")

        content = await log_file.read()
        summary = analytics_service.analyze_log_upload(filename, content)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Log upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Log upload failed: {str(e)}")


@app.get("/log-summary")
@app.get("/api/log-summary")
async def log_summary():
    """Return the latest parsed log dashboard summary."""
    summary = analytics_service.get_log_summary()
    if summary is None:
        raise HTTPException(status_code=404, detail="No log summary available. Upload a log file first.")
    return summary

def format_ticket_text(text: str) -> str:
    """Format ticket text for better readability."""
    import re
    import html

    # Decode HTML entities
    text = html.unescape(text)

    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # Clean up common patterns
    text = re.sub(r'Best Regards:?\s*', 'Best Regards: ', text, flags=re.IGNORECASE)
    text = re.sub(r'Dear\s+', 'Dear ', text, flags=re.IGNORECASE)
    text = re.sub(r'Hello\s+', 'Hello ', text, flags=re.IGNORECASE)

    # Remove excessive spaces
    text = re.sub(r' +', ' ', text)

    # Split into paragraphs and clean up
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    # Limit to reasonable length (first 500 characters of combined text)
    combined_text = '\n\n'.join(paragraphs)
    if len(combined_text) > 500:
        combined_text = combined_text[:497] + '...'

    return combined_text

def generate_ticket_summary(text: str) -> str:
    """Generate a brief summary of the ticket content."""
    import re
    import html

    # Clean the text first
    clean_text = html.unescape(text)
    clean_text = re.sub(r'\r\n', ' ', clean_text)
    clean_text = re.sub(r'\n+', ' ', clean_text)
    clean_text = re.sub(r' +', ' ', clean_text)

    # Extract key information
    sentences = re.split(r'[.!?]+', clean_text)[:3]  # First 3 sentences
    summary = '. '.join([s.strip() for s in sentences if s.strip()])

    # Limit summary length
    if len(summary) > 150:
        summary = summary[:147] + '...'

    return summary

# SQL AI Agent endpoint
@app.post("/api/sql-query")
async def sql_query(request: SQLQueryRequest):
    """Generate and execute SQL query from natural language."""
    try:
        if not getattr(app.state, "capabilities", {}).get("database_ready"):
            raise HTTPException(status_code=503, detail="Database connectivity is unavailable for SQL generation.")
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
        if not getattr(app.state, "capabilities", {}).get("database_ready"):
            raise HTTPException(status_code=503, detail="Database connectivity is unavailable.")
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
        if not getattr(app.state, "capabilities", {}).get("database_ready"):
            raise HTTPException(status_code=503, detail="Database connectivity is unavailable.")
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


def _ndjson_event(event_type: str, data: Any) -> bytes:
    return (json.dumps({"type": event_type, "data": data}) + "\n").encode("utf-8")


@app.post("/api/hackathon-engine/generate-stream")
async def generate_hackathon_ideas_stream(request: HackathonIdeaRequest):
    """Generate ranked hackathon ideas with streaming updates."""
    problem_statement = request.problem_statement.strip()
    if len(problem_statement) < 20:
        raise HTTPException(status_code=400, detail="Please provide a fuller problem statement so ideas can be ranked properly.")

    async def event_stream():
        yield _ndjson_event("status", {"message": "Understanding the banking problem"})
        await asyncio.sleep(0)
        yield _ndjson_event("status", {"message": "Generating practical solution ideas"})
        await asyncio.sleep(0)
        payload = generate_ideas(problem_statement)
        yield _ndjson_event("ideas", payload)
        yield _ndjson_event(
            "status",
            {"message": f"Recommended idea: {payload['recommended_idea_id']} based on business impact, adoption, and simplicity"},
        )
        yield _ndjson_event("done", {"step": "ideas"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/hackathon-engine/roadmap-stream")
async def generate_hackathon_roadmap_stream(request: HackathonRoadmapRequest):
    """Generate the selected roadmap package with streaming updates."""
    mode = request.mode.strip().lower()
    if mode not in {"roadmap", "basic_poc", "advanced"}:
        raise HTTPException(status_code=400, detail="Mode must be one of: roadmap, basic_poc, advanced")

    async def event_stream():
        yield _ndjson_event("status", {"message": "Locking the selected idea and approach"})
        await asyncio.sleep(0)
        yield _ndjson_event("status", {"message": "Building the real-world roadmap"})
        await asyncio.sleep(0)
        payload = build_solution(
            problem_statement=request.problem_statement,
            selected_idea_id=request.selected_idea_id,
            ideas=request.ideas,
            mode=mode,
        )
        yield _ndjson_event("roadmap", payload)
        yield _ndjson_event("done", {"step": "roadmap"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)