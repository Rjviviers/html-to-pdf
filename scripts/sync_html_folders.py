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


def _safe_move_to_done(html_path: Path, done_dir: Path) -> None:
    """Move the given HTML into done-html/ with safe handling of duplicates/errors."""
    destination = done_dir / html_path.name
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


def _gather_pdf_stems(out_dir: Path) -> set[str]:
    stems: set[str] = set()
    if not out_dir.exists():
        return stems
    for p in out_dir.glob('*.pdf'):
        stems.add(p.stem)
    return stems


def run_sync(base_dir: Path | None = None) -> dict:
    if base_dir is None:
        base_dir = DEFAULT_BASE_DIR
    html_dir, out_dir, processing_dir, done_dir = _layout(base_dir)

    # Ensure folder structure exists
    html_dir.mkdir(parents=True, exist_ok=True)
    processing_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_stems = _gather_pdf_stems(out_dir)

    moved_processing = 0
    moved_drop = 0

    for html_path in sorted(processing_dir.glob('*.html')):
        if html_path.stem in pdf_stems:
            _safe_move_to_done(html_path, done_dir)
            moved_processing += 1

    for html_path in sorted(html_dir.glob('*.html')):
        if html_path.stem in pdf_stems:
            _safe_move_to_done(html_path, done_dir)
            moved_drop += 1

    return {"status": "ok", "base_dir": str(base_dir), "moved_processing": moved_processing, "moved_drop": moved_drop}


def main() -> int:
    summary = run_sync(DEFAULT_BASE_DIR)
    print("Sync complete.")
    return 0 if summary.get("status") == "ok" else 1


if __name__ == '__main__':
    raise SystemExit(main())


