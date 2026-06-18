from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark_support import (
    ACTIVE_EVENT_ID,
    benchmark_voter_record,
    ensure_results_dir,
    get_json,
    post_json,
    running_server,
)


DEFAULT_LEVELS = [10, 50, 100, 200, 500]
DEFAULT_MAX_SECONDS = 240.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run concurrent voting stress tests.")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    parser.add_argument(
        "--output",
        type=Path,
        default=ensure_results_dir() / "concurrent_voting_stress_test.json",
    )
    return parser.parse_args()


def execute_voter(base_url: str, index: int) -> dict[str, object]:
    nin = benchmark_voter_record(index)["nin"]
    vote_value = "yes" if index % 2 else "no"
    started = time.perf_counter()

    register_status, register_payload = post_json(base_url, "/register", {"nin": nin})
    if register_status != 200:
        return {"success": False, "latency_ms": (time.perf_counter() - started) * 1000.0}

    token = register_payload["token"]
    biometric_status, _ = post_json(
        base_url,
        "/biometric-verify",
        {"camera_capture": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    if biometric_status != 200:
        return {"success": False, "latency_ms": (time.perf_counter() - started) * 1000.0}

    vote_status, _ = post_json(
        base_url,
        "/vote",
        {"vote": vote_value, "event_id": ACTIVE_EVENT_ID},
        headers={"Authorization": f"Bearer {token}"},
    )
    duplicate_status, _ = post_json(
        base_url,
        "/vote",
        {"vote": vote_value, "event_id": ACTIVE_EVENT_ID},
        headers={"Authorization": f"Bearer {token}"},
    )

    return {
        "success": vote_status == 201,
        "duplicate_rejected": duplicate_status == 409,
        "vote_value": vote_value,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }


def run_level(level: int) -> dict[str, object]:
    with running_server(voter_count=level) as (base_url, _temp_root):
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(execute_voter, base_url, index) for index in range(1, level + 1)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        total_elapsed = time.perf_counter() - started
        latencies = [float(result["latency_ms"]) for result in results]
        successes = sum(1 for result in results if result["success"])
        failures = level - successes
        duplicate_rejections = sum(1 for result in results if result.get("duplicate_rejected"))
        expected_yes = sum(1 for result in results if result.get("vote_value") == "yes")
        expected_no = sum(1 for result in results if result.get("vote_value") == "no")
        _, tally_payload = get_json(base_url, f"/tally?event_id={ACTIVE_EVENT_ID}")

    return {
        "concurrency_level": level,
        "status": "completed",
        "average_request_latency_ms": round(sum(latencies) / max(len(latencies), 1), 6),
        "minimum_latency_ms": round(min(latencies), 6),
        "maximum_latency_ms": round(max(latencies), 6),
        "throughput_ballots_per_second": round(successes / max(total_elapsed, 1e-9), 6),
        "success_rate": round(successes / max(level, 1), 6),
        "failure_rate": round(failures / max(level, 1), 6),
        "duplicate_rejection_correctness": duplicate_rejections == successes,
        "final_tally_correctness": tally_payload["yes"] == expected_yes
        and tally_payload["no"] == expected_no
        and tally_payload["total_ballots_cast"] == successes,
    }


def main() -> int:
    args = parse_args()
    results: list[dict[str, object]] = []
    started_at = time.perf_counter()
    average_latency_ms_hint = 0.0

    for level in DEFAULT_LEVELS:
        elapsed = time.perf_counter() - started_at
        projected = (level * average_latency_ms_hint) / 1000.0 if average_latency_ms_hint else 0.0
        if average_latency_ms_hint and elapsed + projected > args.max_seconds:
            results.append(
                {
                    "concurrency_level": level,
                    "status": "skipped",
                    "reason": f"projected runtime exceeds {args.max_seconds:.0f} seconds",
                }
            )
            continue
        result = run_level(level)
        results.append(result)
        average_latency_ms_hint = float(result["average_request_latency_ms"])

    payload = {
        "benchmark": "concurrent_voting_stress_test",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "requested_concurrency_levels": DEFAULT_LEVELS,
        "max_seconds": args.max_seconds,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
