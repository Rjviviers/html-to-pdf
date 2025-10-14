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
    try:
        value = input(f"{prompt_text}{suffix}: ").strip()
    except EOFError:
        # Non-interactive environment: fall back to default or empty string
        return default or ""
    return value or (default or "")


def _resolve_base_dir_from_user_input(user_input: str) -> Path:
    """Resolve a user-provided path to the intended base directory.

    Accepts either the base directory (containing html-drop, pdf-export, ...)
    or the html-drop directory itself and normalizes accordingly.
    """
    if not user_input:
        return DEFAULT_BASE_DIR
    p = Path(user_input)
    # If they passed the base dir directly
    if (p / "html-drop").exists():
        return p
    # If they passed the html-drop directory
    if p.name == "html-drop":
        return p.parent
    # If the dir looks like it contains HTMLs directly, assume it's html-drop
    if p.is_dir() and any(p.glob("*.html")):
        return p.parent
    return p


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


def run_encrypt(dir_path: Path, out_dir: Path | None = None, password: str | None = None) -> int:
    script = ROOT/"scripts"/"password_protect_pdfs.sh"
    if not script.exists():
        print("Encryption script not found.")
        return 2
    log_dir = Path(out_dir) if out_dir is not None else (dir_path / "encrypted")
    log_file = log_dir / "encrypt.log"
    cmd = ["bash", str(script), "--dir", str(dir_path), "--verbose", "--log-file", str(log_file)]
    if out_dir is not None:
        cmd += ["--out-dir", str(out_dir)]
    if password:
        cmd += ["--password", password]
    try:
        subprocess.check_call(cmd)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Encryption failed with exit code {e.returncode}. See log: {log_file}")
        return e.returncode


def main() -> int:
    # Non-interactive auto-encrypt mode via environment variables
    auto_encrypt_env = os.getenv("AUTO_ENCRYPT", "").strip().lower()
    cli_action_env = os.getenv("CLI_ACTION", "").strip().lower()
    auto_encrypt = auto_encrypt_env in {"1", "true", "yes", "y"} or cli_action_env == "encrypt"
    if auto_encrypt:
        pdf_dir = DEFAULT_BASE_DIR / "pdf-export"
        out_dir = pdf_dir / "encrypted"
        pwd_env = os.getenv("ENCRYPT_PASSWORD")
        return run_encrypt(pdf_dir, out_dir, pwd_env)

    while True:
        print("\nHTML→PDF Console")
        print("1) Convert HTMLs to PDFs")
        print("2) Sync folders (archive done HTMLs)")
        print("3) Encrypt PDFs with qpdf")
        print("4) Exit")
        try:
            choice = input("Select an option [1-4]: ").strip()
        except EOFError:
            print("No stdin available; exiting.")
            return 0

        if choice == "1":
            # Always use the html-drop folder for conversion
            html_folder = DEFAULT_BASE_DIR/"html-drop"
            base = _resolve_base_dir_from_user_input(str(html_folder))
            print(f"Using HTML folder: {html_folder}")
            print(f"Derived base directory: {base}")
            run_convert(base)
        elif choice == "2":
            base_in = prompt(
                "Base directory (or html-drop path)", str(DEFAULT_BASE_DIR)
            )
            base = _resolve_base_dir_from_user_input(base_in)
            print(f"Using base directory: {base}")
            run_sync(base)
        elif choice == "3":
            pdf_dir = prompt("PDF directory", str(DEFAULT_BASE_DIR / "pdf-export"))
            out_dir = prompt(
                "Output directory for encrypted PDFs", str(Path(pdf_dir) / "encrypted")
            )
            try:
                use_existing = input("Provide password now? [y/N]: ").strip().lower() == "y"
            except EOFError:
                use_existing = False
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


