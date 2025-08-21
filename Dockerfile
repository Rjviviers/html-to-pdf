FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    BASE_DIR=/app \
    APP_MODE=cli \
    PORT=8000

# System dependencies required by WeasyPrint (Cairo, Pango, GDK-PixBuf) and tooling
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libffi8 \
    libxml2 \
    libxslt1.1 \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-core \
    qpdf \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY src-backend/requirements.txt /app/src-backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/src-backend/requirements.txt

# Copy scripts and backend module
COPY scripts/ /app/scripts/
COPY src-backend/ /app/src-backend/

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.sh || true

# Prepare working directories for input/output
RUN mkdir -p /app/html-drop /app/pdf-export /app/processing /app/done-html

EXPOSE 8000

# Entrypoint selects between CLI, API, or batch mode
CMD ["bash", "/app/scripts/entrypoint.sh"]


