# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.

import functools
import inspect
import opcode
import os
import sys
import re
import collections
import datetime as datetime_module
import itertools
import threading

from .variables import CommonVariable, Exploding, BaseVariable
from . import utils, pycompat
if pycompat.PY2:
    from io import open


ipython_filename_pattern = re.compile('^<ipython-input-([0-9]+)-.*>$')
ansible_filename_pattern = re.compile(r'^(.+\.zip)[/|\\](ansible[/|\\]modules[/|\\].+\.py)$')
ipykernel_filename_pattern = re.compile(r'^/var/folders/.*/ipykernel_[0-9]+/[0-9]+.py$')
RETURN_OPCODES = {
    'RETURN_GENERATOR', 'RETURN_VALUE', 'RETURN_CONST',
    'INSTRUMENTED_RETURN_GENERATOR', 'INSTRUMENTED_RETURN_VALUE',
    'INSTRUMENTED_RETURN_CONST', 'YIELD_VALUE', 'INSTRUMENTED_YIELD_VALUE'
}

# File coding may be specified. Match pattern from PEP-263
# (https://www.python.org/dev/peps/pep-0263/)
_source_encoding_pattern = re.compile(br'coding[:=]\s*([-\w.]+)')

# Attribute name on `Tracer` -> ANSI escape code used when color is enabled.
_ANSI_STYLE_CODES = (
    ('_FOREGROUND_BLUE', '\x1b[34m'),
    ('_FOREGROUND_CYAN', '\x1b[36m'),
    ('_FOREGROUND_GREEN', '\x1b[32m'),
    ('_FOREGROUND_MAGENTA', '\x1b[35m'),
    ('_FOREGROUND_RED', '\x1b[31m'),
    ('_FOREGROUND_RESET', '\x1b[39m'),
    ('_FOREGROUND_YELLOW', '\x1b[33m'),
    ('_STYLE_BRIGHT', '\x1b[1m'),
    ('_STYLE_DIM', '\x1b[2m'),
    ('_STYLE_NORMAL', '\x1b[22m'),
    ('_STYLE_RESET_ALL', '\x1b[0m'),
)


def call_ended_by_exception(frame, event, arg):
    """Whether a 'return' event was caused by an exception, not a normal return.

    On an exception the interpreter still emits a 'return' event with ``arg`` of
    ``None``, so the last executed opcode is what tells them apart. A frame's
    ``f_lasti`` can be ``-1`` (e.g. before any instruction has run); indexing
    ``co_code[-1]`` would read the wrong opcode, so treat that as a normal
    return. See https://github.com/cool-RR/PySnooper/issues/260.
    """
    if event != 'return' or arg is not None or frame.f_lasti < 0:
        return False
    code_byte = frame.f_code.co_code[frame.f_lasti]
    if not isinstance(code_byte, int):
        code_byte = ord(code_byte)
    return opcode.opname[code_byte] not in RETURN_OPCODES


def get_local_reprs(frame, watch=(), custom_repr=(), max_length=None, normalize=False):
    code = frame.f_code
    vars_order = (code.co_varnames + code.co_cellvars + code.co_freevars +
                  tuple(frame.f_locals.keys()))

    result_items = [(key, utils.get_shortish_repr(value, custom_repr,
                                                  max_length, normalize))
                    for key, value in frame.f_locals.items()]
    result_items.sort(key=lambda key_value: vars_order.index(key_value[0]))
    result = collections.OrderedDict(result_items)

    for variable in watch:
        result.update(sorted(variable.items(frame, normalize)))
    return result


class UnavailableSource(object):
    def __getitem__(self, i):
        return u'SOURCE IS UNAVAILABLE'


source_and_path_cache = {}


def _get_source_from_loader(loader, module_name):
    """Return the module's source lines as given by its loader, or `None`."""
    if not hasattr(loader, 'get_source'):
        return None
    try:
        source = loader.get_source(module_name)
    except ImportError:
        return None
    if source is None:
        return None
    return source.splitlines()


def _get_ipykernel_source(file_name):
    source = None
    try:
        import linecache
        _, _, source, _ = linecache.cache.get(file_name)
        source = [line.rstrip() for line in source] # remove '\n' at the end
    except Exception:
        pass
    return source


def _get_ipython_source(entry_number):
    source = None
    try:
        import IPython
        ipython_shell = IPython.get_ipython()
        ((_, _, source_chunk),) = ipython_shell.history_manager. \
                          get_range(0, entry_number, entry_number + 1)
        source = source_chunk.splitlines()
    except Exception:
        pass
    return source


def _get_ansible_source(archive_path, module_path):
    source = None
    try:
        import zipfile
        archive_file = zipfile.ZipFile(archive_path, 'r')
        source = archive_file.read(module_path.replace('\\', '/')).splitlines()
    except Exception:
        pass
    return source


def _get_source_from_disk(file_name):
    source = None
    try:
        with open(file_name, 'rb') as fp:
            source = fp.read().splitlines()
    except utils.file_reading_errors:
        pass
    return source


def _get_source_from_file_name(file_name):
    """Find the source lines based on the kind of file name, or `None`."""
    ipython_filename_match = ipython_filename_pattern.match(file_name)
    ansible_filename_match = ansible_filename_pattern.match(file_name)
    ipykernel_filename_match = ipykernel_filename_pattern.match(file_name)
    if ipykernel_filename_match:
        return _get_ipykernel_source(file_name)
    elif ipython_filename_match:
        return _get_ipython_source(int(ipython_filename_match.group(1)))
    elif ansible_filename_match:
        return _get_ansible_source(ansible_filename_match.group(1),
                                   ansible_filename_match.group(2))
    else:
        return _get_source_from_disk(file_name)


def _detect_source_encoding(source):
    for line in source[:2]:
        match = _source_encoding_pattern.search(line)
        if match:
            return match.group(1).decode('ascii')
    return 'utf-8'


def _decode_source_lines(source):
    # If we just read the source from a file, or if the loader did not
    # apply tokenize.detect_encoding to decode the source into a
    # string, then we should do that ourselves.
    if not isinstance(source[0], bytes):
        return source
    encoding = _detect_source_encoding(source)
    return [pycompat.text_type(source_line, encoding, 'replace')
            for source_line in source]


def get_path_and_source_from_frame(frame):
    globs = frame.f_globals or {}
    module_name = globs.get('__name__')
    file_name = frame.f_code.co_filename
    cache_key = (module_name, file_name)
    try:
        return source_and_path_cache[cache_key]
    except KeyError:
        pass

    source = _get_source_from_loader(globs.get('__loader__'), module_name)
    if source is None:
        source = _get_source_from_file_name(file_name)
    if not source:
        # We used to check `if source is None` but I found a rare bug where it
        # was empty, but not `None`, so now we check `if not source`.
        source = UnavailableSource()
    source = _decode_source_lines(source)

    result = (file_name, source)
    source_and_path_cache[cache_key] = result
    return result


def _write_to_stderr(s):
    stderr = sys.stderr
    try:
        stderr.write(s)
    except UnicodeEncodeError:
        # God damn Python 2
        stderr.write(utils.shitcode(s))


def get_write_function(output, overwrite):
    is_path = isinstance(output, (pycompat.PathLike, str))
    if overwrite and not is_path:
        raise Exception('`overwrite=True` can only be used when writing '
                        'content to file.')
    if output is None:
        return _write_to_stderr
    if is_path:
        return FileWriter(output, overwrite).write
    if callable(output):
        return output

    assert isinstance(output, utils.WritableStream)

    def write(s):
        output.write(s)
    return write


class FileWriter(object):
    def __init__(self, path, overwrite):
        self.path = pycompat.text_type(path)
        self.overwrite = overwrite

    def write(self, s):
        with open(self.path, 'w' if self.overwrite else 'a',
                  encoding='utf-8') as output_file:
            output_file.write(s)
        self.overwrite = False


def _to_variables(sources, default_variable_class):
    """Wrap each source in `default_variable_class` unless it's already a variable."""
    return [
        source if isinstance(source, BaseVariable)
        else default_variable_class(source)
        for source in utils.ensure_tuple(sources)
    ]


def _normalize_custom_repr(custom_repr):
    """Accept a single `(condition, action)` pair as well as a sequence of them."""
    is_single_pair = len(custom_repr) == 2 and not all(
        isinstance(x, pycompat.collections_abc.Iterable) for x in custom_repr
    )
    if is_single_pair:
        return (custom_repr,)
    return custom_repr


def _find_function_definition(source, line_no, source_line):
    """Skip decorator lines until the actual `def` line is found.

    Return `(line_no, source_line)` of the definition, or the original values
    if the end of the source is reached without finding one.
    """
    for candidate_line_no in itertools.count(line_no):
        try:
            candidate_source_line = source[candidate_line_no - 1]
        except IndexError:
            break
        if candidate_source_line.lstrip().startswith('def'):
            return candidate_line_no, candidate_source_line
    return line_no, source_line


thread_global = threading.local()
DISABLED = bool(os.getenv('PYSNOOPER_DISABLED', ''))

class Tracer:
    '''
    Snoop on the function, writing everything it's doing to stderr.

    This is useful for debugging.

    When you decorate a function with `@pysnooper.snoop()`
    or wrap a block of code in `with pysnooper.snoop():`, you'll get a log of
    every line that ran in the function and a play-by-play of every local
    variable that changed.

    If stderr is not easily accessible for you, you can redirect the output to
    a file::

        @pysnooper.snoop('/my/log/file.log')

    See values of some expressions that aren't local variables::

        @pysnooper.snoop(watch=('foo.bar', 'self.x["whatever"]'))

    Expand values to see all their attributes or items of lists/dictionaries:

        @pysnooper.snoop(watch_explode=('foo', 'self'))

    (see Advanced Usage in the README for more control)

    Show snoop lines for functions that your function calls::

        @pysnooper.snoop(depth=2)

    Start all snoop lines with a prefix, to grep for them easily::

        @pysnooper.snoop(prefix='ZZZ ')

    On multi-threaded apps identify which thread are snooped in output::

        @pysnooper.snoop(thread_info=True)

    Customize how values are represented as strings::

        @pysnooper.snoop(custom_repr=((type1, custom_repr_func1),
                         (condition2, custom_repr_func2), ...))

    Variables and exceptions get truncated to 100 characters by default. You
    can customize that:

        @pysnooper.snoop(max_variable_length=200)

    You can also use `max_variable_length=None` to never truncate them.

    Show timestamps relative to start time rather than wall time::

        @pysnooper.snoop(relative_time=True)

    The output is colored for easy viewing by default, except on Windows
    (but can be enabled by setting `color=True`).

    Disable colors like so:

        @pysnooper.snoop(color=False)

    '''
    def __init__(self, output=None, watch=(), watch_explode=(), depth=1,
                 prefix='', overwrite=False, thread_info=False, custom_repr=(),
                 max_variable_length=100, normalize=False, relative_time=False,
                 color=sys.platform in ('linux', 'linux2', 'cygwin', 'darwin')):
        self._write = get_write_function(output, overwrite)

        self.watch = (_to_variables(watch, CommonVariable) +
                      _to_variables(watch_explode, Exploding))
        self.frame_to_local_reprs = {}
        self.start_times = {}
        self.depth = depth
        self.prefix = prefix
        self.thread_info = thread_info
        self.thread_info_padding = 0
        assert self.depth >= 1
        self.target_codes = set()
        self.target_frames = set()
        self.thread_local = threading.local()
        self.custom_repr = _normalize_custom_repr(custom_repr)
        self.last_source_path = None
        self.max_variable_length = max_variable_length
        self.normalize = normalize
        self.relative_time = relative_time
        self.color = color and (output is None)

        for attribute_name, ansi_code in _ANSI_STYLE_CODES:
            setattr(self, attribute_name, ansi_code if self.color else '')

    def __call__(self, function_or_class):
        if DISABLED:
            return function_or_class

        if inspect.isclass(function_or_class):
            return self._wrap_class(function_or_class)
        else:
            return self._wrap_function(function_or_class)

    def _wrap_class(self, cls):
        for attr_name, attr in cls.__dict__.items():
            # Coroutines are functions, but snooping them is not supported
            # at the moment
            if pycompat.iscoroutinefunction(attr):
                continue

            if inspect.isfunction(attr):
                setattr(cls, attr_name, self._wrap_function(attr))
        return cls

    def _wrap_function(self, function):
        self.target_codes.add(function.__code__)

        if (pycompat.iscoroutinefunction(function) or
                pycompat.isasyncgenfunction(function)):
            raise NotImplementedError
        if inspect.isgeneratorfunction(function):
            return self._make_generator_wrapper(function)
        return self._make_simple_wrapper(function)

    def _make_simple_wrapper(self, function):
        @functools.wraps(function)
        def simple_wrapper(*args, **kwargs):
            with self:
                return function(*args, **kwargs)
        return simple_wrapper

    def _make_generator_wrapper(self, function):
        @functools.wraps(function)
        def generator_wrapper(*args, **kwargs):
            gen = function(*args, **kwargs)
            method, incoming = gen.send, None
            while True:
                with self:
                    try:
                        outgoing = method(incoming)
                    except StopIteration:
                        return
                try:
                    method, incoming = gen.send, (yield outgoing)
                except Exception as e:
                    method, incoming = gen.throw, e
        return generator_wrapper

    def write(self, s):
        self._write(u'{}{}\n'.format(self.prefix, s))

    def __enter__(self):
        if DISABLED:
            return
        thread_global.__dict__.setdefault('depth', -1)
        # Must be computed here directly: `f_back` refers to the frame that
        # executed the `with` statement.
        calling_frame = inspect.currentframe().f_back
        if not self._is_internal_frame(calling_frame):
            calling_frame.f_trace = self.trace
            self.target_frames.add(calling_frame)

        stack = self.thread_local.__dict__.setdefault(
            'original_trace_functions', []
        )
        stack.append(sys.gettrace())
        self.start_times[calling_frame] = datetime_module.datetime.now()
        sys.settrace(self.trace)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if DISABLED:
            return
        stack = self.thread_local.original_trace_functions
        sys.settrace(stack.pop())
        # Must be computed here directly: `f_back` refers to the frame that
        # executed the `with` statement.
        calling_frame = inspect.currentframe().f_back
        self.target_frames.discard(calling_frame)
        self.frame_to_local_reprs.pop(calling_frame, None)
        self._write_elapsed_time(calling_frame)

    def _write_elapsed_time(self, calling_frame):
        start_time = self.start_times.pop(calling_frame)
        duration = datetime_module.datetime.now() - start_time
        indent = ' ' * 4 * (thread_global.depth + 1)
        self.write(
            '{indent}{self._FOREGROUND_YELLOW}{self._STYLE_DIM}'
            'Elapsed time: {self._STYLE_NORMAL}{elapsed_time_string}'
            '{self._STYLE_RESET_ALL}'.format(
                self=self, indent=indent,
                elapsed_time_string=pycompat.timedelta_format(duration),
            )
        )

    def _is_internal_frame(self, frame):
        return frame.f_code.co_filename == Tracer.__enter__.__code__.co_filename

    def _is_target_frame(self, frame):
        return frame.f_code in self.target_codes or frame in self.target_frames

    def _has_target_ancestor_within_depth(self, frame):
        """Whether `frame` is called, up to `self.depth - 1` levels deep, from a
        decorated function or snooped block."""
        if self._is_internal_frame(frame):
            return False
        frame_candidate = frame
        for _ in range(1, self.depth):
            frame_candidate = frame_candidate.f_back
            if frame_candidate is None:
                return False
            if self._is_target_frame(frame_candidate):
                return True
        return False

    def set_thread_info_padding(self, thread_info):
        current_thread_len = len(thread_info)
        self.thread_info_padding = max(self.thread_info_padding,
                                       current_thread_len)
        return thread_info.ljust(self.thread_info_padding)

    def _get_thread_info(self):
        if not self.thread_info:
            return ""
        if self.normalize:
            raise NotImplementedError("normalize is not supported with "
                                      "thread_info")
        current_thread = threading.current_thread()
        return "{ident}-{name} ".format(
            ident=current_thread.ident, name=current_thread.name)

    def _make_timestamp(self, frame):
        if self.normalize:
            return ' ' * 15
        if self.relative_time:
            try:
                start_time = self.start_times[frame]
            except KeyError:
                start_time = self.start_times[frame] = \
                                                 datetime_module.datetime.now()
            duration = datetime_module.datetime.now() - start_time
            return pycompat.timedelta_format(duration)
        return pycompat.time_isoformat(
            datetime_module.datetime.now().time(),
            timespec='microseconds'
        )

    def _write_source_path_if_changed(self, source_path, indent):
        if self.last_source_path == source_path:
            return
        self.write(u'{self._FOREGROUND_YELLOW}{self._STYLE_DIM}{indent}'
                   u'Source path:... {self._STYLE_NORMAL}{source_path}'
                   u'{self._STYLE_RESET_ALL}'.format(
                       self=self, indent=indent, source_path=source_path))
        self.last_source_path = source_path

    def _report_variable_changes(self, frame, event, indent):
        old_local_reprs = self.frame_to_local_reprs.get(frame, {})
        self.frame_to_local_reprs[frame] = local_reprs = get_local_reprs(
            frame,
            watch=self.watch,
            custom_repr=self.custom_repr,
            max_length=self.max_variable_length,
            normalize=self.normalize,
        )

        newish_label = ('Starting var:.. ' if event == 'call' else
                        'New var:....... ')

        for name, value_repr in local_reprs.items():
            if name not in old_local_reprs:
                label = newish_label
            elif old_local_reprs[name] != value_repr:
                label = 'Modified var:.. '
            else:
                continue
            self.write('{indent}{self._FOREGROUND_GREEN}{self._STYLE_DIM}'
                       '{label}{self._STYLE_NORMAL}{name} = '
                       '{value_repr}{self._STYLE_RESET_ALL}'.format(
                           self=self, indent=indent, label=label,
                           name=name, value_repr=value_repr))

    def _write_call_ended_by_exception(self, indent):
        self.write('{self._FOREGROUND_RED}{indent}Call ended by exception'
                   '{self._STYLE_RESET_ALL}'.format(self=self, indent=indent))

    def _write_line(self, indent, timestamp, thread_info, event, line_no,
                    source_line):
        self.write(u'{indent}{self._STYLE_DIM}{timestamp} {thread_info}{event:9} '
                   u'{line_no:4}{self._STYLE_RESET_ALL} {source_line}'.format(
                       self=self, indent=indent, timestamp=timestamp,
                       thread_info=thread_info, event=event, line_no=line_no,
                       source_line=source_line))

    def _write_return_value(self, return_value, indent):
        return_value_repr = utils.get_shortish_repr(
            return_value,
            custom_repr=self.custom_repr,
            max_length=self.max_variable_length,
            normalize=self.normalize,
        )
        self.write('{indent}{self._FOREGROUND_CYAN}{self._STYLE_DIM}'
                   'Return value:.. {self._STYLE_NORMAL}{return_value_repr}'
                   '{self._STYLE_RESET_ALL}'.format(
                       self=self, indent=indent,
                       return_value_repr=return_value_repr))

    def _write_exception(self, exc_info, indent):
        exception = utils.format_exception(*exc_info[:2])
        if self.max_variable_length:
            exception = utils.truncate(exception, self.max_variable_length)
        self.write('{indent}{self._FOREGROUND_RED}Exception:..... '
                   '{self._STYLE_BRIGHT}{exception}'
                   '{self._STYLE_RESET_ALL}'.format(
                       self=self, indent=indent, exception=exception))

    def _leave_frame(self, frame):
        self.frame_to_local_reprs.pop(frame, None)
        self.start_times.pop(frame, None)
        thread_global.depth -= 1

    def trace(self, frame, event, arg):
        # We should trace this line either if it's in the decorated function,
        # or the user asked to go a few levels deeper and we're within that
        # number of levels deeper.
        #
        # The most common and quickest check is done inline, because the
        # trace function runs so incredibly often, therefore it's crucial to
        # hyper-optimize it for the common case.
        if not (frame.f_code in self.target_codes or frame in self.target_frames):
            if self.depth == 1:
                return None
            if not self._has_target_ancestor_within_depth(frame):
                return None

        if event == 'call':
            thread_global.depth += 1
        indent = ' ' * 4 * thread_global.depth

        timestamp = self._make_timestamp(frame)

        line_no = frame.f_lineno
        source_path, source = get_path_and_source_from_frame(frame)
        if self.normalize:
            source_path = os.path.basename(source_path)
        self._write_source_path_if_changed(source_path, indent)
        source_line = source[line_no - 1]
        thread_info = self.set_thread_info_padding(self._get_thread_info())

        self._report_variable_changes(frame, event, indent)

        if event == 'call' and source_line.lstrip().startswith('@'):
            # The call event points at a decorator; show the `def` line instead.
            line_no, source_line = _find_function_definition(source, line_no,
                                                             source_line)

        # If a call ends due to an exception, we still get a 'return' event
        # with arg = None. This seems to be the only way to tell the difference
        # https://stackoverflow.com/a/12800909/2482744
        ended_by_exception = call_ended_by_exception(frame, event, arg)

        if ended_by_exception:
            self._write_call_ended_by_exception(indent)
        else:
            self._write_line(indent, timestamp, thread_info, event, line_no,
                             source_line)

        if event == 'return':
            self._leave_frame(frame)
            if not ended_by_exception:
                self._write_return_value(arg, indent)

        if event == 'exception':
            self._write_exception(arg, indent)

        return self.trace
