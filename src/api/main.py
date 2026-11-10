"""API REST de NovaRent. OpenAPI/Swagger UI en /docs.
Códigos: 200/201 éxito · 404 no encontrado · 409 conflicto de estado · 422 regla de negocio / validación."""
from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, Query
from pathlib import Path
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.application.commands import DecisionDelCliente, EntregarVehiculoCommand, RegistrarDevolucionCommand
from src.application.errors import NoEncontrado
from src.domain.value_objects import Categoria, ConflictoDeEstado, DomainError, Rol

from .container import Container, get_container
from .schemas import (CancelacionCargoIn, CargoPorDanosIn, DecisionIn, DevolucionIn, DocumentacionIn, EntregaIn,
                      ExtensionIn, MantenimientoMayorIn)

app = FastAPI(
    title="NovaRent API", version="1.0.0",
    description="Renta de autos por día: reservación, entrega, devolución con cargos automáticos y "
                "ciclo de vida del vehículo (DDD + Specification + State Machine).")

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse("/docs")


@app.exception_handler(NoEncontrado)
async def _404(_, e): return JSONResponse(status_code=404, content={"detail": str(e)})


@app.exception_handler(ConflictoDeEstado)
async def _409(_, e): return JSONResponse(status_code=409, content={"detail": str(e)})


@app.exception_handler(DomainError)
async def _422(_, e): return JSONResponse(status_code=422, content={"detail": str(e)})


def C() -> Container:
    return get_container()


@app.get("/health", tags=["Sistema"])
def health(): return {"status": "ok"}


# ---- Reservaciones ----
@app.get("/reservaciones/{reservacion_id}", tags=["Reservaciones"])
def obtener_reservacion(reservacion_id: str, c: Container = Depends(C)):
    return asdict(c.consultas.reservacion(reservacion_id))


@app.post("/reservaciones/{reservacion_id}/validar-documentacion", tags=["Reservaciones"],
          summary="CU-02: valida edad, licencia e identificación (US10)")
def validar_documentacion(reservacion_id: str, body: DocumentacionIn, c: Container = Depends(C)):
    return asdict(c.validacion.validar_documentacion_del_conductor(reservacion_id, body.to_domain()))


@app.get("/reservaciones/{reservacion_id}/oferta-compensacion", tags=["Reservaciones"],
         summary="Query CU-03: oferta de upgrade/downgrade (US03)")
def oferta(reservacion_id: str, c: Container = Depends(C)):
    o = c.compensacion.consultar_oferta(reservacion_id)
    return {"oferta": None if o is None else asdict(o)}


@app.post("/reservaciones/{reservacion_id}/compensacion", tags=["Reservaciones"],
          summary="CU-03: resuelve categoría no disponible (upgrade, downgrade 20 % o cancelación)")
def compensacion(reservacion_id: str, body: DecisionIn = DecisionIn(), c: Container = Depends(C)):
    return asdict(c.compensacion.resolver_categoria_no_disponible(
        reservacion_id, DecisionDelCliente(body.acepta_upgrade, body.acepta_inferior)))


@app.post("/reservaciones/{reservacion_id}/entrega", status_code=201, tags=["Contratos"],
          summary="CU-01: entrega el vehículo y crea el contrato (US05, US12)")
def entregar(reservacion_id: str, body: EntregaIn, c: Container = Depends(C)):
    contrato_id = c.entrega.entregar_vehiculo(EntregarVehiculoCommand(
        reservacion_id, body.ultimos_4, body.titular, body.inspeccion_salida.to_domain()))
    return {"contrato_id": contrato_id}


# ---- Contratos ----
@app.post("/contratos/{contrato_id}/devolucion", tags=["Contratos"],
          summary="CU-04: registra la devolución y calcula cargos (US04, US06, US07)")
def devolver(contrato_id: str, body: DevolucionIn, c: Container = Depends(C)):
    cid = c.devolucion.registrar_devolucion(RegistrarDevolucionCommand(
        contrato_id, body.inspeccion_devolucion.to_domain(), body.hora_devolucion))
    return {"contrato_id": cid}


@app.get("/contratos/{contrato_id}/cargos", tags=["Contratos"], summary="Query: resumen de cargos extra")
def cargos(contrato_id: str, c: Container = Depends(C)):
    return asdict(c.consultas.resumen_de_cargos(contrato_id))


@app.post("/contratos/{contrato_id}/extension", tags=["Contratos"],
          summary="US09: extiende la renta (≥ 6 h de anticipación, auto no reservado); cobra por adelantado")
def extender(contrato_id: str, body: ExtensionIn, c: Container = Depends(C)):
    return asdict(c.contratos.extender_renta(contrato_id, body.nuevo_fin, body.vehiculo_reservado_por_otro))


@app.post("/contratos/{contrato_id}/cargos/{indice}/cancelacion", tags=["Contratos"],
          summary="US08: cancela un cargo extra (solo Administración con PIN válido)")
def cancelar_cargo(contrato_id: str, indice: int, body: CancelacionCargoIn, c: Container = Depends(C)):
    return asdict(c.contratos.cancelar_cargo(contrato_id, indice, Rol(body.rol), body.pin, body.motivo))


@app.post("/contratos/{contrato_id}/cargos/danos", tags=["Contratos"],
          summary="Cobra daños nuevos detectados en la devolución (S-3: monto capturado por el agente)")
def cargo_por_danos(contrato_id: str, body: CargoPorDanosIn, c: Container = Depends(C)):
    return asdict(c.contratos.registrar_cargo_por_danos(contrato_id, body.monto_mxn, body.descripcion))


# ---- Reportes (Administración) ----
@app.get("/reportes/tasa-de-utilizacion", tags=["Reportes"],
         summary="US14: Tasa de Utilización = autos rentados ÷ flota total (foto actual)")
def tasa_de_utilizacion(c: Container = Depends(C)):
    return asdict(c.consultas.tasa_de_utilizacion())


@app.get("/reportes/ingresos-por-cargos", tags=["Reportes"],
         summary="US15: Ingresos por Cargos Adicionales de una semana (lunes a domingo)")
def ingresos_por_cargos(desde: Optional[date] = Query(None, description="Lunes de la semana; por defecto la semana en curso"),
                        c: Container = Depends(C)):
    return asdict(c.consultas.ingresos_por_cargos_adicionales(desde))


# ---- Vehículos ----
@app.get("/vehiculos", tags=["Vehículos"], summary="Query: panel en vivo de vehículos (N2)")
def panel(categoria: Optional[str] = Query(None, description="ECONOMICO, COMPACTO, SEDAN, SUV o LUJO"),
          c: Container = Depends(C)):
    try:
        cat = Categoria[categoria.upper()] if categoria else None
    except KeyError:
        raise DomainError(f"Categoría desconocida: {categoria}")
    return [asdict(v) for v in c.consultas.panel_de_vehiculos(cat)]


@app.post("/vehiculos/{vehiculo_id}/limpieza/iniciar", tags=["Vehículos"], summary="EN_REVISION → LIMPIEZA")
def iniciar_limpieza(vehiculo_id: str, c: Container = Depends(C)):
    return asdict(c.limpieza.iniciar_limpieza(vehiculo_id))


@app.post("/vehiculos/{vehiculo_id}/limpieza/terminado", tags=["Vehículos"],
          summary="CU-05: casilla 'Terminado' → DISPONIBLE (US11)")
def terminado(vehiculo_id: str, c: Container = Depends(C)):
    return asdict(c.limpieza.marcar_terminado(vehiculo_id))


@app.post("/vehiculos/{vehiculo_id}/mantenimiento-mayor", tags=["Vehículos"],
          summary="CU-05: reporta Mantenimiento Mayor y cargo retroactivo (US13)")
def mantenimiento_mayor(vehiculo_id: str, body: MantenimientoMayorIn, c: Container = Depends(C)):
    return asdict(c.limpieza.reportar_mantenimiento_mayor(vehiculo_id, body.motivo, body.monto_mxn))

# Interfaz web (HTML + JavaScript) servida por la misma API: /ui 
_WEB = Path(__file__).resolve().parents[2] / "web"
if _WEB.is_dir():
    app.mount("/ui", StaticFiles(directory=_WEB, html=True), name="ui")

    @app.get("/", include_in_schema=False)
    def _inicio(): return RedirectResponse("/ui/")
    