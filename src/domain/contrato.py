"""Aggregate ContratoDeRenta (US04-US07, US12, US13; glosario #15, #19; ADR-02)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from . import events as ev
from .cargos import CalculadoraDeCargosExtra, CargoExtra, ContextoDeCargo
from .specifications import (VoucherATitular, cancelacion_autorizada, danos_cobrables, extension_permitida,
                             inspeccion_de_salida_valida)
from .value_objects import (ContratoYaDevuelto, Dinero, DocumentacionConductor, DomainError,
                            InspeccionDeVehiculo, PeriodoDeRenta, Rol, TipoDeCargo, VoucherAbierto)


@dataclass(frozen=True)
class SolicitudDeExtension:
    ahora: datetime
    fin_pactado_actual: datetime
    nuevo_fin: datetime
    vehiculo_reservado_por_otro: bool


@dataclass(frozen=True)
class SolicitudDeCancelacion:
    rol: Rol
    pin_valido: bool


@dataclass
class ContratoDeRenta:
    contrato_id: str
    reservacion_id: str
    vehiculo_id: str
    periodo: PeriodoDeRenta
    tarifa_diaria: Dinero
    voucher: VoucherAbierto
    inspeccion_salida: InspeccionDeVehiculo
    inspeccion_devolucion: Optional[InspeccionDeVehiculo] = None
    hora_devolucion: Optional[datetime] = None
    cargos: List[CargoExtra] = field(default_factory=list)
    _eventos: List = field(default_factory=list, repr=False)

    @classmethod
    def crear(cls, contrato_id: str, reservacion_id: str, vehiculo_id: str, periodo: PeriodoDeRenta,
              tarifa_diaria: Dinero, voucher: VoucherAbierto, inspeccion_salida: InspeccionDeVehiculo,
              documentacion: DocumentacionConductor) -> "ContratoDeRenta":
        """CU-01: no se firma la salida sin esquema de daños y ≥1 foto (RN-04);
        el voucher debe estar a nombre del titular de la licencia (RN-05)."""
        if not inspeccion_de_salida_valida().is_satisfied_by(inspeccion_salida):
            raise DomainError("No se puede firmar la salida: falta el esquema de daños o al menos una fotografía")
        if not VoucherATitular(documentacion.titular).is_satisfied_by(voucher):
            raise DomainError("La tarjeta debe estar a nombre del titular de la licencia")
        c = cls(contrato_id, reservacion_id, vehiculo_id, periodo, tarifa_diaria, voucher, inspeccion_salida)
        c._eventos.append(ev.VehiculoEntregado(
            contrato_id=contrato_id, vehiculo_id=vehiculo_id, reservacion_id=reservacion_id))
        return c

    @property
    def devuelto(self) -> bool:
        return self.inspeccion_devolucion is not None

    def registrar_devolucion(self, inspeccion: InspeccionDeVehiculo, hora: datetime,
                             calculadora: CalculadoraDeCargosExtra,
                             capacidad_tanque_litros: int, precio_litro: Dinero) -> None:
        if self.devuelto:
            raise ContratoYaDevuelto("La devolución ya fue registrada para este contrato")
        ctx = ContextoDeCargo(self.periodo, self.tarifa_diaria, self.inspeccion_salida, inspeccion,
                              hora, capacidad_tanque_litros, precio_litro)
        nuevos = calculadora.calcular(ctx)       # puede lanzar DomainError (km negativo)
        self.inspeccion_devolucion, self.hora_devolucion = inspeccion, hora
        self.cargos.extend(nuevos)
        self._eventos.append(ev.VehiculoDevuelto(contrato_id=self.contrato_id, vehiculo_id=self.vehiculo_id))
        nuevos = inspeccion.danos_nuevos_respecto_a(self.inspeccion_salida)
        if nuevos:
            self._eventos.append(ev.DanosDetectados(contrato_id=self.contrato_id, zonas=nuevos))
        self._eventos.append(ev.CargosExtraCalculados(contrato_id=self.contrato_id, total=self.total_cargos().monto))

    def agregar_cargo_retroactivo(self, cargo: CargoExtra) -> None:
        """US13 / RN-14: cargo posterior al cierre (p.ej. Mantenimiento Mayor). S-5 pendiente."""
        self.cargos.append(cargo)

    def registrar_cargo_por_danos(self, monto: Dinero, descripcion: str = "") -> None:
        """S-3: el monto lo captura el agente; el dominio exige que existan daños nuevos documentados."""
        if not danos_cobrables().is_satisfied_by(self):
            raise DomainError("Solo se cobran daños nuevos detectados en la inspección de devolución")
        self.cargos.append(CargoExtra(TipoDeCargo.DANOS, monto, descripcion or "Daños nuevos en devolución"))

    def extender(self, nuevo_fin: datetime, ahora: datetime, vehiculo_reservado_por_otro: bool) -> Dinero:
        """RN-12 (US09): ≥ 6 h de anticipación y vehículo no reservado. Cobra por adelantado los días extra."""
        if self.devuelto:
            raise ContratoYaDevuelto("No se puede extender un contrato ya devuelto")
        sol = SolicitudDeExtension(ahora, self.periodo.fin_pactado, nuevo_fin, vehiculo_reservado_por_otro)
        if not extension_permitida().is_satisfied_by(sol):
            raise DomainError("Extensión no permitida: requiere ≥ 6 h de anticipación, una fecha posterior "
                              "y que el vehículo no esté reservado por otro cliente")
        dias_extra = PeriodoDeRenta(self.periodo.fin_pactado, nuevo_fin).dias
        monto = self.tarifa_diaria.por(dias_extra)
        self.periodo = PeriodoDeRenta(self.periodo.inicio, nuevo_fin)
        self.cargos.append(CargoExtra(TipoDeCargo.EXTENSION, monto, f"{dias_extra} día(s) extra pagados por adelantado"))
        self._eventos.append(ev.RentaExtendida(contrato_id=self.contrato_id, nuevo_fin_pactado=nuevo_fin,
                                               monto=monto.monto))
        return monto

    def cancelar_cargo(self, indice: int, solicitud: SolicitudDeCancelacion, motivo: str) -> None:
        """RN-11 (US08): solo Administración con PIN válido cancela un cargo extra."""
        if not cancelacion_autorizada().is_satisfied_by(solicitud):
            raise DomainError("Cancelar cargos requiere rol Administración y PIN válido")
        if not 0 <= indice < len(self.cargos):
            raise DomainError("El cargo indicado no existe")
        cargo = self.cargos[indice]
        if cargo.cancelado:
            raise DomainError("El cargo ya estaba cancelado")
        cargo.cancelar(solicitud.rol)
        self._eventos.append(ev.CargoCancelado(contrato_id=self.contrato_id, tipo=cargo.tipo.value,
                                               monto=cargo.monto.monto, motivo=motivo))

    def total_cargos(self) -> Dinero:
        total = Dinero.cero()
        for c in self.cargos:
            if not c.cancelado:
                total = total + c.monto
        return total

    def pull_events(self):
        e, self._eventos = self._eventos, []
        return e
