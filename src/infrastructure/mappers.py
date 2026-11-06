"""Conversión Aggregate <-> filas SQL (el dominio no conoce la base de datos)."""
from datetime import date
from decimal import Decimal

from src.domain.cargos import CargoExtra
from src.domain.contrato import ContratoDeRenta
from src.domain.reservacion import Reservacion
from src.domain.value_objects import (Categoria, Dinero, DocumentacionConductor, EstatusDeReservacion,
                                      EstatusDeVehiculo, InspeccionDeVehiculo, Kilometraje,
                                      NivelDeCombustible, PeriodoDeRenta, TipoDeCargo, VoucherAbierto)
from src.domain.vehiculo import Vehiculo


def doc_to(d): return None if d is None else {
    "titular": d.titular, "fecha_nacimiento": d.fecha_nacimiento.isoformat(),
    "licencia": d.licencia_vigente_hasta.isoformat(), "identificacion": d.identificacion_vigente_hasta.isoformat()}


def doc_from(j): return None if j is None else DocumentacionConductor(
    j["titular"], date.fromisoformat(j["fecha_nacimiento"]), date.fromisoformat(j["licencia"]),
    date.fromisoformat(j["identificacion"]))


def insp_to(i): return None if i is None else {
    "esquema": i.esquema_completado, "fotos": list(i.fotos), "km": i.kilometraje.km,
    "combustible": i.combustible.cuartos, "danos": list(i.danos)}


def insp_from(j): return None if j is None else InspeccionDeVehiculo(
    j["esquema"], tuple(j["fotos"]), Kilometraje(j["km"]), NivelDeCombustible(j["combustible"]), tuple(j["danos"]))


def voucher_to(v): return {"ultimos_4": v.ultimos_4, "codigo": v.codigo_autorizacion, "titular": v.titular}
def voucher_from(j): return VoucherAbierto(j["ultimos_4"], j["codigo"], j["titular"])


def cargos_to(cs): return [{"tipo": c.tipo.value, "monto": str(c.monto.monto), "descripcion": c.descripcion,
                            "cancelado": c.cancelado} for c in cs]


def cargos_from(js): return [CargoExtra(TipoDeCargo(j["tipo"]), Dinero(Decimal(j["monto"])), j["descripcion"],
                                        j["cancelado"]) for j in js]


def vehiculo_row(v): return dict(vehiculo_id=v.vehiculo_id, placas=v.placas, categoria=v.categoria.name,
                                 capacidad_tanque_litros=v.capacidad_tanque_litros, estatus=v.estatus.value)


def vehiculo_from(r): return Vehiculo(r["vehiculo_id"], r["placas"], Categoria[r["categoria"]],
                                      r["capacidad_tanque_litros"], EstatusDeVehiculo(r["estatus"]))


def reservacion_row(r): return dict(
    reservacion_id=r.reservacion_id, categoria=r.categoria.name, categoria_entrega=r.categoria_entrega.name,
    tarifa_diaria=r.tarifa_diaria.monto, pago_inicial=r.pago_inicial.monto, retencion=r.retencion.monto,
    inicio=r.periodo.inicio, fin_pactado=r.periodo.fin_pactado, estatus=r.estatus.value,
    documentacion_verificada=r.documentacion_verificada, documentacion=doc_to(r.documentacion))


def reservacion_from(r): return Reservacion(
    r["reservacion_id"], Categoria[r["categoria"]], Dinero(r["tarifa_diaria"]), Dinero(r["pago_inicial"]),
    PeriodoDeRenta(r["inicio"], r["fin_pactado"]), Categoria[r["categoria_entrega"]],
    EstatusDeReservacion(r["estatus"]), doc_from(r["documentacion"]), bool(r["documentacion_verificada"]),
    Dinero(r["retencion"]))


def contrato_row(c): return dict(
    contrato_id=c.contrato_id, reservacion_id=c.reservacion_id, vehiculo_id=c.vehiculo_id,
    tarifa_diaria=c.tarifa_diaria.monto, inicio=c.periodo.inicio, fin_pactado=c.periodo.fin_pactado,
    voucher=voucher_to(c.voucher), inspeccion_salida=insp_to(c.inspeccion_salida),
    inspeccion_devolucion=insp_to(c.inspeccion_devolucion), hora_devolucion=c.hora_devolucion,
    cargos=cargos_to(c.cargos))


def contrato_from(r): return ContratoDeRenta(
    r["contrato_id"], r["reservacion_id"], r["vehiculo_id"], PeriodoDeRenta(r["inicio"], r["fin_pactado"]),
    Dinero(r["tarifa_diaria"]), voucher_from(r["voucher"]), insp_from(r["inspeccion_salida"]),
    insp_from(r["inspeccion_devolucion"]), r["hora_devolucion"], cargos_from(r["cargos"]))
