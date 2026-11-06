# ADR-04: Python, FastAPI, SQLAlchemy Core y PostgreSQL
- **Estado:** Aceptada
- **Contexto:** El PIA exige API REST documentada (OpenAPI), persistencia, Docker Compose (DB + App + Tests) y despliegue reproducible.
- **Alternativas:** Java/Spring (más ceremonia para el tiempo disponible); Node/Express (OpenAPI manual); ORM completo (acopla el dominio a la persistencia).
- **Decisión:** FastAPI (OpenAPI/Swagger automáticos), SQLAlchemy Core con mappers explícitos (el dominio no conoce la BD), PostgreSQL en Docker y SQLite en pruebas, configuración por variables de entorno (12-Factor).
- **Consecuencias:** (+) Swagger en `/docs` sin trabajo extra; pruebas rápidas con SQLite en memoria. (−) mappers manuales; los tipos JSON se usan para Value Objects embebidos.
- **Trazabilidad:** Requisitos de PRODUCCIÓN y CALIDAD del PIA.
