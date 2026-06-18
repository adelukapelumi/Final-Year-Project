from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from test_support import accredit, create_test_app, vote


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_replays_public_proof_for_selected_ballot(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        vote_response = vote(self.client, token, "yes")
        ballot = vote_response.get_json()

        response = self.client.post(
            "/verify",
            json={
                "ballot_id": ballot["ballot_id"],
                "event_id": "diaspora-referendum-2026",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["ballot_id"], ballot["ballot_id"])
        self.assertEqual(body["event_id"], "diaspora-referendum-2026")
        self.assertTrue(body["verified"])
        self.assertEqual(body["proof_hash"], ballot["proof_hash"])
        self.assertEqual(body["nullifier"], ballot["nullifier"])
        self.assertEqual(body["vote_commitment"], ballot["vote_commitment"])
        self.assertEqual(body["verification_status"], "verified")
        self.assertNotIn("vote", body)
        self.assertNotIn("encrypted_vote", body)
        self.assertNotIn("nin", body)
        self.assertNotIn("nin_hash", body)
        self.assertNotIn("token", body)

    def test_verify_requires_known_ballot_id(self):
        missing_id = self.client.post("/verify", json={})
        unknown_id = self.client.post("/verify", json={"ballot_id": "missing-ballot"})

        self.assertEqual(missing_id.status_code, 400)
        self.assertEqual(missing_id.get_json()["error"], "ballot_id is required")
        self.assertEqual(unknown_id.status_code, 404)
        self.assertEqual(unknown_id.get_json()["error"], "ballot not found")

    def test_verify_rejects_the_wrong_event_context(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        ballot = vote(self.client, token, "yes").get_json()

        response = self.client.post(
            "/verify",
            json={
                "ballot_id": ballot["ballot_id"],
                "event_id": "secure-ballot-audit-drill",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "ballot not found")

    def test_verify_accepts_closed_demo_board_ballot(self):
        board_response = self.client.get("/board?event_id=secure-ballot-audit-drill")
        ballot = board_response.get_json()["ballots"][0]

        response = self.client.post(
            "/verify",
            json={
                "ballot_id": ballot["ballot_id"],
                "event_id": "secure-ballot-audit-drill",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["ballot_id"], ballot["ballot_id"])
        self.assertEqual(body["event_id"], "secure-ballot-audit-drill")
        self.assertTrue(body["verified"])
        self.assertEqual(body["proof_hash"], ballot["proof_hash"])

    def test_verification_bundle_exports_public_artifact_without_private_fields(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        ballot = vote(self.client, token, "yes").get_json()

        response = self.client.get(
            f"/verify/bundle/{ballot['ballot_id']}?event_id=diaspora-referendum-2026"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["ballot_id"], ballot["ballot_id"])
        self.assertEqual(body["event_id"], "diaspora-referendum-2026")
        self.assertEqual(body["proof_hash"], ballot["proof_hash"])
        self.assertEqual(body["nullifier"], ballot["nullifier"])
        self.assertEqual(body["vote_commitment"], ballot["vote_commitment"])
        self.assertEqual(body["public_inputs"]["event_id"], "diaspora-referendum-2026")
        self.assertEqual(body["public_inputs"]["nullifier"], ballot["nullifier"])
        self.assertEqual(body["public_inputs"]["vote_commitment"], ballot["vote_commitment"])
        self.assertEqual(body["previous_chain_hash"], ballot["previous_chain_hash"])
        self.assertEqual(body["chain_hash"], ballot["chain_hash"])
        self.assertTrue(base64.b64decode(body["proof_artifact_base64"]))
        self.assertNotIn("vote", body)
        self.assertNotIn("encrypted_vote", body)
        self.assertNotIn("nin", body)
        self.assertNotIn("nin_hash", body)
        self.assertNotIn("voter_secret", body)
        self.assertNotIn("ballot_salt", body)
        self.assertNotIn("proof_path", body)


if __name__ == "__main__":
    unittest.main()
