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

### Rust/Cargo Requirement

Rust and Cargo are required locally because `POST /vote` calls the Winterfell proof engine through the Flask backend.

If Rust/Cargo is missing, login and registration may still work, but voting will fail during proof generation.
