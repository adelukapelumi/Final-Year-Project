from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import accredit, create_test_app, vote


class TallyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tally_counts_yes_and_no_correctly(self):
        first = accredit(self.client, "12345678901")
        second = accredit(self.client, "23456789012")

        vote(self.client, first.get_json()["token"], "yes")
        vote(self.client, second.get_json()["token"], "no")

        response = self.client.get("/tally")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "event": {
                    "event_id": "diaspora-referendum-2026",
                    "title": "Diaspora Voting Referendum",
                    "question": "Should secure diaspora voting be enabled for eligible Nigerians abroad?",
                    "ballot_type": "Binary referendum",
                    "status": "Active",
                    "description": "A prototype referendum on enabling secure voting access for eligible Nigerians abroad.",
                    "start_date": "June 10, 2026",
                    "end_date": "June 30, 2026",
                    "action_enabled": True,
                },
                "yes": 1,
                "no": 1,
                "total": 2,
                "total_registered_voters": 3,
                "total_ballots_cast": 2,
                "remaining_voters": 1,
                "status": "Active",
            },
        )

    def test_tally_marks_election_completed_when_all_registered_voters_have_voted(self):
        first = accredit(self.client, "12345678901")
        second = accredit(self.client, "23456789012")
        third = accredit(self.client, "34567890123")

        vote(self.client, first.get_json()["token"], "yes")
        vote(self.client, second.get_json()["token"], "no")
        vote(self.client, third.get_json()["token"], "yes")

        response = self.client.get("/tally")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total_registered_voters"], 3)
        self.assertEqual(response.get_json()["total_ballots_cast"], 3)
        self.assertEqual(response.get_json()["remaining_voters"], 0)
        self.assertEqual(response.get_json()["status"], "Completed")

    def test_tally_filters_results_by_event(self):
        auth = accredit(self.client)
        token = auth.get_json()["token"]
        vote(self.client, token, "yes")

        active = self.client.get("/tally?event_id=diaspora-referendum-2026")
        upcoming = self.client.get("/tally?event_id=overseas-voter-education-poll")
        closed = self.client.get("/tally?event_id=secure-ballot-audit-drill")

        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.get_json()["yes"], 1)
        self.assertEqual(active.get_json()["total"], 1)
        self.assertEqual(upcoming.status_code, 200)
        self.assertEqual(upcoming.get_json()["total"], 0)
        self.assertEqual(upcoming.get_json()["status"], "Coming Soon")
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.get_json()["yes"], 31)
        self.assertEqual(closed.get_json()["no"], 17)
        self.assertEqual(closed.get_json()["total_ballots_cast"], 48)
        self.assertEqual(closed.get_json()["status"], "Completed")


if __name__ == "__main__":
    unittest.main()
