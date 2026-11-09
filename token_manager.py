# -*- coding: utf-8 -*-
"""
=============================================================================
 TOKEN MANAGER — Tự Động Làm Mới Session Google Flow Khi Hết Hạn
=============================================================================
 Cơ chế:
   • Background thread kiểm tra token mỗi 20 phút
   • Khi nhận 401 hoặc cookie gần hết hạn → tự động refresh
   • Dùng extract_chrome_session.py để lấy token mới từ Chrome profile
   • Thread-safe, hỗ trợ nhiều profile đồng thời
   • Retry tự động sau khi refresh thành công

 Tích hợp:
   • Được gọi từ grok_video_tool._load_flow_cookie_header()
   • Được gọi từ fashion_motion_control_engine khi nhận HTTP 401
   • Server endpoint: POST /api/flow/token_manager_status

 Cách bật:
   import token_manager
   token_manager.enable(profiles=["leviettung04", "Default"])
   # hoặc:
   token_manager.TOKEN_MANAGER.start()
=============================================================================
"""
from __future__ import annotations

import os, sys, json, time, threading, logging, hashlib
from pathlib import Path
from typing import Optional, Callable

# ── Logging ────────────────────────────────────────────────────────────────
logger = logging.getLogger("token_manager")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[TokenMgr] %(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    logger.addHandler(_h)

log = logger.info
warn = logger.warning
err = logger.error

# ── Paths ──────────────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).parent
COOKIES_DIR = _THIS_DIR / "cookies"
DATA_DIR    = _THIS_DIR / "data" / "google_flow_grok"

# ── Constants ──────────────────────────────────────────────────────────────
# Thời gian token hợp lệ được coi là sắp hết (giây)
TOKEN_EXPIRY_BUFFER_SEC  = 30 * 60   # refresh trước 30 phút khi hết hạn
# Interval background checker (giây)
CHECK_INTERVAL_SEC       = 20 * 60   # kiểm tra mỗi 20 phút
# Thời gian cooldown tối thiểu giữa 2 lần refresh cùng profile (giây)
REFRESH_COOLDOWN_SEC     = 5 * 60    # không refresh quá 1 lần / 5 phút
# Timeout cho mỗi lần extract (giây)
EXTRACT_TIMEOUT_SEC      = 90

# ── State per profile ──────────────────────────────────────────────────────
class _ProfileState:
    def __init__(self, profile_name: str):
        self.name           = profile_name
        self.last_refresh   = 0.0      # epoch
        self.last_check     = 0.0
        self.refresh_count  = 0
        self.last_error     = ""
        self.refreshing     = False    # đang refresh
        self.valid          = False    # session hiện tại hợp lệ
        self.lock           = threading.Lock()
        self.email          = ""
        self.no_flow_access = False    # profile không có Google Flow PRO access
        self.skip_until     = 0.0     # bỏ qua refresh đến thời điểm này


class TokenManager:
    """
    Singleton quản lý việc tự động làm mới token cho nhiều Google profiles.
    """

    def __init__(self):
        self._profiles: dict[str, _ProfileState] = {}
        self._enabled  = False
        self._auto_profiles: list[str] = []  # profiles cần tự động refresh
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._global_lock = threading.Lock()
        self._on_refresh_callbacks: list[Callable] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def enable(self, profiles: Optional[list[str]] = None, auto: bool = True):
        """
        Bật Token Manager.
        profiles: danh sách profile cần theo dõi (None = tất cả có cookie file).
        auto: nếu True → tự động refresh khi hết hạn ở background.
        """
        self._enabled = True
        if profiles:
            self._auto_profiles = list(profiles)
        else:
            self._auto_profiles = self._discover_profiles()

        log(f"Enabled — theo dõi {len(self._auto_profiles)} profile(s): {self._auto_profiles}")

        if auto:
            self.start()

    def disable(self):
        self._enabled = False
        self.stop()
        log("Disabled")

    def start(self):
        """Khởi động background thread kiểm tra token."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._bg_loop, daemon=True, name="TokenMgrBG")
        self._thread.start()
        log("Background thread started")

    def stop(self):
        """Dừng background thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        log("Background thread stopped")

    def on_401(self, profile_name: str) -> str:
        """
        Gọi khi nhận HTTP 401. Tự động refresh và trả về cookie header mới.
        Returns: cookie header mới (rỗng nếu thất bại).
        """
        log(f"🔑 on_401 triggered for profile: {profile_name}")
        success = self._do_refresh(profile_name, reason="401")
        if success:
            return self._load_cookie_header(profile_name)
        return ""

    def ensure_valid(self, profile_name: str) -> str:
        """
        Đảm bảo session hợp lệ. Nếu hết hạn → refresh tự động.
        Returns: cookie header (rỗng nếu không lấy được).
        """
        if not self._enabled:
            return self._load_cookie_header(profile_name)

        state = self._get_or_create_state(profile_name)
        cookie_hdr = self._load_cookie_header(profile_name)

        # Check nếu cookie header rỗng hoặc sắp hết hạn
        if not cookie_hdr or self._is_session_stale(profile_name):
            if self._can_refresh(state):
                log(f"Session cần refresh cho profile: {profile_name}")
                self._do_refresh(profile_name, reason="ensure_valid")
                cookie_hdr = self._load_cookie_header(profile_name)

        return cookie_hdr

    def force_refresh(self, profile_name: str) -> bool:
        """Force refresh ngay lập tức (bỏ qua cooldown)."""
        log(f"Force refresh: {profile_name}")
        state = self._get_or_create_state(profile_name)
        with state.lock:
            state.last_refresh = 0  # Reset cooldown
        return self._do_refresh(profile_name, reason="force")

    def get_status(self) -> dict:
        """Trả về trạng thái của tất cả profiles đang quản lý."""
        last_refresh_overall = None
        if self._profiles:
            latest = max((s.last_refresh for s in self._profiles.values() if s.last_refresh), default=None)
            if latest:
                last_refresh_overall = time.strftime("%H:%M:%S", time.localtime(latest))
        status = {
            "ok": True,
            "enabled": self._enabled,
            "auto_profiles": self._auto_profiles,
            "running": self._thread.is_alive() if self._thread else False,
            "profiles": list(self._profiles.keys()),
            "last_refresh": last_refresh_overall or "Chưa có",
            "profile_details": {},
        }
        for pname, state in self._profiles.items():
            status["profile_details"][pname] = {
                "name": pname,
                "email": state.email,
                "valid": state.valid,
                "refreshing": state.refreshing,
                "refresh_count": state.refresh_count,
                "last_refresh": time.strftime("%H:%M:%S", time.localtime(state.last_refresh)) if state.last_refresh else "never",
                "last_error": state.last_error,
                "cookie_exists": (COOKIES_DIR / f"{pname}.json").exists(),
            }
        return status

    def add_refresh_callback(self, fn: Callable):
        """Đăng ký callback được gọi sau mỗi lần refresh thành công."""
        self._on_refresh_callbacks.append(fn)

    # ── Internal ───────────────────────────────────────────────────────────

    def _get_or_create_state(self, profile_name: str) -> _ProfileState:
        with self._global_lock:
            if profile_name not in self._profiles:
                self._profiles[profile_name] = _ProfileState(profile_name)
        return self._profiles[profile_name]

    def _can_refresh(self, state: _ProfileState) -> bool:
        """Kiểm tra cooldown."""
        if state.refreshing:
            return False
        if state.no_flow_access and time.time() < state.skip_until:
            return False  # Profile không có Flow access, skip tạm thời
        cooldown_ok = (time.time() - state.last_refresh) >= REFRESH_COOLDOWN_SEC
        return cooldown_ok

    def _is_session_stale(self, profile_name: str) -> bool:
        """Kiểm tra session sắp hết hạn dựa trên cookie expiry."""
        try:
            cookie_file = COOKIES_DIR / f"{profile_name}.json"
            if not cookie_file.exists():
                return True
            data = json.loads(cookie_file.read_text(encoding="utf-8"))
            cookies = data.get("cookies", [])
            # Kiểm tra file có được tạo gần đây không (file mtime)
            mtime = cookie_file.stat().st_mtime
            age_hours = (time.time() - mtime) / 3600
            # Nếu file > 20 tiếng tuổi → stale
            if age_hours > 20:
                log(f"Cookie file for {profile_name} is {age_hours:.1f}h old → stale")
                return True
            # Kiểm tra expiry của SID cookie
            now = time.time()
            for c in cookies:
                if isinstance(c, dict) and c.get("name") == "SID":
                    exp = float(c.get("expires", -1) or -1)
                    if 0 < exp <= now + TOKEN_EXPIRY_BUFFER_SEC:
                        log(f"SID cookie for {profile_name} expires soon: {exp - now:.0f}s left")
                        return True
            return False
        except Exception:
            return True

    def _load_cookie_header(self, profile_name: str) -> str:
        """Load cookie header từ file (gọi hàm gốc của grok_video_tool nếu có)."""
        try:
            # Try grok_video_tool first
            import sys as _sys
            _sys.path.insert(0, str(_THIS_DIR))
            import grok_video_tool as _gvt
            hdr = _gvt._load_flow_cookie_header(profile_name)
            if hdr:
                return hdr
        except Exception:
            pass

        # Fallback: đọc trực tiếp
        try:
            cookie_file = COOKIES_DIR / f"{profile_name}.json"
            if not cookie_file.exists():
                return ""
            data = json.loads(cookie_file.read_text(encoding="utf-8"))
            cookies = data.get("cookies", [])
            now = time.time()
            essential = {"SID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID", "HSID", "SSID",
                         "APISID", "SIDCC", "__Secure-1PAPISID", "__Secure-3PAPISID",
                         "OSID", "__Secure-OSID", "__Secure-1PSIDTS", "__Secure-3PSIDTS"}
            parts = []
            for c in cookies:
                if not isinstance(c, dict):
                    continue
                name = c.get("name", "")
                val = c.get("value", "")
                if not name or not val:
                    continue
                exp = float(c.get("expires", -1) or -1)
                if 0 < exp <= now:
                    continue
                if name in essential or name.startswith("__Secure-") or name.startswith("__Host-"):
                    parts.append(f"{name}={val}")
            return "; ".join(parts)
        except Exception:
            return ""

    def _do_refresh(self, profile_name: str, reason: str = "") -> bool:
        """
        Thực hiện refresh session cho profile.
        Thread-safe, có cooldown, có timeout.
        Returns: True nếu thành công.
        """
        state = self._get_or_create_state(profile_name)

        with state.lock:
            if state.refreshing:
                log(f"Profile {profile_name} đang refresh, bỏ qua trùng lặp")
                return False
            state.refreshing = True

        log(f"🔄 Bắt đầu refresh session: {profile_name} (lý do: {reason})")
        result = [False]

        def _run():
            try:
                # Import extractor
                sys.path.insert(0, str(_THIS_DIR))
                import extract_chrome_session as _ext

                found = _ext.find_profile_by_name(profile_name)
                if not found:
                    # Thử tìm bằng tên chính xác
                    sys_profs = _ext.get_system_profiles()
                    nat_profs = _ext.get_native_profiles()
                    if profile_name in sys_profs:
                        found = (profile_name, sys_profs[profile_name]["path"], False)
                    elif profile_name in nat_profs:
                        found = (profile_name, nat_profs[profile_name]["path"], True)

                if not found:
                    state.last_error = f"Không tìm thấy profile: {profile_name}"
                    err(state.last_error)
                    return

                pname, ppath, is_native = found
                log(f"  Extracting session từ: {ppath[:60]}...")

                data = _ext.extract_via_playwright(ppath, pname, is_native)

                if data and data.get("cookies"):
                    out_name = profile_name  # Save with original name
                    _ext.save_session(data, out_name)

                    state.email = data.get("email", "")
                    state.valid = True
                    state.last_error = ""
                    state.refresh_count += 1
                    result[0] = True

                    n_cookies = len(data.get("cookies", []))
                    has_at = bool(data.get("wiz_tokens", {}).get("at"))
                    log(f"  ✅ Refresh thành công: {n_cookies} cookies, WIZ.at={'✅' if has_at else '❌'}")

                    # Fire callbacks
                    for cb in self._on_refresh_callbacks:
                        try:
                            cb(profile_name, data)
                        except Exception:
                            pass
                else:
                    state.last_error = "Extraction thất bại (profile chưa đăng nhập hoặc Chrome bị chặn)"
                    state.valid = False
                    err(f"  ❌ {state.last_error}")

            except Exception as ex:
                import traceback
                state.last_error = str(ex)
                err(f"  ❌ Refresh error: {ex}")
                traceback.print_exc()
            finally:
                state.last_refresh = time.time()
                state.refreshing = False

        t = threading.Thread(target=_run, daemon=True, name=f"Refresh-{profile_name}")
        t.start()
        t.join(timeout=EXTRACT_TIMEOUT_SEC)

        if t.is_alive():
            warn(f"Refresh timeout sau {EXTRACT_TIMEOUT_SEC}s cho profile {profile_name}")
            state.refreshing = False
            state.last_error = f"Timeout sau {EXTRACT_TIMEOUT_SEC}s"
            return False

        return result[0]

    def _bg_loop(self):
        """Background thread: kiểm tra và tự động refresh định kỳ."""
        log(f"Background loop started — interval={CHECK_INTERVAL_SEC}s")
        # Lần đầu: kiểm tra ngay sau 10 giây
        if self._stop_event.wait(10):
            return

        while not self._stop_event.is_set():
            log(f"🔍 Kiểm tra token định kỳ ({len(self._auto_profiles)} profiles)...")

            for profile_name in list(self._auto_profiles):
                if self._stop_event.is_set():
                    break

                state = self._get_or_create_state(profile_name)
                # Skip nếu profile đã biết không có Flow access
                if state.no_flow_access and time.time() < state.skip_until:
                    log(f"  {profile_name}: ⏸ Bỏ qua (không có Flow access, thử lại sau {(state.skip_until - time.time())/60:.0f}p)")
                    continue

                cookie_hdr = self._load_cookie_header(profile_name)

                if not cookie_hdr:
                    log(f"  {profile_name}: Không có cookie file → cần refresh")
                    if self._can_refresh(state):
                        ok = self._do_refresh(profile_name, reason="no_cookie")
                        # Sau refresh, kiểm tra lại
                        if ok:
                            new_hdr = self._load_cookie_header(profile_name)
                            if not new_hdr:
                                # Cookie save nhưng vẫn empty → profile có thể không có SID cookie
                                # → không refresh lại quá sớm, đánh dấu skip 1 tiếng
                                warn(f"  {profile_name}: Đã refresh nhưng cookie header vẫn rỗng (profile chưa đăng nhập Flow?) → skip 1h")
                                state.no_flow_access = True
                                state.skip_until = time.time() + 3600
                elif self._is_session_stale(profile_name):
                    log(f"  {profile_name}: Session stale → refresh")
                    if self._can_refresh(state):
                        self._do_refresh(profile_name, reason="stale")
                else:
                    state.valid = True
                    state.no_flow_access = False  # Reset nếu có cookie OK
                    log(f"  {profile_name}: ✅ OK")

            # Wait đến lần check tiếp
            self._stop_event.wait(CHECK_INTERVAL_SEC)

        log("Background loop stopped")

    _AUTH_COOKIE_NAMES = {"SID", "HSID", "SSID", "SAPISID", "OSID", "__Secure-OSID",
                          "__Secure-1PSID", "__Secure-3PSID"}

    def _has_auth_cookies(self, profile_name: str) -> bool:
        """Kiểm tra profile có auth cookies hợp lệ không."""
        try:
            cookie_file = COOKIES_DIR / f"{profile_name}.json"
            if not cookie_file.exists():
                return False
            data = json.loads(cookie_file.read_text(encoding="utf-8"))
            cookies = data.get("cookies", [])
            names = {c.get("name", "") for c in cookies if isinstance(c, dict)}
            return bool(self._AUTH_COOKIE_NAMES & names)
        except Exception:
            return False

    def _discover_profiles(self) -> list[str]:
        """Tự động tìm profiles có auth cookie hợp lệ (SID, HSID, OSID...)."""
        candidates = []
        if COOKIES_DIR.exists():
            for f in COOKIES_DIR.glob("*.json"):
                candidates.append(f.stem)
        # Thêm profiles từ accounts config
        try:
            acc_file = DATA_DIR / "Flow_nhieu_worker_accounts.json"
            if acc_file.exists():
                data = json.loads(acc_file.read_text(encoding="utf-8"))
                for acc in data if isinstance(data, list) else []:
                    pname = acc.get("profile_name") or acc.get("profile") or ""
                    if pname and pname not in candidates:
                        candidates.append(pname)
        except Exception:
            pass
        # Lọc chỉ giữ profiles có auth cookies thực sự
        valid = [p for p in candidates if self._has_auth_cookies(p)]
        # Luôn include leviettung04 và Default nếu có cookie file (dù chưa có auth cookies)
        for must_have in ["leviettung04", "Default"]:
            if must_have not in valid:
                cookie_f = COOKIES_DIR / f"{must_have}.json"
                if cookie_f.exists() or must_have == "leviettung04":
                    valid.append(must_have)
        return list(dict.fromkeys(valid)) or ["leviettung04"]


# ── Singleton ──────────────────────────────────────────────────────────────
TOKEN_MANAGER = TokenManager()


# ── Convenience functions ──────────────────────────────────────────────────

def enable(profiles: Optional[list[str]] = None, auto: bool = True):
    """Bật tự động refresh token."""
    TOKEN_MANAGER.enable(profiles=profiles, auto=auto)


def on_401(profile_name: str) -> str:
    """Gọi khi nhận 401 — tự refresh và trả về cookie mới."""
    return TOKEN_MANAGER.on_401(profile_name)


def ensure_valid(profile_name: str) -> str:
    """Lấy cookie header hợp lệ, tự refresh nếu cần."""
    return TOKEN_MANAGER.ensure_valid(profile_name)


def force_refresh(profile_name: str) -> bool:
    """Buộc refresh ngay lập tức."""
    return TOKEN_MANAGER.force_refresh(profile_name)


def get_status() -> dict:
    """Lấy trạng thái token manager."""
    return TOKEN_MANAGER.get_status()


# ── Patch grok_video_tool._load_flow_cookie_header ──────────────────────────
_GVT_PATCHED = False  # Guard: chỉ patch 1 lần duy nhất

def patch_gvt():
    """
    Monkey-patch grok_video_tool._load_flow_cookie_header để tự động
    kiểm tra và refresh token khi cần.
    Chỉ patch 1 lần — gọi nhiều lần cũng an toàn.
    """
    global _GVT_PATCHED
    if _GVT_PATCHED:
        log("patch_gvt: đã được patch rồi, bỏ qua")
        return True
    try:
        import grok_video_tool as _gvt
        _original_load = _gvt._load_flow_cookie_header

        # Cooldown map: profile_name → last_log_time
        _last_empty_log: dict[str, float] = {}

        def _patched_load(profile_name: str, auth_root=None) -> str:
            # Thử load bình thường
            hdr = _original_load(profile_name, auth_root=auth_root)
            if hdr:
                return hdr
            # Cookie rỗng — kiểm tra xem có thể refresh không
            if not TOKEN_MANAGER._enabled:
                return hdr
            state = TOKEN_MANAGER._get_or_create_state(profile_name)
            # Nếu profile đã biết không có Flow access → không log nữa
            if state.no_flow_access:
                return hdr
            # Chỉ log tối đa 1 lần / 10 phút cho mỗi profile (tránh spam)
            now = time.time()
            last_t = _last_empty_log.get(profile_name, 0)
            if now - last_t > 600:
                _last_empty_log[profile_name] = now
                log(f"_load_flow_cookie_header: empty for {profile_name} (bg_loop sẽ tự refresh)")
            return hdr

        _gvt._load_flow_cookie_header = _patched_load
        _GVT_PATCHED = True
        log("✅ Patched grok_video_tool._load_flow_cookie_header (guard active)")
        return True
    except ImportError:
        warn("grok_video_tool not found, skipping patch")
        return False


if __name__ == "__main__":
    # Test / standalone run
    import argparse

    parser = argparse.ArgumentParser(description="Token Manager — Tự động làm mới Google Flow session")
    parser.add_argument("--enable", "-e", nargs="*", metavar="PROFILE",
                        help="Bật tự động refresh (không arg = auto-detect)")
    parser.add_argument("--force", "-f", metavar="PROFILE",
                        help="Force refresh ngay cho profile này")
    parser.add_argument("--status", "-s", action="store_true",
                        help="Xem trạng thái")
    parser.add_argument("--run", "-r", nargs="*", metavar="PROFILE",
                        help="Chạy liên tục, giữ token hợp lệ")
    args = parser.parse_args()

    if args.force:
        print(f"Force refresh: {args.force}")
        ok = TOKEN_MANAGER.force_refresh(args.force)
        print(f"Result: {'✅ OK' if ok else '❌ FAILED'}")

    elif args.status:
        status = TOKEN_MANAGER.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif args.run is not None:
        profiles = args.run if args.run else None
        print(f"Chạy liên tục, theo dõi profiles: {profiles or 'auto-detect'}")
        TOKEN_MANAGER.enable(profiles=profiles, auto=True)
        try:
            while True:
                time.sleep(60)
                s = TOKEN_MANAGER.get_status()
                for pname, pdata in s["profiles"].items():
                    emoji = "✅" if pdata["valid"] else "❌"
                    print(f"  {emoji} {pname}: refresh_count={pdata['refresh_count']}, last={pdata['last_refresh']}")
        except KeyboardInterrupt:
            TOKEN_MANAGER.stop()
            print("\nDừng.")

    elif args.enable is not None:
        profiles = args.enable if args.enable else None
        TOKEN_MANAGER.enable(profiles=profiles, auto=True)
        print(f"Token Manager đã bật cho: {TOKEN_MANAGER._auto_profiles}")
        # Keep running
        try:
            while True:
                time.sleep(300)
        except KeyboardInterrupt:
            TOKEN_MANAGER.stop()
    else:
        parser.print_help()
