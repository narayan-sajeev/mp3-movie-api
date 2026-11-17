import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)

MOVIE_COLUMNS = ['title', 'release_year', 'rating', 'genre']

class MovieStorage:
    def __init__(self, db_path='data/movies.db'):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        ordered_df = df[MOVIE_COLUMNS].copy()
        records = []
        # Loop through rows
        for _, row in ordered_df.iterrows():
            cleaned_row = []
            # Loop through values in row
            for value in row:
                if pd.isna(value):
                    # Add None
                    cleaned_row.append(None)
                else:
                    cleaned_row.append(value)
            records.append(tuple(cleaned_row))

        # Connect
        connection = get_connection(self.db_path)

        try:
            # Clear table
            connection.execute('DELETE FROM movies')
            # Insert rows into table
            connection.executemany(
                '''
                INSERT INTO movies (title, release_year, rating, genre)
                    VALUES (?, ?, ?, ?)
                ''',
                # Comma turns into tuple
                records,
            )
            # Commit changes
            connection.commit()
            logger.debug(f'Stored movies in SQLite: rows={len(records)}')
        except sqlite3.Error:
            # Roll back changes if there's error
            connection.rollback()
            # Raise same error
            raise
        finally:
            connection.close()

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        # Connect
        connection = get_connection(self.db_path)
        try:
            # Start transaction
            cursor = connection.execute(
                '''
                SELECT title, release_year, rating, genre
                FROM movies
                ORDER BY id ASC
                '''
            )
            # Get rows using SQL
            rows = [dict(row) for row in cursor.fetchall()]
            # Return rows as df
            return pd.DataFrame(rows, columns=MOVIE_COLUMNS)
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        # Loop through columns
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        # Join columns
        selected_columns = ", ".join(["id"] + columns)

        connection = get_connection(self.db_path)

        try:
            # Start transaction
            cursor = connection.execute(
                f'SELECT {selected_columns} FROM movies ORDER BY id ASC LIMIT ?',
                    (limit,),
            )
            # Get rows
            results = [dict(row) for row in cursor.fetchall()]
            logger.debug(
                f'Selected movie columns: columns={columns}, limit={limit}, rows={len(results)}'
            )
            return results
        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute('SELECT COUNT(*) FROM movies')
            # Use [0] to retrieve number even if it's just one number
            return int(cursor.fetchone()[0])
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error('Select at least one column')
            raise ValueError('Select at least one column')

        # Loop through columns
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f'Unsupported column: {column}')
                raise ValueError(f'Unsupported column: {column}')

        # Join columns
        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)

        try:
            # Start transaction
            cursor = connection.execute(
                f'''
                SELECT {selected_columns}
                FROM movies
                WHERE rating >= ?
                ORDER BY rating DESC, id ASC
                LIMIT ?
                ''',
                (min_rating, limit),
            )
            # Get results
            results = [dict(row) for row in cursor.fetchall()]
            logger.debug(
                f'Queried movies in SQLite: columns={columns}, min_rating={min_rating}, rows={len(results)}'
            )
            return results
        finally:
            connection.close()