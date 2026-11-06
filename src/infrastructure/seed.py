"""Carga datos de demostración (flota y reservaciones) desde data/*.csv. Uso: python -m src.infrastructure.seed"""
import csv
import os
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, insert, select

from src.domain.value_objects import Categoria
from . import db

DATA_DIR = os.getenv("DATA_DIR", "data")


def _rows(nombre):
    with open(os.path.join(DATA_DIR, nombre), encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def seed(engine) -> None:
    db.metadata.create_all(engine)
    with engine.begin() as c:
        if c.execute(select(func.count()).select_from(db.vehiculos)).scalar():
            return
        c.execute(insert(db.vehiculos), [dict(
            vehiculo_id=r["vehiculo_id"], placas=r["placas"], categoria=Categoria[r["categoria"]].name,
            capacidad_tanque_litros=int(r["capacidad_tanque_litros"]), estatus=r["estatus"])
            for r in _rows("flota.csv")])
        c.execute(insert(db.reservaciones), [dict(
            reservacion_id=r["reservacion_id"], categoria=r["categoria"], categoria_entrega=r["categoria"],
            tarifa_diaria=Decimal(r["tarifa_diaria"]), pago_inicial=Decimal(r["pago_inicial"]),
            retencion=Decimal("0"), inicio=datetime.fromisoformat(r["inicio"]),
            fin_pactado=datetime.fromisoformat(r["fin_pactado"]), estatus="CONFIRMADA",
            documentacion_verificada=False, documentacion=None) for r in _rows("reservaciones.csv")])


if __name__ == "__main__":
    from .db import get_engine
    seed(get_engine())
    print("Datos de demostración cargados")
