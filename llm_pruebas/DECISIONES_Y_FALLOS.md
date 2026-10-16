# Decisiones de diseño, lógica del prompt y fallos encontrados

Este documento complementa a [`README.md`](README.md). Reúne **por qué** se diseñó así el experimento con el LLM, **qué consecuencias** tuvo cada decisión y **todos los problemas** encontrados en el proceso (técnicos, metodológicos y de análisis). Cada punto indica qué pasó, por qué importa y qué se hizo o se propone.

---

## 1. Cómo se compara con Rope (alcance real)

Rope y el LLM no reciben la misma tarea:

- **Rope:** una persona elige 11 refactorizaciones concretas (qué elemento, qué operación, qué nombre nuevo) y Rope las ejecuta.
- **LLM:** recibe un **prompt general** ("refactoriza este módulo sin cambiar el comportamiento") y decide qué hacer.

Esta decisión de diseño fue explícita: no se le da al LLM la instrucción exacta, para observar qué refactorizaciones elige por su cuenta. La consecuencia es que **la comparación 1 a 1 solo es posible donde ambos hicieron la misma operación sobre el mismo código**.

Matriz completa en [README §5.2](README.md#52-matriz-completa-qué-hizo-el-llm-con-cada-refactorización-de-rope). En resumen:

| Grupo | Refactorizaciones de Rope | Estado de la comparación |
|---|---|---|
| **Comparables** | 07, 08, 09, 10 (Extract Method) | ✅ LLM 4/4 frente a Rope 1/4 |
| El LLM podía, pero no quiso | 04 (Rename de un método privado) | ⚠️ Solo se puede decir que no lo eligió |
| **Bloqueadas por el prompt** | 02, 03, 05, 06 (Rename público), 11 (Inline de función pública), 12 (Move entre archivos) | ❌ No medidas |

Así que **sí: por ahora la comparación directa es solo de Extract Method.** No fue un fallo del modelo, sino una consecuencia de las reglas del prompt (sección 2). La sección 5 propone cómo ampliarla.

Hay tres formas complementarias de comparar, y conviene distinguirlas en la tesis:

1. **Comparación por caso (1 a 1):** misma operación, mismo bloque y se compara el resultado de los tests. Es la más fuerte, pero hoy solo cubre Extract Method.
2. **Validación cruzada:** se toma una refactorización que eligió el LLM y se reproduce con Rope. Se hizo con `Exploding._items` (README §5.3) y salió idéntica. Se puede extender a más casos sin gastar en la API.
3. **Comparación agregada:** tasa de preservación, tipos de refactorización, tamaño del diff, determinismo, tiempo y costo (README §5.4). Es útil, pero mezcla tareas distintas, así que no sirve para afirmar que uno sea "mejor" en un tipo concreto.

---

## 2. Lógica del prompt (`prompt_v1.md`), regla por regla

| Elemento del prompt | Por qué se incluyó | Efecto observado | Consecuencia para la tesis |
|---|---|---|---|
| "Eres un ingeniero de software experto en Python" | Rol estándar para orientar el estilo de la respuesta | — | Neutro |
| "Mejorar legibilidad y mantenibilidad, sin cambiar su comportamiento" | Es la definición misma de refactorización: el objetivo es general, no una operación concreta | El modelo eligió sobre todo Extract Function/Method y Rename de elementos locales | Esta es la variable que se estudia |
| "El comportamiento observable debe ser idéntico" | Refuerza la restricción principal | 15/15 corridas preservan. En `tracer` el modelo detectó la dependencia de `.format(**locals())` antes de extraer | Probablemente ayudó a que el modelo fuera cuidadoso. No se aisló su efecto |
| "No cambies nombres ni firmas públicas" | Sin esta regla, si el modelo solo ve un archivo y renombra algo público, los tests fallan por imports rotos y no por una mala refactorización. Esa mezcla contaminaría el resultado | Se respetó en todos los nombres usados por otros módulos. Hubo **1 infracción menor**: el parámetro `C` → `subclass` de `__subclasshook__` (2/3 corridas de `utils`) | **Bloquea las comparaciones de Rename (02, 03, 05, 06) e Inline (11)** |
| "No agregues funcionalidades ni dependencias" | Evitar que el modelo "mejore" el programa en lugar de refactorizarlo | Sin funcionalidades nuevas. Sí agregó docstrings, comentarios y constantes, que no cambian el comportamiento | El diff incluye cambios cosméticos que inflan su tamaño |
| "Modifica solo el archivo indicado; el resto es solo lectura" | Mantener la unidad de análisis por módulo y diffs atribuibles a un archivo | Se respetó | **Bloquea la comparación de Move (12)** y de cualquier refactorización entre módulos |
| "Mantén la compatibilidad con las versiones de Python soportadas" | PySnooper aún tiene código para Python 2 (`pycompat`) | No usó f-strings ni sintaxis moderna | La regla es **vaga**: no dice qué versiones. No se puede verificar en este entorno (solo Python 3.9) |
| Contexto: los 5 módulos completos | El modelo necesita ver qué usan los otros módulos para no romper nada | Ninguna corrida rompió imports internos | Los **tests no se incluyeron** como contexto: el modelo no sabe qué nombres importan los tests. Funcionó gracias a la regla de API pública |
| Formato: archivo completo en un bloque ```python | Más fiable que pedir un diff: los LLM suelen generar parches que no aplican, y eso mezclaría dos tipos de fallo | 15/15 respuestas con un bloque extraíble | Sin fallos de formato |
| Formato: lista "## Refactorizaciones aplicadas" según Fowler | Para obtener la clasificación del propio modelo y contrastarla con el diff | Listas detalladas en las 15 corridas | El ejemplo **"Extract Method, Rename Variable, Inline Function..."** puede **sesgar** al modelo hacia esos tipos (ver 4.1) |
| Instrucción final: "Refactoriza el archivo `pysnooper/<modulo>.py`." | Mínima, para no dar pistas | — | — |

Parámetros de la llamada (no forman parte del texto, pero también son decisiones):

| Parámetro | Valor | Motivo |
|---|---|---|
| Modelo | `claude-opus-5-5` | Modelo por defecto y más capaz de la línea Opus en la fecha del experimento |
| Effort | `high` | El nivel por defecto de Opus 5.5 es `medium`, y se fijó de forma explícita para que sea reproducible. `high` es el nivel recomendado como mínimo para tareas de código |
| Temperatura | (no se envía) | Opus 5.5 **no permite** fijarla: la API rechaza el parámetro. Por eso se hicieron 3 corridas |
| Fallback de refusals | Activado (`fallbacks: "default"`) | Si el modelo rechazaba la petición, otro modelo respondería. Se registra el modelo que respondió: en las 15 corridas fue `claude-opus-5-5`, así que no hubo contaminación |
| Caché de prompts | Sobre el contexto | El contexto es idéntico en todas las llamadas. Esto reduce el costo y no afecta la respuesta |

---

## 3. Fallos y problemas encontrados

### 3.1 Fallos de Rope (contexto)

Las 3 refactorizaciones de Rope que fallaron son Extract Method sobre `Tracer.trace`:

| # | Causa del fallo | Cómo lo resolvió el LLM |
|---|---|---|
| 07 `_make_timestamp` | Las variables calculadas en el bloque se usaban después dentro de `.format(**locals())`, una dependencia invisible para el análisis estático | Primero reemplazó todos los `.format(**locals())` por argumentos explícitos y después extrajo el método |
| 08 `_skip_decorator_lines` | El bloque modifica **dos** variables que el llamador usa después (`line_no` y `source_line`); el método extraído no las devolvía | La función extraída devuelve la tupla `(line_no, source_line)` |
| 09 `_report_variables` | El bloque usa `.format(**locals())`: al moverlo, las variables locales que la plantilla necesita ya no existen | Igual que en 07: dependencias explícitas y después la extracción |

Rope hace una transformación **local y sintáctica**. El LLM hizo una **cadena de refactorizaciones dependientes** (primero hacer explícitas las dependencias, después extraer). Es el hallazgo central del experimento.

### 3.2 Fallos técnicos del proceso

| # | Problema | Causa | Impacto | Solución |
|---|---|---|---|---|
| T1 | Primera llamada real a la API: el script se cayó **después** de recibir la respuesta (`AttributeError: '_request_id'`) | En el SDK `anthropic` 0.125, los mensajes en streaming (`ParsedBetaMessage`) no tienen el atributo `_request_id` | Se perdió una respuesta pagada (~US$ 0.14). No afecta a los resultados | Se registra `respuesta.id` en su lugar. **Lección:** guardar la respuesta cruda antes de procesar metadatos |
| T2 | Python 3.9.6 incompatible con el SDK `anthropic` 1.x | El SDK 1.x requiere Python ≥ 3.10 | Ninguno | Se usa `anthropic<1` (0.125.0), que soporta todos los parámetros necesarios |
| T3 | La API key respondía `401 invalid x-api-key` | La key quedó dos veces en `~/.zshrc`; la última línea contenía la key **pegada dos veces seguidas** (212 caracteres = 2 × 106), y como gana el último `export`, esa era la activa | Bloqueó la ejecución hasta corregirlo | Se dejó una sola línea. Verificación sin exponer la key: largo de la variable + llamada gratuita a `models.retrieve` |
| T4 | `coverage` mide 50 % de cobertura, un número poco fiable | PySnooper usa `sys.settrace`, el mismo mecanismo que usa `coverage` en Python 3.9; mientras PySnooper rastrea, `coverage` deja de registrar | No se puede dar una cifra de cobertura confiable | Se reporta como cota inferior, con la advertencia. Alternativa: medir en Python ≥ 3.12 (allí `coverage` usa `sys.monitoring`) |

### 3.3 Fallos y riesgos metodológicos

| # | Problema | Por qué importa | Mitigación |
|---|---|---|---|
| M1 | **La comparación 1 a 1 solo cubre Extract Method** (sección 1) | No se puede afirmar nada sobre Rename, Inline o Move del LLM frente a Rope | `prompt_v2` (sección 5) |
| M2 | **Los tests son el único oráculo** y no cubren todas las ramas (Python 2, < 3.6, IPython, Ansible) | El LLM cambió código en esas ramas (por ejemplo `getattr(inspect, ..., default)` en `pycompat` y la descomposición de `get_path_and_source_from_frame`). "15/15 preservan" significa "15/15 pasan los tests", no equivalencia demostrada | Revisión manual de esas ramas, o tests nuevos para ellas |
| M3 | **Diffs grandes**: hasta ~620 líneas en `tracer` | Si algo fallara sería difícil aislar la causa. Revisar el resultado cuesta mucho más que con Rope | Opción: pedir una sola refactorización por respuesta, o aplicarlas de a una |
| M4 | **No hay determinismo** (3/3 diffs distintos en todos los módulos) | Un mismo prompt no da el mismo código | Se mide la estabilidad de la *estrategia* (README §4.3), que resultó alta |
| M5 | **Pocas corridas** (3 por módulo) | 15/15 no descarta una tasa de error baja | Subir a 5–10 corridas (`--corridas`) |
| M6 | **La lista de refactorizaciones la escribe el propio modelo** | Podría describir mal lo que hizo | Se contrastó con los diffs y con `ast` en los puntos clave. Para automatizarlo: PyRef |
| M7 | **Un solo modelo y un solo prompt** | Los resultados no generalizan a "los LLM" | Repetir con otros modelos o proveedores |
| M8 | **Infracción menor de la regla de API** (`C` → `subclass`) | Muestra que el modelo no cumple las restricciones al 100 % aunque estén escritas | Se reporta como hallazgo. No rompe nada porque Python llama a ese método de forma posicional |

### 3.4 Problemas en el análisis

| # | Problema | Solución |
|---|---|---|
| A1 | La primera búsqueda de f-strings (buscar `f"` / `f'` en el texto) dio **falsos positivos** en `tracer` y `pycompat` (coincidía con palabras que terminan en "f" seguidas de comillas) | Se repitió con `tokenize`, analizando tokens de tipo cadena: **0 f-strings reales** |
| A2 | La comparación de la API con `ast` mostró nombres "nuevos" en `pycompat` (`iscoroutinefunction`, `isasyncgenfunction`) y `variables` (`Mapping`, `Sequence`) | No son nombres nuevos: en el original se definían dentro de `try/except`, que el análisis no recorría, y el LLM los pasó a asignaciones de nivel superior. Es un artefacto del análisis, no un cambio de API |
| A3 | El veredicto del script compara solo los conteos de pytest | Correcto para este oráculo, pero no detecta cambios en la *salida* de PySnooper que los tests no verifican (ver M2) |

---

## 4. Posibles sesgos del prompt

### 4.1 Ejemplos de Fowler en el formato de salida
El prompt dice: *"tipo de refactorización (según el catálogo de Fowler, por ejemplo Extract Method, Rename Variable, Inline Function...)"*. Los dos tipos más frecuentes en los resultados son justamente **Extract Method/Function y Rename Variable**. Puede ser coincidencia (son los más comunes en general), pero **no se puede descartar** que los ejemplos hayan orientado al modelo. Curiosamente, Inline Function aparece en el ejemplo y el modelo no la usó (la regla de API pública la impide en `normalize_repr`).

**Propuesta:** `prompt_v2` sin ejemplos ("tipo de refactorización según el catálogo de Fowler"), y comparar la distribución de tipos entre v1 y v2.

### 4.2 "Sin cambiar el comportamiento" repetido
Que el prompt insista en el comportamiento probablemente vuelve al modelo más conservador. Es deseable para refactorizar, pero significa que los resultados dependen de esa redacción.

### 4.3 Idioma
El prompt está en español y el código en inglés. En la salida manual previa (`llm_out/CAL1_variables.py`) el modelo usó un nombre en español (`elegir_clase`). En las 15 corridas con `prompt_v1`, **todos los identificadores nuevos (funciones, métodos, constantes) están en inglés**, coherentes con el código. Pero **en 2 de 15 corridas el modelo escribió comentarios en español** dentro de código cuyos comentarios están en inglés:
- `__init___run1.py`, líneas 31–32: "Los nombres auxiliares solo hacen falta…"
- `variables_run1.py`, línea 13: "Se mantienen los nombres a nivel de módulo."

El piloto (`20261015_173914`) tiene el mismo efecto. Es una inconsistencia de estilo, no de comportamiento, y es atribuible al idioma del prompt. **Propuesta:** en `prompt_v2`, agregar "mantén el idioma y el estilo de los comentarios existentes" o escribir el prompt en inglés.

---

## 5. Propuesta para ampliar la comparación (`prompt_v2`)

Para medir Rename, Inline y Move frente a Rope sin abandonar el enfoque de prompt general:

| Cambio respecto a v1 | Qué habilita |
|---|---|
| Quitar la regla "no cambies nombres públicos" | Rename de funciones, clases y parámetros públicos (02, 03, 05, 06), e Inline de funciones públicas (11) |
| Permitir modificar **cualquier archivo** del proyecto, **incluidos los tests**, y devolver todos los archivos modificados | Move entre módulos (12) y actualizar todos los usos de un nombre renombrado, como hace Rope |
| Incluir los tests como contexto | El modelo sabe qué nombres usan los tests y puede actualizarlos |
| Quitar los ejemplos de Fowler del formato | Elimina el sesgo de 4.1 |
| Pedir que respete el idioma y el estilo de los comentarios existentes | Evita los comentarios en español de 4.3 |

Con v2, la unidad de trabajo pasa a ser **el proyecto completo**, no un módulo. Habría que ajustar el script para que acepte varios archivos en la respuesta (por ejemplo con delimitadores `### FILE: ruta`).

Los resultados de v1 y v2 se reportarían por separado. v1 mide al LLM con restricciones de API, como en un uso real dentro de una librería publicada. v2 lo mide con la misma libertad que tuvo Rope.

**Costo estimado de v2:** el contexto es mayor (paquete + tests), pero son menos llamadas (1 por corrida en lugar de 5). Con 3–5 corridas, unos US$ 2–5.

---

## 6. Bitácora de ejecuciones

| Fecha | Carpeta | Qué fue | Resultado | Costo |
|---|---|---|---|---|
| 2026-10-05 | `llm_out/CAL1_variables.py` | Prueba manual previa (fuera del script), solo `variables.py` | 1 Extract Method (`elegir_clase`), 83 passed. Rope reproduce el mismo método | — |
| 2026-10-15 | — | Primer intento real: el script se cayó (T1) | Respuesta perdida | ~US$ 0.14 |
| 2026-10-15 | `resultados/20261015_173914/` | Piloto: `variables`, 1 corrida | Preserva; 9 refactorizaciones | US$ 0.14 |
| 2026-10-15 | `resultados/20261015_174023/` | **Ejecución principal**: 5 módulos × 3 corridas | 15/15 preservan | US$ 2.55 |
