from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

from proof_runtime import ProofRuntimeError, verify_only, write_json
from verifiability import (
    build_public_ballot_record,
    build_public_inputs,
    compute_chain_hash,
    compute_public_record_hash,
    sha256_hex,
)


def load_bundle(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decode_proof_artifact(bundle: dict) -> bytes:
    return base64.b64decode(bundle["proof_artifact_base64"])


def proof_hash_matches(bundle: dict) -> bool:
    return sha256_hex(decode_proof_artifact(bundle)) == bundle.get("proof_hash")


def expected_public_record(bundle: dict) -> dict[str, str]:
    return build_public_ballot_record(
        ballot_id=bundle["ballot_id"],
        event_id=bundle["event_id"],
        event_title=bundle["event_title"],
        nullifier=bundle["nullifier"],
        vote_commitment=bundle["vote_commitment"],
        proof_hash=bundle["proof_hash"],
        timestamp=bundle["timestamp"],
        verification_status=bundle["verification_status"],
    )


def receipt_consistency_passes(bundle: dict) -> bool:
    public_inputs = bundle.get("public_inputs", {})
    expected_inputs = build_public_inputs(
        event_id=bundle["event_id"],
        nullifier=bundle["nullifier"],
        vote_commitment=bundle["vote_commitment"],
    )
    if public_inputs != expected_inputs:
        return False

    metadata = bundle.get("verification_metadata", {})
    public_record = expected_public_record(bundle)
    if metadata.get("public_record") != public_record:
        return False
    current_record_hash = metadata.get("current_record_hash")
    if current_record_hash and current_record_hash != compute_public_record_hash(public_record):
        return False
    return True


def chain_hash_passes(bundle: dict) -> bool:
    public_record = expected_public_record(bundle)
    expected_chain_hash = compute_chain_hash(bundle["previous_chain_hash"], public_record)
    if expected_chain_hash != bundle.get("chain_hash"):
        return False
    current_record_hash = bundle.get("verification_metadata", {}).get("current_record_hash")
    if current_record_hash and current_record_hash != compute_public_record_hash(public_record):
        return False
    return True


def verify_proof_from_bundle(
    *,
    bundle: dict,
    proof_binary_path: Path,
    proof_engine_dir: Path,
) -> bool:
    with tempfile.TemporaryDirectory(prefix="diasporavote-bundle-verify-") as temp_name:
        temp_dir = Path(temp_name)
        proof_path = temp_dir / "bundle.proof.bin"
        verify_input_path = temp_dir / "bundle.verify.json"
        proof_path.write_bytes(decode_proof_artifact(bundle))
        write_json(verify_input_path, bundle["public_inputs"])
        try:
            verify_only(
                binary_path=proof_binary_path,
                proof_dir=proof_engine_dir,
                verify_input_path=verify_input_path,
                proof_path=proof_path,
            )
        except ProofRuntimeError:
            return False
    return True
