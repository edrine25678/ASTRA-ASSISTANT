"""
SQLite storage for Astra's memory.

Simple and deliberately uncomplicated: one table of categorized
entries.  Not a full database system.
"""

import os
import sqlite3
from datetime import datetime


def _now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


class MemoryDatabase:

    CATEGORIES = (
        "short_term",
        "long_term",
        "preferences",
        "facts",
        "tasks",
        "instructions",
    )

    def __init__(self, db_path):
        self.db_path = db_path

        directory = os.path.dirname(db_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):

        with self._connection:

            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            self._connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entries_category
                ON entries(category)
                """
            )

    def add_entry(self, category, content):
        """Insert an entry and return its id."""

        with self._connection:

            cursor = self._connection.execute(
                """
                INSERT INTO entries (category, content, created_at)
                VALUES (?, ?, ?)
                """,
                (category, content, _now()),
            )

        return cursor.lastrowid

    def list_entries(self, category=None, categories=None, limit=20):
        """Return entries, newest first."""

        query = "SELECT id, category, content, created_at FROM entries"
        parameters = []

        if category is not None:
            query += " WHERE category = ?"
            parameters.append(category)
        elif categories:
            placeholders = ", ".join("?" for _ in categories)
            query += f" WHERE category IN ({placeholders})"
            parameters.extend(categories)

        query += " ORDER BY id DESC LIMIT ?"
        parameters.append(limit)

        with self._connection:
            rows = self._connection.execute(query, parameters).fetchall()

        return [dict(row) for row in rows]

    def search_entries(self, query, category=None, categories=None, limit=20):
        """Return entries whose content contains the query."""

        like = f"%{query}%"

        sql = "SELECT id, category, content, created_at FROM entries"
        parameters = []

        sql += " WHERE content LIKE ?"
        parameters.append(like)

        if category is not None:
            sql += " AND category = ?"
            parameters.append(category)
        elif categories:
            placeholders = ", ".join("?" for _ in categories)
            sql += f" AND category IN ({placeholders})"
            parameters.extend(categories)

        sql += " ORDER BY id DESC LIMIT ?"
        parameters.append(limit)

        with self._connection:
            rows = self._connection.execute(sql, parameters).fetchall()

        return [dict(row) for row in rows]

    def delete_entries(self, category=None, content=None):
        """Delete matching entries and return how many were removed."""

        sql = "DELETE FROM entries"
        conditions = []
        parameters = []

        if category is not None:
            conditions.append("category = ?")
            parameters.append(category)

        if content is not None:
            conditions.append("content LIKE ?")
            parameters.append(f"%{content}%")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        with self._connection:
            cursor = self._connection.execute(sql, parameters)

        return cursor.rowcount

    def count_by_category(self):
        """Return {category: count} for every category."""

        with self._connection:
            rows = self._connection.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM entries
                GROUP BY category
                """
            ).fetchall()

        return {row["category"]: row["count"] for row in rows}

    def prune_category(self, category, keep):
        """Keep only the most recent `keep` entries of a category."""

        with self._connection:

            cursor = self._connection.execute(
                """
                DELETE FROM entries
                WHERE category = ?
                  AND id NOT IN (
                      SELECT id FROM entries
                      WHERE category = ?
                      ORDER BY id DESC LIMIT ?
                  )
                """,
                (category, category, keep),
            )

        return cursor.rowcount

    def close(self):

        self._connection.close()
