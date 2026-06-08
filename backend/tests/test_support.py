from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402


def create_test_app(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    proof_artifacts = tmp_path / "proof_artifacts"
    proof_inputs = tmp_path / "proof_inputs"
    registry_path = tmp_path / "mock_nin_registry.json"
    registry_path.write_text(
        json.dumps({"registered_nins": ["12345678901", "23456789012", "34567890123"]}),
        encoding="utf-8",
    )
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_PATH": db_path,
            "NIN_REGISTRY_PATH": registry_path,
            "PROOF_ARTIFACTS_DIR": proof_artifacts,
            "PROOF_INPUTS_DIR": proof_inputs,
            "TOKEN_TTL_SECONDS": 3600,
        }
    )


def register(client, nin: str = "12345678901"):
    response = client.post("/register", json={"nin": nin})
    return response


def vote(client, token: str, vote_value="yes"):
    return client.post("/vote", json={"token": token, "vote": vote_value})
