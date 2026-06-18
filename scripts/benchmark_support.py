from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib import error, request

from werkzeug.serving import make_server


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402


ACTIVE_EVENT_ID = "diaspora-referendum-2026"
BENCHMARK_RESULTS_DIR = REPO_ROOT / "benchmark_results"


def ensure_results_dir() -> Path:
    BENCHMARK_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return BENCHMARK_RESULTS_DIR


def benchmark_voter_record(index: int) -> dict:
    nin = f"{70000000000 + index:011d}"
    return {
        "nin": nin,
        "display_name": f"Benchmark Voter {index:06d}",
        "diaspora_location": "Benchmark Diaspora Cluster",
        "voter_category": "Eligible Diaspora Voter",
        "biometric": {
            "face_template_id": f"bench-template-{index:06d}",
            "accepted_probe_id": "diaspora-face-match",
            "development_profile_label": f"Benchmark profile {index:06d}",
        },
    }


def create_registry_file(path: Path, voter_count: int) -> list[dict]:
    voters = [benchmark_voter_record(index) for index in range(1, voter_count + 1)]
    path.write_text(json.dumps({"registered_voters": voters}, indent=2), encoding="utf-8")
    return voters


def create_benchmark_app(temp_root: Path, voter_count: int):
    temp_root.mkdir(parents=True, exist_ok=True)
    db_path = temp_root / "benchmark.sqlite3"
    proof_artifacts = temp_root / "proof_artifacts"
    proof_inputs = temp_root / "proof_inputs"
    registry_path = temp_root / "mock_nin_registry.json"
    create_registry_file(registry_path, voter_count)
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "benchmark-secret",
            "ADMIN_TOKEN": "benchmark-admin-token",
            "DATABASE_PATH": db_path,
            "NIN_REGISTRY_PATH": registry_path,
            "PROOF_ARTIFACTS_DIR": proof_artifacts,
            "PROOF_INPUTS_DIR": proof_inputs,
            "TOKEN_TTL_SECONDS": 3600,
        }
    )


def register_and_vote(client, nin: str, vote_value: str, event_id: str = ACTIVE_EVENT_ID) -> dict:
    auth_response = client.post("/register", json={"nin": nin})
    auth_payload = auth_response.get_json()
    if auth_response.status_code != 200:
        raise RuntimeError(auth_payload.get("error", "registration failed"))
    token = auth_payload["token"]

    biometric_response = client.post("/biometric-verify", json={"token": token, "camera_capture": True})
    biometric_payload = biometric_response.get_json()
    if biometric_response.status_code != 200:
        raise RuntimeError(biometric_payload.get("error", "biometric verification failed"))

    vote_response = client.post(
        "/vote",
        json={"token": token, "vote": vote_value, "event_id": event_id},
    )
    return {
        "auth_response": auth_response,
        "biometric_response": biometric_response,
        "vote_response": vote_response,
    }


class ServerThread(threading.Thread):
    def __init__(self, app, host: str, port: int):
        super().__init__(daemon=True)
        self.server = make_server(host, port, app)
        self.context = app.app_context()
        self.context.push()

    def run(self) -> None:
        self.server.serve_forever()

    def shutdown(self) -> None:
        self.server.shutdown()
        self.context.pop()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def running_server(voter_count: int) -> Iterator[tuple[str, Path]]:
    with tempfile.TemporaryDirectory(prefix="diasporavote-bench-") as temp_name:
        temp_root = Path(temp_name)
        app = create_benchmark_app(temp_root, voter_count=voter_count)
        port = find_free_port()
        server = ServerThread(app, "127.0.0.1", port)
        server.start()
        base_url = f"http://127.0.0.1:{port}"
        try:
            time.sleep(0.2)
            yield base_url, temp_root
        finally:
            server.shutdown()


def post_json(base_url: str, path: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        return exc.code, payload


def get_json(base_url: str, path: str) -> tuple[int, dict]:
    req = request.Request(f"{base_url}{path}", method="GET")
    with request.urlopen(req, timeout=300) as response:
        return response.status, json.loads(response.read().decode("utf-8"))
