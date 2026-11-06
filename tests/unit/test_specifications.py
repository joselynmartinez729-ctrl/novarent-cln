from datetime import date

from src.domain.specifications import (ConductorMayorDeEdad, LicenciaVigente, VehiculoDisponible,
                                       VoucherATitular, documentacion_valida, existe_alternativa,
                                       inspeccion_de_salida_valida, requiere_compensacion,
                                       reservacion_entregable)
from src.domain.compensacion import DisponibilidadDeCategoria
from src.domain.value_objects import EstatusDeVehiculo, VoucherAbierto
from tests.conftest import HOY, doc, insp, reservacion, vehiculo


def test_documentacion_valida():
    assert documentacion_valida(HOY).is_satisfied_by(doc())


def test_menor_de_edad():
    assert not documentacion_valida(HOY).is_satisfied_by(doc(fecha_nacimiento=date(2010, 1, 1)))


def test_exactamente_18_anios_es_valido():
    assert ConductorMayorDeEdad(HOY).is_satisfied_by(doc(fecha_nacimiento=date(2008, 11, 5)))
    assert not ConductorMayorDeEdad(HOY).is_satisfied_by(doc(fecha_nacimiento=date(2008, 11, 6)))


def test_licencia_o_identificacion_vencida():
    assert not documentacion_valida(HOY).is_satisfied_by(doc(licencia_vigente_hasta=date(2026, 11, 4)))
    assert not documentacion_valida(HOY).is_satisfied_by(doc(identificacion_vigente_hasta=date(2026, 1, 1)))
    assert LicenciaVigente(HOY).is_satisfied_by(doc(licencia_vigente_hasta=HOY))


def test_vehiculo_disponible_y_not():
    v = vehiculo()
    assert VehiculoDisponible().is_satisfied_by(v)
    v.estatus = EstatusDeVehiculo.LIMPIEZA
    assert not VehiculoDisponible().is_satisfied_by(v)
    assert (~VehiculoDisponible()).is_satisfied_by(v)


def test_inspeccion_requiere_esquema_y_foto():
    assert inspeccion_de_salida_valida().is_satisfied_by(insp())
    assert not inspeccion_de_salida_valida().is_satisfied_by(insp(fotos=()))
    assert not inspeccion_de_salida_valida().is_satisfied_by(insp(esquema=False))


def test_voucher_a_titular_ignora_mayusculas():
    v = VoucherAbierto("1234", "AUT1", "ANA PÉREZ")
    assert VoucherATitular("ana pérez").is_satisfied_by(v)
    assert not VoucherATitular("Otra Persona").is_satisfied_by(v)


def test_reservacion_entregable():
    r = reservacion()
    assert not reservacion_entregable().is_satisfied_by(r)
    r.documentacion_verificada = True
    assert reservacion_entregable().is_satisfied_by(r)


def test_compensacion_and_or_not():
    assert not requiere_compensacion().is_satisfied_by(DisponibilidadDeCategoria(True, True, True))
    assert existe_alternativa().is_satisfied_by(DisponibilidadDeCategoria(False, True, False))
    assert existe_alternativa().is_satisfied_by(DisponibilidadDeCategoria(False, False, True))
    assert not existe_alternativa().is_satisfied_by(DisponibilidadDeCategoria(False, False, False))
