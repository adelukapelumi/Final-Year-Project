from __future__ import annotations

import argparse
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark_support import (
    ACTIVE_EVENT_ID,
    benchmark_voter_record,
    create_benchmark_app,
    ensure_results_dir,
    register_and_vote,
)


DEFAULT_SCALES = [1_000, 10_000, 100_000]
DEFAULT_MAX_SECONDS = 240.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark backend ballot acceptance.")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    parser.add_argument(
        "--output",
        type=Path,
        default=ensure_results_dir() / "backend_ballot_benchmark.json",
    )
    return parser.parse_args()


def run_scale(scale: int) -> dict[str, object]:
    latencies: list[float] = []
    accepted = 0
    failed = 0
    expected_yes = 0
    expected_no = 0

    with tempfile.TemporaryDirectory(prefix="diasporavote-backend-benchmark-") as temp_name:
        app = create_benchmark_app(Path(temp_name), voter_count=scale)
        client = app.test_client()
        total_started = time.perf_counter()

        for index in range(1, scale + 1):
            nin = benchmark_voter_record(index)["nin"]
            vote_value = "yes" if index % 2 else "no"
            if vote_value == "yes":
                expected_yes += 1
            else:
                expected_no += 1

            started = time.perf_counter()
            result = register_and_vote(client, nin, vote_value)
            latency_ms = (time.perf_counter() - started) * 1000.0
            latencies.append(latency_ms)
            if result["vote_response"].status_code == 201:
                accepted += 1
            else:
                failed += 1

        total_elapsed_seconds = time.perf_counter() - total_started

        with app.app_context():
            from db import get_db  # local import to avoid script import side effects

            db = get_db()
            unique_nullifiers = db.execute(
                "SELECT COUNT(DISTINCT nullifier) AS count FROM ballots WHERE event_id = ?",
                (ACTIVE_EVENT_ID,),
            ).fetchone()["count"]

        tally_response = client.get(f"/tally?event_id={ACTIVE_EVENT_ID}")
        tally_payload = tally_response.get_json()

    return {
        "scale": scale,
        "status": "completed",
        "total_accepted_ballots": accepted,
        "failed_ballots": failed,
        "average_ballot_acceptance_time_ms": round(sum(latencies) / max(len(latencies), 1), 6),
        "minimum_ballot_acceptance_time_ms": round(min(latencies), 6),
        "maximum_ballot_acceptance_time_ms": round(max(latencies), 6),
        "throughput_ballots_per_second": round(accepted / max(total_elapsed_seconds, 1e-9), 6),
        "proof_generation_and_verification_time_note": "Captured inside end-to-end ballot acceptance latency.",
        "final_tally_correctness": tally_payload["yes"] == expected_yes
        and tally_payload["no"] == expected_no
        and tally_payload["total_ballots_cast"] == accepted,
        "nullifier_uniqueness_correctness": unique_nullifiers == accepted,
        "expected_yes": expected_yes,
        "expected_no": expected_no,
        "observed_yes": tally_payload["yes"],
        "observed_no": tally_payload["no"],
    }


def main() -> int:
    args = parse_args()
    started_at = time.perf_counter()
    results: list[dict[str, object]] = []
    average_latency_ms_hint = 0.0

    for scale in DEFAULT_SCALES:
        elapsed = time.perf_counter() - started_at
        if average_latency_ms_hint and elapsed + ((scale * average_latency_ms_hint) / 1000.0) > args.max_seconds:
            results.append(
                {
                    "scale": scale,
                    "status": "skipped",
                    "reason": f"projected runtime exceeds {args.max_seconds:.0f} seconds",
                }
            )
            continue
        result = run_scale(scale)
        results.append(result)
        average_latency_ms_hint = float(result["average_ballot_acceptance_time_ms"])

    payload = {
        "benchmark": "backend_ballot_benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "requested_scales": DEFAULT_SCALES,
        "max_seconds": args.max_seconds,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
