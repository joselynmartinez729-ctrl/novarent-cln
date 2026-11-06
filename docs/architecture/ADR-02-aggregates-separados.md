# ADR-02: Reservación, Contrato de renta y Vehículo como Aggregates separados
- **Estado:** Aceptada
- **Contexto:** El BRD dice que la reservación garantiza una categoría y la unidad física se asigna hasta la entrega. El contrato nace en la entrega y el vehículo tiene su propio ciclo de vida.
- **Alternativas:** Un solo Aggregate de renta (simple, pero mezcla reglas de reserva y entrega y bloquea muchos datos). Tres Aggregates referenciados por id (límites claros, requiere coordinación).
- **Decisión:** Tres Aggregates (`Reservacion`, `ContratoDeRenta`, `Vehiculo`) relacionados solo por id.
- **Consecuencias:** (+) cada regla vive junto al concepto que la protege; un vehículo cambia de estatus sin cargar un contrato. (−) la Service Layer coordina los tres y necesita transacción (ADR-03).
- **Trazabilidad:** BRD (modelo operativo), N2; US05, US10–US12; CU-01, CU-02, CU-05.
