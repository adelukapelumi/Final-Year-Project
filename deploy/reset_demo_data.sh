#!/usr/bin/env sh
set -eu

DB_PATH="${EVOTING_DATABASE_PATH:-/data/evoting.sqlite3}"
ARTIFACTS_DIR="${EVOTING_PROOF_ARTIFACTS_DIR:-/data/proof_artifacts}"
INPUTS_DIR="${EVOTING_PROOF_INPUTS_DIR:-/data/proof_inputs}"

require_data_path() {
  case "$1" in
    /data|/data/*) ;;
    *)
      echo "Refusing to modify non-/data path: $1" >&2
      exit 1
      ;;
  esac
}

require_data_path "$DB_PATH"
require_data_path "$ARTIFACTS_DIR"
require_data_path "$INPUTS_DIR"

rm -f "$DB_PATH"
mkdir -p "$ARTIFACTS_DIR" "$INPUTS_DIR"
find "$ARTIFACTS_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
find "$INPUTS_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +

echo "Demo deployment data reset complete."
