"""Ejecuta data/casos_prueba_novarent.csv contra el dominio y guarda la evidencia en docs/evidencias/.
Uso: python scripts/ejecutar_casos.py   (código de salida 1 si algún caso falla)"""
import csv
import os
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from tests.casos_novarent import ejecutar_todos  # noqa: E402

res = ejecutar_todos()
os.makedirs(os.path.join(RAIZ, "docs", "evidencias"), exist_ok=True)
salida = os.path.join(RAIZ, "docs", "evidencias", "resultados_casos_novarent.csv")
with open(salida, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
    w.writeheader()
    w.writerows(res)
por_tipo = Counter((r["tipo_prueba"], r["estado"]) for r in res)
print(f"{'tipo':22} PASA FALLA")
for t in sorted({r["tipo_prueba"] for r in res}):
    print(f"{t:22} {por_tipo[(t, 'PASA')]:4} {por_tipo[(t, 'FALLA')]:5}")
fallas = [r for r in res if r["estado"] == "FALLA"]
for r in fallas:
    print("FALLA", r["caso_id"], r["escenario"], "esperado:", r["resultado_esperado"], "obtenido:", r["resultado_obtenido"])
print(f"\nTotal: {len(res)} casos, {len(res) - len(fallas)} pasan, {len(fallas)} fallan → {salida}")
sys.exit(1 if fallas else 0)
