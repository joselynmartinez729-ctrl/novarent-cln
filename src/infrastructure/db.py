"""Esquema SQL (SQLAlchemy Core). SQLite en local/pruebas, PostgreSQL en Docker (DATABASE_URL)."""
import os

from sqlalchemy import (JSON, Boolean, Column, DateTime, Integer, MetaData, Numeric, String, Table,
                        create_engine)
from sqlalchemy.pool import StaticPool

metadata = MetaData()

vehiculos = Table(
    "vehiculos", metadata,
    Column("vehiculo_id", String(20), primary_key=True), Column("placas", String(20)),
    Column("categoria", String(20)), Column("capacidad_tanque_litros", Integer),
    Column("estatus", String(30)))

reservaciones = Table(
    "reservaciones", metadata,
    Column("reservacion_id", String(20), primary_key=True), Column("categoria", String(20)),
    Column("categoria_entrega", String(20)), Column("tarifa_diaria", Numeric(12, 2)),
    Column("pago_inicial", Numeric(12, 2)), Column("retencion", Numeric(12, 2)),
    Column("inicio", DateTime), Column("fin_pactado", DateTime), Column("estatus", String(30)),
    Column("documentacion_verificada", Boolean), Column("documentacion", JSON, nullable=True))

contratos = Table(
    "contratos", metadata,
    Column("contrato_id", String(20), primary_key=True), Column("reservacion_id", String(20)),
    Column("vehiculo_id", String(20)), Column("tarifa_diaria", Numeric(12, 2)),
    Column("inicio", DateTime), Column("fin_pactado", DateTime), Column("voucher", JSON),
    Column("inspeccion_salida", JSON), Column("inspeccion_devolucion", JSON, nullable=True),
    Column("hora_devolucion", DateTime, nullable=True), Column("cargos", JSON),
    Column("creado_en", DateTime))


def get_engine(url=None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./novarent.db")
    for prefijo in ("postgres://", "postgresql://"):  # Render/Railway entregan estos esquemas
        if url.startswith(prefijo):
            url = "postgresql+psycopg://" + url[len(prefijo):]
    kw = {}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kw["poolclass"] = StaticPool
    return create_engine(url, **kw)
