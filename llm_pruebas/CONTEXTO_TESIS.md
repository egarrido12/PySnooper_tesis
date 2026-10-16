# Contexto del experimento Rope vs LLM, para redactar la tesis

Este documento resume todo lo que se hizo en el repositorio `PySnooper_tesis`, para que un asistente de redacción tenga el contexto completo sin acceso al código. Los detalles están en `llm_pruebas/README.md`, `llm_pruebas/DECISIONES_Y_FALLOS.md` y `rope_pruebas/README.md`.

---

## 1. Qué se compara

- **Objeto de estudio:** PySnooper (commit `4be5c15`), paquete `pysnooper/`: 5 módulos, 964 líneas.
- **Oráculo:** la suite de tests del proyecto. Línea base: **83 passed, 0 failed, 2 skipped**. Una refactorización "preserva el comportamiento" si después pasan los mismos 83 tests sin fallos ni errores.
- **Rope** (1.14.0): una persona elige 11 refactorizaciones concretas y Rope las ejecuta (2026-10-05).
- **LLM** (Claude Opus 5.5): recibe un **prompt general** y decide qué refactorizar (2026-10-15). Decisión explícita del autor: **no** darle al LLM la instrucción exacta.
- En ambos casos cada refactorización se aplica sobre una **copia limpia** del proyecto, se guarda el diff y se corren los tests. El código original nunca se modifica.

## 2. Resultados de Rope (11 refactorizaciones)

| # | Tipo | Descripción | Tests (passed/failed) | Veredicto |
|---|---|---|---|---|
| 02 | Rename | `utils.get_shortish_repr` → `get_short_repr` | 83 / 0 | Preserva |
| 03 | Rename | `utils.truncate` → `truncate_string` (también en tests) | 83 / 0 | Preserva |
| 04 | Rename | `Tracer._is_internal_frame` → `_is_pysnooper_frame` | 83 / 0 | Preserva |
| 05 | Rename | clase `CommonVariable` → `GenericVariable` | 83 / 0 | Preserva |
| 06 | Rename | parámetro `string` de `truncate` → `text` | 83 / 0 | Preserva |
| 07 | Extract Method | bloque timestamp de `Tracer.trace` → `_make_timestamp` | 15 / 68 | **Rompe** |
| 08 | Extract Method | bloque decoradores → `_skip_decorator_lines` (2 valores de retorno) | 43 / 40 | **Rompe** |
| 09 | Extract Method | bloque con `.format(**locals())` → `_report_variables` | 15 / 68 | **Rompe** |
| 10 | Extract Method | try/except de `get_shortish_repr` → `_safe_repr` | 83 / 0 | Preserva |
| 11 | Inline | `utils.normalize_repr` en `get_shortish_repr` | 83 / 0 | Preserva |
| 12 | Move | `utils.shitcode` → `pycompat` | 83 / 0 | Preserva |

Total: **8/11 preservan**. Las 3 que fallan son Extract Method sobre `Tracer.trace`.

## 3. Configuración del LLM (datos para la Tabla 5.7)

| Elemento | Valor |
|---|---|
| Modelo | `claude-opus-5-5` (Claude Opus 5.5, Anthropic) |
| Herramienta de acceso | SDK oficial de Anthropic para Python, `anthropic` 0.125.0 |
| Interfaz | Messages API (`/v1/messages`), modo streaming |
| Autenticación | API key personal de la consola de Anthropic, leída de la variable de entorno `ANTHROPIC_API_KEY` (no aparece en el código) |
| Script | `llm_pruebas/ejecutar_pruebas_llm.py` (Python 3.9.6) |
| Effort | `high` |
| Thinking | Adaptativo (siempre activo en este modelo) |
| Temperatura | No configurable: la API la rechaza en este modelo, así que la variabilidad se mide repitiendo corridas |
| `max_tokens` | 64 000 |
| Fallback de refusals | `fallbacks: "default"`; no se activó en ninguna corrida (las 15 respuestas son de `claude-opus-5-5`) |
| Caché de prompts | `cache_control: ephemeral` sobre el contexto (no afecta a la respuesta) |
| Unidad de trabajo | **Un módulo por llamada** (`utils`, `variables`, `tracer`, `pycompat`, `__init__`) |
| Repeticiones | 3 corridas por módulo = **15 llamadas** |
| Costo | US$ 2.55 la ejecución principal (~US$ 2.83 contando el piloto y un intento fallido) |
| Tiempo | 21–186 s por llamada (media 66 s) |

## 4. Prompt v1 (texto exacto)

**Mensaje de sistema** (`llm_pruebas/prompt_v1.md`):

```
Eres un ingeniero de software experto en Python. Tu tarea es refactorizar un módulo del proyecto PySnooper para mejorar su legibilidad y mantenibilidad, sin cambiar su comportamiento.

Reglas:
- El comportamiento observable debe ser idéntico al original.
- No cambies los nombres ni las firmas de las funciones, clases y métodos públicos (los que no empiezan con "_"), porque otros módulos y los tests los usan.
- No agregues funcionalidades nuevas ni dependencias.
- Modifica solo el archivo indicado; el resto del paquete se muestra como contexto de solo lectura.
- Mantén la compatibilidad con las versiones de Python que el proyecto ya soporta.

Formato de respuesta:
1. El archivo completo refactorizado, en un único bloque ```python.
2. Después, una sección "## Refactorizaciones aplicadas" con una lista: tipo de refactorización (según el catálogo de Fowler, por ejemplo Extract Method, Rename Variable, Inline Function...), elementos afectados y motivo.
```

**Mensaje de usuario:** el código completo de los 5 módulos dentro de etiquetas `<archivo ruta="pysnooper/...">…</archivo>`, seguido de la instrucción `Refactoriza el archivo pysnooper/<modulo>.py.`

## 5. Resultados del LLM

- **15/15 corridas preservan el comportamiento** (83 passed en todas). Sin errores de sintaxis, respuestas truncadas, rechazos ni fallback.
- Tamaño de los diffs: `__init__` +7/−5; `pycompat` +34…62; `variables` +68…75; `utils` +100…106; `tracer` +345…347 / −272…278.
- **Determinismo:** las 3 corridas de cada módulo dieron diffs distintos (3/3), pero la **estrategia es muy estable**: casi siempre extrae los mismos bloques y renombra los mismos elementos. Cambian los nombres, los docstrings y el formato.
- **Tipos más usados:** Extract Function/Method (por lejos), Rename Variable/Parameter (solo elementos privados o locales), Replace Magic Literal, Remove Dead Code (imports sin usar), Substitute Algorithm y Consolidate Conditional. **No usó Inline ni Move.**
- **API pública:** verificada con `ast`, ningún nombre público usado por otros módulos o por los tests cambió. Hubo una infracción menor: el parámetro `C` → `subclass` de `WritableStream.__subclasshook__` (2/3 corridas de `utils`), que no rompe nada.
- **Idioma:** todos los identificadores nuevos están en inglés, pero en 2 de 15 corridas el modelo escribió comentarios en español (efecto del prompt en español).

## 6. Fragmentos C1–C6 de `tracer.py` y qué hizo cada herramienta

Líneas referidas al `tracer.py` original.

| ID | Fragmento | Líneas | Rope | LLM run1 | LLM run2 | LLM run3 |
|---|---|---|---|---|---|---|
| C1 | Cálculo del `timestamp` | 468–482 | ❌ prueba 07 (15/68) | `_make_timestamp` | `_make_timestamp` | `_make_timestamp` |
| C2 | Corrección de la definición de función desplazada | 534–549 | ❌ prueba 08 (43/40) | `_find_function_definition` | ídem | ídem |
| C3 | Chequeo "¿debe trazarse esta línea?" | 428–445 | *no probado con Rope* | `_is_within_traced_depth` | `_is_target_frame` + `_has_target_ancestor_within_depth` | `_is_target_frame` + `_is_within_tracing_depth` |
| C4 | Reporte de variables nuevas o modificadas | 518–526 | ❌ prueba 09 (15/68) | `_report_variables` | `_report_variable_changes` | `_report_variable_changes` |
| C5 | Lectura de la fuente vía `loader.get_source` | 85–91 | *no probado con Rope* | `_get_source_from_loader` | ídem | ídem |
| C6 | Lectura de la fuente desde archivo | 121–125 | *no probado con Rope* | `_get_source_from_file_name` | ídem | ídem (+ `_read_source_file`) |

En las 3 corridas, **el LLM extrajo los 6 fragmentos por iniciativa propia**, sin que el prompt los mencionara, y los 83 tests pasan.

**Por qué el LLM logra C1, C2 y C4 y Rope no:**
- **C1 y C4:** el original arma los mensajes con `.format(**locals())`, una dependencia implícita de las variables locales que el análisis estático de Rope no ve. Al mover el bloque, esas variables desaparecen y el formateo falla. El LLM **primero reemplazó los 9 usos de `.format(**locals())` por argumentos explícitos y después extrajo**. Es una cadena de refactorizaciones dependientes.
- **C2:** el bloque modifica dos variables que el llamador usa después (`line_no`, `source_line`). Rope no las devolvía. El LLM devuelve la tupla `(line_no, source_line)`.

Rope aplica una transformación local y sintáctica. El LLM razona sobre las dependencias semánticas.

## 7. Alcance real de la comparación (importante para no sobreafirmar)

| Refactorizaciones de Rope | ¿Comparables con el LLM? | Motivo |
|---|---|---|
| 07, 08, 09, 10 (Extract Method) | ✅ Sí | El LLM extrajo los mismos bloques. Resultado: **LLM 4/4 (12/12 corridas) frente a Rope 1/4** |
| 04 (Rename privado) | ⚠️ Parcial | El LLM podía hacerlo y decidió que no |
| 02, 03, 05, 06 (Rename público), 11 (Inline de función pública) | ❌ No | El prompt prohíbe cambiar la API pública |
| 12 (Move entre archivos) | ❌ No | El prompt prohíbe tocar otros archivos |

Conclusión: con el prompt v1, la comparación directa con Rope **solo es válida para Extract Method**. Sobre Rename, Inline y Move no se puede afirmar nada.

Validación cruzada adicional: el LLM extrajo la selección de clase en `Exploding._items` (`variables.py`). Esa misma extracción hecha con Rope da un método idéntico y pasa los tests. En casos simples, ambos coinciden.

## 8. Discrepancia de diseño pendiente de resolver

En la tesis se describe "una llamada al modelo por fragmento (por ejemplo, la de C1)". **Lo que se ejecutó fue una llamada por módulo completo.** No existe una llamada separada para C1: C1–C6 aparecen dentro de las respuestas de las 3 llamadas de `tracer.py`. Hay dos opciones:
1. **Redactar la tesis según lo ejecutado:** llamada por módulo; C1–C6 se evidencian en la respuesta de `tracer`.
2. **Ejecutar un experimento por fragmento:** prompt general rellenado con el código de cada C, 3 corridas, ~US$ 1–2. También habría que correr Rope sobre C3, C5 y C6, que todavía no se han probado.

Mientras no se decida, **no conviene redactar como si existiera una llamada por fragmento**.

## 9. Limitaciones (para la sección de amenazas a la validez)

1. **Los tests son el único oráculo:** "preserva" significa "pasa los 83 tests", no equivalencia demostrada. Hay ramas sin tests en este entorno: compatibilidad con Python 2 y < 3.6 en `pycompat`, y la obtención de la fuente desde IPython o Ansible en `tracer`. El LLM modificó código en esas ramas.
2. **Cobertura no medible con fiabilidad:** `coverage` reporta 50 %, pero PySnooper usa `sys.settrace`, que interfiere con `coverage` en Python 3.9. Es una cota inferior poco fiable.
3. **Diffs grandes** (~620 líneas en `tracer`): son más difíciles de revisar y de aislar si algo falla.
4. **No hay determinismo**, y no se puede fijar la temperatura en este modelo.
5. **Pocas repeticiones** (3 por módulo): 15/15 no descarta una tasa de error baja.
6. **Un solo modelo y un solo prompt:** no se puede generalizar a "los LLM".
7. **Posible sesgo del prompt:** el formato de salida pone como ejemplo "Extract Method, Rename Variable", que son justamente los dos tipos más usados por el modelo.
8. **La lista de refactorizaciones la escribe el propio modelo;** se verificó contra los diffs y `ast` en los puntos clave, no de forma exhaustiva.
9. **Comparación no simétrica:** Rope ejecutó operaciones elegidas por una persona (incluidos casos límite) y el LLM eligió las suyas.

## 10. Incidencias del proceso (bitácora)

| Incidencia | Efecto | Solución |
|---|---|---|
| El script se cayó en la primera llamada real (`_request_id` no existe en mensajes streaming del SDK 0.125) | Se perdió una respuesta pagada (~US$ 0.14) | Se usa `respuesta.id` |
| Python 3.9 no es compatible con el SDK `anthropic` 1.x | — | Se usó `anthropic<1` (0.125.0) |
| API key duplicada en `~/.zshrc` (la última, pegada dos veces) → error 401 | Retraso | Se dejó una sola línea |
| Falsos positivos al buscar f-strings con texto plano | Error de análisis, corregido | Se repitió con `tokenize`: 0 f-strings |

## 11. Archivos de evidencia

- Ejecución principal: `llm_pruebas/resultados/20261015_174023/` → `resumen.md`, `resumen.json`, y por corrida `<modulo>_run<n>_respuesta.md`, `.py`, `.diff` y `_pytest.txt`.
- Piloto: `llm_pruebas/resultados/20261015_173914/`.
- Rope: `rope_pruebas/resultados/` (`resumen.md` y un `.diff` y `_pytest.txt` por refactorización).
- Todo está versionado en la rama git `tesis/pruebas-llm` (excepto `rope_pruebas/` y `llm_out/`, excluidos localmente).
