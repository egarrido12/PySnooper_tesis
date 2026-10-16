```python
import itertools
import abc
try:
    from collections.abc import Mapping, Sequence
except ImportError:
    from collections import Mapping, Sequence
from copy import deepcopy

from . import utils
from . import pycompat


_VARIABLE_FILENAME = '<variable>'


def _compile_expression(source):
    '''Compile `source` as a Python expression to be evaluated later.'''
    return compile(source, _VARIABLE_FILENAME, 'eval')


def _bytecode_of(expression):
    return _compile_expression(expression).co_code


def needs_parentheses(source):
    '''
    Whether `source` has to be wrapped in parentheses so that we can safely
    append an attribute access or a subscript to it.

    We find out by comparing the bytecode of `source.x` with that of
    `(source).x`. If they differ, the parentheses change the meaning.
    '''
    return (_bytecode_of('{}.x'.format(source)) !=
            _bytecode_of('({}).x'.format(source)))


def _parenthesize_if_needed(source):
    if needs_parentheses(source):
        return '({})'.format(source)
    return source


class BaseVariable(pycompat.ABC):
    def __init__(self, source, exclude=()):
        self.source = source
        self.exclude = utils.ensure_tuple(exclude)
        self.code = _compile_expression(source)
        self.unambiguous_source = _parenthesize_if_needed(source)

    def items(self, frame, normalize=False):
        '''
        Evaluate the expression in `frame` and return `(name, repr)` pairs.

        If the expression can't be evaluated, return an empty tuple.
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
    def _items(self, main_value, normalize=False):
        result = [(self.source,
                   utils.get_shortish_repr(main_value, normalize=normalize))]
        for key, value in self._safe_key_values(main_value):
            # Note: child values are represented without `normalize`.
            result.append((self._child_source(key),
                           utils.get_shortish_repr(value)))
        return result

    def _safe_key_values(self, main_value):
        '''
        Yield `(key, value)` pairs of `main_value`, skipping excluded keys and
        any key whose exclusion check or value retrieval raises an exception.
        '''
        for key in self._safe_keys(main_value):
            try:
                if key in self.exclude:
                    continue
                value = self._get_value(main_value, key)
            except Exception:
                continue
            yield key, value

    def _safe_keys(self, main_value):
        '''Yield the keys of `main_value`, stopping silently on any error.'''
        try:
            for key in self._keys(main_value):
                yield key
        except Exception:
            pass

    def _child_source(self, key):
        return '{}{}'.format(self.unambiguous_source, self._format_key(key))

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
        assert isinstance(item, slice)
        sliced_variable = deepcopy(self)
        sliced_variable._slice = item
        return sliced_variable


class Exploding(BaseVariable):
    def _items(self, main_value, normalize=False):
        variable_class = self._variable_class_for(main_value)
        return variable_class(self.source, self.exclude)._items(main_value,
                                                                normalize)

    @staticmethod
    def _variable_class_for(main_value):
        '''
        Choose how to explode `main_value`. `Mapping` must be checked before
        `Sequence`, and anything else is exploded by its attributes.
        '''
        if isinstance(main_value, Mapping):
            return Keys
        elif isinstance(main_value, Sequence):
            return Indices
        else:
            return Attrs
```

## Refactorizaciones aplicadas

- **Extract Function** (`_compile_expression`) y **Replace Magic Literal** (`_VARIABLE_FILENAME`): la llamada `compile(source, '<variable>', 'eval')` aparecía duplicada en `needs_parentheses` y en `BaseVariable.__init__`. Ahora hay un único punto que define cómo se compilan las expresiones vigiladas. Se mantiene el orden original: primero se compila y después se calcula `unambiguous_source`, de modo que una expresión inválida sigue lanzando el mismo `SyntaxError` en el mismo momento.

- **Extract Function / Rename Function** (función anidada `code` → `_bytecode_of` a nivel de módulo):
  - El nombre `code` se confundía con el atributo `self.code`, que es un objeto código y no bytecode.
  - Al sacarla de `needs_parentheses`, esta función queda reducida a una sola comparación y gana un docstring que explica la técnica.

- **Extract Function** (`_parenthesize_if_needed`): el `if/else` que calculaba `unambiguous_source` dentro de `BaseVariable.__init__` pasa a una función con nombre descriptivo. Así el constructor queda como una lista lineal de asignaciones.

- **Rename Parameter** (`BaseVariable._items(self, key, ...)` → `main_value`):
  - El parámetro del método abstracto se llamaba `key`, pero recibe el valor evaluado de la expresión.
  - Ahora coincide con el nombre que usan todas las subclases.
  - Es un método privado y siempre se invoca por posición, así que el cambio no tiene impacto.

- **Extract Method** (`CommonVariable._safe_key_values`): el bucle de `_items` mezclaba dos cosas: filtrar claves excluidas o que fallan, y construir el resultado.
  - El filtrado pasa a un generador.
  - La comprobación `key in self.exclude` sigue dentro del `try`, porque puede lanzar excepciones con objetos cuyo `__eq__` falle.
  - La evaluación sigue siendo perezosa e intercalada como antes: para cada clave se comprueba la exclusión, se obtiene el valor y se formatea antes de pasar a la siguiente.

- **Extract Method** (`CommonVariable._child_source`): la construcción del nombre de cada hijo (`unambiguous_source` + clave formateada) queda con nombre propio. `_format_key` sigue fuera del `try`, así que sus posibles excepciones se propagan igual que antes.

- **Introduce Assertion-free Comment / Documentar comportamiento existente**: se añade un comentario indicando que los valores hijos se representan sin `normalize`. Ese comportamiento se conserva intacto a propósito; el comentario solo lo hace visible para futuros mantenedores.

- **Extract Method** (`Exploding._variable_class_for`, `staticmethod`): la selección de la clase según el tipo del valor (`Keys`, `Indices` o `Attrs`) se separa de la delegación. El docstring explica por qué `Mapping` debe comprobarse antes que `Sequence`.

- **Rename Variable**:
  - `result` → `sliced_variable` en `Indices.__getitem__`, para reflejar que es una copia de la variable con otro slice.
  - `cls` → `variable_class` en `Exploding._items`, para evitar confusión con el primer parámetro convencional de los métodos de clase.

- **Add Docstrings** en `needs_parentheses`, `BaseVariable.items`, `_safe_keys`, `_safe_key_values` y `_compile_expression`, para documentar el manejo silencioso de errores, que antes era implícito.

No se tocaron:
- Los nombres públicos: `needs_parentheses`, `BaseVariable`, `CommonVariable`, `Attrs`, `Keys`, `Indices`, `Exploding` e `items`.
- Las importaciones de `Mapping`/`Sequence`, que siguen disponibles en el módulo.
- La compatibilidad con Python 2: no se usa `yield from` ni otras construcciones exclusivas de Python 3.