"""Patrón Specification con combinadores AND / OR / NOT.
Cada Specification encapsula una regla de negocio (RN-xx del BRD)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from .value_objects import EstatusDeReservacion, EstatusDeVehiculo


class Specification(ABC):
    @abstractmethod
    def is_satisfied_by(self, candidato) -> bool: ...

    def __and__(self, otra): return _And(self, otra)
    def __or__(self, otra): return _Or(self, otra)
    def __invert__(self): return _Not(self)


class _And(Specification):
    def __init__(self, a, b): self.a, self.b = a, b
    def is_satisfied_by(self, c): return self.a.is_satisfied_by(c) and self.b.is_satisfied_by(c)


class _Or(Specification):
    def __init__(self, a, b): self.a, self.b = a, b
    def is_satisfied_by(self, c): return self.a.is_satisfied_by(c) or self.b.is_satisfied_by(c)


class _Not(Specification):
    def __init__(self, a): self.a = a
    def is_satisfied_by(self, c): return not self.a.is_satisfied_by(c)


# ---- RN-01 Documentación del conductor (US10) : candidato = DocumentacionConductor ----
class ConductorMayorDeEdad(Specification):
    def __init__(self, hoy: date, edad_minima: int = 18):
        self.hoy, self.edad_minima = hoy, edad_minima
    def is_satisfied_by(self, doc): return doc.edad_en(self.hoy) >= self.edad_minima


class LicenciaVigente(Specification):
    def __init__(self, hoy: date): self.hoy = hoy
    def is_satisfied_by(self, doc): return doc.licencia_vigente_hasta >= self.hoy


class IdentificacionVigente(Specification):
    def __init__(self, hoy: date): self.hoy = hoy
    def is_satisfied_by(self, doc): return doc.identificacion_vigente_hasta >= self.hoy


def documentacion_valida(hoy: date) -> Specification:
    return ConductorMayorDeEdad(hoy) & LicenciaVigente(hoy) & IdentificacionVigente(hoy)


# ---- RN-03 Vehículo disponible (N2) : candidato = Vehiculo ----
class VehiculoDisponible(Specification):
    def is_satisfied_by(self, v): return v.estatus == EstatusDeVehiculo.DISPONIBLE


# ---- RN-04 Inspección de salida (US05) : candidato = InspeccionDeVehiculo ----
class EsquemaDeDanosCompletado(Specification):
    def is_satisfied_by(self, i): return i.esquema_completado


class AlMenosUnaFoto(Specification):
    def is_satisfied_by(self, i): return len(i.fotos) >= 1


def inspeccion_de_salida_valida() -> Specification:
    return EsquemaDeDanosCompletado() & AlMenosUnaFoto()


# ---- RN-05 Voucher a nombre del titular de la licencia (US12) : candidato = VoucherAbierto ----
class VoucherATitular(Specification):
    def __init__(self, titular: str): self.titular = titular
    def is_satisfied_by(self, v): return v.titular.strip().lower() == self.titular.strip().lower()


# ---- Reservación entregable : candidato = Reservacion ----
class ReservacionConfirmada(Specification):
    def is_satisfied_by(self, r): return r.estatus == EstatusDeReservacion.CONFIRMADA


class DocumentacionVerificada(Specification):
    def is_satisfied_by(self, r): return r.documentacion_verificada


def reservacion_entregable() -> Specification:
    return ReservacionConfirmada() & DocumentacionVerificada()


# ---- RN-06/07 Compensación (N4, US03) : candidato = DisponibilidadDeCategoria ----
class HayEnCategoria(Specification):
    def is_satisfied_by(self, d): return d.hay_en_categoria


class HaySuperiorDisponible(Specification):
    def is_satisfied_by(self, d): return d.hay_superior


class HayInferiorDisponible(Specification):
    def is_satisfied_by(self, d): return d.hay_inferior


def requiere_compensacion() -> Specification:
    return ~HayEnCategoria()


def existe_alternativa() -> Specification:
    return requiere_compensacion() & (HaySuperiorDisponible() | HayInferiorDisponible())


# ---- RN-12 Extensión de renta (US09) : candidato = SolicitudDeExtension ----
class ExtensionConAnticipacion(Specification):
    """La solicitud debe hacerse al menos `horas_minimas` antes de la hora de devolución pactada."""
    def __init__(self, horas_minimas: int = 6): self.horas_minimas = horas_minimas
    def is_satisfied_by(self, sol):
        return (sol.fin_pactado_actual - sol.ahora).total_seconds() >= self.horas_minimas * 3600


class VehiculoReservadoPorOtro(Specification):
    def is_satisfied_by(self, sol): return sol.vehiculo_reservado_por_otro


class ExtensionAlargaLaRenta(Specification):
    def is_satisfied_by(self, sol): return sol.nuevo_fin > sol.fin_pactado_actual


def extension_permitida() -> Specification:
    """con ≥ 6 h de anticipación AND NOT reservado por otro AND la nueva fecha es posterior."""
    return ExtensionConAnticipacion() & ~VehiculoReservadoPorOtro() & ExtensionAlargaLaRenta()


# ---- RN-11 Autorización de cancelación de cargos (US08) : candidato = SolicitudDeCancelacion ----
class RolAdministracion(Specification):
    def is_satisfied_by(self, sol):
        from .value_objects import Rol
        return sol.rol == Rol.ADMINISTRACION


class PinValido(Specification):
    def is_satisfied_by(self, sol): return sol.pin_valido


def cancelacion_autorizada() -> Specification:
    return RolAdministracion() & PinValido()


# ---- Daños en la devolución (US05, N1) : candidato = ContratoDeRenta ----
class ContratoConDevolucion(Specification):
    def is_satisfied_by(self, c): return c.inspeccion_devolucion is not None


class HayDanosNuevos(Specification):
    def is_satisfied_by(self, c):
        return bool(c.inspeccion_devolucion.danos_nuevos_respecto_a(c.inspeccion_salida))


def danos_cobrables() -> Specification:
    return ContratoConDevolucion() & HayDanosNuevos()
