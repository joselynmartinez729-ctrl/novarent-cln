"""RN-08/09/10: políticas de cargo (US04, US06, US07) con valores límite."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.domain.cargos import (CalculadoraDeCargosExtra, CargoExtra, CargoPorCombustibleFaltante,
                               CargoPorKilometrajeExcedente, CargoPorRetraso, ContextoDeCargo)
from src.domain.value_objects import Dinero, DomainError, PeriodoDeRenta, Rol, TipoDeCargo
from tests.conftest import FIN, INICIO, insp


def ctx(min_retraso=0, km_ini=1000, km_fin=1400, c_ini=4, c_fin=4, tarifa="450", litro="24.50", cap=40):
    return ContextoDeCargo(PeriodoDeRenta(INICIO, FIN), Dinero(Decimal(tarifa)), insp(km_ini, c_ini),
                           insp(km_fin, c_fin), FIN + timedelta(minutes=min_retraso, seconds=0), cap,
                           Dinero(Decimal(litro)))


@pytest.mark.parametrize("minutos,esperado", [
    (0, None), (120, None),            # dentro de la tolerancia
    (121, "90.00"),                    # minuto 121: 1 h al 20 % de 450
    (180, "90.00"), (181, "180.00"),   # fracción = hora completa (S-11)
    (240, "180.00"),                   # límite de 4 h todavía por horas
    (241, "450.00"), (600, "450.00"),  # > 4 h = día completo
])
def test_retraso(minutos, esperado):
    cargo = CargoPorRetraso().calcular(ctx(min_retraso=minutos))
    if esperado is None:
        assert cargo is None
    else:
        assert cargo.tipo == TipoDeCargo.RETRASO and cargo.monto.monto == Decimal(esperado)


def test_retraso_con_segundos_cuenta_como_minuto_121():
    c = ctx()
    c = ContextoDeCargo(c.periodo, c.tarifa_diaria, c.inspeccion_salida, c.inspeccion_devolucion,
                        FIN + timedelta(minutes=120, seconds=30), 40, c.precio_litro)
    assert CargoPorRetraso().calcular(c) is not None


def test_devolucion_anticipada_sin_retraso():
    assert CargoPorRetraso().calcular(ctx(min_retraso=-300)) is None


def test_combustible_faltante():
    c = CargoPorCombustibleFaltante().calcular(ctx(c_ini=4, c_fin=2))
    assert c.monto.monto == Decimal("590.00")  # 20 L * 24.50 + 100


def test_combustible_igual_o_mayor_no_cobra():
    assert CargoPorCombustibleFaltante().calcular(ctx(c_ini=2, c_fin=2)) is None
    assert CargoPorCombustibleFaltante().calcular(ctx(c_ini=2, c_fin=4)) is None


@pytest.mark.parametrize("recorrido,esperado", [(500, None), (499, None), (501, "5.00"), (700, "1000.00")])
def test_kilometraje(recorrido, esperado):
    cargo = CargoPorKilometrajeExcedente().calcular(ctx(km_ini=1000, km_fin=1000 + recorrido))
    assert (cargo is None) if esperado is None else cargo.monto.monto == Decimal(esperado)


def test_kilometraje_final_menor_al_inicial():
    with pytest.raises(DomainError):
        CargoPorKilometrajeExcedente().calcular(ctx(km_ini=1000, km_fin=900))


def test_calculadora_aplica_las_tres_politicas():
    cargos = CalculadoraDeCargosExtra().calcular(ctx(min_retraso=200, km_fin=1700, c_fin=1))
    assert {c.tipo for c in cargos} == {TipoDeCargo.RETRASO, TipoDeCargo.COMBUSTIBLE, TipoDeCargo.KILOMETRAJE}


def test_solo_administracion_cancela_cargos():
    c = CargoExtra(TipoDeCargo.RETRASO, Dinero(Decimal("90")))
    with pytest.raises(DomainError):
        c.cancelar(Rol.AGENTE)
    c.cancelar(Rol.ADMINISTRACION)
    assert c.cancelado
