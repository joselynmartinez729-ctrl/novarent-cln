"""Domain Events (U3: 'Eventos de dominio')."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    ocurrido_en: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, kw_only=True)
class DocumentacionInvalidaRegistrada(DomainEvent):
    reservacion_id: str
    retencion: Decimal


@dataclass(frozen=True, kw_only=True)
class CategoriaCompensada(DomainEvent):
    reservacion_id: str
    tipo: str
    categoria: str


@dataclass(frozen=True, kw_only=True)
class VehiculoEntregado(DomainEvent):
    contrato_id: str
    vehiculo_id: str
    reservacion_id: str


@dataclass(frozen=True, kw_only=True)
class VehiculoDevuelto(DomainEvent):
    contrato_id: str
    vehiculo_id: str


@dataclass(frozen=True, kw_only=True)
class CargosExtraCalculados(DomainEvent):
    contrato_id: str
    total: Decimal


@dataclass(frozen=True, kw_only=True)
class VehiculoLiberado(DomainEvent):
    vehiculo_id: str


@dataclass(frozen=True, kw_only=True)
class MantenimientoMayorRegistrado(DomainEvent):
    vehiculo_id: str
    motivo: str
    monto: Decimal


@dataclass(frozen=True, kw_only=True)
class DanosDetectados(DomainEvent):
    contrato_id: str
    zonas: tuple


@dataclass(frozen=True, kw_only=True)
class RentaExtendida(DomainEvent):
    contrato_id: str
    nuevo_fin_pactado: datetime
    monto: Decimal


@dataclass(frozen=True, kw_only=True)
class CargoCancelado(DomainEvent):
    contrato_id: str
    tipo: str
    monto: Decimal
    motivo: str
