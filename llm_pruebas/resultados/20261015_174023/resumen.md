# Resumen de pruebas con LLM (prompt general)

- Python: `3.9.6`
- SDK anthropic: `0.125.0`
- Modelo solicitado: `claude-opus-5-5` (effort `high`)
- Prompt: `prompt_v1.md`
- Corridas por módulo: 3
- Fecha: 2026-10-15 17:58
- Costo total estimado: US$ 2.55

## Línea base

83 passed, 0 failed, 2 skipped, 0 errors

## Corridas

| Corrida | Modelo | +/− líneas | Tests (passed/failed/errors) | Veredicto | Tipo de fallo | Tiempo (s) | Costo (US$) |
|---|---|---|---|---|---|---|---|
| utils_run1 | claude-opus-5-5 | +105 / −49 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 43.9 | 0.1055 |
| utils_run2 | claude-opus-5-5 | +100 / −45 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 46.3 | 0.1097 |
| utils_run3 | claude-opus-5-5 | +106 / −48 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 55.0 | 0.1364 |
| variables_run1 | claude-opus-5-5 | +75 / −31 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 58.2 | 0.1382 |
| variables_run2 | claude-opus-5-5 | +68 / −23 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 51.0 | 0.1251 |
| variables_run3 | claude-opus-5-5 | +69 / −25 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 53.0 | 0.1282 |
| tracer_run1 | claude-opus-5-5 | +346 / −277 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 185.6 | 0.4805 |
| tracer_run2 | claude-opus-5-5 | +345 / −278 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 182.5 | 0.4684 |
| tracer_run3 | claude-opus-5-5 | +347 / −272 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 142.1 | 0.4495 |
| pycompat_run1 | claude-opus-5-5 | +62 / −23 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 41.9 | 0.0979 |
| pycompat_run2 | claude-opus-5-5 | +45 / −24 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 38.5 | 0.0931 |
| pycompat_run3 | claude-opus-5-5 | +34 / −18 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 30.8 | 0.0737 |
| __init___run1 | claude-opus-5-5 | +8 / −5 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 21.3 | 0.0471 |
| __init___run2 | claude-opus-5-5 | +7 / −6 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 20.9 | 0.0494 |
| __init___run3 | claude-opus-5-5 | +7 / −5 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | 20.6 | 0.0492 |

## Determinismo

| Módulo | Corridas | Diffs distintos |
|---|---|---|
| __init__ | 3 | 3 |
| pycompat | 3 | 3 |
| tracer | 3 | 3 |
| utils | 3 | 3 |
| variables | 3 | 3 |

Las refactorizaciones que el modelo dice haber aplicado están al final de cada `<corrida>_respuesta.md`.
