from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3

from flask import current_app, request

from auth import normalize_nin
from crypto_utils import constant_time_equal, hash_nin
from db import get_db
from events import ACTIVE_EVENT_ID, require_event


ADMIN_TOKEN_HEADER = "X-Admin-Token"
ADMIN_DISABLED_MESSAGE = "prototype registry admin is not configured"
ADMIN_CONFIRMATION_TEXT = "RESET DEMO DATA"


def admin_token_configured() -> bool:
    return bool(str(current_app.config.get("ADMIN_TOKEN") or "").strip())


def require_admin(request_obj=request) -> str:
    configured_token = str(current_app.config.get("ADMIN_TOKEN") or "").strip()
    if not configured_token:
        raise RuntimeError(ADMIN_DISABLED_MESSAGE)

    candidate = str(request_obj.headers.get(ADMIN_TOKEN_HEADER, "") or "").strip()
    if not candidate:
        raise ValueError(f"{ADMIN_TOKEN_HEADER} header is required")
    if not constant_time_equal(candidate, configured_token):
        raise PermissionError("invalid admin token")
    return candidate


def mask_nin(nin: str) -> str:
    normalized = normalize_nin(nin)
    return f"{'*' * 7}{normalized[-4:]}"


def admin_identity() -> dict:
    event = require_event(ACTIVE_EVENT_ID)
    return {
        "label": "Prototype Registry Admin",
        "scope": "prototype-demo-management",
        "active_event": {
            "event_id": event["event_id"],
            "title": event["title"],
            "status": event["status"],
        },
    }


def _bool_flag(value) -> int:
    return 1 if bool(value) else 0


def _placeholders(values: list[int]) -> str:
    return ",".join("?" for _ in values)


def _proof_input_path_for_ballot(proof_path: str | Path, inputs_dir: Path) -> Path | None:
    name = Path(proof_path).name
    suffix = ".proof.bin"
    if not name.endswith(suffix):
        return None
    artifact_id = name[: -len(suffix)]
    if not artifact_id:
        return None
    return inputs_dir / f"{artifact_id}.json"


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _delete_file_if_safe(candidate: Path, root: Path) -> bool:
    if not _is_within_root(candidate, root):
        return False
    if not candidate.exists() or not candidate.is_file():
        return False
    candidate.unlink()
    return True


def _clear_directory_contents(root: Path) -> int:
    root.mkdir(parents=True, exist_ok=True)
    deleted = 0
    resolved_root = root.resolve()
    for child in root.iterdir():
        resolved_child = child.resolve()
        if not _is_within_root(resolved_child, resolved_root):
            continue
        if child.is_dir():
            shutil.rmtree(child)
            deleted += 1
        elif child.is_file():
            child.unlink()
            deleted += 1
    return deleted


def _fetch_ballots_for_cleanup(
    db: sqlite3.Connection, *, voter_id: int | None = None, event_id: str | None = None
) -> list[sqlite3.Row]:
    clauses = []
    params: list[object] = []
    if voter_id is not None:
        clauses.append("voter_id = ?")
        params.append(voter_id)
    if event_id is not None:
        clauses.append("event_id = ?")
        params.append(event_id)

    query = "SELECT id, ballot_id, voter_id, event_id, proof_path FROM ballots"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    return db.execute(query, tuple(params)).fetchall()


def _delete_ballot_artifacts(ballots: list[sqlite3.Row]) -> dict[str, int]:
    artifacts_dir = Path(current_app.config["PROOF_ARTIFACTS_DIR"])
    inputs_dir = Path(current_app.config["PROOF_INPUTS_DIR"])
    deleted_artifacts = 0
    deleted_inputs = 0

    for ballot in ballots:
        proof_path = Path(ballot["proof_path"])
        if _delete_file_if_safe(proof_path, artifacts_dir):
            deleted_artifacts += 1
        input_path = _proof_input_path_for_ballot(proof_path, inputs_dir)
        if input_path is not None and _delete_file_if_safe(input_path, inputs_dir):
            deleted_inputs += 1

    return {
        "proof_artifacts_deleted": deleted_artifacts,
        "proof_inputs_deleted": deleted_inputs,
    }


def _recalculate_has_voted(db: sqlite3.Connection, voter_ids: list[int] | None = None) -> None:
    if voter_ids:
        db.execute(
            f"""
            UPDATE voters
            SET
                has_voted = CASE
                    WHEN EXISTS (SELECT 1 FROM ballots WHERE ballots.voter_id = voters.id) THEN 1
                    ELSE 0
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({_placeholders(voter_ids)})
            """,
            tuple(voter_ids),
        )
        return

    db.execute(
        """
        UPDATE voters
        SET
            has_voted = CASE
                WHEN EXISTS (SELECT 1 FROM ballots WHERE ballots.voter_id = voters.id) THEN 1
                ELSE 0
            END,
            updated_at = CURRENT_TIMESTAMP
        """
    )


def _reset_voter_session_state(db: sqlite3.Connection, voter_id: int) -> None:
    db.execute(
        """
        UPDATE voters
        SET
            session_token_hash = '',
            token_expires_at = ?,
            biometric_verified = 0,
            biometric_verified_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(), voter_id),
    )


def _registry_projection(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "diaspora_location": row["diaspora_location"],
        "voter_category": row["voter_category"],
        "nin_last4": row["nin_last4"],
        "masked_nin": row["masked_nin"],
        "mock_biometric_enabled": bool(row["mock_biometric_enabled"]),
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "has_voted": bool(row["has_voted"]) if row["has_voted"] is not None else False,
        "biometric_verified": bool(row["biometric_verified"]) if row["biometric_verified"] is not None else False,
    }


def list_admin_voters() -> dict:
    db = get_db()
    rows = db.execute(
        """
        SELECT
            mv.id,
            mv.display_name,
            mv.diaspora_location,
            mv.voter_category,
            mv.nin_last4,
            mv.masked_nin,
            mv.mock_biometric_enabled,
            mv.is_active,
            mv.created_at,
            mv.updated_at,
            v.has_voted,
            v.biometric_verified
        FROM mock_voters mv
        LEFT JOIN voters v ON v.nin_hash = mv.nin_hash
        ORDER BY mv.is_active DESC, mv.display_name COLLATE NOCASE ASC, mv.id ASC
        """
    ).fetchall()

    overview = db.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM mock_voters) AS total_mock_voters,
            (SELECT COUNT(*) FROM mock_voters WHERE is_active = 1) AS active_mock_voters,
            (SELECT COUNT(*) FROM ballots WHERE event_id = ?) AS ballots_cast
        """,
        (ACTIVE_EVENT_ID,),
    ).fetchone()

    event = require_event(ACTIVE_EVENT_ID)
    return {
        "overview": {
            "total_mock_voters": overview["total_mock_voters"],
            "active_mock_voters": overview["active_mock_voters"],
            "ballots_cast": overview["ballots_cast"],
            "active_event": {
                "event_id": event["event_id"],
                "title": event["title"],
                "status": event["status"],
            },
        },
        "voters": [_registry_projection(row) for row in rows],
    }


def create_mock_voter(payload: dict) -> dict:
    normalized_nin = normalize_nin(payload.get("nin"))
    db = get_db()
    nin_hash = hash_nin(normalized_nin)
    display_name = str(payload.get("display_name") or "Prototype Diaspora Voter").strip()
    diaspora_location = str(payload.get("diaspora_location") or "Diaspora").strip()
    voter_category = str(payload.get("voter_category") or "Eligible Diaspora Voter").strip()
    mock_biometric_enabled = _bool_flag(
        payload.get("mock_biometric_enabled", payload.get("face_template_enabled", True))
    )

    if not display_name:
        raise ValueError("display_name is required")
    if not diaspora_location:
        raise ValueError("diaspora_location is required")
    if not voter_category:
        raise ValueError("voter_category is required")

    try:
        cursor = db.execute(
            """
            INSERT INTO mock_voters (
                nin_hash,
                nin_last4,
                masked_nin,
                display_name,
                diaspora_location,
                voter_category,
                mock_biometric_enabled,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                nin_hash,
                normalized_nin[-4:],
                mask_nin(normalized_nin),
                display_name,
                diaspora_location,
                voter_category,
                mock_biometric_enabled,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("mock voter already exists") from exc
    db.commit()

    row = db.execute(
        """
        SELECT
            id,
            display_name,
            diaspora_location,
            voter_category,
            nin_last4,
            masked_nin,
            mock_biometric_enabled,
            is_active,
            created_at,
            updated_at,
            NULL AS has_voted,
            NULL AS biometric_verified
        FROM mock_voters
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return _registry_projection(row)


def deactivate_mock_voter(mock_voter_id: int) -> dict:
    db = get_db()
    row = db.execute("SELECT id, nin_hash FROM mock_voters WHERE id = ?", (mock_voter_id,)).fetchone()
    if row is None:
        raise LookupError("mock voter not found")

    voter = db.execute("SELECT id FROM voters WHERE nin_hash = ?", (row["nin_hash"],)).fetchone()
    if voter is not None:
        reset_summary = reset_voter(mock_voter_id)
    else:
        reset_summary = {
            "ballots_deleted": 0,
            "proof_artifacts_deleted": 0,
            "proof_inputs_deleted": 0,
            "session_cleared": False,
            "events_cleared": [],
        }

    db.execute(
        "UPDATE mock_voters SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (mock_voter_id,),
    )
    db.commit()
    return {"id": mock_voter_id, "is_active": False, **reset_summary}


def delete_mock_voter(mock_voter_id: int) -> dict:
    db = get_db()
    row = db.execute("SELECT id, nin_hash FROM mock_voters WHERE id = ?", (mock_voter_id,)).fetchone()
    if row is None:
        raise LookupError("mock voter not found")

    ballots = []
    voter = db.execute("SELECT id FROM voters WHERE nin_hash = ?", (row["nin_hash"],)).fetchone()
    if voter is not None:
        ballots = _fetch_ballots_for_cleanup(db, voter_id=voter["id"])
        cleanup = _delete_ballot_artifacts(ballots)
        db.execute("DELETE FROM voters WHERE id = ?", (voter["id"],))
    else:
        cleanup = {"proof_artifacts_deleted": 0, "proof_inputs_deleted": 0}

    db.execute("DELETE FROM mock_voters WHERE id = ?", (mock_voter_id,))
    db.commit()
    return {
        "id": mock_voter_id,
        "deleted": True,
        "ballots_deleted": len(ballots),
        **cleanup,
    }


def reset_voter(mock_voter_id: int, event_id: str | None = None) -> dict:
    db = get_db()
    registry_row = db.execute(
        "SELECT id, nin_hash FROM mock_voters WHERE id = ?",
        (mock_voter_id,),
    ).fetchone()
    if registry_row is None:
        raise LookupError("mock voter not found")

    if event_id:
        require_event(event_id)

    voter = db.execute("SELECT id FROM voters WHERE nin_hash = ?", (registry_row["nin_hash"],)).fetchone()
    if voter is None:
        return {
            "id": mock_voter_id,
            "ballots_deleted": 0,
            "proof_artifacts_deleted": 0,
            "proof_inputs_deleted": 0,
            "session_cleared": False,
            "events_cleared": [event_id] if event_id else [],
        }

    ballots = _fetch_ballots_for_cleanup(db, voter_id=voter["id"], event_id=event_id)
    cleanup = _delete_ballot_artifacts(ballots)
    if event_id:
        db.execute(
            "DELETE FROM ballots WHERE voter_id = ? AND event_id = ?",
            (voter["id"], event_id),
        )
    else:
        db.execute("DELETE FROM ballots WHERE voter_id = ?", (voter["id"],))
    _reset_voter_session_state(db, voter["id"])
    _recalculate_has_voted(db, [voter["id"]])
    db.commit()

    cleared_events = sorted({row["event_id"] for row in ballots})
    return {
        "id": mock_voter_id,
        "ballots_deleted": len(ballots),
        **cleanup,
        "session_cleared": True,
        "events_cleared": cleared_events,
    }


def reset_event(event_id: str) -> dict:
    event = require_event(event_id)
    db = get_db()
    ballots = _fetch_ballots_for_cleanup(db, event_id=event["event_id"])
    cleanup = _delete_ballot_artifacts(ballots)
    voter_ids = sorted({row["voter_id"] for row in ballots})
    db.execute("DELETE FROM ballots WHERE event_id = ?", (event["event_id"],))
    if voter_ids:
        _recalculate_has_voted(db, voter_ids)
    db.commit()

    return {
        "event_id": event["event_id"],
        "ballots_deleted": len(ballots),
        "affected_voters": len(voter_ids),
        **cleanup,
    }


def reset_demo_data(clear_registry: bool = False) -> dict:
    db = get_db()
    ballots = _fetch_ballots_for_cleanup(db)
    cleanup = _delete_ballot_artifacts(ballots)
    db.execute("DELETE FROM ballots")
    db.execute(
        """
        UPDATE voters
        SET
            session_token_hash = '',
            token_expires_at = ?,
            biometric_verified = 0,
            biometric_verified_at = NULL,
            has_voted = 0,
            updated_at = CURRENT_TIMESTAMP
        """,
        (datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(),),
    )
    if clear_registry:
        db.execute("DELETE FROM mock_voters")
    db.commit()

    extra_inputs_deleted = _clear_directory_contents(Path(current_app.config["PROOF_INPUTS_DIR"]))
    extra_artifacts_deleted = _clear_directory_contents(Path(current_app.config["PROOF_ARTIFACTS_DIR"]))
    return {
        "ballots_deleted": len(ballots),
        "registry_preserved": not clear_registry,
        "registry_deleted": clear_registry,
        "voter_sessions_cleared": True,
        "biometric_state_cleared": True,
        "proof_artifacts_deleted": cleanup["proof_artifacts_deleted"] + extra_artifacts_deleted,
        "proof_inputs_deleted": cleanup["proof_inputs_deleted"] + extra_inputs_deleted,
    }
