from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


class ProofRuntimeError(RuntimeError):
    pass


def is_executable(binary_path: Path) -> bool:
    return binary_path.exists() and (os.name == "nt" or os.access(binary_path, os.X_OK))


def ensure_binary(binary_path: Path, proof_dir: Path) -> Path:
    if is_executable(binary_path):
        return binary_path

    cargo_path = shutil.which("cargo")
    if cargo_path is None:
        raise ProofRuntimeError("cargo is not installed or not available on PATH")

    try:
        result = subprocess.run(
            [cargo_path, "build", "--release"],
            cwd=proof_dir,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ProofRuntimeError("cargo is not installed or not available on PATH") from exc
    if result.returncode != 0:
        raise ProofRuntimeError(result.stderr.strip() or result.stdout.strip() or "cargo build failed")
    if not is_executable(binary_path):
        raise ProofRuntimeError("proof binary not found")
    return binary_path


def run_command(args: list[str]) -> str:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProofRuntimeError(result.stderr.strip() or result.stdout.strip() or "proof command failed")
    return result.stdout


def artifact_hash_from_path(proof_path: Path) -> str:
    return hashlib.sha256(proof_path.read_bytes()).hexdigest()


def parse_key_value_output(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def prove_and_verify(
    *,
    binary_path: Path,
    proof_dir: Path,
    prove_input_path: Path,
    verify_input_path: Path,
    proof_path: Path,
) -> dict[str, object]:
    resolved_binary = ensure_binary(binary_path, proof_dir)
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    prove_output = run_command([str(resolved_binary), "prove", str(prove_input_path), str(proof_path)])
    verify_output = run_command(
        [str(resolved_binary), "verify", str(verify_input_path), str(proof_path)]
    )
    if "verified=true" not in verify_output:
        raise ProofRuntimeError("proof verification output missing verified=true")

    return {
        "proof_hash": artifact_hash_from_path(proof_path),
        "prove_output": parse_key_value_output(prove_output),
        "verify_output": parse_key_value_output(verify_output),
    }


def verify_only(
    *,
    binary_path: Path,
    proof_dir: Path,
    verify_input_path: Path,
    proof_path: Path,
) -> dict[str, object]:
    resolved_binary = ensure_binary(binary_path, proof_dir)
    verify_output = run_command(
        [str(resolved_binary), "verify", str(verify_input_path), str(proof_path)]
    )
    if "verified=true" not in verify_output:
        raise ProofRuntimeError("proof verification failed")
    return {
        "proof_hash": artifact_hash_from_path(proof_path),
        "verify_output": parse_key_value_output(verify_output),
    }
