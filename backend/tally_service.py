from __future__ import annotations

import base64
import json
from pathlib import Path

from flask import current_app

from crypto_utils import decrypt_vote
from db import get_db
from events import ACTIVE_EVENT_ID, get_demo_ballot, get_demo_public_board, get_demo_tally, require_event
from nin_registry import MockNINRegistry
from verifiability import (
    BOARD_CHAIN_GENESIS_HASH,
    PROTOCOL_VERSION,
    build_public_ballot_record,
    build_public_inputs,
    compute_chain_hash,
    compute_public_record_hash,
)


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


def public_board(
    event_id: str = ACTIVE_EVENT_ID,
    *,
    page: int | None = None,
    page_size: int | None = None,
) -> list[dict]:
    event = require_event(event_id)
    demo_rows = get_demo_public_board(event["event_id"])
    if demo_rows is not None:
        if page is not None and page_size is not None:
            start = max(page - 1, 0) * page_size
            end = start + page_size
            demo_rows = demo_rows[start:end]
        return [
            {
                "ballot_id": row["ballot_id"],
                "event_id": row["event_id"],
                "event_title": event["title"],
                "nullifier": row.get("nullifier", "demo-unavailable"),
                "vote_commitment": row.get("vote_commitment", "demo-unavailable"),
                "proof_hash": row["proof_hash"],
                "timestamp": row["timestamp"],
                "verification_status": row.get("verification_status", "verified"),
                "previous_chain_hash": row.get("previous_chain_hash", BOARD_CHAIN_GENESIS_HASH),
                "chain_hash": row.get("chain_hash", "demo-unavailable"),
            }
            for row in demo_rows
        ]

    db = get_db()
    query = """
        SELECT
            ballot_id,
            event_id,
            nullifier,
            vote_commitment,
            proof_hash,
            verification_status,
            previous_chain_hash,
            chain_hash,
            created_at
        FROM ballots
        WHERE event_id = ?
        ORDER BY id ASC
        """
    params: list[object] = [event["event_id"]]
    if page is not None and page_size is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([page_size, max(page - 1, 0) * page_size])
    rows = db.execute(query, tuple(params)).fetchall()
    return [
        {
            "ballot_id": row["ballot_id"],
            "event_id": row["event_id"],
            "event_title": event["title"],
            "nullifier": row["nullifier"],
            "vote_commitment": row["vote_commitment"],
            "proof_hash": row["proof_hash"],
            "verification_status": row["verification_status"],
            "previous_chain_hash": row["previous_chain_hash"],
            "chain_hash": row["chain_hash"],
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
            "nullifier": demo_ballot.get("nullifier", "demo-unavailable"),
            "vote_commitment": demo_ballot.get("vote_commitment", "demo-unavailable"),
            "is_demo": True,
        }

    db = get_db()
    if event_id:
        row = db.execute(
            """
            SELECT
                ballot_id,
                event_id,
                nullifier,
                vote_commitment,
                proof_hash,
                proof_path,
                public_inputs,
                verification_status,
                previous_chain_hash,
                current_record_hash,
                chain_hash,
                created_at
            FROM ballots
            WHERE ballot_id = ? AND event_id = ?
            """,
            (ballot_id, event_id),
        ).fetchone()
    else:
        row = db.execute(
            """
            SELECT
                ballot_id,
                event_id,
                nullifier,
                vote_commitment,
                proof_hash,
                proof_path,
                public_inputs,
                verification_status,
                previous_chain_hash,
                current_record_hash,
                chain_hash,
                created_at
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


def verify_public_board_chain(event_id: str = ACTIVE_EVENT_ID) -> dict:
    event = require_event(event_id)
    db = get_db()
    rows = db.execute(
        """
        SELECT
            ballot_id,
            event_id,
            nullifier,
            vote_commitment,
            proof_hash,
            verification_status,
            previous_chain_hash,
            current_record_hash,
            chain_hash,
            created_at
        FROM ballots
        WHERE event_id = ?
        ORDER BY id ASC
        """,
        (event["event_id"],),
    ).fetchall()

    previous_chain_hash = BOARD_CHAIN_GENESIS_HASH
    for index, row in enumerate(rows):
        public_record = build_public_ballot_record(
            ballot_id=row["ballot_id"],
            event_id=row["event_id"],
            event_title=event["title"],
            nullifier=row["nullifier"],
            vote_commitment=row["vote_commitment"],
            proof_hash=row["proof_hash"],
            timestamp=row["created_at"],
            verification_status=row["verification_status"],
        )
        expected_record_hash = compute_public_record_hash(public_record)
        expected_chain_hash = compute_chain_hash(previous_chain_hash, public_record)
        if row["previous_chain_hash"] != previous_chain_hash:
            return {
                "event_id": event["event_id"],
                "verified": False,
                "checked_ballots": index,
                "error": f"previous chain hash mismatch for ballot {row['ballot_id']}",
            }
        if row["current_record_hash"] != expected_record_hash:
            return {
                "event_id": event["event_id"],
                "verified": False,
                "checked_ballots": index + 1,
                "error": f"current record hash mismatch for ballot {row['ballot_id']}",
            }
        if row["chain_hash"] != expected_chain_hash:
            return {
                "event_id": event["event_id"],
                "verified": False,
                "checked_ballots": index + 1,
                "error": f"chain hash mismatch for ballot {row['ballot_id']}",
            }
        previous_chain_hash = row["chain_hash"]

    return {
        "event_id": event["event_id"],
        "event_title": event["title"],
        "verified": True,
        "checked_ballots": len(rows),
        "genesis_hash": BOARD_CHAIN_GENESIS_HASH,
        "final_chain_hash": previous_chain_hash,
    }


def build_verification_bundle(ballot_id: str, event_id: str | None = None):
    ballot = fetch_ballot_for_verification(ballot_id, event_id)
    if ballot is None or ballot.get("is_demo"):
        return None

    event = require_event(ballot["event_id"])
    public_record = build_public_ballot_record(
        ballot_id=ballot["ballot_id"],
        event_id=ballot["event_id"],
        event_title=event["title"],
        nullifier=ballot["nullifier"],
        vote_commitment=ballot["vote_commitment"],
        proof_hash=ballot["proof_hash"],
        timestamp=ballot["created_at"],
        verification_status=ballot["verification_status"],
    )
    bundle_public_inputs = build_public_inputs(
        event_id=ballot["event_id"],
        nullifier=ballot["nullifier"],
        vote_commitment=ballot["vote_commitment"],
    )
    proof_bytes = Path(ballot["proof_path"]).read_bytes()
    return {
        "bundle_format_version": "diasporavote-verification-bundle-v1",
        "ballot_id": ballot["ballot_id"],
        "event_id": ballot["event_id"],
        "event_title": event["title"],
        "public_inputs": bundle_public_inputs,
        "proof_artifact_base64": base64.b64encode(proof_bytes).decode("ascii"),
        "proof_hash": ballot["proof_hash"],
        "nullifier": ballot["nullifier"],
        "vote_commitment": ballot["vote_commitment"],
        "previous_chain_hash": ballot["previous_chain_hash"],
        "chain_hash": ballot["chain_hash"],
        "timestamp": ballot["created_at"],
        "verification_status": ballot["verification_status"],
        "verification_metadata": {
            "protocol_version": PROTOCOL_VERSION,
            "proof_system": "Winterfell zk-STARK",
            "public_record": public_record,
            "current_record_hash": ballot["current_record_hash"],
            "hash_chain_genesis": BOARD_CHAIN_GENESIS_HASH,
            "statement": (
                "The proof attests that a private binary vote, a private voter secret, and a "
                "private ballot salt are consistent with the published nullifier and vote "
                "commitment for the supplied event identifier."
            ),
        },
    }
