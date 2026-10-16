```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.

import abc
import re
import traceback

from .pycompat import ABC, string_types, collections_abc


def _find_defining_class(cls, method_name):
    '''Return the first class in `cls.__mro__` that defines `method_name`.

    Return `None` if no class in the MRO defines it.
    '''
    for base in cls.__mro__:
        if method_name in base.__dict__:
            return base
    return None


def _check_methods(C, *methods):
    '''Check that `C` implements every method in `methods`.

    A method counts as not implemented if no class in the MRO defines it, or
    if the first class that defines it sets it to `None`.
    '''
    for method_name in methods:
        defining_class = _find_defining_class(C, method_name)
        if defining_class is None or \
                                  defining_class.__dict__[method_name] is None:
            return NotImplemented
    return True


class WritableStream(ABC):
    @abc.abstractmethod
    def write(self, s):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is WritableStream:
            return _check_methods(C, 'write')
        return NotImplemented


file_reading_errors = (
    IOError,
    OSError,
    ValueError # IronPython weirdness.
)


_REPLACEMENT_CHAR = '?'


def _is_safe_char(char):
    '''Whether `char` is a non-null Latin-1 character.'''
    return 0 < ord(char) < 256


def shitcode(s):
    return ''.join(
        char if _is_safe_char(char) else _REPLACEMENT_CHAR for char in s
    )


def _matches_condition(condition, item):
    '''Whether `item` satisfies a `custom_repr` condition.

    The condition can be a type (checked with `isinstance`) or a predicate.
    '''
    if isinstance(condition, type):
        return isinstance(item, condition)
    return condition(item)


def get_repr_function(item, custom_repr):
    for condition, action in custom_repr:
        if _matches_condition(condition, item):
            return action
    return repr


DEFAULT_REPR_RE = re.compile(r' at 0x[a-f0-9A-F]{4,}')


def normalize_repr(item_repr):
    """Remove memory address (0x...) from a default python repr"""
    return DEFAULT_REPR_RE.sub('', item_repr)


_REPR_FAILED_MESSAGE = 'REPR FAILED'


def _safe_repr(repr_function, item):
    '''Call `repr_function` on `item`, never letting an exception escape.'''
    try:
        return repr_function(item)
    except Exception:
        return _REPR_FAILED_MESSAGE


def _remove_line_breaks(string):
    return string.replace('\r', '').replace('\n', '')


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
    available_length = max_length - len(_ELLIPSIS)
    left_length = available_length // 2
    right_length = available_length - left_length
    return u'{}{}{}'.format(string[:left_length], _ELLIPSIS,
                            string[-right_length:])


def _is_exception_group(exc_value):
    '''Whether `exc_value` is an exception group.

    `BaseExceptionGroup` only exists in Python 3.11+, so on older versions
    this always returns `False`.
    '''
    try:
        return isinstance(exc_value, BaseExceptionGroup)
    except NameError:
        return False


def _format_exception_group(exc_type, exc_value):
    sub_exceptions = exc_value.exceptions
    sub_types = ', '.join(type(e).__name__ for e in sub_exceptions)
    message = exc_value.args[0] if exc_value.args else ''
    return u"{}: '{}' ({} sub-exceptions: {})".format(
        exc_type.__name__, message, len(sub_exceptions), sub_types,
    )


def format_exception(exc_type, exc_value):
    if _is_exception_group(exc_value):
        return _format_exception_group(exc_type, exc_value)
    return u'\n'.join(
        traceback.format_exception_only(exc_type, exc_value)
    ).strip()


def _is_non_string_iterable(x):
    return isinstance(x, collections_abc.Iterable) and \
                                               not isinstance(x, string_types)


def ensure_tuple(x):
    if _is_non_string_iterable(x):
        return tuple(x)
    return (x,)
```

## Refactorizaciones aplicadas

- **Extract Function** (`_find_defining_class`, usada desde `_check_methods`).
  - Antes, `_check_methods` tenía dos bucles anidados con un `for ... else` y un `break` que costaban de seguir.
  - Ahora la búsqueda del método en el MRO tiene nombre propio. `_check_methods` queda en una única condición: que no haya clase que lo defina, o que la clase que lo define lo ponga a `None`. Ambos casos devuelven `NotImplemented` igual que antes.

- **Rename Variable** (variables internas de `_check_methods`: `B` → `defining_class`, `method` → `method_name`).
  - Los nombres de una letra ocultaban su significado.
  - Se mantuvo el parámetro `C` de `_check_methods` y de `WritableStream.__subclasshook__` para no alterar firmas.

- **Extract Function + Replace Magic Literal with Symbolic Constant** (`_is_safe_char`, `_REPLACEMENT_CHAR` en `shitcode`).
  - La condición `0 < ord(c) < 256` ahora expresa su intención: es un carácter Latin-1 no nulo.
  - El `'?'` pasa a tener nombre.

- **Extract Function / Substitute Algorithm** (`_matches_condition`, usada desde `get_repr_function`).
  - Sustituye el truco de la `lambda` con argumento por defecto (`lambda x, y=condition: ...`), que reasignaba la variable del bucle, por una función explícita.
  - El resultado es equivalente: `isinstance` si la condición es un tipo y, si no, llamada al predicado.

- **Extract Function** (`_safe_repr` y `_remove_line_breaks`, usadas desde `get_shortish_repr`).
  - Separa la protección ante `repr` fallidos y la limpieza de saltos de línea del flujo principal.
  - Se conserva el orden original: repr → quitar saltos → normalizar → truncar.
  - Se conserva el `if max_length:` original, que no trunca con `0`.

- **Rename Variable** (`r` → `item_repr` en `get_shortish_repr`), para dar un nombre descriptivo al valor que se va transformando.

- **Replace Magic Literal with Symbolic Constant** (`_REPR_FAILED_MESSAGE`), para dar nombre al texto de fallback.

- **Replace Magic Literal with Symbolic Constant + Rename Variable** (`_ELLIPSIS`, `left`/`right` → `left_length`/`right_length` en `truncate`).
  - El `3` mágico se deriva ahora de `len(_ELLIPSIS)`.
  - La aritmética y el slicing `string[-right_length:]` se mantienen idénticos. Esto incluye el caso límite `max_length == 3`, cuyo comportamiento original se conserva.
  - También se eliminó el `else` innecesario tras el `return`.

- **Extract Function** (`_is_exception_group` y `_format_exception_group`, usadas desde `format_exception`).
  - Aísla la detección compatible con versiones antiguas de Python. Se mantiene la búsqueda de `BaseExceptionGroup` en tiempo de llamada, que lanza `NameError` antes de 3.11.
  - Aísla también el formateo específico de grupos, de modo que `format_exception` muestra solo la decisión entre ambos caminos.

- **Decompose Conditional** (`_is_non_string_iterable`, usada desde `ensure_tuple`).
  - La condición compuesta ahora tiene un nombre que explica por qué los strings se tratan como valores escalares.
  - Se eliminó el `else` redundante.

- **Remove Dead Code** (`import sys`).
  - Era una importación no utilizada en el módulo y ningún otro módulo del paquete accede a `utils.sys`.
  - También se normalizaron las líneas en blanco sobrantes entre definiciones y al final del archivo.