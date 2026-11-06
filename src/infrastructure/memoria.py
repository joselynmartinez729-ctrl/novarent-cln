"""Implementaciones en memoria de los puertos (pruebas unitarias de la Service Layer y adaptadores externos simulados)."""
from __future__ import annotations

import copy
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from src.application import ports
from src.domain.value_objects import Categoria, Dinero, EstatusDeVehiculo

log = logging.getLogger(__name__)


# ---- Adaptadores externos simulados ----
class CatalogoEstatico(ports.CatalogoDeCategorias):
    """Jerarquía y tarifa por categoría (S-12: valores de ejemplo, el BRD no las define)."""
    TARIFAS = {Categoria.ECONOMICO: "450", Categoria.COMPACTO: "550", Categoria.SEDAN: "700",
               Categoria.SUV: "950", Categoria.LUJO: "1400"}

    def tarifa_de(self, categoria): return Dinero(Decimal(self.TARIFAS[categoria]))

    def superior_inmediata_de(self, c):
        return Categoria(c + 1) if c < max(Categoria) else None

    def inferior_inmediata_de(self, c):
        return Categoria(c - 1) if c > min(Categoria) else None


class PasarelaBancariaSimulada(ports.PasarelaDeAutorizacionBancaria):
    def autorizar_deposito(self, ultimos_4, titular):
        return f"AUT-{ultimos_4}-{abs(hash(titular)) % 100000:05d}"


class PrecioCombustibleConfigurable(ports.ProveedorDePrecioDeCombustible):
    """Precio de mercado por litro, configurable por variable de entorno PRECIO_LITRO."""
    def __init__(self, precio: Optional[str] = None):
        self.precio = Dinero(Decimal(precio or os.getenv("PRECIO_LITRO", "24.50")))

    def precio_por_litro(self): return self.precio


class ValidadorDePinConfigurable(ports.ValidadorDePin):
    """PIN de Administración tomado de PIN_ADMINISTRACION. Sin variable definida, ningún PIN es válido."""
    def __init__(self, pin: Optional[str] = None):
        self._pin = pin if pin is not None else os.getenv("PIN_ADMINISTRACION", "")

    def es_valido(self, pin: str) -> bool:
        import hmac
        return bool(self._pin) and hmac.compare_digest(self._pin.encode(), (pin or "").encode())


class RelojDelSistema(ports.Reloj):
    def ahora(self): return datetime.now()


class RelojFijo(ports.Reloj):
    def __init__(self, ahora: datetime): self._ahora = ahora
    def ahora(self): return self._ahora


class PublicadorEnMemoria(ports.PublicadorDeEventos):
    def __init__(self):
        self.historial: List = []
        self._manejadores: Dict[type, List[Callable]] = {}

    def suscribir(self, tipo: type, manejador: Callable) -> None:
        self._manejadores.setdefault(tipo, []).append(manejador)

    def publicar(self, evento):
        self.historial.append(evento)
        for m in self._manejadores.get(type(evento), []):
            try:
                m(evento)
            except Exception:  # el commit ya ocurrió; un handler fallido no revierte el caso de uso
                log.exception("Falló el manejador de %s", type(evento).__name__)


# ---- Repositorios y Unit of Work en memoria ----
class _Repo:
    def __init__(self, uow, store, pend):
        self._uow, self._store, self._pend = uow, store, pend

    def _get(self, k):
        obj = self._pend.get(k, self._store.get(k))
        if obj is None:
            return None
        obj = copy.deepcopy(obj)
        self._uow.rastrear(obj)
        return obj

    def _put(self, k, obj):
        copia = copy.deepcopy(obj)
        copia._eventos = []  # los eventos pendientes los publica la UoW desde el original rastreado
        self._pend[k] = copia
        self._uow.rastrear(obj)


class ReservacionRepoMem(_Repo, ports.ReservacionRepository):
    def obtener(self, i): return self._get(i)
    def guardar(self, r): self._put(r.reservacion_id, r)


class _ListarDevueltosMem:
    def listar_devueltos_entre(self, desde, hasta):
        todos = {**self._store, **self._pend}
        return [copy.deepcopy(c) for c in todos.values()
                if c.hora_devolucion is not None and desde <= c.hora_devolucion < hasta]


class ContratoRepoMem(_ListarDevueltosMem, _Repo, ports.ContratoDeRentaRepository):
    def obtener(self, i): return self._get(i)
    def agregar(self, c): self._put(c.contrato_id, c)
    def guardar(self, c): self._put(c.contrato_id, c)

    def obtener_ultimo_de_vehiculo(self, vehiculo_id):
        todos = {**self._store, **self._pend}
        cs = [c for c in todos.values() if c.vehiculo_id == vehiculo_id]
        return self._get(cs[-1].contrato_id) if cs else None


class VehiculoRepoMem(_Repo, ports.VehiculoRepository):
    def obtener(self, i): return self._get(i)
    def guardar(self, v): self._put(v.vehiculo_id, v)

    def listar(self, categoria=None):
        todos = {**self._store, **self._pend}
        return [copy.deepcopy(v) for v in todos.values() if categoria is None or v.categoria == categoria]

    def buscar_disponible_de_categoria(self, categoria):
        todos = {**self._store, **self._pend}
        for v in todos.values():
            if v.categoria == categoria and v.estatus == EstatusDeVehiculo.DISPONIBLE:
                return self._get(v.vehiculo_id)
        return None

    def hay_disponibilidad_en(self, categoria):
        todos = {**self._store, **self._pend}
        return any(v.categoria == categoria and v.estatus == EstatusDeVehiculo.DISPONIBLE for v in todos.values())


class AlmacenEnMemoria:
    def __init__(self):
        self.reservaciones: dict = {}
        self.contratos: dict = {}
        self.vehiculos: dict = {}


class UowEnMemoria(ports.UnidadDeTrabajo):
    def __init__(self, almacen: AlmacenEnMemoria, publicador):
        super().__init__(publicador)
        self._a = almacen
        self._p = ({}, {}, {})
        self.reservaciones = ReservacionRepoMem(self, almacen.reservaciones, self._p[0])
        self.contratos = ContratoRepoMem(self, almacen.contratos, self._p[1])
        self.vehiculos = VehiculoRepoMem(self, almacen.vehiculos, self._p[2])

    def _commit(self):
        self._a.reservaciones.update(self._p[0])
        self._a.contratos.update(self._p[1])
        self._a.vehiculos.update(self._p[2])
        self.rollback()

    def rollback(self):
        for d in self._p:
            d.clear()
