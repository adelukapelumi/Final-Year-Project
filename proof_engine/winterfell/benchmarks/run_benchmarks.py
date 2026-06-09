from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter_ns


DEFAULT_BALLOT_COUNTS = (1, 10, 100)
PROJECT_DIR = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = PROJECT_DIR / "benchmarks"
ARTIFACTS_DIR = BENCHMARKS_DIR / "artifacts"
RESULTS_DIR = BENCHMARKS_DIR / "results"
ARCHIVE_DIR = RESULTS_DIR / "archive"
BINARY_NAME = "referendum_acceptance_winterfell.exe" if sys.platform.startswith("win") else "referendum_acceptance_winterfell"
BINARY_PATH = PROJECT_DIR / "target" / "release" / BINARY_NAME


class BenchmarkError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the real Winterfell accepted-ballot proof path."
    )
    parser.add_argument(
        "--counts",
        metavar="N",
        nargs="+",
        type=int,
        default=list(DEFAULT_BALLOT_COUNTS),
        help="Ballot counts to benchmark. Defaults to 1 10 100.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip cargo build and use the existing release binary.",
    )
    return parser.parse_args()


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        command_text = " ".join(args)
        raise BenchmarkError(
            f"command failed ({command_text}): "
            f"{result.stderr.strip() or result.stdout.strip() or 'no output'}"
        )
    return result


def parse_key_value_output(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def ensure_release_binary(skip_build: bool) -> dict[str, str | Path]:
    cargo_path = shutil.which("cargo")
    if cargo_path is None:
        raise BenchmarkError("cargo is not installed or not available on PATH")

    cargo_version = run_command([cargo_path, "--version"]).stdout.strip()

    if not skip_build:
        run_command([cargo_path, "build", "--release"], cwd=PROJECT_DIR)

    if not BINARY_PATH.exists():
        raise BenchmarkError(f"expected benchmark binary at {BINARY_PATH}")

    return {
        "cargo_path": cargo_path,
        "cargo_version": cargo_version,
        "binary_path": BINARY_PATH,
    }


def ballot_input(ballot_index: int) -> dict[str, int]:
    return {
        "vote_value": 1 if ballot_index % 2 == 0 else 0,
        "registered_flag": 1,
        "already_voted_flag": 0,
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_case(ballot_count: int, runs: list[dict[str, object]]) -> dict[str, object]:
    generation_times = [float(run["generation_time_ms"]) for run in runs]
    verification_times = [float(run["verification_time_ms"]) for run in runs]
    proof_sizes = [int(run["proof_size_bytes"]) for run in runs]
    engine_generation_times = [
        float(run["engine_reported_generation_ms"]) for run in runs
    ]
    engine_verification_times = [
        float(run["engine_reported_verification_ms"]) for run in runs
    ]

    return {
        "ballot_count": ballot_count,
        "proofs_generated": len(runs),
        "proofs_verified": len(runs),
        "generation_time_ms_total": round(sum(generation_times), 3),
        "generation_time_ms_average": round(mean(generation_times), 3),
        "generation_time_ms_min": round(min(generation_times), 3),
        "generation_time_ms_max": round(max(generation_times), 3),
        "verification_time_ms_total": round(sum(verification_times), 3),
        "verification_time_ms_average": round(mean(verification_times), 3),
        "verification_time_ms_min": round(min(verification_times), 3),
        "verification_time_ms_max": round(max(verification_times), 3),
        "proof_size_bytes_total": sum(proof_sizes),
        "proof_size_bytes_average": round(mean(proof_sizes), 3),
        "proof_size_bytes_min": min(proof_sizes),
        "proof_size_bytes_max": max(proof_sizes),
        "engine_reported_generation_ms_total": round(sum(engine_generation_times), 3),
        "engine_reported_generation_ms_average": round(mean(engine_generation_times), 3),
        "engine_reported_verification_ms_total": round(sum(engine_verification_times), 3),
        "engine_reported_verification_ms_average": round(mean(engine_verification_times), 3),
    }


def benchmark_case(ballot_count: int, binary_path: Path, artifact_root: Path) -> dict[str, object]:
    case_dir = artifact_root / f"{ballot_count}_ballots"
    case_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, object]] = []
    for ballot_index in range(ballot_count):
        ballot_number = ballot_index + 1
        input_payload = ballot_input(ballot_index)
        input_path = case_dir / f"ballot_{ballot_number:03d}.input.json"
        proof_path = case_dir / f"ballot_{ballot_number:03d}.proof.bin"
        input_path.write_text(json.dumps(input_payload), encoding="utf-8")

        prove_started = perf_counter_ns()
        prove_result = run_command([str(binary_path), "prove", str(input_path), str(proof_path)])
        generation_time_ms = round((perf_counter_ns() - prove_started) / 1_000_000, 3)
        prove_output = parse_key_value_output(prove_result.stdout)

        if not proof_path.exists():
            raise BenchmarkError(f"proof file was not created: {proof_path}")

        verify_started = perf_counter_ns()
        verify_result = run_command([str(binary_path), "verify", str(input_path), str(proof_path)])
        verification_time_ms = round((perf_counter_ns() - verify_started) / 1_000_000, 3)
        verify_output = parse_key_value_output(verify_result.stdout)

        if verify_output.get("verified") != "true":
            raise BenchmarkError(f"proof verification did not report success for {proof_path}")

        actual_proof_size = proof_path.stat().st_size
        reported_proof_size = int(prove_output.get("proof_size_bytes", actual_proof_size))
        if reported_proof_size != actual_proof_size:
            raise BenchmarkError(
                f"reported proof size {reported_proof_size} did not match actual size {actual_proof_size}"
            )

        runs.append(
            {
                "ballot_index": ballot_number,
                "vote_value": input_payload["vote_value"],
                "registered_flag": input_payload["registered_flag"],
                "already_voted_flag": input_payload["already_voted_flag"],
                "generation_time_ms": generation_time_ms,
                "verification_time_ms": verification_time_ms,
                "engine_reported_generation_ms": float(prove_output.get("proof_generation_ms", "0")),
                "engine_reported_verification_ms": float(
                    verify_output.get("proof_verification_ms", "0")
                ),
                "proof_size_bytes": actual_proof_size,
                "proof_sha256": sha256_file(proof_path),
                "input_path": str(input_path.relative_to(PROJECT_DIR)),
                "proof_path": str(proof_path.relative_to(PROJECT_DIR)),
            }
        )

    summary = summarize_case(ballot_count, runs)
    return {"ballot_count": ballot_count, "summary": summary, "runs": runs}


def write_summary_csv(path: Path, cases: list[dict[str, object]]) -> None:
    fieldnames = [
        "ballot_count",
        "proofs_generated",
        "proofs_verified",
        "generation_time_ms_total",
        "generation_time_ms_average",
        "generation_time_ms_min",
        "generation_time_ms_max",
        "verification_time_ms_total",
        "verification_time_ms_average",
        "verification_time_ms_min",
        "verification_time_ms_max",
        "proof_size_bytes_total",
        "proof_size_bytes_average",
        "proof_size_bytes_min",
        "proof_size_bytes_max",
        "engine_reported_generation_ms_total",
        "engine_reported_generation_ms_average",
        "engine_reported_verification_ms_total",
        "engine_reported_verification_ms_average",
    ]

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            writer.writerow(case["summary"])


def main() -> int:
    args = parse_args()
    counts = [count for count in args.counts if count > 0]
    if not counts:
        raise BenchmarkError("at least one positive ballot count is required")

    binary_info = ensure_release_binary(skip_build=args.skip_build)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_root = ARTIFACTS_DIR / timestamp
    artifact_root.mkdir(parents=True, exist_ok=True)

    cases = [
        benchmark_case(ballot_count=count, binary_path=BINARY_PATH, artifact_root=artifact_root)
        for count in counts
    ]

    payload = {
        "generated_at_utc": timestamp,
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cargo_version": binary_info["cargo_version"],
            "binary_path": str(Path(binary_info["binary_path"]).resolve()),
            "project_dir": str(PROJECT_DIR.resolve()),
            "artifact_root": str(artifact_root.resolve()),
        },
        "benchmark_cases": cases,
    }

    latest_json_path = RESULTS_DIR / "benchmark_results.json"
    latest_csv_path = RESULTS_DIR / "benchmark_results.csv"
    archive_json_path = ARCHIVE_DIR / f"benchmark_results_{timestamp}.json"
    archive_csv_path = ARCHIVE_DIR / f"benchmark_results_{timestamp}.csv"

    json_text = json.dumps(payload, indent=2)
    latest_json_path.write_text(json_text + "\n", encoding="utf-8")
    archive_json_path.write_text(json_text + "\n", encoding="utf-8")
    write_summary_csv(latest_csv_path, cases)
    write_summary_csv(archive_csv_path, cases)

    print(f"saved_json={latest_json_path}")
    print(f"saved_csv={latest_csv_path}")
    print(f"saved_archive_json={archive_json_path}")
    print(f"saved_archive_csv={archive_csv_path}")

    for case in cases:
        summary = case["summary"]
        print(
            "ballot_count={ballot_count} generation_time_ms_total={generation_time_ms_total} "
            "verification_time_ms_total={verification_time_ms_total} proof_size_bytes_total={proof_size_bytes_total}".format(
                **summary
            )
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BenchmarkError as error:
        print(f"error={error}", file=sys.stderr)
        raise SystemExit(1)
