from __future__ import annotations

import json
from pathlib import Path

from crypto_utils import hash_nin


class MockNINRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self._hashed_nins = self._load_hashed_nins()

    def _load_hashed_nins(self) -> set[str]:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        records = payload.get("registered_nins", [])
        return {hash_nin(str(nin)) for nin in records}

    def is_registered_hash(self, nin_hash: str) -> bool:
        return nin_hash in self._hashed_nins
