"""Repositorios SQL y Unit of Work transaccional (ADR-03: una transacción por caso de uso)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import insert, select, update

from src.application import ports
from src.domain.value_objects import Categoria, EstatusDeVehiculo
from . import db, mappers as m


class _SqlRepo:
    def __init__(self, uow, conn):
        self._uow, self._c = uow, conn

    def _upsert(self, table, pk, row):
        res = self._c.execute(update(table).where(table.c[pk] == row[pk]).values(**row))
        if res.rowcount == 0:
            self._c.execute(insert(table).values(**row))

    def _one(self, table, pk, valor, convertir):
        row = self._c.execute(select(table).where(table.c[pk] == valor)).mappings().first()
        if row is None:
            return None
        obj = convertir(row)
        self._uow.rastrear(obj)
        return obj


class SqlReservacionRepository(_SqlRepo, ports.ReservacionRepository):
    def obtener(self, reservacion_id): return self._one(db.reservaciones, "reservacion_id", reservacion_id, m.reservacion_from)

    def guardar(self, r):
        self._upsert(db.reservaciones, "reservacion_id", m.reservacion_row(r))
        self._uow.rastrear(r)


class SqlContratoRepository(_SqlRepo, ports.ContratoDeRentaRepository):
    def obtener(self, contrato_id): return self._one(db.contratos, "contrato_id", contrato_id, m.contrato_from)

    def agregar(self, c):
        self._c.execute(insert(db.contratos).values(**m.contrato_row(c), creado_en=datetime.now()))
        self._uow.rastrear(c)

    def guardar(self, c):
        self._c.execute(update(db.contratos).where(db.contratos.c.contrato_id == c.contrato_id)
                        .values(**m.contrato_row(c)))
        self._uow.rastrear(c)

    def obtener_ultimo_de_vehiculo(self, vehiculo_id):
        row = self._c.execute(select(db.contratos).where(db.contratos.c.vehiculo_id == vehiculo_id)
                              .order_by(db.contratos.c.creado_en.desc())).mappings().first()
        if row is None:
            return None
        c = m.contrato_from(row)
        self._uow.rastrear(c)
        return c


    def listar_devueltos_entre(self, desde, hasta):
        q = select(db.contratos).where(db.contratos.c.hora_devolucion >= desde,
                                       db.contratos.c.hora_devolucion < hasta)
        return [m.contrato_from(r) for r in self._c.execute(q).mappings()]


class SqlVehiculoRepository(_SqlRepo, ports.VehiculoRepository):
    def obtener(self, vehiculo_id): return self._one(db.vehiculos, "vehiculo_id", vehiculo_id, m.vehiculo_from)

    def guardar(self, v):
        self._upsert(db.vehiculos, "vehiculo_id", m.vehiculo_row(v))
        self._uow.rastrear(v)

    def listar(self, categoria: Optional[Categoria] = None):
        q = select(db.vehiculos).order_by(db.vehiculos.c.vehiculo_id)
        if categoria is not None:
            q = q.where(db.vehiculos.c.categoria == categoria.name)
        return [m.vehiculo_from(r) for r in self._c.execute(q).mappings()]

    def buscar_disponible_de_categoria(self, categoria):
        row = self._c.execute(select(db.vehiculos).where(
            db.vehiculos.c.categoria == categoria.name,
            db.vehiculos.c.estatus == EstatusDeVehiculo.DISPONIBLE.value).order_by(db.vehiculos.c.vehiculo_id)
        ).mappings().first()
        if row is None:
            return None
        v = m.vehiculo_from(row)
        self._uow.rastrear(v)
        return v

    def hay_disponibilidad_en(self, categoria):
        return self._c.execute(select(db.vehiculos.c.vehiculo_id).where(
            db.vehiculos.c.categoria == categoria.name,
            db.vehiculos.c.estatus == EstatusDeVehiculo.DISPONIBLE.value).limit(1)).first() is not None


class SqlUnitOfWork(ports.UnidadDeTrabajo):
    def __init__(self, engine, publicador):
        super().__init__(publicador)
        self._engine = engine

    def __enter__(self):
        self._conn = self._engine.connect()
        self._tx = self._conn.begin()
        self.reservaciones = SqlReservacionRepository(self, self._conn)
        self.contratos = SqlContratoRepository(self, self._conn)
        self.vehiculos = SqlVehiculoRepository(self, self._conn)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.rollback()
        self._conn.close()
        return False

    def _commit(self): self._tx.commit()

    def rollback(self):
        if self._tx.is_active:
            self._tx.rollback()
