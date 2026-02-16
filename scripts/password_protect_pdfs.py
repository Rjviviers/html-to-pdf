#!/usr/bin/env python3
"""
Password-protect all PDFs in a directory with a single randomly generated password.

Behavior:
- Generates a strong random password at startup and writes it to a file
- Encrypts every non-encrypted PDF found in the input directory and writes the
  protected files into an "encrypted" subfolder (or a custom output directory)
- Copies PDFs that are already encrypted into the output directory (so the
  output set is complete)

Usage:
  python scripts/password_protect_pdfs.py --dir pdf-export

Options:
  --dir            Input directory containing PDFs (default: pdf-export)
  --out-dir        Output directory for encrypted PDFs (default: <dir>/encrypted)
  --password-file  File path to write the generated password (default: <out-dir>/password.txt)
  --length         Password length (default: 20)
  --symbols        Include symbols in password (default: enabled)
  --no-symbols     Disable symbols in password
  --suffix         Temp output suffix used during write (default: .tmp)
"""

import argparse
import os
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple, Dict

from pypdf import PdfReader, PdfWriter

import secrets
import string


def generate_password(length: int = 20, include_symbols: bool = True) -> str:
    """Generate a strong random password.

    Ensures at least one character from each selected group is included.
    """
    if length < 8:
        length = 8

    alphabet_groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
    if include_symbols:
        # Modest and broadly accepted subset of symbols to avoid shell/filename issues
        symbols = "!@#$%^&*()-_=+[]{}:,.?"
        alphabet_groups.append(symbols)

    # Start with one from each group
    password_chars = [secrets.choice(group) for group in alphabet_groups]
    remaining_len = max(0, length - len(password_chars))
    full_alphabet = "".join(alphabet_groups)
    password_chars.extend(secrets.choice(full_alphabet) for _ in range(remaining_len))
    # Shuffle securely by selecting new random order
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]
    return "".join(password_chars)


def find_pdfs(directory: Path, recursive: bool = False) -> List[Path]:
    """Find .pdf files in directory.

    If recursive is False, scans only the top-level. If True, scans all subfolders.
    Returns a sorted list of file paths.
    """
    if recursive:
        results = [p for p in directory.rglob("*.pdf") if p.is_file()]
    else:
        results = [p for p in directory.glob("*.pdf") if p.is_file()]
    return sorted(results)


def is_pdf_encrypted(pdf_path: Path) -> bool:
    reader = PdfReader(str(pdf_path))
    return bool(getattr(reader, "is_encrypted", False))


def encrypt_pdf_to_path(input_pdf: Path, output_pdf: Path, password: str, temp_suffix: str = ".tmp") -> None:
    """Encrypt a PDF and write to a new path using AES-256 if available, else fallback.

    Writes to a temporary file in the output directory, then atomically moves into place.
    """
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    # Try strong AES-256 first; if unavailable, progressively fallback to RC4-128 and legacy APIs
    try:
        writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
    except Exception:
        try:
            # Prefer RC4-128 if AES-256 is unavailable or cryptography is missing
            writer.encrypt(user_password=password, owner_password=password, algorithm="RC4-128")
        except Exception:
            try:
                # Legacy PyPDF2 signature
                writer.encrypt(user_pwd=password, owner_pwd=password, use_128bit=True)
            except Exception:
                try:
                    # Newer API without specifying algorithm (library default)
                    writer.encrypt(user_password=password, owner_password=password)
                except Exception:
                    # Very old API: single-arg
                    writer.encrypt(password)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_pdf.with_suffix(output_pdf.suffix + temp_suffix)
    with open(temp_path, "wb") as tmp_f:
        writer.write(tmp_f)
    try:
        os.replace(temp_path, output_pdf)
    except OSError:
        try:
            if output_pdf.exists():
                os.remove(output_pdf)
        except OSError:
            pass
        shutil.move(str(temp_path), str(output_pdf))


def process_pdf_worker(input_path: str, output_path: str, password: str, temp_suffix: str) -> Tuple[str, Dict[str, int]]:
    """Worker: process a single PDF.

    Returns a tuple of (action, metrics) where action in {encrypted, copied, skipped}.
    metrics may include sizes for logging.
    """
    src = Path(input_path)
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        return ("skipped", {"src_size": src.stat().st_size, "dst_size": dest.stat().st_size})

    try:
        reader = PdfReader(str(src))
        if getattr(reader, "is_encrypted", False):
            shutil.copy2(str(src), str(dest))
            return ("copied", {"src_size": src.stat().st_size, "dst_size": dest.stat().st_size})
        # Not encrypted: encrypt to destination
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        try:
            writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
        except Exception:
            try:
                writer.encrypt(user_password=password, owner_password=password, algorithm="RC4-128")
            except Exception:
                try:
                    writer.encrypt(user_pwd=password, owner_pwd=password, use_128bit=True)
                except Exception:
                    try:
                        writer.encrypt(user_password=password, owner_password=password)
                    except Exception:
                        writer.encrypt(password)

        temp_path = dest.with_suffix(dest.suffix + temp_suffix)
        with open(temp_path, "wb") as tmp_f:
            writer.write(tmp_f)
        try:
            os.replace(temp_path, dest)
        except OSError:
            try:
                if dest.exists():
                    os.remove(dest)
            except OSError:
                pass
            shutil.move(str(temp_path), str(dest))
        return ("encrypted", {"src_size": src.stat().st_size, "dst_size": dest.stat().st_size})
    except Exception:
        # On any error, signal failure to caller by raising to be caught there
        raise


def write_password_file(password_file: Path, password: str, input_dir: Path, output_dir: Path, total_files: int) -> None:
    password_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_lines = [
        f"Generated: {timestamp}",
        f"Input Directory: {input_dir}",
        f"Output Directory: {output_dir}",
        f"Total PDFs (at generation time): {total_files}",
        f"Password: {password}",
        "",
        "Keep this file secure.",
    ]
    password_file.write_text("\n".join(content_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Password-protect PDFs in a directory with a single random password.")
    parser.add_argument("--dir", dest="directory", default="pdf-export", help="Input directory containing PDFs (default: pdf-export)")
    parser.add_argument("--out-dir", dest="out_dir", default=None, help="Output directory for encrypted PDFs (default: <dir>/encrypted)")
    parser.add_argument("--password-file", dest="password_file", default=None, help="Where to write the password (default: <out-dir>/password.txt)")
    parser.add_argument("--length", dest="length", type=int, default=20, help="Password length (default: 20)")
    parser.add_argument("--symbols", dest="symbols", action="store_true", default=True, help="Include symbols in password (default: enabled)")
    parser.add_argument("--no-symbols", dest="no_symbols", action="store_true", help="Disable symbols in password")
    parser.add_argument("--suffix", dest="suffix", default=".tmp", help="Temporary suffix to use while encrypting (default: .tmp)")
    parser.add_argument("--recursive", dest="recursive", action="store_true", help="Scan input directory recursively for PDFs")
    parser.add_argument("--workers", dest="workers", type=int, default=max(1, os.cpu_count() or 1), help="Number of parallel workers (default: CPU count)")

    args = parser.parse_args()
    target_dir = Path(args.directory).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"ERROR: Directory not found: {target_dir}")
        return 2

    include_symbols = False if args.no_symbols else args.symbols
    password = generate_password(length=args.length, include_symbols=include_symbols)

    pdfs = list(find_pdfs(target_dir, recursive=args.recursive))
    if not pdfs and not args.recursive:
        # Helpful fallback: try recursive automatically
        pdfs = list(find_pdfs(target_dir, recursive=True))
        if pdfs:
            print(f"No PDFs found in top-level of {target_dir}; found {len(pdfs)} PDF(s) recursively.")
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (target_dir / "encrypted")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.password_file is None:
        password_file = out_dir / "password.txt"
    else:
        password_file = Path(args.password_file).resolve()

    total = len(pdfs)
    # Write password file at the start
    write_password_file(password_file, password, target_dir, out_dir, total)
    print(f"Found {total} PDF(s) in {target_dir}{' (recursive)' if args.recursive else ''}.", flush=True)
    print(f"Output directory: {out_dir}", flush=True)
    print(f"Password file: {password_file}", flush=True)
    print(f"Using {min(args.workers, max(1, total))} worker(s).\n", flush=True)

    processed = 0
    skipped = 0
    failed = 0
    copied = 0

    if total == 0:
        print("No PDFs to process.")
        return 0

    # Parallel processing
    futures = []
    with ProcessPoolExecutor(max_workers=min(args.workers, max(1, total))) as executor:
        future_to_pdf = {}
        for pdf in pdfs:
            dest = out_dir / pdf.name
            fut = executor.submit(
                process_pdf_worker,
                str(pdf),
                str(dest),
                password,
                args.suffix,
            )
            futures.append(fut)
            future_to_pdf[fut] = pdf

        completed = 0
        for future in as_completed(futures):
            pdf = future_to_pdf[future]
            completed += 1
            try:
                action, metrics = future.result()
                if action == "encrypted":
                    processed += 1
                    print(f"[{completed}/{total}] Encrypted: {pdf.name}", flush=True)
                elif action == "copied":
                    copied += 1
                    print(f"[{completed}/{total}] Copied (already encrypted): {pdf.name}", flush=True)
                elif action == "skipped":
                    skipped += 1
                    print(f"[{completed}/{total}] Skipped (exists in output): {pdf.name}", flush=True)
                else:
                    skipped += 1
                    print(f"[{completed}/{total}] Skipped: {pdf.name}", flush=True)
            except Exception as exc:
                failed += 1
                print(f"[{completed}/{total}] FAIL: {pdf.name} - {exc}", flush=True)

    print("\nSummary:")
    print(f"  Input Directory: {target_dir}")
    print(f"  Output Directory: {out_dir}")
    print(f"  Password File: {password_file}")
    print(f"  Total PDFs scanned: {total}")
    print(f"  Encrypted: {processed}")
    print(f"  Copied (already encrypted): {copied}")
    print(f"  Skipped (exists in output): {skipped}")
    print(f"  Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())


