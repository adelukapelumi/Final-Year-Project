#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CAIRO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PROOF_FILE=${1:-"$CAIRO_DIR/artifacts/valid_yes.proof.json"}

if [ ! -f "$PROOF_FILE" ]; then
  echo "error: proof file not found: $PROOF_FILE" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$PROOF_FILE"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$PROOF_FILE"
elif command -v openssl >/dev/null 2>&1; then
  openssl dgst -sha256 "$PROOF_FILE"
else
  echo "error: no SHA-256 tool found (sha256sum, shasum, or openssl)" >&2
  exit 1
fi
