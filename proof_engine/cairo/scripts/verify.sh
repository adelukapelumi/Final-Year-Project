#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CAIRO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PROOF_FILE=${1:-"$CAIRO_DIR/artifacts/valid_yes.proof.json"}

if ! command -v scarb >/dev/null 2>&1; then
  echo "error: scarb is not installed or not on PATH" >&2
  exit 1
fi

if [ ! -f "$PROOF_FILE" ]; then
  echo "error: proof file not found: $PROOF_FILE" >&2
  exit 1
fi

cd "$CAIRO_DIR"
scarb verify "$PROOF_FILE"
