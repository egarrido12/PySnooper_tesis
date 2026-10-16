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

# Los nombres auxiliares solo hacen falta para construir `__version_info__`;
# los borramos para no exponerlos como atributos del paquete.
del collections, _VersionInfo
```

## Refactorizaciones aplicadas

- **Rename Variable**: `__VersionInfo` → `_VersionInfo`.
  *Motivo:* el doble guion bajo sugiere *name mangling*, pero eso solo ocurre dentro de clases. A nivel de módulo no tiene ningún efecto especial y confunde al lector. Un solo guion bajo es la convención estándar para nombres privados de módulo.
  *Comportamiento:* se conserva. El nombre se elimina con `del` al final, así que no es visible desde fuera. El nombre interno de la clase sigue siendo `'VersionInfo'`, de modo que `repr(__version_info__)` sigue mostrando `VersionInfo(major=1, minor=2, micro=3)`. Su `__module__` sigue siendo `pysnooper`.

- **Remove Redundant Parentheses** (simplificación de expresión, en la línea de *Substitute Algorithm* a pequeña escala): `__VersionInfo(*(map(int, ...)))` → `_VersionInfo(*map(int, ...))`.
  *Motivo:* los paréntesis alrededor de `map(...)` no aportan nada y dificultan la lectura. El desempaquetado produce exactamente los mismos argumentos.

- **Slide Statements**: `import collections` se movió al principio, antes de los imports relativos.
  *Motivo:* sigue la convención de PEP 8 (biblioteca estándar primero, luego imports locales) y agrupa todas las dependencias del módulo en un mismo sitio. El orden no altera el comportamiento: `collections` no tiene efectos secundarios dependientes de `tracer` o `variables`, y esos submódulos ya lo importan por su cuenta.

- **Replace Comment / mejora del comentario**: el comentario en línea `# Avoid polluting the namespace` pasó a ser un comentario previo al `del`.
  *Motivo:* ahora explica también *por qué* esos nombres existen solo temporalmente.

Cambios descartados a propósito:

- **No se añadió `__all__`.** Habría cambiado el resultado de `from pysnooper import *`, que hoy también exporta los submódulos importados implícitamente (`tracer`, `variables`, `utils`, `pycompat`).
- **No se extrajo una función auxiliar para parsear la versión** (*Extract Function*). Habría añadido un nombre más que borrar del espacio de nombres sin ganar claridad en una expresión de una sola línea.