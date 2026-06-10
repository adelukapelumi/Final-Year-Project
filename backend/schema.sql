CREATE TABLE IF NOT EXISTS mock_voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nin_hash TEXT NOT NULL UNIQUE,
    nin_last4 TEXT NOT NULL,
    masked_nin TEXT NOT NULL,
    display_name TEXT NOT NULL,
    diaspora_location TEXT NOT NULL,
    voter_category TEXT NOT NULL DEFAULT 'Eligible Diaspora Voter',
    mock_biometric_enabled INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (mock_biometric_enabled IN (0, 1)),
    CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nin_hash TEXT NOT NULL UNIQUE,
    session_token_hash TEXT NOT NULL,
    token_expires_at TEXT NOT NULL,
    biometric_verified INTEGER NOT NULL DEFAULT 0,
    biometric_verified_at TEXT,
    has_voted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (biometric_verified IN (0, 1)),
    CHECK (has_voted IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ballots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ballot_id TEXT NOT NULL UNIQUE,
    voter_id INTEGER NOT NULL,
    event_id TEXT NOT NULL DEFAULT 'diaspora-referendum-2026',
    encrypted_vote TEXT NOT NULL,
    proof_hash TEXT NOT NULL,
    proof_path TEXT NOT NULL,
    public_inputs TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
    UNIQUE (voter_id, event_id)
);
