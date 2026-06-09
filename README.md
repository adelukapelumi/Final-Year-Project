# Diaspora E-voting Prototype

This prototype uses mock NIN accreditation and mock facial verification only. It does not connect to live INEC, NIMC, BVAS, presidential-election, candidate, party, or blockchain systems.

## Local Run

### Backend

Run the Flask backend locally at `http://127.0.0.1:5000`.

```bash
cd backend
python -m pip install -r requirements.txt
python app.py
```

### Frontend

Run the frontend locally with `pnpm dev`.

```bash
cd frontend
pnpm install
pnpm dev
```

The Vite frontend expects the backend at `http://127.0.0.1:5000` and proxies the existing Flask endpoints there during local development.

## Accreditation Flow

The current accreditation flow is intentionally development-only:

- mock NIN verification checks the submitted 11-digit NIN against `backend/data/mock_nin_registry.json`
- BVAS-inspired prototype verification runs a mock facial-verification step using preloaded development face-sample IDs
- ballot access is granted only after the mock NIN is eligible, the voter has not already voted, and the mock facial verification passes

Fallback notice shown in the UI:

`This prototype simulates biometric accreditation and does not connect to live INEC or NIMC systems.`

## Production Note

Production deployment would require authorized and compliant integration with INEC/NIMC systems and an approved biometric-verification stack. Those integrations are not part of this repository.

### Rust/Cargo Requirement

Rust and Cargo are required locally because `POST /vote` calls the Winterfell proof engine through the Flask backend.

If Rust/Cargo is missing, login and registration may still work, but voting will fail during proof generation.

## Winterfell Benchmarks

Run the real Winterfell accepted-ballot benchmark from the repository root:

```bash
python proof_engine/winterfell/benchmarks/run_benchmarks.py
```

What it does:

- builds `proof_engine/winterfell` in release mode unless `--skip-build` is passed
- runs the real Winterfell binary for `prove` and `verify`
- benchmarks `1`, `10`, and `100` accepted ballots
- writes the latest benchmark outputs to:
  - `proof_engine/winterfell/benchmarks/results/benchmark_results.json`
  - `proof_engine/winterfell/benchmarks/results/benchmark_results.csv`
- writes timestamped archive copies under `proof_engine/winterfell/benchmarks/results/archive/`

The benchmark also stores the generated proof artifacts under `proof_engine/winterfell/benchmarks/artifacts/` for local inspection, while keeping them out of Git by default.
