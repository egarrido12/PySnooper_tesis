# Análisis estático con Rope 1.14.0

## find_errors (rope.contrib.finderrors)

| Módulo | Errores reportados |
|---|---|
| `pysnooper/__init__.py` | 0 |
| `pysnooper/pycompat.py` | 3 |
| `pysnooper/tracer.py` | 20 |
| `pysnooper/utils.py` | 8 |
| `pysnooper/variables.py` | 0 |

- `pysnooper/pycompat.py:62` — Unresolved variable basestring
- `pysnooper/pycompat.py:63` — Unresolved variable unicode
- `pysnooper/pycompat.py:87` — Unresolved attribute min
- `pysnooper/tracer.py:54` — Defined later key
- `pysnooper/tracer.py:54` — Defined later value
- `pysnooper/tracer.py:57` — Unresolved variable key_value
- `pysnooper/tracer.py:91` — Unresolved attribute splitlines
- `pysnooper/tracer.py:93` — Unresolved attribute match
- `pysnooper/tracer.py:94` — Unresolved attribute match
- `pysnooper/tracer.py:95` — Unresolved attribute match
- `pysnooper/tracer.py:100` — Defined later line
- `pysnooper/tracer.py:143` — Defined later sline
- `pysnooper/tracer.py:260` — Defined later v
- `pysnooper/tracer.py:260` — Defined later v
- `pysnooper/tracer.py:260` — Defined later v
- `pysnooper/tracer.py:276` — Defined later x
- `pysnooper/tracer.py:277` — Unresolved attribute Iterable
- `pysnooper/tracer.py:370` — Unresolved attribute __dict__
- `pysnooper/tracer.py:376` — Unresolved attribute __dict__
- `pysnooper/tracer.py:386` — Unresolved attribute original_trace_functions
- `pysnooper/tracer.py:402` — Unresolved attribute depth
- `pysnooper/tracer.py:412` — Unresolved attribute __code__
- `pysnooper/tracer.py:452` — Unresolved attribute depth
- `pysnooper/utils.py:47` — Unresolved variable c
- `pysnooper/utils.py:47` — Unresolved variable c
- `pysnooper/utils.py:54` — Unresolved variable x
- `pysnooper/utils.py:54` — Unresolved variable y
- `pysnooper/utils.py:65` — Unresolved attribute sub
- `pysnooper/utils.py:93` — Unresolved variable BaseExceptionGroup
- `pysnooper/utils.py:97` — Defined later e
- `pysnooper/utils.py:107` — Unresolved attribute Iterable

## find_occurrences (rope.contrib.findit)

### `get_shortish_repr` (6 ocurrencias)

- `pysnooper/variables.py:55`
- `pysnooper/variables.py:65`
- `pysnooper/variables.py:105`
- `pysnooper/utils.py:68`
- `pysnooper/tracer.py:54`
- `pysnooper/tracer.py:571`

### `truncate` (8 ocurrencias)

- `tests/test_multiple_files/test_multiple_files.py:11`
- `tests/test_pysnooper.py:13`
- `tests/test_pysnooper.py:1325`
- `pysnooper/utils.py:78`
- `pysnooper/utils.py:82`
- `pysnooper/tracer.py:584`
- `tests/test_chinese.py:11`
- `tests/test_not_implemented.py:12`

### `_is_internal_frame` (3 ocurrencias)

- `pysnooper/tracer.py:372`
- `pysnooper/tracer.py:411`
- `pysnooper/tracer.py:434`

### `Tracer` (3 ocurrencias)

- `pysnooper/__init__.py:20`
- `pysnooper/tracer.py:191`
- `pysnooper/tracer.py:412`

### `CommonVariable` (5 ocurrencias)

- `pysnooper/variables.py:53`
- `pysnooper/variables.py:86`
- `pysnooper/variables.py:100`
- `pysnooper/tracer.py:16`
- `pysnooper/tracer.py:260`

## find_definition (rope.contrib.findit)

Desde `pysnooper/variables.py` (`utils.get_shortish_repr(key)`) Rope resuelve la definición en `pysnooper/utils.py:68`.
