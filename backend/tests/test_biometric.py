from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from test_support import biometric_verify, camera_verify, create_test_app, register, vote


class BiometricVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_camera_capture_verification_succeeds_without_receiving_an_image(self):
        auth = register(self.client)
        token = auth.get_json()["token"]

        response = camera_verify(self.client, token)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["verified"])
        self.assertEqual(body["verification_mode"], "Camera-based prototype face verification")
        self.assertNotIn("image", body)
        self.assertNotIn("frame", body)

    def test_camera_capture_confirmation_is_required(self):
        auth = register(self.client)
        token = auth.get_json()["token"]

        response = self.client.post("/biometric-verify", json={"token": token})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "camera capture confirmation is required")

    def test_biometric_verification_succeeds_with_mock_probe(self):
        auth = register(self.client)
        token = auth.get_json()["token"]

        response = biometric_verify(self.client, token, "diaspora-face-match")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["verified"])

    def test_biometric_verification_rejects_non_matching_probe(self):
        auth = register(self.client)
        token = auth.get_json()["token"]

        response = biometric_verify(self.client, token, "diaspora-face-alt")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.get_json()["verified"])
        self.assertEqual(response.get_json()["error"], "camera-based prototype verification failed")

    def test_biometric_verification_can_start_a_later_event_session(self):
        auth = register(self.client)
        token = auth.get_json()["token"]
        biometric_verify(self.client, token, "diaspora-face-match")
        vote(self.client, token, "yes")

        response = biometric_verify(self.client, token, "diaspora-face-match")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["verified"])


if __name__ == "__main__":
    unittest.main()
