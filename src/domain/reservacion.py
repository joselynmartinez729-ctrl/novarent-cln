"""Aggregate Reservacion (US01, US03, US10; glosario #1, #16; ADR-02)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from . import events as ev
from .compensacion import OfertaDeCompensacion
from .specifications import documentacion_valida, reservacion_entregable
from .value_objects import (Categoria, ConflictoDeEstado, DocumentacionConductor, Dinero,
                            DomainError, EstatusDeReservacion as R, PeriodoDeRenta)

PORCENTAJE_RETENCION = 10  # RN-02


@dataclass
class Reservacion:
    reservacion_id: str
    categoria: Categoria            # categoría reservada (garantizada)
    tarifa_diaria: Dinero
    pago_inicial: Dinero            # S-1: monto/momento pendientes de validar
    periodo: PeriodoDeRenta
    categoria_entrega: Optional[Categoria] = None
    estatus: R = R.CONFIRMADA
    documentacion: Optional[DocumentacionConductor] = None
    documentacion_verificada: bool = False
    retencion: Dinero = field(default_factory=Dinero.cero)
    _eventos: List = field(default_factory=list, repr=False)

    def __post_init__(self):
        if self.categoria_entrega is None:
            self.categoria_entrega = self.categoria

    def _exigir_confirmada(self):
        if self.estatus != R.CONFIRMADA:
            raise ConflictoDeEstado(f"La reservación está {self.estatus.value}")

    # --- CU-02 ---
    def validar_documentacion(self, doc: DocumentacionConductor, hoy: date) -> bool:
        self._exigir_confirmada()
        self.documentacion = doc
        if documentacion_valida(hoy).is_satisfied_by(doc):
            self.documentacion_verificada = True
            return True
        self.cancelar_por_documentacion_invalida()
        return False

    def cancelar_por_documentacion_invalida(self) -> None:
        self.estatus = R.DOCUMENTACION_INVALIDA
        self.documentacion_verificada = False
        self.retencion = self.pago_inicial.por(PORCENTAJE_RETENCION / 100)
        self._eventos.append(ev.DocumentacionInvalidaRegistrada(
            reservacion_id=self.reservacion_id, retencion=self.retencion.monto))

    # --- CU-03 ---
    def aplicar_compensacion(self, oferta: OfertaDeCompensacion) -> None:
        self._exigir_confirmada()
        self.categoria_entrega = oferta.categoria
        self.tarifa_diaria = oferta.tarifa_diaria
        self._eventos.append(ev.CategoriaCompensada(
            reservacion_id=self.reservacion_id, tipo=oferta.tipo.value, categoria=oferta.categoria.name))

    def cancelar_por_falta_de_categoria(self) -> None:
        """H-5 (supuesto): se cancela sin penalización."""
        self._exigir_confirmada()
        self.estatus = R.CANCELADA

    # --- CU-01 ---
    def marcar_entregada(self) -> None:
        if not reservacion_entregable().is_satisfied_by(self):
            raise ConflictoDeEstado(
                "La reservación debe estar confirmada y con documentación verificada para entregarse")
        self.estatus = R.ENTREGADA

    def pull_events(self):
        e, self._eventos = self._eventos, []
        return e
