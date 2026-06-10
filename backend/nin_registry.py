from __future__ import annotations

import json
from pathlib import Path

from crypto_utils import hash_nin


PROTOTYPE_FALLBACK_MESSAGE = (
    "This prototype verifies face presence for demonstration only and does not connect to live INEC, BVAS, or NIMC systems."
)

DEFAULT_PROBE_CATALOG = {
    "diaspora-face-match": {
        "id": "diaspora-face-match",
        "label": "Preloaded Development Face Sample A",
        "description": "Simulated enrolled face sample for prototype accreditation.",
    },
    "diaspora-face-alt": {
        "id": "diaspora-face-alt",
        "label": "Preloaded Development Face Sample B",
        "description": "Alternate mock face sample used for negative-path testing.",
    },
    "diaspora-face-retry": {
        "id": "diaspora-face-retry",
        "label": "Preloaded Development Face Sample C",
        "description": "Fallback mock sample for retry and UI-state testing.",
    },
}


class MockNINRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self._records = self._load_records()

    def _load_records(self) -> dict[str, dict]:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        registered_voters = payload.get("registered_voters")
        if registered_voters is None:
            registered_voters = [{"nin": nin} for nin in payload.get("registered_nins", [])]

        records: dict[str, dict] = {}
        for item in registered_voters:
            normalized_nin = str(item.get("nin", ""))
            nin_hash = hash_nin(normalized_nin)
            biometric = item.get("biometric") or {}
            records[nin_hash] = {
                "nin_hash": nin_hash,
                "profile": {
                    "display_name": item.get("display_name", "Prototype Diaspora Voter"),
                    "diaspora_location": item.get("diaspora_location", "Diaspora"),
                    "voter_category": item.get("voter_category", "Eligible Diaspora Voter"),
                },
                "biometric": {
                    "face_template_id": biometric.get("face_template_id", ""),
                    "accepted_probe_id": biometric.get("accepted_probe_id", "diaspora-face-match"),
                    "development_profile_label": biometric.get(
                        "development_profile_label", "Diaspora kiosk prototype sample"
                    ),
                    "verification_mode": biometric.get(
                        "verification_mode", "Camera-based prototype face verification"
                    ),
                    "available_probes": self._resolve_available_probes(
                        biometric.get("available_probe_ids") or ["diaspora-face-match", "diaspora-face-alt", "diaspora-face-retry"]
                    ),
                    "fallback_message": biometric.get("fallback_message", PROTOTYPE_FALLBACK_MESSAGE),
                },
            }
        return records

    def _resolve_available_probes(self, probe_ids: list[str]) -> list[dict]:
        probes = []
        for probe_id in probe_ids:
            probe = DEFAULT_PROBE_CATALOG.get(probe_id)
            if probe is not None:
                probes.append(dict(probe))
        return probes

    def is_registered_hash(self, nin_hash: str) -> bool:
        return nin_hash in self._records

    def get_record(self, nin_hash: str) -> dict | None:
        return self._records.get(nin_hash)

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
            "verified": bool(biometric["face_template_id"]),
            "verification_mode": "Camera-based prototype face verification",
            "fallback_message": biometric["fallback_message"],
        }

    def verify_face_probe(self, nin_hash: str, probe_id: str) -> dict:
        record = self.get_record(nin_hash)
        if record is None:
            raise PermissionError("nin is not registered")

        biometric = record["biometric"]
        passed = probe_id == biometric["accepted_probe_id"] and bool(biometric["face_template_id"])
        return {
            "verified": passed,
            "verification_mode": biometric["verification_mode"],
            "development_profile_label": biometric["development_profile_label"],
            "probe_id": probe_id,
            "fallback_message": biometric["fallback_message"],
        }

    def total_registered_voters(self) -> int:
        return len(self._records)
