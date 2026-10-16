# Pruebas de PySnooper con un LLM (prompt general)

Este documento describe el proceso completo: qué se probó, cómo reproducirlo, qué resultados se obtuvieron, cómo interpretarlos y cómo se comparan con las pruebas de Rope (`../rope_pruebas/`).

- **Proyecto bajo prueba:** PySnooper (commit `4be5c15`), carpeta `pysnooper/` (964 líneas en 5 módulos).
- **Modelo:** Claude Opus 5.5 (`claude-opus-5-5`), effort `high`, API de Anthropic (SDK `anthropic` 0.125.0).
- **Entorno:** Python 3.9.6, pytest 8.4.2, macOS (Darwin 24.6.0), `.venv` del repositorio.
- **Fecha de ejecución:** 2026-10-15.
- **Ejecución principal:** `resultados/20261015_174023/` (15 corridas).
- **Piloto:** `resultados/20261015_173914/` (1 corrida de `variables`).

---

## 1. Objetivo y diferencia con Rope

La pregunta es: **cuando un LLM refactoriza PySnooper por su cuenta, ¿conserva el comportamiento? ¿Qué refactorizaciones elige?**

Rope y el LLM se usan de forma distinta:

| | Rope | LLM |
|---|---|---|
| ¿Quién decide qué refactorizar? | La persona (offset + nombre nuevo) | **El modelo** |
| ¿Quién ejecuta el cambio? | Rope | El modelo |
| Instrucción | Una refactorización concreta por prueba (11 en total) | **Un único prompt general**, igual para todos los módulos |
| Determinismo | Total | No: el mismo prompt puede dar resultados distintos |

Por eso aquí no se le dice al modelo "extrae este bloque" ni "renombra esta función". Recibe el mismo prompt general para cada módulo y decide qué hacer.

## 2. Metodología

1. **Prompt fijo y versionado:** [`prompt_v1.md`](prompt_v1.md). Pide mejorar legibilidad y mantenibilidad sin cambiar el comportamiento, con estas reglas:
   - no cambiar nombres ni firmas públicas (los usan otros módulos y los tests);
   - no agregar funcionalidades;
   - modificar solo el archivo indicado;
   - mantener la compatibilidad con las versiones de Python soportadas.

   También pide devolver el archivo completo y una lista de las refactorizaciones aplicadas según el catálogo de Fowler.
2. **Contexto:** en cada llamada el modelo recibe **los 5 módulos del paquete** como contexto de solo lectura, más la instrucción `Refactoriza el archivo pysnooper/<modulo>.py`. El contexto es idéntico en todas las llamadas, así que se reutiliza la caché de prompts.
3. **Unidad de trabajo:** un módulo por llamada (`utils`, `variables`, `tracer`, `pycompat`, `__init__`).
4. **Repeticiones:** **3 corridas por módulo**, 15 llamadas en total. Opus 5.5 no permite fijar la temperatura (la API rechaza el parámetro), así que la variabilidad se mide repitiendo.
5. **Evaluación**, igual que con Rope:
   - se aplica el archivo devuelto sobre una **copia limpia** del proyecto;
   - se genera el diff;
   - se corre la suite completa (83 tests).

   Si pasan los mismos tests que en la línea base, sin fallos ni errores, el veredicto es **comportamiento preservado**.
6. **Clasificación de fallos** (si los hubiera): sintaxis, API rota (import o atributo) o cambio de comportamiento.
7. **Análisis posterior:**
   - clasificación de las refactorizaciones según Fowler;
   - verificación de la API pública con `ast`;
   - comparación con las refactorizaciones de Rope.

> El código original en `pysnooper/` **nunca se modifica**. Cada ejecución se guarda en su propia carpeta `resultados/<fecha_hora>/` para no sobrescribir corridas que ya costaron dinero.

## 3. Cómo ejecutarlo

Requiere una API key de Anthropic en la variable de entorno `ANTHROPIC_API_KEY` (en este equipo está en `~/.zshrc`).

```bash
# (una sola vez) dependencias
.venv/bin/pip install "anthropic<1" pytest      # anthropic 1.x requiere Python >= 3.10

# ver el prompt exacto, sin llamar a la API ni gastar
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --dry-run

# ejecución completa (5 módulos × 3 corridas, ~17 min, ~US$ 2.5)
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py

# variantes
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --modulos variables --corridas 1
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --corridas 5 --effort xhigh
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --modelo claude-sonnet-5-5
```

### Estructura de archivos

```
llm_pruebas/
├── README.md                  ← este documento
├── ejecutar_pruebas_llm.py    ← script que automatiza todo
├── prompt_v1.md               ← prompt general (versionado)
├── .gitignore                 ← ignora _trabajo/
├── _trabajo/                  ← copias del proyecto, una por corrida (temporal)
└── resultados/
    └── <fecha_hora>/
        ├── resumen.md / resumen.json       ← tabla general, tokens, costo, determinismo
        ├── prompt.md                       ← copia del prompt usado
        ├── 00_linea_base_pytest.txt
        ├── <modulo>_run<n>_respuesta.md    ← respuesta completa del modelo (incluye su lista de refactorizaciones)
        ├── <modulo>_run<n>.py              ← archivo refactorizado
        ├── <modulo>_run<n>.diff            ← diff contra el original
        └── <modulo>_run<n>_pytest.txt      ← salida de pytest
```

---

## 4. Resultados

### 4.1 Línea base

`83 passed, 0 failed, 2 skipped, 0 errors`, idéntica a la de Rope.

### 4.2 Preservación del comportamiento: 15 de 15

| Módulo | Corridas | Tests en las 3 corridas | +/− líneas (rango) | Tiempo medio | Costo (3 corridas) |
|---|---|---|---|---|---|
| `utils` | 3 | 83 / 0 / 0 ✅✅✅ | +100…106 / −45…49 | 48 s | US$ 0.35 |
| `variables` | 3 | 83 / 0 / 0 ✅✅✅ | +68…75 / −23…31 | 54 s | US$ 0.39 |
| `tracer` | 3 | 83 / 0 / 0 ✅✅✅ | +345…347 / −272…278 | 170 s | US$ 1.40 |
| `pycompat` | 3 | 83 / 0 / 0 ✅✅✅ | +34…62 / −18…24 | 37 s | US$ 0.26 |
| `__init__` | 3 | 83 / 0 / 0 ✅✅✅ | +7…8 / −5…6 | 21 s | US$ 0.15 |
| **Total** | **15** | **15 / 15 preservan** | | **66 s** | **US$ 2.55** |

- No hubo errores de sintaxis, respuestas truncadas, rechazos ni fallback a otro modelo: las 15 respuestas las generó `claude-opus-5-5`.
- Tokens: 125 616 de salida (incluye el razonamiento interno) y 189 540 de entrada leídos desde la caché.
- Contando el piloto (US$ 0.14) y un primer intento que falló por un bug del script ya corregido (~US$ 0.14), el gasto total fue de unos **US$ 2.83**.

Detalle por corrida: [`resultados/20261015_174023/resumen.md`](resultados/20261015_174023/resumen.md).

### 4.3 Refactorizaciones elegidas por el modelo

Esta clasificación sale de la lista que el modelo entrega al final de cada respuesta, contrastada con los diffs.

| Módulo | Refactorizaciones que aparecen en **las 3 corridas** | Variaciones entre corridas |
|---|---|---|
| `utils` | Extract Function (`_safe_repr`, `_remove_line_breaks`, `_is_exception_group`, `_format_exception_group`, `_is_non_string_iterable`, búsqueda en el MRO desde `_check_methods`); Rename Variable (`r` → `item_repr`, `left/right` → `left_length/right_length`, `B` → nombre descriptivo); Replace Magic Literal (`'REPR FAILED'`, `'...'`); Remove Dead Code (`import sys`) | Nombres de las funciones extraídas (`_find_defining_class` / `_lookup_in_mro`); las corridas 1 y 3 renombran el parámetro `C` → `subclass` de `WritableStream.__subclasshook__` |
| `variables` | Extract Function `_compile_expression` + constante `_VARIABLE_FILENAME`; Extract Function para el cálculo de `unambiguous_source`; Rename Parameter `key` → `main_value` en `BaseVariable._items`; Extract Method en `CommonVariable._items` (nombre del hijo); **Extract Method en `Exploding._items`** (selección de `Keys/Indices/Attrs`); docstrings | La corrida 1 reemplaza el `try/except ImportError` por `pycompat.collections_abc`; la corrida 3 extrae además `BaseVariable._evaluate`; los nombres cambian (`_choose_variable_class` / `_variable_class_for`) |
| `tracer` | Descomposición de `get_path_and_source_from_frame` en 5–6 funciones; `_write_to_stderr` con guard clauses; `_normalize_custom_repr`; tabla de colores ANSI en lugar de 2×11 asignaciones; split de `_wrap_function`; `_write_elapsed_time`; **descomposición de `Tracer.trace`** (`_make_timestamp`, reporte de variables, salto de decoradores, info de hilo, etc.); **eliminación de los 9 `.format(**locals())`**; Remove Dead Code (`import traceback`) | Nombres de los métodos extraídos; la corrida 3 crea `_format_line` y `_make_indent`; cuántas variables locales renombra |
| `pycompat` | Extract Function `_always_false` (reemplaza 2 lambdas duplicadas); Substitute Algorithm (`try/except AttributeError` → `getattr(..., default)`); Replace Magic Literal (plantilla y longitud `15` de `time_isoformat`); Rename `time` → `time_of_day`; Extract Variable en `timedelta_parse`; reorganización en secciones | La extracción del predicado de `PathLike.__subclasshook__` aparece solo en las corridas 1 y 2; el tamaño del diff varía mucho (+34 a +62) |
| `__init__` | Rename `__VersionInfo` → `_VersionInfo`; quitar paréntesis redundantes; mover `import collections` antes de los imports relativos | Solo el texto del comentario |

**Tipos más frecuentes:** Extract Function/Method (por lejos), Rename Variable/Parameter, Replace Magic Literal, Remove Dead Code, Substitute Algorithm y Consolidate Conditional. No usó Move ni Inline, que son dos de los tipos probados con Rope.

### 4.4 Determinismo

| Módulo | Corridas | Diffs distintos |
|---|---|---|
| todos | 3 | **3** |

Ninguna corrida produjo un diff idéntico a otra. Aun así, como muestra la tabla 4.3, **las decisiones de fondo son muy estables**: casi siempre extrae los mismos bloques y renombra los mismos elementos. Las diferencias están sobre todo en los nombres elegidos, los docstrings y el formato. La variabilidad está en la superficie y no en la estrategia.

### 4.5 Respeto de la API pública (verificación con `ast`)

Se compararon los nombres de nivel de módulo y los métodos públicos de cada archivo antes y después:

| Cambio detectado | Corridas | ¿Rompe algo? |
|---|---|---|
| `__VersionInfo` → `_VersionInfo` (`__init__`) | 3/3 | No: es privado y el propio módulo lo borra con `del` |
| Se elimina `import traceback` (`tracer`) / `import sys` (`utils`) | 3/3 | No se usaban; solo desaparecen como atributo del módulo |
| Parámetro `C` → `subclass` en `WritableStream.__subclasshook__` | 2/3 (`utils`) | No en la práctica: Python siempre lo llama de forma posicional. Formalmente cambia una firma, así que es una **infracción menor de la regla del prompt** |

Ningún nombre público usado por otros módulos o por los tests cambió. No se introdujeron f-strings, lo que es coherente con la regla de compatibilidad con Python 2, aunque esa compatibilidad no se puede probar en este entorno.

---

## 5. Comparación con Rope

### 5.1 El caso clave: Extract Method en `Tracer.trace`

Tres de las once refactorizaciones de Rope **rompieron los tests**, y las tres eran Extract Method sobre `Tracer.trace`. En las 3 corridas, el LLM extrajo **por su cuenta** métodos equivalentes de esos mismos bloques, sin recibir ninguna instrucción al respecto, y **los 83 tests siguieron pasando**:

| Bloque de `Tracer.trace` | Rope (prueba) | Resultado de Rope | LLM (3 corridas) | Resultado del LLM |
|---|---|---|---|---|
| "Making timestamp" | `_make_timestamp` (07) | ❌ 15 passed / 68 failed | `_make_timestamp(self, frame)` | ✅ 3/3 |
| Salto de decoradores ("misplaced function definition") | `_skip_decorator_lines` (08) | ❌ 43 / 40 | función `_find_function_definition(source, line_no, source_line)` que **devuelve la tupla** `(line_no, source_line)` | ✅ 3/3 |
| Reporte de variables (usa `.format(**locals())`) | `_report_variables` (09) | ❌ 15 / 68 | `_report_variables` / `_report_variable_changes(self, frame, event, indent)` | ✅ 3/3 |

**Por qué el LLM lo logra y Rope no:** el código original arma sus mensajes con `.format(**locals())`, que depende implícitamente de las variables locales de `trace`. El análisis estático de Rope no ve esa dependencia. Al mover el bloque a otro método, las variables dejan de existir en ese ámbito y el formateo falla. El LLM **reconoció el problema y lo eliminó primero**: en las 3 corridas sustituyó los 9 usos de `.format(**locals())` por argumentos explícitos, y después extrajo los métodos. En el caso del salto de decoradores (que tiene dos valores de salida), devolvió una tupla en lugar de mutar variables del llamador.

Rope aplica una transformación mecánica y local. El LLM hace una **cadena de refactorizaciones dependientes**: primero vuelve explícitas las dependencias y después extrae.

### 5.2 Matriz completa: qué hizo el LLM con cada refactorización de Rope

Para cada una de las 11 refactorizaciones de Rope se revisó qué hizo el LLM con **el mismo elemento** en sus 3 corridas:

| # Rope | Refactorización | Rope | ¿El prompt permitía hacerla? | LLM (3 corridas) | ¿Comparable? |
|---|---|---|---|---|---|
| 02 | Rename `get_shortish_repr` (pública) | ✅ | ❌ regla "no cambiar nombres públicos" | No la renombra (0/3) | No: bloqueada por el prompt |
| 03 | Rename `truncate` (pública, usada en tests) | ✅ | ❌ misma regla | No (0/3) | No: bloqueada |
| 04 | Rename `Tracer._is_internal_frame` (privada) | ✅ | ✅ | No la renombra (0/3); el modelo no lo consideró necesario | Parcial: el LLM *pudo* y decidió que no |
| 05 | Rename clase `CommonVariable` (pública) | ✅ | ❌ | No (0/3) | No: bloqueada |
| 06 | Rename parámetro `string` de `truncate` (firma pública) | ✅ | ❌ | No (0/3) | No: bloqueada |
| 07 | Extract Method "timestamp" en `trace` | ❌ 15/68 | ✅ | `_make_timestamp` 3/3 | **Sí** → LLM ✅, Rope ❌ |
| 08 | Extract Method salto de decoradores | ❌ 43/40 | ✅ | `_find_function_definition` 3/3 | **Sí** → LLM ✅, Rope ❌ |
| 09 | Extract Method con `.format(**locals())` | ❌ 15/68 | ✅ | `_report_variables` / `_report_variable_changes` 3/3 | **Sí** → LLM ✅, Rope ❌ |
| 10 | Extract Method `_safe_repr` en `get_shortish_repr` | ✅ | ✅ | `_safe_repr` 3/3, **con el mismo nombre que Rope**; el LLM además usa `return` directo y una constante para `'REPR FAILED'` | **Sí** → ambos ✅ |
| 11 | Inline `normalize_repr` (pública) | ✅ | ❌ eliminarla rompería la API pública | La conserva (0/3) | No: bloqueada |
| 12 | Move `shitcode` a `pycompat` (2 archivos) | ✅ | ❌ regla "modifica solo el archivo indicado" | La conserva (0/3) | No: bloqueada |

**Conclusión:** con `prompt_v1` la comparación directa 1 a 1 con Rope es posible **solo para Extract Method** (4 casos: 07, 08, 09 y 10), más el caso de validación cruzada de `Exploding._items` (5.3). De las otras 7, 6 quedaron **bloqueadas por reglas del propio prompt** (API pública y un solo archivo), y en 1 (04) el modelo podía hacerla pero decidió que no hacía falta. Por lo tanto, *no* se puede concluir que el LLM sea mejor o peor que Rope en Rename, Inline o Move: con este diseño, esos tipos no se midieron. La lógica de esas reglas y una propuesta de `prompt_v2` para medirlos están en [`DECISIONES_Y_FALLOS.md`](DECISIONES_Y_FALLOS.md).

En Extract Method, los resultados de los 4 casos comparables son **LLM 4/4 (12/12 corridas) frente a Rope 1/4**.

Además, el LLM aplicó muchas refactorizaciones que Rope no ofrece como operación automática: Replace Magic Literal, Guard Clauses, Substitute Algorithm, Remove Dead Code, docstrings y tablas de datos en lugar de código repetido.

### 5.3 Validación cruzada de un caso (`Exploding._items`)

El LLM extrajo la selección de clase de `Exploding._items` en todas las corridas, igual que en la salida manual previa `llm_out/CAL1_variables.py`. Se reprodujo esa extracción con `rope.refactor.extract.ExtractMethod` sobre el mismo bloque: Rope genera **el mismo método** (misma firma y mismo cuerpo, solo cambia una línea en blanco) y los 83 tests pasan. En las refactorizaciones simples, Rope y el LLM llegan al mismo resultado. La diferencia aparece cuando la refactorización exige entender el código, como en 5.1.

### 5.4 Resumen

| Criterio | Rope | LLM (Opus 5.5) |
|---|---|---|
| Preservación del comportamiento (global, tareas distintas) | 8/11 (73 %) | 15/15 corridas (100 %) |
| Preservación en Extract Method (mismos 4 bloques) | 1/4 | 4/4 (12/12 corridas) |
| Tipos comparados 1 a 1 | — | Solo Extract Method (ver §5.2) |
| Decide qué refactorizar | No | Sí |
| Determinismo | Total | Estrategia estable, texto variable (3/3 diffs distintos) |
| Alcance de cada cambio | Pequeño y acotado (1 operación) | Grande (+7 a +347 líneas por módulo, muchas operaciones juntas) |
| Cambios en varios archivos | Sí (actualiza todos los usos) | No en este diseño (un archivo por llamada) |
| Tiempo | ~0.1 s por refactorización | 21–186 s por módulo |
| Costo | Gratis | ~US$ 0.05–0.48 por módulo |
| Revisabilidad | Diff mínimo y predecible | Diff grande que requiere revisión humana |

---

## 6. Limitaciones y amenazas a la validez

> El análisis completo de las decisiones de diseño, la lógica de cada regla del prompt, los posibles sesgos y todos los fallos encontrados (técnicos, metodológicos y de análisis) está en [`DECISIONES_Y_FALLOS.md`](DECISIONES_Y_FALLOS.md). Abajo va un resumen.

1. **Los tests son el único oráculo.** Una refactorización que pasa los 83 tests no está demostrado que sea equivalente. Hay ramas sin tests en este entorno: compatibilidad con Python 2 y < 3.6 en `pycompat`, y la obtención de código desde IPython o Ansible en `tracer`. Una medición rápida con `coverage` da 50 % de cobertura de líneas, pero **es una cota inferior poco fiable**: PySnooper usa `sys.settrace`, que interfiere con el rastreo de `coverage` en Python 3.9. En particular, los cambios del LLM en `pycompat` (por ejemplo `getattr(..., default)`) y en las ramas de IPython o Ansible **no están cubiertos por los tests** y habría que revisarlos a mano.
2. **Diffs grandes.** El LLM aplica muchas refactorizaciones a la vez (en `tracer`, ~620 líneas cambiadas). Si algo fallara sería difícil aislar la causa, y revisar el diff cuesta más que con Rope.
3. **Un solo modelo, un solo prompt.** Los resultados corresponden a `claude-opus-5-5` con effort `high` y `prompt_v1.md`. Otro modelo, otro effort u otra redacción del prompt pueden dar otros resultados.
4. **3 corridas por módulo** bastan para observar variabilidad, pero no para estimar con precisión una tasa de error. Si la tasa real fuera baja pero no nula, 15/15 no la descarta.
5. **Comparación no simétrica.** Rope recibió 11 operaciones elegidas por una persona (incluidos casos límite a propósito). El LLM eligió las suyas. La sección 5.1 compara los casos donde ambos hicieron la misma operación sobre el mismo bloque.
6. **La lista de refactorizaciones la escribe el propio modelo.** Se contrastó con los diffs y con `ast` en los puntos clave (secciones 4.5 y 5.1), pero no se verificó cada elemento de forma exhaustiva. Una herramienta como PyRef permitiría automatizarlo.

## 7. Próximos pasos posibles

- Repetir con más corridas (5–10) o con otros modelos o proveedores (Sonnet 5.5, OpenAI, Gemini, un modelo local con Ollama) para comparar varios LLM contra Rope.
- Probar un prompt que permita cambios en varios archivos, para comparar con los Rename y Move de Rope.
- Revisar a mano los cambios en ramas sin tests (sección 6.1) o agregar tests para esas ramas.
- Reproducir con Rope más refactorizaciones del LLM (validación cruzada como en 5.3).
