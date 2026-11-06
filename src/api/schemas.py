"""Esquemas de entrada de la API (validación de formato; las reglas de negocio viven en el dominio)."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

from src.domain.value_objects import (DocumentacionConductor, InspeccionDeVehiculo, Kilometraje,
                                      NivelDeCombustible)


class DocumentacionIn(BaseModel):
    titular: str
    fecha_nacimiento: date
    licencia_vigente_hasta: date
    identificacion_vigente_hasta: date

    def to_domain(self):
        return DocumentacionConductor(self.titular, self.fecha_nacimiento, self.licencia_vigente_hasta,
                                      self.identificacion_vigente_hasta)


class InspeccionIn(BaseModel):
    esquema_completado: bool
    fotos: List[str] = Field(default_factory=list, description="URLs o nombres de fotografías")
    kilometraje: int = Field(ge=0)
    combustible: Literal["vacio", "1/4", "1/2", "3/4", "lleno"]
    danos: List[str] = Field(default_factory=list, description="Zonas marcadas en el esquema digital")

    def to_domain(self):
        return InspeccionDeVehiculo(self.esquema_completado, tuple(self.fotos), Kilometraje(self.kilometraje),
                                    NivelDeCombustible.desde_texto(self.combustible), tuple(self.danos))


class EntregaIn(BaseModel):
    ultimos_4: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    titular: str
    inspeccion_salida: InspeccionIn


class DevolucionIn(BaseModel):
    hora_devolucion: datetime
    inspeccion_devolucion: InspeccionIn

    @field_validator("hora_devolucion")
    @classmethod
    def _naive(cls, v):
        return v.replace(tzinfo=None)


class DecisionIn(BaseModel):
    acepta_upgrade: bool = True
    acepta_inferior: bool = True


class MantenimientoMayorIn(BaseModel):
    motivo: str
    monto_mxn: Decimal = Field(gt=0)


class ExtensionIn(BaseModel):
    nuevo_fin: datetime
    vehiculo_reservado_por_otro: bool = Field(
        False, description="El agente verifica si otro cliente tiene reservado el vehículo (S-15)")

    @field_validator("nuevo_fin")
    @classmethod
    def _naive(cls, v):
        return v.replace(tzinfo=None)


class CancelacionCargoIn(BaseModel):
    rol: Literal["AGENTE", "PATIO", "LIMPIEZA", "ADMINISTRACION"]
    pin: str
    motivo: str = Field(min_length=3)


class CargoPorDanosIn(BaseModel):
    monto_mxn: Decimal = Field(gt=0)
    descripcion: str = ""
