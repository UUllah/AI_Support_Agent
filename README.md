# AI Support Agent

This is a local AI-powered support agent built with FastAPI, FAISS, Sentence Transformers, and Ollama for semantic search on ticket data and natural language SQL queries.

## Features

- **Semantic Search**: Find relevant tickets using vector similarity search
- **SQL AI Agent**: Generate and execute SQL queries from natural language
- **RAG Summarization**: Summarize ticket solutions using local LLM
- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **Local Operation**: No external API dependencies (uses Ollama for LLM)

## Architecture

- `app.py`: FastAPI application with REST endpoints
- `loader.py`: Ticket data loading and FAISS index management
- `db.py`: SQL Server database operations and safety checks
- `llm.py`: Local LLM interactions via Ollama API

## Prerequisites

- Python 3.8+
- SQL Server with ODBC driver
- Ollama installed with Mistral model: `ollama pull mistral`

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/UUllah/AI_Support_Agent.git
   cd AI_Support_Agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. Start Ollama service (if not running):
   ```bash
   ollama serve
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /health`: Health check
- `POST /api/search-tickets`: Semantic search for tickets
- `POST /api/sql-query`: Natural language to SQL query generation
- `POST /api/summarize-tickets`: RAG-based ticket summarization
- `GET /api/tables`: List available database tables
- `GET /api/schema/{table_name}`: Get table schema

## Environment Variables

- `DB_SERVER`: SQL Server hostname
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `PORT`: Application port (default: 8000)
- `OLLAMA_BASE_URL`: Ollama API URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Ollama model name (default: mistral)

## Security Notes

- Only SELECT queries are allowed for safety
- All database credentials are stored in environment variables
- No hardcoded secrets in the codebase
- Local LLM ensures data privacy

## Development

The system automatically builds the FAISS index on first startup. Index and metadata are cached in the `data/` directory for faster subsequent loads.