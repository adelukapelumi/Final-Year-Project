from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import create_test_app, register, vote


class TallyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tally_counts_yes_and_no_correctly(self):
        first = register(self.client, "12345678901")
        second = register(self.client, "23456789012")

        vote(self.client, first.get_json()["token"], "yes")
        vote(self.client, second.get_json()["token"], "no")

        response = self.client.get("/tally")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"yes": 1, "no": 1, "total": 2})


if __name__ == "__main__":
    unittest.main()
