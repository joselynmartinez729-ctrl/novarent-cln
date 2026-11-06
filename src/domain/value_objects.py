"""Value Objects y errores del dominio NovaRent (renta de autos por día).
Trazabilidad: glosario #3, #10, #12, #13, #16, #17, #19."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


# ---------- Errores ----------
class DomainError(Exception):
    """Regla de negocio violada (HTTP 422)."""


class ConflictoDeEstado(DomainError):
    """La operación no es válida en el estado actual (HTTP 409)."""


class TransicionInvalida(ConflictoDeEstado):
    pass


class ContratoYaDevuelto(ConflictoDeEstado):
    pass


# ---------- Dinero ----------
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Dinero:
    monto: Decimal
    moneda: str = "MXN"

    def __post_init__(self):
        m = Decimal(str(self.monto)).quantize(_CENT, ROUND_HALF_UP)
        if m < 0:
            raise DomainError("El importe no puede ser negativo")
        object.__setattr__(self, "monto", m)

    @staticmethod
    def cero() -> "Dinero":
        return Dinero(Decimal("0"))

    def __add__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.monto + otro.monto, self.moneda)

    def por(self, factor) -> "Dinero":
        return Dinero(self.monto * Decimal(str(factor)), self.moneda)

    def __str__(self) -> str:
        return f"{self.monto} {self.moneda}"


# ---------- Categoría y estatus ----------
class Categoria(int, Enum):
    """Jerarquía de categorías (supuesto S-12: el BRD no lista las categorías)."""
    ECONOMICO = 1
    COMPACTO = 2
    SEDAN = 3
    SUV = 4
    LUJO = 5


class EstatusDeVehiculo(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    RENTADO = "RENTADO"
    EN_REVISION = "EN_REVISION"
    LIMPIEZA = "LIMPIEZA"
    MANTENIMIENTO_MAYOR = "MANTENIMIENTO_MAYOR"


class EstatusDeReservacion(str, Enum):
    CONFIRMADA = "CONFIRMADA"
    ENTREGADA = "ENTREGADA"
    CANCELADA = "CANCELADA"
    DOCUMENTACION_INVALIDA = "DOCUMENTACION_INVALIDA"


class TipoDeCargo(str, Enum):
    RETRASO = "RETRASO"
    COMBUSTIBLE = "COMBUSTIBLE"
    KILOMETRAJE = "KILOMETRAJE"
    DANOS = "DANOS"
    MANTENIMIENTO_MAYOR = "MANTENIMIENTO_MAYOR"
    EXTENSION = "EXTENSION"


class Rol(str, Enum):
    AGENTE = "AGENTE"
    PATIO = "PATIO"
    LIMPIEZA = "LIMPIEZA"
    ADMINISTRACION = "ADMINISTRACION"


# ---------- Combustible, kilometraje, periodo ----------
@dataclass(frozen=True)
class NivelDeCombustible:
    """Nivel fraccional en cuartos de tanque: 0 (vacío) … 4 (lleno). Glosario #10."""
    cuartos: int

    def __post_init__(self):
        if not 0 <= self.cuartos <= 4:
            raise DomainError("El nivel de combustible debe estar entre 0 y 4 cuartos")

    @staticmethod
    def desde_texto(txt: str) -> "NivelDeCombustible":
        mapa = {"vacio": 0, "1/4": 1, "1/2": 2, "3/4": 3, "lleno": 4}
        try:
            return NivelDeCombustible(mapa[txt.strip().lower()])
        except KeyError:
            raise DomainError(f"Nivel de combustible desconocido: {txt}")


@dataclass(frozen=True)
class Kilometraje:
    km: int

    def __post_init__(self):
        if self.km < 0:
            raise DomainError("El kilometraje no puede ser negativo")


@dataclass(frozen=True)
class PeriodoDeRenta:
    inicio: datetime
    fin_pactado: datetime

    def __post_init__(self):
        if self.fin_pactado <= self.inicio:
            raise DomainError("El fin pactado debe ser posterior al inicio")

    @property
    def dias(self) -> int:
        """Días de renta (mínimo 1; fracción de día cuenta como día completo)."""
        return max(1, math.ceil((self.fin_pactado - self.inicio).total_seconds() / 86400))


# ---------- Documentación, voucher, inspección ----------
@dataclass(frozen=True)
class DocumentacionConductor:
    titular: str
    fecha_nacimiento: date
    licencia_vigente_hasta: date
    identificacion_vigente_hasta: date

    def edad_en(self, hoy: date) -> int:
        n = self.fecha_nacimiento
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))


@dataclass(frozen=True)
class VoucherAbierto:
    """Depósito en garantía: últimos 4 dígitos + código bancario + titular (US12, glosario #19)."""
    ultimos_4: str
    codigo_autorizacion: str
    titular: str

    def __post_init__(self):
        if not (len(self.ultimos_4) == 4 and self.ultimos_4.isdigit()):
            raise DomainError("Se requieren exactamente los últimos 4 dígitos de la tarjeta")
        if not self.codigo_autorizacion:
            raise DomainError("Falta el código de autorización bancaria")


@dataclass(frozen=True)
class InspeccionDeVehiculo:
    """Esquema digital de daños + fotos + km + combustible (US05; glosario #8, #9)."""
    esquema_completado: bool
    fotos: tuple
    kilometraje: Kilometraje
    combustible: NivelDeCombustible
    danos: tuple = ()

    def danos_nuevos_respecto_a(self, anterior: "InspeccionDeVehiculo") -> tuple:
        """Zonas dañadas que no estaban marcadas en la inspección anterior (US05, N1)."""
        previos = {d.strip().lower() for d in anterior.danos}
        return tuple(d for d in self.danos if d.strip().lower() not in previos)
