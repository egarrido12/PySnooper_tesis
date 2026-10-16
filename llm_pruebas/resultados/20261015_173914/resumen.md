# Resumen de pruebas con LLM (prompt general)

- Python: `3.9.6`
- SDK anthropic: `0.125.0`
- Modelo solicitado: `claude-opus-5-5` (effort `high`)
- Prompt: `prompt_v1.md`
- Corridas por módulo: 1
- Fecha: 2026-10-15 17:40
- Costo total estimado: US$ 0.14

## Línea base

83 passed, 0 failed, 2 skipped, 0 errors

## Corridas

| Corrida | Modelo | +/− líneas | Tests (passed/failed/errors) | Veredicto | Tipo de fallo | Tiempo (s) | Costo (US$) |
|---|---|---|---|---|---|---|---|
| variables_run1 | claude-opus-5-5 | +53 / −25 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 56.3 | 0.1351 |

## Determinismo

| Módulo | Corridas | Diffs distintos |
|---|---|---|
| variables | 1 | 1 |

Las refactorizaciones que el modelo dice haber aplicado están al final de cada `<corrida>_respuesta.md`.
