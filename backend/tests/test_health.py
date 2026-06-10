from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import create_test_app


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_returns_ok_without_touching_proof_engine(self):
        app = create_test_app(Path(self.temp_dir.name), {"PROOF_BINARY_PATH": Path(self.temp_dir.name) / "missing-binary"})
        client = app.test_client()

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_health_proof_reports_binary_availability_without_exposing_paths(self):
        temp_path = Path(self.temp_dir.name)
        binary_path = temp_path / "referendum_acceptance_winterfell.exe"
        binary_path.write_text("test-binary", encoding="utf-8")
        app = create_test_app(temp_path, {"PROOF_BINARY_PATH": binary_path})
        client = app.test_client()

        response = client.get("/health/proof")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok", "proof_engine": "available"})
        self.assertNotIn(str(binary_path), response.get_data(as_text=True))

    def test_cors_allows_authorization_header_for_configured_origin(self):
        app = create_test_app(Path(self.temp_dir.name), {"ALLOWED_ORIGINS": "https://frontend.example.com"})
        client = app.test_client()

        response = client.options(
            "/vote",
            headers={
                "Origin": "https://frontend.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "https://frontend.example.com")
        allow_headers = response.headers.get("Access-Control-Allow-Headers", "")
        self.assertIn("Authorization", allow_headers)
        self.assertIn("Content-Type", allow_headers)


if __name__ == "__main__":
    unittest.main()
