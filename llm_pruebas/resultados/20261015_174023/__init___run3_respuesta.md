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

_VersionInfo = collections.namedtuple('VersionInfo',
                                      ('major', 'minor', 'micro'))

__version__ = '1.2.3'
__version_info__ = _VersionInfo(*map(int, __version__.split('.')))

# Remove the auxiliary names so they are not exposed as part of the package.
del collections, _VersionInfo
```

## Refactorizaciones aplicadas

- **Rename Variable**: `__VersionInfo` → `_VersionInfo`.
  - **Motivo**: el doble guion bajo sugiere *name mangling*, pero ese mecanismo solo existe dentro de clases. A nivel de módulo resulta engañoso.
  - La convención idiomática para un nombre privado es un solo guion bajo.
  - El nombre del tipo pasado a `namedtuple` (`'VersionInfo'`) no cambia. Por tanto, `repr(__version_info__)` sigue mostrando `VersionInfo(major=1, minor=2, micro=3)`.

- **Simplificación de expresión** (eliminación de paréntesis redundantes; no tiene entrada propia en el catálogo de Fowler): `__VersionInfo(*(map(int, ...)))` → `_VersionInfo(*map(int, ...))`.
  - **Motivo**: los paréntesis alrededor de `map(...)` no aportan nada y dificultan la lectura.
  - El desempaquetado funciona igual en Python 2 (`map` devuelve una lista) y en Python 3 (devuelve un iterador).

- **Slide Statements**: `import collections` se movió antes de los imports relativos del paquete.
  - **Motivo**: así se sigue el orden de PEP 8 (biblioteca estándar primero, luego imports locales) y se separan visualmente ambos grupos.
  - No hay efectos observables: `tracer` ya importa `collections` por su cuenta, y el nombre se elimina del espacio de nombres al final igual que antes.

- **Aclaración del comentario del `del`**: el comentario se reescribió para explicar el propósito de la línea, que es no exponer nombres auxiliares en el paquete.
  - El conjunto de nombres públicos de `pysnooper` queda exactamente igual: `snoop`, `Attrs`, `Exploding`, `Indices`, `Keys`, `__version__`, `__version_info__` y los submódulos importados.
  - No se agregó `__all__` a propósito, porque alteraría el resultado de `from pysnooper import *`.