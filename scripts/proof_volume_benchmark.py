from __future__ import annotations

import argparse
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark_support import BACKEND_DIR, ensure_results_dir

import sys

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import PROOF_BINARY_PATH, PROOF_ENGINE_DIR  # noqa: E402
from proof_runtime import prove_and_verify, write_json  # noqa: E402
from verifiability import (  # noqa: E402
    build_public_inputs,
    derive_nullifier,
    derive_vote_commitment,
    field_element_to_hex,
)


DEFAULT_SCALES = [1_000, 10_000, 100_000, 1_000_000]
DEFAULT_MAX_SECONDS = 180.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run proof-engine volume benchmarks.")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    parser.add_argument(
        "--output",
        type=Path,
        default=ensure_results_dir() / "proof_volume_benchmark.json",
    )
    return parser.parse_args()


def projected_seconds(scale: int, average_cycle_ms: float) -> float:
    return (scale * average_cycle_ms) / 1000.0


def run_scale(scale: int) -> dict[str, object]:
    vote_pattern = ["yes", "no"]
    vote_values = {"yes": 1, "no": 0}
    voter_secret = field_element_to_hex(987654321)
    event_id = "diaspora-referendum-2026"
    generation_total_ms = 0.0
    verification_total_ms = 0.0
    success_count = 0
    failure_count = 0
    proof_sizes: list[int] = []

    with tempfile.TemporaryDirectory(prefix="diasporavote-proof-volume-") as temp_name:
        temp_dir = Path(temp_name)
        for index in range(scale):
            vote_label = vote_pattern[index % len(vote_pattern)]
            vote_value = vote_values[vote_label]
            ballot_salt = field_element_to_hex(index + 1)
            _, nullifier = derive_nullifier(987654321, event_id)
            vote_commitment = derive_vote_commitment(vote_value, int(ballot_salt, 16))
            prove_input_path = temp_dir / f"prove-{index}.json"
            verify_input_path = temp_dir / f"verify-{index}.json"
            proof_path = temp_dir / f"proof-{index}.bin"

            write_json(
                prove_input_path,
                {
                    "vote_value": vote_value,
                    "registered_flag": 1,
                    "already_voted_flag": 0,
                    "event_id": event_id,
                    "voter_secret": voter_secret,
                    "ballot_salt": ballot_salt,
                },
            )
            write_json(
                verify_input_path,
                build_public_inputs(
                    event_id=event_id,
                    nullifier=nullifier,
                    vote_commitment=vote_commitment,
                ),
            )
            try:
                result = prove_and_verify(
                    binary_path=Path(PROOF_BINARY_PATH),
                    proof_dir=Path(PROOF_ENGINE_DIR),
                    prove_input_path=prove_input_path,
                    verify_input_path=verify_input_path,
                    proof_path=proof_path,
                )
            except Exception:
                failure_count += 1
                continue

            success_count += 1
            generation_total_ms += float(result["prove_output"]["proof_generation_ms"])
            verification_total_ms += float(result["verify_output"]["proof_verification_ms"])
            proof_sizes.append(int(result["prove_output"]["proof_size_bytes"]))

    average_size = (sum(proof_sizes) / len(proof_sizes)) if proof_sizes else 0.0
    return {
        "scale": scale,
        "status": "completed",
        "total_proof_generation_time_ms": round(generation_total_ms, 6),
        "average_proof_generation_time_ms": round(generation_total_ms / max(success_count, 1), 6),
        "total_proof_verification_time_ms": round(verification_total_ms, 6),
        "average_proof_verification_time_ms": round(
            verification_total_ms / max(success_count, 1), 6
        ),
        "proof_size_bytes": round(average_size, 3),
        "total_proof_storage_estimate_bytes": int(round(average_size * success_count)),
        "success_rate": round(success_count / max(scale, 1), 6),
        "failure_rate": round(failure_count / max(scale, 1), 6),
        "successful_proofs": success_count,
        "failed_proofs": failure_count,
    }


def main() -> int:
    args = parse_args()
    started_at = time.perf_counter()
    results: list[dict[str, object]] = []
    average_cycle_ms_hint = 0.0

    for scale in DEFAULT_SCALES:
        elapsed = time.perf_counter() - started_at
        if average_cycle_ms_hint and elapsed + projected_seconds(scale, average_cycle_ms_hint) > args.max_seconds:
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
        average_cycle_ms_hint = (
            result["average_proof_generation_time_ms"] + result["average_proof_verification_time_ms"]
        )

    payload = {
        "benchmark": "proof_volume_benchmark",
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
