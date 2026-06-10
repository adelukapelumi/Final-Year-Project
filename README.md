# Diaspora E-voting Prototype

This prototype uses mock NIN accreditation and mock camera-based facial verification only. It does not connect to live INEC, NIMC, BVAS, presidential-election, candidate, party, blockchain, or other production election systems.

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

The Vite frontend can call the backend through `VITE_API_BASE_URL`. If that variable is unset, local development can still use the existing Vite proxy to `http://127.0.0.1:5000`.

## Accreditation Flow

The current accreditation flow is intentionally development-only:

- mock NIN verification checks the submitted 11-digit NIN against the DB-backed mock voter registry
- on first startup, existing records from `backend/data/mock_nin_registry.json` seed the registry table if it is empty
- camera-based prototype verification confirms face presence using a browser camera session
- ballot access is granted only after the mock NIN is eligible, the voter has not already voted, and the prototype face check passes

Fallback notice shown in the UI:

`This prototype verifies face presence for demonstration only and does not connect to live INEC, BVAS, or NIMC systems.`

## Deployment

### Recommended Architecture

- Deploy the frontend as a separate web service.
- Deploy the Flask backend API as a Railway service.
- Bundle the Winterfell proof engine inside the backend deployment.
- Keep SQLite and proof artifacts on a Railway volume mounted at `/data`.

Important repository constraint:

- Build the backend from the repository root, or from a Docker build context that includes both `backend/` and `proof_engine/`.
- Do not set the Railway root directory to only `backend/` unless `proof_engine/` is still included in the build context. The backend depends on `proof_engine/winterfell`.

### Railway Backend Setup

- Service source: repository root
- Dockerfile path: `deploy/backend.Dockerfile`
- Railway variable: `RAILWAY_DOCKERFILE_PATH=deploy/backend.Dockerfile`
- Healthcheck path: `/health`
- Volume mount path: `/data`
- Start command inside the container: `gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile -`

Required Railway variables:

- `EVOTING_SECRET_KEY=<strong generated secret>`
- `EVOTING_ADMIN_TOKEN=<strong admin token>`
- `EVOTING_DATABASE_PATH=/data/evoting.sqlite3`
- `EVOTING_PROOF_ARTIFACTS_DIR=/data/proof_artifacts`
- `EVOTING_PROOF_INPUTS_DIR=/data/proof_inputs`
- `EVOTING_ALLOWED_ORIGINS=https://<frontend-domain>`
- `EVOTING_TOKEN_TTL_SECONDS=86400`

Notes:

- `EVOTING_ALLOWED_ORIGINS` accepts a comma-separated list. Local frontend origins on `localhost` and `127.0.0.1` are still allowed for development.
- CORS is intentionally allowlist-based. Do not use wildcard origins in production.
- The backend allows the `Authorization` header for voter endpoints and `X-Admin-Token` for prototype admin endpoints.
- `GET /health` returns `{"status":"ok"}` without generating a proof.
- `GET /health/proof` checks whether the configured proof binary is available without exposing private absolute paths.
- One Gunicorn worker is intentional because this demo uses SQLite writes and persistent proof artifacts.

### Prototype Registry Admin

The hidden `/admin` route is for prototype/demo registry management only.

What it is for:

- validating an admin session with `X-Admin-Token: <EVOTING_ADMIN_TOKEN>`
- creating mock eligible voters without redeploying
- deactivating or deleting demo voters
- resetting one voter, the active event, or all demo data without manually editing Railway volume contents

What it is not:

- a full INEC officer dashboard
- a production election management system
- a live NIMC, NIN, BVAS, blockchain, or candidate-management integration

Privacy behavior:

- the console stores the admin token in browser `sessionStorage` only
- the console shows masked NIN values and last-four digits only
- the console does not show raw vote choices, decrypted votes, session tokens, secret values, or private proof paths

### Safe Demo Reset Options

For deployed prototypes, prefer `/admin` for reset operations.

Available prototype reset actions:

- reset one mock voter: clears that voter session, biometric state, ballots, and linked proof artifacts
- reset the active event: clears only that event's ballots/proofs and recalculates `has_voted`
- reset demo data: clears ballots, proof artifacts, proof inputs, voter sessions, biometric state, and `has_voted` flags while keeping the mock voter registry intact

The destructive frontend reset action requires the confirmation text `RESET DEMO DATA`.

### Persistent Storage Plan

Mount one Railway volume at `/data`.

Keep all demo persistence there:

- SQLite database: `/data/evoting.sqlite3`
- generated proof artifacts: `/data/proof_artifacts`
- generated proof input snapshots: `/data/proof_inputs`

This matters for public verification after redeploy. Existing ballots store proof artifact locations under the persistent `/data` path, so changing the storage path or failing to mount the volume can break later verification.

### Secret-Key Stability

Keep `EVOTING_SECRET_KEY` stable after votes are cast.

Why it matters:

- changing the secret invalidates active login sessions
- the ballot encryption key is derived from the secret, so changing it may prevent tally decryption for previously encrypted ballots

Use a strong generated secret in Railway variables and do not commit it to the repository.

### Demo Reset Command

Destructive demo-only reset:

```bash
sh deploy/reset_demo_data.sh
```

What it clears:

- `/data/evoting.sqlite3`
- `/data/proof_artifacts/*`
- `/data/proof_inputs/*`

The script refuses to touch paths outside `/data`.

Use this shell reset only when the admin console is unavailable. In normal deployed prototype use, prefer the protected `/admin` reset actions.

### Frontend Deployment

The frontend reads `VITE_API_BASE_URL` for API calls. No deployed API call should rely on the Vite local proxy.

#### Vercel

- Root directory: `frontend`
- Build command: `pnpm build`
- Output directory: `dist`
- Required variable: `VITE_API_BASE_URL=https://<backend-domain>`
- SPA route fallback: `frontend/vercel.json`

#### Railway Static Frontend Option

- Service source: repository root
- Dockerfile path: `deploy/frontend.Dockerfile`
- Build arg or environment variable: `VITE_API_BASE_URL=https://<backend-domain>`

The frontend Dockerfile builds the Vite app and serves `dist/` with SPA fallback support.

### Camera Requirement

Browser camera access works only on `https://` origins or `localhost`. If the deployed frontend is served over plain HTTP, camera verification will be blocked by the browser.

## Post-Deployment Smoke Test

1. Open the backend health check at `/health` and confirm HTTP 200 with `{"status":"ok"}`.
2. Open the frontend.
3. Confirm the frontend can fetch `/events`.
4. Open `/admin`, validate the admin token, and confirm the Prototype Registry Admin loads.
5. Create or review a mock eligible voter record from the admin console.
6. Accredit using a mock NIN from the admin registry.
7. Complete the camera verification step.
8. Proceed to the active referendum event.
9. Cast a `yes` or `no` vote.
10. Confirm the receipt appears.
11. Verify the ballot from the public board.
12. Confirm the tally updates for the active event.
13. Try a duplicate vote and confirm it is rejected.
14. Use the admin console to reset the demo voter or active event and confirm the voter can re-run the prototype flow.

## Troubleshooting

### CORS Errors

- Confirm `EVOTING_ALLOWED_ORIGINS` includes the exact frontend origin, including scheme and host.
- If multiple frontend origins are needed, use a comma-separated list.
- If authenticated requests fail preflight, confirm the browser is sending `Authorization` and the backend is using the deployed config.

### Missing Proof Binary

- Confirm the backend was built from the repository root with `proof_engine/` included in the Docker context.
- Confirm Railway is using `deploy/backend.Dockerfile`.
- Check `/health/proof` to confirm the bundled Winterfell binary is available.

### Proof Verification Fails After Redeploy

- Confirm the Railway volume is mounted at `/data`.
- Confirm proof artifacts were persisted under `/data/proof_artifacts`.
- Confirm `EVOTING_PROOF_ARTIFACTS_DIR` and `EVOTING_PROOF_INPUTS_DIR` still point to `/data/...`.

### SQLite Reset

- Use `sh deploy/reset_demo_data.sh` only for destructive demo resets.
- After reset, the backend will recreate the database schema on next startup.

### Camera Permission Blocked

- Confirm the frontend is running on HTTPS or `localhost`.
- Recheck browser camera permissions for the deployed domain.

### Frontend Route Refresh Returns 404

- On Vercel, keep `frontend/vercel.json` in place for SPA rewrites.
- On Railway, use `deploy/frontend.Dockerfile` so all routes fall back to `index.html`.

### Railway Cold Start or First Request Delay

- Sleeping services or cold starts can delay the first request.
- Use `/health` as the healthcheck endpoint because it is lightweight and does not trigger proof generation.

## Production Note

Production deployment would require authorized and compliant integration with real election and identity systems, including appropriate INEC and NIMC controls. Those integrations are not part of this repository.

## Rust/Cargo Requirement

Rust and Cargo are required locally because `POST /vote` calls the Winterfell proof engine through the Flask backend.

If Rust/Cargo is missing locally, login and registration may still work, but voting will fail during proof generation.

## Winterfell Benchmarks

Run the accepted-ballot benchmark from the repository root:

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

The benchmark also stores generated proof artifacts under `proof_engine/winterfell/benchmarks/artifacts/` for local inspection while keeping them out of Git by default.
