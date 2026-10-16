# Resumen de pruebas con Rope

- Python: `3.9.6`
- Rope: `1.14.0`
- Fecha: 2026-10-05 22:45

## Línea base

83 passed, 0 failed, 2 skipped, 0 errors

## Refactorizaciones

| # | Tipo | Descripción | Rope | Tiempo (s) | Tests (passed/failed/errors) | Veredicto |
|---|---|---|---|---|---|---|
| 02_rename_funcion | Rename | utils.get_shortish_repr -> get_short_repr (usada en 3 módulos) | aplicada | 0.134 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 03_rename_funcion_tests | Rename | utils.truncate -> truncate_string (también importada por los tests) | aplicada | 0.162 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 04_rename_metodo | Rename | Tracer._is_internal_frame -> _is_pysnooper_frame | aplicada | 0.139 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 05_rename_clase | Rename | variables.CommonVariable -> GenericVariable (clase base con subclases) | aplicada | 0.134 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 06_rename_parametro | Rename | parámetro string de truncate -> text | aplicada | 0.06 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 07_extract_timestamp | Extract Method | bloque "Making timestamp" de Tracer.trace -> _make_timestamp | aplicada | 0.173 | 15 / 68 / 0 | **ROMPE TESTS** |
| 08_extract_decorador | Extract Method | bloque "misplaced function definition" -> _skip_decorator_lines (2 valores de retorno) | aplicada | 0.054 | 43 / 40 / 0 | **ROMPE TESTS** |
| 09_extract_con_locals | Extract Method | bloque que usa .format(**locals()) -> _report_variables (caso límite) | aplicada | 0.174 | 15 / 68 / 0 | **ROMPE TESTS** |
| 10_extract_control | Extract Method | control sin locals(): try/except de get_shortish_repr -> _safe_repr | aplicada | 0.007 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 11_inline_funcion | Inline | inline de utils.normalize_repr en get_shortish_repr | aplicada | 0.047 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 12_move_funcion | Move | mover utils.shitcode a pycompat | aplicada | 0.096 | 83 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
