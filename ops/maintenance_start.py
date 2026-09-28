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


def receiver_detail(proc):
    """Best-effort evidence, never a reason to ignore a name-matched process."""
    detail = {'pid': proc.name, 'observed_monotonic_ns': time.monotonic_ns()}
    try:
        fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        detail.update(process_start=fields[19], ppid=fields[1], state=fields[0])
        status = (proc / 'status').read_text().splitlines()
        detail['uid'] = int(next(line for line in status if line.startswith('Uid:')).split()[1])
        exe = str((proc / 'exe').resolve(strict=True))
        detail.update(expected_exe=exe == EXE,
                      exe_path_sha256=hashlib.sha256(exe.encode()).hexdigest(),
                      cgroup_sha256=hashlib.sha256((proc / 'cgroup').read_bytes()).hexdigest())
        after = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        detail['process_start_after'] = after[19]
        detail['observation'] = ('complete' if fields[19] == after[19]
                                 and str((proc / 'exe').resolve(strict=True)) == exe
                                 else 'changed_during_read')
    except (FileNotFoundError, ProcessLookupError):
        detail['observation'] = 'disappeared_during_read'
    except PermissionError:
        detail['observation'] = 'permission_denied'
    except (OSError, ValueError, IndexError, StopIteration):
        detail['observation'] = 'unreadable'
    return detail


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
        # Capture before any protective stop; exits remain in the original count.
        # Bound extra diagnostic I/O, never the receiver count/guard.
        # Normal samples retain their schema and equality for frozen health callers.
        if state['receivers'] and state['receivers'] != [pid]:
            state['receiver_details'] = [receiver_detail(Path('/proc') / p)
                                         for p in state['receivers'][:32]]
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
        'process_start': state['process_start'], 'receiver_count': len(state['receivers']),
        'receiver_pids': state['receivers'][:32],
        'receiver_details': state.get('receiver_details', []),
        'receiver_details_truncated': len(state['receivers']) > 32}


def systemd_view(state):
    """Lifecycle decisions; the original systemd sample/receipts stay unchanged."""
    return dict(pid=state['MainPID'], epoch=state['InvocationID'] or None,
                stopped=state['ActiveState'] == 'inactive' and state['MainPID'] == '0',
                alive=state['ActiveState'] in ('active', 'activating'),
                running=state['ActiveState'] == 'active' and state['SubState'] == 'running',
                no_restarts=state['NRestarts'] == '0', exe=state['exe'],
                process_start=state['process_start'], receivers=state['receivers'])


def pause_verified(backend, identity, invocation, verify_controls):
    """Stop the unchanged unit, including before its child exec has completed.

    The stop target is the verified unit, not an arbitrary process/PID. A different
    invocation or changed control plane requires manual reconciliation.
    """
    verify_controls()
    state = backend.sample()
    require(getattr(backend, 'identity', unit_identity)(state) == identity, 'pause_unit_changed')
    view = getattr(backend, 'view', systemd_view)(state)
    if view['stopped']:
        require(not view['receivers'], 'receiver_outside_stopped_unit')
        return 'already_stopped'
    require(invocation and view['epoch'] == invocation, 'pause_invocation_changed')
    backend.command('stop')
    stopped = backend.sample()
    view = getattr(backend, 'view', systemd_view)(stopped)
    require(getattr(backend, 'identity', unit_identity)(stopped) == identity
            and view['stopped'] and not view['receivers'], 'pause_not_stopped')
    return 'paused'


def start_once(record, verify_controls, *, backend=None, timeout=40,
               clock=time.monotonic, sleep=time.sleep):
    """Return process identity only; caller must still verify application health.

    record(name, payload) must durably create a new root-protected receipt and
    reject an existing name. A consumed start request is never retried here.
    """
    require(0 < timeout <= 40, 'invalid_timeout')
    backend = backend or Systemd()
    identify = getattr(backend, 'identity', unit_identity)
    inspect = getattr(backend, 'view', systemd_view)
    verify_controls()
    state = backend.sample()
    identity = identify(state)
    view = inspect(state)
    require(view['stopped'] and not view['receivers'], 'service_not_stopped')
    record('start-requested.json', {'time': time.time(), 'unit': getattr(backend, 'unit', UNIT),
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
            require(identify(last) == identity, 'startup_unit_changed')
            view = inspect(last)
            current_invocation = view['epoch']
            if invocation is None:
                invocation = current_invocation
            require(invocation == current_invocation, 'startup_invocation_changed')
            require(view['no_restarts'], 'unexpected_restart')
            require(view['alive'], 'startup_exited')
            pid = view['pid']
            if pid != '0':
                pinned_pid = pinned_pid or pid
            require(pinned_pid is None or pinned_pid == pid, 'startup_pid_changed')
            if view['process_start'] is not None:
                pinned_start = pinned_start or view['process_start']
            require(view['process_start'] is None or pinned_start == view['process_start'], 'startup_pid_reused')
            require(not view['receivers'] or (pid != '0' and view['receivers'] == [pid]), 'duplicate_receiver')
            require(clock() < deadline, 'startup_timeout')
            ready = (invocation and pid != '0' and view['process_start'] is not None
                     and view['running'] and view['exe'] == getattr(backend, 'exe', EXE)
                     and view['receivers'] == [pid])
            current_identity = (invocation, pid, view['process_start']) if ready else None
            if current_identity is not None and current_identity == ready_identity:
                break
            ready_identity = current_identity
            sleep(min(0.25, max(0, deadline - clock())))
        verify_controls()
        result = {'time': time.time(), 'pid': view['pid'], 'invocation': invocation,
                  'process_start': view['process_start'], 'process_identity_ready': True}
        if hasattr(backend, 'diagnostic'):
            result['native_sample'] = backend.diagnostic(last)
        record('started.json', result)
        return result
    except BaseException as exc:
        # A command error may happen after systemd accepted the single request.
        safety = 'manual_reconciliation_required'
        pause_error = None
        try:
            if invocation is None:
                current = backend.sample()
                require(identify(current) == identity, 'pause_unit_changed')
                invocation = inspect(current)['epoch']
            safety = pause_verified(backend, identity, invocation, verify_controls)
        except BaseException as pause_exc:
            pause_error = str(pause_exc) if isinstance(pause_exc, StartError) else type(pause_exc).__name__
        failure = {'failed': True, 'category': type(exc).__name__,
                   'reason': str(exc) if isinstance(exc, StartError) else 'start_or_receipt_failed',
                   'last_sample': getattr(backend, 'diagnostic', diagnostic)(last),
                   'safety': safety, 'pause_error': pause_error}
        try:
            record('start-failed.json', failure)
        except BaseException:
            failure['receipt_failed'] = True
        error = StartError(json.dumps(failure, sort_keys=True))
        raise error from None


def recover_once(record, read_record, verify_controls, verify_reconciled, *, expected,
                 backend=None, timeout=40, clock=time.monotonic, sleep=time.sleep):
    """One explicit, diagnosed recovery in the *original* protected receipt root.

    Both receipt callbacks are bound to that same root. read_record returns exact
    bytes; record retains start_once's durable, exclusive-create contract.
    verify_reconciled is trusted maintenance code, never Bot input: it must
    freshly check the complete installed manifest, controls/permissions, explained
    business changes, no unfinished work and no unknown deliveries. It returns
    the frozen controls_sha256, business_state_sha256 and installed_manifest_sha256
    from those actual checks (the last is inspect_inventory's inventory_sha256).
    All application health and stable-window checks still belong to the caller.
    """
    fields = {'attempt_sha256', 'start_request_sha256', 'failure_sha256',
              'diagnosis_sha256', 'candidate_sha256', 'manifest_sha256',
              'installed_manifest_sha256', 'failure_receipt'}
    require(isinstance(expected, dict) and set(expected) == fields, 'invalid_recovery_binding')
    for key in fields - {'failure_receipt'}:
        require(isinstance(expected[key], str)
                and re.fullmatch('[0-9a-f]{64}', expected[key]) is not None, 'invalid_recovery_digest')
    require(expected['failure_receipt'] in ('failed.json', 'start-failed.json'),
            'invalid_failure_receipt')
    require(0 < timeout <= 40, 'invalid_timeout')
    backend = backend or Systemd()
    try:
        read_record('recovery-requested.json')
    except FileNotFoundError:
        pass
    else:
        raise StartError('recovery_already_requested')

    def read_bound(name, digest):
        raw = read_record(name)
        require(isinstance(raw, bytes) and hashlib.sha256(raw).hexdigest() == digest,
                'recovery_receipt_changed')
        try:
            value = json.loads(raw)
        except (UnicodeError, ValueError):
            raise StartError('invalid_recovery_receipt') from None
        require(isinstance(value, dict), 'invalid_recovery_receipt')
        return value

    attempt = read_bound('attempt.json', expected['attempt_sha256'])
    request = read_bound('start-requested.json', expected['start_request_sha256'])
    failure = read_bound(expected['failure_receipt'], expected['failure_sha256'])
    diagnosis = read_bound('recovery-diagnosis.json', expected['diagnosis_sha256'])
    require(all(attempt.get(key) == expected[key] for key in
                ('candidate_sha256', 'manifest_sha256', 'installed_manifest_sha256')),
            'recovery_candidate_changed')
    require(request.get('unit') == getattr(backend, 'unit', UNIT)
            and isinstance(request.get('identity_sha256'), str),
            'invalid_original_start_request')
    require(isinstance(failure.get('category'), str) and bool(failure['category']),
            'invalid_original_failure')
    require(all(diagnosis.get(key) == expected[key] for key in fields - {'diagnosis_sha256'}),
            'recovery_diagnosis_unbound')
    require(all(isinstance(diagnosis.get(key), str) and diagnosis[key].strip()
                for key in ('cause', 'maintainer_reference')), 'recovery_not_diagnosed')
    snapshots = {key: diagnosis.get(key) for key in
                 ('controls_sha256', 'business_state_sha256', 'installed_manifest_sha256')}
    require(all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)
                for value in snapshots.values()), 'invalid_reconciliation_snapshot')

    def reconciled():
        # Recheck the immutable bindings as well as live state immediately before
        # consuming the existing start helper. A failed second check spends the
        # recovery allowance; it cannot become an automatic retry path.
        read_bound('attempt.json', expected['attempt_sha256'])
        read_bound('start-requested.json', expected['start_request_sha256'])
        read_bound(expected['failure_receipt'], expected['failure_sha256'])
        read_bound('recovery-diagnosis.json', expected['diagnosis_sha256'])
        verify_controls()
        require(verify_reconciled() == snapshots, 'reconciliation_changed')
        state = backend.sample()
        identity = getattr(backend, 'identity', unit_identity)(state)
        identity_sha = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        require(identity_sha == request['identity_sha256'], 'recovery_unit_changed')
        view = getattr(backend, 'view', systemd_view)(state)
        require(view['stopped'] and not view['receivers'], 'service_not_stopped')

    reconciled()
    # Atomic non-overwrite creation is the concurrency guard. Never remove this
    # marker, even if its writer raises after persistence or the process dies.
    record('recovery-requested.json', dict(expected, **snapshots, time=time.time(),
                                         unit=getattr(backend, 'unit', UNIT)))
    try:
        reconciled()
        return start_once(lambda name, payload: record('recovery-' + name, payload),
                          verify_controls, backend=backend, timeout=timeout, clock=clock, sleep=sleep)
    except BaseException as exc:
        try:
            record('recovery-failed.json', {'failed': True, 'category': type(exc).__name__,
                                            'reconciliation_required': True})
        except BaseException:
            pass  # The consumed marker remains authoritative even without this receipt.
        raise
