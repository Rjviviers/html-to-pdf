"""
FastAPI microservice to trigger HTML→PDF conversions and syncs.

Endpoints:
- GET /health: Health check
- POST /convert: Trigger batch conversion; body: {"base_dir": "/path"} optional
- POST /sync: Trigger sync of folders; body: {"base_dir": "/path"} optional
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel


# Ensure we can import scripts as modules
SCRIPTS_DIR = Path("/app/scripts")
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DEFAULT_BASE_DIR = Path(os.getenv("BASE_DIR", "/app"))


class ConvertRequest(BaseModel):
    base_dir: Optional[str] = None


app = FastAPI(title="HTML to PDF Service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/convert")
def convert(req: ConvertRequest) -> dict[str, Any]:
    from batch_convert import run_batch_convert

    base_dir = Path(req.base_dir) if req.base_dir else DEFAULT_BASE_DIR
    summary = run_batch_convert(base_dir)
    return summary


@app.post("/sync")
def sync(req: ConvertRequest) -> dict[str, Any]:
    from sync_html_folders import run_sync

    base_dir = Path(req.base_dir) if req.base_dir else DEFAULT_BASE_DIR
    summary = run_sync(base_dir)
    return summary


