"""Ejecutor de casos de prueba NovaRent: aplica cada caso del CSV al DOMINIO y devuelve el resultado obtenido.
El oráculo (resultado_esperado) está escrito a mano a partir del BRD; no se calcula con el código."""
import csv
import json
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.domain.cargos import (CargoPorCombustibleFaltante, CargoPorKilometrajeExcedente, CargoPorRetraso,
                               ContextoDeCargo)
from src.domain.compensacion import CompensacionDeCategoria, DisponibilidadDeCategoria
from src.domain.contrato import SolicitudDeCancelacion, SolicitudDeExtension
from src.domain.reservacion import Reservacion
from src.domain.specifications import (VoucherATitular, cancelacion_autorizada, documentacion_valida,
                                       extension_permitida, inspeccion_de_salida_valida, requiere_compensacion)
from src.domain.value_objects import (Categoria, ConflictoDeEstado, Dinero, DocumentacionConductor, DomainError,
                                      EstatusDeVehiculo, InspeccionDeVehiculo, Kilometraje, NivelDeCombustible,
                                      PeriodoDeRenta, Rol, VoucherAbierto)
from src.domain.vehiculo import Vehiculo

HOY = date(2026, 11, 5)
T0 = datetime(2026, 11, 10, 9, 0)


def _m(x) -> str:
    return str(Dinero(Decimal(str(x))).monto)


def _insp(km=0, cuartos=4, esquema=True, fotos=1):
    return InspeccionDeVehiculo(esquema, tuple(f"f{i}.jpg" for i in range(fotos)), Kilometraje(km),
                                NivelDeCombustible(cuartos))


def _ctx(tarifa="450", fin=None, ini=None, dev=None, cap=40, litro="24.50", hora=None, periodo=None):
    periodo = periodo or PeriodoDeRenta(T0, T0 + timedelta(days=2))
    return ContextoDeCargo(periodo, Dinero(Decimal(tarifa)), ini or _insp(), dev or _insp(),
                           hora or periodo.fin_pactado, cap, Dinero(Decimal(litro)))


def ejecutar(tipo: str, e: dict) -> str:
    if tipo == "documentacion":
        doc = DocumentacionConductor("X", date.fromisoformat(e["nacimiento"]), date.fromisoformat(e["licencia"]),
                                     date.fromisoformat(e["identificacion"]))
        return "VALIDA" if documentacion_valida(HOY).is_satisfied_by(doc) else "INVALIDA"
    if tipo == "retencion":
        r = Reservacion("R", Categoria.ECONOMICO, Dinero(Decimal("450")), Dinero(Decimal(e["pago_inicial"])),
                        PeriodoDeRenta(T0, T0 + timedelta(days=2)))
        r.cancelar_por_documentacion_invalida()
        return str(r.retencion.monto)
    if tipo == "retraso":
        p = PeriodoDeRenta(T0, T0 + timedelta(days=2))
        c = CargoPorRetraso().calcular(_ctx(e["tarifa"], periodo=p, hora=p.fin_pactado + timedelta(minutes=e["minutos"])))
        return str(c.monto.monto) if c else "0.00"
    if tipo == "combustible":
        c = CargoPorCombustibleFaltante().calcular(_ctx(
            ini=_insp(cuartos=e["salida"]), dev=_insp(cuartos=e["devolucion"]), cap=e["capacidad"], litro=e["precio_litro"]))
        return str(c.monto.monto) if c else "0.00"
    if tipo == "kilometraje":
        p = PeriodoDeRenta(T0, T0 + timedelta(hours=e["horas_renta"]))
        try:
            c = CargoPorKilometrajeExcedente().calcular(_ctx(
                periodo=p, ini=_insp(km=e["km_salida"]), dev=_insp(km=e["km_devolucion"])))
        except DomainError:
            return "KM_INVALIDO"
        return str(c.monto.monto) if c else "0.00"
    if tipo == "compensacion":
        disp = DisponibilidadDeCategoria(e["hay_en_categoria"], e["hay_superior"], e["hay_inferior"])
        if not requiere_compensacion().is_satisfied_by(disp):
            return "NO_REQUIERE"
        o = CompensacionDeCategoria().determinar_oferta(
            Dinero(Decimal(e["tarifa_reservada"])), disp, Categoria.SUV, Categoria.COMPACTO,
            Dinero(Decimal(e["tarifa_inferior"])), e["rechaza_upgrade"])
        return "SIN_OFERTA" if o is None else f"{o.tipo.value}|{o.tarifa_diaria.monto}"
    if tipo == "extension":
        fin = T0 + timedelta(days=2)
        sol = SolicitudDeExtension(fin - timedelta(minutes=e["anticipacion_min"]), fin,
                                   fin + timedelta(hours=e["horas_extra"]), e["reservado"])
        if not extension_permitida().is_satisfied_by(sol):
            return "RECHAZADA"
        dias = PeriodoDeRenta(fin, sol.nuevo_fin).dias
        return f"PERMITIDA|{Dinero(Decimal(e['tarifa'])).por(dias).monto}"
    if tipo == "cancelacion":
        ok = cancelacion_autorizada().is_satisfied_by(SolicitudDeCancelacion(Rol(e["rol"]), e["pin_valido"]))
        return "AUTORIZADA" if ok else "RECHAZADA"
    if tipo == "inspeccion":
        ok = inspeccion_de_salida_valida().is_satisfied_by(_insp(esquema=e["esquema"], fotos=e["fotos"]))
        return "FIRMA_PERMITIDA" if ok else "FIRMA_BLOQUEADA"
    if tipo == "voucher":
        v = VoucherAbierto("1234", "AUT", e["titular_tarjeta"])
        return "ACEPTADA" if VoucherATitular(e["titular_licencia"]).is_satisfied_by(v) else "RECHAZADA"
    if tipo == "transicion_vehiculo":
        v = Vehiculo("V", "P", Categoria.ECONOMICO, 40, EstatusDeVehiculo(e["estatus"]))
        try:
            m = getattr(v, e["accion"])
            m("Motivo", Decimal("100")) if e["accion"] == "reportar_mantenimiento_mayor" else m()
        except ConflictoDeEstado:
            return "TRANSICION_INVALIDA"
        return v.estatus.value
    raise ValueError(f"tipo_prueba desconocido: {tipo}")


def cargar_casos(ruta=None):
    ruta = ruta or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "data", "casos_prueba_novarent.csv")
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ejecutar_todos(casos=None):
    resultados = []
    for c in casos or cargar_casos():
        obtenido = ejecutar(c["tipo_prueba"], json.loads(c["entrada_json"]))
        resultados.append({**c, "resultado_obtenido": obtenido,
                           "estado": "PASA" if obtenido == c["resultado_esperado"] else "FALLA"})
    return resultados
