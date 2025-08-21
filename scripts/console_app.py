#!/usr/bin/env python3
"""
Interactive console app for HTML→PDF workflow.

Options:
- Convert all HTMLs in html-drop/ to PDFs
- Sync folders (move HTMLs to done-html/ when PDFs exist)
- Encrypt PDFs using qpdf shell script
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE_DIR = Path(os.getenv("BASE_DIR", "/app"))


def prompt(prompt_text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt_text}{suffix}: ").strip()
    return value or (default or "")


def run_convert(base_dir: Path) -> None:
    from batch_convert import run_batch_convert
    summary = run_batch_convert(base_dir)
    if summary.get("status") == "error":
        print(f"Error: {summary.get('error')}")
        return
    print(
        f"Converted. Success: {summary['successes']}, Failures: {summary['failures']}, Skipped existing: {summary['skipped_existing']}"
    )


def run_sync(base_dir: Path) -> None:
    from sync_html_folders import run_sync
    summary = run_sync(base_dir)
    print(
        f"Synced. Moved from processing: {summary['moved_processing']}, from html-drop: {summary['moved_drop']}"
    )


def run_encrypt(dir_path: Path, out_dir: Path | None = None, password: str | None = None) -> None:
    script = ROOT / "scripts" / "password_protect_pdfs.sh"
    if not script.exists():
        print("Encryption script not found.")
        return
    cmd = ["bash", str(script), "--dir", str(dir_path)]
    if out_dir is not None:
        cmd += ["--out-dir", str(out_dir)]
    if password:
        cmd += ["--password", password]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Encryption failed with exit code {e.returncode}")


def main() -> int:
    while True:
        print("\nHTML→PDF Console")
        print("1) Convert HTMLs to PDFs")
        print("2) Sync folders (archive done HTMLs)")
        print("3) Encrypt PDFs with qpdf")
        print("4) Exit")
        choice = input("Select an option [1-4]: ").strip()

        if choice == "1":
            base = prompt("Base directory", str(DEFAULT_BASE_DIR))
            run_convert(Path(base))
        elif choice == "2":
            base = prompt("Base directory", str(DEFAULT_BASE_DIR))
            run_sync(Path(base))
        elif choice == "3":
            pdf_dir = prompt("PDF directory", str(DEFAULT_BASE_DIR / "pdf-export"))
            out_dir = prompt(
                "Output directory for encrypted PDFs", str(Path(pdf_dir) / "encrypted")
            )
            use_existing = input("Provide password now? [y/N]: ").strip().lower() == "y"
            pwd = None
            if use_existing:
                pwd = prompt("Password")
            run_encrypt(Path(pdf_dir), Path(out_dir), pwd)
        elif choice == "4":
            return 0
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    raise SystemExit(main())


