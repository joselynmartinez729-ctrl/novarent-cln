# BRD — NovaRent (renta de automóviles por día)

> Fuente: BRD de la Unidad 2 (08/09/2026), refinado con los hallazgos H-1 a H-8 de la Actividad U3.
> Equipo 7 — Angélica Reyna García (2144918), Nohemi Delgado Castillo (2145346), Joselyn María Quiroga Martínez (2144717).
> Curso: Componentes de Lógica de Negocio · Profesor: Miguel Ángel Gómez Marroquín.

## 1. Contexto
NovaRent renta automóviles por día. Sus ingresos provienen del alquiler, complementado con seguros, conductores extra y equipamiento especial. Garantiza al cliente una **categoría** al reservar, no una unidad física específica hasta la entrega en sucursal.

**Problemas actuales:** (1) reclamaciones por cobros de daños no reconocidos (mala documentación inicial, en papel); (2) disponibilidad en sistema desfasada respecto al patio; (3) cuellos de botella entre devolución, limpieza y liberación del auto.

**Oportunidad:** sistema centralizado que automatice el ciclo de vida de la renta, unifique la comunicación entre áreas y elimine la ambigüedad en los cobros.

## 2. Inicio y fin del proceso central
Inicia cuando el cliente confirma su reservación. Termina cuando el vehículo es devuelto, se cobran los cargos finales (si los hay) y Limpieza lo libera dejándolo **Disponible**.

## 3. Stakeholders / roles
| Rol | Responsabilidad |
|---|---|
| Cliente | Realiza la reserva |
| Agente de renta | Valida documentos, gestiona contratos y cobros, ofrece compensaciones |
| Personal de patio | Registra las condiciones del vehículo en entrega y devolución |
| Limpieza | Acondiciona el vehículo y lo libera (casilla "Terminado") |
| Administración | Monitorea, resuelve disputas, autoriza excepciones, reportes |

## 4. Alcance
**Dentro:** reservaciones por categoría · registro de entrada/salida (validación de cliente y depósito en garantía) · inspección digital con fotos (daños, gasolina, kilometraje) · cobro automático de recargos (gasolina, retrasos, km extra) · panel en vivo del estado de los autos.
**Fuera:** nómina · contabilidad general · reparaciones mecánicas de taller.

## 5. Necesidades del negocio
| ID | Necesidad |
|---|---|
| N1 | **Registro visual de daños:** fotos y marcado en un dibujo digital del auto al entregar y al recibir |
| N2 | **Control de disponibilidad en tiempo real:** un auto no se renta hasta que Limpieza lo marque "Disponible" |
| N3 | **Cobro automático de extras:** gasolina ($100 + litros faltantes), km extra ($5/km tras 250 km/día), retraso (20 % de la tarifa diaria por hora desde el minuto 121) |
| N4 | **Autos sin stock:** upgrade gratuito a la categoría superior; si el cliente no lo acepta o no hay superior, categoría inferior con tarifa a la baja y 20 % de descuento adicional *(corrección H-4: el BRD original solo mencionaba el upgrade)* |

## 6. Reglas de negocio (con ID para trazabilidad)
| ID | Regla | Necesidad / US |
|---|---|---|
| RN-01 | El conductor debe tener ≥ 18 años, licencia e identificación vigentes; si no, se impide la entrega | US10 |
| RN-02 | Documentación inválida → reservación cancelada con estatus "Documentación inválida" y retención del 10 % del pago inicial | US10 |
| RN-03 | Solo se entrega un vehículo "Disponible" | N2 |
| RN-04 | No se firma la salida sin esquema digital de daños y al menos una fotografía | US05, N1 |
| RN-05 | Tarjeta de crédito a nombre del titular de la licencia; se registran últimos 4 dígitos y código de autorización bancaria | US12 |
| RN-06 | Categoría no disponible → upgrade gratuito a la superior inmediata | US03a, N4 |
| RN-07 | Si rechaza el upgrade o no hay superior → categoría inferior con tarifa a la baja + 20 % de descuento adicional | US03b, N4 |
| RN-08 | Retraso: 120 min de gracia; desde el minuto 121, 20 % de la tarifa diaria por hora; más de 4 h → día completo | US04, N3 |
| RN-09 | Combustible: debe volver el mismo nivel fraccional; si falta, litros faltantes × precio de mercado + $100 MXN | US06, N3 |
| RN-10 | Kilometraje: 250 km incluidos por día; excedente (final − inicial − incluidos) × $5 MXN | US07, N3 |
| RN-11 | Solo el rol Administración (con PIN) cancela cargos extra | US08 |
| RN-12 | Extensión de renta: avisar ≥ 6 h antes de la devolución; si el auto no está reservado, cobro por adelantado del día extra | US09 |
| RN-13 | Ciclo del vehículo: En revisión → Limpieza → Disponible; solo la casilla "Terminado" de Limpieza lo deja Disponible | US11, N2 |
| RN-14 | Limpieza puede reportar Mantenimiento Mayor (vestiduras / desodorización extrema) con cargo retroactivo | US13 |
| RN-15 | La devolución se registra una sola vez por contrato | U3 (invariante) |
| RN-16 | Reportes: Tasa de Utilización (diario) e Ingresos por Cargos Adicionales (semanal) | US14, US15 |

## 7. Supuestos del BRD
- Patio y Limpieza cuentan con conectividad inalámbrica y dispositivos móviles.
- El sistema se conecta con el banco para cobros y retención de la garantía.

## 8. Criterios de éxito
- Reducción del 90 % en disputas por daños preexistentes y combustible (< 10 % de reclamaciones).
- Tiempo promedio en "En revisión/Limpieza" ≤ 45 minutos.
- 100 % de los vehículos en sucursal coinciden con su estatus en el panel de Administración.

## 9. Supuestos pendientes de validar con el stakeholder
Ver [`docs/SUPUESTOS.md`](SUPUESTOS.md) (S-1 a S-12).
