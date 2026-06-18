from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import datetime, timedelta

from verifiability import (
    BOARD_CHAIN_GENESIS_HASH,
    build_public_ballot_record,
    compute_chain_hash,
)


ACTIVE_EVENT_ID = "diaspora-referendum-2026"

EVENTS = (
    {
        "event_id": ACTIVE_EVENT_ID,
        "title": "Diaspora Voting Referendum",
        "question": "Should secure diaspora voting be enabled for eligible Nigerians abroad?",
        "ballot_type": "Binary referendum",
        "status": "Active",
        "description": "A prototype referendum on enabling secure voting access for eligible Nigerians abroad.",
        "start_date": "June 10, 2026",
        "end_date": "June 30, 2026",
        "action_enabled": True,
    },
    {
        "event_id": "overseas-voter-education-poll",
        "title": "Overseas Voter Education Poll",
        "question": "How should future diaspora voter education materials be delivered?",
        "ballot_type": "Demonstration event",
        "status": "Upcoming",
        "description": "A non-voteable preview event for future voter education and portal guidance.",
        "start_date": "July 2026",
        "end_date": "To be announced",
        "action_enabled": False,
    },
    {
        "event_id": "secure-ballot-audit-drill",
        "title": "Secure Ballot Audit Drill",
        "question": "Prototype audit workflow demonstration",
        "ballot_type": "Demonstration event",
        "status": "Closed",
        "description": "A completed demonstration of privacy-preserving ballot receipt auditing.",
        "start_date": "May 2026",
        "end_date": "Closed May 31, 2026",
        "action_enabled": False,
    },
)


def _build_closed_demo_board() -> list[dict]:
    start_time = datetime(2026, 5, 31, 8, 0, 0)
    ballots: list[dict] = []
    previous_chain_hash = BOARD_CHAIN_GENESIS_HASH
    for index in range(1, 49):
        ballot_id = f"audit-drill-{index:04d}"
        proof_hash = hashlib.sha256(
            f"secure-ballot-audit-drill:{ballot_id}".encode("utf-8")
        ).hexdigest()
        nullifier = hashlib.sha256(
            f"secure-ballot-audit-drill:nullifier:{ballot_id}".encode("utf-8")
        ).hexdigest()[:32]
        vote_commitment = hashlib.sha256(
            f"secure-ballot-audit-drill:commitment:{ballot_id}".encode("utf-8")
        ).hexdigest()[:32]
        timestamp = (start_time + timedelta(minutes=index * 6)).strftime("%Y-%m-%d %H:%M:%S")
        public_record = build_public_ballot_record(
            ballot_id=ballot_id,
            event_id="secure-ballot-audit-drill",
            event_title="Secure Ballot Audit Drill",
            nullifier=f"0x{nullifier}",
            vote_commitment=f"0x{vote_commitment}",
            proof_hash=proof_hash,
            timestamp=timestamp,
            verification_status="verified",
        )
        chain_hash = compute_chain_hash(previous_chain_hash, public_record)
        ballots.append(
            {
                "ballot_id": ballot_id,
                "event_id": "secure-ballot-audit-drill",
                "nullifier": f"0x{nullifier}",
                "vote_commitment": f"0x{vote_commitment}",
                "proof_hash": proof_hash,
                "timestamp": timestamp,
                "verification_status": "verified",
                "previous_chain_hash": previous_chain_hash,
                "chain_hash": chain_hash,
            }
        )
        previous_chain_hash = chain_hash
    return ballots


DEMO_EVENT_TALLIES = {
    "overseas-voter-education-poll": {
        "yes": 0,
        "no": 0,
        "total": 0,
        "total_registered_voters": 0,
        "total_ballots_cast": 0,
        "remaining_voters": 0,
        "status": "Coming Soon",
    },
    "secure-ballot-audit-drill": {
        "yes": 31,
        "no": 17,
        "total": 48,
        "total_registered_voters": 48,
        "total_ballots_cast": 48,
        "remaining_voters": 0,
        "status": "Completed",
    },
}

DEMO_PUBLIC_BOARD = {
    "overseas-voter-education-poll": [],
    "secure-ballot-audit-drill": _build_closed_demo_board(),
}


def list_events() -> list[dict]:
    return [dict(event) for event in EVENTS]


def get_event(event_id: str | None) -> dict | None:
    normalized_event_id = str(event_id or ACTIVE_EVENT_ID).strip()
    return next((dict(event) for event in EVENTS if event["event_id"] == normalized_event_id), None)


def require_event(event_id: str | None) -> dict:
    event = get_event(event_id)
    if event is None:
        raise ValueError("unknown referendum event")
    return event


def get_demo_tally(event_id: str) -> dict | None:
    demo_tally = DEMO_EVENT_TALLIES.get(event_id)
    return deepcopy(demo_tally) if demo_tally is not None else None


def get_demo_public_board(event_id: str) -> list[dict] | None:
    if event_id not in DEMO_PUBLIC_BOARD:
        return None
    return deepcopy(DEMO_PUBLIC_BOARD[event_id])


def get_demo_ballot(ballot_id: str, event_id: str | None = None) -> dict | None:
    event_ids = [event_id] if event_id else list(DEMO_PUBLIC_BOARD.keys())
    for candidate_event_id in event_ids:
        ballots = DEMO_PUBLIC_BOARD.get(candidate_event_id, [])
        for ballot in ballots:
            if ballot["ballot_id"] == ballot_id:
                return deepcopy(ballot)
    return None
