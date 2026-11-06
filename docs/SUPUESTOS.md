# Supuestos pendientes de validar (S-1 … S-12) y cómo los resolvió el código
| ID | Supuesto / pendiente | Decisión en el código |
|---|---|---|
| S-1 | Monto y momento del pago inicial (base del 10 %) | `Reservacion.pago_inicial` es un dato de la reservación; la retención = 10 % de ese monto |
| S-2 | Capacidad del tanque por vehículo | `Vehiculo.capacidad_tanque_litros` (dato de flota; por defecto 50 L) |
| S-3 | Cálculo del cargo por daños | El monto lo captura el agente; el dominio solo permite cobrar daños **nuevos** (no marcados en la salida): `registrar_cargo_por_danos` |
| S-13 | PIN de Administración | El dominio recibe `pin_valido` ya verificado (`SolicitudDeCancelacion`); el PIN real no vive en el dominio |
| S-14 | Extensión: cobro por adelantado | Se registra como `CargoExtra` tipo `EXTENSION`; fracción de día = día completo; el retraso se mide contra el nuevo fin pactado |
| S-4 | Cómo sale un vehículo de Mantenimiento Mayor | Sin transición de salida (queda pendiente) |
| S-5 | Hasta cuándo se agrega un cargo retroactivo | Se agrega al último contrato del vehículo, sin límite de tiempo |
| S-6 | Quién pasa de "En revisión" a "Limpieza" | Endpoint `limpieza/iniciar` (cualquier rol; sin autenticación en este alcance) |
| S-7 | Qué verifica el Agente y qué el sistema en la documentación | El sistema valida edad y vigencias con las fechas capturadas por el Agente |
| S-8 | Firma de salida sin daños | Esquema completado sin marcas + ≥ 1 foto |
| S-9 | Monto del cargo por Mantenimiento Mayor | Lo captura Limpieza al reportarlo (`monto_mxn`) |
| S-10 | Liberación de autorización bancaria / reintentos | `PasarelaDeAutorizacionBancaria` simulada; no hay compensación bancaria |
| S-11 | Retraso: las 4 h cuentan desde la hora pactada; fracción de hora = hora completa; el 20 % por hora se aplica a las horas posteriores a la tolerancia | `CargoPorRetraso` (con pruebas en los límites 120, 121, 180, 181, 240, 241 min) |
| S-12 | Las categorías no se listan en el BRD | `Categoria`: Económico < Compacto < Sedán < SUV < Lujo con tarifas de ejemplo en `CatalogoEstatico` |
| H-5 | Cliente rechaza el downgrade | Reservación `CANCELADA` sin penalización |
| H-7 | El 20 % del downgrade ¿uno o dos descuentos? | Un solo 20 % sobre la tarifa de la categoría inferior |
| S-15 | Cómo sabe el sistema que otro cliente reservó el auto (extensión) | El Agente lo declara en la solicitud (`vehiculo_reservado_por_otro`); el sistema no cruza reservaciones futuras por vehículo (se reserva por categoría) |
| S-16 | Autenticación de roles | No hay login: el `rol` viaja en la solicitud y el PIN de Administración se compara con la variable `PIN_ADMINISTRACION` (sin ella, nadie cancela cargos). En producción se sustituiría por autenticación real |
| S-17 | Tasa de Utilización "diaria" | Foto del momento de la consulta (rentados ÷ flota total); no se guarda historial diario |
| S-18 | Semana del reporte de ingresos | Lunes a domingo; un contrato cuenta en la semana de su hora de devolución (incluye cargos retroactivos y de extensión); los cargos cancelados no suman |
