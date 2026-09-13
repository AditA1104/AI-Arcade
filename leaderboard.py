import sqlite3
from datetime import datetime


DATABASE_NAME = "leaderboard.db"


def initialize_database():
    """Create the leaderboard table if it doesn't already exist."""
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def add_score(name, score):
    """Add a player's score to the leaderboard."""
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    timestamp = datetime.now().isoformat(timespec="seconds")

    cursor.execute("""
        INSERT INTO leaderboard (name, score, timestamp)
        VALUES (?, ?, ?)
    """, (name, score, timestamp))

    connection.commit()
    connection.close()


def get_top_scores(limit=10):
    """Return the highest scores."""
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT name, score, timestamp
        FROM leaderboard
        ORDER BY score DESC
        LIMIT ?
    """, (limit,))

    scores = cursor.fetchall()

    connection.close()

    return scores
