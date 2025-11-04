#!/usr/bin/env bash
set -euo pipefail

# Password-protect PDFs with qpdf.
#
# Usage:
#   bash scripts/password_protect_pdfs.sh --dir /path/to/pdfs [--out-dir /path/to/out] [--password 'secret'] [--verbose] [--log-file /path/to/log]
#
# Notes:
# - If --password is omitted, a random password will be generated and written to <out-dir>/password.txt
# - Uses AES-256 if supported by qpdf; falls back to 128-bit if necessary
# - When --verbose is set, detailed per-file diagnostics are printed and written to the log file if provided

DIR=""
OUT_DIR=""
PASSWORD=""
VERBOSE=false
LOG_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      DIR="$2"; shift 2;;
    --out-dir)
      OUT_DIR="$2"; shift 2;;
    --password)
      PASSWORD="$2"; shift 2;;
    --verbose)
      VERBOSE=true; shift 1;;
    --log-file)
      LOG_FILE="$2"; shift 2;;
    *)
      echo "Unknown argument: $1" >&2; exit 2;;
  esac
done

# Simple logging helpers
_ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() {
  local msg
  msg="[$(_ts)] $*"
  echo "$msg"
  if [[ -n "$LOG_FILE" ]]; then
    mkdir -p "$(dirname "$LOG_FILE")" || true
    echo "$msg" >> "$LOG_FILE" || true
  fi
}
vlog() { if [[ "$VERBOSE" == true ]]; then log "$@"; fi }

if [[ -z "$DIR" ]]; then
  echo "--dir is required" >&2
  exit 2
fi

DIR="$(realpath "$DIR")"
if [[ -z "${OUT_DIR}" ]]; then
  OUT_DIR="${DIR}/encrypted"
fi
OUT_DIR="$(realpath -m "$OUT_DIR")"
mkdir -p "$OUT_DIR"

vlog "qpdf version: $(qpdf --version 2>/dev/null || echo 'unknown')"
vlog "Input directory: $DIR"
vlog "Output directory: $OUT_DIR"
if [[ -n "$PASSWORD" ]]; then
  vlog "Using provided password (hidden)"
else
  vlog "No password provided; will generate a random one"
fi

# Generate random password if not provided
if [[ -z "$PASSWORD" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    PASSWORD="$(openssl rand -base64 24 | tr -d '\n' | cut -c1-24)"
  else
    PASSWORD="$(head -c 32 /dev/urandom | base64 | tr -d '\n' | tr -dc 'A-Za-z0-9' | head -c 24)"
  fi
  PASSWORD_FILE="$OUT_DIR/password.txt"
  {
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Input Directory: $DIR"
    echo "Output Directory: $OUT_DIR"
    echo "Password: $PASSWORD"
    echo
    echo "Keep this file secure."
  } > "$PASSWORD_FILE"
  vlog "Random password generated and written to $PASSWORD_FILE"
fi

shopt -s nullglob
# Recursively find all PDF files in subdirectories, similar to how the converter handles HTML files
PDFS=()
while IFS= read -r -d '' file; do
  PDFS+=("$file")
done < <(find "$DIR" -type f \( -iname '*.pdf' \) -print0)

total=${#PDFS[@]}
log "Found $total PDF(s) in $DIR and subdirectories"

encrypted=0
copied=0
skipped=0
failed=0

use_aes256=true
qpdf --help >/dev/null 2>&1 || { echo "qpdf is required." >&2; exit 3; }

for src in "${PDFS[@]}"; do
  # Calculate relative path from input directory to preserve folder structure
  relative_path="${src#$DIR/}"
  dest="$OUT_DIR/$relative_path"

  # Create output directory structure if needed
  dest_dir="$(dirname "$dest")"
  mkdir -p "$dest_dir"

  base="$(basename "$src")"
  vlog "-----"
  log "Processing: $relative_path"
  if [[ -e "$dest" ]]; then
    log "[skip] exists: $base"
    skipped=$((skipped+1))
    continue
  fi

  # Detect if file is already encrypted
  enc_info="$(qpdf --show-encryption "$src" 2>&1 || true)"
  vlog "Encryption info for $base:\n$enc_info"
  if echo "$enc_info" | grep -qiE "encryption|R =|P =|key length"; then
    if echo "$enc_info" | grep -qi "no encryption"; then
      already=false
    else
      already=true
    fi
  else
    already=false
  fi

  if $already; then
    if ! cp -p "$src" "$dest" 2>>"${LOG_FILE:-/dev/null}"; then
      log "[fail] copy failed (already encrypted): $base"
      failed=$((failed+1))
      continue
    fi
    log "[copy] already encrypted: $base"
    copied=$((copied+1))
    continue
  fi

  tmp="${dest}.tmp"
  if $use_aes256; then
    vlog "Trying AES-256 for $base"
    if qpdf --encrypt "$PASSWORD" "$PASSWORD" 256 -- "$src" "$tmp" 1>>"${LOG_FILE:-/dev/null}" 2>&1; then
      :
    else
      vlog "AES-256 failed for $base; falling back to 128-bit"
      use_aes256=false
    fi
  fi
  if ! $use_aes256; then
    if ! qpdf --encrypt "$PASSWORD" "$PASSWORD" 128 -- "$src" "$tmp" 1>>"${LOG_FILE:-/dev/null}" 2>&1; then
      log "[fail] encryption failed: $base"
      failed=$((failed+1))
      rm -f "$tmp" || true
      continue
    fi
  fi
  if ! mv -f "$tmp" "$dest" 2>>"${LOG_FILE:-/dev/null}"; then
    log "[fail] move failed: $base"
    failed=$((failed+1))
    rm -f "$tmp" || true
    continue
  fi
  log "[enc]  $base"
  encrypted=$((encrypted+1))
done

echo
log "Summary:"
log "  Encrypted: $encrypted"
log "  Copied (already encrypted): $copied"
log "  Skipped (exists in output): $skipped"
log "  Failed: $failed"

# Return non-zero if any failures occurred so callers can detect problems
if [[ "$failed" -gt 0 ]]; then
  exit 1
fi
exit 0


