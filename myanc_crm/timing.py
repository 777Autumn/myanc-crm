"""Host-only timing counts; never include arguments, output, identities or errors."""

from contextlib import contextmanager
from contextvars import ContextVar
import json
import sys
import time


_phases = ContextVar('crm_timing_phases', default=None)


@contextmanager
def capture():
    phases = {}
    token = _phases.set(phases)
    started = time.perf_counter_ns()
    try:
        yield
    finally:
        _phases.reset(token)
        report = {'version': 1, 'total_ns': time.perf_counter_ns() - started, 'phases': phases}
        try:
            print('MYANC_TIMING ' + json.dumps(report, separators=(',', ':')), file=sys.stderr)
        except OSError:
            pass  # Observability must not turn a completed business action into a retry.


@contextmanager
def measure(name):
    phases = _phases.get()
    if phases is None:
        yield
        return
    started = time.perf_counter_ns()
    try:
        yield
    finally:
        phase = phases.setdefault(name, {'count': 0, 'elapsed_ns': 0})
        phase['count'] += 1
        phase['elapsed_ns'] += time.perf_counter_ns() - started
