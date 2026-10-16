"""Pruebas de PySnooper con Rope (refactorización automática).

Flujo:
  1. Línea base: corre la suite de tests original de PySnooper.
  2. Análisis estático con Rope (sin modificar código): find_errors,
     find_occurrences y find_definition.
  3. Refactorizaciones: cada una se aplica con la API de Rope sobre una
     copia limpia del proyecto, se guarda el diff y se vuelve a correr la
     suite de tests. Si los tests siguen pasando, la refactorización
     preservó el comportamiento.

El código original en ../pysnooper NUNCA se modifica.

Uso (desde la raíz del repositorio):
    .venv/bin/python rope_pruebas/ejecutar_pruebas_rope.py
"""
import json
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import rope
from rope.base.project import Project
from rope.contrib import findit, finderrors
from rope.refactor.extract import ExtractMethod
from rope.refactor.inline import create_inline
from rope.refactor.move import create_move
from rope.refactor.rename import Rename

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
TRABAJO = AQUI / '_trabajo'
RESULTADOS = AQUI / 'resultados'
PYTHON = sys.executable

IGNORAR = shutil.ignore_patterns(
    '.git', '.venv', '.pytest_cache', '*.egg-info', '__pycache__',
    '.ropeproject', 'rope_pruebas',
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def copia_limpia(nombre):
    """Copia el repositorio (sin .git/.venv) a _trabajo/<nombre>."""
    destino = TRABAJO / nombre
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(REPO, destino, ignore=IGNORAR)
    return destino


def correr_pytest(carpeta):
    """Corre pytest en `carpeta` y devuelve (resumen, salida completa)."""
    proc = subprocess.run(
        [PYTHON, '-m', 'pytest', 'tests', '-q', '-rs', '-p', 'no:cacheprovider'],
        cwd=carpeta, capture_output=True, text=True,
    )
    salida = proc.stdout + proc.stderr
    resumen = {'returncode': proc.returncode}
    for clave in ('passed', 'failed', 'skipped', 'error', 'errors'):
        m = re.search(r'(\d+) ' + clave + r'\b', salida)
        resumen[clave] = int(m.group(1)) if m else 0
    resumen['errors'] += resumen.pop('error')
    return resumen, salida


def verificar_import(carpeta):
    """Confirma que pytest importa el pysnooper de la copia, no otro."""
    proc = subprocess.run(
        [PYTHON, '-c', 'import pysnooper; print(pysnooper.__file__)'],
        cwd=carpeta, capture_output=True, text=True,
    )
    ruta = proc.stdout.strip()
    assert ruta.startswith(str(carpeta)), ruta
    return ruta


def offset_de(recurso, marcador, desplazamiento=0):
    """Offset (en caracteres) de `marcador` dentro del archivo."""
    codigo = recurso.read()
    assert codigo.count(marcador) == 1, 'marcador ambiguo o ausente: %r' % marcador
    return codigo.index(marcador) + desplazamiento


def inicio_de_linea(recurso, marcador):
    codigo = recurso.read()
    return codigo.rfind('\n', 0, offset_de(recurso, marcador)) + 1


# ---------------------------------------------------------------------------
# 1. Línea base
# ---------------------------------------------------------------------------

def linea_base():
    carpeta = copia_limpia('00_linea_base')
    ruta = verificar_import(carpeta)
    resumen, salida = correr_pytest(carpeta)
    (RESULTADOS / '00_linea_base_pytest.txt').write_text(salida)
    print('[linea base] %s  (pysnooper importado desde %s)' % (resumen, ruta))
    return resumen


# ---------------------------------------------------------------------------
# 2. Análisis estático
# ---------------------------------------------------------------------------

SIMBOLOS = [
    # (archivo, marcador, desplazamiento hasta el nombre)
    ('pysnooper/utils.py', 'def get_shortish_repr', 4),
    ('pysnooper/utils.py', 'def truncate', 4),
    ('pysnooper/tracer.py', 'def _is_internal_frame', 4),
    ('pysnooper/tracer.py', 'class Tracer:', 6),
    ('pysnooper/variables.py', 'class CommonVariable', 6),
]


def analisis_estatico():
    carpeta = copia_limpia('01_analisis')
    proyecto = Project(str(carpeta))
    lineas = ['# Análisis estático con Rope %s' % rope.VERSION, '']

    lineas += ['## find_errors (rope.contrib.finderrors)', '',
               '| Módulo | Errores reportados |', '|---|---|']
    errores_totales = []
    for archivo in sorted((carpeta / 'pysnooper').glob('*.py')):
        rel = archivo.relative_to(carpeta).as_posix()
        errores = finderrors.find_errors(proyecto, proyecto.get_resource(rel))
        errores_totales += [(rel, e.lineno, e.error) for e in errores]
        lineas.append('| `%s` | %d |' % (rel, len(errores)))
    lineas.append('')
    for rel, lineno, error in errores_totales:
        lineas.append('- `%s:%d` — %s' % (rel, lineno, error))
    if errores_totales:
        lineas.append('')

    lineas += ['## find_occurrences (rope.contrib.findit)', '']
    ocurrencias = {}
    for rel, marcador, desp in SIMBOLOS:
        recurso = proyecto.get_resource(rel)
        offset = offset_de(recurso, marcador, desp)
        nombre = re.match(r'\w+', recurso.read()[offset:]).group(0)
        encontradas = findit.find_occurrences(proyecto, recurso, offset)
        ocurrencias[nombre] = len(encontradas)
        lineas.append('### `%s` (%d ocurrencias)' % (nombre, len(encontradas)))
        lineas.append('')
        for o in encontradas:
            lineas.append('- `%s:%d`%s' % (o.resource.path, o.lineno,
                                          ' (dudosa)' if o.unsure else ''))
        lineas.append('')

    lineas += ['## find_definition (rope.contrib.findit)', '']
    recurso = proyecto.get_resource('pysnooper/variables.py')
    offset = offset_de(recurso, 'utils.get_shortish_repr(key)', 6)
    definicion = findit.find_definition(proyecto, recurso.read(), offset, recurso)
    lineas.append('Desde `pysnooper/variables.py` (`utils.get_shortish_repr(key)`) '
                  'Rope resuelve la definición en `%s:%d`.'
                  % (definicion.resource.path, definicion.lineno))
    lineas.append('')

    proyecto.close()
    (RESULTADOS / '01_analisis_estatico.md').write_text('\n'.join(lineas))
    print('[analisis] errores=%d ocurrencias=%s' % (len(errores_totales), ocurrencias))
    return {'errores': len(errores_totales), 'ocurrencias': ocurrencias,
            'definicion': '%s:%d' % (definicion.resource.path, definicion.lineno)}


# ---------------------------------------------------------------------------
# 3. Refactorizaciones
# ---------------------------------------------------------------------------
# Cada función recibe el proyecto Rope y devuelve un objeto ChangeSet.

def ref_rename_funcion(p):
    r = p.get_resource('pysnooper/utils.py')
    return Rename(p, r, offset_de(r, 'def get_shortish_repr', 4)).get_changes('get_short_repr')


def ref_rename_funcion_usada_en_tests(p):
    r = p.get_resource('pysnooper/utils.py')
    return Rename(p, r, offset_de(r, 'def truncate', 4)).get_changes('truncate_string')


def ref_rename_metodo(p):
    r = p.get_resource('pysnooper/tracer.py')
    return Rename(p, r, offset_de(r, 'def _is_internal_frame', 4)).get_changes('_is_pysnooper_frame')


def ref_rename_clase(p):
    r = p.get_resource('pysnooper/variables.py')
    return Rename(p, r, offset_de(r, 'class CommonVariable', 6)).get_changes('GenericVariable')


def ref_rename_parametro(p):
    r = p.get_resource('pysnooper/utils.py')
    return Rename(p, r, offset_de(r, 'def truncate(string', 13)).get_changes('text')


def ref_extract_timestamp(p):
    # Bloque "Making timestamp" de Tracer.trace -> self._make_timestamp(frame)
    r = p.get_resource('pysnooper/tracer.py')
    inicio = inicio_de_linea(r, "            timestamp = ' ' * 15") - len('        if self.normalize:\n')
    fin = inicio_de_linea(r, '### Finished making timestamp.')
    fin = r.read().rfind('\n', 0, fin - 1) + 1  # excluye la línea "#   #"
    return ExtractMethod(p, r, inicio, fin).get_changes('_make_timestamp')


def ref_extract_decorador(p):
    # Bloque "Dealing with misplaced function definition" (devuelve 2 valores)
    r = p.get_resource('pysnooper/tracer.py')
    inicio = inicio_de_linea(r, "        if event == 'call' and source_line.lstrip().startswith('@'):")
    fin = inicio_de_linea(r, '### Finished dealing with misplaced function definition.')
    fin = r.read().rfind('\n', 0, fin - 1) + 1
    return ExtractMethod(p, r, inicio, fin).get_changes('_skip_decorator_lines')


def ref_extract_con_locals(p):
    # Bloque que usa '...'.format(**locals()): caso límite para Rope
    r = p.get_resource('pysnooper/tracer.py')
    inicio = inicio_de_linea(r, '        for name, value_repr in local_reprs.items():')
    fin = inicio_de_linea(r, '### Finished newish and modified variables.')
    fin = r.read().rfind('\n', 0, fin - 1) + 1
    return ExtractMethod(p, r, inicio, fin).get_changes('_report_variables')


def ref_extract_control(p):
    # Control: bloque sin **locals(); la variable de salida `r` se usa de
    # forma explícita después del bloque.
    r = p.get_resource('pysnooper/utils.py')
    inicio = inicio_de_linea(r, '    try:\n        r = repr_function(item)')
    fin = inicio_de_linea(r, "    r = r.replace('\\r', '')")
    return ExtractMethod(p, r, inicio, fin).get_changes('_safe_repr')


def ref_inline_funcion(p):
    r = p.get_resource('pysnooper/utils.py')
    return create_inline(p, r, offset_de(r, 'def normalize_repr', 4)).get_changes()


def ref_move_funcion(p):
    r = p.get_resource('pysnooper/utils.py')
    destino = p.get_resource('pysnooper/pycompat.py')
    return create_move(p, r, offset_de(r, 'def shitcode', 4)).get_changes(destino)


REFACTORIZACIONES = [
    ('02_rename_funcion', 'Rename', 'utils.get_shortish_repr -> get_short_repr (usada en 3 módulos)', ref_rename_funcion),
    ('03_rename_funcion_tests', 'Rename', 'utils.truncate -> truncate_string (también importada por los tests)', ref_rename_funcion_usada_en_tests),
    ('04_rename_metodo', 'Rename', 'Tracer._is_internal_frame -> _is_pysnooper_frame', ref_rename_metodo),
    ('05_rename_clase', 'Rename', 'variables.CommonVariable -> GenericVariable (clase base con subclases)', ref_rename_clase),
    ('06_rename_parametro', 'Rename', 'parámetro string de truncate -> text', ref_rename_parametro),
    ('07_extract_timestamp', 'Extract Method', 'bloque "Making timestamp" de Tracer.trace -> _make_timestamp', ref_extract_timestamp),
    ('08_extract_decorador', 'Extract Method', 'bloque "misplaced function definition" -> _skip_decorator_lines (2 valores de retorno)', ref_extract_decorador),
    ('09_extract_con_locals', 'Extract Method', 'bloque que usa .format(**locals()) -> _report_variables (caso límite)', ref_extract_con_locals),
    ('10_extract_control', 'Extract Method', 'control sin locals(): try/except de get_shortish_repr -> _safe_repr', ref_extract_control),
    ('11_inline_funcion', 'Inline', 'inline de utils.normalize_repr en get_shortish_repr', ref_inline_funcion),
    ('12_move_funcion', 'Move', 'mover utils.shitcode a pycompat', ref_move_funcion),
]


def aplicar(nombre, tipo, descripcion, funcion, base):
    carpeta = copia_limpia(nombre)
    proyecto = Project(str(carpeta))
    fila = {'id': nombre, 'tipo': tipo, 'descripcion': descripcion}
    t0 = time.perf_counter()
    try:
        cambios = funcion(proyecto)
        proyecto.do(cambios)
    except Exception as e:
        fila['tiempo_rope_s'] = round(time.perf_counter() - t0, 3)
        fila['estado_rope'] = 'error: %s: %s' % (type(e).__name__, e)
        fila['veredicto'] = 'RECHAZADA POR ROPE'
        (RESULTADOS / (nombre + '_error.txt')).write_text(traceback.format_exc())
        proyecto.close()
        print('[%s] Rope rechazó: %s' % (nombre, fila['estado_rope']))
        return fila
    fila['tiempo_rope_s'] = round(time.perf_counter() - t0, 3)
    fila['estado_rope'] = 'aplicada'
    fila['archivos_modificados'] = sorted(r.path for r in cambios.get_changed_resources())
    proyecto.close()
    (RESULTADOS / (nombre + '.diff')).write_text(cambios.get_description())

    resumen, salida = correr_pytest(carpeta)
    (RESULTADOS / (nombre + '_pytest.txt')).write_text(salida)
    fila['tests'] = resumen
    igual = (resumen['passed'] == base['passed'] and resumen['failed'] == 0
             and resumen['errors'] == 0)
    fila['veredicto'] = 'COMPORTAMIENTO PRESERVADO' if igual else 'ROMPE TESTS'
    print('[%s] %s  %s' % (nombre, fila['veredicto'], resumen))
    return fila


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def escribir_resumen(base, analisis, filas):
    lineas = [
        '# Resumen de pruebas con Rope', '',
        '- Python: `%s`' % sys.version.split()[0],
        '- Rope: `%s`' % rope.VERSION,
        '- Fecha: %s' % time.strftime('%Y-%m-%d %H:%M'), '',
        '## Línea base', '',
        '%(passed)d passed, %(failed)d failed, %(skipped)d skipped, %(errors)d errors' % base, '',
        '## Refactorizaciones', '',
        '| # | Tipo | Descripción | Rope | Tiempo (s) | Tests (passed/failed/errors) | Veredicto |',
        '|---|---|---|---|---|---|---|',
    ]
    for f in filas:
        t = f.get('tests')
        tests = '%d / %d / %d' % (t['passed'], t['failed'], t['errors']) if t else '—'
        lineas.append('| %s | %s | %s | %s | %s | %s | **%s** |' % (
            f['id'], f['tipo'], f['descripcion'], f['estado_rope'],
            f['tiempo_rope_s'], tests, f['veredicto']))
    lineas.append('')
    (RESULTADOS / 'resumen.md').write_text('\n'.join(lineas))
    (RESULTADOS / 'resumen.json').write_text(json.dumps(
        {'python': sys.version.split()[0], 'rope': rope.VERSION,
         'linea_base': base, 'analisis': analisis, 'refactorizaciones': filas},
        indent=2, ensure_ascii=False))


def main():
    RESULTADOS.mkdir(exist_ok=True)
    for viejo in RESULTADOS.iterdir():
        viejo.unlink()
    base = linea_base()
    analisis = analisis_estatico()
    filas = [aplicar(*r, base=base) for r in REFACTORIZACIONES]
    escribir_resumen(base, analisis, filas)
    print('\nResultados en %s' % RESULTADOS)


if __name__ == '__main__':
    main()
