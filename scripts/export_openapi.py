"""Genera docs/api/openapi.json.  Uso: python scripts/export_openapi.py"""
import json, os, sys
os.environ.setdefault("DATABASE_URL", "sqlite://")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.api.main import app
os.makedirs("docs/api", exist_ok=True)
with open("docs/api/openapi.json", "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
print("docs/api/openapi.json generado")
