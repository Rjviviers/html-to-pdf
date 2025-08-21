#!/usr/bin/env bash
set -euo pipefail

# Password-protect PDFs with qpdf.
#
# Usage:
#   bash scripts/password_protect_pdfs.sh --dir /path/to/pdfs [--out-dir /path/to/out] [--password 'secret']
#
# Notes:
# - If --password is omitted, a random password will be generated and written to <out-dir>/password.txt
# - Uses AES-256 if supported by qpdf; falls back to 128-bit if necessary

DIR=""
OUT_DIR=""
PASSWORD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      DIR="$2"; shift 2;;
    --out-dir)
      OUT_DIR="$2"; shift 2;;
    --password)
      PASSWORD="$2"; shift 2;;
    *)
      echo "Unknown argument: $1" >&2; exit 2;;
  esac
done

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
fi

shopt -s nullglob
PDFS=("$DIR"/*.pdf)

total=${#PDFS[@]}
echo "Found $total PDF(s) in $DIR"

encrypted=0
copied=0
skipped=0
failed=0

use_aes256=true
qpdf --help >/dev/null 2>&1 || { echo "qpdf is required." >&2; exit 3; }

for src in "${PDFS[@]}"; do
  base="$(basename "$src")"
  dest="$OUT_DIR/$base"
  if [[ -e "$dest" ]]; then
    echo "[skip] exists: $base"
    ((skipped++))
    continue
  fi

  # Detect if file is already encrypted
  if qpdf --show-encryption "$src" 2>/dev/null | grep -qiE "encryption|R =|P =|key length"; then
    # Some qpdf versions always show encryption section; check for explicit marker
    if qpdf --show-encryption "$src" 2>/dev/null | grep -qi "no encryption"; then
      already=false
    else
      already=true
    fi
  else
    already=false
  fi

  if $already; then
    cp -p "$src" "$dest"
    echo "[copy] already encrypted: $base"
    ((copied++))
    continue
  fi

  tmp="${dest}.tmp"
  if $use_aes256; then
    if qpdf --encrypt "$PASSWORD" "$PASSWORD" 256 -- "$src" "$tmp" 2>/dev/null; then
      :
    else
      use_aes256=false
    fi
  fi
  if ! $use_aes256; then
    if ! qpdf --encrypt "$PASSWORD" "$PASSWORD" 128 -- "$src" "$tmp"; then
      echo "[fail] $base"
      ((failed++))
      rm -f "$tmp" || true
      continue
    fi
  fi
  mv -f "$tmp" "$dest"
  echo "[enc]  $base"
  ((encrypted++))
done

echo
echo "Summary:"
echo "  Encrypted: $encrypted"
echo "  Copied (already encrypted): $copied"
echo "  Skipped (exists in output): $skipped"
echo "  Failed: $failed"

exit 0


