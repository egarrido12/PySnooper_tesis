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
