import os
import logging
from typing import List, Dict, Any
import pyodbc
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicketLoader:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.metadata = []
        # Use hardcoded database config for now (from knowledge_loader.py)
        self.db_config = {
            'server': '172.16.0.22',
            'database': 'jitbitHelpDesk',
            'username': 'ubaid',
            'password': 'Avanza@123',
            'driver': '{ODBC Driver 17 for SQL Server}'
        }

    def connect_db(self):
        """Establish database connection."""
        try:
            conn_str = (
                f"DRIVER={self.db_config['driver']};"
                f"SERVER={self.db_config['server']};"
                f"DATABASE={self.db_config['database']};"
                f"UID={self.db_config['username']};"
                f"PWD={self.db_config['password']};"
                "Encrypt=no;"
                "TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def load_tickets(self) -> List[Dict[str, Any]]:
        """Load ticket data from database using updated knowledge_loader."""
        try:
            # Import the updated knowledge_loader
            from knowledge_loader import load_ticket_conversations

            # Load structured tickets
            structured_tickets = load_ticket_conversations()

            # Convert to format expected by the rest of the system
            tickets = []
            for ticket in structured_tickets:
                tickets.append({
                    'ticket_id': ticket['ticket_id'],
                    'subject': ticket['subject'],
                    'summary': ticket['summary'],
                    'comments': ticket['comments'],
                    'text': ticket['full_text']  # For embeddings
                })

            logger.info(f"Loaded {len(tickets)} structured tickets")
            return tickets
        except Exception as e:
            logger.error(f"Failed to load tickets: {e}")
            raise

    def build_index(self, tickets: List[Dict[str, Any]]):
        """Build FAISS index from ticket embeddings."""
        texts = [ticket['text'] for ticket in tickets]
        logger.info("Encoding ticket texts...")
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

        # Build FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        # Store metadata with structured information
        self.metadata = [{
            'ticket_id': ticket['ticket_id'],
            'subject': ticket['subject'],
            'summary': ticket['summary'],
            'comments': ticket['comments'],
            'text': ticket['text']
        } for ticket in tickets]

        logger.info(f"Built FAISS index with {len(tickets)} vectors")

    def save_index(self, index_path: str = 'data/ticket_index.faiss', meta_path: str = 'data/ticket_meta.pkl'):
        """Save FAISS index and metadata to disk."""
        os.makedirs('data', exist_ok=True)
        faiss.write_index(self.index, index_path)
        with open(meta_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        logger.info("Index and metadata saved")

    def load_index(self, index_path: str = 'data/ticket_index.faiss', meta_path: str = 'data/ticket_meta.pkl'):
        """Load FAISS index and metadata from disk."""
        if os.path.exists(index_path) and os.path.exists(meta_path):
            self.index = faiss.read_index(index_path)
            with open(meta_path, 'rb') as f:
                self.metadata = pickle.load(f)
            logger.info("Index and metadata loaded")
            return True
        return False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar tickets."""
        if self.index is None:
            raise ValueError("Index not loaded. Call load_index() or build_index() first.")

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['score'] = round(float(distances[0][i]), 3)

                # Create clean summarized insight
                result['insight'] = self._generate_clean_insight(result)

                # Remove full text and comments from response for cleaner output
                result.pop('text', None)
                result.pop('comments', None)

                results.append(result)

        return results

    def _generate_clean_insight(self, ticket_data: Dict[str, Any]) -> str:
        """Generate a clean, summarized insight from ticket data."""
        import re

        # Combine subject and summary
        insight_parts = []
        if ticket_data.get('subject'):
            insight_parts.append(ticket_data['subject'])
        if ticket_data.get('summary'):
            insight_parts.append(ticket_data['summary'])

        # Add key comments (first 2-3 meaningful comments)
        comments = ticket_data.get('comments', [])
        meaningful_comments = []
        for comment in comments[:3]:  # Limit to first 3 comments
            text = comment.get('text', '') if isinstance(comment, dict) else str(comment)
            # Remove noise patterns
            text = re.sub(r'^(Dear|Hello|Hi)\s+\w+,?\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'Best\s+Regards:?\s*\w+', '', text, flags=re.IGNORECASE)
            text = re.sub(r'Please\s+connect|Kindly|Regards\s*$', '', text, flags=re.IGNORECASE)
            text = text.strip()
            if text and len(text) > 10:  # Only meaningful comments
                meaningful_comments.append(text[:100] + '...' if len(text) > 100 else text)

        insight_parts.extend(meaningful_comments[:2])  # Limit to 2 key comments

        # Join and limit length
        insight = '. '.join([p for p in insight_parts if p])
        if len(insight) > 200:
            insight = insight[:197] + '...'

        return insight

# Global loader instance
loader = TicketLoader()