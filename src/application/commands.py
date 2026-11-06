"""Commands (escritura) del CQRS básico."""
from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects import InspeccionDeVehiculo


@dataclass(frozen=True)
class EntregarVehiculoCommand:
    reservacion_id: str
    ultimos_4: str
    titular: str
    inspeccion_salida: InspeccionDeVehiculo


@dataclass(frozen=True)
class RegistrarDevolucionCommand:
    contrato_id: str
    inspeccion_devolucion: InspeccionDeVehiculo
    hora_devolucion: datetime


@dataclass(frozen=True)
class DecisionDelCliente:
    acepta_upgrade: bool = True
    acepta_inferior: bool = True
