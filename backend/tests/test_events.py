from __future__ import annotations

import tempfile
import unittest
import sqlite3
from pathlib import Path

from db import get_db
from test_support import create_test_app


class EventCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_test_app(Path(self.temp_dir.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_catalog_has_one_voteable_active_event(self):
        response = self.client.get("/events")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["active_event_id"], "diaspora-referendum-2026")
        self.assertEqual(len(body["events"]), 3)
        voteable = [event for event in body["events"] if event["action_enabled"]]
        self.assertEqual([event["event_id"] for event in voteable], ["diaspora-referendum-2026"])

    def test_legacy_ballots_are_migrated_to_the_active_event(self):
        self.temp_dir.cleanup()
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        db_path = temp_path / "test.sqlite3"
        connection = sqlite3.connect(db_path)
        connection.executescript(
            """
            CREATE TABLE voters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nin_hash TEXT NOT NULL UNIQUE,
                session_token_hash TEXT NOT NULL,
                token_expires_at TEXT NOT NULL,
                biometric_verified INTEGER NOT NULL DEFAULT 0,
                biometric_verified_at TEXT,
                has_voted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE ballots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ballot_id TEXT NOT NULL UNIQUE,
                voter_id INTEGER NOT NULL UNIQUE,
                encrypted_vote TEXT NOT NULL,
                proof_hash TEXT NOT NULL,
                proof_path TEXT NOT NULL,
                public_inputs TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE
            );
            INSERT INTO voters (
                nin_hash,
                session_token_hash,
                token_expires_at
            ) VALUES ('legacy-nin', 'legacy-token', '2099-01-01T00:00:00+00:00');
            INSERT INTO ballots (
                ballot_id,
                voter_id,
                encrypted_vote,
                proof_hash,
                proof_path,
                public_inputs
            ) VALUES ('legacy-ballot', 1, 'encrypted', 'hash', 'path', '{}');
            """
        )
        connection.close()

        app = create_test_app(temp_path)
        with app.app_context():
            db = get_db()
            ballot = db.execute(
                "SELECT event_id FROM ballots WHERE ballot_id = 'legacy-ballot'"
            ).fetchone()
            indexes = db.execute("PRAGMA index_list(ballots)").fetchall()
            unique_index_columns = [
                [column["name"] for column in db.execute(f"PRAGMA index_info('{index['name']}')").fetchall()]
                for index in indexes
                if index["unique"]
            ]

        self.assertEqual(ballot["event_id"], "diaspora-referendum-2026")
        self.assertIn(["voter_id", "event_id"], unique_index_columns)


if __name__ == "__main__":
    unittest.main()
