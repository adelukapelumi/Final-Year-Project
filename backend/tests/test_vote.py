from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from db import get_db
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
        self.assertEqual(body["event_id"], "diaspora-referendum-2026")
        self.assertEqual(body["event_title"], "Diaspora Voting Referendum")
        self.assertTrue(body["nullifier"].startswith("0x"))
        self.assertTrue(body["vote_commitment"].startswith("0x"))
        self.assertEqual(body["verification_status"], "verified")
        self.assertEqual(len(body["previous_chain_hash"]), 64)
        self.assertEqual(len(body["chain_hash"]), 64)
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
        self.assertEqual(second.get_json()["error"], "duplicate nullifier rejected")

    def test_ballot_uniqueness_is_scoped_per_voter_and_event(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        first = vote(self.client, token, "yes")

        with self.app.app_context():
            db = get_db()
            voter_id = db.execute(
                "SELECT id FROM voters ORDER BY id LIMIT 1"
            ).fetchone()["id"]
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
                    chain_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "closed-event-ballot",
                    voter_id,
                    "secure-ballot-audit-drill",
                    "test-encrypted-vote",
                    "0x11111111111111111111111111111111",
                    "0x22222222222222222222222222222222",
                    "0x33333333333333333333333333333333",
                    "test-proof-hash",
                    "test-proof-path",
                    "{}",
                    "verified",
                    "previous-hash",
                    "current-record-hash",
                    "chain-hash",
                ),
            )
            db.commit()

        self.assertEqual(first.status_code, 201)

    def test_vote_rejects_unknown_and_non_active_events(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]

        unknown = vote(self.client, token, "yes", "missing-event")
        upcoming = vote(self.client, token, "yes", "overseas-voter-education-poll")

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.get_json()["error"], "unknown referendum event")
        self.assertEqual(upcoming.status_code, 409)
        self.assertEqual(upcoming.get_json()["error"], "referendum event is not open for voting")

    def test_vote_requires_biometric_verification_before_ballot_access(self):
        auth = register(self.client)
        token = auth.get_json()["token"]

        response = vote(self.client, token, "yes")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "biometric verification required before ballot access")

    def test_vote_rejects_invalid_vote_value(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]

        response = vote(self.client, token, "maybe")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "vote must be one of yes/no/1/0")


if __name__ == "__main__":
    unittest.main()
