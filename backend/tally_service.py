from __future__ import annotations

import json
from pathlib import Path

from crypto_utils import decrypt_vote
from db import get_db
from events import ACTIVE_EVENT_ID, get_demo_ballot, get_demo_public_board, get_demo_tally, require_event
from nin_registry import MockNINRegistry


def compute_tally(encryption_key: bytes, registry_path: Path, event_id: str = ACTIVE_EVENT_ID) -> dict:
    event = require_event(event_id)
    demo_tally = get_demo_tally(event["event_id"])
    if demo_tally is not None:
        return {"event": event, **demo_tally}

    db = get_db()
    ballots = db.execute(
        "SELECT encrypted_vote FROM ballots WHERE event_id = ? ORDER BY id ASC",
        (event["event_id"],),
    ).fetchall()
    total_ballots_cast = db.execute(
        "SELECT COUNT(*) AS count FROM ballots WHERE event_id = ?",
        (event["event_id"],),
    ).fetchone()["count"]
    total_registered_voters = MockNINRegistry(registry_path).total_registered_voters()
    yes = 0
    no = 0
    for ballot in ballots:
        vote = decrypt_vote(ballot["encrypted_vote"], encryption_key)
        if vote == "yes":
            yes += 1
        elif vote == "no":
            no += 1
    remaining_voters = max(total_registered_voters - total_ballots_cast, 0)
    status = event["status"]
    if status == "Active" and total_registered_voters > 0 and remaining_voters == 0:
        status = "Completed"
    return {
        "event": event,
        "yes": yes,
        "no": no,
        "total": yes + no,
        "total_registered_voters": total_registered_voters,
        "total_ballots_cast": total_ballots_cast,
        "remaining_voters": remaining_voters,
        "status": status,
    }


def public_board(event_id: str = ACTIVE_EVENT_ID) -> list[dict]:
    event = require_event(event_id)
    demo_rows = get_demo_public_board(event["event_id"])
    if demo_rows is not None:
        return [
            {
                "ballot_id": row["ballot_id"],
                "event_id": row["event_id"],
                "event_title": event["title"],
                "proof_hash": row["proof_hash"],
                "timestamp": row["timestamp"],
            }
            for row in demo_rows
        ]

    db = get_db()
    rows = db.execute(
        """
        SELECT ballot_id, event_id, proof_hash, created_at
        FROM ballots
        WHERE event_id = ?
        ORDER BY id ASC
        """,
        (event["event_id"],),
    ).fetchall()
    return [
        {
            "ballot_id": row["ballot_id"],
            "event_id": row["event_id"],
            "event_title": event["title"],
            "proof_hash": row["proof_hash"],
            "timestamp": row["created_at"],
        }
        for row in rows
    ]


def fetch_ballot_for_verification(ballot_id: str, event_id: str | None = None):
    demo_ballot = get_demo_ballot(ballot_id, event_id)
    if demo_ballot is not None:
        return {
            "ballot_id": demo_ballot["ballot_id"],
            "event_id": demo_ballot["event_id"],
            "proof_hash": demo_ballot["proof_hash"],
            "is_demo": True,
        }

    db = get_db()
    if event_id:
        row = db.execute(
            """
            SELECT ballot_id, event_id, proof_hash, proof_path, public_inputs
            FROM ballots
            WHERE ballot_id = ? AND event_id = ?
            """,
            (ballot_id, event_id),
        ).fetchone()
    else:
        row = db.execute(
            """
            SELECT ballot_id, event_id, proof_hash, proof_path, public_inputs
            FROM ballots
            WHERE ballot_id = ?
            """,
            (ballot_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["public_inputs"] = json.loads(result["public_inputs"])
    result["is_demo"] = False
    return result
