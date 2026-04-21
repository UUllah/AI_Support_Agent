import os
import logging
import requests
import json
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMManager:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

    def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate a response using the local LLM."""
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\n\nQuestion: {prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get('response', '').strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def generate_sql_query(self, natural_language_query: str, schema_info: Dict[str, Any]) -> str:
        """Generate a SQL query from natural language using the LLM."""
        schema_str = json.dumps(schema_info, indent=2)

        prompt = f"""
You are a SQL expert. Generate a SELECT query based on the user's natural language request.
Only generate SELECT queries. Do not generate INSERT, UPDATE, DELETE, or any other modifying queries.

Database Schema:
{schema_str}

User Request: {natural_language_query}

Generate only the SQL query, no explanations. Make sure it's safe and correct.
"""

        try:
            sql_query = self.generate_response(prompt)
            # Basic validation - ensure it starts with SELECT
            if not sql_query.strip().upper().startswith('SELECT'):
                raise ValueError("Generated query is not a SELECT statement")
            return sql_query.strip()
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise

    def summarize_tickets(self, tickets: List[Dict[str, Any]], user_query: str) -> str:
        """Summarize relevant tickets for RAG."""
        if not tickets:
            return "No relevant tickets found."

        context = "\n\n".join([
            f"Ticket ID: {ticket['ticket_id']}\nSubject: {ticket['text']}"
            for ticket in tickets
        ])

        prompt = f"""
Based on the following ticket data, provide a concise summary that answers the user's query.

User Query: {user_query}

Relevant Tickets:
{context}

Summary:
"""

        try:
            return self.generate_response(prompt, context)
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise

# Global LLM manager instance
llm_manager = LLMManager()