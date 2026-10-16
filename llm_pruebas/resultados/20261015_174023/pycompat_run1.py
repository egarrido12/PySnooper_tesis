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
