from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flask import current_app, g

from crypto_utils import hash_nin
from events import ACTIVE_EVENT_ID, get_event
from verifiability import (
    BOARD_CHAIN_GENESIS_HASH,
    build_public_ballot_record,
    compute_chain_hash,
    compute_public_record_hash,
    derive_voter_secret,
    field_element_to_hex,
    voter_secret_hash,
)


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


def _ensure_voter_secret_hashes(db: sqlite3.Connection) -> None:
    columns = {row["name"] for row in db.execute("PRAGMA table_info(voters)").fetchall()}
    if "voter_secret_hash" not in columns:
        db.execute("ALTER TABLE voters ADD COLUMN voter_secret_hash TEXT NOT NULL DEFAULT ''")

    rows = db.execute("SELECT id, nin_hash, voter_secret_hash FROM voters").fetchall()
    for row in rows:
        if row["voter_secret_hash"]:
            continue
        secret_value = derive_voter_secret(current_app.config["SECRET_KEY"], row["nin_hash"])
        db.execute(
            "UPDATE voters SET voter_secret_hash = ? WHERE id = ?",
            (voter_secret_hash(secret_value), row["id"]),
        )


def _backfill_ballot_integrity_fields(db: sqlite3.Connection) -> None:
    columns = {row["name"] for row in db.execute("PRAGMA table_info(ballots)").fetchall()}
    required_columns = {
        "nullifier": "ALTER TABLE ballots ADD COLUMN nullifier TEXT NOT NULL DEFAULT ''",
        "vote_commitment": "ALTER TABLE ballots ADD COLUMN vote_commitment TEXT NOT NULL DEFAULT ''",
        "ballot_salt": "ALTER TABLE ballots ADD COLUMN ballot_salt TEXT NOT NULL DEFAULT ''",
        "verification_status": "ALTER TABLE ballots ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'verified'",
        "previous_chain_hash": "ALTER TABLE ballots ADD COLUMN previous_chain_hash TEXT NOT NULL DEFAULT ''",
        "current_record_hash": "ALTER TABLE ballots ADD COLUMN current_record_hash TEXT NOT NULL DEFAULT ''",
        "chain_hash": "ALTER TABLE ballots ADD COLUMN chain_hash TEXT NOT NULL DEFAULT ''",
    }
    for column, statement in required_columns.items():
        if column not in columns:
            db.execute(statement)

    rows = db.execute(
        """
        SELECT
            id,
            ballot_id,
            event_id,
            proof_hash,
            created_at,
            nullifier,
            vote_commitment,
            ballot_salt,
            verification_status,
            previous_chain_hash,
            current_record_hash,
            chain_hash
        FROM ballots
        ORDER BY event_id ASC, id ASC
        """
    ).fetchall()

    chain_heads: dict[str, str] = {}
    for row in rows:
        event = get_event(row["event_id"]) or {"title": row["event_id"]}
        verification_status = row["verification_status"] or "verified"
        nullifier = row["nullifier"] or field_element_to_hex(
            int.from_bytes(
                f"legacy-nullifier:{row['ballot_id']}".encode("utf-8"),
                "big",
                signed=False,
            )
        )
        vote_commitment = row["vote_commitment"] or field_element_to_hex(
            int.from_bytes(
                f"legacy-commitment:{row['ballot_id']}".encode("utf-8"),
                "big",
                signed=False,
            )
        )
        ballot_salt = row["ballot_salt"] or field_element_to_hex(
            int.from_bytes(
                f"legacy-salt:{row['ballot_id']}".encode("utf-8"),
                "big",
                signed=False,
            )
        )
        public_record = build_public_ballot_record(
            ballot_id=row["ballot_id"],
            event_id=row["event_id"],
            event_title=event["title"],
            nullifier=nullifier,
            vote_commitment=vote_commitment,
            proof_hash=row["proof_hash"],
            timestamp=row["created_at"],
            verification_status=verification_status,
        )
        previous_chain_hash = (
            row["previous_chain_hash"]
            or chain_heads.get(row["event_id"], BOARD_CHAIN_GENESIS_HASH)
        )
        current_record_hash = row["current_record_hash"] or compute_public_record_hash(public_record)
        chain_hash = row["chain_hash"] or compute_chain_hash(previous_chain_hash, public_record)

        db.execute(
            """
            UPDATE ballots
            SET
                nullifier = ?,
                vote_commitment = ?,
                ballot_salt = ?,
                verification_status = ?,
                previous_chain_hash = ?,
                current_record_hash = ?,
                chain_hash = ?
            WHERE id = ?
            """,
            (
                nullifier,
                vote_commitment,
                ballot_salt,
                verification_status,
                previous_chain_hash,
                current_record_hash,
                chain_hash,
                row["id"],
            ),
        )
        chain_heads[row["event_id"]] = chain_hash


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
    _ensure_voter_secret_hashes(db)
    _backfill_ballot_integrity_fields(db)
    _seed_mock_voters_if_empty(db)
    db.commit()
