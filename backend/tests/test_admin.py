from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import accredit, admin_headers, create_test_app, vote
from db import get_db


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_admin_token_protection_and_safe_config_error(self):
        missing = self.client.get("/admin/me")
        invalid = self.client.get("/admin/me", headers=admin_headers("wrong-token"))

        disabled_app = create_test_app(Path(self.temp_dir.name) / "disabled", {"ADMIN_TOKEN": ""})
        disabled_client = disabled_app.test_client()
        disabled = disabled_client.post("/admin/voters", json={"nin": "45678901234"})

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.get_json()["error"], "X-Admin-Token header is required")
        self.assertEqual(invalid.status_code, 403)
        self.assertEqual(invalid.get_json()["error"], "invalid admin token")
        self.assertEqual(disabled.status_code, 503)
        self.assertEqual(disabled.get_json()["error"], "prototype registry admin is not configured")

    def test_admin_can_create_mock_voter_and_login_without_redeploy(self):
        create_response = self.client.post(
            "/admin/voters",
            headers=admin_headers(),
            json={
                "nin": "45678901234",
                "display_name": "Chidinma Eze",
                "diaspora_location": "Berlin, Germany",
                "voter_category": "Eligible Diaspora Voter",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        voter = create_response.get_json()["voter"]
        self.assertEqual(voter["masked_nin"], "*******1234")
        self.assertEqual(voter["nin_last4"], "1234")
        self.assertNotIn("nin_hash", voter)
        self.assertNotIn("nin", voter)

        registry_response = self.client.get("/admin/voters", headers=admin_headers())
        self.assertEqual(registry_response.status_code, 200)
        self.assertEqual(registry_response.get_json()["overview"]["total_mock_voters"], 4)

        login_response = self.client.post("/login", json={"nin": "45678901234"})
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.get_json()["profile"]["display_name"], "Chidinma Eze")
        self.assertEqual(login_response.get_json()["profile"]["diaspora_location"], "Berlin, Germany")

    def test_admin_can_reset_voter_and_clear_session_ballot_and_artifacts(self):
        auth = accredit(self.client, "12345678901")
        token = auth.get_json()["token"]
        self.client.post("/vote", json={"token": token, "vote": "yes", "event_id": "diaspora-referendum-2026"})

        with self.app.app_context():
            db = get_db()
            ballot = db.execute(
                """
                SELECT b.proof_path, v.id AS voter_id
                FROM ballots b
                JOIN voters v ON v.id = b.voter_id
                ORDER BY b.id ASC
                LIMIT 1
                """
            ).fetchone()
            proof_path = Path(ballot["proof_path"])
            input_path = proof_path.parent.parent / "proof_inputs" / f"{proof_path.name[:-10]}.json"
            mock_voter_id = db.execute(
                "SELECT id FROM mock_voters WHERE display_name = ?",
                ("Amara Okafor",),
            ).fetchone()["id"]

        self.assertTrue(proof_path.exists())
        self.assertTrue(input_path.exists())

        reset_response = self.client.post(
            f"/admin/voters/{mock_voter_id}/reset",
            headers=admin_headers(),
            json={},
        )

        self.assertEqual(reset_response.status_code, 200)
        body = reset_response.get_json()
        self.assertEqual(body["ballots_deleted"], 1)
        self.assertTrue(body["session_cleared"])
        self.assertEqual(body["events_cleared"], ["diaspora-referendum-2026"])
        self.assertFalse(proof_path.exists())
        self.assertFalse(input_path.exists())

        vote_again = vote(self.client, token, "yes")
        self.assertEqual(vote_again.status_code, 403)
        self.assertEqual(vote_again.get_json()["error"], "invalid session token")

        with self.app.app_context():
            db = get_db()
            voter_state = db.execute(
                "SELECT has_voted, biometric_verified, session_token_hash FROM voters WHERE id = ?",
                (ballot["voter_id"],),
            ).fetchone()
            ballot_count = db.execute("SELECT COUNT(*) AS count FROM ballots").fetchone()["count"]
            self.assertEqual(ballot_count, 0)
            self.assertEqual(voter_state["has_voted"], 0)
            self.assertEqual(voter_state["biometric_verified"], 0)
            self.assertEqual(voter_state["session_token_hash"], "")

    def test_admin_can_reset_event_and_keep_registry(self):
        first = accredit(self.client, "12345678901")
        second = accredit(self.client, "23456789012")
        vote(self.client, first.get_json()["token"], "yes")
        vote(self.client, second.get_json()["token"], "no")

        reset_response = self.client.post(
            "/admin/events/diaspora-referendum-2026/reset",
            headers=admin_headers(),
            json={},
        )

        self.assertEqual(reset_response.status_code, 200)
        body = reset_response.get_json()
        self.assertEqual(body["ballots_deleted"], 2)
        self.assertEqual(body["affected_voters"], 2)

        board_response = self.client.get("/board?event_id=diaspora-referendum-2026")
        self.assertEqual(board_response.status_code, 200)
        self.assertEqual(board_response.get_json()["ballots"], [])

        with self.app.app_context():
            db = get_db()
            voter_count = db.execute("SELECT COUNT(*) AS count FROM mock_voters").fetchone()["count"]
            voted_count = db.execute("SELECT COUNT(*) AS count FROM voters WHERE has_voted = 1").fetchone()["count"]
            self.assertEqual(voter_count, 3)
            self.assertEqual(voted_count, 0)

    def test_admin_can_reset_demo_data_and_preserve_registry(self):
        auth = accredit(self.client, "12345678901")
        token = auth.get_json()["token"]
        vote(self.client, token, "yes")

        with self.app.app_context():
            artifacts_dir = Path(self.app.config["PROOF_ARTIFACTS_DIR"])
            inputs_dir = Path(self.app.config["PROOF_INPUTS_DIR"])
            (artifacts_dir / "extra-artifact.bin").write_text("demo", encoding="utf-8")
            (inputs_dir / "extra-input.json").write_text("{}", encoding="utf-8")

        reset_response = self.client.post(
            "/admin/reset-demo-data",
            headers=admin_headers(),
            json={"confirmation_text": "RESET DEMO DATA"},
        )

        self.assertEqual(reset_response.status_code, 200)
        body = reset_response.get_json()
        self.assertEqual(body["ballots_deleted"], 1)
        self.assertTrue(body["registry_preserved"])
        self.assertFalse(body["registry_deleted"])
        self.assertTrue(body["voter_sessions_cleared"])
        self.assertTrue(body["biometric_state_cleared"])
        self.assertGreaterEqual(body["proof_artifacts_deleted"], 1)
        self.assertGreaterEqual(body["proof_inputs_deleted"], 1)

        with self.app.app_context():
            db = get_db()
            ballot_count = db.execute("SELECT COUNT(*) AS count FROM ballots").fetchone()["count"]
            registry_count = db.execute("SELECT COUNT(*) AS count FROM mock_voters").fetchone()["count"]
            active_sessions = db.execute(
                "SELECT COUNT(*) AS count FROM voters WHERE session_token_hash != ''"
            ).fetchone()["count"]
            biometric_count = db.execute(
                "SELECT COUNT(*) AS count FROM voters WHERE biometric_verified = 1 OR has_voted = 1"
            ).fetchone()["count"]

            self.assertEqual(ballot_count, 0)
            self.assertEqual(registry_count, 3)
            self.assertEqual(active_sessions, 0)
            self.assertEqual(biometric_count, 0)
            self.assertEqual(list(Path(self.app.config["PROOF_ARTIFACTS_DIR"]).iterdir()), [])
            self.assertEqual(list(Path(self.app.config["PROOF_INPUTS_DIR"]).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
