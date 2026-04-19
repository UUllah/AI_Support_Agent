import os
import logging
from typing import List, Dict, Any
import pyodbc
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = {
            'server': os.getenv('DB_SERVER'),
            'database': os.getenv('DB_NAME'),
            'username': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'driver': '{ODBC Driver 17 for SQL Server}'
        }

    def connect(self):
        """Establish database connection."""
        try:
            conn_str = (
                f"DRIVER={self.config['driver']};"
                f"SERVER={self.config['server']};"
                f"DATABASE={self.config['database']};"
                f"UID={self.config['username']};"
                f"PWD={self.config['password']};"
                "Trusted_Connection=no;"
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def execute_select_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SELECT query safely and return results as JSON-serializable dicts."""
        if not query.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")

        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    result_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert to JSON-serializable types
                        if isinstance(value, (pyodbc.Time, pyodbc.Date, pyodbc.Timestamp)):
                            value = str(value)
                        elif value is None:
                            pass  # Keep as None
                        result_dict[col] = value
                    results.append(result_dict)

                logger.info(f"Executed query, returned {len(results)} rows")
                return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a table."""
        query = f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        try:
            schema = self.execute_select_query(query)
            return {
                'table': table_name,
                'columns': schema
            }
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            raise

    def get_available_tables(self) -> List[str]:
        """Get list of available tables in the database."""
        query = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        """
        try:
            results = self.execute_select_query(query)
            return [row['TABLE_NAME'] for row in results]
        except Exception as e:
            logger.error(f"Failed to get available tables: {e}")
            raise

# Global database manager instance
db_manager = DatabaseManager()