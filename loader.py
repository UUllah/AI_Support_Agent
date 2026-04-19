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
        self.db_config = {
            'server': os.getenv('DB_SERVER'),
            'database': os.getenv('DB_NAME'),
            'username': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
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
                "Trusted_Connection=no;"
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def load_tickets(self) -> List[Dict[str, Any]]:
        """Load ticket data from SQL Server."""
        query = """
        SELECT ticket_id, subject, summary
        FROM tickets
        WHERE subject IS NOT NULL AND summary IS NOT NULL
        """
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                tickets = []
                for row in rows:
                    ticket_text = f"{row.subject} {row.summary}"
                    tickets.append({
                        'ticket_id': row.ticket_id,
                        'text': ticket_text
                    })
                logger.info(f"Loaded {len(tickets)} tickets")
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

        # Store metadata
        self.metadata = [{'ticket_id': ticket['ticket_id'], 'text': ticket['text']} for ticket in tickets]

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
                result['score'] = float(distances[0][i])
                results.append(result)

        return results

# Global loader instance
loader = TicketLoader()