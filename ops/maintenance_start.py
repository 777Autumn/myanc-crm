"""Fixed-unit lifecycle helpers for an authorized, backed-up maintenance script.

No CLI or deployment entry point. The caller supplies its frozen control-file
verification and protected, non-overwriting receipt writer.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

UNIT = 'cc-connect.service'
EXE = '/usr/local/bin/cc-connect-anc'
CONFIG_KEYS = ('Id', 'LoadState', 'Type', 'User', 'Group', 'WorkingDirectory',
               'KillMode', 'FragmentPath', 'DropInPaths', 'ExecStart')
STATE_KEYS = ('MainPID', 'InvocationID', 'ActiveState', 'SubState', 'NRestarts',
              'NeedDaemonReload')


class StartError(RuntimeError):
    """Only controlled category strings are exposed, never raw subprocess logs."""


def require(condition, reason):
    if not condition:
        raise StartError(reason)


class Systemd:
    def command(self, verb):
        require(verb in ('start', 'stop'), 'unsupported_verb')
        subprocess.run(['systemctl', verb, UNIT], check=True, timeout=55,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def sample(self):
        output = subprocess.check_output(
            ['systemctl', 'show', UNIT, *['--property=' + k for k in CONFIG_KEYS + STATE_KEYS]],
            text=True, timeout=5, stderr=subprocess.PIPE)
        state = dict(line.split('=', 1) for line in output.splitlines())
        require(set(CONFIG_KEYS + STATE_KEYS) <= state.keys(), 'incomplete_unit_state')
        pid = state['MainPID']
        require(pid.isdecimal(), 'invalid_pid')
        state['exe'] = None
        state['process_start'] = None
        if pid != '0':
            try:
                proc = Path('/proc') / pid
                before = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
                state['exe'] = str((proc / 'exe').resolve(strict=True))
                after = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
                require(before == after, 'pid_reused_during_sample')
                state['process_start'] = before
            except (FileNotFoundError, ProcessLookupError):
                state['exe'] = state['process_start'] = None
        receivers = []
        for entry in Path('/proc').glob('[0-9]*/comm'):
            try:
                if entry.read_text().strip() in ('cc-connect', 'cc-connect-anc'):
                    receivers.append(entry.parent.name)
            except (FileNotFoundError, ProcessLookupError):
                continue
        state['receivers'] = sorted(receivers)
        return state


def unit_identity(state):
    require(all(k in state for k in CONFIG_KEYS + STATE_KEYS), 'incomplete_unit_state')
    require(state['Id'] == UNIT and state['LoadState'] == 'loaded'
            and state['Type'] == 'simple' and state['User'] == 'ccconnect'
            and state['WorkingDirectory'] == '/var/lib/cc-connect'
            and state['KillMode'] == 'control-group'
            and state['ExecStart'].startswith('{ path=' + EXE + ' ;'), 'unexpected_unit')
    require(state['NeedDaemonReload'] == 'no', 'unit_needs_reload')
    # systemctl's ExecStart display also includes mutable execution status.
    command = re.fullmatch(
        r'\{ path=([^;{}\n]+) ; argv\[\]=(.*?) ; ignore_errors=(yes|no)'
        r' ; start_time=\[[^\]\n]*\] ; stop_time=\[[^\]\n]*\]'
        r' ; pid=\d+ ; code=[^;\n]* ; status=[^{}\n]* \}', state['ExecStart'])
    require(command is not None and state['ExecStart'].count('{ path=') == 1, 'unsupported_exec_format')
    identity = {key: state[key] for key in CONFIG_KEYS}
    identity['ExecStart'] = command.groups()  # path, displayed argv, ignore_errors
    return identity


def diagnostic(state):
    if state is None:
        return {'sample_available': False}
    # Do not emit ExecStart arguments, environment, arbitrary exe paths or logs.
    return {k: state[k] for k in ('MainPID', 'InvocationID', 'ActiveState', 'SubState', 'NRestarts')} | {
        'sample_available': True, 'expected_exe': state['exe'] == EXE,
        'exe_available': state['exe'] is not None,
        'process_start': state['process_start'], 'receiver_count': len(state['receivers'])}


def pause_verified(backend, identity, invocation, verify_controls):
    """Stop the unchanged unit, including before its child exec has completed.

    The stop target is the verified unit, not an arbitrary process/PID. A different
    invocation or changed control plane requires manual reconciliation.
    """
    verify_controls()
    state = backend.sample()
    require(unit_identity(state) == identity, 'pause_unit_changed')
    if state['ActiveState'] == 'inactive' and state['MainPID'] == '0':
        require(not state['receivers'], 'receiver_outside_stopped_unit')
        return 'already_stopped'
    require(invocation and state['InvocationID'] == invocation, 'pause_invocation_changed')
    backend.command('stop')
    stopped = backend.sample()
    require(unit_identity(stopped) == identity and stopped['ActiveState'] == 'inactive'
            and stopped['MainPID'] == '0' and not stopped['receivers'], 'pause_not_stopped')
    return 'paused'


def start_once(record, verify_controls, *, backend=None, timeout=40,
               clock=time.monotonic, sleep=time.sleep):
    """Return process identity only; caller must still verify application health.

    record(name, payload) must durably create a new root-protected receipt and
    reject an existing name. A consumed start request is never retried here.
    """
    require(0 < timeout <= 40, 'invalid_timeout')
    backend = backend or Systemd()
    verify_controls()
    state = backend.sample()
    identity = unit_identity(state)
    require(state['ActiveState'] == 'inactive' and state['MainPID'] == '0'
            and not state['receivers'], 'service_not_stopped')
    record('start-requested.json', {'time': time.time(), 'unit': UNIT,
           'identity_sha256': hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()})
    invocation = None
    last = state
    pinned_pid = None
    pinned_start = None
    try:
        backend.command('start')
        deadline = clock() + timeout
        ready_identity = None
        while True:
            last = backend.sample()
            require(unit_identity(last) == identity, 'startup_unit_changed')
            current_invocation = last['InvocationID'] or None
            if invocation is None:
                invocation = current_invocation
            require(invocation == current_invocation, 'startup_invocation_changed')
            require(last['NRestarts'] == '0', 'unexpected_restart')
            require(last['ActiveState'] in ('active', 'activating'), 'startup_exited')
            pid = last['MainPID']
            if pid != '0':
                pinned_pid = pinned_pid or pid
            require(pinned_pid is None or pinned_pid == pid, 'startup_pid_changed')
            if last['process_start'] is not None:
                pinned_start = pinned_start or last['process_start']
            require(last['process_start'] is None or pinned_start == last['process_start'], 'startup_pid_reused')
            require(not last['receivers'] or (pid != '0' and last['receivers'] == [pid]), 'duplicate_receiver')
            require(clock() < deadline, 'startup_timeout')
            ready = (invocation and pid != '0' and last['process_start'] is not None
                     and last['ActiveState'] == 'active' and last['SubState'] == 'running'
                     and last['exe'] == EXE and last['receivers'] == [pid])
            current_identity = (invocation, pid, last['process_start']) if ready else None
            if current_identity is not None and current_identity == ready_identity:
                break
            ready_identity = current_identity
            sleep(min(0.25, max(0, deadline - clock())))
        verify_controls()
        result = {'time': time.time(), 'pid': last['MainPID'], 'invocation': invocation,
                  'process_start': last['process_start'], 'process_identity_ready': True}
        record('started.json', result)
        return result
    except BaseException as exc:
        # A command error may happen after systemd accepted the single request.
        safety = 'manual_reconciliation_required'
        pause_error = None
        try:
            if invocation is None:
                current = backend.sample()
                require(unit_identity(current) == identity, 'pause_unit_changed')
                invocation = current['InvocationID'] or None
            safety = pause_verified(backend, identity, invocation, verify_controls)
        except BaseException as pause_exc:
            pause_error = str(pause_exc) if isinstance(pause_exc, StartError) else type(pause_exc).__name__
        failure = {'failed': True, 'category': type(exc).__name__,
                   'reason': str(exc) if isinstance(exc, StartError) else 'start_or_receipt_failed',
                   'last_sample': diagnostic(last), 'safety': safety, 'pause_error': pause_error}
        try:
            record('start-failed.json', failure)
        except BaseException:
            failure['receipt_failed'] = True
        error = StartError(json.dumps(failure, sort_keys=True))
        raise error from None
