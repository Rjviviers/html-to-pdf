FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# System dependencies required by WeasyPrint (Cairo, Pango, GDK-PixBuf) and Python
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
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY src-backend/requirements.txt /app/src-backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/src-backend/requirements.txt

# Copy scripts and backend module
COPY scripts/ /app/scripts/
COPY src-backend/ /app/src-backend/

# Prepare working directories for input/output
RUN mkdir -p /app/html-drop /app/pdf-export /app/processing /app/done-html

# Default command converts any HTMLs present in /app/html-drop into /app/pdf-export
CMD ["python3", "/app/scripts/batch_convert.py"]


