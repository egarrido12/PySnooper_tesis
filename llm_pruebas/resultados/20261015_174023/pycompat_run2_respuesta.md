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
#                                                                             #
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
    def _is_legacy_pathlib_class(cls):
        '''Concession for older `pathlib` versions, which lack `__fspath__`.'''
        return hasattr(cls, 'open') and 'path' in cls.__name__.lower()

    class PathLike(ABC):
        """Abstract base class for implementing the file system path protocol."""

        @abc.abstractmethod
        def __fspath__(self):
            """Return the file system path representation of the object."""
            raise NotImplementedError

        @classmethod
        def __subclasshook__(cls, subclass):
            return (hasattr(subclass, '__fspath__') or
                    _is_legacy_pathlib_class(subclass))
#                                                                             #
### Finished abstract base classes. ###########################################


### Function introspection: ###################################################
#                                                                             #
def _always_false(whatever):
    '''Fallback for `inspect` predicates missing in old Python versions.'''
    return False


iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', _always_false)
isasyncgenfunction = getattr(inspect, 'isasyncgenfunction', _always_false)
#                                                                             #
### Finished function introspection. ##########################################


### String types: #############################################################
#                                                                             #
if PY3:
    string_types = (str,)
    text_type = str
    binary_type = bytes
else:
    string_types = (basestring,)
    text_type = unicode
    binary_type = str
#                                                                             #
### Finished string types. ####################################################


try:
    from collections import abc as collections_abc
except ImportError: # Python 2.7
    import collections as collections_abc


### Time formatting: ##########################################################
#                                                                             #
if sys.version_info[:2] >= (3, 6):
    time_isoformat = datetime_module.time.isoformat
else:
    _MICROSECONDS_TIME_TEMPLATE = '{:02d}:{:02d}:{:02d}.{:06d}'
    _MICROSECONDS_TIME_LENGTH = len('HH:MM:SS.ffffff')

    def time_isoformat(time, timespec='microseconds'):
        '''Backport of `datetime.time.isoformat`, only for microseconds.'''
        assert isinstance(time, datetime_module.time)
        if timespec != 'microseconds':
            raise NotImplementedError
        result = _MICROSECONDS_TIME_TEMPLATE.format(
            time.hour, time.minute, time.second, time.microsecond
        )
        assert len(result) == _MICROSECONDS_TIME_LENGTH
        return result


def timedelta_format(timedelta):
    '''Format a `timedelta` as `HH:MM:SS.ffffff`.'''
    time_of_day = (datetime_module.datetime.min + timedelta).time()
    return time_isoformat(time_of_day, timespec='microseconds')


def timedelta_parse(s):
    '''Parse a `HH:MM:SS.ffffff` string into a `timedelta`.'''
    colon_separated = s.replace('.', ':')
    hours, minutes, seconds, microseconds = map(int,
                                                colon_separated.split(':'))
    return datetime_module.timedelta(hours=hours, minutes=minutes,
                                     seconds=seconds,
                                     microseconds=microseconds)
#                                                                             #
### Finished time formatting. #################################################
```

## Refactorizaciones aplicadas

- **Extract Function** — `_is_legacy_pathlib_class` (usada en `PathLike.__subclasshook__` del respaldo para Python < 3.6). La condición compuesta para las versiones antiguas de `pathlib` ahora tiene un nombre que explica su intención. Se conserva la evaluación en cortocircuito con `or`, así que la segunda comprobación solo se ejecuta si falta `__fspath__`, igual que antes. Además desaparece el comentario con la errata (`versions:g`).

- **Replace Lambda with Named Function** y **Remove Duplicated Code** — `iscoroutinefunction` e `isasyncgenfunction`. Las dos lambdas idénticas (`lambda whatever: False # Lolz`) se sustituyen por una única función `_always_false`, documentada y con el mismo parámetro posicional.

- **Substitute Algorithm** (simplificación) — los bloques `try/except AttributeError` pasan a ser `getattr(inspect, ..., _always_false)`. Es semánticamente equivalente y más conciso.

- **Replace Magic Literal** — `_MICROSECONDS_TIME_TEMPLATE` y `_MICROSECONDS_TIME_LENGTH`, dentro del respaldo de `time_isoformat`. El `15` de la aserción pasa a calcularse como `len('HH:MM:SS.ffffff')`, lo que documenta de dónde sale ese número. El valor es idéntico.

- **Rename Variable** — la variable local `time` pasa a llamarse `time_of_day` en `timedelta_format`. El nuevo nombre deja claro que es un `datetime.time` derivado del `timedelta`. No se renombraron parámetros de funciones públicas (`time`, `timespec`, `s`) para no romper llamadas con argumentos nombrados.

- **Extract Variable** — `colon_separated`, en `timedelta_parse`. Separa en dos pasos legibles la normalización del separador y la conversión a enteros.

- **Add Docstrings / Slide Statements** (organización) — afecta a todo el módulo:
  - Las definiciones se agrupan en secciones comentadas (clases abstractas, introspección, tipos de cadena, formato de tiempo), siguiendo el estilo de comentarios por bloques que ya usa `tracer.py`.
  - Se añaden docstrings breves a las funciones.

**Compatibilidad:** se mantienen todos los nombres públicos (`PY2`, `PY3`, `ABC`, `PathLike`, `iscoroutinefunction`, `isasyncgenfunction`, `string_types`, `text_type`, `binary_type`, `collections_abc`, `time_isoformat`, `timedelta_format`, `timedelta_parse`) y los módulos importados. La sintaxis sigue siendo válida en Python 2.7: no hay f-strings, anotaciones ni argumentos solo-keyword.