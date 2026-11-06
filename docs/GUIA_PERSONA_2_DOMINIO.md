# Guía — Persona 2: Dominio y lógica de negocio
Carpeta de trabajo: `src/domain/` y `tests/unit/`. Regla de oro: **el dominio no importa SQL, FastAPI ni nada de `application/`**.

## Tu lista → dónde está
| Tarea del PIA | Archivo | Qué mirar |
|---|---|---|
| A. Entidades y agregados (U3) | `reservacion.py`, `contrato.py`, `vehiculo.py` | 3 Aggregate Roots; se relacionan **solo por id** |
| A. Value Objects | `value_objects.py` | `Dinero`, `Categoria`, `NivelDeCombustible`, `Kilometraje`, `PeriodoDeRenta`, `DocumentacionConductor`, `VoucherAbierto`, `InspeccionDeVehiculo` (inmutables, validan en el constructor) |
| A. Invariantes | métodos de los agregados | `ContratoDeRenta.crear` (foto y titular), `registrar_devolucion` (una sola vez) |
| A. Domain Events | `events.py` | 10 eventos; el agregado los acumula (`_eventos`) y la Unit of Work los publica tras el commit |
| A. Vehículo ≠ Contrato | `vehiculo.py` vs `contrato.py` | Vehículo = estatus; Contrato = dinero, inspecciones y cargos |
| B. Specification + AND/OR/NOT | `specifications.py` | `&`, `\|`, `~` sobre cualquier Specification |
| B. State Machine | `vehiculo.py` (`TRANSICIONES`) | tabla `(acción, estatus) → nuevo estatus`; lo demás lanza `TransicionInvalida` |
| B. Domain Model | todo `domain/` | ADR-01 |
| C. Upgrade / downgrade | `compensacion.py` | `CompensacionDeCategoria.determinar_oferta` |
| C. Retraso, combustible, km | `cargos.py` | 3 `PoliticaDeCargo` (Strategy) + `CalculadoraDeCargosExtra` |
| C. Documentación | `specifications.py::documentacion_valida`, `Reservacion.validar_documentacion` | |
| C. Cancelación de cargos | `contrato.py::cancelar_cargo` + `cancelacion_autorizada` | rol Administración AND PIN válido |
| C. Extensiones | `contrato.py::extender` + `extension_permitida` | ≥ 6 h AND NOT reservado AND fecha posterior |
| C. Inspecciones y daños | `value_objects.py::InspeccionDeVehiculo`, `contrato.py::registrar_cargo_por_danos` | solo daños **nuevos** |
| D. Pruebas | `tests/unit/test_{cargos,specifications,agregados,reglas_adicionales}.py` y `test_casos_csv.py` | valores límite; matriz completa de transiciones; 110 casos del CSV `data/casos_prueba_novarent.csv` |

## Pasos (≈ 2 h, para dominar tu parte y poder defenderla)
1. **Correr todo (10 min):** `pip install -r requirements.txt && pytest tests/unit -v`. Debe verse todo en verde.
2. **Leer en este orden (40 min):** `value_objects.py` → `specifications.py` → `vehiculo.py` → `cargos.py` → `compensacion.py` → `reservacion.py` → `contrato.py` → `events.py`. En cada archivo ubica la regla RN-xx del BRD (`docs/BRD.md`).
3. **Romper algo a propósito (15 min):** en `cargos.py` cambia `TOLERANCIA_MINUTOS` a 100 y corre `pytest tests/unit/test_cargos.py`. Verás qué prueba falla; así entiendes qué protege cada una. Revierte el cambio.
4. **Ajustar a SU BRD (30 min):** revisa `docs/SUPUESTOS.md`. Los supuestos S-2 (litros del tanque), S-12 (categorías y tarifas) y S-11 (interpretación del retraso) son decisiones nuestras; confírmenlas con el equipo/docente y cambien las constantes si hace falta (las pruebas te dicen qué se afecta).
5. **Matriz de trazabilidad (15 min):** `docs/TRAZABILIDAD.md` ya liga regla → código → prueba; verifica que los nombres de prueba existan y agrega los tuyos.
6. **Preparar la defensa (20 min):** ver abajo.

## Ejemplo para la defensa
> "Un cliente devuelve 4 h tarde un auto de $450/día. `CargoPorRetraso` calcula 240 min > 120 de gracia, no pasa de 4 h, así que cobra ceil((240−120)/60)=2 horas × 20 % × 450 = **$180**. Si fueran 241 min, cobra el día completo ($450). Está probado en `test_cargos.py::test_retraso`."

Preguntas típicas: *¿por qué Specification y no `if`s?* (se combinan y reutilizan: `~HayEnCategoria & (HaySuperior | HayInferior)`); *¿por qué la State Machine es una tabla?* (agregar un estatus no toca la lógica); *¿por qué Strategy en los cargos?* (OCP: un cargo nuevo = una clase nueva).
