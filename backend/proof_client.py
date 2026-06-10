from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from flask import current_app


class ProofClientError(RuntimeError):
    pass


def _is_executable(binary_path: Path) -> bool:
    return binary_path.exists() and (os.name == "nt" or os.access(binary_path, os.X_OK))


def proof_binary_available() -> bool:
    return _is_executable(Path(current_app.config["PROOF_BINARY_PATH"]))


def _build_binary() -> Path:
    binary_path = Path(current_app.config["PROOF_BINARY_PATH"])
    if _is_executable(binary_path):
        return binary_path

    cargo_path = shutil.which("cargo")
    if cargo_path is None:
        raise ProofClientError("cargo is not installed or not available on PATH")

    proof_dir = Path(current_app.config["PROOF_ENGINE_DIR"])
    try:
        result = subprocess.run(
            [cargo_path, "build", "--release"],
            cwd=proof_dir,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ProofClientError("cargo is not installed or not available on PATH") from exc
    if result.returncode != 0:
        raise ProofClientError(result.stderr.strip() or result.stdout.strip() or "cargo build failed")
    if not _is_executable(binary_path):
        raise ProofClientError("proof binary not found")
    return binary_path


def _run_command(args: list[str]) -> str:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProofClientError(result.stderr.strip() or result.stdout.strip() or "proof command failed")
    return result.stdout


def _artifact_receipt_hash(proof_path: Path) -> str:
    return hashlib.sha256(proof_path.read_bytes()).hexdigest()


def generate_and_verify_proof(vote_value: int, registered_flag: int, already_voted_flag: int) -> dict:
    binary_path = _build_binary()
    artifacts_dir = Path(current_app.config["PROOF_ARTIFACTS_DIR"])
    inputs_dir = Path(current_app.config["PROOF_INPUTS_DIR"])
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    artifact_id = uuid.uuid4().hex
    input_path = inputs_dir / f"{artifact_id}.json"
    proof_path = artifacts_dir / f"{artifact_id}.proof.bin"

    public_inputs = {
        "vote_value": int(vote_value),
        "registered_flag": int(registered_flag),
        "already_voted_flag": int(already_voted_flag),
        "accepted": 1,
    }
    input_path.write_text(
        json.dumps(
            {
                "vote_value": public_inputs["vote_value"],
                "registered_flag": public_inputs["registered_flag"],
                "already_voted_flag": public_inputs["already_voted_flag"],
            }
        ),
        encoding="utf-8",
    )

    _run_command([str(binary_path), "prove", str(input_path), str(proof_path)])
    verify_output = _run_command([str(binary_path), "verify", str(input_path), str(proof_path)])
    if "verified=true" not in verify_output:
        raise ProofClientError("proof verification output missing verified=true")

    return {
        "proof_path": str(proof_path),
        "proof_hash": _artifact_receipt_hash(proof_path),
        "public_inputs": public_inputs,
    }


def verify_existing_proof(public_inputs: dict, proof_path: str) -> dict:
    binary_path = _build_binary()
    inputs_dir = Path(current_app.config["PROOF_INPUTS_DIR"])
    inputs_dir.mkdir(parents=True, exist_ok=True)

    artifact_id = uuid.uuid4().hex
    input_path = inputs_dir / f"verify-{artifact_id}.json"
    input_path.write_text(
        json.dumps(
            {
                "vote_value": int(public_inputs["vote_value"]),
                "registered_flag": int(public_inputs["registered_flag"]),
                "already_voted_flag": int(public_inputs["already_voted_flag"]),
            }
        ),
        encoding="utf-8",
    )
    output = _run_command([str(binary_path), "verify", str(input_path), str(proof_path)])
    verified = "verified=true" in output
    if not verified:
        raise ProofClientError("proof verification failed")
    return {"verified": True, "proof_hash": _artifact_receipt_hash(Path(proof_path))}
