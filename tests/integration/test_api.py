"""Pruebas de integración: API REST + SQL (SQLite en memoria) + Service Layer + dominio."""
DOC_OK = {"titular": "Ana Pérez", "fecha_nacimiento": "1995-03-10",
          "licencia_vigente_hasta": "2029-01-01", "identificacion_vigente_hasta": "2030-01-01"}
INSP = {"esquema_completado": True, "fotos": ["f1.jpg"], "kilometraje": 1000, "combustible": "lleno"}


def _entregar(api, res="RES-001"):
    assert api.post(f"/reservaciones/{res}/validar-documentacion", json=DOC_OK).status_code == 200
    r = api.post(f"/reservaciones/{res}/entrega", json={"ultimos_4": "1234", "titular": "Ana Pérez",
                                                         "inspeccion_salida": INSP})
    return r


def test_health_y_swagger(api):
    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/docs").status_code == 200
    assert "/reservaciones/{reservacion_id}/entrega" in api.get("/openapi.json").json()["paths"]


def test_panel_de_vehiculos(api):
    assert len(api.get("/vehiculos").json()) == 15
    suv = api.get("/vehiculos", params={"categoria": "SUV"}).json()
    assert len(suv) == 3 and all(v["categoria"] == "SUV" for v in suv)


def test_flujo_completo_201_y_cargos(api):
    r = _entregar(api)
    assert r.status_code == 201
    cid = r.json()["contrato_id"]
    dev = {"hora_devolucion": "2026-11-12T13:00:00",
           "inspeccion_devolucion": {**INSP, "kilometraje": 1700, "combustible": "1/2"}}
    assert api.post(f"/contratos/{cid}/devolucion", json=dev).status_code == 200
    cargos = api.get(f"/contratos/{cid}/cargos").json()
    assert {c["tipo"] for c in cargos["cargos"]} == {"RETRASO", "COMBUSTIBLE", "KILOMETRAJE"}
    assert cargos["total_mxn"] == 1770.0
    # el vehículo quedó En revisión y recorre el ciclo hasta Disponible
    vid = next(v["vehiculo_id"] for v in api.get("/vehiculos").json() if v["estatus"] == "EN_REVISION"
               and v["categoria"] == "ECONOMICO")
    assert api.post(f"/vehiculos/{vid}/limpieza/iniciar").json()["estatus"] == "LIMPIEZA"
    assert api.post(f"/vehiculos/{vid}/limpieza/terminado").json()["estatus"] == "DISPONIBLE"


def test_documentacion_invalida_retiene_10(api):
    malo = {**DOC_OK, "fecha_nacimiento": "2015-01-01"}
    r = api.post("/reservaciones/RES-005/validar-documentacion", json=malo).json()
    assert r["estatus"] == "DOCUMENTACION_INVALIDA" and r["retencion_mxn"] == 90.0
    # ya no se puede entregar ni revalidar
    assert api.post("/reservaciones/RES-005/validar-documentacion", json=DOC_OK).status_code == 409


def test_errores_404_409_422(api):
    assert api.get("/reservaciones/NOPE").status_code == 404
    assert api.get("/contratos/NOPE/cargos").status_code == 404
    # 409: entregar sin validar documentación
    r = api.post("/reservaciones/RES-001/entrega", json={"ultimos_4": "1234", "titular": "Ana Pérez",
                                                          "inspeccion_salida": INSP})
    assert r.status_code == 409
    # 409: transición inválida de vehículo
    assert api.post("/vehiculos/VEH-ECO-01/limpieza/terminado").status_code == 409
    # 422: sin foto (regla de negocio) y formato inválido (tarjeta)
    api.post("/reservaciones/RES-001/validar-documentacion", json=DOC_OK)
    sin_foto = {**INSP, "fotos": []}
    r = api.post("/reservaciones/RES-001/entrega", json={"ultimos_4": "1234", "titular": "Ana Pérez",
                                                          "inspeccion_salida": sin_foto})
    assert r.status_code == 422 and "fotograf" in r.json()["detail"]
    assert api.post("/reservaciones/RES-001/entrega", json={"ultimos_4": "12", "titular": "A",
                                                             "inspeccion_salida": INSP}).status_code == 422
    # 422: tarjeta de otra persona
    r = api.post("/reservaciones/RES-001/entrega", json={"ultimos_4": "1234", "titular": "Otra Persona",
                                                          "inspeccion_salida": INSP})
    assert r.status_code == 422


def test_doble_devolucion_409(api):
    cid = _entregar(api).json()["contrato_id"]
    dev = {"hora_devolucion": "2026-11-12T09:00:00", "inspeccion_devolucion": {**INSP, "kilometraje": 1100}}
    assert api.post(f"/contratos/{cid}/devolucion", json=dev).status_code == 200
    assert api.post(f"/contratos/{cid}/devolucion", json=dev).status_code == 409


def test_compensacion_upgrade_y_downgrade(api):
    assert api.get("/reservaciones/RES-002/oferta-compensacion").json()["oferta"]["tipo"] == "UPGRADE"
    r = api.post("/reservaciones/RES-002/compensacion").json()
    assert r["resultado"] == "UPGRADE" and r["categoria_entrega"] == "SUV"
    r = api.post("/reservaciones/RES-003/compensacion", json={"acepta_inferior": True}).json()
    assert r["resultado"] == "DOWNGRADE" and r["tarifa_diaria_mxn"] == 760.0
    r = api.post("/reservaciones/RES-004/compensacion").json()  # compacto sí hay
    assert r["resultado"] == "SIN_COMPENSACION"
    assert api.get("/reservaciones/RES-004/oferta-compensacion").json() == {"oferta": None}


def test_mantenimiento_mayor_cargo_retroactivo(api):
    cid = _entregar(api).json()["contrato_id"]
    dev = {"hora_devolucion": "2026-11-12T09:00:00", "inspeccion_devolucion": {**INSP, "kilometraje": 1100}}
    api.post(f"/contratos/{cid}/devolucion", json=dev)
    vid = next(v["vehiculo_id"] for v in api.get("/vehiculos").json() if v["estatus"] == "EN_REVISION"
               and v["categoria"] == "ECONOMICO")
    api.post(f"/vehiculos/{vid}/limpieza/iniciar")
    r = api.post(f"/vehiculos/{vid}/mantenimiento-mayor", json={"motivo": "Humo de cigarro", "monto_mxn": "1500"})
    assert r.json()["estatus"] == "MANTENIMIENTO_MAYOR"
    cargos = api.get(f"/contratos/{cid}/cargos").json()
    assert cargos["total_mxn"] == 1500.0 and cargos["cargos"][0]["tipo"] == "MANTENIMIENTO_MAYOR"


# ---------------- Reportes, extensión, cancelación de cargos y daños ----------------
def _devolver(api, cid, km=1700, comb="1/2", hora="2026-11-12T13:00:00", danos=None):
    insp = {**INSP, "kilometraje": km, "combustible": comb, "danos": danos or []}
    return api.post(f"/contratos/{cid}/devolucion", json={"hora_devolucion": hora, "inspeccion_devolucion": insp})


def test_reporte_tasa_de_utilizacion(api):
    r = api.get("/reportes/tasa-de-utilizacion").json()
    # flota demo: 4 RENTADOS de 15 (1 económico, 2 sedán, 1 SUV)
    assert (r["rentados"], r["flota_total"], r["tasa_pct"]) == (4, 15, 26.67)
    assert len(r["por_categoria"]) == 5


def test_reporte_ingresos_por_cargos(api):
    cid = _entregar(api).json()["contrato_id"]
    _devolver(api, cid)
    r = api.get("/reportes/ingresos-por-cargos", params={"desde": "2026-11-09"}).json()
    por = {f["tipo"]: f["monto_mxn"] for f in r["filas"]}
    assert por["RETRASO"] == 180.0 and por["COMBUSTIBLE"] == 590.0 and por["KILOMETRAJE"] == 1000.0
    assert r["total_mxn"] == 1770.0 and r["contratos"] == 1
    assert api.get("/reportes/ingresos-por-cargos", params={"desde": "2026-11-16"}).json()["total_mxn"] == 0
    assert api.get("/reportes/ingresos-por-cargos", params={"desde": "no-es-fecha"}).status_code == 422


def test_cancelacion_de_cargos_con_pin(api):
    cid = _entregar(api).json()["contrato_id"]
    _devolver(api, cid)
    url = f"/contratos/{cid}/cargos/0/cancelacion"
    assert api.post(url, json={"rol": "AGENTE", "pin": "4321", "motivo": "cortesía"}).status_code == 422
    assert api.post(url, json={"rol": "ADMINISTRACION", "pin": "9999", "motivo": "cortesía"}).status_code == 422
    r = api.post(url, json={"rol": "ADMINISTRACION", "pin": "4321", "motivo": "cortesía"})
    assert r.status_code == 200 and r.json()["cargos"][0]["cancelado"] is True
    assert api.post(url, json={"rol": "ADMINISTRACION", "pin": "4321", "motivo": "otra vez"}).status_code == 422
    assert api.post(f"/contratos/{cid}/cargos/99/cancelacion",
                    json={"rol": "ADMINISTRACION", "pin": "4321", "motivo": "x x"}).status_code == 422
    assert api.post("/contratos/NOPE/cargos/0/cancelacion",
                    json={"rol": "ADMINISTRACION", "pin": "4321", "motivo": "x x"}).status_code == 404


def test_extension_de_renta(api):
    from datetime import datetime
    from src.api.container import get_container
    from src.infrastructure.memoria import RelojFijo
    cid = _entregar(api).json()["contrato_id"]
    get_container().contratos.reloj = RelojFijo(datetime(2026, 11, 5, 10))   # reloj determinista
    body = {"nuevo_fin": "2026-11-13T09:00:00"}
    r = api.post(f"/contratos/{cid}/extension", json=body)
    assert r.status_code == 200 and r.json()["monto_mxn"] == 450.0
    # auto reservado por otro cliente → 422
    assert api.post(f"/contratos/{cid}/extension",
                    json={"nuevo_fin": "2026-11-14T09:00:00", "vehiculo_reservado_por_otro": True}).status_code == 422
    # sin anticipación (2 h antes del nuevo fin pactado) → 422
    get_container().contratos.reloj = RelojFijo(datetime(2026, 11, 13, 7))
    assert api.post(f"/contratos/{cid}/extension", json={"nuevo_fin": "2026-11-14T09:00:00"}).status_code == 422
    assert api.post("/contratos/NOPE/extension", json=body).status_code == 404


def test_cargo_por_danos_via_api(api):
    cid = _entregar(api).json()["contrato_id"]
    _devolver(api, cid, km=1100, comb="lleno", hora="2026-11-12T09:00:00", danos=["abolladura cofre"])
    r = api.post(f"/contratos/{cid}/cargos/danos", json={"monto_mxn": "800", "descripcion": "Abolladura"})
    assert r.status_code == 200 and r.json()["total_mxn"] == 800.0
    cid2 = api.post("/reservaciones/RES-004/validar-documentacion", json=DOC_OK) and \
        api.post("/reservaciones/RES-004/entrega", json={"ultimos_4": "1234", "titular": "Ana Pérez",
                                                         "inspeccion_salida": INSP}).json()["contrato_id"]
    _devolver(api, cid2, km=1100, comb="lleno", hora="2026-11-12T09:00:00")
    assert api.post(f"/contratos/{cid2}/cargos/danos", json={"monto_mxn": "500"}).status_code == 422
