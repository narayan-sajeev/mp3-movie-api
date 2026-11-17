import sqlite3
from pathlib import Path

def get_connection(db_path):
    """Return a fresh connection with rows accessible by column name."""
    # Define path
    path = Path(db_path)
    # Creates folder if needed
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create connection
    connection = sqlite3.connect(path)
    # Format row to access values easier
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database(db_path):
    """Create the movie table if it does not exist."""
    connection = get_connection(db_path)
    try:
        # Try to run SQL
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY,
                title TEXT,
                release_year INTEGER,
                rating REAL,
                genre TEXT
            )
            '''
        )
        # Commit transaction
        connection.commit()
    finally:
        # Close connection
        connection.close()