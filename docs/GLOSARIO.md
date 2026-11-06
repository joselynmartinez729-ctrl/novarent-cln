# Glosario de dominio (lenguaje ubicuo) — NovaRent
| # | Término | Nombre en código | Definición |
|---|---|---|---|
| 1 | Reservación | `Reservacion` | Registro que el cliente confirma; marca el inicio del proceso. Garantiza una categoría, no una unidad física |
| 2 | Agente de renta | `Rol.AGENTE` | Valida documentos, gestiona disponibilidad, registra el pago, entrega el vehículo |
| 3 | Categoría de vehículo | `Categoria` | Clasificación del auto reservado; define la jerarquía de compensación |
| 4 | Upgrade gratuito | `TipoDeOferta.UPGRADE` | Categoría superior sin costo extra cuando no hay unidades de la reservada |
| 5 | Downgrade con descuento | `TipoDeOferta.DOWNGRADE` | Categoría inferior con tarifa a la baja y 20 % de descuento adicional |
| 6 | Tiempo de gracia | `TOLERANCIA_MINUTOS` | 120 minutos tras la hora pactada sin cargo por retraso |
| 7 | Cargo por retraso | `CargoPorRetraso` | Desde el minuto 121, 20 % de la tarifa diaria por hora; > 4 h = día completo |
| 8 | Esquema digital de daños | `InspeccionDeVehiculo.esquema_completado` | Marcado de daños en tablet; sustituye el papel |
| 9 | Fotografía obligatoria | `InspeccionDeVehiculo.fotos` | Al menos una foto antes de la firma de salida |
| 10 | Nivel fraccional de combustible | `NivelDeCombustible` | 0 a 4 cuartos (vacío, 1/4, 1/2, 3/4, lleno) |
| 11 | Cargo por combustible faltante | `CargoPorCombustibleFaltante` | Litros faltantes × precio de mercado + $100 de servicio de recarga |
| 12 | Kilometraje incluido | `KM_INCLUIDOS_POR_DIA` | 250 km por día de renta |
| 13 | Kilometraje excedente | `CargoPorKilometrajeExcedente` | (km final − km inicial) − incluidos; $5 por km |
| 14 | Rol "Administración" | `Rol.ADMINISTRACION` | Único rol que cancela cargos extra |
| 15 | Extensión de renta | *(US09, fuera de los 5 CU)* | Prolongar el contrato; avisar ≥ 6 h antes; cobro por adelantado |
| 16 | Documentación inválida | `EstatusDeReservacion.DOCUMENTACION_INVALIDA` | Impide la entrega; retiene el 10 % del pago inicial |
| 17 | Estatus del vehículo | `EstatusDeVehiculo` | Disponible, Rentado, En revisión, Limpieza, Mantenimiento Mayor |
| 18 | "Terminado" | `Vehiculo.marcar_terminado` | Casilla de Limpieza; único camino a Disponible |
| 19 | Voucher abierto | `VoucherAbierto` | Últimos 4 dígitos + código de autorización + titular de la licencia |
| 20 | Restricción de edad | `ConductorMayorDeEdad` | Conductor ≥ 18 años con licencia vigente |
| 21 | Mantenimiento Mayor | `EstatusDeVehiculo.MANTENIMIENTO_MAYOR` | Vestiduras o desodorización extrema; cargo retroactivo |
| 22 | Tasa de Utilización | *(US14)* | Autos rentados / flota total, diaria |
| — | Contrato de renta *(nuevo U3)* | `ContratoDeRenta` | Acuerdo vigente que nace al firmar la salida; une reservación, vehículo, voucher y cargos |
| — | Cargo extra *(nuevo U3)* | `CargoExtra` | Monto adicional a la tarifa: retraso, combustible, km, daños o Mantenimiento Mayor |
| — | Inspección de vehículo *(nuevo U3)* | `InspeccionDeVehiculo` | Registro de esquema, fotos, km y combustible en la salida o la devolución |
| — | Disponible *(precisión U3)* | `hay_disponibilidad_en` | Un vehículo está Disponible por su estatus; una categoría tiene disponibilidad si al menos uno de sus vehículos lo está |
