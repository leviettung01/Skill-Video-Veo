"""Google Flow authentication for app-owned browser contexts.

No Qt dependency. Callers own the profile lock. Secrets never enter diagnostics.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
import threading
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

FLOW_HOME = 'https://flow.google.com/'
FLOW_HOSTS = {'flow.google.com', 'labs.google'}
SESSION_URLS = (
    'https://flow.google.com/api/auth/session',
    'https://flow.google.com/fx/api/auth/session',
    'https://labs.google/fx/api/auth/session',
)

class ProfileLock:
    """One-byte Windows lock, bounded across both local and OS lock waits."""
    def __init__(self, local_lock, lock_path):
        self._local_lock, self._lock_path = local_lock, Path(lock_path)
        self._handle = None
        self.last_error = ''

    def acquire(self, timeout=None):
        import msvcrt
        deadline = None if timeout is None else time.monotonic() + max(0, timeout)
        if not self._local_lock.acquire(timeout=-1 if timeout is None else max(0, timeout)):
            return False
        handle = None
        try:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = self._lock_path.open('a+b')
            # Do not READ byte zero to test the size: another process may hold
            # that byte locked. Seek-to-end works without touching locked data.
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    self._handle = handle
                    return True
                except OSError:
                    if deadline is not None and time.monotonic() >= deadline:
                        break
                    time.sleep(0.05)
        except Exception as exc:
            self.last_error = type(exc).__name__
        if handle:
            handle.close()
        self._local_lock.release()
        return False

    def release(self):
        import msvcrt
        try:
            if self._handle:
                try:
                    self._handle.seek(0)
                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
                finally:
                    self._handle.close()
                    self._handle = None
        finally:
            self._local_lock.release()

    def __enter__(self):
        if not self.acquire(timeout=120):
            raise TimeoutError('profile_busy')
        return self

    def __exit__(self, *args):
        self.release()


_refresh_guard = threading.Lock()
_refresh_locks = {}
_refresh_results = {}


def single_refresh(root, profile, action):
    """Share a refresh only with callers already waiting when it completed."""
    key = os.path.normcase(str(profile_paths(root, profile)[0]))
    started = time.perf_counter_ns()
    with _refresh_guard:
        lock = _refresh_locks.setdefault(key, threading.Lock())
    with lock:
        previous = _refresh_results.get(key)
        if previous and previous[0] >= started:
            return previous[1]
        result = action()
        _refresh_results[key] = (time.perf_counter_ns(), result)
        return result


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def read_store_json(path, default):
    """Missing is normal; corrupt/unreadable existing data must never be reset."""
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        raise ValueError('storage_unreadable: ' + path.name) from exc


def token_result_is_current(root, profile, token):
    metadata = read_json(Path(root) / 'session_metadata' / (profile + '.json'), {}) or {}
    fingerprint = metadata.get('token_fingerprint')
    return not fingerprint or fingerprint == hashlib.sha256(token.encode()).hexdigest()


def save_browser_settings(root, profile, settings=None):
    config = Path(root) / 'browser_settings' / (str(profile).strip() + '.json')
    previous = read_json(config, {}) or {}
    if not isinstance(previous, dict):
        previous = {}
    merged = dict(previous, **(settings if isinstance(settings, dict) else {'channel': 'chrome', 'login_mode': 'system_chrome'}))
    atomic_json(config, merged)
    return merged


def load_session_metadata(root, profile):
    meta = read_json(Path(root) / 'session_metadata' / (str(profile).strip() + '.json'), {}) or {}
    if not isinstance(meta, dict):
        return {}
    if 'project' in meta and 'project_id' not in meta:
        meta['project_id'] = meta['project']
    return meta


def save_session_metadata(root, profile, email, project='', browser_mode='system_chrome', token='', token_source='manual'):
    prof = str(profile).strip()
    meta_path = Path(root) / 'session_metadata' / (prof + '.json')
    prev = read_json(meta_path, {}) or {}
    if not isinstance(prev, dict):
        prev = {}
    tok_str = str(token or prev.get('token') or '').strip()
    payload = {
        **prev,
        'profile': prof,
        'email': str(email or prev.get('email') or '').strip(),
        'project': str(project or prev.get('project') or '').strip(),
        'project_id': str(project or prev.get('project_id') or prev.get('project') or '').strip(),
        'verified_at': time.time(),
        'token_source': token_source,
        'browser_mode': browser_mode or 'system_chrome',
        'token_fingerprint': hashlib.sha256(tok_str.encode()).hexdigest() if tok_str else prev.get('token_fingerprint', ''),
        'token': tok_str,
    }
    atomic_json(meta_path, payload)
    return payload


def account_key(row):
    return ('profile', row['profile_name']) if row.get('profile_name') else ('name', row.get('name', ''))


def merge_account_rows(rows, disk, loaded_keys):
    """Keep new external rows and newer auth, but honor explicit local deletion."""
    if not isinstance(disk, list) or not all(isinstance(r, dict) for r in disk):
        raise ValueError('storage_invalid: accounts.json')
    by_key = {account_key(r): r for r in disk}
    present = {account_key(r) for r in rows}
    for row in rows:
        newer = by_key.get(account_key(row))
        if newer and newer.get('auth_revision', 0) > row.get('auth_revision', 0):
            if row.get('auth_state') == 'profile_known':
                row['active'] = newer.get('active', False)
            for key in ('api_key', 'google_email', 'auth_state', 'auth_revision', 'name', 'proxy_url'):
                if key in newer:
                    row[key] = newer[key]
    rows.extend(dict(r) for r in disk if account_key(r) not in loaded_keys and account_key(r) not in present)
    return rows


def profile_paths(root, name):
    root = Path(root).resolve()
    name = str(name or '').strip()
    if not name or name in ('.', '..') or re.search(r'[\\/:*?"<>|\x00-\x1f]', name) or name.endswith(('.', ' ')) or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', name, re.I):
        raise ValueError('profile_invalid: tên profile không hợp lệ')
    settings = read_json(root / 'browser_settings' / (name + '.json'), {}) or {}
    login_mode = settings.get('login_mode', 'system_chrome')
    if login_mode != 'system_chrome' and not (root / 'profiles' / name).exists():
        login_mode = 'system_chrome'
    folder = 'native_profiles' if login_mode == 'system_chrome' else 'profiles'
    profile = (root / folder / name).resolve()
    if profile.parent != (root / folder).resolve():
        raise ValueError('profile_invalid: đường dẫn nằm ngoài kho tài khoản')
    return profile, root / 'cookies' / (name + '.json')


def session_values(payload):
    """Only OAuth access-token fields; never ID token, CSRF or generic token."""
    if not isinstance(payload, dict):
        return '', ''
    token, email = '', ''
    pending = [payload]
    for _ in range(12):
        if not pending:
            break
        item = pending.pop(0)
        if not isinstance(item, dict):
            continue
        value = item.get('access_token') or item.get('accessToken')
        if isinstance(value, str) and len(value.strip()) > 20:
            token = token or value.strip()
        value = item.get('email')
        if isinstance(value, str) and '@' in value:
            email = email or value.strip()
        pending.extend(item.get(key) for key in ('session', 'data', 'user') if isinstance(item.get(key), dict))
    return token, email


def identity_matches(expected, actual):
    actual = str(actual or '').strip().lower()
    # Accept any valid Google email signed into this isolated Chrome profile so
    # logging in with a new/different account updates the profile seamlessly.
    return '@' in actual


def _cookies_list_to_flow_token(cookies):
    if not isinstance(cookies, list):
        return ''
    essential = {
        'SID', 'HSID', 'SSID', 'APISID', 'SAPISID', 'OSID', 'AEC', 'NID',
        'SIDCC', 'SEARCH_SAMESITE',
    }
    selected = {}
    for item in cookies:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name', '') or '').strip()
        value = str(item.get('value', '') or '').strip()
        domain = str(item.get('domain', '') or '').strip().lower().lstrip('.')
        if not name or not value:
            continue
        if domain and not (
            domain == 'flow.google.com'
            or domain == 'labs.google'
            or domain == 'google.com'
            or domain.endswith('.google.com')
        ):
            continue
        if name in essential or name.startswith(('__Secure-', '__Host-')):
            selected[name] = value
    if not selected:
        return ''
    return 'flow_cookie:' + '; '.join(f'{k}={v}' for k, v in selected.items())


def check_token(token, client_factory):
    if not isinstance(token, str) or len(token.strip()) < 20:
        return False, 'token_missing'
    raw = token.strip()
    if raw.startswith('flow_cookie:') or ('SID=' in raw and '__Secure-' in raw):
        cookie_header = raw[len('flow_cookie:'):].strip() if raw.startswith('flow_cookie:') else raw
        if not cookie_header:
            return False, 'token_missing'
        try:
            with client_factory(timeout=12, target_url='https://flow.google.com/', use_proxy=True) as client:
                response = client.get(
                    'https://flow.google.com/',
                    headers={
                        'Cookie': cookie_header,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    },
                )
            if response.status_code == 200:
                html = response.text or ''
                at_match = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
                email_match = re.search(r'"oPEP7c"\s*:\s*"([^"]+@[^"]+)"', html)
                if at_match and email_match:
                    return True, email_match.group(1).strip()
                return False, 'token_rejected: phiên Google Flow đã hết hạn'
            code = {401: 'token_rejected', 403: 'permission_denied', 429: 'rate_limited'}.get(response.status_code, 'service_error')
            return False, f'{code}: flow HTTP {response.status_code}'
        except Exception as exc:
            return False, f'network_error: {type(exc).__name__}'
    try:
        with client_factory(timeout=10, target_url='https://www.googleapis.com/oauth2/v3/userinfo', use_proxy=True) as client:
            response = client.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={'Authorization': 'Bearer ' + token})
        if response.status_code == 200:
            payload = response.json()
            email = payload.get('email', '')
            if not isinstance(email, str) or '@' not in email:
                return False, 'identity_missing: userinfo chưa trả email'
            if payload.get('email_verified') is False:
                return False, 'identity_unverified'
            return True, email
        code = {401: 'token_rejected', 403: 'permission_denied', 429: 'rate_limited'}.get(response.status_code, 'service_error')
        return False, f'{code}: userinfo HTTP {response.status_code}'
    except Exception as exc:
        return False, f'network_error: {type(exc).__name__}'


def transient_auth_error(info):
    return str(info).startswith(('network_error', 'service_error', 'rate_limited', 'permission_denied', 'identity_missing'))


def expected_email(root, profile):
    rows = read_json(Path(root) / 'accounts.json', [])
    for row in rows if isinstance(rows, list) else []:
        if row.get('profile_name') == profile:
            email = row.get('google_email') or str(row.get('name', '')).removeprefix('Google_')
            if '@' in email:
                return email
    return profile if '@' in profile else ''


def flow_pages(context):
    result = []
    for page in list(context.pages):
        try:
            if not page.is_closed() and urlsplit(page.url).hostname in FLOW_HOSTS:
                result.append(page)
        except Exception:
            pass
    return result


class SessionObserver:
    """Observe only Flow/aisandbox traffic in the explicitly selected context."""
    def __init__(self, context):
        self.context = context
        self.candidates = []
        self.diagnostic = 'flow_session_missing'
        context.on('request', self.on_request)
        context.on('response', self.on_response)

    def remember(self, token, email, source):
        if token and not any(item[0] == token for item in self.candidates):
            self.candidates.append((token, email, source))
            self.candidates = self.candidates[-8:]

    def on_request(self, request):
        try:
            url = urlsplit(request.url)
            if url.scheme != 'https' or url.hostname != 'aisandbox-pa.googleapis.com':
                return
            if urlsplit(request.frame.url).hostname not in FLOW_HOSTS:
                return
            value = request.header_value('authorization') or ''
            if value.startswith('Bearer ya29.'):
                self.remember(value[7:].strip(), '', 'flow-api-request')
        except Exception:
            pass

    def on_response(self, response):
        try:
            url = urlsplit(response.url)
            if url.scheme != 'https' or url.hostname not in FLOW_HOSTS or url.path not in ('/api/auth/session', '/fx/api/auth/session'):
                return
            self.consume(response, url.hostname)
        except Exception:
            pass

    def consume(self, response, host):
        if response.status != 200:
            self.diagnostic = f'session_http: {host} HTTP {response.status}'
            return
        if 'json' not in response.headers.get('content-type', ''):
            self.diagnostic = f'session_html: {host} trả HTML, chưa có JSON session'
            return
        payload = response.json()
        token, email = session_values(payload)
        self.remember(token, email, 'flow-session-json')
        if token:
            self.diagnostic = 'token_received'
        elif email:
            self.diagnostic = 'token_missing: session có email, chưa có access token'
        else:
            self.diagnostic = 'flow_session_missing: session rỗng hoặc schema chưa hỗ trợ'

    def probe(self, deadline):
        # APIRequestContext shares the browser cookie jar and handles Set-Cookie.
        # No cross-origin JS fetch or navigation away from the user's login tab.
        for endpoint in SESSION_URLS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                response = self.context.request.get(endpoint, timeout=min(3000, max(1, int(remaining * 1000))))
                try:
                    self.consume(response, urlsplit(endpoint).hostname)
                finally:
                    response.dispose()
            except Exception as exc:
                self.diagnostic = f'session_network: {type(exc).__name__}'
        if not self.candidates and deadline - time.monotonic() > 0:
            html_candidates = []
            for p in reversed(flow_pages(self.context)):
                try:
                    html_candidates.append(p.content() or '')
                except Exception:
                    pass
            try:
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    response = self.context.request.get(FLOW_HOME, timeout=min(5000, max(1, int(remaining * 1000))))
                    try:
                        if response.status == 200:
                            html_candidates.append(response.text() or '')
                    finally:
                        response.dispose()
            except Exception:
                pass
            for html in html_candidates:
                if not html:
                    continue
                at_match = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
                email_match = re.search(r'"oPEP7c"\s*:\s*"([^"]+@[^"]+)"', html)
                if at_match and email_match:
                    try:
                        cookies = self.context.cookies([
                            'https://flow.google.com',
                            'https://labs.google',
                            'https://www.google.com',
                            'https://google.com',
                            'https://accounts.google.com',
                        ])
                        flow_tok = _cookies_list_to_flow_token(cookies)
                        if flow_tok:
                            self.remember(flow_tok, email_match.group(1).strip(), 'flow-wiz-session')
                            self.diagnostic = 'token_received'
                            break
                    except Exception:
                        pass


def probe_session(context, page=None, allow_navigation=False):
    observer = SessionObserver(context)
    try:
        observer.probe(time.monotonic() + 9)
        if observer.candidates:
            return observer.candidates[-1]
        return '', '', observer.diagnostic
    finally:
        context.remove_listener('request', observer.on_request)
        context.remove_listener('response', observer.on_response)


def project_from_context(context):
    for page in reversed(flow_pages(context)):
        url = urlsplit(page.url)
        value = parse_qs(url.query).get('project', [''])[0]
        match = re.search(r'/project/([0-9a-fA-F-]{36})(?:/|$)', url.path)
        if value or match:
            return value or match.group(1)
    for page in reversed(flow_pages(context)):
        try:
            html = page.content() or ''
            match = re.search(r'/project/([0-9a-fA-F-]{36})', html)
            if match:
                return match.group(1)
        except Exception:
            pass
    return ''


def launch_options(root, name, headless):
    """Persist the browser choice, use it identically for login and refresh."""
    config = Path(root) / 'browser_settings' / (name + '.json')
    settings = read_json(config, {}) or {}
    options = {'headless': headless, 'timeout': 20000}
    channel = settings.get('channel', 'chrome')
    if channel in ('chrome', 'msedge'):
        options['channel'] = channel
    try:
        from proxy_manager import _global_proxy_manager
        if _global_proxy_manager:
            server = _global_proxy_manager.get_chrome_proxy_arg()
            if server:
                options['proxy'] = {'server': server}
    except ImportError:
        pass
    if not config.exists():
        atomic_json(config, {'channel': channel, 'login_mode': settings.get('login_mode', 'system_chrome')})
    return options


def find_system_chrome():
    """Use installed Chrome, not the browser bundled for automated tests."""
    for env, suffix in (('PROGRAMFILES', 'Google/Chrome/Application/chrome.exe'),
                        ('PROGRAMFILES(X86)', 'Google/Chrome/Application/chrome.exe'),
                        ('LOCALAPPDATA', 'Google/Chrome/Application/chrome.exe')):
        base = os.environ.get(env)
        if base:
            candidate = Path(base) / suffix
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError('chrome_missing: cần cài Google Chrome trước khi đăng nhập')


def _is_chrome_profile_open(profile_dir: Path) -> bool:
    """Return True if a Chrome instance currently holds an exclusive OS lock on profile_dir/lockfile."""
    lockfile = Path(profile_dir) / 'lockfile'
    if not lockfile.exists():
        return False
    try:
        lockfile.unlink()
        return False
    except PermissionError:
        return True
    except OSError:
        return False


class _Win32DesktopProcess:
    """Process handle returned by CreateProcessW on WinSta0\\Default, compatible with subprocess.Popen API."""
    def __init__(self, pid: int, h_process: int):
        self.pid = int(pid or 0)
        self._h_process = int(h_process or 0)
        self.returncode = None

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        if not self._h_process or os.name != 'nt':
            self.returncode = 0
            return 0
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.windll.kernel32
            k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
            k32.WaitForSingleObject.restype = wintypes.DWORD
            k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
            k32.GetExitCodeProcess.restype = wintypes.BOOL
            wait_res = k32.WaitForSingleObject(ctypes.c_void_p(self._h_process), 0)
            if wait_res == 0x00000102:  # WAIT_TIMEOUT -> still running
                return None
            code = wintypes.DWORD(0)
            if k32.GetExitCodeProcess(ctypes.c_void_p(self._h_process), ctypes.byref(code)):
                if code.value == 259 and wait_res != 0:  # STILL_ACTIVE
                    return None
                self.returncode = int(code.value)
            else:
                self.returncode = 0
            self._close_handle()
            return self.returncode
        except Exception:
            return None

    def wait(self, timeout: float | None = None):
        t0 = time.monotonic()
        while self.poll() is None:
            if timeout is not None and (time.monotonic() - t0) >= timeout:
                raise subprocess.TimeoutExpired(cmd=f'pid={self.pid}', timeout=timeout)
            time.sleep(0.2)
        return self.returncode

    def terminate(self):
        if self.poll() is None and self.pid > 0:
            subprocess.run(
                ['taskkill', '/PID', str(self.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            self._close_handle()

    kill = terminate

    def _close_handle(self):
        if self._h_process and os.name == 'nt':
            try:
                import ctypes
                k32 = ctypes.windll.kernel32
                k32.CloseHandle.argtypes = [ctypes.c_void_p]
                k32.CloseHandle(ctypes.c_void_p(self._h_process))
            except Exception:
                pass
            self._h_process = 0

    def __del__(self):
        try:
            self._close_handle()
        except Exception:
            pass


def spawn_process_on_user_desktop(cmd_list, env=None, cwd=None):
    """Spawn a GUI process explicitly onto WinSta0\\Default so it ALWAYS appears on the user's real desktop
    even when the server process was started inside a background/sandbox desktop (e.g. exebox-*)."""
    if os.name != 'nt':
        return subprocess.Popen(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, cwd=cwd)
    try:
        import ctypes
        from ctypes import wintypes

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('lpReserved', wintypes.LPWSTR),
                ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR),
                ('dwX', wintypes.DWORD),
                ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD),
                ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD),
                ('cbReserved2', wintypes.WORD),
                ('lpReserved2', ctypes.POINTER(wintypes.BYTE)),
                ('hStdInput', wintypes.HANDLE),
                ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('hProcess', ctypes.c_void_p),
                ('hThread', ctypes.c_void_p),
                ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD),
            ]

        k32 = ctypes.windll.kernel32
        k32.CreateProcessW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.LPCWSTR,
            ctypes.POINTER(STARTUPINFOW),
            ctypes.POINTER(PROCESS_INFORMATION),
        ]
        k32.CreateProcessW.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [ctypes.c_void_p]

        cmdline = subprocess.list2cmdline([str(x) for x in cmd_list])
        cmd_buf = ctypes.create_unicode_buffer(cmdline)
        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.lpDesktop = 'WinSta0\\Default'
        si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
        si.wShowWindow = 1       # SW_SHOWNORMAL
        pi = PROCESS_INFORMATION()

        # Build Unicode environment block if custom env is provided
        env_block = None
        creation_flags = 0
        if isinstance(env, dict):
            env_items = [f'{k}={v}' for k, v in env.items() if k and '\x00' not in str(k) and '\x00' not in str(v)]
            env_str = '\x00'.join(env_items) + '\x00\x00'
            env_block = ctypes.create_unicode_buffer(env_str)
            creation_flags |= 0x00000400  # CREATE_UNICODE_ENVIRONMENT

        ok = k32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            creation_flags,
            ctypes.cast(env_block, ctypes.c_void_p) if env_block is not None else None,
            str(cwd) if cwd else None,
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if ok:
            if pi.hThread:
                k32.CloseHandle(ctypes.c_void_p(pi.hThread))
            return _Win32DesktopProcess(pi.dwProcessId, pi.hProcess)
    except Exception:
        pass
    return subprocess.Popen(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, cwd=cwd)


def _get_chrome_pids_for_profile(profile_dir: Path, include_headless: bool = False) -> set[int]:
    """Return all running chrome.exe PIDs whose command line references profile_dir."""
    if os.name != 'nt' or not profile_dir:
        return set()
    try:
        pdir_norm = str(Path(profile_dir).resolve()).replace("'", "''").lower()
        hl_filter = "" if include_headless else " -and ($_.CommandLine.ToLower() -notlike '*--headless*')"
        ps_cmd = (
            f"$procs = Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | "
            f"Where-Object {{ $_.CommandLine -and $_.CommandLine.ToLower().Contains('{pdir_norm}'){hl_filter} }}; "
            f"foreach ($p in $procs) {{ Write-Output $p.ProcessId }}"
        )
        out = subprocess.check_output(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            text=True,
            timeout=4,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return {int(x.strip()) for x in out.splitlines() if x.strip().isdigit()}
    except Exception:
        return set()


def has_visible_chrome_profile_window(profile_dir: Path) -> int:
    """Return the PID (> 0) of a visible Chrome_WidgetWin_1 window on WinSta0\\Default for profile_dir, or 0 if none."""
    if os.name != 'nt':
        return 0
    pdir = Path(profile_dir).resolve()
    if not _is_chrome_profile_open(pdir):
        return 0
    pids = _get_chrome_pids_for_profile(pdir, include_headless=False)
    if not pids:
        return 0
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        u32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
        u32.OpenDesktopW.restype = ctypes.c_void_p
        u32.CloseDesktop.argtypes = [ctypes.c_void_p]
        u32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
        u32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        u32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        u32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        u32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]

        found_pid = [0]

        def _cb(hwnd, lparam):
            if not u32.IsWindowVisible(hwnd):
                return True
            cls = ctypes.create_unicode_buffer(128)
            u32.GetClassNameW(hwnd, cls, 128)
            if cls.value != 'Chrome_WidgetWin_1':
                return True
            if u32.GetWindowTextLengthW(hwnd) <= 0:
                return True
            pid = ctypes.c_ulong()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                found_pid[0] = int(pid.value)
                return False
            return True

        cb_ref = WNDENUMPROC(_cb)
        hd = u32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hd:
            try:
                u32.EnumDesktopWindows(hd, cb_ref, 0)
            finally:
                u32.CloseDesktop(hd)
        return found_pid[0]
    except Exception:
        return 0


def current_desktop_name() -> str:
    """Return the name of the Windows Desktop the calling thread is attached to (e.g. 'Default' or 'exebox-...')."""
    if os.name != 'nt':
        return 'Default'
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        u32.GetThreadDesktop.argtypes = [wintypes.DWORD]
        u32.GetThreadDesktop.restype = ctypes.c_void_p
        u32.GetUserObjectInformationW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        h_desk = u32.GetThreadDesktop(k32.GetCurrentThreadId())
        buf = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD(0)
        if u32.GetUserObjectInformationW(h_desk, 2, buf, ctypes.sizeof(buf), ctypes.byref(needed)):
            return buf.value or 'Default'
    except Exception:
        pass
    return 'Default'


def cleanup_hidden_desktop_windows() -> int:
    """Kill orphaned File Explorer, Photo Viewer, and Chrome windows that were previously spawned onto hidden exebox-* desktops
    so Windows Explorer never deduplicates/routes folder-open requests to a hidden desktop."""
    if os.name != 'nt':
        return 0
    killed = 0
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        ENUM_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_wchar_p, ctypes.c_void_p)
        u32.GetProcessWindowStation.restype = ctypes.c_void_p
        u32.EnumDesktopsW.argtypes = [ctypes.c_void_p, ENUM_PROC, ctypes.c_void_p]
        u32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
        u32.OpenDesktopW.restype = ctypes.c_void_p
        u32.CloseDesktop.argtypes = [ctypes.c_void_p]
        u32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
        u32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        u32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]

        desks = []
        def _d_cb(name, lparam):
            if name:
                desks.append(name)
            return True
        d_ref = ENUM_PROC(_d_cb)
        u32.EnumDesktopsW(u32.GetProcessWindowStation(), d_ref, 0)

        default_pids = {os.getpid()}
        hd_def = u32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hd_def:
            def _def_cb(hwnd, lparam):
                pid = ctypes.c_ulong()
                u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value:
                    default_pids.add(int(pid.value))
                return True
            def_ref = WNDENUMPROC(_def_cb)
            try:
                u32.EnumDesktopWindows(hd_def, def_ref, 0)
            finally:
                u32.CloseDesktop(hd_def)

        hidden_pids = set()
        target_classes = {'CabinetWClass', 'ExploreWClass', 'WinUIDesktopWin32WindowClass', 'Chrome_WidgetWin_1'}
        for dname in desks:
            if dname.lower() == 'default':
                continue
            hd = u32.OpenDesktopW(dname, 0, False, 0x01FF)
            if not hd:
                continue
            def _hid_cb(hwnd, lparam):
                cls = ctypes.create_unicode_buffer(128)
                u32.GetClassNameW(hwnd, cls, 128)
                if cls.value in target_classes:
                    pid = ctypes.c_ulong()
                    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value and int(pid.value) not in default_pids:
                        hidden_pids.add(int(pid.value))
                return True
            hid_ref = WNDENUMPROC(_hid_cb)
            try:
                u32.EnumDesktopWindows(hd, hid_ref, 0)
            finally:
                u32.CloseDesktop(hd)

        for pid_val in hidden_pids:
            subprocess.run(
                ['taskkill', '/PID', str(pid_val), '/T', '/F'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            killed += 1
    except Exception:
        pass
    return killed


def _force_hwnd_to_foreground(u32, k32, hwnd_int: int, x: int = 110, y: int = 50, w: int = 1280, h: int = 860, resize: bool = True) -> None:
    """Reliably bring hwnd_int to the foreground on WinSta0\\Default above Microsoft Edge App mode using AttachThreadInput + HWND_TOPMOST."""
    from ctypes import wintypes
    u32.IsIconic.argtypes = [ctypes.c_void_p]
    u32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    u32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    u32.BringWindowToTop.argtypes = [ctypes.c_void_p]
    u32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    u32.GetForegroundWindow.restype = ctypes.c_void_p
    u32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    u32.GetWindowThreadProcessId.restype = wintypes.DWORD
    u32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    k32.GetCurrentThreadId.restype = wintypes.DWORD

    best_hwnd = ctypes.c_void_p(hwnd_int)
    fg_hwnd = u32.GetForegroundWindow()
    cur_tid = k32.GetCurrentThreadId()
    fg_tid = 0
    attached = False
    if fg_hwnd:
        dummy_pid = ctypes.c_ulong()
        fg_tid = u32.GetWindowThreadProcessId(ctypes.c_void_p(fg_hwnd), ctypes.byref(dummy_pid))
        if fg_tid and fg_tid != cur_tid:
            attached = bool(u32.AttachThreadInput(cur_tid, fg_tid, True))
    try:
        u32.AllowSetForegroundWindow(-1)
        u32.keybd_event(0x12, 0, 1, 0)
        u32.keybd_event(0x12, 0, 3, 0)
        if u32.IsIconic(best_hwnd):
            u32.ShowWindow(best_hwnd, 9)  # SW_RESTORE
        else:
            u32.ShowWindow(best_hwnd, 5)  # SW_SHOW
        HWND_TOPMOST = ctypes.c_void_p(-1 & ((1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1))
        HWND_NOTOPMOST = ctypes.c_void_p(-2 & ((1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1))
        flags_top = 0x0040 if resize else (0x0001 | 0x0002 | 0x0040)
        u32.SetWindowPos(best_hwnd, HWND_TOPMOST, x, y, w, h, flags_top)
        u32.BringWindowToTop(best_hwnd)
        u32.SetForegroundWindow(best_hwnd)
        time.sleep(0.15)
        u32.SetWindowPos(best_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
        u32.SetForegroundWindow(best_hwnd)
    finally:
        if attached and fg_tid:
            u32.AttachThreadInput(cur_tid, fg_tid, False)


def list_default_desktop_explorer_hwnds() -> set[int]:
    """Return all currently open CabinetWClass (File Explorer) HWNDs on WinSta0\\Default."""
    if os.name != 'nt':
        return set()
    hwnds = set()
    try:
        import ctypes
        u32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        u32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
        u32.OpenDesktopW.restype = ctypes.c_void_p
        u32.CloseDesktop.argtypes = [ctypes.c_void_p]
        u32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
        u32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        u32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

        def _cb(hwnd, lparam):
            if u32.IsWindowVisible(hwnd):
                cls = ctypes.create_unicode_buffer(128)
                u32.GetClassNameW(hwnd, cls, 128)
                if cls.value in ('CabinetWClass', 'ExploreWClass'):
                    hwnds.add(int(hwnd))
            return True

        cb_ref = WNDENUMPROC(_cb)
        hd = u32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hd:
            try:
                u32.EnumDesktopWindows(hd, cb_ref, 0)
            finally:
                u32.CloseDesktop(hd)
    except Exception:
        pass
    return hwnds


def bring_explorer_window_to_front(target_path: Path, before_hwnds: set[int] | None = None) -> bool:
    """Bring the newly opened (or matching) Windows File Explorer window on WinSta0\\Default to the very front."""
    if os.name != 'nt':
        return False
    p = Path(target_path).resolve()
    folder_name = (p.parent.name if p.is_file() else p.name).lower()
    prev_set = set(before_hwnds or ())
    result_box = [False]

    def _worker():
        try:
            import ctypes
            u32 = ctypes.windll.user32
            k32 = ctypes.windll.kernel32
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            u32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
            u32.OpenDesktopW.restype = ctypes.c_void_p
            u32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            u32.CloseDesktop.argtypes = [ctypes.c_void_p]
            u32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
            u32.IsWindowVisible.argtypes = [ctypes.c_void_p]
            u32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
            u32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
            u32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

            hd = u32.OpenDesktopW('Default', 0, False, 0x01FF)
            if hd:
                u32.SetThreadDesktop(hd)
            candidates = []

            def _cb(hwnd, lparam):
                if not u32.IsWindowVisible(hwnd):
                    return True
                cls = ctypes.create_unicode_buffer(128)
                u32.GetClassNameW(hwnd, cls, 128)
                if cls.value not in ('CabinetWClass', 'ExploreWClass'):
                    return True
                tlen = u32.GetWindowTextLengthW(hwnd)
                title = ''
                if tlen > 0:
                    tbuf = ctypes.create_unicode_buffer(tlen + 1)
                    u32.GetWindowTextW(hwnd, tbuf, tlen + 1)
                    title = (tbuf.value or '').lower()
                score = 1
                if int(hwnd) not in prev_set:
                    score += 100
                if folder_name and folder_name in title:
                    score += 50
                candidates.append((score, int(hwnd)))
                return True

            cb_ref = WNDENUMPROC(_cb)
            if hd:
                try:
                    u32.EnumDesktopWindows(hd, cb_ref, 0)
                finally:
                    u32.CloseDesktop(hd)
            if not candidates:
                return
            candidates.sort(key=lambda x: x[0], reverse=True)
            _force_hwnd_to_foreground(u32, k32, candidates[0][1], x=180, y=80, w=1160, h=760, resize=False)
            result_box[0] = True
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=1.5)
    return result_box[0]


def _bring_chrome_window_to_front(target_pid: int = 0, profile_dir: Path | None = None) -> bool:
    """Bring the newly launched Google Chrome (chrome.exe, never msedge.exe) window on WinSta0\\Default to the very front."""
    if os.name != 'nt':
        return False
    target_pids = {int(target_pid)} if target_pid and int(target_pid) > 0 else set()
    if not target_pids and profile_dir is not None:
        target_pids |= _get_chrome_pids_for_profile(Path(profile_dir), include_headless=False)

    result_box = [False]

    def _worker(pids_to_match: set[int]):
        try:
            import ctypes
            from ctypes import wintypes
            u32 = ctypes.windll.user32
            k32 = ctypes.windll.kernel32
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            u32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
            u32.OpenDesktopW.restype = ctypes.c_void_p
            u32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            u32.SetThreadDesktop.restype = wintypes.BOOL
            u32.CloseDesktop.argtypes = [ctypes.c_void_p]
            u32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
            u32.IsWindowVisible.argtypes = [ctypes.c_void_p]
            u32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
            u32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
            u32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
            u32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k32.OpenProcess.restype = ctypes.c_void_p
            k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p, ctypes.POINTER(wintypes.DWORD)]
            k32.CloseHandle.argtypes = [ctypes.c_void_p]

            hd = u32.OpenDesktopW('Default', 0, False, 0x01FF)
            if hd:
                u32.SetThreadDesktop(hd)
            matched_hwnds = []

            def _enum_cb(hwnd, lparam):
                if not u32.IsWindowVisible(hwnd):
                    return True
                cls_buf = ctypes.create_unicode_buffer(128)
                u32.GetClassNameW(hwnd, cls_buf, 128)
                if cls_buf.value != 'Chrome_WidgetWin_1':
                    return True
                t_len = u32.GetWindowTextLengthW(hwnd)
                if t_len <= 0:
                    return True
                t_buf = ctypes.create_unicode_buffer(t_len + 1)
                u32.GetWindowTextW(hwnd, t_buf, t_len + 1)
                title = t_buf.value or ''
                if 'restore pages' in title.lower():
                    return True
                pid = ctypes.c_ulong()
                u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pids_to_match and pid.value not in pids_to_match:
                    return True
                h_proc = k32.OpenProcess(0x1000, False, pid.value)
                exe_path = ''
                if h_proc:
                    try:
                        p_buf = ctypes.create_unicode_buffer(1024)
                        sz = wintypes.DWORD(1024)
                        if k32.QueryFullProcessImageNameW(h_proc, 0, p_buf, ctypes.byref(sz)):
                            exe_path = (p_buf.value or '').lower()
                    finally:
                        k32.CloseHandle(h_proc)
                if exe_path and not exe_path.endswith('chrome.exe'):
                    return True
                score = 100 if (pids_to_match and pid.value in pids_to_match) else 1
                if any(k in title.lower() for k in ('flow', 'google', 'sign in', 'đăng nhập', 'chrome')):
                    score += 10
                matched_hwnds.append((score, int(hwnd)))
                return True

            cb_ref = WNDENUMPROC(_enum_cb)
            if hd:
                try:
                    u32.EnumDesktopWindows(hd, cb_ref, 0)
                finally:
                    u32.CloseDesktop(hd)
            if not matched_hwnds:
                return
            matched_hwnds.sort(key=lambda x: x[0], reverse=True)
            _force_hwnd_to_foreground(u32, k32, matched_hwnds[0][1], x=110, y=50, w=1280, h=860, resize=True)
            result_box[0] = True
        except Exception:
            pass

    t = threading.Thread(target=_worker, args=(target_pids,), daemon=True)
    t.start()
    t.join(timeout=1.5)
    if not result_box[0] and profile_dir is not None and target_pid > 0:
        extra_pids = _get_chrome_pids_for_profile(Path(profile_dir), include_headless=False)
        if extra_pids and extra_pids != target_pids:
            t2 = threading.Thread(target=_worker, args=(extra_pids,), daemon=True)
            t2.start()
            t2.join(timeout=1.5)
    return result_box[0]


def close_chrome_profile_processes(profile_dir: Path, timeout_sec: float = 4.0) -> bool:
    """Gracefully close any running chrome.exe instance using `--user-data-dir=<profile_dir>` so its cookies are flushed and lockfile released."""
    pdir = Path(profile_dir).resolve()
    if not _is_chrome_profile_open(pdir):
        return True
    if os.name == 'nt':
        try:
            import ctypes
            u32 = ctypes.windll.user32
            pids = _get_chrome_pids_for_profile(pdir, include_headless=True)
            if pids:
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                u32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
                u32.OpenDesktopW.restype = ctypes.c_void_p
                u32.CloseDesktop.argtypes = [ctypes.c_void_p]
                u32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
                u32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
                u32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]

                def _close_cb(hwnd, lparam):
                    pid = ctypes.c_ulong()
                    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value in pids:
                        u32.PostMessageW(ctypes.c_void_p(hwnd), 0x0010, 0, 0)  # WM_CLOSE for clean cookie flush
                    return True

                cb_ref = WNDENUMPROC(_close_cb)
                hd = u32.OpenDesktopW('Default', 0, False, 0x01FF)
                if hd:
                    try:
                        u32.EnumDesktopWindows(hd, cb_ref, 0)
                    finally:
                        u32.CloseDesktop(hd)
                t0 = time.monotonic()
                while time.monotonic() - t0 < min(2.2, timeout_sec):
                    if not _is_chrome_profile_open(pdir):
                        return True
                    time.sleep(0.2)
                for pid_val in pids:
                    subprocess.run(
                        ['taskkill', '/PID', str(pid_val), '/T', '/F'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                    )
        except Exception:
            pass
    t1 = time.monotonic()
    while time.monotonic() - t1 < timeout_sec:
        if not _is_chrome_profile_open(pdir):
            return True
        time.sleep(0.2)
    return not _is_chrome_profile_open(pdir)


def _profile_has_google_cookies_on_disk(profile_dir: Path) -> bool:
    """Return True if the Chrome profile's Cookies SQLite store contains authenticated Google session cookies."""
    pdir = Path(profile_dir).resolve()
    def_dir = pdir / 'Default'
    if not def_dir.is_dir():
        return False
    markers = (b'__Secure-1PSID', b'__Secure-3PSID', b'SAPISID', b'HSID', b'SSID')
    for rel in ('Network/Cookies', 'Network/Cookies-wal', 'Network/Cookies-journal', 'Cookies', 'Cookies-wal'):
        cpath = def_dir / rel
        if cpath.is_file():
            try:
                raw = cpath.read_bytes()
                if b'google.com' in raw and any(m in raw for m in markers):
                    return True
            except Exception:
                pass
    return False


def _ensure_chrome_profile_display_name(profile_dir: Path, custom_label: str = '') -> None:
    """Set a clear custom profile name in Default/Preferences if Preferences already exists."""
    try:
        pdir = Path(profile_dir).resolve()
        if _is_chrome_profile_open(pdir):
            return
        pref_file = pdir / 'Default' / 'Preferences'
        if not pref_file.is_file():
            return
        data = read_json(pref_file, {})
        if not isinstance(data, dict) or not data:
            return
        prof_sec = data.get('profile')
        if not isinstance(prof_sec, dict):
            prof_sec = {}
        prof_sec['name'] = custom_label or f'Flow: {pdir.name}'
        prof_sec['exit_type'] = 'Normal'
        prof_sec['exited_cleanly'] = True
        data['profile'] = prof_sec
        atomic_json(pref_file, data)
    except Exception:
        pass


def native_login_command(executable, profile_dir):
    # Pure isolated Chrome profile per Google Flow account (no extension loaded here).
    pdir = Path(profile_dir).resolve()
    _ensure_chrome_profile_display_name(pdir)
    return [
        executable,
        '--user-data-dir=' + str(pdir),
        '--profile-directory=Default',
        '--no-first-run',
        '--no-default-browser-check',
        '--hide-crash-restore-bubble',
        '--disable-background-mode',
        '--new-window',
        '--window-size=1280,860',
        '--window-position=110,50',
        FLOW_HOME,
    ]


def manual_chrome_login(root, profile, cancelled, status, deadline):
    """The human owns sign-in. Never attach automation to the login window."""
    if cancelled():
        return 'cancelled: đã dừng trước khi mở Chrome'
    profile_paths(root, profile)  # validate before constructing settings paths
    executable = find_system_chrome()
    config = Path(root) / 'browser_settings' / (profile + '.json')
    previous = read_store_json(config, {})
    if not isinstance(previous, dict):
        raise ValueError('storage_invalid: browser_settings')
    # Preserve old Chromium data/snapshot. Chrome owns a separate directory;
    # never copy a running browser database or silently change its encryption.
    settings = dict(previous, channel='chrome', login_mode='system_chrome')
    atomic_json(config, settings)
    directory, _ = profile_paths(root, profile)
    directory.mkdir(parents=True, exist_ok=True)
    # If a headless or hidden-desktop Chrome instance holds lockfile without any visible window on Default desktop, close it first
    if _is_chrome_profile_open(directory) and not has_visible_chrome_profile_window(directory):
        close_chrome_profile_processes(directory, timeout_sec=4.0)
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.keybd_event(0x12, 0, 1, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 3, 0)
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass
    clean_env = os.environ.copy()
    for _pk in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
        clean_env.pop(_pk, None)
    process = spawn_process_on_user_desktop(native_login_command(executable, directory), env=clean_env)
    status(f'Chrome thường đã mở (Profile riêng: {profile}). Đăng nhập Google Flow 1 lần rồi ĐÓNG cửa sổ Chrome này (hoặc bấm "🔄 Tự Lấy Cookie Mới") để tool tự động trích xuất & lưu Cookie/Token!')
    # Wait up to 3.6s for Chrome to create lockfile and bring the Chrome window on WinSta0\Default to the very front
    for wait_step in range(9):
        time.sleep(0.4)
        if wait_step in (1, 2, 4, 6, 8):
            _bring_chrome_window_to_front(getattr(process, 'pid', 0), profile_dir=directory)
        if _is_chrome_profile_open(directory) and wait_step >= 4:
            break
    while process.poll() is None or _is_chrome_profile_open(directory):
        if cancelled():
            return 'cancelled: đã dừng chờ; cửa sổ Chrome và dữ liệu được giữ nguyên'
        if time.monotonic() >= deadline:
            return 'manual_login_timeout: chưa hoàn tất; cửa sổ Chrome và dữ liệu vẫn được giữ nguyên'
        time.sleep(.3)
    if cancelled():
        return 'cancelled: đã dừng chờ'
    time.sleep(0.5)
    status(f'Đang kiểm tra và tự động trích xuất Cookie/Token từ Profile Chrome "{profile}" vừa đóng...')
    return ''


def is_google_signin_rejected(pages):
    for page in pages:
        url = urlsplit(page.url)
        if url.hostname == 'accounts.google.com' and ('/signin/rejected' in url.path or '/deniedsigninrejected' in url.path):
            return True
    return False


def has_signed_in_flow_ui(context):
    """UI evidence only: not OAuth identity verification or API readiness."""
    for page in flow_pages(context):
        try:
            if urlsplit(page.url).hostname != 'flow.google.com':
                continue
            signout = page.locator('a[href*="accounts.google.com/SignOutOptions"]').count() > 0
            projects = page.locator('a[href*="/project/"]').count() > 0
            if signout and (projects or '/project/' in urlsplit(page.url).path):
                return True
        except Exception:
            pass
    return False


@dataclass(repr=False)
class AuthResult:
    ok: bool = False
    token: str = ''
    email: str = ''
    project: str = ''
    error: str = ''


def auth_attempt_text(root, profile, has_token=False):
    if not str(profile or '').strip():
        return 'Chưa liên kết với profile Chrome riêng'
    profile_paths(root, profile)
    attempt = read_json(Path(root) / 'auth_attempts' / (profile + '.json'), {}) or {}
    phase = attempt.get('phase', '')
    if phase in ('starting', 'awaiting_manual_close', 'checking_flow') and time.time() - attempt.get('updated_at', 0) > 720:
        return 'Lần kiểm tra trước đã gián đoạn; bấm kiểm tra lại'
    labels = {
        'starting': 'Đang chuẩn bị kiểm tra phiên',
        'awaiting_manual_close': 'Chờ bạn vào Flow rồi đóng cửa sổ Chrome riêng',
        'checking_flow': 'Đang kiểm tra phiên Flow đã lưu',
        'google_signin_rejected': 'Google từ chối trình duyệt — dùng Chrome thường',
        'flow_token_unavailable': 'Chưa lấy được Bearer Google; profile vẫn được giữ — cần kiểm tra luồng lấy token',
        'flow_transport_required': 'Phiên Flow còn sau khi mở lại; chưa lấy được Bearer Google, không cần login lại',
        'manual_login_timeout': 'Hết thời gian chờ đóng Chrome; profile vẫn được giữ',
        'profile_busy': 'Profile đang mở; đóng riêng cửa sổ profile trước khi kiểm tra',
        'cancelled': 'Đã dừng kiểm tra; không xóa profile',
        'storage_write_failed': 'Lỗi lưu phiên — chưa hoàn tất',
        'verified': 'Đã xác minh token' if has_token else 'Đã xác minh phiên; chưa thấy token được lưu vào tài khoản',
    }
    return labels.get(phase, 'Đã có token lưu; cần kiểm tra hiệu lực' if has_token else 'Profile có sẵn / chưa có token được xác minh')


def acquire_session(root, profile, validator, persist, *, interactive=False,
                    use_snapshot=False, expected='', cancelled=lambda: False,
                    status=lambda message: None, timeout=None):
    """Keep non-secret phase diagnostics, without treating browser login as ready."""
    profile_paths(root, profile)
    path = Path(root) / 'auth_attempts' / (profile + '.json')
    attempt_id = uuid.uuid4().hex
    def record(phase, initial=False):
        try:
            previous = read_json(path, {}) or {}
            if not initial and previous.get('attempt_id') != attempt_id:
                return
            atomic_json(path, {'attempt_id': attempt_id, 'phase': phase, 'updated_at': time.time()})
        except (OSError, ValueError):
            pass  # Diagnostics cannot replace the actual persistence result.
    record('starting', initial=True)
    def report(message):
        record('awaiting_manual_close' if message.startswith('Chrome thường đã mở') else 'checking_flow')
        status(message)
    try:
        result = _acquire_session_impl(root, profile, validator, persist, interactive=interactive,
            use_snapshot=use_snapshot, expected=expected, cancelled=cancelled, status=report, timeout=timeout)
    except Exception:
        record('auth_error')
        raise
    known = {'google_signin_rejected', 'flow_token_unavailable', 'flow_transport_required', 'manual_login_timeout', 'profile_busy',
             'cancelled', 'storage_write_failed', 'browser_missing', 'browser_error', 'native_browser_error',
             'profile_missing', 'timeout', 'snapshot_not_verified', 'browser_closed'}
    code = result.error.split(':', 1)[0]
    record('verified' if result.ok else code if code in known else 'auth_error')
    return result


def _acquire_session_impl(root, profile, validator, persist, *, interactive=False,
                    use_snapshot=False, expected='', cancelled=lambda: False,
                    status=lambda message: None, timeout=None):
    """Run entirely on the calling worker thread, under its profile lock."""
    from playwright.sync_api import sync_playwright
    deadline = time.monotonic() + (timeout if timeout is not None else (600 if interactive else 14))
    if interactive:
        try:
            error = manual_chrome_login(root, profile, cancelled, status, deadline)
        except Exception as exc:
            return AuthResult(error='native_browser_error: ' + type(exc).__name__ + '; kiểm tra Chrome cài trên máy và quyền ghi profile')
        if error:
            return AuthResult(error=error)
        # Automated work starts only AFTER the human-controlled browser exits.
        interactive = False
        # Bound post-close extraction to ~15s so the profile is never locked for long.
        deadline = time.monotonic() + 15 if timeout is None else min(deadline, time.monotonic() + 15)
    profile_dir, snapshot = profile_paths(root, profile)
    settings = read_json(Path(root) / 'browser_settings' / (profile + '.json'), {}) or {}
    native = settings.get('login_mode', 'system_chrome') == 'system_chrome'
    if use_snapshot and native:
        metadata = read_json(Path(root) / 'session_metadata' / (profile + '.json'), {}) or {}
        if metadata.get('browser_mode') not in ('system_chrome', '', None) and not snapshot.is_file():
            return AuthResult(error='snapshot_not_verified: không dùng snapshot Chromium cũ cho Chrome mới')
    if not interactive and not (snapshot.is_file() if use_snapshot else profile_dir.is_dir()):
        return AuthResult(error='profile_missing: chưa có dữ liệu phiên cho profile này')
    if not interactive and not use_snapshot and _is_chrome_profile_open(profile_dir):
        return AuthResult(error='profile_busy: cửa sổ Chrome của profile này đang mở; hãy đóng cửa sổ Chrome đó để lưu/làm mới Cookie')
    if not interactive and not use_snapshot and not snapshot.is_file() and not _profile_has_google_cookies_on_disk(profile_dir):
        return AuthResult(error='flow_session_missing: chưa đăng nhập tài khoản Google trên cửa sổ Chrome của profile này; hãy bấm Mở Chrome để đăng nhập 1 lần')
    if interactive:
        profile_dir.mkdir(parents=True, exist_ok=True)
    context, browser = None, None
    last_diagnostic = 'flow_session_missing'
    try:
        with sync_playwright() as pw:
            try:
                options = launch_options(root, profile, not interactive)
                if use_snapshot:
                    browser = pw.chromium.launch(**options)
                    context = browser.new_context(storage_state=str(snapshot))
                else:
                    context = pw.chromium.launch_persistent_context(str(profile_dir), **options)
                context.set_default_timeout(3000)
                observer = SessionObserver(context)
                status('Đã mở đúng profile; đang chờ phiên Google Flow.')
                page = flow_pages(context)[-1] if flow_pages(context) else context.new_page()
                if urlsplit(page.url).hostname not in FLOW_HOSTS:
                    try:
                        page.goto(FLOW_HOME, wait_until='domcontentloaded', timeout=min(12000, max(1, int((deadline-time.monotonic())*1000))))
                    except Exception:
                        pass
                checked = {}
                next_probe, next_status = 0.0, 0.0
                probe_count = 0
                while time.monotonic() < deadline and not cancelled():
                    live = [p for p in context.pages if not p.is_closed()]
                    if is_google_signin_rejected(live):
                        return AuthResult(error='google_signin_rejected: Google chặn trình duyệt tự động. Đăng nhập bằng Chrome thường từ nút khóa; không lặp lại đăng nhập trong browser kiểm thử.')
                    if not live:
                        return AuthResult(error='browser_closed: đã đóng cửa sổ trước khi nhận được token Flow')
                    now = time.monotonic()
                    if now >= next_probe:
                        observer.probe(min(deadline, now + 6))
                        probe_count += 1
                        next_probe = time.monotonic() + 6
                    for token, session_email, source in reversed(observer.candidates):
                        if cancelled() or time.monotonic() >= deadline:
                            break
                        if token in checked and time.monotonic() - checked[token] < 15:
                            continue
                        checked[token] = time.monotonic()
                        valid, info = validator(token)
                        if not valid:
                            last_diagnostic = info
                            continue
                        if not identity_matches(expected, info):
                            last_diagnostic = 'wrong_account: email token không hợp lệ'
                            continue
                        if not persist(context, snapshot):
                            return AuthResult(error='storage_write_failed: không ghi được snapshot phiên đã xác minh')
                        project = project_from_context(context)
                        atomic_json(Path(root) / 'session_metadata' / (profile + '.json'), {
                            'profile': profile, 'email': info, 'project': project,
                            'verified_at': time.time(), 'token_source': source,
                            'browser_mode': 'system_chrome' if native else 'chromium',
                            'token_fingerprint': hashlib.sha256(token.encode()).hexdigest(),
                            'token': token,
                        })
                        return AuthResult(True, token, info, project)
                    pages = flow_pages(context)
                    about = any(urlsplit(p.url).path.startswith('/about') for p in pages)
                    if not interactive and probe_count >= 1 and about and not observer.candidates:
                        return AuthResult(error='flow_session_missing: profile này chưa đăng nhập Google Flow; hãy bấm Mở Chrome Đăng Nhập 1 lần')
                    if time.monotonic() >= next_status:
                        diagnostic = last_diagnostic if checked else observer.diagnostic
                        if about and not observer.candidates:
                            diagnostic = 'flow_session_missing: đang ở trang giới thiệu; bấm đăng nhập/Start trong cửa sổ Flow này'
                        status(diagnostic)
                        next_status = time.monotonic() + 12
                    # Pump Playwright events (plain time.sleep starves request callbacks).
                    live[-1].wait_for_timeout(400)
                if cancelled():
                    return AuthResult(error='cancelled: đã dừng; profile được giữ lại')
                if native and not checked:
                    if has_signed_in_flow_ui(context):
                        return AuthResult(error='flow_transport_required: đã quan sát phiên Flow đăng nhập và dự án sau khi mở lại profile; chưa nhận được Bearer Google. Cần kiểm tra luồng lấy Bearer riêng; token reCAPTCHA của Captcha Bridge không thay thế Bearer. Không đăng nhập lại; chưa xác minh email OAuth hoặc khả năng tạo video.')
                    return AuthResult(error='flow_token_unavailable: chưa nhận được Bearer token Flow. Profile vẫn được giữ. Cần kiểm tra luồng lấy Bearer của tài khoản; trạng thái này không chứng minh đã logout và không yêu cầu đổi extension.')
                return AuthResult(error='timeout: ' + (last_diagnostic if checked else observer.diagnostic))
            finally:
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
    except Exception as exc:
        message = str(exc).lower()
        if any(s in message for s in ('processsingleton', 'singletonlock', 'profile is in use', 'user data directory is already in use')):
            if snapshot.is_file():
                snap_data = read_json(snapshot, {}) or {}
                flow_tok = _cookies_list_to_flow_token(snap_data.get('cookies', []))
                if flow_tok:
                    valid, info = validator(flow_tok)
                    if valid and identity_matches(expected, info):
                        metadata = read_json(Path(root) / 'session_metadata' / (profile + '.json'), {}) or {}
                        project = metadata.get('project', '')
                        atomic_json(Path(root) / 'session_metadata' / (profile + '.json'), {
                            'profile': profile, 'email': info, 'project': project,
                            'verified_at': time.time(), 'token_source': 'flow-cookie-snapshot',
                            'browser_mode': 'system_chrome' if native else 'chromium',
                            'token_fingerprint': hashlib.sha256(flow_tok.encode()).hexdigest(),
                            'token': flow_tok,
                        })
                        return AuthResult(True, flow_tok, info, project)
                if not use_snapshot:
                    try:
                        return _acquire_session_impl(
                            root, profile, validator, persist,
                            interactive=False, use_snapshot=True,
                            expected=expected, cancelled=cancelled,
                            status=status, timeout=timeout,
                        )
                    except Exception:
                        pass
            return AuthResult(error='profile_busy: profile đang mở ở tác vụ khác')
        if 'executable doesn' in message or 'playwright install' in message:
            return AuthResult(error='browser_missing: chưa cài browser cho Python đang chạy tool')
        return AuthResult(error=f'browser_error: {type(exc).__name__}; profile và cookies được giữ lại')


def discover_profiles(root):
    root = Path(root)
    ignored = {'captcha_bridge_solver', 'test_sbx'}
    return sorted({p.name for name in ('profiles', 'native_profiles') for folder in [root / name]
                   if folder.exists() for p in folder.iterdir() if p.is_dir() and p.name.lower() not in ignored})


def pending_record(root, profile):
    profile_paths(root, profile)
    return {
        'name': 'Google_' + profile, 'profile_name': profile,
        'proxy_url': '', 'api_key': '', 'active': False,
        'auth_state': 'profile_known', 'google_email': '',
    }


def recover_login_commit(root):
    """Finish config/registry writes after an account commit interrupted by exit.

    The journal carries a fingerprint, never another plaintext token copy.
    Callers serialize the operation with the account-store lock.
    """
    root = Path(root)
    journal = read_store_json(root / 'login_commit.json', {}) or {}
    if not journal:
        return
    rows = read_store_json(root / 'accounts.json', [])
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError('storage_invalid: accounts.json')
    row = next((r for r in rows if r.get('profile_name') == journal.get('profile')), None)
    if not row or hashlib.sha256(str(row.get('api_key', '')).encode()).hexdigest() != journal.get('fingerprint'):
        return
    profile = row['profile_name']
    directory, snapshot = profile_paths(root, profile)
    registry = read_store_json(root / 'Flow_nhieu_worker_accounts.json', [])
    if isinstance(registry, dict):
        registry = next((registry[k] for k in ('accounts','items','data') if isinstance(registry.get(k), list)), [registry])
    if not isinstance(registry, list):
        raise ValueError('storage_invalid: registry không phải danh sách')
    entry = next((r for r in registry if isinstance(r, dict) and
        (r.get('email') == row.get('google_email') or Path(r.get('profile_dir', '')).name == profile)), None)
    if entry is None:
        entry = {}
        registry.append(entry)
    entry.update(email=row['google_email'], profile_dir=str(directory), cookies_file=str(snapshot),
                 project_id=row.get('proxy_url', ''), status='ready')
    atomic_json(root / 'Flow_nhieu_worker_accounts.json', registry)
    config = read_store_json(root / 'veo3_config.json', {})
    if not isinstance(config, dict):
        raise ValueError('storage_invalid: veo3_config.json')
    if not journal.get('refresh') or config.get('flow_profile_name') in (None, '', profile):
        config.update(bearer_token=row['api_key'], flow_profile_name=profile, project_id=row.get('proxy_url', ''))
    atomic_json(root / 'veo3_config.json', config)
    (root / 'login_commit.json').unlink(missing_ok=True)


_commit_lock = threading.Lock()

def commit_login(root, profile, email, token, project='', hint='', *, refresh=False):
    if not identity_matches('', email):
        raise ValueError('identity_missing')
    root = Path(root).resolve()
    profile_paths(root, profile)
    lock = ProfileLock(_commit_lock, root / 'locks' / 'account_commit.lock')
    with lock:
        recover_login_commit(root)
        rows = read_store_json(root / 'accounts.json', [])
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise ValueError('storage_invalid: accounts.json không phải danh sách')
        row = next((r for r in rows if r.get('profile_name') == profile), None)
        if row is None:
            row = next((r for r in rows if r.get('name') == hint or r.get('name') == 'Google_' + email), None)
        if row is None:
            if refresh:
                raise ValueError('account_missing: tài khoản đã bị xóa; không tạo lại từ refresh cũ')
            row = pending_record(root, profile)
            rows.append(row)
        if refresh and not token_result_is_current(root, profile, token):
            raise ValueError('stale_or_wrong_account: bỏ kết quả refresh cũ')
        row.update(name='Google_' + email, google_email=email, api_key=token,
                   proxy_url=project or row.get('proxy_url', ''), profile_name=profile,
                   auth_state='ready', active=row.get('active', True) if refresh else True, auth_revision=time.time_ns())
        atomic_json(root / 'login_commit.json', {
            'profile': profile, 'fingerprint': hashlib.sha256(token.encode()).hexdigest(), 'refresh': refresh})
        atomic_json(root / 'accounts.json', rows)
        recover_login_commit(root)
        return dict(row)
