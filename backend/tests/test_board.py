from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import create_test_app, register, vote


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_board_hides_sensitive_fields(self):
        auth = register(self.client)
        token = auth.get_json()["token"]
        vote_response = vote(self.client, token, "yes")
        ballot_id = vote_response.get_json()["ballot_id"]

        response = self.client.get("/board")

        self.assertEqual(response.status_code, 200)
        board_ballot = response.get_json()["ballots"][0]
        self.assertEqual(board_ballot["ballot_id"], ballot_id)
        self.assertIn("proof_hash", board_ballot)
        self.assertIn("timestamp", board_ballot)
        self.assertNotIn("nin", board_ballot)
        self.assertNotIn("nin_hash", board_ballot)
        self.assertNotIn("token", board_ballot)
        self.assertNotIn("vote", board_ballot)
        self.assertNotIn("encrypted_vote", board_ballot)


if __name__ == "__main__":
    unittest.main()
