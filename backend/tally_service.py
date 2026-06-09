from __future__ import annotations

import json
from pathlib import Path

from crypto_utils import decrypt_vote
from db import get_db
from nin_registry import MockNINRegistry


def compute_tally(encryption_key: bytes, registry_path: Path) -> dict:
    db = get_db()
    ballots = db.execute("SELECT encrypted_vote FROM ballots ORDER BY id ASC").fetchall()
    total_ballots_cast = db.execute("SELECT COUNT(*) AS count FROM ballots").fetchone()["count"]
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
    status = "Completed" if total_registered_voters > 0 and remaining_voters == 0 else "Active"
    return {
        "yes": yes,
        "no": no,
        "total": yes + no,
        "total_registered_voters": total_registered_voters,
        "total_ballots_cast": total_ballots_cast,
        "remaining_voters": remaining_voters,
        "status": status,
    }


def public_board() -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT ballot_id, proof_hash, created_at
        FROM ballots
        ORDER BY id ASC
        """
    ).fetchall()
    return [
        {
            "ballot_id": row["ballot_id"],
            "proof_hash": row["proof_hash"],
            "timestamp": row["created_at"],
        }
        for row in rows
    ]


def fetch_ballot_for_verification(ballot_id: str):
    db = get_db()
    row = db.execute(
        """
        SELECT ballot_id, proof_hash, proof_path, public_inputs
        FROM ballots
        WHERE ballot_id = ?
        """,
        (ballot_id,),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["public_inputs"] = json.loads(result["public_inputs"])
    return result
