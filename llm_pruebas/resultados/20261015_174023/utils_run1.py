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
