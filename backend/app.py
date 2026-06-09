from __future__ import annotations

import json
import uuid
from pathlib import Path

from flask import Flask, jsonify, request

from auth import authenticate_token, register_or_login, resolve_token_from_request
from config import Config
from crypto_utils import encrypt_vote
from db import close_db, get_db, init_db
from proof_client import ProofClientError, generate_and_verify_proof, verify_existing_proof
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


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db_path = Path(app.config["DATABASE_PATH"])
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["PROOF_ARTIFACTS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PROOF_INPUTS_DIR"]).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)
    if not db_path.exists():
        with app.app_context():
            init_db()

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
        return jsonify({"token": result["token"], "nin_hash": result["nin_hash"]}), 200

    @app.post("/vote")
    def vote():
        payload = request.get_json(silent=True) or {}
        try:
            token = resolve_token_from_request(request)
            voter = authenticate_token(token)
            vote_value, vote_label = _normalize_vote_value(payload.get("vote"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except PermissionError as exc:
            return jsonify({"error": str(exc)}), 403

        db = get_db()
        prior_vote = db.execute("SELECT ballot_id FROM ballots WHERE voter_id = ?", (voter["id"],)).fetchone()
        if prior_vote is not None:
            return jsonify({"error": "duplicate vote rejected"}), 409

        try:
            proof_result = generate_and_verify_proof(vote_value=vote_value, registered_flag=1, already_voted_flag=0)
        except ProofClientError as exc:
            return jsonify({"error": f"proof generation failed: {exc}"}), 500

        ballot_id = uuid.uuid4().hex
        encrypted_vote = encrypt_vote(vote_label, app.config["ENCRYPTION_KEY"])
        db.execute(
            """
            INSERT INTO ballots (
                ballot_id,
                voter_id,
                encrypted_vote,
                proof_hash,
                proof_path,
                public_inputs,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                ballot_id,
                voter["id"],
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
                    "proof_hash": proof_result["proof_hash"],
                    "proof_path": proof_result["proof_path"],
                    "public_inputs": proof_result["public_inputs"],
                }
            ),
            201,
        )

    @app.post("/verify")
    def verify():
        payload = request.get_json(silent=True) or {}
        ballot_id = payload.get("ballot_id")
        if not ballot_id:
            return jsonify({"error": "ballot_id is required"}), 400

        ballot = fetch_ballot_for_verification(str(ballot_id))
        if ballot is None:
            return jsonify({"error": "ballot not found"}), 404

        try:
            result = verify_existing_proof(ballot["public_inputs"], ballot["proof_path"])
        except ProofClientError as exc:
            return jsonify({"error": f"proof verification failed: {exc}"}), 500

        return jsonify({"ballot_id": ballot["ballot_id"], "verified": result["verified"], "proof_hash": result["proof_hash"]}), 200

    @app.get("/board")
    def board():
        return jsonify({"ballots": public_board()}), 200

    @app.get("/tally")
    def tally():
        return jsonify(compute_tally(app.config["ENCRYPTION_KEY"], app.config["NIN_REGISTRY_PATH"])), 200

    app.config["ENCRYPTION_KEY"] = Config.encryption_key(app.config["SECRET_KEY"])
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
