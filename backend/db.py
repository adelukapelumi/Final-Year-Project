from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flask import current_app, g

from crypto_utils import hash_nin
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


def _seed_mock_voters_if_empty(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT COUNT(*) AS count FROM mock_voters").fetchone()["count"]
    if existing:
        return

    registry_path = Path(current_app.config["NIN_REGISTRY_PATH"])
    if not registry_path.exists():
        return

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    registered_voters = payload.get("registered_voters")
    if registered_voters is None:
        registered_voters = [{"nin": nin} for nin in payload.get("registered_nins", [])]

    for item in registered_voters:
        normalized_nin = "".join(ch for ch in str(item.get("nin", "")) if ch.isdigit())
        if len(normalized_nin) != 11:
            continue
        biometric = item.get("biometric") or {}
        biometric_flag = item.get("mock_biometric_enabled")
        if biometric_flag is None:
            if "face_template_enabled" in item:
                biometric_flag = item.get("face_template_enabled")
            elif "face_template_id" in biometric or "accepted_probe_id" in biometric or "verification_mode" in biometric:
                biometric_flag = bool(biometric.get("face_template_id", True))
            else:
                biometric_flag = True
        db.execute(
            """
            INSERT INTO mock_voters (
                nin_hash,
                nin_last4,
                masked_nin,
                display_name,
                diaspora_location,
                voter_category,
                mock_biometric_enabled,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                hash_nin(normalized_nin),
                normalized_nin[-4:],
                f"{'*' * 7}{normalized_nin[-4:]}",
                item.get("display_name", "Prototype Diaspora Voter"),
                item.get("diaspora_location", "Diaspora"),
                item.get("voter_category", "Eligible Diaspora Voter"),
                1 if biometric_flag else 0,
            ),
        )


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
    _seed_mock_voters_if_empty(db)
    db.commit()
