from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    schema_path = Path(current_app.config["SCHEMA_PATH"])
    db.executescript(schema_path.read_text(encoding="utf-8"))
    columns = {row["name"] for row in db.execute("PRAGMA table_info(voters)").fetchall()}
    if "biometric_verified" not in columns:
        db.execute("ALTER TABLE voters ADD COLUMN biometric_verified INTEGER NOT NULL DEFAULT 0")
    if "biometric_verified_at" not in columns:
        db.execute("ALTER TABLE voters ADD COLUMN biometric_verified_at TEXT")
    db.commit()
