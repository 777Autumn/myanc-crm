"""Native Mac backend for maintenance_start; no installer or Bot entry point.

Only the frozen system LaunchDaemon is mutable. Callers still verify the complete
installation, credentials, directory permissions and business state separately.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess

from maintenance_start import require

LABEL = 'com.myanc.cc-connect'
PLIST = Path('/Library/LaunchDaemons/com.myanc.cc-connect.plist')
EXE = '/usr/local/bin/cc-connect-anc'
USER = '_ancgateway'
GROUP = '_ancgateway'
CWD = '/var/lib/cc-connect'
CONFIG = '/usr/local/etc/cc-connect/config.toml'
STDOUT = '/var/log/anc-gateway/stdout.log'
STDERR = '/var/log/anc-gateway/stderr.log'


class BSDInfo(ctypes.Structure):
    # Public Darwin proc_bsdinfo ABI (136 bytes), not ps's second-resolution date.
    _fields_ = [(name, ctypes.c_uint32) for name in (
        'flags', 'status', 'xstatus', 'pid', 'ppid', 'uid', 'gid', 'ruid',
        'rgid', 'svuid', 'svgid', 'reserved')]
    _fields_ += [('comm', ctypes.c_char * 16), ('name', ctypes.c_char * 32)]
    _fields_ += [(name, ctypes.c_uint32) for name in (
        'nfiles', 'pgid', 'jobc', 'tty', 'tpgid', 'nice')]
    _fields_ += [('start_sec', ctypes.c_uint64), ('start_usec', ctypes.c_uint64)]


def process(pid):
    """Read native identity twice; an uncertain process never becomes ready."""
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    before, after = BSDInfo(), BSDInfo()
    size = ctypes.sizeof(BSDInfo)
    require(size == 136, 'unsupported_proc_abi')
    if lib.proc_pidinfo(pid, 3, 0, ctypes.byref(before), size) != size:
        return None
    path = ctypes.create_string_buffer(4096)
    if lib.proc_pidpath(pid, path, len(path)) <= 0:
        return None
    if lib.proc_pidinfo(pid, 3, 0, ctypes.byref(after), size) != size:
        return None
    identity = lambda info: (info.pid, info.uid, info.gid, info.start_sec, info.start_usec)
    if identity(before) != identity(after) or before.pid != pid:
        return None
    return dict(pid=str(pid), uid=before.uid, gid=before.gid, ppid=before.ppid,
                process_start=f'{before.start_sec}.{before.start_usec:06d}',
                exe=os.fsdecode(path.value))


def parse_print(output):
    """Read known top-level fields, never a nested coalition's state/type."""
    lines = output.splitlines()
    require(lines and lines[0] == f'system/{LABEL} = {{' and lines[-1] == '}',
            'unknown_launchctl_format')
    fields = {}
    for line in lines[1:-1]:
        match = re.fullmatch(r'\t([^\t=]+) = ([^\n]*)', line)
        if match and match[2] != '{':
            require(match[1] not in fields, 'duplicate_launchctl_field')
            fields[match[1]] = match[2]
    coalitions = re.findall(r'\tresource coalition = \{\n\t\tID = (\d+)\n', output)
    require(len(coalitions) <= 1, 'ambiguous_launchd_coalition')
    fields['coalition'] = coalitions[0] if coalitions else None
    arguments = re.findall(r'\targuments = \{\n(.*?)\n\t\}', output, re.S)
    require(len(arguments) == 1, 'missing_launchd_arguments')
    fields['arguments'] = arguments[0].splitlines()
    return fields


def frozen_plist():
    before = PLIST.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == 0
            and before.st_mode & 0o022 == 0, 'unprotected_launchd_plist')
    raw = PLIST.read_bytes()
    after = PLIST.lstat()
    require((before.st_ino, before.st_mtime_ns, before.st_size, before.st_mode, before.st_uid)
            == (after.st_ino, after.st_mtime_ns, after.st_size, after.st_mode, after.st_uid),
            'launchd_plist_changed_during_read')
    value = plistlib.loads(raw)
    expected = dict(Label=LABEL, ProgramArguments=[EXE, '-config', CONFIG],
                    UserName=USER, GroupName=GROUP, WorkingDirectory=CWD,
                    RunAtLoad=True, KeepAlive=False, AbandonProcessGroup=False,
                    ProcessType='Background', ExitTimeOut=30, Umask=0o077,
                    StandardOutPath=STDOUT, StandardErrorPath=STDERR,
                    EnvironmentVariables={'HOME': CWD, 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'})
    require(value == expected, 'unexpected_launchd_plist')
    return dict(manager='launchd', label=LABEL, plist_sha256=hashlib.sha256(raw).hexdigest())


class Launchd:
    unit = 'system/' + LABEL
    exe = EXE

    def command(self, verb):
        require(verb in ('start', 'stop'), 'unsupported_verb')
        frozen_plist()
        args = (['bootstrap', 'system', str(PLIST)] if verb == 'start'
                else ['bootout', self.unit])
        subprocess.run(['/bin/launchctl', *args], check=True, timeout=55,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def sample(self):
        identity = frozen_plist()
        boot = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'kern.bootsessionuuid'],
                                       text=True, timeout=5).strip()
        require(re.fullmatch(r'[0-9A-Fa-f-]{36}', boot), 'invalid_boot_identity')
        query = subprocess.run(['/bin/launchctl', 'print', self.unit], text=True,
                               capture_output=True, timeout=5, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'})
        state = dict(manager='launchd', identity=identity, boot_session=boot, loaded=False,
                     state='unloaded', runs=0, pid='0', coalition=None, exe=None,
                     process_start=None, receivers=[], receiver_details=[], last_exit_code=None)
        if query.returncode != 0:
            require(query.returncode == 113 and not query.stdout
                    and query.stderr.strip() == 'Bad request.\nCould not find service "'
                    + LABEL + '" in domain for system', 'launchd_query_failed')
        else:
            fields = parse_print(query.stdout)
            require(all(fields.get(key) == value for key, value in {
                'path': PLIST.as_posix(), 'type': 'LaunchDaemon', 'program': EXE,
                'working directory': CWD, 'domain': 'system', 'username': USER,
                'group': GROUP}.items()), 'loaded_launchd_identity_mismatch')
            require(fields['arguments'] == ['\t\t' + arg for arg in [EXE, '-config', CONFIG]],
                    'loaded_launchd_arguments_mismatch')
            require(fields.get('runs', '').isdecimal()
                    and fields.get('pid', '0').isdecimal(), 'invalid_launchd_counters')
            state.update(loaded=True, state=fields.get('state'), runs=int(fields['runs']),
                         pid=fields.get('pid', '0'), coalition=fields['coalition'])
            exit_code = fields.get('last exit code', '').split(':', 1)[0]
            if re.fullmatch(r'-?\d+', exit_code):
                state['last_exit_code'] = int(exit_code)
            require(state['state'] in ('running', 'spawn scheduled', 'waiting', 'not running'),
                    'unknown_launchd_state')
            require(state['pid'] == '0' or state['coalition'], 'missing_launchd_coalition')
            if state['pid'] != '0':
                detail = process(int(state['pid']))
                if detail:
                    if detail['exe'] == EXE:
                        import pwd
                        account = pwd.getpwnam(USER)
                        require(detail['uid'] == account.pw_uid != 0
                                and detail['gid'] == account.pw_gid, 'unexpected_gateway_identity')
                    state.update(exe=detail['exe'], process_start=detail['process_start'])
        output = subprocess.check_output(['/bin/ps', '-axo', 'pid=,comm='], text=True, timeout=5)
        for line in output.splitlines():
            parts = line.strip().split(None, 1)
            require(len(parts) == 2 and parts[0].isdecimal(), 'unknown_process_list')
            if Path(parts[1]).name in ('cc-connect', 'cc-connect-anc'):
                pid = parts[0]
                state['receivers'].append(pid)
                if len(state['receiver_details']) < 32:
                    detail = process(int(pid))
                    state['receiver_details'].append(
                        dict(pid=pid, observation='unreadable_or_changed') if detail is None else
                        {key: value for key, value in detail.items() if key != 'exe'} |
                        dict(expected_exe=detail['exe'] == EXE,
                             exe_path_sha256=hashlib.sha256(detail['exe'].encode()).hexdigest()))
        state['receivers'].sort()
        return state

    @staticmethod
    def identity(state):
        require(state['manager'] == 'launchd', 'unexpected_service_manager')
        return state['identity']

    @staticmethod
    def view(state):
        # A boot-session + resource-coalition pair is native evidence, not a
        # fabricated systemd InvocationID. A second run is always rejected.
        epoch = ([state['boot_session'], state['coalition']]
                 if state['coalition'] else None)
        return dict(pid=state['pid'], epoch=epoch,
                    stopped=not state['loaded'] and state['pid'] == '0',
                    alive=state['loaded'] and (state['pid'] != '0' or state['runs'] == 0),
                    running=state['state'] == 'running', no_restarts=state['runs'] <= 1,
                    exe=state['exe'], process_start=state['process_start'],
                    receivers=state['receivers'])

    @staticmethod
    def diagnostic(state):
        if state is None:
            return {'sample_available': False, 'manager': 'launchd'}
        return {key: state[key] for key in ('manager', 'boot_session', 'loaded', 'state',
                'runs', 'pid', 'coalition', 'process_start', 'receiver_details')} | dict(
            sample_available=True, expected_exe=state['exe'] == EXE,
            last_exit_code=state.get('last_exit_code'),
            receiver_count=len(state['receivers']), receiver_pids=state['receivers'][:32],
            receiver_details_truncated=len(state['receivers']) > 32)
