#!/usr/bin/env python3
"""
Sync HTML folders with generated PDFs.

Rules:
- If a PDF exists in `pdf-export/` for an HTML of the same stem, move that HTML to `done-html/`.
- Apply this rule for HTMLs located in `processing/` and `html-drop/`.
- Avoid duplicate collisions by preferring to keep the existing file in `done-html/`.
"""
from __future__ import annotations

import os
from pathlib import Path


# Base directory; can be overridden with BASE_DIR env var. Docker sets BASE_DIR=/app.
DEFAULT_BASE_DIR = Path(os.getenv('BASE_DIR', '/var/www/html'))

def _layout(base_dir: Path) -> tuple[Path, Path, Path, Path]:
    html_dir = base_dir / 'html-drop'
    out_dir = base_dir / 'pdf-export'
    processing_dir = base_dir / 'processing'
    done_dir = base_dir / 'done-html'
    return html_dir, out_dir, processing_dir, done_dir


def _safe_move_to_done(html_path: Path, done_dir: Path, source_dir: Path) -> None:
    """Move the given HTML into done-html/ with safe handling of duplicates/errors."""
    # Preserve folder structure in done-html
    relative_path = html_path.relative_to(source_dir)
    destination = done_dir / relative_path
    # Ensure parent directories exist in done-html
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if destination.exists():
            # Already archived; remove the source to avoid duplicates
            html_path.unlink(missing_ok=True)
        else:
            os.rename(html_path, destination)
    except FileNotFoundError:
        # Source vanished concurrently; nothing to do
        pass
    except OSError:
        # Fallback to replace semantics; if that fails, drop the source to avoid loops
        try:
            os.replace(html_path, destination)
        except Exception:
            html_path.unlink(missing_ok=True)


def _gather_pdf_paths(out_dir: Path) -> set[Path]:
    """Gather all PDF file paths relative to out_dir, preserving folder structure."""
    pdf_paths: set[Path] = set()
    if not out_dir.exists():
        return pdf_paths
    for p in out_dir.rglob('*.pdf'):
        # Store relative path from out_dir, but with .html extension for comparison
        relative_path = p.relative_to(out_dir)
        html_path = relative_path.with_suffix('.html')
        pdf_paths.add(html_path)
    return pdf_paths


def run_sync(base_dir: Path | None = None) -> dict:
    if base_dir is None:
        base_dir = DEFAULT_BASE_DIR
    html_dir, out_dir, processing_dir, done_dir = _layout(base_dir)

    # Ensure folder structure exists
    html_dir.mkdir(parents=True, exist_ok=True)
    processing_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = _gather_pdf_paths(out_dir)

    moved_processing = 0
    moved_drop = 0

    # Recursively find HTML files in processing directory
    for html_path in sorted(processing_dir.rglob('*.html')):
        # Calculate relative path from processing_dir to compare with PDF paths
        relative_path = html_path.relative_to(processing_dir)
        if relative_path in pdf_paths:
            _safe_move_to_done(html_path, done_dir, processing_dir)
            moved_processing += 1

    # Recursively find HTML files in html-drop directory
    for html_path in sorted(html_dir.rglob('*.html')):
        # Calculate relative path from html_dir to compare with PDF paths
        relative_path = html_path.relative_to(html_dir)
        if relative_path in pdf_paths:
            _safe_move_to_done(html_path, done_dir, html_dir)
            moved_drop += 1

    return {"status": "ok", "base_dir": str(base_dir), "moved_processing": moved_processing, "moved_drop": moved_drop}


def main() -> int:
    summary = run_sync(DEFAULT_BASE_DIR)
    print("Sync complete.")
    return 0 if summary.get("status") == "ok" else 1


if __name__ == '__main__':
    raise SystemExit(main())


