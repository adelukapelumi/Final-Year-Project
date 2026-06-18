from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from admin_service import (
    ADMIN_CONFIRMATION_TEXT,
    ADMIN_DISABLED_MESSAGE,
    create_mock_voter,
    deactivate_mock_voter,
    delete_mock_voter,
    list_admin_voters,
    require_admin,
    reset_demo_data,
    reset_event,
    reset_voter,
    admin_identity,
)
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
from tally_service import (
    build_verification_bundle,
    compute_tally,
    fetch_ballot_for_verification,
    public_board,
    verify_public_board_chain,
)
from verifiability import (
    BOARD_CHAIN_GENESIS_HASH,
    build_public_ballot_record,
    compute_chain_hash,
    compute_public_record_hash,
    derive_nullifier,
    derive_vote_commitment,
    derive_voter_secret,
    field_element_to_hex,
    random_field_element,
)


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
        methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
    )


def _admin_error_response(exc: Exception):
    if isinstance(exc, RuntimeError):
        return jsonify({"error": ADMIN_DISABLED_MESSAGE}), 503
    if isinstance(exc, ValueError):
        message = str(exc)
        status = 401 if "X-Admin-Token header is required" in message else 400
        return jsonify({"error": message}), status
    if isinstance(exc, PermissionError):
        return jsonify({"error": str(exc)}), 403
    if isinstance(exc, LookupError):
        return jsonify({"error": str(exc)}), 404
    return jsonify({"error": "admin request failed"}), 500


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

    @app.get("/admin/me")
    @app.post("/admin/login")
    def admin_me():
        try:
            require_admin(request)
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify({"authenticated": True, "admin": admin_identity()}), 200

    @app.get("/admin/voters")
    def admin_voters():
        try:
            require_admin(request)
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        payload = list_admin_voters()
        payload["admin"] = admin_identity()
        return jsonify(payload), 200

    @app.post("/admin/voters")
    def admin_create_voter():
        try:
            require_admin(request)
            voter = create_mock_voter(request.get_json(silent=True) or {})
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify({"voter": voter}), 201

    @app.post("/admin/voters/<int:mock_voter_id>/deactivate")
    def admin_deactivate_voter(mock_voter_id: int):
        try:
            require_admin(request)
            result = deactivate_mock_voter(mock_voter_id)
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify(result), 200

    @app.delete("/admin/voters/<int:mock_voter_id>")
    def admin_delete_voter(mock_voter_id: int):
        try:
            require_admin(request)
            result = delete_mock_voter(mock_voter_id)
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify(result), 200

    @app.post("/admin/voters/<int:mock_voter_id>/reset")
    def admin_reset_voter(mock_voter_id: int):
        payload = request.get_json(silent=True) or {}
        try:
            require_admin(request)
            result = reset_voter(mock_voter_id, payload.get("event_id"))
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify(result), 200

    @app.post("/admin/events/<event_id>/reset")
    def admin_reset_event(event_id: str):
        try:
            require_admin(request)
            result = reset_event(event_id)
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify(result), 200

    @app.post("/admin/reset-demo-data")
    def admin_reset_demo():
        payload = request.get_json(silent=True) or {}
        try:
            require_admin(request)
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        confirmation_text = str(payload.get("confirmation_text") or "").strip()
        if confirmation_text != ADMIN_CONFIRMATION_TEXT:
            return jsonify({"error": f"confirmation_text must equal {ADMIN_CONFIRMATION_TEXT}"}), 400

        try:
            result = reset_demo_data(bool(payload.get("clear_registry")))
        except (RuntimeError, ValueError, PermissionError, LookupError) as exc:
            return _admin_error_response(exc)
        return jsonify(result), 200

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
            return jsonify({"error": "duplicate nullifier rejected"}), 409

        voter_secret_value = derive_voter_secret(app.config["SECRET_KEY"], voter["nin_hash"])
        voter_secret = field_element_to_hex(voter_secret_value)
        ballot_salt = field_element_to_hex(random_field_element())
        _event_id_scalar, nullifier = derive_nullifier(voter_secret_value, event["event_id"])
        vote_commitment = derive_vote_commitment(vote_value, int(ballot_salt, 16))

        duplicate_nullifier = db.execute(
            "SELECT ballot_id FROM ballots WHERE nullifier = ?",
            (nullifier,),
        ).fetchone()
        if duplicate_nullifier is not None:
            return jsonify({"error": "duplicate nullifier rejected"}), 409

        try:
            proof_result = generate_and_verify_proof(
                vote_value=vote_value,
                registered_flag=1,
                already_voted_flag=0,
                voter_secret=voter_secret,
                ballot_salt=ballot_salt,
                event_id=event["event_id"],
                nullifier=nullifier,
                vote_commitment=vote_commitment,
            )
        except ProofClientError as exc:
            app.logger.exception("Proof generation failed: %s", exc)
            return jsonify({"error": "proof generation failed"}), 500

        ballot_id = uuid.uuid4().hex
        encrypted_vote = encrypt_vote(vote_label, app.config["ENCRYPTION_KEY"])
        previous_chain_hash_row = db.execute(
            """
            SELECT chain_hash
            FROM ballots
            WHERE event_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (event["event_id"],),
        ).fetchone()
        verification_status = "verified"
        created_at = db.execute("SELECT CURRENT_TIMESTAMP AS current_timestamp").fetchone()[
            "current_timestamp"
        ]
        previous_chain_hash = (
            previous_chain_hash_row["chain_hash"]
            if previous_chain_hash_row is not None
            else BOARD_CHAIN_GENESIS_HASH
        )
        public_record = build_public_ballot_record(
            ballot_id=ballot_id,
            event_id=event["event_id"],
            event_title=event["title"],
            nullifier=nullifier,
            vote_commitment=vote_commitment,
            proof_hash=proof_result["proof_hash"],
            timestamp=created_at,
            verification_status=verification_status,
        )
        current_record_hash = compute_public_record_hash(public_record)
        chain_hash = compute_chain_hash(previous_chain_hash, public_record)

        try:
            db.execute(
                """
                INSERT INTO ballots (
                    ballot_id,
                    voter_id,
                    event_id,
                    encrypted_vote,
                    nullifier,
                    vote_commitment,
                    ballot_salt,
                    proof_hash,
                    proof_path,
                    public_inputs,
                    verification_status,
                    previous_chain_hash,
                    current_record_hash,
                    chain_hash,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ballot_id,
                    voter["id"],
                    event["event_id"],
                    encrypted_vote,
                    nullifier,
                    vote_commitment,
                    ballot_salt,
                    proof_result["proof_hash"],
                    proof_result["proof_path"],
                    json.dumps(proof_result["public_inputs"]),
                    verification_status,
                    previous_chain_hash,
                    current_record_hash,
                    chain_hash,
                    created_at,
                ),
            )
            db.execute(
                "UPDATE voters SET has_voted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (voter["id"],),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            return jsonify({"error": "duplicate nullifier rejected"}), 409

        return (
            jsonify(
                {
                    "ballot_id": ballot_id,
                    "event_id": event["event_id"],
                    "event_title": event["title"],
                    "nullifier": nullifier,
                    "vote_commitment": vote_commitment,
                    "proof_hash": proof_result["proof_hash"],
                    "previous_chain_hash": previous_chain_hash,
                    "chain_hash": chain_hash,
                    "verification_status": verification_status,
                    "timestamp": created_at,
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
                "nullifier": ballot["nullifier"],
                "vote_commitment": ballot["vote_commitment"],
                "verification_status": ballot.get("verification_status", "verified"),
                "timestamp": ballot.get("created_at"),
            }
        ), 200

    @app.get("/board")
    def board():
        try:
            event = require_event(request.args.get("event_id"))
            page = request.args.get("page", type=int)
            page_size = request.args.get("page_size", type=int)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if (page is None) != (page_size is None):
            return jsonify({"error": "page and page_size must be supplied together"}), 400
        if page is not None and (page < 1 or page_size < 1):
            return jsonify({"error": "page and page_size must be positive integers"}), 400
        return (
            jsonify(
                {
                    "event": event,
                    "ballots": public_board(
                        event["event_id"],
                        page=page,
                        page_size=page_size,
                    ),
                    "pagination": (
                        {"page": page, "page_size": page_size} if page is not None else None
                    ),
                }
            ),
            200,
        )

    @app.get("/board/verify-chain")
    def board_verify_chain():
        try:
            event = require_event(request.args.get("event_id"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        result = verify_public_board_chain(event["event_id"])
        return jsonify(result), 200

    @app.get("/verify/bundle/<ballot_id>")
    def verify_bundle(ballot_id: str):
        event_id = request.args.get("event_id")
        if event_id:
            try:
                require_event(event_id)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
        bundle = build_verification_bundle(ballot_id, event_id)
        if bundle is None:
            return jsonify({"error": "ballot not found"}), 404
        return jsonify(bundle), 200

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
