"""Выгружает OpenAPI-схему сервиса в docs.json: python -m scripts.export_openapi"""

import json
from pathlib import Path

from app.main import app

Path("docs.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
