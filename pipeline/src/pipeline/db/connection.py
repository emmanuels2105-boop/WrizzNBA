import sqlite3
from pathlib import Path

from pipeline.db.schema import SCHEMA_STATEMENTS, SEED_PROP_TYPES


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)

    # Migration for databases created before is_lock existed -- CREATE TABLE IF
    # NOT EXISTS above won't add columns to an already-existing predictions table.
    try:
        conn.execute("ALTER TABLE predictions ADD COLUMN is_lock INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists

    for name, stat_column, description in SEED_PROP_TYPES:
        conn.execute(
            """
            INSERT INTO prop_types (name, stat_column, description)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                stat_column = excluded.stat_column,
                description = excluded.description
            """,
            (name, stat_column, description),
        )
    conn.commit()
