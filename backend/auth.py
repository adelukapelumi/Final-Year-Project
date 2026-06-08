from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from flask import current_app

from crypto_utils import constant_time_equal, hash_nin, hash_token, issue_session_token
from db import get_db
from nin_registry import MockNINRegistry


def normalize_nin(nin: str | None) -> str:
    if not nin:
        raise ValueError("nin is required")
    normalized = "".join(ch for ch in str(nin) if ch.isdigit())
    if len(normalized) != 11:
        raise ValueError("nin must contain 11 digits")
    return normalized


def resolve_token_from_request(request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    if not token:
        raise ValueError("authentication token is required")
    return str(token)


def register_or_login(nin: str) -> dict:
    normalized_nin = normalize_nin(nin)
    nin_hash = hash_nin(normalized_nin)
    registry = MockNINRegistry(current_app.config["NIN_REGISTRY_PATH"])
    if not registry.is_registered_hash(nin_hash):
        raise PermissionError("nin is not registered")

    db = get_db()
    token = issue_session_token()
    token_hash = hash_token(token)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=current_app.config["TOKEN_TTL_SECONDS"])).isoformat()

    voter = db.execute("SELECT id FROM voters WHERE nin_hash = ?", (nin_hash,)).fetchone()
    if voter is None:
        cursor = db.execute(
            """
            INSERT INTO voters (nin_hash, session_token_hash, token_expires_at, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (nin_hash, token_hash, expires_at),
        )
        voter_id = cursor.lastrowid
    else:
        voter_id = voter["id"]
        db.execute(
            """
            UPDATE voters
            SET session_token_hash = ?, token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (token_hash, expires_at, voter_id),
        )
    db.commit()

    return {"token": token, "voter_id": voter_id, "nin_hash": nin_hash}


def authenticate_token(token: str) -> sqlite3.Row:
    db = get_db()
    token_hash = hash_token(token)
    voter = db.execute(
        """
        SELECT id, nin_hash, session_token_hash, token_expires_at
        FROM voters
        WHERE session_token_hash = ?
        """,
        (token_hash,),
    ).fetchone()
    if voter is None or not constant_time_equal(voter["session_token_hash"], token_hash):
        raise PermissionError("invalid session token")
    if voter["token_expires_at"] < datetime.now(timezone.utc).isoformat():
        raise PermissionError("session token expired")
    return voter
