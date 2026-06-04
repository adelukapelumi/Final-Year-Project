#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CAIRO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
INPUT_FILE=${1:-"$CAIRO_DIR/inputs/valid_yes.json"}

if ! command -v scarb >/dev/null 2>&1; then
  echo "error: scarb is not installed or not on PATH" >&2
  exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
  echo "error: input file not found: $INPUT_FILE" >&2
  exit 1
fi

CASE_NAME=$(basename "$INPUT_FILE" .json)
ARTIFACT_DIR="$CAIRO_DIR/artifacts"
PROOF_DEST="$ARTIFACT_DIR/$CASE_NAME.proof.json"

cd "$CAIRO_DIR"
scarb clean
scarb execute -p referendum_acceptance --output standard --arguments-file "$INPUT_FILE"
scarb prove --execution-id 1

PROOF_SOURCE="$CAIRO_DIR/target/execute/referendum_acceptance/execution1/proof/proof.json"

if [ ! -f "$PROOF_SOURCE" ]; then
  echo "error: expected proof artifact was not generated at $PROOF_SOURCE" >&2
  exit 1
fi

mkdir -p "$ARTIFACT_DIR"
cp "$PROOF_SOURCE" "$PROOF_DEST"
echo "Proof copied to: $PROOF_DEST"
