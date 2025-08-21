# HTML-to-PDF Service and CLI

Toolkit to convert HTML files to PDF with WeasyPrint, manage outputs, and optionally encrypt PDFs. Includes a Docker image with a selectable entrypoint for API or interactive CLI.

## Contents

- `scripts/batch_convert.py`: Converts all `*.html` in `html-drop/` to `pdf-export/` using WeasyPrint. Safe for concurrent runs and resumes.
- `src-backend/converter.py`: Conversion library used by the batch script.
- `scripts/sync_html_folders.py`: Moves completed HTMLs into `done-html/` when PDFs exist.
- `scripts/password_protect_pdfs.sh`: Encrypts PDFs using qpdf (AES-256 preferred) with either a provided or generated password.
- `scripts/console_app.py`: Interactive console to run convert/sync/encrypt.
- `src-backend/api_service.py`: FastAPI microservice endpoints to trigger convert and sync.
- `Dockerfile`: Headless environment with all WeasyPrint system deps.

## Folder workflow

- All folders live under a single base directory (`BASE_DIR`).
  - Local default: `/var/www/html`
  - Docker default: `/app` (set in the image)
- Folders are auto-created on first run if missing.
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
  -e APP_MODE=batch \
  -e BASE_DIR=/app \
  -v $(pwd)/html-drop:/app/html-drop \
  -v $(pwd)/pdf-export:/app/pdf-export \
  -v $(pwd)/processing:/app/processing \
  -v $(pwd)/done-html:/app/done-html \
  html-to-pdf
```

Run interactive CLI inside the container:

```bash
docker run --rm -it \
  -e APP_MODE=cli \
  -e BASE_DIR=/app \
  -v $(pwd)/html-drop:/app/html-drop \
  -v $(pwd)/pdf-export:/app/pdf-export \
  -v $(pwd)/processing:/app/processing \
  -v $(pwd)/done-html:/app/done-html \
  html-to-pdf
```

Password-protect PDFs with qpdf:

```bash
docker run --rm \
  -v $(pwd)/pdf-export:/app/pdf-export \
  -v $(pwd)/pdf-encrypted:/app/pdf-encrypted \
  html-to-pdf \
  bash /app/scripts/password_protect_pdfs.sh --dir /app/pdf-export --out-dir /app/pdf-encrypted

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

Run as an API service:

```bash
docker run -d \
  -e APP_MODE=api -e BASE_DIR=/app -p 8000:8000 \
  -v $(pwd)/html-drop:/app/html-drop \
  -v $(pwd)/pdf-export:/app/pdf-export \
  -v $(pwd)/processing:/app/processing \
  -v $(pwd)/done-html:/app/done-html \
  html-to-pdf

# Trigger conversion
curl -X POST http://localhost:8000/convert -H 'Content-Type: application/json' -d '{}'

# Trigger sync
curl -X POST http://localhost:8000/sync -H 'Content-Type: application/json' -d '{}'
```

## Docker Compose

Create `env.txt` (already included with sensible defaults), then:

```bash
# Build once
docker compose build

# Start API (reads PORT/WORKERS from env.txt)
docker compose --profile api up -d api

# Trigger convert
curl -X POST http://localhost:8000/convert -H 'Content-Type: application/json' -d '{}'

# Run a one-shot batch conversion
docker compose --profile batch up batch

# Run interactive CLI
docker compose run --rm --profile cli cli
```
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
# Uses BASE_DIR=/var/www/html by default
python3 scripts/batch_convert.py
```

Use a different base directory locally by setting `BASE_DIR` (folders will be created on first run):

```bash
BASE_DIR=$(pwd) python3 scripts/batch_convert.py
```

## Notes

- Environment variables for fine-tuning are supported in `src-backend/converter.py` (e.g., `HEADER_SPACE_MM`, `FOOTER_SPACE_MM`, `DISABLE_SAFE_HEADER_FOOTER`).
- The batch converter is idempotent and concurrent-safe; multiple instances can run against the same shared folders.
- Both `scripts/batch_convert.py` and `scripts/sync_html_folders.py` respect `BASE_DIR` and are importable for API/CLI use.


