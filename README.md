# Diaspora E-voting Prototype

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

## Public Verification

The prototype supports server-mediated public verification through `POST /verify`.

- Submit `{ "ballot_id": "<ballot id>" }` to `/verify`.
- The backend looks up the selected ballot receipt and re-runs the Winterfell verifier for that proof artifact.
- The public board remains privacy-preserving and only publishes `ballot_id`, `proof_hash`, and `timestamp`.
- The verification response is intended for receipt checking only and does not expose NIN, NIN hash, vote choice, decrypted vote, or session token.

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
