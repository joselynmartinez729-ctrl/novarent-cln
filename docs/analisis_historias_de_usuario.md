# Historias de usuario y criterios de aceptación (Gherkin)
> Refinadas desde la Unidad 2. Correcciones aplicadas: **H-1** (ID duplicado US03 → US03a/US03b; no existe US02), **H-2** (Gherkin completo en US13 y US14), **H-3** (nuevas US16 y US17 para devolución y revisión).
> Estado: ✅ implementada y probada (dominio + aplicación + API) · 🔶 parcial · ⏳ no implementada. Las historias US08, US09, US14 y US15 estaban fuera de los 5 casos de uso de la U3; se implementaron después.

| ID | Historia | CU | Estado | Endpoint / componente |
|---|---|---|---|---|
| US01 | Confirmar la reservación | — | ✅ (precondición: reservación `CONFIRMADA`) | `Reservacion` |
| US03a | Upgrade gratuito | CU-03 | ✅ | `POST /reservaciones/{id}/compensacion` |
| US03b | Downgrade con 20 % | CU-03 | ✅ | idem |
| US04 | Cobro por retraso | CU-04 | ✅ | `POST /contratos/{id}/devolucion` |
| US05 | Esquema de daños + foto obligatoria | CU-01 | ✅ | `POST /reservaciones/{id}/entrega` |
| US06 | Cobro de combustible faltante | CU-04 | ✅ | devolución |
| US07 | Cobro de kilometraje excedente | CU-04 | ✅ | devolución |
| US08 | PIN de Administración para cancelar cargos | — | ✅ | `POST /contratos/{id}/cargos/{indice}/cancelacion` |
| US09 | Extensión de renta | — | ✅ | `POST /contratos/{id}/extension` |
| US10 | Documentación inválida | CU-02 | ✅ | `POST /reservaciones/{id}/validar-documentacion` |
| US11 | Casilla "Terminado" | CU-05 | ✅ | `POST /vehiculos/{id}/limpieza/terminado` |
| US12 | Tarjeta del titular y voucher | CU-01 | ✅ | entrega |
| US13 | Mantenimiento Mayor con cargo retroactivo | CU-05 | ✅ | `POST /vehiculos/{id}/mantenimiento-mayor` |
| US14 | Reporte diario Tasa de Utilización | — | ✅ | `GET /reportes/tasa-de-utilizacion` |
| US15 | Reporte semanal Ingresos por Cargos Adicionales | — | ✅ | `GET /reportes/ingresos-por-cargos` |
| US16 | Registrar la devolución y pasar a "En revisión" *(nueva, H-3)* | CU-04 | ✅ | devolución |
| US17 | Iniciar limpieza *(nueva, H-3)* | CU-05 | ✅ | `POST /vehiculos/{id}/limpieza/iniciar` |

---
### US01 — Confirmar la reservación
Como **Agente de renta**, quiero confirmar la reservación en el sistema, para dar inicio oficial al proceso de renta.
```gherkin
Escenario: Reservación confirmada inicia el proceso
  Dado que el cliente cuenta con una reservación previa
  Cuando el Agente de renta confirma dicha reservación en el sistema
  Entonces la reservación queda en estatus "CONFIRMADA" y el proceso inicia de manera oficial
```
### US03a — Upgrade gratuito
Como **Agente de renta**, quiero ofrecer un upgrade gratuito a la categoría superior inmediata, para retener la satisfacción del cliente cuando su categoría no tiene vehículos.
```gherkin
Escenario: Existe disponibilidad en la categoría superior
  Dado que un cliente llega y no hay autos de su categoría reservada disponibles
  Cuando existe disponibilidad en la categoría superior inmediata
  Entonces el sistema otorga el upgrade sin aumentar la tarifa de la renta
```
### US03b — Downgrade con descuento
Como **Agente de renta**, quiero ofrecer una categoría inferior con tarifa a la baja y 20 % de descuento adicional, para concretar la renta si no hay categorías superiores.
```gherkin
Escenario: El cliente acepta la categoría inferior
  Dado que no hay vehículos de la categoría reservada ni superiores (o el cliente rechazó el upgrade)
  Cuando el cliente acepta la categoría inferior
  Entonces el sistema calcula la tarifa de la categoría inferior y aplica un 20 % de descuento adicional

Escenario: El cliente rechaza todas las opciones
  Dado que no hay vehículos de la categoría reservada
  Cuando el cliente no acepta la categoría inferior
  Entonces la reservación se cancela sin penalización (supuesto H-5)
```
### US04 — Cobro por retraso
Como **Sistema**, quiero cobrar el 20 % de la tarifa diaria por cada hora de retraso desde el minuto 121, para penalizar las devoluciones tardías.
```gherkin
Escenario: Retraso dentro de la tolerancia
  Dado que el cliente tiene 120 minutos de gracia
  Cuando devuelve el vehículo con 120 minutos de retraso o menos
  Entonces no se genera cargo por retraso

Escenario: Retraso mayor a la tolerancia
  Dado que el retraso supera los 120 minutos
  Cuando el sistema calcula los cargos
  Entonces cobra el 20 % de la tarifa diaria por cada hora posterior a la tolerancia (fracción = hora completa)

Escenario: Retraso mayor a 4 horas
  Dado que el retraso supera las 4 horas desde la hora pactada
  Cuando el sistema calcula los cargos
  Entonces cobra el día completo
```
### US05 — Esquema digital de daños y foto obligatoria
Como **Personal de patio**, quiero marcar daños en un esquema digital y adjuntar al menos una fotografía, para documentar el estado del auto antes de que el cliente firme.
```gherkin
Escenario: Firma de salida bloqueada
  Dado que se está realizando la entrega del vehículo
  Cuando el esquema de daños no está completado o no hay al menos una fotografía
  Entonces el sistema bloquea la firma de salida (HTTP 422)

Escenario: Firma de salida permitida
  Dado que el esquema está completado y hay al menos una fotografía
  Cuando se firma la salida
  Entonces se crea el contrato de renta y el vehículo pasa a "RENTADO"
```
### US06 — Combustible faltante
Como **Sistema**, quiero cobrar el precio por litro del mercado más $100 MXN, para recuperar costos cuando hay combustible faltante.
```gherkin
Escenario: El auto regresa con menor nivel de combustible
  Dado que el vehículo debe regresar con el mismo nivel fraccional con el que se entregó
  Cuando regresa con un nivel menor
  Entonces el sistema suma (litros faltantes × precio por litro del mercado) + $100 MXN de "servicio de recarga"

Escenario: El auto regresa con el mismo nivel o mayor
  Cuando el nivel de regreso es igual o mayor al de salida
  Entonces no se genera cargo por combustible
```
### US07 — Kilometraje excedente
Como **Sistema**, quiero calcular el excedente restando el kilometraje inicial del final, para cobrar $5 MXN por cada km sobre el límite.
```gherkin
Escenario: Recorrido sobre el límite
  Dado que la renta incluye 250 km por día
  Cuando (km final − km inicial) supera 250 × días de renta
  Entonces el sistema multiplica el excedente por $5 MXN y lo agrega a los cargos

Escenario: Kilometraje inválido
  Cuando el kilometraje final es menor que el inicial
  Entonces el sistema rechaza la devolución (HTTP 422)
```
### US08 — PIN de Administración
Como **Administración**, quiero usar un PIN de autorización, para ser el único rol capaz de cancelar cargos extra.
```gherkin
Escenario: Un Agente intenta cancelar un cargo
  Dado que un Agente de renta tiene restringido cancelar cargos por sí solo
  Cuando solicita la cancelación de un cargo por daño o retraso
  Entonces el sistema rechaza la operación

Escenario: Administración cancela un cargo
  Cuando Administración presenta un PIN válido
  Entonces el cargo queda cancelado y no suma al total
```
### US09 — Extensión de renta
```gherkin
Escenario: Extensión con anticipación y auto no apartado
  Dado que el cliente solicita extender al menos 6 horas antes de su hora de devolución
  Cuando el auto no está reservado por alguien más
  Entonces el sistema permite el cobro por adelantado del día extra y actualiza el contrato
```
### US10 — Documentación inválida
Como **Agente de renta**, quiero marcar la reserva como "Documentación inválida", para impedir que el cliente tome el auto si su identidad o licencia no son válidas.
```gherkin
Escenario: Conductor no cumple los requisitos
  Dado que el conductor no es mayor de 18 años, o su licencia o identificación no están vigentes
  Cuando el agente valida la documentación en mostrador
  Entonces el sistema cancela la reserva con estatus "DOCUMENTACION_INVALIDA" y retiene el 10 % del pago inicial

Escenario: Documentación válida
  Cuando la documentación cumple los requisitos
  Entonces la reservación queda con documentación verificada y puede entregarse
```
### US11 — Casilla "Terminado"
Como **Personal de limpieza**, quiero marcar "Terminado", para que el vehículo aparezca de inmediato como "Disponible".
```gherkin
Escenario: Limpieza concluida
  Dado que el vehículo está en estatus "LIMPIEZA"
  Cuando Limpieza marca la casilla "Terminado"
  Entonces el estatus cambia en tiempo real a "DISPONIBLE" y se emite VehiculoLiberado

Escenario: Intento de liberar sin limpieza
  Dado que el vehículo no está en "LIMPIEZA"
  Cuando alguien intenta marcarlo "Terminado"
  Entonces el sistema responde HTTP 409 (transición inválida)
```
### US12 — Tarjeta del titular y voucher
Como **Agente de renta**, quiero validar y registrar una tarjeta a nombre del titular de la licencia, para retener el voucher del depósito en garantía.
```gherkin
Escenario: Tarjeta del titular
  Dado que se solicita el método de pago obligatorio
  Cuando la tarjeta coincide con el titular de la licencia
  Entonces el sistema almacena los últimos 4 dígitos y el código de autorización bancaria

Escenario: Tarjeta de otra persona
  Cuando el titular de la tarjeta no coincide con el de la licencia
  Entonces el sistema rechaza la entrega (HTTP 422)
```
### US13 — Mantenimiento Mayor (Gherkin completado, H-2)
Como **Personal de limpieza**, quiero reportar que el vehículo requiere desodorización extrema o lavado de vestiduras, para aplicar un cargo retroactivo al cliente.
```gherkin
Escenario: Limpieza reporta Mantenimiento Mayor
  Dado que el vehículo está en estatus "LIMPIEZA"
  Cuando Limpieza reporta lavado de vestiduras o desodorización extrema con su monto
  Entonces el vehículo pasa a "MANTENIMIENTO_MAYOR"
  Y se agrega un cargo retroactivo al último contrato del vehículo
```
### US14 — Tasa de Utilización (Gherkin completado, H-2)
Como **Administración**, quiero visualizar diariamente la "Tasa de Utilización", para medir la eficiencia de la flota.
```gherkin
Escenario: Reporte diario
  Dado que ha concluido el día operativo
  Cuando Administración solicita el reporte
  Entonces el sistema muestra autos rentados ÷ flota total, como porcentaje
```
### US15 — Ingresos por Cargos Adicionales
```gherkin
Escenario: Reporte semanal
  Dado que ha concluido la semana operativa
  Cuando Administración solicita el reporte
  Entonces el sistema genera una tabla desglosada por combustible, daños y retraso
```
### US16 — Registrar la devolución (nueva, H-3)
Como **Personal de patio**, quiero registrar km, combustible y daños de la devolución, para calcular los cargos y pasar el vehículo a "En revisión".
```gherkin
Escenario: Devolución registrada
  Dado un contrato vigente con un vehículo "RENTADO"
  Cuando Patio registra la inspección de devolución y la hora
  Entonces el sistema calcula los cargos (retraso, combustible, km), el vehículo pasa a "EN_REVISION" y se emiten VehiculoDevuelto y CargosExtraCalculados

Escenario: Devolución repetida
  Dado un contrato cuya devolución ya fue registrada
  Cuando se intenta registrar de nuevo
  Entonces el sistema responde HTTP 409 (ContratoYaDevuelto)
```
### US17 — Iniciar limpieza (nueva, H-3)
```gherkin
Escenario: Del patio a limpieza
  Dado que el vehículo está "EN_REVISION"
  Cuando se inicia la limpieza
  Entonces el estatus cambia a "LIMPIEZA"
```
