from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import create_test_app, register, vote


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_replays_public_proof_for_selected_ballot(self):
        auth = register(self.client)
        token = auth.get_json()["token"]
        vote_response = vote(self.client, token, "yes")
        ballot = vote_response.get_json()

        response = self.client.post("/verify", json={"ballot_id": ballot["ballot_id"]})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["ballot_id"], ballot["ballot_id"])
        self.assertTrue(body["verified"])
        self.assertEqual(body["proof_hash"], ballot["proof_hash"])
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


if __name__ == "__main__":
    unittest.main()
