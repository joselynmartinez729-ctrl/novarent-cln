# Diferencias entre el paquete de datos del docente (`07_NovaRent.zip`) y nuestro modelo
El `LEEME.txt` del paquete aclara que sus reglas y datos (actores, "equipos", `SOLICITADA → APROBADA → ENTREGADA → DEVUELTA`, `puede_procesarse`, `beneficio_referencia`) son un **modelo de pruebas propuesto** y que el PIA oficial exige derivar la implementación del BRD, las historias, el BPMN y el diseño DDD/UML del equipo; si difieren, se documentan las diferencias y se adaptan fixtures y oráculos.

| Paquete del docente (genérico) | NovaRent del equipo (renta de **autos**) |
|---|---|
| Operación con estados SOLICITADA/APROBADA/ENTREGADA/DEVUELTA/CANCELADA | `Reservacion` → `ContratoDeRenta` + `Vehiculo` con su propia State Machine (Disponible, Rentado, En revisión, Limpieza, Mantenimiento Mayor) |
| Actor "arrendatario" preferente/activo | Conductor con documentación (edad, licencia, identificación) |
| Recurso "equipo" con precio y stock | `Vehiculo` por categoría con tarifa diaria y tanque |
| Reglas `puede_procesarse` / `beneficio_referencia` | RN-01 … RN-16 del BRD |
| Total = Σ precio × cantidad | Cargos extra: retraso, combustible, kilometraje |

**Qué se adaptó:** se conservaron los CSV originales en `data/referencia_zip_generico/` y se crearon fixtures propios (`data/flota.csv`, `data/reservaciones.csv`) con 15 vehículos y 6 reservaciones que cubren upgrade, downgrade, documentación inválida y flujo normal. Los oráculos de prueba son los valores de las reglas del BRD (por ejemplo, 240 min de retraso en una tarifa de $450 = $180).
**Qué se conservó del enfoque del docente:** Specifications combinadas con AND/OR/NOT, máquina de estados, Domain Events, `Decimal` para importes, validación de transiciones inválidas y respuestas HTTP 200/201/404/409/422.

## Casos de prueba adaptados
`casos_prueba.csv` y `transiciones_prueba.csv` del paquete (120 + 20 filas) están escritos para el modelo genérico (`validar_operacion`, `evaluar_beneficio`, `completar`, `saltar_estado`…). Su equivalente en NovaRent es **`data/casos_prueba_novarent.csv`: 110 casos** con oráculo escrito a mano desde el BRD:

| Tipo | Casos | Regla | Equivalente en el paquete del docente |
|---|---|---|---|
| documentacion / retencion | 14 | RN-01, RN-02 | `validar_operacion` |
| compensacion | 9 | RN-06, RN-07 | `evaluar_beneficio` (reglas combinadas AND/OR/NOT) |
| retraso / combustible / kilometraje | 37 | RN-08, RN-09, RN-10 | cálculo de importes con `Decimal` |
| extension / cancelacion / inspeccion / voucher | 25 | RN-04, RN-05, RN-11, RN-12 | precondiciones |
| transicion_vehiculo | 25 | RN-13 | `transiciones_prueba.csv` (matriz completa 5 estatus × 5 acciones: 5 válidas, 20 inválidas) |

Ejecución: `python scripts/ejecutar_casos.py` → `docs/evidencias/resultados_casos_novarent.csv` (columnas `resultado_esperado`, `resultado_obtenido`, `estado`). Además `pytest` ejecuta cada fila como una prueba.
