```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.

import abc
import re
import traceback

from .pycompat import ABC, string_types, collections_abc


### Abstract stream protocol: #################################################

def _lookup_in_mro(cls, name):
    '''Return the first definition of `name` along the MRO of `cls`, or `None`.'''
    for base in cls.__mro__:
        if name in base.__dict__:
            return base.__dict__[name]
    return None


def _check_methods(cls, *methods):
    '''
    Return `True` if `cls` implements every one of `methods`, otherwise
    `NotImplemented`.

    A method that is missing, or explicitly set to `None`, counts as not
    implemented.
    '''
    for method in methods:
        if _lookup_in_mro(cls, method) is None:
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
    ValueError  # IronPython weirdness.
)


### Text sanitizing: ##########################################################

def _is_latin1_non_nul(char):
    return 0 < ord(char) < 256


def shitcode(s):
    '''Replace every character that is NUL or outside Latin-1 with `?`.'''
    return ''.join(
        char if _is_latin1_non_nul(char) else '?' for char in s
    )


### Reprs: ####################################################################

def _condition_matches(condition, item):
    '''
    A `custom_repr` condition is either a type (matched with `isinstance`) or
    a predicate called with the item.
    '''
    if isinstance(condition, type):
        return isinstance(item, condition)
    return condition(item)


def get_repr_function(item, custom_repr):
    for condition, action in custom_repr:
        if _condition_matches(condition, item):
            return action
    return repr


DEFAULT_REPR_RE = re.compile(r' at 0x[a-f0-9A-F]{4,}')


def normalize_repr(item_repr):
    """Remove memory address (0x...) from a default python repr"""
    return DEFAULT_REPR_RE.sub('', item_repr)


_REPR_FAILED = 'REPR FAILED'


def _safe_repr(item, repr_function):
    try:
        return repr_function(item)
    except Exception:
        return _REPR_FAILED


def _remove_line_breaks(text):
    return text.replace('\r', '').replace('\n', '')


def get_shortish_repr(item, custom_repr=(), max_length=None, normalize=False):
    repr_function = get_repr_function(item, custom_repr)
    item_repr = _remove_line_breaks(_safe_repr(item, repr_function))
    if normalize:
        item_repr = normalize_repr(item_repr)
    if max_length:
        item_repr = truncate(item_repr, max_length)
    return item_repr


_TRUNCATION_MARKER = u'...'


def truncate(string, max_length):
    if (max_length is None) or (len(string) <= max_length):
        return string
    available_length = max_length - len(_TRUNCATION_MARKER)
    left_length = available_length // 2
    right_length = available_length - left_length
    return u'{}{}{}'.format(string[:left_length], _TRUNCATION_MARKER,
                            string[-right_length:])


### Exceptions: ###############################################################

def _is_exception_group(exc_value):
    try:
        exception_group_type = BaseExceptionGroup
    except NameError:  # `BaseExceptionGroup` only exists in Python 3.11+.
        return False
    return isinstance(exc_value, exception_group_type)


def _format_exception_group(exc_type, exc_group):
    sub_exceptions = exc_group.exceptions
    sub_types = ', '.join(type(e).__name__ for e in sub_exceptions)
    message = exc_group.args[0] if exc_group.args else ''
    return u"{}: '{}' ({} sub-exceptions: {})".format(
        exc_type.__name__, message, len(sub_exceptions), sub_types,
    )


def _format_single_exception(exc_type, exc_value):
    return u'\n'.join(
        traceback.format_exception_only(exc_type, exc_value)
    ).strip()


def format_exception(exc_type, exc_value):
    if _is_exception_group(exc_value):
        return _format_exception_group(exc_type, exc_value)
    return _format_single_exception(exc_type, exc_value)


### Misc: #####################################################################

def _is_non_string_iterable(x):
    return (isinstance(x, collections_abc.Iterable) and
            not isinstance(x, string_types))


def ensure_tuple(x):
    if _is_non_string_iterable(x):
        return tuple(x)
    return (x,)
```

## Refactorizaciones aplicadas

- **Extract Function** (`_lookup_in_mro`) y **Rename Variable** (`C` → `cls`, `B` → `base`) en `_check_methods`.
  - Motivo: el bucle anidado con `for ... else` y dos salidas `NotImplemented` era difícil de seguir.
  - Ahora la búsqueda en el MRO está aislada. Tanto "no encontrado" como "definido como `None`" devuelven `None`, y ambos casos producían `NotImplemented` en el original, así que la semántica se conserva.
- **Rename Parameter** (`C` → `subclass`) en `WritableStream.__subclasshook__`.
  - Motivo: el nombre de una sola letra en mayúscula no comunicaba su rol.
  - `ABCMeta` invoca el hook de forma posicional, así que la firma efectiva no cambia.
- **Extract Function** (`_is_latin1_non_nul`) y **Rename Variable** (`c` → `char`) en `shitcode`.
  - Motivo: dar nombre a la condición `0 < ord(c) < 256`.
  - Se añadió un docstring que explica qué hace la función, sin cambiar su nombre público.
- **Replace Lambda with Function / Decompose Conditional** (`_condition_matches`) en `get_repr_function`.
  - Motivo: el original reasignaba `condition` con una lambda que usaba un argumento por defecto (`y=condition`), un truco poco evidente.
  - La nueva función hace explícitas las dos formas de condición (tipo o predicado), con el mismo resultado y las mismas excepciones propagadas.
- **Extract Function** (`_safe_repr`, `_remove_line_breaks`) y **Rename Variable** (`r` → `item_repr`) en `get_shortish_repr`.
  - Motivo: separar los pasos del pipeline de repr y dar nombres descriptivos.
  - Se mantiene `get_repr_function` fuera del `try`, como en el original. También se mantiene el chequeo `if max_length:`, que trata `0` como "sin truncar".
- **Replace Magic Literal with Symbolic Constant** (`_REPR_FAILED`, `_TRUNCATION_MARKER`).
  - Motivo: nombrar los literales `'REPR FAILED'` y `'...'`.
  - En `truncate`, el `3` mágico pasa a derivarse de `len(_TRUNCATION_MARKER)`.
- **Rename Variable** (`left`/`right` → `left_length`/`right_length`, nueva `available_length`) y **Remove Redundant Else** en `truncate`.
  - Motivo: hacer explícito el cálculo del espacio disponible.
  - Las expresiones de slicing son las mismas, así que se preservan incluso los casos límite (por ejemplo, `max_length <= 3`).
- **Extract Function** (`_is_exception_group`, `_format_exception_group`, `_format_single_exception`) en `format_exception`.
  - Motivo: separar la detección de compatibilidad (`BaseExceptionGroup` solo existe en Python 3.11+) del formateo de cada caso.
  - `format_exception` queda como un simple despachador.
  - También se aplica **Extract Variable** (`sub_exceptions`) para no acceder dos veces a `.exceptions`.
- **Extract Function** (`_is_non_string_iterable`) y **Remove Redundant Else** en `ensure_tuple`.
  - Motivo: nombrar la condición en lugar de partirla con una barra invertida y una indentación forzada.
- **Remove Dead Code** (`import sys`).
  - Motivo: el import no se usaba en el módulo y ningún otro módulo accede a `utils.sys`.
- **Agrupación del código en secciones y limpieza de líneas en blanco** (PEP 8).
  - Motivo: mejorar la navegación del archivo. Se usan comentarios de sección con el mismo estilo que `tracer.py`.
  - No se usan f-strings ni sintaxis exclusiva de Python 3, para mantener la compatibilidad con Python 2 que el proyecto conserva vía `pycompat`.