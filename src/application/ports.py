"""Puertos (interfaces) que la Service Layer necesita. El dominio no conoce SQL ni HTTP (ADR-01/03)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional

from src.domain.contrato import ContratoDeRenta
from src.domain.reservacion import Reservacion
from src.domain.value_objects import Categoria, Dinero, VoucherAbierto
from src.domain.vehiculo import Vehiculo


class ReservacionRepository(ABC):
    @abstractmethod
    def obtener(self, reservacion_id: str) -> Optional[Reservacion]: ...
    @abstractmethod
    def guardar(self, reservacion: Reservacion) -> None: ...


class ContratoDeRentaRepository(ABC):
    @abstractmethod
    def obtener(self, contrato_id: str) -> Optional[ContratoDeRenta]: ...
    @abstractmethod
    def agregar(self, contrato: ContratoDeRenta) -> None: ...
    @abstractmethod
    def guardar(self, contrato: ContratoDeRenta) -> None: ...
    @abstractmethod
    def obtener_ultimo_de_vehiculo(self, vehiculo_id: str) -> Optional[ContratoDeRenta]: ...
    @abstractmethod
    def listar_devueltos_entre(self, desde: datetime, hasta: datetime) -> List[ContratoDeRenta]:
        """Contratos cuya devolución ocurrió en [desde, hasta) — base de los reportes."""


class VehiculoRepository(ABC):
    @abstractmethod
    def obtener(self, vehiculo_id: str) -> Optional[Vehiculo]: ...
    @abstractmethod
    def guardar(self, vehiculo: Vehiculo) -> None: ...
    @abstractmethod
    def listar(self, categoria: Optional[Categoria] = None) -> List[Vehiculo]: ...
    # Puerto DisponibilidadDeVehiculos (U3): "Disponible" es regla de estatus del vehículo
    @abstractmethod
    def buscar_disponible_de_categoria(self, categoria: Categoria) -> Optional[Vehiculo]: ...
    @abstractmethod
    def hay_disponibilidad_en(self, categoria: Categoria) -> bool: ...


class PublicadorDeEventos(ABC):
    @abstractmethod
    def publicar(self, evento) -> None: ...


class UnidadDeTrabajo(ABC):
    """Una transacción por caso de uso; los eventos se publican DESPUÉS del commit (ADR-03)."""
    reservaciones: ReservacionRepository
    contratos: ContratoDeRentaRepository
    vehiculos: VehiculoRepository

    def __init__(self, publicador: PublicadorDeEventos):
        self._publicador = publicador
        self._rastreados: list = []

    def rastrear(self, agregado) -> None:
        if all(a is not agregado for a in self._rastreados):
            self._rastreados.append(agregado)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        self.rollback()
        return False

    @abstractmethod
    def _commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...

    def commit(self) -> None:
        self._commit()
        eventos = [e for a in self._rastreados for e in a.pull_events()]
        self._rastreados = []
        for e in eventos:
            self._publicador.publicar(e)


class CatalogoDeCategorias(ABC):
    @abstractmethod
    def tarifa_de(self, categoria: Categoria) -> Dinero: ...
    @abstractmethod
    def superior_inmediata_de(self, categoria: Categoria) -> Optional[Categoria]: ...
    @abstractmethod
    def inferior_inmediata_de(self, categoria: Categoria) -> Optional[Categoria]: ...


class PasarelaDeAutorizacionBancaria(ABC):
    @abstractmethod
    def autorizar_deposito(self, ultimos_4: str, titular: str) -> str:
        """Devuelve el código de autorización bancaria."""


class ProveedorDePrecioDeCombustible(ABC):
    @abstractmethod
    def precio_por_litro(self) -> Dinero: ...


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime: ...
    def hoy(self) -> date:
        return self.ahora().date()


class ValidadorDePin(ABC):
    @abstractmethod
    def es_valido(self, pin: str) -> bool:
        """PIN de Administración (RN-11). El dominio solo recibe el resultado."""
