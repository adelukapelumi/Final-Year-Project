from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

from events import ACTIVE_EVENT_ID


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _migrate_ballots_to_events(db: sqlite3.Connection) -> None:
    table = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ballots'"
    ).fetchone()
    if table is None:
        return

    columns = {row["name"] for row in db.execute("PRAGMA table_info(ballots)").fetchall()}
    table_sql = str(table["sql"] or "")
    needs_migration = "event_id" not in columns or "voter_id INTEGER NOT NULL UNIQUE" in table_sql
    if not needs_migration:
        return

    db.execute(
        """
        CREATE TABLE ballots_event_migration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ballot_id TEXT NOT NULL UNIQUE,
            voter_id INTEGER NOT NULL,
            event_id TEXT NOT NULL DEFAULT 'diaspora-referendum-2026',
            encrypted_vote TEXT NOT NULL,
            proof_hash TEXT NOT NULL,
            proof_path TEXT NOT NULL,
            public_inputs TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
            UNIQUE (voter_id, event_id)
        )
        """
    )
    event_expression = "event_id" if "event_id" in columns else "?"
    db.execute(
        f"""
        INSERT INTO ballots_event_migration (
            id,
            ballot_id,
            voter_id,
            event_id,
            encrypted_vote,
            proof_hash,
            proof_path,
            public_inputs,
            created_at
        )
        SELECT
            id,
            ballot_id,
            voter_id,
            {event_expression},
            encrypted_vote,
            proof_hash,
            proof_path,
            public_inputs,
            created_at
        FROM ballots
        """,
        () if "event_id" in columns else (ACTIVE_EVENT_ID,),
    )
    db.execute("DROP TABLE ballots")
    db.execute("ALTER TABLE ballots_event_migration RENAME TO ballots")


def init_db() -> None:
    db = get_db()
    schema_path = Path(current_app.config["SCHEMA_PATH"])
    db.executescript(schema_path.read_text(encoding="utf-8"))
    columns = {row["name"] for row in db.execute("PRAGMA table_info(voters)").fetchall()}
    if "biometric_verified" not in columns:
        db.execute("ALTER TABLE voters ADD COLUMN biometric_verified INTEGER NOT NULL DEFAULT 0")
    if "biometric_verified_at" not in columns:
        db.execute("ALTER TABLE voters ADD COLUMN biometric_verified_at TEXT")
    _migrate_ballots_to_events(db)
    db.commit()
