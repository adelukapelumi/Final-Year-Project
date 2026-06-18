from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import accredit, create_test_app, vote


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_board_hides_sensitive_fields(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        vote_response = vote(self.client, token, "yes")
        ballot_id = vote_response.get_json()["ballot_id"]

        response = self.client.get("/board")

        self.assertEqual(response.status_code, 200)
        board_ballot = response.get_json()["ballots"][0]
        self.assertEqual(board_ballot["ballot_id"], ballot_id)
        self.assertEqual(board_ballot["event_id"], "diaspora-referendum-2026")
        self.assertEqual(board_ballot["event_title"], "Diaspora Voting Referendum")
        self.assertIn("nullifier", board_ballot)
        self.assertIn("vote_commitment", board_ballot)
        self.assertIn("proof_hash", board_ballot)
        self.assertIn("timestamp", board_ballot)
        self.assertIn("verification_status", board_ballot)
        self.assertIn("previous_chain_hash", board_ballot)
        self.assertIn("chain_hash", board_ballot)
        self.assertNotIn("nin", board_ballot)
        self.assertNotIn("nin_hash", board_ballot)
        self.assertNotIn("token", board_ballot)
        self.assertNotIn("vote", board_ballot)
        self.assertNotIn("encrypted_vote", board_ballot)
        self.assertNotIn("proof_path", board_ballot)
        self.assertNotIn("public_inputs", board_ballot)
        self.assertNotIn("biometric_verified", board_ballot)
        self.assertNotIn("face_template_id", board_ballot)

    def test_board_filters_ballots_by_event(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        vote(self.client, token, "yes")

        active = self.client.get("/board?event_id=diaspora-referendum-2026")
        upcoming = self.client.get("/board?event_id=overseas-voter-education-poll")
        closed = self.client.get("/board?event_id=secure-ballot-audit-drill")

        self.assertEqual(active.status_code, 200)
        self.assertEqual(len(active.get_json()["ballots"]), 1)
        self.assertEqual(active.get_json()["event"]["title"], "Diaspora Voting Referendum")
        self.assertEqual(upcoming.status_code, 200)
        self.assertEqual(upcoming.get_json()["ballots"], [])
        self.assertEqual(upcoming.get_json()["event"]["status"], "Upcoming")
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(len(closed.get_json()["ballots"]), 48)
        self.assertEqual(closed.get_json()["event"]["status"], "Closed")
        self.assertTrue(closed.get_json()["ballots"][0]["ballot_id"].startswith("audit-drill-"))

    def test_board_chain_verification_succeeds_for_active_event(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        vote(self.client, token, "yes")

        response = self.client.get("/board/verify-chain?event_id=diaspora-referendum-2026")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["verified"])
        self.assertEqual(body["checked_ballots"], 1)
        self.assertEqual(body["event_id"], "diaspora-referendum-2026")

    def test_board_supports_pagination_parameters(self):
        first = accredit(self.client, "12345678901")
        second = accredit(self.client, "23456789012")

        vote(self.client, first.get_json()["token"], "yes")
        vote(self.client, second.get_json()["token"], "no")

        response = self.client.get("/board?event_id=diaspora-referendum-2026&page=1&page_size=1")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body["ballots"]), 1)
        self.assertEqual(body["pagination"], {"page": 1, "page_size": 1})


if __name__ == "__main__":
    unittest.main()
