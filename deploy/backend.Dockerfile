FROM rust:1-bookworm AS proof-builder

WORKDIR /build/proof_engine/winterfell

COPY proof_engine/winterfell/Cargo.toml proof_engine/winterfell/Cargo.lock ./
COPY proof_engine/winterfell/src ./src

RUN cargo build --release


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EVOTING_DATABASE_PATH=/data/evoting.sqlite3 \
    EVOTING_PROOF_ARTIFACTS_DIR=/data/proof_artifacts \
    EVOTING_PROOF_INPUTS_DIR=/data/proof_inputs \
    EVOTING_PROOF_BINARY_PATH=/app/proof_engine/winterfell/target/release/referendum_acceptance_winterfell

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY proof_engine /app/proof_engine
RUN mkdir -p /data/proof_artifacts /data/proof_inputs /app/proof_engine/winterfell/target/release
COPY --from=proof-builder /build/proof_engine/winterfell/target/release/referendum_acceptance_winterfell /app/proof_engine/winterfell/target/release/referendum_acceptance_winterfell

EXPOSE 8000

CMD ["sh", "-c", "mkdir -p /data/proof_artifacts /data/proof_inputs && exec gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile -"]
