from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import accredit, create_test_app, register, vote


class VoteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_vote_generates_proof_and_persists_ballot(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]

        response = vote(self.client, token, "yes")

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertTrue(body["ballot_id"])
        self.assertEqual(len(body["proof_hash"]), 64)
        self.assertNotIn("proof_path", body)
        self.assertNotIn("public_inputs", body)
        self.assertNotIn("vote", body)

    def test_duplicate_vote_rejected(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]

        first = vote(self.client, token, "no")
        second = vote(self.client, token, "yes")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()["error"], "duplicate vote rejected")

    def test_vote_requires_biometric_verification_before_ballot_access(self):
        auth = register(self.client)
        token = auth.get_json()["token"]

        response = vote(self.client, token, "yes")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "biometric verification required before ballot access")


if __name__ == "__main__":
    unittest.main()
