# Pruebas de PySnooper con Rope

Este documento cuenta todo el proceso: qué se probó, cómo reproducirlo, qué salió y cómo se interpreta.

- **Proyecto bajo prueba:** PySnooper (commit `4be5c15`), carpeta `pysnooper/` (964 líneas en 5 módulos).
- **Herramienta:** [Rope](https://github.com/python-rope/rope) 1.14.0, una biblioteca de refactorización automática para Python.
- **Entorno:** Python 3.9.6, pytest 8.4.2, macOS (Darwin 24.6.0), `.venv` del repositorio.
- **Fecha de ejecución:** 2026-10-05.

---

## 1. Objetivo y metodología

La pregunta es: **¿las refactorizaciones automáticas de Rope conservan el comportamiento de PySnooper?**

La suite de tests de PySnooper sirve como oráculo:

1. **Línea base:** se corre la suite original y se anota el resultado de referencia.
2. **Análisis estático:** se usan las herramientas de análisis de Rope (`find_errors`, `find_occurrences`, `find_definition`) sin modificar código.
3. **Refactorizaciones:** cada refactorización se aplica con la API de Rope **sobre una copia limpia e independiente** del proyecto. Se guarda el diff y se vuelve a correr la suite completa.
4. **Veredicto:** si el número de tests que pasan es igual al de la línea base y no hay fallos ni errores, la refactorización **preserva el comportamiento**. Si no, **rompe tests**.

> El código original en `pysnooper/` **nunca se modifica**. Todo se hace en `rope_pruebas/_trabajo/<experimento>/`.

---

## 2. Cómo ejecutarlo

Desde la raíz del repositorio:

```bash
# (una sola vez) instalar dependencias en el entorno virtual
.venv/bin/pip install rope pytest

# 1) Línea base "a mano" (opcional, el script también la hace)
.venv/bin/python -m pytest tests -q -rs

# 2) Todo el proceso: línea base + análisis estático + refactorizaciones
.venv/bin/python rope_pruebas/ejecutar_pruebas_rope.py
```

Tarda unos 15 segundos. La salida en consola se ve así:

```
[linea base] {'returncode': 0, 'passed': 83, 'failed': 0, 'skipped': 2, 'errors': 0}  (pysnooper importado desde .../_trabajo/00_linea_base/pysnooper/__init__.py)
[analisis] errores=31 ocurrencias={'get_shortish_repr': 6, 'truncate': 8, ...}
[02_rename_funcion] COMPORTAMIENTO PRESERVADO  {...}
...
```

Cada ejecución **borra y regenera** la carpeta `resultados/`.

### Estructura de archivos

```
rope_pruebas/
├── README.md                    ← este documento
├── ejecutar_pruebas_rope.py     ← script que automatiza todo
├── .gitignore                   ← ignora _trabajo/
├── _trabajo/                    ← copias del proyecto, una por experimento (temporal)
└── resultados/
    ├── resumen.md               ← tabla resumen (se genera sola)
    ├── resumen.json             ← los mismos datos en JSON (para gráficos o tablas de la tesis)
    ├── 00_linea_base_pytest.txt ← salida completa de pytest de la línea base
    ├── 01_analisis_estatico.md  ← resultados de find_errors / find_occurrences / find_definition
    ├── NN_<nombre>.diff         ← cambios exactos que hizo Rope
    └── NN_<nombre>_pytest.txt   ← salida de pytest después de la refactorización
```

---

## 3. Paso 1: línea base (tests de PySnooper sin cambios)

Comando: `.venv/bin/python -m pytest tests -q -rs`

| Resultado | Cantidad |
|---|---|
| Passed | **83** |
| Failed | 0 |
| Skipped | 2 |
| Errors | 0 |

Los 2 tests omitidos están en `tests/test_pysnooper.py:1911` y `:1941`. Necesitan `ExceptionGroup`, que solo existe desde Python 3.11, así que se omiten en Python 3.9 y no indican ningún fallo.

El script también comprueba que pytest importa el `pysnooper` de cada copia y no otro instalado (la ruta aparece en la consola). Así cada experimento prueba de verdad el código refactorizado.

**Referencia para comparar: 83 passed / 0 failed / 2 skipped.**

---

## 4. Paso 2: análisis estático con Rope

Detalle completo en [`resultados/01_analisis_estatico.md`](resultados/01_analisis_estatico.md).

### 4.1 `find_occurrences`: búsqueda de referencias

| Símbolo | Ocurrencias encontradas | ¿Correcto? |
|---|---|---|
| `utils.get_shortish_repr` | 6 (definición + usos en `tracer.py` y `variables.py`) | Sí |
| `utils.truncate` | 8 (incluye imports en 4 archivos de tests) | Sí |
| `Tracer._is_internal_frame` | 3 | Sí |
| `Tracer` | 3 | Sí |
| `variables.CommonVariable` | 5 (incluye subclases `Attrs` y `Keys`) | Sí |

Los conteos coinciden con una revisión manual hecha con `grep`.

### 4.2 `find_definition`: ir a la definición

Desde la llamada `utils.get_shortish_repr(key)` en `variables.py`, Rope resuelve bien la definición en `pysnooper/utils.py:68`.

### 4.3 `find_errors`: detección de errores

Rope reporta **31 avisos** (pycompat: 3, tracer: 20, utils: 8). Los revisé uno por uno y **los 31 son falsos positivos**. El código funciona y los 83 tests pasan.

| Categoría | Cant. | Ejemplos | Por qué es falso positivo |
|---|---|---|---|
| Variables de comprensiones, generadores o lambdas | 14 | `tracer.py:54` (`key`, `value`), `utils.py:47` (`c`), `utils.py:54` (`x`, `y`) | Rope no modela bien el alcance de las variables dentro de `[... for x in ...]` y reporta "Defined later" o "Unresolved variable" |
| Tipos de la biblioteca estándar que Rope no infiere | 9 | `.match` de un `re.Pattern`, `.splitlines`, `collections_abc.Iterable`, `datetime.min` | Rope no infiere el tipo del objeto y no encuentra el atributo |
| Atributos dinámicos de `threading.local` | 5 | `thread_global.depth`, `.original_trace_functions` | Esos atributos se crean en tiempo de ejecución |
| Nombres de Python 2 protegidos por versión | 2 | `basestring`, `unicode` (`pycompat.py:62-63`) | Solo se ejecutan en Python 2 (rama `else` del chequeo de versión) |
| Nombres de Python 3.11+ protegidos | 1 | `BaseExceptionGroup` (`utils.py:93`) | Está dentro de `try/except NameError` |

**Conclusión del análisis:** la búsqueda de referencias y definiciones es precisa. `find_errors` genera mucho ruido en un código como PySnooper (compatible con Python 2 y 3 y con uso intensivo de comprensiones), así que no sirve como detector de bugs sin revisión manual.

---

## 5. Paso 3: refactorizaciones automáticas

Se probaron 11 refactorizaciones de 4 tipos: Rename, Extract Method, Inline y Move.

### 5.1 Resultados

| # | Tipo | Qué se hizo | Archivos modificados | Tests (passed/failed) | Veredicto |
|---|---|---|---|---|---|
| 02 | Rename | `get_shortish_repr` → `get_short_repr` | 3 | 83 / 0 | ✅ Preservado |
| 03 | Rename | `truncate` → `truncate_string` (importada por tests) | 6 | 83 / 0 | ✅ Preservado |
| 04 | Rename | método `Tracer._is_internal_frame` → `_is_pysnooper_frame` | 1 | 83 / 0 | ✅ Preservado |
| 05 | Rename | clase `CommonVariable` → `GenericVariable` | 2 | 83 / 0 | ✅ Preservado |
| 06 | Rename | parámetro `string` de `truncate` → `text` | 1 | 83 / 0 | ✅ Preservado |
| 07 | Extract Method | bloque "Making timestamp" de `Tracer.trace` → `_make_timestamp` | 1 | 15 / **68** | ❌ Rompe tests |
| 08 | Extract Method | bloque "misplaced function definition" → `_skip_decorator_lines` | 1 | 43 / **40** | ❌ Rompe tests |
| 09 | Extract Method | bloque de reporte de variables (usa `**locals()`) → `_report_variables` | 1 | 15 / **68** | ❌ Rompe tests |
| 10 | Extract Method | **control:** `try/except` de `get_shortish_repr` → `_safe_repr` | 1 | 83 / 0 | ✅ Preservado |
| 11 | Inline | `normalize_repr` dentro de `get_shortish_repr` | 1 | 83 / 0 | ✅ Preservado |
| 12 | Move | `utils.shitcode` → módulo `pycompat` | 3 | 83 / 0 | ✅ Preservado |

**Totales: 8 de 11 preservan el comportamiento (73 %). Las 3 que fallan son Extract Method dentro de `Tracer.trace` y tienen la misma causa.** Cada operación de Rope tardó menos de 0,2 s.

### 5.2 Rename, Inline y Move (todas correctas)

- **02 y 03:** Rope actualizó todos los usos entre módulos, incluidos `from pysnooper.utils import truncate` en `tests/test_chinese.py`, `tests/test_not_implemented.py`, `tests/test_multiple_files/test_multiple_files.py` y `tests/test_pysnooper.py`.
- **05:** renombró la clase, sus subclases (`class Attrs(GenericVariable)`), el `import` en `tracer.py` y la instanciación.
- **11:** reemplazó la llamada por su cuerpo (`r = DEFAULT_REPR_RE.sub('', r)`) y borró la función.
- **12:** el resultado funciona, pero el diff muestra dos detalles de estilo:
  - Agregó `import pysnooper.pycompat` y usa `pysnooper.pycompat.shitcode(s)`, aunque `tracer.py` ya tenía `from . import pycompat`. El import nuevo es redundante e inconsistente con el estilo del módulo.
  - Además borró `import sys` de `utils.py`, que no se usaba. Es un cambio extra que no se pidió.

### 5.3 Por qué fallan los Extract Method 07, 08 y 09

`Tracer.trace` arma su salida con este patrón:

```python
self.write(u'{indent}{_STYLE_DIM}{timestamp} {thread_info}{event:9} '
           u'{line_no:4}{_STYLE_RESET_ALL} {source_line}'.format(**locals()))
```

Las variables (`timestamp`, `line_no`, `source_line`, `_FOREGROUND_GREEN`, etc.) **solo se leen por nombre dentro de un string** a través de `locals()`. El análisis de flujo de datos de Rope es estático y no puede saber que esas variables se usan después del bloque extraído. Por eso:

- **07:** Rope genera `self._make_timestamp(frame)` **sin asignar el resultado**, y el método nuevo no hace `return timestamp`. Luego `format(**locals())` falla con `KeyError: 'timestamp'`.
- **08:** el método `_skip_decorator_lines` modifica `line_no` y `source_line` pero no los devuelve, así que se pierde el ajuste de líneas con decoradores. 40 tests fallan porque la salida muestra la línea del `@decorador` en vez de la del `def`.
- **09:** el método extraído usa `'{indent}{_FOREGROUND_GREEN}...'.format(**locals())`, pero Rope no pasó `indent`, `newish_string` ni las variables de color como parámetros, porque no las ve usadas. Resultado: `KeyError`.

Además, en el 08 Rope movió al método nuevo todo lo que seguía en `trace`, no solo el bloque seleccionado (ver `resultados/08_extract_decorador.diff`). Es una consecuencia de no poder determinar bien el flujo del bloque.

**Experimento de control (10):** para confirmar que el problema es `locals()` y no Extract Method en general, se extrajo un bloque equivalente en `utils.get_shortish_repr`, donde la variable de salida `r` se usa explícitamente. Rope generó bien `r = _safe_repr(repr_function, item)` con `return r`, y los 83 tests pasaron. El único detalle es estético: dejó una sola línea en blanco entre funciones en vez de las dos de PEP 8.

**Conclusión:** la limitación no es de Extract Method en sí. Es la combinación del **análisis estático de Rope** con el **uso de `locals()` / `**locals()`** (acceso dinámico a variables) en PySnooper. Ninguna herramienta de refactorización basada en análisis estático puede ver ese tipo de dependencias.

---

## 6. Conclusiones

1. **Rename, Inline y Move son confiables** en PySnooper: 7 de 7 preservaron el comportamiento, incluso con cambios que cruzan módulos y archivos de tests.
2. **Extract Method es inseguro en código que usa `locals()`**: 3 de 3 rompieron tests dentro de `Tracer.trace`. Lo hace sin avisar: Rope aplica el cambio sin advertencias y solo los tests detectan el problema.
3. **La suite de tests es indispensable como red de seguridad.** Sin ella, las refactorizaciones 07 a 09 habrían introducido bugs silenciosos.
4. **`find_errors` tiene una tasa alta de falsos positivos** (31/31) en este código, mientras que `find_occurrences` y `find_definition` fueron precisos.
5. **Calidad de estilo:** incluso las refactorizaciones correctas pueden dejar imports redundantes (Move) o espaciado distinto a PEP 8 (Extract). Conviene revisar los diffs a mano.

---

## 7. Cómo agregar una refactorización nueva

En `ejecutar_pruebas_rope.py`:

1. Escribe una función que reciba el proyecto Rope `p` y devuelva los cambios:

   ```python
   def ref_mi_prueba(p):
       r = p.get_resource('pysnooper/utils.py')
       offset = offset_de(r, 'def ensure_tuple', 4)   # apunta al nombre
       return Rename(p, r, offset).get_changes('as_tuple')
   ```

   - `offset_de(recurso, marcador, desplazamiento)` busca un texto **único** en el archivo y devuelve su posición. El desplazamiento mueve el cursor hasta el nombre (`'def '` = 4, `'class '` = 6).
   - Para Extract Method se necesita un rango `(inicio, fin)`; ver `ref_extract_control` como ejemplo.

2. Agrégala a la lista `REFACTORIZACIONES`:

   ```python
   ('13_mi_prueba', 'Rename', 'ensure_tuple -> as_tuple', ref_mi_prueba),
   ```

3. Vuelve a correr el script. La fila nueva aparece en `resultados/resumen.md`.

### API de Rope usada (referencia rápida)

| Operación | Clase / función | Llamada |
|---|---|---|
| Abrir proyecto | `rope.base.project.Project` | `Project(ruta)` … `proyecto.close()` |
| Renombrar | `rope.refactor.rename.Rename` | `Rename(p, recurso, offset).get_changes('nuevo')` |
| Extraer método | `rope.refactor.extract.ExtractMethod` | `ExtractMethod(p, recurso, inicio, fin).get_changes('nombre')` |
| Inline | `rope.refactor.inline.create_inline` | `create_inline(p, recurso, offset).get_changes()` |
| Mover | `rope.refactor.move.create_move` | `create_move(p, recurso, offset).get_changes(recurso_destino)` |
| Aplicar cambios | — | `p.do(cambios)` |
| Ver diff | — | `cambios.get_description()` |
| Buscar usos | `rope.contrib.findit.find_occurrences` | `find_occurrences(p, recurso, offset)` |
| Ir a definición | `rope.contrib.findit.find_definition` | `find_definition(p, codigo, offset, recurso)` |
| Buscar errores | `rope.contrib.finderrors.find_errors` | `find_errors(p, recurso)` |
