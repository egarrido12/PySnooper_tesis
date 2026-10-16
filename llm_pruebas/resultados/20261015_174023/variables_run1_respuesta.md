```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.
'''Variables that can be watched by the tracer (``watch``/``watch_explode``).'''

import abc
import itertools
from copy import deepcopy

from . import pycompat
from . import utils

# Se reutiliza la capa de compatibilidad de `pycompat` en lugar de repetir el
# `try/except ImportError`. Se mantienen los nombres a nivel de módulo.
Mapping = pycompat.collections_abc.Mapping
Sequence = pycompat.collections_abc.Sequence


_VARIABLE_FILENAME = '<variable>'


def _compile_expression(source):
    '''Compile `source` as a Python expression that can be evaluated.'''
    return compile(source, _VARIABLE_FILENAME, 'eval')


def needs_parentheses(source):
    '''Whether `source` must be parenthesized before appending an accessor.

    For example, `x + y` needs parentheses (`(x + y).attr`), but `x` doesn't.
    It is detected by comparing the bytecode with and without parentheses.
    '''
    def bytecode(expression):
        return _compile_expression(expression).co_code

    return bytecode('{}.x'.format(source)) != bytecode('({}).x'.format(source))


def _make_unambiguous(source):
    '''Return `source` parenthesized only if necessary.'''
    if needs_parentheses(source):
        return '({})'.format(source)
    return source


class BaseVariable(pycompat.ABC):
    def __init__(self, source, exclude=()):
        self.source = source
        self.exclude = utils.ensure_tuple(exclude)
        self.code = _compile_expression(source)
        self.unambiguous_source = _make_unambiguous(source)

    def items(self, frame, normalize=False):
        '''Evaluate the expression in `frame` and return (name, repr) pairs.

        If the evaluation fails, nothing is reported.
        '''
        try:
            main_value = eval(self.code, frame.f_globals or {}, frame.f_locals)
        except Exception:
            return ()
        return self._items(main_value, normalize)

    @abc.abstractmethod
    def _items(self, main_value, normalize=False):
        raise NotImplementedError

    @property
    def _fingerprint(self):
        return (type(self), self.source, self.exclude)

    def __hash__(self):
        return hash(self._fingerprint)

    def __eq__(self, other):
        return (isinstance(other, BaseVariable) and
                self._fingerprint == other._fingerprint)


class CommonVariable(BaseVariable):
    '''Variable that reports its value and the value of each of its "keys".

    Subclasses define what the keys are (`_keys`), how they are read
    (`_get_value`) and how they are shown in the name (`_format_key`).
    '''

    def _items(self, main_value, normalize=False):
        result = [(self.source,
                   utils.get_shortish_repr(main_value, normalize=normalize))]
        for key in self._safe_keys(main_value):
            try:
                if key in self.exclude:
                    continue
                value = self._get_value(main_value, key)
            except Exception:
                # Keys that can't be compared or read are skipped.
                continue
            result.append((self._full_name(key), utils.get_shortish_repr(value)))
        return result

    def _full_name(self, key):
        '''Name under which the value of `key` is reported, e.g. `foo.bar`.'''
        return '{}{}'.format(self.unambiguous_source, self._format_key(key))

    def _safe_keys(self, main_value):
        '''Iterate over the keys, stopping silently if something fails.'''
        try:
            for key in self._keys(main_value):
                yield key
        except Exception:
            pass

    def _keys(self, main_value):
        return ()

    def _format_key(self, key):
        raise NotImplementedError

    def _get_value(self, main_value, key):
        raise NotImplementedError


class Attrs(CommonVariable):
    def _keys(self, main_value):
        return itertools.chain(
            getattr(main_value, '__dict__', ()),
            getattr(main_value, '__slots__', ())
        )

    def _format_key(self, key):
        return '.' + key

    def _get_value(self, main_value, key):
        return getattr(main_value, key)


class Keys(CommonVariable):
    def _keys(self, main_value):
        return main_value.keys()

    def _format_key(self, key):
        return '[{}]'.format(utils.get_shortish_repr(key))

    def _get_value(self, main_value, key):
        return main_value[key]


class Indices(Keys):
    _slice = slice(None)

    def _keys(self, main_value):
        return range(len(main_value))[self._slice]

    def __getitem__(self, item):
        '''Return a copy of this variable restricted to the slice `item`.'''
        assert isinstance(item, slice)
        sliced_variable = deepcopy(self)
        sliced_variable._slice = item
        return sliced_variable


class Exploding(BaseVariable):
    '''Variable that picks `Keys`, `Indices` or `Attrs` based on its value.'''

    def _items(self, main_value, normalize=False):
        variable_class = self._choose_variable_class(main_value)
        return variable_class(self.source, self.exclude)._items(main_value,
                                                                normalize)

    @staticmethod
    def _choose_variable_class(main_value):
        # The order matters: a mapping must be explored by its keys before
        # it is considered as a sequence.
        if isinstance(main_value, Mapping):
            return Keys
        if isinstance(main_value, Sequence):
            return Indices
        return Attrs
```

## Refactorizaciones aplicadas

- **Extract Function** – `_compile_expression(source)` (y la constante `_VARIABLE_FILENAME`): `BaseVariable.__init__` y `needs_parentheses` repetían la llamada `compile(source, '<variable>', 'eval')`. Ahora esa forma de compilar las expresiones vigiladas está definida en un único sitio.

- **Rename Variable** – la función interna `code` de `needs_parentheses` pasa a llamarse `bytecode`, y su parámetro `s` pasa a llamarse `expression`:
  - El nombre `code` se confundía con el atributo `self.code`, que es un objeto código y no bytecode.
  - Añadí un docstring que explica el truco de comparar el bytecode.

- **Extract Function** – `_make_unambiguous(source)`: el `if/else` de `BaseVariable.__init__` que calculaba `unambiguous_source` pasa a ser una función con nombre. Así el constructor queda como una lista lineal de asignaciones.
  - Se mantiene el orden: se compila antes de comprobar los paréntesis, de modo que un error de sintaxis se lanza en el mismo punto que antes.

- **Rename Parameter** – en el método abstracto `BaseVariable._items`, `key` pasa a llamarse `main_value`:
  - El nombre anterior era engañoso.
  - Ahora coincide con el de todas las implementaciones.
  - Todas las llamadas son posicionales, así que no hay cambio observable.

- **Extract Method** – `CommonVariable._full_name(key)`: aísla el formato del nombre reportado (`'{}{}'.format(self.unambiguous_source, self._format_key(key))`).
  - Sigue fuera del `try`, por lo que las excepciones de `_format_key` se propagan igual que antes.
  - Se evalúa antes que el `repr` del valor, como en el original.

- **Extract Method / Replace Nested Conditional with Guard Clauses** – `Exploding._choose_variable_class(main_value)`: la selección de `Keys`/`Indices`/`Attrs` pasa a un método estático con retornos tempranos.
  - Se documenta por qué importa el orden: `Mapping` va antes que `Sequence`.

- **Rename Variable** – `cls` pasa a llamarse `variable_class` en `Exploding._items`, y `result` pasa a llamarse `sliced_variable` en `Indices.__getitem__`. Describen mejor su contenido; `cls` además sugiere un parámetro de método de clase.

- **Substitute Algorithm (compatibilidad)** – el `try/except ImportError` para importar `Mapping` y `Sequence` se sustituye por `pycompat.collections_abc`, que ya resuelve esa diferencia entre Python 2 y 3.
  - Se conservan `Mapping` y `Sequence` como nombres del módulo para no alterar su espacio de nombres.

- **Introduce Assertion de intención (comentarios/docstrings)** – añadí docstrings y comentarios en `BaseVariable.items`, `CommonVariable`, `_safe_keys`, `Indices.__getitem__` y `Exploding`. Documentan comportamientos implícitos:
  - los errores silenciados al evaluar la expresión o al leer claves;
  - el papel de cada método de extensión (`_keys`, `_get_value`, `_format_key`).

**Lo que conservé a propósito:**

- Los métodos protegidos `_items`, `_keys`, `_format_key`, `_get_value`, `_safe_keys` y `_fingerprint` mantienen sus nombres. Son el protocolo de extensión documentado para subclases de usuario, así que renombrarlos rompería código externo.
- El cuerpo de `_safe_keys` sigue con un bucle `for ... yield` en lugar de `yield from`, para mantener la compatibilidad con Python 2.
- La comprobación `key in self.exclude` sigue dentro del `try`, de modo que las claves cuya comparación falla se siguen omitiendo.
- Los valores de las claves se siguen representando sin `normalize`; solo el valor principal lo usa. Es el comportamiento original, aunque parezca inconsistente.