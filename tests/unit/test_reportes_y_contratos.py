"""Reportes (US14/US15) y servicios de contrato (US08/US09/daños) con repositorios en memoria."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from src.application.commands import RegistrarDevolucionCommand
from src.application.errors import NoEncontrado
from src.domain import events as ev
from src.domain.value_objects import Categoria, DomainError, EstatusDeVehiculo, InspeccionDeVehiculo, Kilometraje, NivelDeCombustible, Rol
from tests.conftest import FIN, doc, insp, reservacion, vehiculo
from tests.unit.test_servicios import Mundo, _entregar


def _devuelto(m, insp_dev, hora=FIN):
    m.con(None, vehiculo())
    cid = _entregar(m)
    m.devolucion.registrar_devolucion(RegistrarDevolucionCommand(cid, insp_dev, hora))
    return cid


# ---------- US14 Tasa de Utilización ----------
def test_tasa_de_utilizacion():
    m = Mundo()
    flota = [vehiculo(Categoria.ECONOMICO, "E1"), vehiculo(Categoria.ECONOMICO, "E2"),
             vehiculo(Categoria.SUV, "U1"), vehiculo(Categoria.SUV, "U2")]
    flota[0].estatus = EstatusDeVehiculo.RENTADO
    m.con(None, *flota)
    r = m.consultas.tasa_de_utilizacion()
    assert (r.rentados, r.flota_total, r.tasa_pct) == (1, 4, Decimal("25.00"))
    assert r.fecha == date(2026, 11, 5)
    eco = next(x for x in r.por_categoria if x.categoria == "ECONOMICO")
    assert (eco.rentados, eco.flota) == (1, 2)


def test_tasa_con_flota_vacia_es_cero():
    assert Mundo().consultas.tasa_de_utilizacion().tasa_pct == Decimal("0.00")


def test_tasa_redondea_a_dos_decimales():
    m = Mundo()
    flota = [vehiculo(Categoria.ECONOMICO, f"E{i}") for i in range(3)]
    flota[0].estatus = EstatusDeVehiculo.RENTADO
    m.con(None, *flota)
    assert m.consultas.tasa_de_utilizacion().tasa_pct == Decimal("33.33")


# ---------- US15 Ingresos por Cargos Adicionales ----------
def test_ingresos_semanales_desglosados():
    m = Mundo()
    _devuelto(m, insp(1700, 2), FIN + timedelta(minutes=121))  # retraso 90 + combustible 590 + km 1000
    r = m.consultas.ingresos_por_cargos_adicionales(date(2026, 11, 9))  # lunes de la semana del 12-nov
    por = {f.tipo: f for f in r.filas}
    assert por["RETRASO"].monto_mxn == Decimal("90.00") and por["RETRASO"].cargos == 1
    assert por["COMBUSTIBLE"].monto_mxn == Decimal("590.00")
    assert por["KILOMETRAJE"].monto_mxn == Decimal("1000.00")
    assert por["DANOS"].monto_mxn == Decimal("0")
    assert r.total_mxn == Decimal("1680.00") and r.contratos == 1
    assert (r.desde, r.hasta) == (date(2026, 11, 9), date(2026, 11, 15))


def test_ingresos_fuera_de_la_semana_no_cuentan():
    m = Mundo()
    _devuelto(m, insp(1700, 2), FIN + timedelta(minutes=121))
    r = m.consultas.ingresos_por_cargos_adicionales(date(2026, 11, 16))
    assert r.total_mxn == Decimal("0") and r.contratos == 0


def test_ingresos_por_defecto_usa_la_semana_en_curso():
    r = Mundo().consultas.ingresos_por_cargos_adicionales()
    assert r.desde == date(2026, 11, 2) and r.hasta == date(2026, 11, 8)  # lunes-domingo de la semana del 5-nov


def test_ingresos_excluyen_cargos_cancelados():
    m = Mundo()
    cid = _devuelto(m, insp(1700, 4))  # solo km: 1000
    m.contratos.cancelar_cargo(cid, 0, Rol.ADMINISTRACION, "4321", "Cortesía")
    assert m.consultas.ingresos_por_cargos_adicionales(date(2026, 11, 9)).total_mxn == Decimal("0")


# ---------- US09 extensión ----------
def test_extender_renta_cobra_y_actualiza():
    m = Mundo()
    cid = _devuelto_sin_cerrar(m)
    r = m.contratos.extender_renta(cid, FIN + timedelta(days=1))
    assert r.monto_mxn == Decimal("450.00") and r.nuevo_fin_pactado == FIN + timedelta(days=1)
    assert m.consultas.resumen_de_cargos(cid).cargos[0].tipo == "EXTENSION"
    assert isinstance(m.pub.historial[-1], ev.RentaExtendida)


def _devuelto_sin_cerrar(m):
    m.con(None, vehiculo())
    return _entregar(m)


def test_extender_rechazada_por_reserva_ajena():
    m = Mundo()
    cid = _devuelto_sin_cerrar(m)
    with pytest.raises(DomainError):
        m.contratos.extender_renta(cid, FIN + timedelta(days=1), vehiculo_reservado_por_otro=True)
    assert m.consultas.resumen_de_cargos(cid).cargos == []  # rollback / sin cambios


def test_extender_contrato_inexistente():
    with pytest.raises(NoEncontrado):
        Mundo().contratos.extender_renta("NOPE", FIN)


# ---------- US08 cancelación con PIN ----------
def test_cancelar_cargo_con_pin_correcto():
    m = Mundo()
    cid = _devuelto(m, insp(1700, 4))
    r = m.contratos.cancelar_cargo(cid, 0, Rol.ADMINISTRACION, "4321", "Cortesía")
    assert r.cargos[0].cancelado and r.total_mxn == Decimal("0.00")
    assert isinstance(m.pub.historial[-1], ev.CargoCancelado)


@pytest.mark.parametrize("rol,pin", [(Rol.ADMINISTRACION, "0000"), (Rol.AGENTE, "4321"), (Rol.ADMINISTRACION, "")])
def test_cancelar_cargo_sin_autorizacion(rol, pin):
    m = Mundo()
    cid = _devuelto(m, insp(1700, 4))
    with pytest.raises(DomainError):
        m.contratos.cancelar_cargo(cid, 0, rol, pin, "x")
    assert not m.consultas.resumen_de_cargos(cid).cargos[0].cancelado


def test_sin_pin_configurado_nadie_cancela():
    from src.infrastructure.memoria import ValidadorDePinConfigurable
    assert not ValidadorDePinConfigurable("").es_valido("")
    assert not ValidadorDePinConfigurable("").es_valido("1234")


# ---------- Daños ----------
def test_cargo_por_danos_via_servicio():
    m = Mundo()
    dano = InspeccionDeVehiculo(True, ("f.jpg",), Kilometraje(1100), NivelDeCombustible(4), ("abolladura cofre",))
    cid = _devuelto(m, dano)
    r = m.contratos.registrar_cargo_por_danos(cid, Decimal("800"), "Abolladura")
    assert r.total_mxn == Decimal("800.00") and r.cargos[-1].tipo == "DANOS"
    assert any(isinstance(e, ev.DanosDetectados) for e in m.pub.historial)


def test_cargo_por_danos_sin_danos_nuevos_se_rechaza():
    m = Mundo()
    cid = _devuelto(m, insp(1100, 4))
    with pytest.raises(DomainError):
        m.contratos.registrar_cargo_por_danos(cid, Decimal("800"))
