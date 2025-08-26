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
import shutil
import errno
import sys
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Base directory for all working folders. Can be overridden with BASE_DIR env var.
# Defaults to '/var/www/html' to support system-wide deployments.
DEFAULT_BASE_DIR = Path(os.getenv('BASE_DIR', '/var/www/html'))

# Folder layout computed dynamically from a given base directory
def _layout(base_dir: Path) -> Tuple[Path, Path, Path, Path]:
    html_dir = base_dir / 'html-drop'
    out_dir = base_dir / 'pdf-export'
    processing_dir = base_dir / 'processing'
    done_dir = base_dir / 'done-html'
    return html_dir, out_dir, processing_dir, done_dir


def _atomic_acquire_html(src_html_path: Path, processing_dir: Path) -> Optional[Path]:
    """
    Try to atomically move an HTML file from html-drop/ to processing/ to acquire it
    for this worker instance. Returns the new processing path on success, or None if
    the file could not be acquired (e.g., another process acquired it first).
    """
    processing_path = processing_dir / src_html_path.name
    try:
        # os.rename is atomic on same filesystem
        os.rename(src_html_path, processing_path)
        return processing_path
    except FileNotFoundError:
        # Another process likely moved it already
        return None
    except FileExistsError:
        # Already being processed by another instance
        return None
    except OSError as e:
        # Cross-device link? Fall back to shutil.move (copy+delete)
        if getattr(e, 'errno', None) in (errno.EXDEV,):
            try:
                shutil.move(str(src_html_path), str(processing_path))
                return processing_path
            except Exception:
                return None
        # Any other issue: skip acquisition
        return None


def _finalize_html_after_success(processing_path: Path, done_dir: Path) -> None:
    """Move processed HTML from processing/ to done-html/, avoiding duplicates."""
    destination = done_dir / processing_path.name
    try:
        if destination.exists():
            # If already archived as done, remove the processing copy
            processing_path.unlink(missing_ok=True)
        else:
            os.rename(processing_path, destination)
    except FileNotFoundError:
        # Already moved or removed by someone else
        pass
    except OSError as e:
        # Cross-device: fall back to shutil.move; otherwise try replace
        if getattr(e, 'errno', None) in (errno.EXDEV,):
            try:
                shutil.move(str(processing_path), str(destination))
                return
            except Exception:
                processing_path.unlink(missing_ok=True)
                return
        try:
            os.replace(processing_path, destination)
        except Exception:
            try:
                shutil.move(str(processing_path), str(destination))
            except Exception:
                # Last resort: delete processing copy to avoid clogging the queue
                processing_path.unlink(missing_ok=True)


def _requeue_html_after_failure(processing_path: Path, html_dir: Path) -> None:
    """On failure, move HTML back to html-drop/ for retry. Avoid overwriting."""
    if not processing_path.exists():
        return
    destination = html_dir / processing_path.name
    if destination.exists():
        # If original name is taken, append a suffix to retry later
        destination = destination.with_name(destination.stem + "__retry" + destination.suffix)
    try:
        os.rename(processing_path, destination)
    except OSError as e:
        if getattr(e, 'errno', None) in (errno.EXDEV,):
            try:
                shutil.move(str(processing_path), str(destination))
                return
            except Exception:
                return
        # If rename fails, attempt replace, then shutil.move
        try:
            os.replace(processing_path, html_dir / processing_path.name)
        except Exception:
            try:
                shutil.move(str(processing_path), str(html_dir / processing_path.name))
            except Exception:
                # Give up and leave it in processing for manual intervention
                pass

def run_batch_convert(base_dir: Optional[Path | str] = None) -> dict:
    """Run the batch conversion process for the given base directory.

    Returns a summary dict with counts.
    """
    sys.path.insert(0, str(ROOT / 'src-backend'))
    try:
        from converter import HTMLToPDFConverter
    except Exception as e:
        return {"status": "error", "error": f"Failed to import converter: {e}"}

    if base_dir is None:
        base_dir = DEFAULT_BASE_DIR
    else:
        base_dir = Path(base_dir)

    html_dir, out_dir, processing_dir, done_dir = _layout(base_dir)

    # Ensure required directories exist on first run
    html_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    processing_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)

    # Gather HTML files (case-insensitive, .html and .htm)
    patterns = ['*.html', '*.htm', '*.HTML', '*.HTM']
    html_files = []
    for pat in patterns:
        html_files.extend([p for p in html_dir.glob(pat)])
    html_files = sorted({p.resolve() for p in html_files})
    converter = HTMLToPDFConverter()
    successes = 0
    failures = 0
    skipped_existing = 0
    acquired = 0

    if not html_files:
        # Helpful debug output when nothing is found
        try:
            listing = ', '.join(sorted([p.name for p in html_dir.iterdir()]))
        except Exception:
            listing = '(unavailable)'
        return {
            "status": "ok",
            "base_dir": str(base_dir),
            "acquired": 0,
            "successes": 0,
            "failures": 0,
            "skipped_existing": 0,
            "note": f"No HTML files found in {html_dir}",
            "html_drop_listing": listing,
        }

    for src_html_path in html_files:
        processing_path = _atomic_acquire_html(src_html_path, processing_dir)
        if processing_path is None:
            continue
        acquired += 1

        out_path = out_dir / (processing_path.stem + '.pdf')
        if out_path.exists():
            _finalize_html_after_success(processing_path, done_dir)
            successes += 1
            skipped_existing += 1
            continue

        try:
            result = converter.convert_file(str(processing_path), str(out_path))
            if result.get('status') == 'success':
                successes += 1
                _finalize_html_after_success(processing_path, done_dir)
            else:
                failures += 1
                _requeue_html_after_failure(processing_path, html_dir)
        except Exception:
            failures += 1
            _requeue_html_after_failure(processing_path, html_dir)

    return {
        "status": "ok" if failures == 0 else "partial",
        "base_dir": str(base_dir),
        "acquired": acquired,
        "successes": successes,
        "failures": failures,
        "skipped_existing": skipped_existing,
    }

def main() -> int:
    base_dir = DEFAULT_BASE_DIR
    summary = run_batch_convert(base_dir)
    if summary.get("status") == "error":
        print(summary.get("error"))
        return 2
    if summary.get("successes", 0) + summary.get("failures", 0) + summary.get("skipped_existing", 0) == 0:
        print(f"No HTML files found in {base_dir / 'html-drop'}")
        return 1
    print(
        f"Done. Success: {summary['successes']}, Failures: {summary['failures']}, Skipped existing: {summary['skipped_existing']}"
    )
    return 0 if summary.get("failures", 0) == 0 else 3

if __name__ == '__main__':
    raise SystemExit(main())


