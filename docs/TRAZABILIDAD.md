# Matriz de trazabilidad: BRD/US → regla → componente → prueba
| BRD / US | Regla | Componente (código) | Prueba |
|---|---|---|---|
| US10, restricción de edad | RN-01 | `specifications.documentacion_valida` (`ConductorMayorDeEdad`, `LicenciaVigente`, `IdentificacionVigente`) | `test_specifications.py::test_documentacion_valida`, `::test_menor_de_edad`, `::test_exactamente_18_anios_es_valido`, `::test_licencia_o_identificacion_vencida` |
| US10 | RN-02 | `Reservacion.cancelar_por_documentacion_invalida` | `test_agregados.py::test_documentacion_invalida_cancela_y_retiene_10_por_ciento`; `test_api.py::test_documentacion_invalida_retiene_10` |
| N2 | RN-03 | `Vehiculo.entregar`, `VehiculoDisponible`, `ServicioDeEntrega` | `test_agregados.py::test_no_se_entrega_un_vehiculo_no_disponible`; `test_servicios.py::test_entrega_sin_vehiculo_disponible` |
| US05, N1 | RN-04 | `ContratoDeRenta.crear`, `inspeccion_de_salida_valida` | `test_agregados.py::test_no_se_firma_sin_foto_ni_esquema`; `test_api.py::test_errores_404_409_422` |
| US12 | RN-05 | `VoucherAbierto`, `VoucherATitular` | `test_agregados.py::test_tarjeta_debe_ser_del_titular_de_la_licencia`, `::test_voucher_requiere_4_digitos` |
| US03a, N4 | RN-06 | `CompensacionDeCategoria` (UPGRADE) | `test_agregados.py::test_upgrade_gratuito_mantiene_tarifa`; `test_api.py::test_compensacion_upgrade_y_downgrade` |
| US03b, N4 | RN-07 | `CompensacionDeCategoria` (DOWNGRADE 20 %) | `test_agregados.py::test_downgrade_con_20_por_ciento_si_rechaza_upgrade`; `test_servicios.py::test_compensacion_downgrade_y_rechazo_cancela` |
| US04, N3 | RN-08 | `CargoPorRetraso` | `test_cargos.py::test_retraso` (120/121/180/181/240/241 min) |
| US06, N3 | RN-09 | `CargoPorCombustibleFaltante` | `test_cargos.py::test_combustible_faltante`, `::test_combustible_igual_o_mayor_no_cobra` |
| US07, N3 | RN-10 | `CargoPorKilometrajeExcedente` | `test_cargos.py::test_kilometraje`, `::test_kilometraje_final_menor_al_inicial` |
| US08 | RN-11 | `ContratoDeRenta.cancelar_cargo`, `cancelacion_autorizada` (rol Administración AND PIN válido), `CargoExtra.cancelar` | `test_reglas_adicionales.py::test_autorizacion_and`, `::test_administracion_con_pin_cancela_y_total_baja`, `::test_cancelacion_no_autorizada`; `test_cargos.py::test_solo_administracion_cancela_cargos` |
| US09 | RN-12 | `ContratoDeRenta.extender`, `extension_permitida` (≥ 6 h AND NOT reservado AND nueva fecha posterior) | `test_reglas_adicionales.py::test_extension_requiere_6_horas_de_anticipacion`, `::test_extension_no_permitida_si_el_auto_esta_reservado`, `::test_extender_cobra_por_adelantado_y_actualiza_periodo`, `::test_extender_rechazada` |
| US05, N1, S-3 | Daños | `InspeccionDeVehiculo.danos_nuevos_respecto_a`, `ContratoDeRenta.registrar_cargo_por_danos`, `danos_cobrables`, evento `DanosDetectados` | `test_reglas_adicionales.py::test_danos_nuevos_respecto_a_la_salida`, `::test_cargo_por_danos_solo_con_danos_nuevos`, `::test_no_se_cobran_danos_preexistentes` |
| US11, N2 | RN-13 | `Vehiculo` (State Machine) | `test_agregados.py::test_ciclo_completo_del_vehiculo`, `::test_solo_limpieza_lleva_a_disponible`; `test_api.py::test_flujo_completo_201_y_cargos` |
| US13 | RN-14 | `Vehiculo.reportar_mantenimiento_mayor`, `ManejadorMantenimientoMayor` | `test_servicios.py::test_mantenimiento_mayor_agrega_cargo_retroactivo`; `test_api.py::test_mantenimiento_mayor_cargo_retroactivo` |
| U3 invariante | RN-15 | `ContratoDeRenta.registrar_devolucion` (`ContratoYaDevuelto`) | `test_agregados.py::test_devolucion_calcula_cargos_y_solo_una_vez`; `test_api.py::test_doble_devolucion_409` |
| ADR-03 | Transacción | `UnidadDeTrabajo` / `SqlUnitOfWork` | `test_servicios.py::test_error_de_dominio_hace_rollback` |
| US14 | RN-16 | `ConsultasDeNovaRent.tasa_de_utilizacion` · `GET /reportes/tasa-de-utilizacion` | `test_reportes_y_contratos.py::test_tasa_de_utilizacion`, `::test_tasa_redondea_a_dos_decimales`; `test_api.py::test_reporte_tasa_de_utilizacion` |
| US15 | RN-16 | `ConsultasDeNovaRent.ingresos_por_cargos_adicionales` · `GET /reportes/ingresos-por-cargos` | `test_reportes_y_contratos.py::test_ingresos_semanales_desglosados`, `::test_ingresos_excluyen_cargos_cancelados`; `test_api.py::test_reporte_ingresos_por_cargos` |
| Casos NovaRent (110) | RN-01, 02, 04–13 | `data/casos_prueba_novarent.csv` + `tests/casos_novarent.py` | `test_casos_csv.py` (una prueba por caso); evidencia en `docs/evidencias/resultados_casos_novarent.csv` |

| Caso de uso (U3) | Endpoint | Servicio |
|---|---|---|
| CU-01 Entregar vehículo | `POST /reservaciones/{id}/entrega` (201) | `ServicioDeEntrega.entregar_vehiculo` |
| CU-02 Documentación inválida | `POST /reservaciones/{id}/validar-documentacion` | `ServicioDeValidacionDeDocumentacion` |
| CU-03 Categoría no disponible | `GET …/oferta-compensacion`, `POST …/compensacion` | `ServicioDeCompensacionDeCategoria` |
| CU-04 Registrar devolución | `POST /contratos/{id}/devolucion`, `GET …/cargos` | `ServicioDeDevolucion` |
| US08, US09, daños | `POST /contratos/{id}/cargos/{indice}/cancelacion`, `…/extension`, `…/cargos/danos` | `ServicioDeContratos` |
| US14, US15 | `GET /reportes/tasa-de-utilizacion`, `GET /reportes/ingresos-por-cargos` | `ConsultasDeNovaRent` |
| CU-05 Liberar vehículo | `POST /vehiculos/{id}/limpieza/{iniciar,terminado}`, `…/mantenimiento-mayor`, `GET /vehiculos` | `ServicioDeLimpieza` |
