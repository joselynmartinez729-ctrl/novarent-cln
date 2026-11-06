"""CargoExtra, políticas de cargo (Strategy) y CalculadoraDeCargosExtra (Domain Service).
RN-08 retraso (US04) · RN-09 combustible (US06) · RN-10 kilometraje (US07)."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from .value_objects import (DomainError, Dinero, InspeccionDeVehiculo, PeriodoDeRenta,
                            Rol, TipoDeCargo)

TOLERANCIA_MINUTOS = 120          # glosario #6
PORCENTAJE_POR_HORA = Decimal("0.20")
LIMITE_DIA_COMPLETO_MINUTOS = 240  # S-11: se cuentan desde la hora pactada
CARGO_FIJO_RECARGA = Dinero(Decimal("100"))
KM_INCLUIDOS_POR_DIA = 250
PRECIO_KM_EXTRA = Decimal("5")


@dataclass
class CargoExtra:
    tipo: TipoDeCargo
    monto: Dinero
    descripcion: str = ""
    cancelado: bool = False

    def cancelar(self, rol: Rol) -> None:
        """RN-11 (US08): solo Administración cancela cargos. (PIN: pendiente, fuera de los 5 CU)."""
        if rol != Rol.ADMINISTRACION:
            raise DomainError("Solo el rol Administración puede cancelar cargos extra")
        self.cancelado = True


@dataclass(frozen=True)
class ContextoDeCargo:
    periodo: PeriodoDeRenta
    tarifa_diaria: Dinero
    inspeccion_salida: InspeccionDeVehiculo
    inspeccion_devolucion: InspeccionDeVehiculo
    hora_devolucion: datetime
    capacidad_tanque_litros: int
    precio_litro: Dinero


class PoliticaDeCargo(ABC):
    @abstractmethod
    def calcular(self, ctx: ContextoDeCargo) -> Optional[CargoExtra]: ...


class CargoPorRetraso(PoliticaDeCargo):
    """120 min de gracia; desde el minuto 121, 20 % de la tarifa diaria por hora
    (fracción = hora completa, S-11); más de 4 h desde la hora pactada = día completo."""
    def calcular(self, ctx):
        segundos = (ctx.hora_devolucion - ctx.periodo.fin_pactado).total_seconds()
        minutos = math.ceil(segundos / 60) if segundos > 0 else 0
        if minutos <= TOLERANCIA_MINUTOS:
            return None
        if minutos > LIMITE_DIA_COMPLETO_MINUTOS:
            return CargoExtra(TipoDeCargo.RETRASO, ctx.tarifa_diaria,
                              f"Retraso de {minutos} min: se cobra el día completo")
        horas = math.ceil((minutos - TOLERANCIA_MINUTOS) / 60)
        monto = ctx.tarifa_diaria.por(PORCENTAJE_POR_HORA * horas)
        return CargoExtra(TipoDeCargo.RETRASO, monto, f"Retraso de {minutos} min: {horas} h al 20 %")


class CargoPorCombustibleFaltante(PoliticaDeCargo):
    """Litros faltantes × precio de mercado + $100 de servicio de recarga."""
    def calcular(self, ctx):
        faltante = ctx.inspeccion_salida.combustible.cuartos - ctx.inspeccion_devolucion.combustible.cuartos
        if faltante <= 0:
            return None
        litros = Decimal(faltante) / 4 * ctx.capacidad_tanque_litros
        monto = ctx.precio_litro.por(litros) + CARGO_FIJO_RECARGA
        return CargoExtra(TipoDeCargo.COMBUSTIBLE, monto,
                          f"{faltante}/4 de tanque faltante ({litros} L) + servicio de recarga")


class CargoPorKilometrajeExcedente(PoliticaDeCargo):
    """250 km por día incluidos; $5 por km extra. Excedente nunca negativo."""
    def calcular(self, ctx):
        recorrido = ctx.inspeccion_devolucion.kilometraje.km - ctx.inspeccion_salida.kilometraje.km
        if recorrido < 0:
            raise DomainError("El kilometraje final no puede ser menor al inicial")
        excedente = max(0, recorrido - KM_INCLUIDOS_POR_DIA * ctx.periodo.dias)
        if excedente == 0:
            return None
        return CargoExtra(TipoDeCargo.KILOMETRAJE, Dinero(PRECIO_KM_EXTRA * excedente),
                          f"{excedente} km excedentes a $5")


class CalculadoraDeCargosExtra:
    """Domain Service: aplica las políticas; agregar una política nueva no toca ContratoDeRenta (OCP)."""
    def __init__(self, politicas: Optional[List[PoliticaDeCargo]] = None):
        self.politicas = politicas or [CargoPorRetraso(), CargoPorCombustibleFaltante(),
                                       CargoPorKilometrajeExcedente()]

    def calcular(self, ctx: ContextoDeCargo) -> List[CargoExtra]:
        return [c for p in self.politicas if (c := p.calcular(ctx)) is not None]
