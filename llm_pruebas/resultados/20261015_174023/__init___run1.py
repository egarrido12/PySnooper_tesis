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
