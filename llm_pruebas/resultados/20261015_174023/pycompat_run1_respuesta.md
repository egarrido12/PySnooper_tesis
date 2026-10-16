```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.
'''Python 2/3 compatibility'''

import abc
import os
import inspect
import sys
import datetime as datetime_module


###############################################################################
# Interpreter version flags
###############################################################################

PY3 = (sys.version_info[0] == 3)
PY2 = not PY3


###############################################################################
# Abstract base classes
###############################################################################

if hasattr(abc, 'ABC'):
    ABC = abc.ABC
else:
    class ABC(object):
        """Helper class that provides a standard way to create an ABC using
        inheritance.
        """
        __metaclass__ = abc.ABCMeta
        __slots__ = ()


def _looks_like_path_class(cls):
    """Whether `cls` implements the file system path protocol.

    Makes a concession for older `pathlib` versions, whose path classes don't
    define `__fspath__` but do have an `open` method and "path" in their name.
    """
    if hasattr(cls, '__fspath__'):
        return True
    return hasattr(cls, 'open') and 'path' in cls.__name__.lower()


if hasattr(os, 'PathLike'):
    PathLike = os.PathLike
else:
    class PathLike(ABC):
        """Abstract base class for implementing the file system path protocol."""

        @abc.abstractmethod
        def __fspath__(self):
            """Return the file system path representation of the object."""
            raise NotImplementedError

        @classmethod
        def __subclasshook__(cls, subclass):
            return _looks_like_path_class(subclass)


###############################################################################
# `inspect` predicates missing in old Python versions
###############################################################################

def _always_false(whatever):
    """Fallback predicate for Python versions where the feature doesn't exist,
    so nothing can ever match it."""
    return False


iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', _always_false)
isasyncgenfunction = getattr(inspect, 'isasyncgenfunction', _always_false)


###############################################################################
# String types
###############################################################################

if PY3:
    string_types = (str,)
    text_type = str
    binary_type = bytes
else:
    string_types = (basestring,)
    text_type = unicode
    binary_type = str


###############################################################################
# Collections ABCs
###############################################################################

try:
    from collections import abc as collections_abc
except ImportError: # Python 2.7
    import collections as collections_abc


###############################################################################
# Time formatting
###############################################################################

_TIME_ISOFORMAT_TEMPLATE = '{:02d}:{:02d}:{:02d}.{:06d}'
_TIME_ISOFORMAT_LENGTH = len('HH:MM:SS.ffffff')


if sys.version_info[:2] >= (3, 6):
    time_isoformat = datetime_module.time.isoformat
else:
    def time_isoformat(time, timespec='microseconds'):
        """Backport of `datetime.time.isoformat`, supporting only
        `timespec='microseconds'`."""
        assert isinstance(time, datetime_module.time)
        if timespec != 'microseconds':
            raise NotImplementedError
        result = _TIME_ISOFORMAT_TEMPLATE.format(
            time.hour, time.minute, time.second, time.microsecond
        )
        assert len(result) == _TIME_ISOFORMAT_LENGTH
        return result


def timedelta_format(timedelta):
    """Format a timedelta as `HH:MM:SS.ffffff`."""
    time_of_day = (datetime_module.datetime.min + timedelta).time()
    return time_isoformat(time_of_day, timespec='microseconds')


def timedelta_parse(s):
    """Parse a `HH:MM:SS.ffffff` string, as produced by `timedelta_format`,
    back into a timedelta."""
    fields = s.replace('.', ':').split(':')
    hours, minutes, seconds, microseconds = map(int, fields)
    return datetime_module.timedelta(hours=hours, minutes=minutes,
                                     seconds=seconds,
                                     microseconds=microseconds)
```

## Refactorizaciones aplicadas

- **Extract Function** — `PathLike.__subclasshook__` → nueva función privada `_looks_like_path_class`.
  - **Motivo:** la expresión booleana compuesta, con un comentario intercalado, era difícil de leer. Ahora la lógica tiene un nombre que revela su intención y un docstring que explica la concesión a versiones antiguas de `pathlib`.
  - De paso se corrigió la errata del comentario original (`versions:g`).
  - El resultado devuelto es el mismo `True`/`False` en todos los casos.

- **Replace Lambda with Named Function** — las dos lambdas `lambda whatever: False  # Lolz` → función privada `_always_false`.
  - **Motivo:** se elimina la duplicación y se sustituye un comentario poco descriptivo por un nombre y un docstring explicativos.
  - **Diferencias solo en introspección:**
    - El `__name__` del respaldo pasa a ser `_always_false` en lugar de `<lambda>`.
    - En intérpretes que carecen de ambas funciones, `iscoroutinefunction` e `isasyncgenfunction` pasan a ser el mismo objeto.
    - Ninguna de las dos diferencias afecta al valor devuelto ni a ningún uso del paquete.

- **Substitute Algorithm** — `try: x = inspect.attr / except AttributeError: x = fallback` → `getattr(inspect, 'attr', fallback)`.
  - **Afecta a:** `iscoroutinefunction` e `isasyncgenfunction`.
  - **Motivo:** es una forma más concisa y semánticamente equivalente de expresar lo mismo (`getattr` con valor por defecto solo captura `AttributeError`).

- **Replace Magic Literal** — la cadena `'{:02d}:{:02d}:{:02d}.{:06d}'` y el número `15` → constantes privadas `_TIME_ISOFORMAT_TEMPLATE` y `_TIME_ISOFORMAT_LENGTH`.
  - **Motivo:** el `15` no explicaba de dónde salía. Ahora se deriva de `len('HH:MM:SS.ffffff')`, que documenta el formato esperado y vale exactamente 15.

- **Rename Variable** — variable local `time` → `time_of_day` en `timedelta_format`.
  - **Motivo:** describe mejor el valor (la hora del día resultante de sumar el timedelta a `datetime.min`).
  - El parámetro `time` de `time_isoformat` no se renombró, para no alterar la firma pública.

- **Extract Variable** — `s.replace('.', ':').split(':')` → variable `fields` en `timedelta_parse`.
  - **Motivo:** separa la normalización de separadores de la conversión a enteros, lo que hace más legible el desempaquetado.

- **Slide Statements / reorganización en secciones** — todo el módulo.
  - **Motivo:** las definiciones se agruparon en bloques temáticos con encabezados: versión, ABCs, predicados de `inspect`, tipos de cadena, ABCs de colecciones y formato de tiempo.
  - El orden de definición se mantiene; únicamente `_looks_like_path_class` aparece antes de `PathLike`, que la utiliza.

- **Add Docstrings** — `time_isoformat` (respaldo), `timedelta_format` y `timedelta_parse`.
  - **Motivo:** documentar el formato `HH:MM:SS.ffffff` y la relación inversa entre `timedelta_format` y `timedelta_parse`.

Se conservan intactos todos los nombres públicos y sus firmas:

- `PY3`, `PY2`, `ABC`, `PathLike`
- `iscoroutinefunction`, `isasyncgenfunction`
- `string_types`, `text_type`, `binary_type`
- `collections_abc`
- `time_isoformat`, `timedelta_format`, `timedelta_parse`

También se conservan los módulos importados. La compatibilidad con Python 2 se mantiene: las referencias a `basestring` y `unicode` siguen confinadas a la rama `PY2`, y no se usa sintaxis exclusiva de Python 3.