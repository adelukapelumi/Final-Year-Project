from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INSTANCE_DIR = BASE_DIR / "instance"
PROOF_ENGINE_DIR = BASE_DIR.parent / "proof_engine" / "winterfell"
PROOF_BINARY_NAME = "referendum_acceptance_winterfell.exe" if os.name == "nt" else "referendum_acceptance_winterfell"
PROOF_BINARY_PATH = PROOF_ENGINE_DIR / "target" / "release" / PROOF_BINARY_NAME


class Config:
    SECRET_KEY = os.environ.get("EVOTING_SECRET_KEY", "dev-secret-key-change-me")
    DATABASE_PATH = Path(os.environ.get("EVOTING_DATABASE_PATH", INSTANCE_DIR / "evoting.sqlite3"))
    SCHEMA_PATH = BASE_DIR / "schema.sql"
    NIN_REGISTRY_PATH = Path(os.environ.get("EVOTING_NIN_REGISTRY_PATH", DATA_DIR / "mock_nin_registry.json"))
    DEV_TEST_NINS_PATH = Path(os.environ.get("EVOTING_DEV_TEST_NINS_PATH", DATA_DIR / "dev_test_nins.json"))
    PROOF_ENGINE_DIR = Path(os.environ.get("EVOTING_PROOF_ENGINE_DIR", PROOF_ENGINE_DIR))
    PROOF_BINARY_PATH = Path(os.environ.get("EVOTING_PROOF_BINARY_PATH", PROOF_BINARY_PATH))
    PROOF_ARTIFACTS_DIR = Path(os.environ.get("EVOTING_PROOF_ARTIFACTS_DIR", BASE_DIR / "proof_artifacts"))
    PROOF_INPUTS_DIR = Path(os.environ.get("EVOTING_PROOF_INPUTS_DIR", BASE_DIR / "proof_inputs"))
    TOKEN_TTL_SECONDS = int(os.environ.get("EVOTING_TOKEN_TTL_SECONDS", "86400"))

    @staticmethod
    def encryption_key(secret_key: str) -> bytes:
        digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
