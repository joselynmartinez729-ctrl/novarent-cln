from datetime import timedelta
from decimal import Decimal

import pytest

from src.domain import events as ev
from src.domain.cargos import CalculadoraDeCargosExtra
from src.domain.compensacion import CompensacionDeCategoria, DisponibilidadDeCategoria, TipoDeOferta
from src.domain.contrato import ContratoDeRenta
from src.domain.value_objects import (Categoria, ConflictoDeEstado, ContratoYaDevuelto, Dinero, DomainError,
                                      EstatusDeReservacion, EstatusDeVehiculo, NivelDeCombustible,
                                      TransicionInvalida, VoucherAbierto, Kilometraje, PeriodoDeRenta, Rol)
from tests.conftest import FIN, HOY, INICIO, doc, insp, reservacion, vehiculo
from datetime import date


# ---------- Reservacion (CU-02) ----------
def test_documentacion_valida_verifica_la_reservacion():
    r = reservacion()
    assert r.validar_documentacion(doc(), HOY) is True
    assert r.documentacion_verificada and r.estatus == EstatusDeReservacion.CONFIRMADA


def test_documentacion_invalida_cancela_y_retiene_10_por_ciento():
    r = reservacion()
    assert r.validar_documentacion(doc(fecha_nacimiento=date(2012, 1, 1)), HOY) is False
    assert r.estatus == EstatusDeReservacion.DOCUMENTACION_INVALIDA
    assert r.retencion.monto == Decimal("90.00")  # 10 % de 900
    assert isinstance(r.pull_events()[0], ev.DocumentacionInvalidaRegistrada)
    with pytest.raises(ConflictoDeEstado):
        r.marcar_entregada()
    with pytest.raises(ConflictoDeEstado):
        r.validar_documentacion(doc(), HOY)


def test_no_se_entrega_sin_documentacion_verificada():
    with pytest.raises(ConflictoDeEstado):
        reservacion().marcar_entregada()


# ---------- Compensacion (CU-03) ----------
def _determinar(disp, rechaza=False, sup=Categoria.SUV, inf=Categoria.COMPACTO):
    return CompensacionDeCategoria().determinar_oferta(
        Dinero(Decimal("700")), disp, sup, inf, Dinero(Decimal("550")), rechaza)


def test_sin_compensacion_si_hay_categoria():
    assert _determinar(DisponibilidadDeCategoria(True, True, True)) is None


def test_upgrade_gratuito_mantiene_tarifa():
    o = _determinar(DisponibilidadDeCategoria(False, True, True))
    assert o.tipo == TipoDeOferta.UPGRADE and o.categoria == Categoria.SUV
    assert o.tarifa_diaria.monto == Decimal("700.00") and o.descuento_adicional_pct == 0


def test_downgrade_con_20_por_ciento_si_rechaza_upgrade():
    o = _determinar(DisponibilidadDeCategoria(False, True, True), rechaza=True)
    assert o.tipo == TipoDeOferta.DOWNGRADE and o.tarifa_diaria.monto == Decimal("440.00")  # 550 * 0.8


def test_downgrade_si_no_hay_superior():
    o = _determinar(DisponibilidadDeCategoria(False, False, True), sup=None)
    assert o.tipo == TipoDeOferta.DOWNGRADE


def test_sin_alternativas():
    assert _determinar(DisponibilidadDeCategoria(False, False, False)) is None


def test_reservacion_aplica_compensacion_y_cancela():
    r = reservacion(Categoria.SEDAN, "700")
    o = _determinar(DisponibilidadDeCategoria(False, True, False))
    r.aplicar_compensacion(o)
    assert r.categoria_entrega == Categoria.SUV and r.categoria == Categoria.SEDAN
    assert isinstance(r.pull_events()[0], ev.CategoriaCompensada)
    r.cancelar_por_falta_de_categoria()
    assert r.estatus == EstatusDeReservacion.CANCELADA
    with pytest.raises(ConflictoDeEstado):
        r.cancelar_por_falta_de_categoria()


# ---------- Contrato (CU-01 / CU-04) ----------
def _voucher(titular="Ana Pérez"):
    return VoucherAbierto("1234", "AUT-1", titular)


def _contrato(**kw):
    args = dict(contrato_id="C1", reservacion_id="R1", vehiculo_id="V1", periodo=PeriodoDeRenta(INICIO, FIN),
                tarifa_diaria=Dinero(Decimal("450")), voucher=_voucher(), inspeccion_salida=insp(),
                documentacion=doc())
    args.update(kw)
    return ContratoDeRenta.crear(**args)


def test_crear_contrato_emite_evento():
    c = _contrato()
    assert isinstance(c.pull_events()[0], ev.VehiculoEntregado)


def test_no_se_firma_sin_foto_ni_esquema():
    with pytest.raises(DomainError):
        _contrato(inspeccion_salida=insp(fotos=()))
    with pytest.raises(DomainError):
        _contrato(inspeccion_salida=insp(esquema=False))


def test_tarjeta_debe_ser_del_titular_de_la_licencia():
    with pytest.raises(DomainError):
        _contrato(voucher=_voucher("Otra Persona"))


def test_voucher_requiere_4_digitos():
    with pytest.raises(DomainError):
        VoucherAbierto("12", "X", "A")


def test_devolucion_calcula_cargos_y_solo_una_vez():
    c = _contrato()
    c.pull_events()
    c.registrar_devolucion(insp(1700, 2), FIN + timedelta(minutes=121), CalculadoraDeCargosExtra(), 40,
                           Dinero(Decimal("24.50")))
    assert c.devuelto and len(c.cargos) == 3
    assert c.total_cargos().monto == Decimal("90.00") + Decimal("590.00") + Decimal("1000.00")
    tipos = {type(e) for e in c.pull_events()}
    assert tipos == {ev.VehiculoDevuelto, ev.CargosExtraCalculados}
    with pytest.raises(ContratoYaDevuelto):
        c.registrar_devolucion(insp(1700, 2), FIN, CalculadoraDeCargosExtra(), 40, Dinero(Decimal("24.50")))


def test_devolucion_con_error_no_deja_el_contrato_a_medias():
    c = _contrato()
    with pytest.raises(DomainError):
        c.registrar_devolucion(insp(10, 4), FIN, CalculadoraDeCargosExtra(), 40, Dinero(Decimal("24.50")))
    assert not c.devuelto and c.cargos == []


def test_cargo_cancelado_no_suma_al_total():
    c = _contrato()
    c.registrar_devolucion(insp(1700, 4), FIN, CalculadoraDeCargosExtra(), 40, Dinero(Decimal("24.50")))
    c.cargos[0].cancelar(Rol.ADMINISTRACION)
    assert c.total_cargos().monto == Decimal("0.00")


# ---------- Vehiculo: State Machine (N2, US11) ----------
def test_ciclo_completo_del_vehiculo():
    v = vehiculo()
    v.entregar(); v.recibir_en_revision(); v.iniciar_limpieza(); v.marcar_terminado()
    assert v.estatus == EstatusDeVehiculo.DISPONIBLE
    assert isinstance(v.pull_events()[0], ev.VehiculoLiberado)


def test_solo_limpieza_lleva_a_disponible():
    v = vehiculo()
    v.entregar(); v.recibir_en_revision()
    with pytest.raises(TransicionInvalida):
        v.marcar_terminado()


def test_no_se_entrega_un_vehiculo_no_disponible():
    v = vehiculo(); v.estatus = EstatusDeVehiculo.LIMPIEZA
    with pytest.raises(ConflictoDeEstado):
        v.entregar()


def test_mantenimiento_mayor_desde_limpieza():
    v = vehiculo(); v.entregar(); v.recibir_en_revision(); v.iniciar_limpieza()
    v.reportar_mantenimiento_mayor("Humo de cigarro", Decimal("1500"))
    assert v.estatus == EstatusDeVehiculo.MANTENIMIENTO_MAYOR
    e = v.pull_events()[0]
    assert isinstance(e, ev.MantenimientoMayorRegistrado) and e.monto == Decimal("1500")
    with pytest.raises(TransicionInvalida):
        v.iniciar_limpieza()


@pytest.mark.parametrize("txt,n", [("vacio", 0), ("1/4", 1), ("1/2", 2), ("3/4", 3), ("lleno", 4)])
def test_nivel_de_combustible(txt, n):
    assert NivelDeCombustible.desde_texto(txt).cuartos == n


def test_valores_invalidos():
    for f in (lambda: NivelDeCombustible.desde_texto("medio"), lambda: NivelDeCombustible(5),
              lambda: Kilometraje(-1), lambda: Dinero(Decimal("-1")),
              lambda: PeriodoDeRenta(FIN, INICIO)):
        with pytest.raises(DomainError):
            f()


def test_periodo_dias_minimo_1():
    assert PeriodoDeRenta(INICIO, INICIO + timedelta(hours=3)).dias == 1
    assert PeriodoDeRenta(INICIO, INICIO + timedelta(hours=49)).dias == 3
