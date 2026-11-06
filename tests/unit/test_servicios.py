"""Service Layer con Repository/UoW en memoria (sin base de datos)."""
from datetime import timedelta
from decimal import Decimal

import pytest

from src.application.commands import DecisionDelCliente, EntregarVehiculoCommand, RegistrarDevolucionCommand
from src.application.errors import NoEncontrado, SinVehiculoDisponible
from src.application.services import (ConsultasDeNovaRent, ManejadorMantenimientoMayor,
                                      ServicioDeCompensacionDeCategoria, ServicioDeDevolucion, ServicioDeEntrega,
                                      ServicioDeContratos, ServicioDeLimpieza, ServicioDeValidacionDeDocumentacion)
from src.domain import events as ev
from src.domain.cargos import CalculadoraDeCargosExtra
from src.domain.value_objects import (Categoria, ConflictoDeEstado, DomainError, EstatusDeReservacion,
                                      EstatusDeVehiculo, TransicionInvalida)
from src.infrastructure.memoria import (AlmacenEnMemoria, CatalogoEstatico, PasarelaBancariaSimulada,
                                        PrecioCombustibleConfigurable, PublicadorEnMemoria, RelojFijo, UowEnMemoria,
                                        ValidadorDePinConfigurable)
from tests.conftest import FIN, HOY, INICIO, doc, insp, reservacion, vehiculo
from datetime import datetime


class Mundo:
    def __init__(self):
        self.alm, self.pub = AlmacenEnMemoria(), PublicadorEnMemoria()
        self.uow = lambda: UowEnMemoria(self.alm, self.pub)
        self.reloj = RelojFijo(datetime(2026, 11, 5, 10))
        self.validacion = ServicioDeValidacionDeDocumentacion(self.uow, self.reloj)
        self.compensacion = ServicioDeCompensacionDeCategoria(self.uow, CatalogoEstatico())
        self.entrega = ServicioDeEntrega(self.uow, PasarelaBancariaSimulada())
        self.devolucion = ServicioDeDevolucion(self.uow, CalculadoraDeCargosExtra(), PrecioCombustibleConfigurable("24.50"))
        self.limpieza = ServicioDeLimpieza(self.uow)
        self.consultas = ConsultasDeNovaRent(self.uow, self.reloj)
        self.contratos = ServicioDeContratos(self.uow, self.reloj, ValidadorDePinConfigurable("4321"))
        self.pub.suscribir(ev.MantenimientoMayorRegistrado, ManejadorMantenimientoMayor(self.uow))

    def con(self, r=None, *vs):
        r = r or reservacion()
        self.alm.reservaciones[r.reservacion_id] = r
        for v in vs:
            self.alm.vehiculos[v.vehiculo_id] = v
        return r


@pytest.fixture
def m():
    return Mundo()


def _entregar(m, reserva="RES-T"):
    m.validacion.validar_documentacion_del_conductor(reserva, doc())
    return m.entrega.entregar_vehiculo(EntregarVehiculoCommand(reserva, "1234", "Ana Pérez", insp()))


def test_flujo_completo_entrega_devolucion_limpieza(m):
    m.con(None, vehiculo())
    cid = _entregar(m)
    assert m.alm.vehiculos["V1"].estatus == EstatusDeVehiculo.RENTADO
    assert m.alm.reservaciones["RES-T"].estatus == EstatusDeReservacion.ENTREGADA
    m.devolucion.registrar_devolucion(RegistrarDevolucionCommand(cid, insp(1700, 2), FIN + timedelta(minutes=121)))
    resumen = m.consultas.resumen_de_cargos(cid)
    assert resumen.total_mxn == Decimal("1680.00") and len(resumen.cargos) == 3
    assert m.alm.vehiculos["V1"].estatus == EstatusDeVehiculo.EN_REVISION
    m.limpieza.iniciar_limpieza("V1")
    assert m.limpieza.marcar_terminado("V1").estatus == "DISPONIBLE"
    tipos = [type(e) for e in m.pub.historial]
    assert tipos == [ev.VehiculoEntregado, ev.VehiculoDevuelto, ev.CargosExtraCalculados, ev.VehiculoLiberado]


def test_documentacion_invalida_cancela(m):
    m.con(None, vehiculo())
    from datetime import date
    r = m.validacion.validar_documentacion_del_conductor("RES-T", doc(fecha_nacimiento=date(2015, 1, 1)))
    assert not r.documentacion_valida and r.estatus == "DOCUMENTACION_INVALIDA" and r.retencion_mxn == Decimal("90.00")
    assert isinstance(m.pub.historial[0], ev.DocumentacionInvalidaRegistrada)


def test_entrega_exige_documentacion_verificada(m):
    m.con(None, vehiculo())
    with pytest.raises(ConflictoDeEstado):
        m.entrega.entregar_vehiculo(EntregarVehiculoCommand("RES-T", "1234", "Ana Pérez", insp()))


def test_entrega_sin_vehiculo_disponible(m):
    v = vehiculo(); v.estatus = EstatusDeVehiculo.LIMPIEZA
    m.con(None, v)
    m.validacion.validar_documentacion_del_conductor("RES-T", doc())
    with pytest.raises(SinVehiculoDisponible):
        m.entrega.entregar_vehiculo(EntregarVehiculoCommand("RES-T", "1234", "Ana Pérez", insp()))


def test_error_de_dominio_hace_rollback(m):
    """Sin foto: ni el vehículo ni la reservación deben cambiar (ADR-03)."""
    m.con(None, vehiculo())
    m.validacion.validar_documentacion_del_conductor("RES-T", doc())
    with pytest.raises(DomainError):
        m.entrega.entregar_vehiculo(EntregarVehiculoCommand("RES-T", "1234", "Ana Pérez", insp(fotos=())))
    assert m.alm.vehiculos["V1"].estatus == EstatusDeVehiculo.DISPONIBLE
    assert m.alm.reservaciones["RES-T"].estatus == EstatusDeReservacion.CONFIRMADA
    assert m.alm.contratos == {}


def test_no_encontrado(m):
    with pytest.raises(NoEncontrado):
        m.consultas.reservacion("NOPE")
    with pytest.raises(NoEncontrado):
        m.limpieza.iniciar_limpieza("NOPE")


def test_doble_devolucion_es_conflicto(m):
    m.con(None, vehiculo())
    cid = _entregar(m)
    cmd = RegistrarDevolucionCommand(cid, insp(1100, 4), FIN)
    m.devolucion.registrar_devolucion(cmd)
    with pytest.raises(ConflictoDeEstado):
        m.devolucion.registrar_devolucion(cmd)


def test_limpieza_transicion_invalida(m):
    m.con(None, vehiculo())
    with pytest.raises(TransicionInvalida):
        m.limpieza.marcar_terminado("V1")


def test_mantenimiento_mayor_agrega_cargo_retroactivo(m):
    m.con(None, vehiculo())
    cid = _entregar(m)
    m.devolucion.registrar_devolucion(RegistrarDevolucionCommand(cid, insp(1100, 4), FIN))
    m.limpieza.iniciar_limpieza("V1")
    m.limpieza.reportar_mantenimiento_mayor("V1", "Humo de cigarro", Decimal("1500"))
    res = m.consultas.resumen_de_cargos(cid)
    assert [c.tipo for c in res.cargos] == ["MANTENIMIENTO_MAYOR"] and res.total_mxn == Decimal("1500.00")


def test_mantenimiento_mayor_sin_contrato_previo_no_falla(m):
    v = vehiculo(); v.estatus = EstatusDeVehiculo.LIMPIEZA
    m.con(None, v)
    m.limpieza.reportar_mantenimiento_mayor("V1", "Olor", Decimal("500"))
    assert m.alm.vehiculos["V1"].estatus == EstatusDeVehiculo.MANTENIMIENTO_MAYOR


def test_compensacion_upgrade(m):
    sedan = vehiculo(Categoria.SEDAN, "S1"); sedan.estatus = EstatusDeVehiculo.RENTADO
    m.con(reservacion(Categoria.SEDAN, "700"), sedan, vehiculo(Categoria.SUV, "U1"))
    assert m.compensacion.consultar_oferta("RES-T").tipo == "UPGRADE"
    r = m.compensacion.resolver_categoria_no_disponible("RES-T", DecisionDelCliente())
    assert r.resultado == "UPGRADE" and r.categoria_entrega == "SUV" and r.tarifa_diaria_mxn == Decimal("700.00")


def test_compensacion_downgrade_y_rechazo_cancela(m):
    lujo = vehiculo(Categoria.LUJO, "L1"); lujo.estatus = EstatusDeVehiculo.MANTENIMIENTO_MAYOR
    m.con(reservacion(Categoria.LUJO, "1400"), lujo, vehiculo(Categoria.SUV, "U1"))
    r = m.compensacion.resolver_categoria_no_disponible("RES-T", DecisionDelCliente())
    assert r.resultado == "DOWNGRADE" and r.tarifa_diaria_mxn == Decimal("760.00")
    m2 = Mundo(); lujo2 = vehiculo(Categoria.LUJO, "L1"); lujo2.estatus = EstatusDeVehiculo.LIMPIEZA
    m2.con(reservacion(Categoria.LUJO, "1400"), lujo2, vehiculo(Categoria.SUV, "U1"))
    r2 = m2.compensacion.resolver_categoria_no_disponible("RES-T", DecisionDelCliente(acepta_inferior=False))
    assert r2.resultado == "CANCELADA" and r2.estatus == "CANCELADA"


def test_compensacion_sin_necesidad_y_sin_alternativas(m):
    m.con(None, vehiculo())
    assert m.compensacion.consultar_oferta("RES-T") is None
    assert m.compensacion.resolver_categoria_no_disponible("RES-T", DecisionDelCliente()).resultado == "SIN_COMPENSACION"
    m2 = Mundo(); m2.con(None)
    assert m2.compensacion.resolver_categoria_no_disponible("RES-T", DecisionDelCliente()).resultado == "CANCELADA"


def test_panel_filtra_por_categoria(m):
    m.con(None, vehiculo(Categoria.ECONOMICO, "E1"), vehiculo(Categoria.SUV, "U1"))
    assert len(m.consultas.panel_de_vehiculos()) == 2
    assert [v.vehiculo_id for v in m.consultas.panel_de_vehiculos(Categoria.SUV)] == ["U1"]
    assert m.consultas.reservacion("RES-T").estatus == "CONFIRMADA"
