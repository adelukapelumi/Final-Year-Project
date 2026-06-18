from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any


FIELD_MODULUS = 340282366920938463463374557953744961537
FIELD_HEX_LENGTH = 32
NULLIFIER_DOMAIN = 101
COMMITMENT_DOMAIN = 202
BOARD_CHAIN_GENESIS_HASH = hashlib.sha256(
    b"diasporavote-public-board-genesis-v1"
).hexdigest()
PROTOCOL_VERSION = "diasporavote-stark-nullifier-v1"


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def encode_event_id_to_field(event_id: str) -> int:
    accumulator = 0
    for byte in str(event_id).encode("utf-8"):
        accumulator = (accumulator * 257 + byte + 1) % FIELD_MODULUS
    return accumulator


def _normalize_field_element(value: int) -> int:
    return int(value) % FIELD_MODULUS


def field_element_to_hex(value: int) -> str:
    normalized = _normalize_field_element(value)
    return f"0x{normalized:0{FIELD_HEX_LENGTH}x}"


def parse_field_element(value: int | str) -> int:
    if isinstance(value, int):
        return _normalize_field_element(value)
    text = str(value or "").strip()
    if not text:
        raise ValueError("field element is required")
    base = 16 if text.lower().startswith("0x") else 10
    return _normalize_field_element(int(text, base))


def random_field_element() -> int:
    return secrets.randbelow(FIELD_MODULUS - 1) + 1


def derive_voter_secret(secret_key: str, nin_hash: str) -> int:
    seed = hashlib.sha256(
        f"diasporavote:voter-secret:{secret_key}:{nin_hash}".encode("utf-8")
    ).digest()
    return (int.from_bytes(seed[:16], "big") % (FIELD_MODULUS - 1)) + 1


def voter_secret_hash(secret_value: int) -> str:
    return sha256_hex(field_element_to_hex(secret_value).encode("utf-8"))


def prototype_field_hash(left: int, right: int, domain: int) -> int:
    x = _normalize_field_element(left + domain)
    y = _normalize_field_element(right + domain + 1)
    z = _normalize_field_element(left + right + domain + 2)
    return _normalize_field_element(
        pow(x, 3, FIELD_MODULUS)
        + 5 * pow(y, 3, FIELD_MODULUS)
        + 7 * pow(z, 3, FIELD_MODULUS)
        + 11 * x * y
        + 13 * y * z
        + 17 * x * z
        + 19 * domain
    )


def derive_nullifier(secret_value: int, event_id: str) -> tuple[str, str]:
    event_scalar = encode_event_id_to_field(event_id)
    nullifier = prototype_field_hash(secret_value, event_scalar, NULLIFIER_DOMAIN)
    return field_element_to_hex(event_scalar), field_element_to_hex(nullifier)


def derive_vote_commitment(vote_value: int, ballot_salt: int) -> str:
    commitment = prototype_field_hash(vote_value, ballot_salt, COMMITMENT_DOMAIN)
    return field_element_to_hex(commitment)


def build_public_inputs(
    *,
    event_id: str,
    nullifier: str,
    vote_commitment: str,
) -> dict[str, str]:
    event_id_scalar = field_element_to_hex(encode_event_id_to_field(event_id))
    return {
        "event_id": str(event_id),
        "event_id_scalar": event_id_scalar,
        "nullifier": field_element_to_hex(parse_field_element(nullifier)),
        "vote_commitment": field_element_to_hex(parse_field_element(vote_commitment)),
        "protocol_version": PROTOCOL_VERSION,
    }


def build_public_ballot_record(
    *,
    ballot_id: str,
    event_id: str,
    event_title: str,
    nullifier: str,
    vote_commitment: str,
    proof_hash: str,
    timestamp: str,
    verification_status: str,
) -> dict[str, str]:
    return {
        "ballot_id": ballot_id,
        "event_id": event_id,
        "event_title": event_title,
        "nullifier": field_element_to_hex(parse_field_element(nullifier)),
        "vote_commitment": field_element_to_hex(parse_field_element(vote_commitment)),
        "proof_hash": proof_hash,
        "timestamp": timestamp,
        "verification_status": verification_status,
    }


def compute_public_record_hash(public_record: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(public_record).encode("utf-8"))


def compute_chain_hash(previous_chain_hash: str, public_record: dict[str, Any]) -> str:
    serialized_record = canonical_json(public_record).encode("utf-8")
    payload = previous_chain_hash.encode("utf-8") + serialized_record
    return sha256_hex(payload)
