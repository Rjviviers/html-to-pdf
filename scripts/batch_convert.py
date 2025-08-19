#!/usr/bin/env python3
"""
Batch convert all HTML files in html-drop/ to PDF into pdf-export/ using WeasyPrint.

Concurrent-safe:
- Each instance atomically moves work items from `html-drop/` to `processing/` before
  converting. This prevents duplicate processing when multiple runs happen at once.
- On success, the HTML is moved to `done-html/`.
- If the PDF already exists, conversion is skipped and the HTML is moved to `done-html/`.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
HTML_DIR = ROOT / 'html-drop'
OUT_DIR = ROOT / 'pdf-export'
PROCESSING_DIR = ROOT / 'processing'
DONE_DIR = ROOT / 'done-html'


def _atomic_acquire_html(src_html_path: Path) -> Optional[Path]:
    """
    Try to atomically move an HTML file from html-drop/ to processing/ to acquire it
    for this worker instance. Returns the new processing path on success, or None if
    the file could not be acquired (e.g., another process acquired it first).
    """
    processing_path = PROCESSING_DIR / src_html_path.name
    try:
        # os.rename is atomic and will fail on Windows if destination exists
        os.rename(src_html_path, processing_path)
        return processing_path
    except FileNotFoundError:
        # Another process likely moved it already
        return None
    except FileExistsError:
        # Already being processed by another instance
        return None
    except OSError:
        # Any other rename issue: skip acquisition
        return None


def _finalize_html_after_success(processing_path: Path) -> None:
    """Move processed HTML from processing/ to done-html/, avoiding duplicates."""
    destination = DONE_DIR / processing_path.name
    try:
        if destination.exists():
            # If already archived as done, remove the processing copy
            processing_path.unlink(missing_ok=True)
        else:
            os.rename(processing_path, destination)
    except FileNotFoundError:
        # Already moved or removed by someone else
        pass
    except OSError:
        # As a fallback, try replace semantics
        try:
            os.replace(processing_path, destination)
        except Exception:
            # Last resort: delete processing copy to avoid clogging the queue
            processing_path.unlink(missing_ok=True)


def _requeue_html_after_failure(processing_path: Path) -> None:
    """On failure, move HTML back to html-drop/ for retry. Avoid overwriting."""
    if not processing_path.exists():
        return
    destination = HTML_DIR / processing_path.name
    if destination.exists():
        # If original name is taken, append a suffix to retry later
        destination = destination.with_name(destination.stem + "__retry" + destination.suffix)
    try:
        os.rename(processing_path, destination)
    except OSError:
        # If rename fails, attempt replace (may overwrite) to avoid stuck files
        try:
            os.replace(processing_path, HTML_DIR / processing_path.name)
        except Exception:
            # Give up and leave it in processing for manual intervention
            pass

def main() -> int:
    sys.path.insert(0, str(ROOT / 'src-backend'))
    try:
        from converter import HTMLToPDFConverter
    except Exception as e:
        print(f"ERROR: Failed to import converter: {e}")
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    html_files = sorted([p for p in HTML_DIR.glob('*.html')])
    if not html_files:
        print(f"No HTML files found in {HTML_DIR}")
        return 1

    converter = HTMLToPDFConverter()
    successes = 0
    failures = 0
    for src_html_path in html_files:
        # Attempt to acquire this file for processing by atomically renaming it
        processing_path = _atomic_acquire_html(src_html_path)
        if processing_path is None:
            # Could not acquire; another concurrent worker likely took it
            continue

        out_path = OUT_DIR / (processing_path.stem + '.pdf')
        # If output already exists, skip conversion and archive the HTML
        if out_path.exists():
            print(f"Already done (PDF exists): {processing_path.name} -> {out_path.name}")
            _finalize_html_after_success(processing_path)
            successes += 1
            continue

        print(f"Converting: {processing_path.name} -> {out_path.name}")
        try:
            result = converter.convert_file(str(processing_path), str(out_path))
            if result.get('status') == 'success':
                successes += 1
                print(f"  OK: {out_path.name} ({result.get('output_size', 0)} bytes)")
                _finalize_html_after_success(processing_path)
            else:
                failures += 1
                print(f"  FAIL: {processing_path.name} - {result.get('error')}")
                _requeue_html_after_failure(processing_path)
        except Exception as e:
            failures += 1
            print(f"  EXCEPTION: {processing_path.name} - {e}")
            _requeue_html_after_failure(processing_path)

    print(f"Done. Success: {successes}, Failures: {failures}")
    return 0 if failures == 0 else 3

if __name__ == '__main__':
    raise SystemExit(main())


