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
    '''Compile `source` as an expression, the way watched variables are.'''
    return compile(source, _VARIABLE_FILENAME, 'eval')


def needs_parentheses(source):
    '''Whether `source` must be wrapped in parentheses before appending to it.

    It compares the bytecode of `source.x` with that of `(source).x`. If they
    differ, appending an attribute or index to `source` would apply only to
    part of the expression (e.g. `a + b`), so parentheses are needed.
    '''
    def bytecode(expression):
        return _compile_expression(expression).co_code

    return bytecode('{}.x'.format(source)) != bytecode('({}).x'.format(source))


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
        try:
            main_value = self._evaluate(frame)
        except Exception:
            return ()
        return self._items(main_value, normalize)

    def _evaluate(self, frame):
        return eval(self.code, frame.f_globals or {}, frame.f_locals)

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
    '''Variable that reports its main value plus one entry per sub-key.

    Subclasses define which keys exist (`_keys`), how a key is written next
    to the source (`_format_key`) and how its value is obtained (`_get_value`).
    '''

    def _items(self, main_value, normalize=False):
        # Only the main value's repr is normalized; sub-values are not.
        result = [
            (self.source,
             utils.get_shortish_repr(main_value, normalize=normalize))
        ]
        for key, value in self._safe_key_value_pairs(main_value):
            result.append((
                self._child_source(key),
                utils.get_shortish_repr(value)
            ))
        return result

    def _child_source(self, key):
        return '{}{}'.format(self.unambiguous_source, self._format_key(key))

    def _safe_key_value_pairs(self, main_value):
        '''Yield `(key, value)` pairs, skipping excluded or failing keys.'''
        for key in self._safe_keys(main_value):
            try:
                if key in self.exclude:
                    continue
                value = self._get_value(main_value, key)
            except Exception:
                continue
            yield key, value

    def _safe_keys(self, main_value):
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
        assert isinstance(item, slice)
        sliced_variable = deepcopy(self)
        sliced_variable._slice = item
        return sliced_variable


class Exploding(BaseVariable):
    '''Variable that expands according to the kind of value it finds.'''

    def _items(self, main_value, normalize=False):
        variable_class = self._variable_class_for(main_value)
        return variable_class(self.source, self.exclude)._items(main_value,
                                                                normalize)

    @staticmethod
    def _variable_class_for(main_value):
        if isinstance(main_value, Mapping):
            return Keys
        elif isinstance(main_value, Sequence):
            return Indices
        else:
            return Attrs
```

## Refactorizaciones aplicadas

- **Extract Function** — `_compile_expression(source)`; afecta a `needs_parentheses` y a `BaseVariable.__init__`. La llamada `compile(source, '<variable>', 'eval')` estaba duplicada en dos sitios. Ahora vive en un único punto con un nombre que explica su intención.

- **Replace Magic Literal (Introduce Constant)** — `'<variable>'` pasa a ser `_VARIABLE_FILENAME`. Así se da nombre al pseudo-nombre de archivo que se usa al compilar las expresiones vigiladas.

- **Rename Function (función anidada)** — `code` pasa a llamarse `bytecode` dentro de `needs_parentheses`. El nombre anterior era ambiguo, porque también existe el atributo `self.code`. El nuevo dice qué devuelve (`co_code`).

- **Add Docstring** — en `needs_parentheses`, `CommonVariable`, `_safe_key_value_pairs` y `Exploding`. Se documenta el truco de comparar bytecode y el contrato de plantilla de `CommonVariable` (`_keys`, `_format_key`, `_get_value`).

- **Extract Function** — `_parenthesize_if_needed(source)`; afecta a `BaseVariable.__init__`. El `if/else` que calculaba `unambiguous_source` queda en una sola línea declarativa en el constructor. El orden se conserva: primero se compila `source`, así que un `SyntaxError` se sigue lanzando en el mismo punto.

- **Extract Method** — `BaseVariable._evaluate(frame)`; afecta a `BaseVariable.items`. Separa la evaluación de la expresión en el contexto del frame del manejo de errores. `items` se lee ahora como "evaluar o devolver vacío, y luego expandir".

- **Rename Parameter** — `key` pasa a `main_value` en el método abstracto `BaseVariable._items`. El nombre no coincidía con el uso real ni con las implementaciones de las subclases. Solo se invoca posicionalmente, así que no afecta a ningún llamador.

- **Extract Method** — `CommonVariable._safe_key_value_pairs(main_value)`; afecta a `CommonVariable._items`.
  - El generador encapsula el filtrado de claves excluidas y la obtención tolerante a fallos de cada valor.
  - El bloque `try` cubre exactamente lo mismo que antes: la comprobación `in self.exclude` y `_get_value`.
  - La evaluación sigue siendo perezosa e intercalada, así que el orden de efectos y las excepciones que se propagan no cambian.

- **Extract Method** — `CommonVariable._child_source(key)`; afecta a `CommonVariable._items`. Da nombre a la construcción del texto `fuente + clave` de cada sub-entrada.
  - Además, un comentario aclara que solo el valor principal se normaliza.
  - Ese comportamiento se mantiene intacto.

- **Rename Variable** — `result` pasa a `sliced_variable` en `Indices.__getitem__`. Deja claro que se devuelve una copia de la variable con el slice aplicado.

- **Extract Method** — `Exploding._variable_class_for(main_value)`, como `staticmethod`; afecta a `Exploding._items`.
  - Aísla la elección de la clase de expansión (`Keys`, `Indices` o `Attrs`) mediante retornos directos, sin variable temporal.
  - Se respeta el orden de comprobación original: primero `Mapping` y después `Sequence`.

Se mantienen sin cambios:
- los nombres públicos (`needs_parentheses`, `BaseVariable`, `CommonVariable`, `Attrs`, `Keys`, `Indices`, `Exploding`, `items`);
- los ganchos privados que las subclases sobrescriben (`_items`, `_keys`, `_format_key`, `_get_value`, `_safe_keys`, `_fingerprint`);
- las importaciones, incluido el fallback para Python 2.

Tampoco se usa sintaxis exclusiva de Python 3, como `yield from`.