from __future__ import annotations

import argparse
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark_support import ACTIVE_EVENT_ID, create_benchmark_app, ensure_results_dir

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from crypto_utils import encrypt_vote  # noqa: E402
from db import get_db  # noqa: E402
from events import require_event  # noqa: E402
from tally_service import fetch_ballot_for_verification  # noqa: E402
from verifiability import (  # noqa: E402
    BOARD_CHAIN_GENESIS_HASH,
    build_public_ballot_record,
    build_public_inputs,
    compute_chain_hash,
    compute_public_record_hash,
    derive_nullifier,
    derive_vote_commitment,
    derive_voter_secret,
    field_element_to_hex,
    voter_secret_hash,
)


DEFAULT_SIZES = [1_000, 10_000, 100_000, 1_000_000]
DEFAULT_MAX_SECONDS = 240.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run public board and database scalability tests.")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    parser.add_argument(
        "--output",
        type=Path,
        default=ensure_results_dir() / "public_board_scalability_test.json",
    )
    return parser.parse_args()


def populate_ballots(app, size: int) -> Path:
    event = require_event(ACTIVE_EVENT_ID)
    with app.app_context():
        db = get_db()
        encryption_key = app.config["ENCRYPTION_KEY"]
        previous_chain_hash = BOARD_CHAIN_GENESIS_HASH
        voters = []
        ballots = []
        for index in range(1, size + 1):
            nin_hash = f"synthetic-nin-hash-{index:07d}"
            secret_value = derive_voter_secret(app.config["SECRET_KEY"], nin_hash)
            voters.append(
                (
                    nin_hash,
                    voter_secret_hash(secret_value),
                    "",
                    datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(),
                    1,
                    None,
                    1,
                )
            )

        db.executemany(
            """
            INSERT INTO voters (
                nin_hash,
                voter_secret_hash,
                session_token_hash,
                token_expires_at,
                biometric_verified,
                biometric_verified_at,
                has_voted
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            voters,
        )

        voter_rows = db.execute("SELECT id, nin_hash FROM voters ORDER BY id ASC").fetchall()
        created_at = "2026-06-18 12:00:00"
        for index, voter_row in enumerate(voter_rows, start=1):
            vote_value = 1 if index % 2 else 0
            vote_label = "yes" if vote_value == 1 else "no"
            secret_value = derive_voter_secret(app.config["SECRET_KEY"], voter_row["nin_hash"])
            ballot_salt = field_element_to_hex(index)
            _, nullifier = derive_nullifier(secret_value, ACTIVE_EVENT_ID)
            vote_commitment = derive_vote_commitment(vote_value, int(ballot_salt, 16))
            proof_hash = f"{index:064x}"[-64:]
            public_inputs = build_public_inputs(
                event_id=ACTIVE_EVENT_ID,
                nullifier=nullifier,
                vote_commitment=vote_commitment,
            )
            public_record = build_public_ballot_record(
                ballot_id=f"scalability-ballot-{index:07d}",
                event_id=ACTIVE_EVENT_ID,
                event_title=event["title"],
                nullifier=nullifier,
                vote_commitment=vote_commitment,
                proof_hash=proof_hash,
                timestamp=created_at,
                verification_status="verified",
            )
            current_record_hash = compute_public_record_hash(public_record)
            chain_hash = compute_chain_hash(previous_chain_hash, public_record)
            ballots.append(
                (
                    public_record["ballot_id"],
                    voter_row["id"],
                    ACTIVE_EVENT_ID,
                    encrypt_vote(vote_label, encryption_key),
                    nullifier,
                    vote_commitment,
                    ballot_salt,
                    proof_hash,
                    "synthetic-proof-path",
                    json.dumps(public_inputs),
                    "verified",
                    previous_chain_hash,
                    current_record_hash,
                    chain_hash,
                    created_at,
                )
            )
            previous_chain_hash = chain_hash

        db.executemany(
            """
            INSERT INTO ballots (
                ballot_id,
                voter_id,
                event_id,
                encrypted_vote,
                nullifier,
                vote_commitment,
                ballot_salt,
                proof_hash,
                proof_path,
                public_inputs,
                verification_status,
                previous_chain_hash,
                current_record_hash,
                chain_hash,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ballots,
        )
        db.commit()
        return Path(app.config["DATABASE_PATH"])


def timed_call(fn):
    started = time.perf_counter()
    result = fn()
    return (time.perf_counter() - started) * 1000.0, result


def lookup_ballot(app):
    with app.app_context():
        return fetch_ballot_for_verification("scalability-ballot-0000001", ACTIVE_EVENT_ID)


def run_size(size: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="diasporavote-scalability-") as temp_name:
        app = create_benchmark_app(Path(temp_name), voter_count=size)
        db_path = populate_ballots(app, size)
        client = app.test_client()

        tally_ms, tally_response = timed_call(
            lambda: client.get(f"/tally?event_id={ACTIVE_EVENT_ID}")
        )
        first_page_ms, first_page_response = timed_call(
            lambda: client.get(f"/board?event_id={ACTIVE_EVENT_ID}&page=1&page_size=50")
        )
        paginated_page = min(max(size // 50, 1), 10)
        paginated_ms, paginated_response = timed_call(
            lambda: client.get(
                f"/board?event_id={ACTIVE_EVENT_ID}&page={paginated_page}&page_size=50"
            )
        )
        lookup_ms, ballot_lookup = timed_call(lambda: lookup_ballot(app))
        chain_ms, chain_response = timed_call(
            lambda: client.get(f"/board/verify-chain?event_id={ACTIVE_EVENT_ID}")
        )

        return {
            "ballot_table_size": size,
            "status": "completed",
            "database_size_bytes": db_path.stat().st_size,
            "tally_query_time_ms": round(tally_ms, 6),
            "public_board_first_page_query_time_ms": round(first_page_ms, 6),
            "paginated_query_time_ms": round(paginated_ms, 6),
            "ballot_lookup_time_ms": round(lookup_ms, 6),
            "chain_verification_time_ms": round(chain_ms, 6),
            "tally_total": tally_response.get_json()["total"],
            "first_page_rows": len(first_page_response.get_json()["ballots"]),
            "paginated_rows": len(paginated_response.get_json()["ballots"]),
            "chain_verified": chain_response.get_json()["verified"],
            "lookup_found": ballot_lookup is not None,
        }


def main() -> int:
    args = parse_args()
    results: list[dict[str, object]] = []
    started_at = time.perf_counter()
    average_db_time_ms_hint = 0.0

    for size in DEFAULT_SIZES:
        elapsed = time.perf_counter() - started_at
        projected = (size * average_db_time_ms_hint) / 1_000_000.0 if average_db_time_ms_hint else 0.0
        if average_db_time_ms_hint and elapsed + projected > args.max_seconds:
            results.append(
                {
                    "ballot_table_size": size,
                    "status": "skipped",
                    "reason": f"projected runtime exceeds {args.max_seconds:.0f} seconds",
                }
            )
            continue
        result = run_size(size)
        results.append(result)
        average_db_time_ms_hint = float(result["tally_query_time_ms"])

    payload = {
        "benchmark": "public_board_scalability_test",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "requested_ballot_table_sizes": DEFAULT_SIZES,
        "max_seconds": args.max_seconds,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
