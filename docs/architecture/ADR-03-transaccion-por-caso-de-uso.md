# ADR-03: Una transacción por caso de uso, eventos después del commit
- **Estado:** Aceptada *(en la U3 estaba "Propuesta"; se implementó y se probó el rollback)*
- **Contexto:** CU-01 cambia tres Aggregates y CU-04 cambia dos. N2 exige que un auto no se rente dos veces. El banco es externo y puede fallar.
- **Alternativas:** Una transacción por Aggregate con consistencia eventual (deja una ventana donde el auto parece libre aunque ya tenga contrato). Llamadas al banco dentro de la transacción (se descartó: mantiene bloqueos esperando la red).
- **Decisión:** `UnidadDeTrabajo` por método de Application Service; los eventos de dominio se publican **después** del commit.
- **Consecuencias:** (+) todo ocurre junto o nada (`test_error_de_dominio_hace_rollback`); eventos solo de hechos confirmados. (−) un handler que falla no revierte el caso de uso (se registra en el log); falta compensación bancaria (S-10).
- **Trazabilidad:** N2; CU-01, CU-04, CU-05.
