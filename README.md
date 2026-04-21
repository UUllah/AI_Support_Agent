# AI Support Agent

This is a local AI-powered support agent built with FastAPI, FAISS, Sentence Transformers, and Ollama for semantic search on ticket data and natural language SQL queries.

## Features

- **Hackathon Engine**: Generate ranked banking solution ideas in real time, then build roadmap, demo, PPT, and video-script output
- **Semantic Ticket Search**: Find relevant tickets using vector similarity search
- **SQL AI Agent**: Generate and execute SQL queries from natural language
- **RAG Summarization**: Generate context-aware ticket solutions using local LLM
- **User-Friendly Web UI**: Clean interface with tabbed API selection
- **Admin Panel**: Upload and manage database schemas for different categories
- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **Local Operation**: No external API dependencies (uses Ollama for LLM)
- **Production Ready**: Comprehensive error handling, logging, and security

## Architecture

- `app.py`: FastAPI application with REST endpoints and web UI serving
- `loader.py`: Ticket data loading and FAISS index management
- `db.py`: SQL Server database operations and safety checks
- `llm.py`: Local LLM interactions via Ollama API
- `static/`: Web interface files (HTML, CSS, JavaScript)

## Prerequisites

- Python 3.8+
- SQL Server with ODBC driver
- Ollama installed with Mistral model: `ollama pull mistral`
- Modern web browser

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

6. Open your browser and navigate to `http://localhost:8000`

The default landing page is now the Hackathon Engine. The legacy support agent UI is available at `http://localhost:8000/support-agent`.

## Web Interface

### User Interface (`/support-agent`)
- **Ticket Search Tab**: Semantic search through support tickets
- **SQL Query Agent Tab**: Convert natural language to SQL queries
- **Support Chat Tab**: Get AI-powered answers based on ticket history
- Real-time loading indicators and error handling
- JSON-formatted responses for easy reading

### Hackathon Engine (`/` and `/hackathon-engine`)
- **Problem Intake**: Capture a banking pain point, current process, systems, and success metric
- **Real-Time Idea Ranking**: Stream 3-5 practical ideas ranked by business impact, adoption, and simplicity
- **Roadmap Generator**: Build rollout phases, quantified impact, demo flow, PPT content, and a 3-minute video script
- **Mode Selection**: Switch between roadmap-focused, basic POC, and advanced production vision outputs
- **Session Persistence**: Restore the latest problem, selected idea, chosen mode, and generated roadmap from browser storage
- **Export Actions**: Download the generated package as JSON or Markdown for easy handoff into PPT or notes

### Admin Panel (`/admin`)
- **Schema Upload**: Upload database schema files (JSON/TXT) for different categories
- **Schema Library**: View, manage, and delete uploaded schemas
- **Schema Viewer**: Inspect schema contents before use
- Categories: Transaction_Log, Tickets, Customer_Data, Account_Data, Other

## API Endpoints

### Core APIs
- `POST /api/search-tickets`: Semantic search for tickets
- `POST /api/sql-query`: Natural language to SQL query generation
- `POST /api/summarize-tickets`: RAG-based ticket summarization
- `GET /api/tables`: List available database tables
- `GET /api/schema/{table_name}`: Get table schema

### Schema Management APIs
- `POST /api/schemas/upload`: Upload schema file
- `GET /api/schemas`: List all uploaded schemas
- `GET /api/schemas/{category}/{name}`: Get schema content
- `DELETE /api/schemas/{category}/{name}`: Delete schema

### Web Interface
- `GET /`: Hackathon engine landing page
- `GET /hackathon-engine`: Hackathon engine landing page alias
- `GET /support-agent`: Legacy support agent UI
- `GET /admin`: Admin panel
- `GET /static/*`: Static files (CSS, JS)

## Environment Variables

- `DB_SERVER`: SQL Server hostname
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `PORT`: Application port (default: 8000)
- `OLLAMA_BASE_URL`: Ollama API URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Ollama model name (default: mistral)

## Schema Management

The admin panel allows you to upload and manage database schemas that enhance the LLM's ability to generate accurate SQL queries. Schemas are stored locally in the `schemas/` directory.

### Supported Schema Categories:
- **Transaction_Log**: Transaction table schemas
- **Tickets**: Support ticket table schemas
- **Customer_Data**: Customer information schemas
- **Account_Data**: Account-related schemas
- **Other**: Custom schemas

### Schema File Format:
- **JSON**: Structured schema definitions
- **TXT**: Plain text schema descriptions

## Security Notes

- Only SELECT queries are allowed for safety
- All database credentials are stored in environment variables
- No hardcoded secrets in the codebase
- Local LLM ensures data privacy
- Schema files are stored locally (not in database)

## Development

The system automatically builds the FAISS index on first startup. Index and metadata are cached in the `data/` directory for faster subsequent loads.

### Adding New API Functions:
1. Add endpoint to `app.py`
2. Create corresponding UI tab in `index.html`
3. Add JavaScript handler in `app.js`
4. Update CSS styling as needed

### Schema Integration:
Schemas uploaded via the admin panel can be used by the LLM to improve SQL query generation accuracy. The system automatically loads available schemas when processing SQL queries.

## Troubleshooting

- **UI not loading**: Ensure all static files are in the `static/` directory
- **API errors**: Check Ollama is running and accessible
- **Database connection**: Verify environment variables and SQL Server connectivity
- **Schema upload fails**: Check file format (JSON/TXT) and category selection