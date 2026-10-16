```python
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.
'''
PySnooper - Never use print for debugging again

Usage:

    import pysnooper

    @pysnooper.snoop()
    def your_function(x):
        ...

A log will be written to stderr showing the lines executed and variables
changed in the decorated function.

For more information, see https://github.com/cool-RR/PySnooper
'''

import collections

from .tracer import Tracer as snoop
from .variables import Attrs, Exploding, Indices, Keys

__version__ = '1.2.3'

_VersionInfo = collections.namedtuple('VersionInfo',
                                      ('major', 'minor', 'micro'))
__version_info__ = _VersionInfo(*map(int, __version__.split('.')))

del collections, _VersionInfo  # Avoid polluting the namespace
```

## Refactorizaciones aplicadas

- **Rename Variable**: `__VersionInfo` → `_VersionInfo`.
  - Motivo: el doble guion bajo inicial sugiere *name mangling*, pero ese mecanismo solo actúa dentro de clases. A nivel de módulo no tiene efecto y confunde al lector.
  - El guion bajo simple es la convención estándar para nombres privados del módulo.
  - El nombre del tipo del `namedtuple` (`'VersionInfo'`) no cambia, así que `repr(__version_info__)` sigue mostrando `VersionInfo(major=1, minor=2, micro=3)`.

- **Remove Redundant Parentheses** (simplificación de expresión, afín a *Substitute Algorithm*): `__VersionInfo(*(map(int, ...)))` → `_VersionInfo(*map(int, ...))`.
  - Motivo: los paréntesis alrededor de `map(...)` no aportaban nada y dificultaban la lectura del desempaquetado.

- **Slide Statements**:
  - Elementos afectados:
    - `import collections` pasa al principio, siguiendo el orden PEP 8: primero la biblioteca estándar y luego los imports relativos del paquete.
    - `__version__` se define justo antes de construir `__version_info__`, que es la única línea que depende de él.
  - Motivo: agrupar las declaraciones relacionadas. Así, el dato de origen (`__version__`) y su versión derivada (`__version_info__`) se leen juntos.

## Notas sobre compatibilidad y comportamiento

- La API pública del paquete no cambia: `snoop`, `Attrs`, `Exploding`, `Indices`, `Keys`, `__version__` y `__version_info__`.
- El docstring del módulo (`pysnooper.__doc__`) se mantiene intacto.
- No se añadió `__all__`, porque eso alteraría el resultado de `from pysnooper import *`.
- Se mantiene el `del` final, de modo que el espacio de nombres del módulo queda igual que antes (sin `collections` ni la clase auxiliar).
- La línea `__version__ = '1.2.3'` conserva exactamente su formato original, por si alguna herramienta de empaquetado la extrae con una expresión regular.
- El código sigue siendo compatible con Python 2.7 y 3.x: no usa f-strings ni anotaciones de tipo.