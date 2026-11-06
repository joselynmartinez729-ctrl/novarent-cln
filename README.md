# NovaRent — Sistema de renta de autos por día
**PIA · Componentes de Lógica de Negocio (AD2026)** · Equipo 7: Angélica Reyna García (2144918) · Nohemi Delgado Castillo (2145346) · Joselyn María Quiroga Martínez (2144717)

| | |
|---|---|
| Repositorio |  https://github.com/joselynmartinez729-ctrl/novarent-cln |
| Sistema desplegado / Swagger UI | https://novarent-cln.onrender.com/docs#/ |

Solución de software que implementa las reglas del BRD de NovaRent: reservación por categoría, validación de documentos, entrega con inspección digital y depósito en garantía, devolución con **cargos automáticos** (retraso, combustible, kilometraje), compensación de categoría (upgrade / downgrade 20 %) y ciclo de vida del vehículo (En revisión → Limpieza → Disponible).
Componentes del curso: **DDD** (3 Aggregates, Value Objects, Domain Services, Domain Events) · **Specification** (AND/OR/NOT) · **State Machine** (Vehículo) · **Service Layer + Repository + Unit of Work + CQRS básico** · **API REST con OpenAPI**.

## Estructura
```
docs/            BRD.md · analisis_historias_de_usuario.md (Gherkin) · analisis_bpmn.md · GLOSARIO.md · SUPUESTOS.md
                 TRAZABILIDAD.md · architecture/ (ADRs, diagramas, SOLID, patrones) · api/openapi.json
src/domain/          entidades, Value Objects, agregados, specifications, state machine, eventos
src/application/     casos de uso (Service Layer), commands, DTOs, puertos
src/infrastructure/  repositorios SQL, Unit of Work, adaptadores simulados (banco, combustible, reloj), seed
src/api/             endpoints REST (FastAPI) y composición de dependencias
tests/               unit/ (dominio + servicios) · integration/ (API + base de datos)
data/                flota.csv y reservaciones.csv de demostración · referencia_zip_generico/ (CSV del docente)
.github/workflows/   CI (pruebas + cobertura ≥ 80 % + PostgreSQL + build Docker)
```

## Ejecución local (SQLite, sin Docker)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload                       # Swagger UI: http://localhost:8000/docs
```
Al arrancar se crea `novarent.db` y se cargan 15 vehículos y 6 reservaciones desde `data/`.

## Pruebas y cobertura
```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```
233 pruebas: unitarias de dominio y servicios, integración de API + SQL y **110 casos de NovaRent** (`data/casos_prueba_novarent.csv`). Cobertura actual ≈ 99 %.

Evidencia de los casos: `python scripts/ejecutar_casos.py` → `docs/evidencias/resultados_casos_novarent.csv`.

## Docker Compose (DB + App + Tests)
```bash
cp .env.example .env            # ajusta la contraseña; .env no se sube al repositorio
docker compose up --build       # app en http://localhost:8000/docs + PostgreSQL
docker compose --profile test run --rm tests     # pruebas con cobertura contra PostgreSQL (BD novarent_test)
```
La configuración (BD, precio por litro, etc.) se separa del código con variables de entorno (12-Factor): ver `.env.example`.

## Despliegue (Render / Railway)
1. Crear un servicio *Web Service* desde este repositorio (Docker) y una base PostgreSQL gestionada.
2. Variables: `DATABASE_URL` (la de la BD gestionada), `PRECIO_LITRO`, `PIN_ADMINISTRACION`. `PORT` lo define la plataforma.
3. Comprobar `GET /health` y abrir `/docs` (Swagger UI). Poner las URLs en la tabla de arriba.

## Demostración (guion rápido)
`bash scripts/demo.sh` (o Swagger UI) recorre: CU-02 documentación → CU-01 entrega (201) → CU-04 devolución tardía con cargos → CU-03 upgrade y downgrade.

| Caso de uso | Endpoint | Resultado |
|---|---|---|
| CU-02 Documentación inválida | `POST /reservaciones/{id}/validar-documentacion` | 200; si es inválida → `DOCUMENTACION_INVALIDA` y retención 10 % |
| CU-03 Categoría no disponible | `GET …/oferta-compensacion` · `POST …/compensacion` | UPGRADE / DOWNGRADE 20 % / CANCELADA |
| CU-01 Entregar vehículo | `POST /reservaciones/{id}/entrega` | **201** `contrato_id`; 422 sin foto o tarjeta ajena; 409 sin validar documentos |
| CU-04 Registrar devolución | `POST /contratos/{id}/devolucion` · `GET …/cargos` | 200; cargos de retraso, combustible y km; 409 si ya se devolvió |
| US08 Cancelar cargo (PIN) | `POST /contratos/{id}/cargos/{indice}/cancelacion` | 200; 422 si no es Administración con PIN válido |
| US09 Extender renta | `POST /contratos/{id}/extension` | 200 con cobro por adelantado; 422 si falta anticipación o el auto está reservado |
| Daños | `POST /contratos/{id}/cargos/danos` | 200; 422 si no hay daños nuevos |
| US14 / US15 Reportes | `GET /reportes/tasa-de-utilizacion` · `GET /reportes/ingresos-por-cargos?desde=AAAA-MM-DD` | tasa de utilización y tabla de ingresos por tipo de cargo |
| CU-05 Liberar vehículo | `POST /vehiculos/{id}/limpieza/iniciar` · `…/terminado` · `…/mantenimiento-mayor` · `GET /vehiculos` | 200; 409 si la transición es inválida |

Códigos: **200/201** éxito · **404** no encontrado · **409** conflicto de estado/transición · **422** regla de negocio o validación.
Datos de demo: `RES-001` (Económico, hay stock) · `RES-002` (Sedán → upgrade a SUV) · `RES-003` (Lujo → downgrade a SUV) · `RES-005` (para probar documentación inválida).

## Trazabilidad y alcance
- Matriz BRD/US → regla → componente → prueba: [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md)
- Decisiones: [`docs/architecture/`](docs/architecture/README.md) (ADR-01 a ADR-04) · Supuestos: [`docs/SUPUESTOS.md`](docs/SUPUESTOS.md)
- **Alcance:** las 17 historias están implementadas. US08, US09, US14 y US15 estaban fuera de los 5 casos de uso de la U3 y se agregaron después. Limitaciones y supuestos (sin login, PIN por variable de entorno, etc.): `docs/SUPUESTOS.md`.
- Diferencias con el paquete de datos genérico del docente: [`docs/DIFERENCIAS_CON_EL_ZIP_DEL_DOCENTE.md`](docs/DIFERENCIAS_CON_EL_ZIP_DEL_DOCENTE.md)

