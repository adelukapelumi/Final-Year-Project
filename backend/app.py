from __future__ import annotations

import json
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from auth import authenticate_token, register_or_login, resolve_token_from_request
from config import Config, LOCAL_FRONTEND_ORIGINS
from crypto_utils import encrypt_vote
from db import close_db, get_db, init_db
from events import ACTIVE_EVENT_ID, list_events, require_event
from nin_registry import MockNINRegistry, PROTOTYPE_FALLBACK_MESSAGE
from proof_client import (
    ProofClientError,
    generate_and_verify_proof,
    proof_binary_available,
    verify_existing_proof,
)
from tally_service import compute_tally, fetch_ballot_for_verification, public_board


def _normalize_vote_value(value) -> tuple[int, str]:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "yes"}:
            return 1, "yes"
        if normalized in {"0", "no"}:
            return 0, "no"
    elif value in (0, 1):
        return int(value), "yes" if int(value) == 1 else "no"
    raise ValueError("vote must be one of yes/no/1/0")


def _allowed_cors_origins(config: dict) -> list[str]:
    configured = []
    raw_origins = str(config.get("ALLOWED_ORIGINS", "") or "")
    for origin in raw_origins.split(","):
        normalized = origin.strip()
        if normalized and normalized != "*":
            configured.append(normalized)

    seen = set()
    allowed = []
    for origin in [*LOCAL_FRONTEND_ORIGINS, *configured]:
        if origin in seen:
            continue
        seen.add(origin)
        allowed.append(origin)
    return allowed


def _configure_cors(app: Flask) -> None:
    CORS(
        app,
        resources={r"/*": {"origins": _allowed_cors_origins(app.config)}},
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.config["ENCRYPTION_KEY"] = Config.encryption_key(app.config["SECRET_KEY"])
    _configure_cors(app)

    db_path = Path(app.config["DATABASE_PATH"])
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["PROOF_ARTIFACTS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PROOF_INPUTS_DIR"]).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)
    with app.app_context():
        if not db_path.exists():
            init_db()
        else:
            init_db()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/health/proof")
    def health_proof():
        if proof_binary_available():
            return jsonify({"status": "ok", "proof_engine": "available"}), 200
        return jsonify({"status": "error", "proof_engine": "unavailable"}), 503

    @app.post("/register")
    @app.post("/login")
    def register():
        payload = request.get_json(silent=True) or {}
        try:
            result = register_or_login(payload.get("nin"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except PermissionError as exc:
            return jsonify({"error": str(exc)}), 403
        return (
            jsonify(
                {
                    "token": result["token"],
                    "profile": result["profile"],
                    "biometric": result["biometric"],
                    "fallback_message": PROTOTYPE_FALLBACK_MESSAGE,
                }
            ),
            200,
        )

    @app.get("/events")
    def events():
        return jsonify({"events": list_events(), "active_event_id": ACTIVE_EVENT_ID}), 200

    @app.post("/biometric-verify")
    def biometric_verify():
        payload = request.get_json(silent=True) or {}
        try:
            token = resolve_token_from_request(request)
            voter = authenticate_token(token)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except PermissionError as exc:
            return jsonify({"error": str(exc)}), 403

        registry = MockNINRegistry(app.config["NIN_REGISTRY_PATH"])
        camera_capture = payload.get("camera_capture") is True
        probe_id = str(payload.get("probe_id") or "").strip()
        if camera_capture:
            result = registry.verify_camera_capture(voter["nin_hash"])
        elif probe_id:
            # Kept for backend compatibility; the public UI only uses camera capture.
            result = registry.verify_face_probe(voter["nin_hash"], probe_id)
        else:
            return jsonify({"error": "camera capture confirmation is required"}), 400

        if not result["verified"]:
            return (
                jsonify(
                    {
                        "error": "camera-based prototype verification failed",
                        "verified": False,
                        "fallback_message": result["fallback_message"],
                    }
                ),
                403,
            )

        db = get_db()
        db.execute(
            """
            UPDATE voters
            SET biometric_verified = 1, biometric_verified_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (voter["id"],),
        )
        db.commit()

        return (
            jsonify(
                {
                    "verified": True,
                    "verification_mode": result["verification_mode"],
                    "fallback_message": result["fallback_message"],
                }
            ),
            200,
        )

    @app.post("/vote")
    def vote():
        payload = request.get_json(silent=True) or {}
        try:
            token = resolve_token_from_request(request)
            voter = authenticate_token(token)
            vote_value, vote_label = _normalize_vote_value(payload.get("vote"))
            event = require_event(payload.get("event_id"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except PermissionError as exc:
            return jsonify({"error": str(exc)}), 403

        if not voter["biometric_verified"]:
            return jsonify({"error": "biometric verification required before ballot access"}), 403
        if not event["action_enabled"] or event["status"] != "Active":
            return jsonify({"error": "referendum event is not open for voting"}), 409

        db = get_db()
        prior_vote = db.execute(
            "SELECT ballot_id FROM ballots WHERE voter_id = ? AND event_id = ?",
            (voter["id"], event["event_id"]),
        ).fetchone()
        if prior_vote is not None:
            return jsonify({"error": "duplicate vote rejected"}), 409

        try:
            proof_result = generate_and_verify_proof(vote_value=vote_value, registered_flag=1, already_voted_flag=0)
        except ProofClientError as exc:
            app.logger.exception("Proof generation failed: %s", exc)
            return jsonify({"error": "proof generation failed"}), 500

        ballot_id = uuid.uuid4().hex
        encrypted_vote = encrypt_vote(vote_label, app.config["ENCRYPTION_KEY"])
        db.execute(
            """
            INSERT INTO ballots (
                ballot_id,
                voter_id,
                event_id,
                encrypted_vote,
                proof_hash,
                proof_path,
                public_inputs,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                ballot_id,
                voter["id"],
                event["event_id"],
                encrypted_vote,
                proof_result["proof_hash"],
                proof_result["proof_path"],
                json.dumps(proof_result["public_inputs"]),
            ),
        )
        db.execute("UPDATE voters SET has_voted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (voter["id"],))
        db.commit()

        return (
            jsonify(
                {
                    "ballot_id": ballot_id,
                    "event_id": event["event_id"],
                    "event_title": event["title"],
                    "proof_hash": proof_result["proof_hash"],
                }
            ),
            201,
        )

    @app.post("/verify")
    def verify():
        payload = request.get_json(silent=True) or {}
        ballot_id = payload.get("ballot_id")
        event_id = payload.get("event_id")
        if not ballot_id:
            return jsonify({"error": "ballot_id is required"}), 400

        if event_id:
            try:
                require_event(event_id)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        ballot = fetch_ballot_for_verification(str(ballot_id), str(event_id) if event_id else None)
        if ballot is None:
            return jsonify({"error": "ballot not found"}), 404

        if ballot.get("is_demo"):
            return jsonify(
                {
                    "ballot_id": ballot["ballot_id"],
                    "event_id": ballot["event_id"],
                    "verified": True,
                    "proof_hash": ballot["proof_hash"],
                }
            ), 200

        try:
            result = verify_existing_proof(ballot["public_inputs"], ballot["proof_path"])
        except ProofClientError as exc:
            app.logger.exception("Proof verification failed: %s", exc)
            return jsonify({"error": "proof verification failed"}), 500

        return jsonify(
            {
                "ballot_id": ballot["ballot_id"],
                "event_id": ballot["event_id"],
                "verified": result["verified"],
                "proof_hash": result["proof_hash"],
            }
        ), 200

    @app.get("/board")
    def board():
        try:
            event = require_event(request.args.get("event_id"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"event": event, "ballots": public_board(event["event_id"])}), 200

    @app.get("/tally")
    def tally():
        try:
            event = require_event(request.args.get("event_id"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(
            compute_tally(
                app.config["ENCRYPTION_KEY"],
                app.config["NIN_REGISTRY_PATH"],
                event["event_id"],
            )
        ), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
