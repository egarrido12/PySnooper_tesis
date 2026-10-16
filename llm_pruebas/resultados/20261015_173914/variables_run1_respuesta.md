```python
import itertools
import abc
from copy import deepcopy

from . import utils
from . import pycompat


# Se reutiliza la compatibilidad Python 2/3 que ya resuelve `pycompat`. Los
# nombres se mantienen a nivel de módulo por compatibilidad con código que
# pudiera importarlos desde aquí.
Mapping = pycompat.collections_abc.Mapping
Sequence = pycompat.collections_abc.Sequence


_VARIABLE_FILENAME = '<variable>'


def _compile_expression(source):
    return compile(source, _VARIABLE_FILENAME, 'eval')


def needs_parentheses(source):
    """Whether ``source`` must be wrapped in parentheses before an attribute
    access or a subscript can be appended to it (e.g. ``a + b`` needs them,
    ``a.b`` does not)."""
    def bytecode(expression):
        return _compile_expression(expression).co_code

    return bytecode('{}.x'.format(source)) != bytecode('({}).x'.format(source))


def _make_unambiguous_source(source):
    if needs_parentheses(source):
        return '({})'.format(source)
    return source


class BaseVariable(pycompat.ABC):
    def __init__(self, source, exclude=()):
        self.source = source
        self.exclude = utils.ensure_tuple(exclude)
        self.code = _compile_expression(source)
        self.unambiguous_source = _make_unambiguous_source(source)

    def items(self, frame, normalize=False):
        try:
            main_value = eval(self.code, frame.f_globals or {}, frame.f_locals)
        except Exception:
            return ()
        return self._items(main_value, normalize)

    @abc.abstractmethod
    def _items(self, main_value, normalize=False):
        """Return ``(name, repr)`` pairs describing ``main_value``."""
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
        main_item = (
            self.source,
            utils.get_shortish_repr(main_value, normalize=normalize)
        )
        return [main_item] + list(self._child_items(main_value))

    def _child_items(self, main_value):
        """Yield ``(name, repr)`` for every non-excluded, readable child."""
        for key in self._safe_keys(main_value):
            try:
                if key in self.exclude:
                    continue
                value = self._get_value(main_value, key)
            except Exception:
                continue
            yield (self._format_child_name(key), utils.get_shortish_repr(value))

    def _format_child_name(self, key):
        return '{}{}'.format(self.unambiguous_source, self._format_key(key))

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
        result = deepcopy(self)
        result._slice = item
        return result


class Exploding(BaseVariable):
    def _items(self, main_value, normalize=False):
        variable_class = self._choose_variable_class(main_value)
        return variable_class(self.source, self.exclude)._items(main_value,
                                                                normalize)

    @staticmethod
    def _choose_variable_class(main_value):
        # Mapping must be checked before Sequence.
        if isinstance(main_value, Mapping):
            return Keys
        elif isinstance(main_value, Sequence):
            return Indices
        else:
            return Attrs
```

## Refactorizaciones aplicadas

- **Extract Function** – `_compile_expression(source)` (usada por `needs_parentheses` y `BaseVariable.__init__`).
  Motivo: la llamada `compile(..., '<variable>', 'eval')` estaba duplicada. Ahora hay un único punto que define cómo se compila una expresión vigilada.

- **Replace Magic Literal (Extract Constant)** – `_VARIABLE_FILENAME = '<variable>'`.
  Motivo: el pseudo-nombre de archivo aparecía repetido como literal. Al darle nombre queda clara su intención.

- **Rename Variable** – función interna `code` → `bytecode` y su parámetro `s` → `expression`, dentro de `needs_parentheses`.
  Motivo: `code` se confundía con el atributo `BaseVariable.code`, que es un objeto código y no bytecode. El nuevo nombre describe lo que se compara realmente: `co_code`.

- **Extract Function** – `_make_unambiguous_source(source)`, extraída de `BaseVariable.__init__`.
  Motivo: el constructor solo asigna atributos. La regla "envolver entre paréntesis si hace falta" queda aislada y con nombre propio. Se conserva el orden original: se compila `source` antes de evaluar `needs_parentheses`, así que los errores de sintaxis se lanzan en el mismo punto.

- **Rename Parameter** – `key` → `main_value` en el método abstracto `BaseVariable._items`.
  Motivo: el parámetro recibe el valor evaluado de la expresión, no una clave. Así coincide con todas las implementaciones concretas. Es un método privado que siempre se invoca de forma posicional.

- **Extract Method** – `CommonVariable._child_items(main_value)` (generador), extraído de `CommonVariable._items`.
  Motivo: separa la entrada principal de la iteración sobre los hijos. Se mantienen intactos varios detalles:
  - el orden de evaluación;
  - que `key in self.exclude` siga dentro del `try`;
  - que las excepciones de `_format_key` se propaguen;
  - que los hijos se representen sin `normalize`;
  - que el resultado siga siendo una `list`.

- **Extract Method** – `CommonVariable._format_child_name(key)`.
  Motivo: da nombre a la construcción `unambiguous_source + clave formateada`, que antes iba incrustada dentro de una tupla.

- **Extract Method** + **Rename Variable** – `Exploding._choose_variable_class(main_value)` y la variable local `cls` → `variable_class` en `Exploding._items`.
  Motivo: la selección de la estrategia (`Keys`, `Indices` o `Attrs`) queda separada de su uso. `cls` sugería falsamente la clase propia del método. Se añade un comentario sobre la importancia del orden de comprobación, ya que una `str` o un mapeo también podrían encajar en otra rama.

- **Substitute Algorithm** (eliminación de lógica de compatibilidad duplicada) – el bloque `try/except ImportError` de `Mapping`/`Sequence` pasa a usar `pycompat.collections_abc`.
  Motivo: `pycompat` ya resuelve exactamente esa diferencia entre Python 2 y 3, con el mismo orden de intento (`collections.abc` primero, `collections` después). Los nombres `Mapping` y `Sequence` se mantienen a nivel de módulo para no romper posibles importaciones externas.