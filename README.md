# AI Support Agent

This is an AI-powered support agent built with FastAPI, OpenAI, and FAISS for semantic search on ticket conversations.

## Features

- Load and process ticket conversations from Jitbit or similar systems
- Semantic search using Sentence Transformers and FAISS
- Summarize relevant tickets using OpenAI GPT models
- Web interface for user interaction

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

3. Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. Run the application:
   ```bash
   python app_final.py
   ```

5. Open your browser to `http://localhost:8000` or the chat.html file.

## Files

- `app_final.py`: Main FastAPI application
- `knowledge_loader.py`: Loads ticket data
- `vector_store.py`: Handles FAISS indexing
- `embeddings.py`: Sentence embedding utilities
- `chat.html`: Simple web interface
- `requirements.txt`: Python dependencies

## Note

Ensure your OpenAI API key is set securely and not committed to the repository.