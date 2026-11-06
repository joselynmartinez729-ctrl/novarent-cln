"""Extensión de renta (US09), cancelación de cargos con autorización (US08) y daños (US05)."""
from datetime import timedelta
from decimal import Decimal

import pytest

from src.domain import events as ev
from src.domain.cargos import CalculadoraDeCargosExtra
from src.domain.contrato import ContratoDeRenta, SolicitudDeCancelacion, SolicitudDeExtension
from src.domain.specifications import extension_permitida, cancelacion_autorizada, danos_cobrables
from src.domain.value_objects import (ContratoYaDevuelto, Dinero, DomainError, InspeccionDeVehiculo, Kilometraje,
                                      NivelDeCombustible, PeriodoDeRenta, Rol, TipoDeCargo, VoucherAbierto)
from tests.conftest import FIN, INICIO, doc, insp

PRECIO = Dinero(Decimal("24.50"))


def contrato(salida=None):
    return ContratoDeRenta.crear("C1", "R1", "V1", PeriodoDeRenta(INICIO, FIN), Dinero(Decimal("450")),
                                 VoucherAbierto("1234", "AUT", "Ana Pérez"), salida or insp(), doc())


def con_danos(*zonas, km=1100):
    return InspeccionDeVehiculo(True, ("f.jpg",), Kilometraje(km), NivelDeCombustible(4), tuple(zonas))


# ---------------- Extensión de renta ----------------
def sol(ahora_antes_h=10, nuevo_fin=FIN + timedelta(days=1), reservado=False):
    return SolicitudDeExtension(FIN - timedelta(hours=ahora_antes_h), FIN, nuevo_fin, reservado)


@pytest.mark.parametrize("horas,ok", [(10, True), (6, True), (5.99, False), (1, False)])
def test_extension_requiere_6_horas_de_anticipacion(horas, ok):
    assert extension_permitida().is_satisfied_by(sol(horas)) is ok


def test_extension_no_permitida_si_el_auto_esta_reservado():
    assert not extension_permitida().is_satisfied_by(sol(reservado=True))


def test_extension_debe_alargar_la_renta():
    assert not extension_permitida().is_satisfied_by(sol(nuevo_fin=FIN))
    assert not extension_permitida().is_satisfied_by(sol(nuevo_fin=FIN - timedelta(hours=1)))


def test_extender_cobra_por_adelantado_y_actualiza_periodo():
    c = contrato(); c.pull_events()
    monto = c.extender(FIN + timedelta(days=2), FIN - timedelta(hours=8), False)
    assert monto.monto == Decimal("900.00")
    assert c.periodo.fin_pactado == FIN + timedelta(days=2)
    assert c.cargos[-1].tipo == TipoDeCargo.EXTENSION
    e = c.pull_events()[0]
    assert isinstance(e, ev.RentaExtendida) and e.monto == Decimal("900.00")


def test_extender_fraccion_de_dia_cuenta_como_dia():
    c = contrato()
    assert c.extender(FIN + timedelta(hours=3), FIN - timedelta(hours=8), False).monto == Decimal("450.00")


def test_extension_cambia_el_calculo_de_retraso():
    """Tras extender, el retraso se mide contra el nuevo fin pactado."""
    c = contrato()
    c.extender(FIN + timedelta(days=1), FIN - timedelta(hours=8), False)
    c.registrar_devolucion(insp(1100), FIN + timedelta(days=1, minutes=30), CalculadoraDeCargosExtra(), 40, PRECIO)
    assert TipoDeCargo.RETRASO not in {x.tipo for x in c.cargos}


@pytest.mark.parametrize("ahora_antes,reservado", [(2, False), (10, True)])
def test_extender_rechazada(ahora_antes, reservado):
    c = contrato()
    with pytest.raises(DomainError):
        c.extender(FIN + timedelta(days=1), FIN - timedelta(hours=ahora_antes), reservado)
    assert c.periodo.fin_pactado == FIN and c.cargos == []  # nada cambió


def test_no_se_extiende_un_contrato_devuelto():
    c = contrato()
    c.registrar_devolucion(insp(1100), FIN, CalculadoraDeCargosExtra(), 40, PRECIO)
    with pytest.raises(ContratoYaDevuelto):
        c.extender(FIN + timedelta(days=1), FIN - timedelta(hours=8), False)


# ---------------- Cancelación de cargos ----------------
def contrato_con_cargo():
    c = contrato()
    c.registrar_devolucion(insp(1700), FIN, CalculadoraDeCargosExtra(), 40, PRECIO)  # genera cargo de km
    c.pull_events()
    return c


def test_autorizacion_and():
    assert cancelacion_autorizada().is_satisfied_by(SolicitudDeCancelacion(Rol.ADMINISTRACION, True))
    assert not cancelacion_autorizada().is_satisfied_by(SolicitudDeCancelacion(Rol.ADMINISTRACION, False))
    assert not cancelacion_autorizada().is_satisfied_by(SolicitudDeCancelacion(Rol.AGENTE, True))


def test_administracion_con_pin_cancela_y_total_baja():
    c = contrato_con_cargo()
    antes = c.total_cargos().monto
    c.cancelar_cargo(0, SolicitudDeCancelacion(Rol.ADMINISTRACION, True), "Cortesía autorizada")
    assert c.cargos[0].cancelado and c.total_cargos().monto == Decimal("0.00") < antes
    e = c.pull_events()[0]
    assert isinstance(e, ev.CargoCancelado) and e.motivo == "Cortesía autorizada"


@pytest.mark.parametrize("rol,pin", [(Rol.AGENTE, True), (Rol.ADMINISTRACION, False), (Rol.PATIO, False)])
def test_cancelacion_no_autorizada(rol, pin):
    c = contrato_con_cargo()
    with pytest.raises(DomainError):
        c.cancelar_cargo(0, SolicitudDeCancelacion(rol, pin), "x")
    assert not c.cargos[0].cancelado


def test_cancelar_cargo_inexistente_o_repetido():
    c = contrato_con_cargo()
    ok = SolicitudDeCancelacion(Rol.ADMINISTRACION, True)
    with pytest.raises(DomainError):
        c.cancelar_cargo(5, ok, "x")
    c.cancelar_cargo(0, ok, "x")
    with pytest.raises(DomainError):
        c.cancelar_cargo(0, ok, "x")


# ---------------- Inspecciones y daños ----------------
def test_danos_nuevos_respecto_a_la_salida():
    salida = con_danos("rayón puerta")
    dev = con_danos("Rayón Puerta", "abolladura cofre")
    assert dev.danos_nuevos_respecto_a(salida) == ("abolladura cofre",)


def test_devolucion_con_danos_nuevos_emite_evento():
    c = contrato(salida=con_danos("rayón puerta", km=1000)); c.pull_events()
    c.registrar_devolucion(con_danos("rayón puerta", "abolladura cofre"), FIN, CalculadoraDeCargosExtra(), 40, PRECIO)
    tipos = [type(e) for e in c.pull_events()]
    assert ev.DanosDetectados in tipos


def test_devolucion_sin_danos_nuevos_no_emite_evento():
    c = contrato(salida=con_danos("rayón puerta", km=1000)); c.pull_events()
    c.registrar_devolucion(con_danos("rayón puerta"), FIN, CalculadoraDeCargosExtra(), 40, PRECIO)
    assert ev.DanosDetectados not in [type(e) for e in c.pull_events()]


def test_cargo_por_danos_solo_con_danos_nuevos():
    c = contrato(salida=con_danos(km=1000))
    with pytest.raises(DomainError):  # aún no hay devolución
        c.registrar_cargo_por_danos(Dinero(Decimal("800")))
    c.registrar_devolucion(con_danos("abolladura cofre"), FIN, CalculadoraDeCargosExtra(), 40, PRECIO)
    assert danos_cobrables().is_satisfied_by(c)
    c.registrar_cargo_por_danos(Dinero(Decimal("800")), "Abolladura en cofre")
    assert c.cargos[-1].tipo == TipoDeCargo.DANOS and c.total_cargos().monto == Decimal("800.00")


def test_no_se_cobran_danos_preexistentes():
    c = contrato(salida=con_danos("rayón puerta", km=1000))
    c.registrar_devolucion(con_danos("rayón puerta"), FIN, CalculadoraDeCargosExtra(), 40, PRECIO)
    with pytest.raises(DomainError):
        c.registrar_cargo_por_danos(Dinero(Decimal("500")))
