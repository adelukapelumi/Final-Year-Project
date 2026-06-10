from __future__ import annotations

from pathlib import Path

from db import get_db


PROTOTYPE_FALLBACK_MESSAGE = (
    "This prototype verifies face presence for demonstration only and does not connect to live INEC, BVAS, or NIMC systems."
)


class MockNINRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)

    def _active_row(self, nin_hash: str):
        db = get_db()
        return db.execute(
            """
            SELECT
                nin_hash,
                display_name,
                diaspora_location,
                voter_category,
                mock_biometric_enabled
            FROM mock_voters
            WHERE nin_hash = ? AND is_active = 1
            """,
            (nin_hash,),
        ).fetchone()

    def is_registered_hash(self, nin_hash: str) -> bool:
        return self._active_row(nin_hash) is not None

    def get_record(self, nin_hash: str) -> dict | None:
        row = self._active_row(nin_hash)
        if row is None:
            return None
        return {
            "nin_hash": row["nin_hash"],
            "profile": {
                "display_name": row["display_name"],
                "diaspora_location": row["diaspora_location"],
                "voter_category": row["voter_category"],
            },
            "biometric": {
                "verification_mode": "Camera-based prototype face verification",
                "mock_biometric_enabled": bool(row["mock_biometric_enabled"]),
                "fallback_message": PROTOTYPE_FALLBACK_MESSAGE,
            },
        }

    def biometric_prompt(self, nin_hash: str) -> dict:
        record = self.get_record(nin_hash)
        if record is None:
            raise KeyError("mock voter record not found")

        biometric = record["biometric"]
        return {
            "status": "pending",
            "verification_mode": biometric["verification_mode"],
            "fallback_message": biometric["fallback_message"],
        }

    def public_profile(self, nin_hash: str) -> dict:
        record = self.get_record(nin_hash)
        if record is None:
            raise KeyError("mock voter record not found")
        return dict(record["profile"])

    def verify_camera_capture(self, nin_hash: str) -> dict:
        record = self.get_record(nin_hash)
        if record is None:
            raise PermissionError("nin is not registered")

        biometric = record["biometric"]
        return {
            "verified": bool(biometric["mock_biometric_enabled"]),
            "verification_mode": biometric["verification_mode"],
            "fallback_message": biometric["fallback_message"],
        }

    def verify_face_probe(self, nin_hash: str, probe_id: str) -> dict:
        record = self.get_record(nin_hash)
        if record is None:
            raise PermissionError("nin is not registered")

        biometric = record["biometric"]
        return {
            "verified": bool(biometric["mock_biometric_enabled"]) and probe_id == "diaspora-face-match",
            "verification_mode": biometric["verification_mode"],
            "probe_id": probe_id,
            "fallback_message": biometric["fallback_message"],
        }

    def total_registered_voters(self) -> int:
        db = get_db()
        return db.execute("SELECT COUNT(*) AS count FROM mock_voters WHERE is_active = 1").fetchone()["count"]
