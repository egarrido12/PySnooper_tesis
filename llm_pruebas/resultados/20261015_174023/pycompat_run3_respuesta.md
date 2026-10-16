```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.
'''Python 2/3 compatibility'''

import abc
import os
import inspect
import sys
import datetime as datetime_module

PY3 = (sys.version_info[0] == 3)
PY2 = not PY3


### Abstract base classes: ####################################################

if hasattr(abc, 'ABC'):
    ABC = abc.ABC
else:
    class ABC(object):
        """Helper class that provides a standard way to create an ABC using
        inheritance.
        """
        __metaclass__ = abc.ABCMeta
        __slots__ = ()


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
            return (
                hasattr(subclass, '__fspath__') or
                # Make a concession for older `pathlib` versions:
                (hasattr(subclass, 'open') and
                 'path' in subclass.__name__.lower())
            )


### Function introspection: ###################################################

def _always_false(whatever):
    '''Fallback for `inspect` predicates missing in old Python versions.'''
    return False


iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', _always_false)
isasyncgenfunction = getattr(inspect, 'isasyncgenfunction', _always_false)


### String types: #############################################################

if PY3:
    string_types = (str,)
    text_type = str
    binary_type = bytes
else:
    string_types = (basestring,)
    text_type = unicode
    binary_type = str


### Collections: ##############################################################

try:
    from collections import abc as collections_abc
except ImportError: # Python 2.7
    import collections as collections_abc


### Time formatting: ##########################################################

_ISOFORMAT_MICROSECONDS_TEMPLATE = '{:02d}:{:02d}:{:02d}.{:06d}'
_ISOFORMAT_MICROSECONDS_LENGTH = len('HH:MM:SS.ffffff')

if sys.version_info[:2] >= (3, 6):
    time_isoformat = datetime_module.time.isoformat
else:
    def time_isoformat(time, timespec='microseconds'):
        '''Backport of `datetime.time.isoformat`, supporting only
        `timespec='microseconds'`.'''
        assert isinstance(time, datetime_module.time)
        if timespec != 'microseconds':
            raise NotImplementedError
        result = _ISOFORMAT_MICROSECONDS_TEMPLATE.format(
            time.hour, time.minute, time.second, time.microsecond
        )
        assert len(result) == _ISOFORMAT_MICROSECONDS_LENGTH
        return result


def timedelta_format(timedelta):
    '''Format a timedelta as `HH:MM:SS.ffffff`.'''
    time_of_day = (datetime_module.datetime.min + timedelta).time()
    return time_isoformat(time_of_day, timespec='microseconds')


def timedelta_parse(s):
    '''Parse a `HH:MM:SS.ffffff` string, as produced by `timedelta_format`,
    back into a timedelta.'''
    time_components = s.replace('.', ':').split(':')
    hours, minutes, seconds, microseconds = map(int, time_components)
    return datetime_module.timedelta(hours=hours, minutes=minutes,
                                     seconds=seconds,
                                     microseconds=microseconds)
```

## Refactorizaciones aplicadas

- **Substitute Algorithm** — `iscoroutinefunction`, `isasyncgenfunction`: los bloques `try/except AttributeError` se reemplazan por `getattr(inspect, nombre, fallback)`. El resultado es equivalente, ya que el objeto devuelto es el mismo cuando el atributo existe y el fallback cuando no existe, pero resulta más conciso y declarativo.

- **Extract Function** (y eliminación de duplicación) — `_always_false`: las dos lambdas idénticas `lambda whatever: False  # Lolz` se sustituyen por una única función privada, nombrada y documentada, que ambos fallbacks comparten.

- **Replace Magic Literal** — `_ISOFORMAT_MICROSECONDS_TEMPLATE`, `_ISOFORMAT_MICROSECONDS_LENGTH` en el `time_isoformat` de respaldo:
  - La plantilla de formato y el número `15` pasan a ser constantes con nombre.
  - La longitud se expresa como `len('HH:MM:SS.ffffff')`, que vale 15, para que el significado de la aserción sea evidente.
  - Ambas son privadas para no ampliar la API pública.

- **Rename Variable** — variable local `time` → `time_of_day` en `timedelta_format`: evita sombrear visualmente el nombre del módulo estándar `time` y describe mejor qué contiene. El parámetro `time` de `time_isoformat` no se renombra, porque forma parte de la firma pública.

- **Extract Variable** — `time_components` en `timedelta_parse`: separa la normalización y el troceado del string de la conversión a enteros, lo que hace más legible la expresión antes anidada dentro de `map`. El parámetro `s` se mantiene para no romper llamadas por nombre.

- **Agrupación en secciones y documentación**:
  - Se organizó el módulo en secciones temáticas: ABCs, introspección, tipos de cadena, colecciones y formato de tiempo.
  - Se añadieron docstrings a `time_isoformat` (fallback), `timedelta_format` y `timedelta_parse`.
  - Se corrigió la errata del comentario `versions:g` → `versions:`.

Se conservaron todos los nombres públicos del módulo, con sus mismos valores y firmas: `PY2`, `PY3`, `ABC`, `PathLike`, `iscoroutinefunction`, `isasyncgenfunction`, `string_types`, `text_type`, `binary_type`, `collections_abc`, `time_isoformat`, `timedelta_format`, `timedelta_parse` y `datetime_module`. También se mantienen los imports a nivel de módulo, así que la compatibilidad con Python 2.7 y 3.x queda intacta.

La única diferencia introspectiva es que los fallbacks ahora tienen `__name__ == '_always_false'` en lugar de `'<lambda>'`. Esto solo afecta a intérpretes muy antiguos que carecen de esos predicados en `inspect`, y no altera ningún resultado de llamada.