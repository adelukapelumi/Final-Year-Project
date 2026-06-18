from __future__ import annotations

import uuid
from pathlib import Path

from flask import current_app

from proof_runtime import (
    ProofRuntimeError,
    ensure_binary,
    is_executable,
    prove_and_verify,
    verify_only,
    write_json,
)
from verifiability import build_public_inputs


class ProofClientError(RuntimeError):
    pass


def proof_binary_available() -> bool:
    return is_executable(Path(current_app.config["PROOF_BINARY_PATH"]))


def generate_and_verify_proof(
    *,
    vote_value: int,
    registered_flag: int,
    already_voted_flag: int,
    voter_secret: str,
    ballot_salt: str,
    event_id: str,
    nullifier: str,
    vote_commitment: str,
) -> dict:
    binary_path = Path(current_app.config["PROOF_BINARY_PATH"])
    proof_dir = Path(current_app.config["PROOF_ENGINE_DIR"])
    artifacts_dir = Path(current_app.config["PROOF_ARTIFACTS_DIR"])
    inputs_dir = Path(current_app.config["PROOF_INPUTS_DIR"])
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    artifact_id = uuid.uuid4().hex
    prove_input_path = inputs_dir / f"{artifact_id}.json"
    verify_input_path = inputs_dir / f"verify-{artifact_id}.json"
    proof_path = artifacts_dir / f"{artifact_id}.proof.bin"
    public_inputs = build_public_inputs(
        event_id=event_id,
        nullifier=nullifier,
        vote_commitment=vote_commitment,
    )
    write_json(
        prove_input_path,
        {
            "vote_value": int(vote_value),
            "registered_flag": int(registered_flag),
            "already_voted_flag": int(already_voted_flag),
            "event_id": str(event_id),
            "voter_secret": str(voter_secret),
            "ballot_salt": str(ballot_salt),
        },
    )
    write_json(verify_input_path, public_inputs)
    try:
        result = prove_and_verify(
            binary_path=binary_path,
            proof_dir=proof_dir,
            prove_input_path=prove_input_path,
            verify_input_path=verify_input_path,
            proof_path=proof_path,
        )
    except ProofRuntimeError as exc:
        raise ProofClientError(str(exc)) from exc

    return {
        "proof_path": str(proof_path),
        "proof_hash": str(result["proof_hash"]),
        "public_inputs": public_inputs,
        "proof_metrics": {
            "generation_ms": result["prove_output"].get("proof_generation_ms"),
            "verification_ms": result["verify_output"].get("proof_verification_ms"),
            "proof_size_bytes": result["prove_output"].get("proof_size_bytes"),
        },
    }


def verify_existing_proof(public_inputs: dict, proof_path: str) -> dict:
    binary_path = Path(current_app.config["PROOF_BINARY_PATH"])
    proof_dir = Path(current_app.config["PROOF_ENGINE_DIR"])
    inputs_dir = Path(current_app.config["PROOF_INPUTS_DIR"])
    inputs_dir.mkdir(parents=True, exist_ok=True)

    artifact_id = uuid.uuid4().hex
    input_path = inputs_dir / f"verify-{artifact_id}.json"
    write_json(input_path, public_inputs)
    try:
        result = verify_only(
            binary_path=binary_path,
            proof_dir=proof_dir,
            verify_input_path=input_path,
            proof_path=Path(proof_path),
        )
    except ProofRuntimeError as exc:
        raise ProofClientError(str(exc)) from exc
    return {
        "verified": True,
        "proof_hash": str(result["proof_hash"]),
        "verification_ms": result["verify_output"].get("proof_verification_ms"),
    }
