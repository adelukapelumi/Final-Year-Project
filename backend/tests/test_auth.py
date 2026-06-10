from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import create_test_app


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_login_alias_registers_and_returns_token(self):
        response = self.client.post("/login", json={"nin": "12345678901"})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["token"])
        self.assertNotIn("nin_hash", body)
        self.assertEqual(body["profile"]["display_name"], "Amara Okafor")
        self.assertEqual(body["profile"]["diaspora_location"], "London, United Kingdom")
        self.assertEqual(body["profile"]["voter_category"], "Eligible Diaspora Voter")
        self.assertEqual(body["biometric"]["verification_mode"], "Camera-based prototype face verification")
        self.assertNotIn("available_probes", body["biometric"])
        self.assertNotIn("recommended_probe_id", body["biometric"])
        self.assertEqual(
            body["fallback_message"],
            "This prototype verifies face presence for demonstration only and does not connect to live INEC, BVAS, or NIMC systems.",
        )

    def test_invalid_nin_is_rejected(self):
        response = self.client.post("/register", json={"nin": "99999999999"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "nin is not registered")


if __name__ == "__main__":
    unittest.main()
