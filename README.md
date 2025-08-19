# HTML-to-PDF Scripts (Headless)

Script-only toolkit to convert HTML files to PDF with WeasyPrint and manage outputs, with optional PDF password protection. Includes a Docker image for reliable headless use on Ubuntu servers.

## Contents

- `scripts/batch_convert.py`: Converts all `*.html` in `html-drop/` to `pdf-export/` using WeasyPrint. Safe for concurrent runs and resumes.
- `src-backend/converter.py`: Conversion library used by the batch script.
- `scripts/sync_html_folders.py`: Moves completed HTMLs into `done-html/` when PDFs exist.
- `scripts/password_protect_pdfs.py`: Encrypts PDFs in a folder with a single random password, saving it to a file.
- `Dockerfile`: Headless environment with all WeasyPrint system deps.

## Folder workflow

- Put input HTML files into `html-drop/`
- Generated PDFs are written to `pdf-export/`
- While processing, files are moved to `processing/` and on success to `done-html/`

## Run with Docker (recommended)

Build once:

```bash
docker build -t html-to-pdf .
```

Convert any HTMLs in a host folder (mounted as `html-drop`) to PDFs (mounted as `pdf-export`):

```bash
docker run --rm \
  -v $(pwd)/html-drop:/app/html-drop \
  -v $(pwd)/pdf-export:/app/pdf-export \
  html-to-pdf
```

Use the password protection tool in the container:

```bash
docker run --rm \
  -v $(pwd)/pdf-export:/app/pdf-export \
  -v $(pwd)/pdf-encrypted:/app/pdf-encrypted \
  html-to-pdf \
  python3 /app/scripts/password_protect_pdfs.py --dir /app/pdf-export --out-dir /app/pdf-encrypted
```

Sync helper (archive HTMLs that have PDFs):

```bash
docker run --rm \
  -v $(pwd)/html-drop:/app/html-drop \
  -v $(pwd)/processing:/app/processing \
  -v $(pwd)/done-html:/app/done-html \
  -v $(pwd)/pdf-export:/app/pdf-export \
  html-to-pdf \
  python3 /app/scripts/sync_html_folders.py
```

## Local (without Docker)

Install system deps for WeasyPrint, then Python deps from `src-backend/requirements.txt`. On Ubuntu:

```bash
sudo apt-get update && sudo apt-get install -y \
  libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info
python3 -m pip install -r src-backend/requirements.txt
```

Run converter:

```bash
python3 scripts/batch_convert.py
```

## Notes

- Environment variables for fine-tuning are supported in `src-backend/converter.py` (e.g., `HEADER_SPACE_MM`, `FOOTER_SPACE_MM`, `DISABLE_SAFE_HEADER_FOOTER`).
- The batch converter is idempotent and concurrent-safe; multiple instances can run against the same shared folders.


