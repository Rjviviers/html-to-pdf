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


ROOT = Path(__file__).resolve().parents[1]
HTML_DIR = ROOT / 'html-drop'
OUT_DIR = ROOT / 'pdf-export'
PROCESSING_DIR = ROOT / 'processing'
DONE_DIR = ROOT / 'done-html'


def _safe_move_to_done(html_path: Path) -> None:
    """Move the given HTML into done-html/ with safe handling of duplicates/errors."""
    destination = DONE_DIR / html_path.name
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


def _gather_pdf_stems() -> set[str]:
    stems: set[str] = set()
    if not OUT_DIR.exists():
        return stems
    for p in OUT_DIR.glob('*.pdf'):
        stems.add(p.stem)
    return stems


def main() -> int:
    # Ensure folder structure exists
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_stems = _gather_pdf_stems()

    # From processing/ → done-html/ when PDF exists
    for html_path in sorted(PROCESSING_DIR.glob('*.html')):
        if html_path.stem in pdf_stems:
            print(f"Archiving processed HTML: processing/{html_path.name} → done-html/{html_path.name}")
            _safe_move_to_done(html_path)

    # From html-drop/ → done-html/ when PDF exists
    for html_path in sorted(HTML_DIR.glob('*.html')):
        if html_path.stem in pdf_stems:
            print(f"Archiving completed HTML: html-drop/{html_path.name} → done-html/{html_path.name}")
            _safe_move_to_done(html_path)

    print("Sync complete.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


