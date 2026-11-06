"""Aggregate Vehiculo + State Machine de estatus (N2, US11, glosario #17, RN-13).

DISPONIBLE --entregar--> RENTADO --recibir--> EN_REVISION --iniciar_limpieza--> LIMPIEZA
LIMPIEZA --marcar_terminado--> DISPONIBLE   (único camino a Disponible)
LIMPIEZA --reportar_mantenimiento_mayor--> MANTENIMIENTO_MAYOR
(S-4: la salida de Mantenimiento Mayor está pendiente de validar con el stakeholder)"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from . import events as ev
from .specifications import VehiculoDisponible
from .value_objects import Categoria, EstatusDeVehiculo as E, TransicionInvalida, ConflictoDeEstado

TRANSICIONES = {
    ("entregar", E.DISPONIBLE): E.RENTADO,
    ("recibir", E.RENTADO): E.EN_REVISION,
    ("iniciar_limpieza", E.EN_REVISION): E.LIMPIEZA,
    ("marcar_terminado", E.LIMPIEZA): E.DISPONIBLE,
    ("reportar_mantenimiento_mayor", E.LIMPIEZA): E.MANTENIMIENTO_MAYOR,
}


@dataclass
class Vehiculo:
    vehiculo_id: str
    placas: str
    categoria: Categoria
    capacidad_tanque_litros: int = 50  # S-2 (supuesto)
    estatus: E = E.DISPONIBLE
    _eventos: List = field(default_factory=list, repr=False)

    def _transicionar(self, accion: str) -> None:
        try:
            self.estatus = TRANSICIONES[(accion, self.estatus)]
        except KeyError:
            raise TransicionInvalida(
                f"No se puede '{accion}' un vehículo en estatus {self.estatus.value}")

    def entregar(self) -> None:
        if not VehiculoDisponible().is_satisfied_by(self):
            raise ConflictoDeEstado("Solo un vehículo 'Disponible' puede entregarse (N2)")
        self._transicionar("entregar")

    def recibir_en_revision(self) -> None:
        self._transicionar("recibir")

    def iniciar_limpieza(self) -> None:
        self._transicionar("iniciar_limpieza")

    def marcar_terminado(self) -> None:
        self._transicionar("marcar_terminado")
        self._eventos.append(ev.VehiculoLiberado(vehiculo_id=self.vehiculo_id))

    def reportar_mantenimiento_mayor(self, motivo: str, monto: Decimal) -> None:
        self._transicionar("reportar_mantenimiento_mayor")
        self._eventos.append(ev.MantenimientoMayorRegistrado(
            vehiculo_id=self.vehiculo_id, motivo=motivo, monto=Decimal(str(monto))))

    def pull_events(self):
        e, self._eventos = self._eventos, []
        return e
