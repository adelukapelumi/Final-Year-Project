from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


DEFAULT_ITERATIONS = 30
DEFAULT_WARMUP_RUNS = 3
PROJECT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_DIR / "benchmarks" / "results"
BINARY_NAME = (
    "referendum_acceptance_winterfell.exe"
    if sys.platform.startswith("win")
    else "referendum_acceptance_winterfell"
)
BINARY_PATH = PROJECT_DIR / "target" / "release" / BINARY_NAME
BALLOT_CASES = (("Yes", 1), ("No", 0))


class BenchmarkError(RuntimeError):
    pass


@dataclass(frozen=True)
class Measurement:
    generation_time_ms: float
    verification_time_ms: float
    proof_size_bytes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the Winterfell binary referendum proof engine."
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Measured runs for each ballot value (minimum {DEFAULT_ITERATIONS}).",
    )
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=DEFAULT_WARMUP_RUNS,
        help=f"Discarded warm-up runs for each ballot value (minimum {DEFAULT_WARMUP_RUNS}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS_DIR / "benchmark_results.json",
        help="JSON result file. A CSV summary is written beside it.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Use the existing release binary without running cargo build.",
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
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise BenchmarkError(f"proof engine command failed: {detail}")
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


def read_float_metric(output: dict[str, str], key: str) -> float:
    try:
        value = float(output[key])
    except (KeyError, ValueError) as error:
        raise BenchmarkError(f"proof engine output is missing a valid {key} metric") from error
    if not math.isfinite(value) or value < 0:
        raise BenchmarkError(f"proof engine returned an invalid {key} metric")
    return value


def ensure_release_binary(skip_build: bool) -> str:
    cargo_path = shutil.which("cargo")
    if cargo_path is None:
        raise BenchmarkError("cargo is not installed or not available on PATH")

    cargo_version = run_command([cargo_path, "--version"]).stdout.strip()
    if not skip_build:
        print("Building the Winterfell proof engine in release mode...")
        run_command([cargo_path, "build", "--release"], cwd=PROJECT_DIR)

    if not BINARY_PATH.is_file():
        raise BenchmarkError("the Winterfell release binary was not produced")

    return cargo_version


def execute_proof_cycle(
    binary_path: Path,
    input_path: Path,
    proof_path: Path,
) -> Measurement:
    prove_result = run_command(
        [str(binary_path), "prove", str(input_path), str(proof_path)]
    )
    prove_output = parse_key_value_output(prove_result.stdout)
    if not proof_path.is_file():
        raise BenchmarkError("the proof engine did not create a proof")

    verify_result = run_command(
        [str(binary_path), "verify", str(input_path), str(proof_path)]
    )
    verify_output = parse_key_value_output(verify_result.stdout)
    if verify_output.get("verified") != "true":
        raise BenchmarkError("the proof engine did not report successful verification")

    proof_size = proof_path.stat().st_size
    try:
        reported_size = int(prove_output["proof_size_bytes"])
    except (KeyError, ValueError) as error:
        raise BenchmarkError(
            "proof engine output is missing a valid proof_size_bytes metric"
        ) from error
    if reported_size != proof_size:
        raise BenchmarkError("the reported proof size does not match the proof file")

    return Measurement(
        generation_time_ms=read_float_metric(
            prove_output, "proof_generation_ms"
        ),
        verification_time_ms=read_float_metric(
            verify_output, "proof_verification_ms"
        ),
        proof_size_bytes=proof_size,
    )


def metric_summary(values: list[float | int], precision: int = 6) -> dict[str, float | int]:
    return {
        "average": round(mean(values), precision),
        "minimum": round(min(values), precision),
        "maximum": round(max(values), precision),
    }


def summarize_case(
    ballot_case: str,
    measurements: list[Measurement],
) -> dict[str, object]:
    generation_times = [item.generation_time_ms for item in measurements]
    verification_times = [item.verification_time_ms for item in measurements]
    proof_sizes = [item.proof_size_bytes for item in measurements]

    return {
        "synthetic_ballot_case": ballot_case,
        "run_count": len(measurements),
        "generation_time_ms": metric_summary(generation_times),
        "verification_time_ms": metric_summary(verification_times),
        "proof_size_bytes": metric_summary(proof_sizes, precision=3),
    }


def benchmark_case(
    ballot_case: str,
    vote_value: int,
    iterations: int,
    warmup_runs: int,
    binary_path: Path,
    temporary_dir: Path,
) -> dict[str, object]:
    case_name = ballot_case.lower()
    input_path = temporary_dir / f"{case_name}.json"
    proof_path = temporary_dir / f"{case_name}.proof.bin"
    input_path.write_text(
        json.dumps(
            {
                "vote_value": vote_value,
                "registered_flag": 1,
                "already_voted_flag": 0,
            }
        ),
        encoding="utf-8",
    )

    print(
        f"Running {ballot_case}: {warmup_runs} warm-up runs, "
        f"then {iterations} measured runs..."
    )
    for _ in range(warmup_runs):
        execute_proof_cycle(binary_path, input_path, proof_path)

    measurements = [
        execute_proof_cycle(binary_path, input_path, proof_path)
        for _ in range(iterations)
    ]
    return summarize_case(ballot_case, measurements)


def write_csv(path: Path, results: list[dict[str, object]]) -> None:
    fieldnames = [
        "synthetic_ballot_case",
        "run_count",
        "generation_time_ms_average",
        "generation_time_ms_minimum",
        "generation_time_ms_maximum",
        "verification_time_ms_average",
        "verification_time_ms_minimum",
        "verification_time_ms_maximum",
        "proof_size_bytes_average",
        "proof_size_bytes_minimum",
        "proof_size_bytes_maximum",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            generation = result["generation_time_ms"]
            verification = result["verification_time_ms"]
            proof_size = result["proof_size_bytes"]
            writer.writerow(
                {
                    "synthetic_ballot_case": result["synthetic_ballot_case"],
                    "run_count": result["run_count"],
                    "generation_time_ms_average": generation["average"],
                    "generation_time_ms_minimum": generation["minimum"],
                    "generation_time_ms_maximum": generation["maximum"],
                    "verification_time_ms_average": verification["average"],
                    "verification_time_ms_minimum": verification["minimum"],
                    "verification_time_ms_maximum": verification["maximum"],
                    "proof_size_bytes_average": proof_size["average"],
                    "proof_size_bytes_minimum": proof_size["minimum"],
                    "proof_size_bytes_maximum": proof_size["maximum"],
                }
            )


def print_report(results: list[dict[str, object]]) -> None:
    print("\nWinterfell zk-STARK proof benchmark")
    print("=" * 39)
    for result in results:
        generation = result["generation_time_ms"]
        verification = result["verification_time_ms"]
        proof_size = result["proof_size_bytes"]
        print(f"\nSynthetic ballot: {result['synthetic_ballot_case']}")
        print(f"Measured runs: {result['run_count']}")
        print(
            "Generation time (ms): "
            f"avg {generation['average']:.3f}, "
            f"min {generation['minimum']:.3f}, "
            f"max {generation['maximum']:.3f}"
        )
        print(
            "Verification time (ms): "
            f"avg {verification['average']:.3f}, "
            f"min {verification['minimum']:.3f}, "
            f"max {verification['maximum']:.3f}"
        )
        print(
            "Proof size (bytes): "
            f"avg {proof_size['average']:.3f}, "
            f"min {proof_size['minimum']}, "
            f"max {proof_size['maximum']}"
        )


def display_path(path: Path) -> Path:
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(Path.cwd().resolve())
    except ValueError:
        return resolved_path


def main() -> int:
    args = parse_args()
    if args.iterations < DEFAULT_ITERATIONS:
        raise BenchmarkError(
            f"--iterations must be at least {DEFAULT_ITERATIONS}"
        )
    if args.warmup_runs < DEFAULT_WARMUP_RUNS:
        raise BenchmarkError(
            f"--warmup-runs must be at least {DEFAULT_WARMUP_RUNS}"
        )

    cargo_version = ensure_release_binary(skip_build=args.skip_build)
    output_path = args.output.resolve()
    csv_path = output_path.with_suffix(".csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="evoting-proof-benchmark-") as temp_name:
        temporary_dir = Path(temp_name)
        results = [
            benchmark_case(
                ballot_case=ballot_case,
                vote_value=vote_value,
                iterations=args.iterations,
                warmup_runs=args.warmup_runs,
                binary_path=BINARY_PATH,
                temporary_dir=temporary_dir,
            )
            for ballot_case, vote_value in BALLOT_CASES
        ]

    payload = {
        "benchmark": "Winterfell binary referendum proof engine",
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "configuration": {
            "measured_iterations_per_ballot": args.iterations,
            "warmup_runs_per_ballot": args.warmup_runs,
            "warmup_runs_excluded": True,
            "timing_source": "Winterfell engine internal high-resolution timer",
            "cargo_version": cargo_version,
            "database_accessed": False,
            "proof_artifacts_retained": False,
        },
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, results)

    print_report(results)
    print(f"\nJSON results saved to: {display_path(output_path)}")
    print(f"CSV results saved to:  {display_path(csv_path)}")
    print("Temporary synthetic inputs and proofs were deleted; no database was used.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BenchmarkError as error:
        print(f"Benchmark failed: {error}", file=sys.stderr)
        raise SystemExit(1)
