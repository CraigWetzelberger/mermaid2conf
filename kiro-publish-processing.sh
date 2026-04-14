#!/bin/bash
# Usage: kiro-publish-processing.sh <source.md> <output_dir>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_FILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTPUT_DIR="${2:-$SCRIPT_DIR/output}"

rm -rf "$OUTPUT_DIR"
uv run --project "$SCRIPT_DIR" kiro-publish-processing "$INPUT_FILE" "$OUTPUT_DIR"
