```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.

import abc
import re
import traceback

from .pycompat import ABC, string_types, collections_abc


### Protocolo de streams escribibles: #########################################

def _is_method_implemented(mro, method_name):
    '''
    Indica si `method_name` está implementado en alguna clase de `mro`.

    Se busca la primera clase del MRO que defina el nombre. Si esa definición
    es `None`, el método se considera bloqueado explícitamente y, por lo
    tanto, no implementado.
    '''
    for klass in mro:
        if method_name in klass.__dict__:
            return klass.__dict__[method_name] is not None
    return False


def _check_methods(cls, *method_names):
    mro = cls.__mro__
    for method_name in method_names:
        if not _is_method_implemented(mro, method_name):
            return NotImplemented
    return True


class WritableStream(ABC):
    @abc.abstractmethod
    def write(self, s):
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is WritableStream:
            return _check_methods(subclass, 'write')
        return NotImplemented


file_reading_errors = (
    IOError,
    OSError,
    ValueError # IronPython weirdness.
)


### Saneamiento de texto: #####################################################

_REPLACEMENT_CHARACTER = '?'


def _is_safe_character(character):
    '''Si el carácter es no nulo y cabe en un solo byte (rango Latin-1).'''
    return 0 < ord(character) < 256


def shitcode(s):
    return ''.join(
        character if _is_safe_character(character) else _REPLACEMENT_CHARACTER
        for character in s
    )


### Representación de valores: ################################################

_REPR_FAILED_MESSAGE = 'REPR FAILED'

DEFAULT_REPR_RE = re.compile(r' at 0x[a-f0-9A-F]{4,}')


def _matches_condition(condition, item):
    '''
    Evalúa una condición de `custom_repr`: puede ser un tipo (se comprueba
    con `isinstance`) o un predicado invocable.
    '''
    if isinstance(condition, type):
        return isinstance(item, condition)
    return condition(item)


def get_repr_function(item, custom_repr):
    for condition, action in custom_repr:
        if _matches_condition(condition, item):
            return action
    return repr


def _safe_repr(repr_function, item):
    try:
        return repr_function(item)
    except Exception:
        return _REPR_FAILED_MESSAGE


def _remove_line_breaks(text):
    return text.replace('\r', '').replace('\n', '')


def normalize_repr(item_repr):
    """Remove memory address (0x...) from a default python repr"""
    return DEFAULT_REPR_RE.sub('', item_repr)


def get_shortish_repr(item, custom_repr=(), max_length=None, normalize=False):
    repr_function = get_repr_function(item, custom_repr)
    item_repr = _remove_line_breaks(_safe_repr(repr_function, item))
    if normalize:
        item_repr = normalize_repr(item_repr)
    if max_length:
        item_repr = truncate(item_repr, max_length)
    return item_repr


_ELLIPSIS = u'...'


def truncate(string, max_length):
    if (max_length is None) or (len(string) <= max_length):
        return string
    visible_length = max_length - len(_ELLIPSIS)
    head_length = visible_length // 2
    tail_length = visible_length - head_length
    return u'{}{}{}'.format(string[:head_length], _ELLIPSIS,
                            string[-tail_length:])


### Formateo de excepciones: ##################################################

def _is_exception_group(exc_value):
    # `BaseExceptionGroup` solo existe a partir de Python 3.11.
    try:
        return isinstance(exc_value, BaseExceptionGroup)
    except NameError:
        return False


def _format_exception_group(exc_type, exc_value):
    sub_exceptions = exc_value.exceptions
    sub_type_names = ', '.join(type(e).__name__ for e in sub_exceptions)
    message = exc_value.args[0] if exc_value.args else ''
    return u"{}: '{}' ({} sub-exceptions: {})".format(
        exc_type.__name__, message, len(sub_exceptions), sub_type_names,
    )


def format_exception(exc_type, exc_value):
    if _is_exception_group(exc_value):
        return _format_exception_group(exc_type, exc_value)
    exception_lines = traceback.format_exception_only(exc_type, exc_value)
    return u'\n'.join(exception_lines).strip()


### Utilidades de colecciones: ################################################

def _is_non_string_iterable(x):
    return (isinstance(x, collections_abc.Iterable) and
            not isinstance(x, string_types))


def ensure_tuple(x):
    if _is_non_string_iterable(x):
        return tuple(x)
    return (x,)
```

## Refactorizaciones aplicadas

- **Extract Function** + **Replace Nested Conditional with Guard Clauses / Replace Control Flag**
  - *Elementos:* `_check_methods` → nueva `_is_method_implemented(mro, method_name)`.
  - *Motivo:* el doble bucle con `for … else` y `break` era difícil de seguir. Ahora la búsqueda de un método en el MRO es una función con nombre propio, que devuelve un booleano. El MRO se sigue leyendo una sola vez, como antes.

- **Rename Variable / Rename Parameter**
  - *Elementos:*
    - `C` → `cls` en `_check_methods`;
    - `C` → `subclass` en `WritableStream.__subclasshook__`, igual que en `pycompat.PathLike`;
    - `methods` → `method_names` y `B` → `klass`;
    - `r` → `item_repr` en `get_shortish_repr`;
    - `left`/`right` → `head_length`/`tail_length` en `truncate`;
    - `sub_types` → `sub_type_names`.
  - *Motivo:* los nombres de una letra o genéricos no comunicaban qué contenían. Ninguno forma parte de la API pública: son parámetros privados o del hook invocado posicionalmente por `ABCMeta`.

- **Replace Lambda with Function** / **Extract Function**
  - *Elementos:* `get_repr_function` → `_matches_condition(condition, item)`.
  - *Motivo:* la lambda con argumento por defecto (`y=condition`) era un truco para capturar la variable del bucle. La nueva función expresa directamente las dos formas de condición admitidas: un tipo o un predicado. El resultado es el mismo.

- **Extract Function**
  - *Elementos:* `get_shortish_repr` → `_safe_repr` y `_remove_line_breaks`.
  - *Motivo:* separar el `try/except` y la limpieza de saltos de línea deja el cuerpo principal como una secuencia lineal de transformaciones.

- **Extract Function**
  - *Elementos:* `format_exception` → `_is_exception_group` y `_format_exception_group`.
  - *Motivo:*
    - Aísla el detalle de compatibilidad: `BaseExceptionGroup` solo existe desde Python 3.11. La comprobación se sigue haciendo en cada llamada, como en el original.
    - Separa el formato específico de los grupos de excepciones del caso general.

- **Extract Function** + **Decompose Conditional**
  - *Elementos:*
    - `ensure_tuple` → `_is_non_string_iterable`;
    - `shitcode` → `_is_safe_character`.
  - *Motivo:*
    - En `ensure_tuple`, la condición ocupaba dos líneas con una continuación `\` poco legible. Ahora tiene un nombre que explica su intención.
    - En `shitcode`, el rango `0 < ord(c) < 256` pasa a tener un nombre descriptivo.

- **Replace Magic Literal with Symbolic Constant**
  - *Elementos:* `_REPR_FAILED_MESSAGE`, `_ELLIPSIS`, `_REPLACEMENT_CHARACTER`.
  - *Motivo:*
    - Da nombre a valores literales repetidos o con significado implícito.
    - En `truncate`, el `3` mágico pasa a ser `len(_ELLIPSIS)`, con la misma aritmética exacta. Esto incluye los casos límite con `max_length` pequeño.
    - `_ELLIPSIS` es `u'...'`, lo que conserva el resultado `unicode` en Python 2.

- **Remove Dead Code**
  - *Elementos:* `import sys`, que no se usaba.
  - *Motivo:* las importaciones sin uso confunden sobre las dependencias reales del módulo. Ningún otro módulo del paquete accede a `utils.sys`.

- **Consolidate Conditional / Remove Redundant Else**
  - *Elementos:* ramas `else` tras `return` en `truncate` y `ensure_tuple`.
  - *Motivo:* reducir el anidamiento sin alterar el flujo.

- **Reorganización en secciones** (cambio de formato, no una refactorización de Fowler)
  - *Elementos:* el módulo se agrupa en bloques comentados: protocolo de streams, saneamiento de texto, representación de valores, formateo de excepciones y colecciones.
  - *Motivo:* mantiene el estilo de comentarios de bloque que ya usa `tracer.py` y facilita la navegación.

Todos los nombres públicos se conservan con sus firmas intactas: `WritableStream`, `file_reading_errors`, `shitcode`, `get_repr_function`, `DEFAULT_REPR_RE`, `normalize_repr`, `get_shortish_repr`, `truncate`, `format_exception` y `ensure_tuple`.