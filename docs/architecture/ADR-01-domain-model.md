# ADR-01: Domain Model como patrón de lógica de negocio
- **Estado:** Aceptada
- **Contexto:** El sistema controla el ciclo de vida del vehículo (N2), calcula tres cargos con umbrales (N3) y decide categorías alternativas (N4). Las reglas interactúan entre varios conceptos y deben protegerse con invariantes.
- **Alternativas:** *Transaction Script* — rápido, pero duplicaría validaciones de estatus y fórmulas de cargo. *Table Module* — organiza por tabla, pero las reglas cruzan tablas (contrato, inspección, vehículo). *Domain Model* — concentra cada regla en el concepto que la protege, a mayor costo de diseño.
- **Decisión:** Domain Model para los casos de uso que cambian estado; consultas de lectura directas con DTOs.
- **Consecuencias:** (+) invariantes protegidos y reglas probables sin base de datos (99 % de cobertura, dominio sin dependencias externas). (−) más clases, mapeo a persistencia, curva de aprendizaje; riesgo de sobreingeniería en operaciones simples como CU-02.
- **Trazabilidad:** N2, N3, N4; US03–US07, US11; CU-01 a CU-05.
