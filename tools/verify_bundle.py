from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from bundle_verifier import (  # noqa: E402
    chain_hash_passes,
    load_bundle,
    proof_hash_matches,
    receipt_consistency_passes,
    verify_proof_from_bundle,
)
from config import PROOF_BINARY_PATH, PROOF_ENGINE_DIR  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a DiasporaVote independent verification bundle."
    )
    parser.add_argument("bundle_path", type=Path, help="Path to the exported bundle JSON file.")
    return parser.parse_args()


def status_label(value: bool) -> str:
    return "passed" if value else "failed"


def main() -> int:
    args = parse_args()
    bundle = load_bundle(args.bundle_path)

    proof_ok = verify_proof_from_bundle(
        bundle=bundle,
        proof_binary_path=Path(PROOF_BINARY_PATH),
        proof_engine_dir=Path(PROOF_ENGINE_DIR),
    )
    proof_hash_ok = proof_hash_matches(bundle)
    receipt_ok = receipt_consistency_passes(bundle)
    chain_ok = chain_hash_passes(bundle)
    final_ok = proof_ok and proof_hash_ok and receipt_ok and chain_ok

    print(f"proof verification: {status_label(proof_ok)}")
    print(f"proof hash check: {status_label(proof_hash_ok)}")
    print(f"receipt consistency check: {status_label(receipt_ok)}")
    print(f"chain hash check: {status_label(chain_ok)}")
    print(f"final result: {'valid' if final_ok else 'invalid'}")
    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
