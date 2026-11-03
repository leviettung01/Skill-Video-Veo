# -*- coding: utf-8 -*-
"""
ProxyManager — Quản lý proxy xoay & tĩnh cho AutoGrok.
Hỗ trợ proxyxoay.shop API, round-robin nhiều key, auto-rotate.
"""

import json
import time
import uuid
import threading
import requests
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Callable

APP_DIR = Path(__file__).resolve().parent
PROXY_CONFIG_FILE = APP_DIR / "proxy_config.json"


@dataclass
class ProxyConfig:
    """Cấu hình 1 proxy (xoay hoặc tĩnh)."""
    id: str = ""
    name: str = ""
    type: str = "rotating"          # "rotating" | "static"
    enabled: bool = True

    # ── Rotating proxy (proxyxoay.shop) ──
    api_key: str = ""               # Key xoay
    nhamang: str = "Random"         # "Random", "fpt", "viettel", "mobifone"
    tinhthanh: str = "0"            # "0" = random
    rotate_interval: int = 60       # Giây

    # ── Static proxy ──
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    protocol: str = "http"          # "http" | "socks5"

    # ── Runtime (không lưu) ──
    current_proxy_http: str = ""    # "ip:port:user:pass" hoặc "ip:port::"
    current_proxy_socks5: str = ""
    current_exit_ip: str = ""
    current_location: str = ""
    current_isp: str = ""
    proxy_die_after: int = 0        # Proxy die sau N giây
    expires_at: str = ""            # Ngày hết hạn key
    last_rotate_time: float = 0.0
    last_error: str = ""
    rotation_lock_count: int = 0    # Đếm số luồng đang giải reCAPTCHA/Submit để khóa xoay IP
    current_timezone: str = "Asia/Ho_Chi_Minh"
    current_latitude: float = 21.02
    current_longitude: float = 105.80
    current_country_code: str = "VN"

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]

    def to_dict(self) -> dict:
        """Chỉ lưu các field cần thiết (bỏ runtime)."""
        skip_runtime = {
            "current_proxy_http", "current_proxy_socks5", "current_exit_ip",
            "current_location", "current_isp", "proxy_die_after",
            "last_rotate_time", "last_error", "rotation_lock_count",
            "current_timezone", "current_latitude", "current_longitude",
            "current_country_code"
        }
        d = asdict(self)
        for k in skip_runtime:
            d.pop(k, None)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ProxyConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)

    def get_httpx_proxy_url(self) -> Optional[str]:
        """Trả về proxy URL format cho httpx: http://user:pass@host:port"""
        if self.type == "static":
            if not self.host or not self.port:
                return None
            if self.username and self.password:
                return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
            return f"{self.protocol}://{self.host}:{self.port}"

        elif self.type == "rotating":
            if not self.current_proxy_http:
                return None
            # Format from API: "ip:port:user:pass" hoặc "ip:port::"
            parts = self.current_proxy_http.split(":")
            if len(parts) >= 2:
                ip, port = parts[0], parts[1]
                user = parts[2] if len(parts) > 2 and parts[2] else ""
                pwd = parts[3] if len(parts) > 3 and parts[3] else ""
                if user and pwd:
                    return f"http://{user}:{pwd}@{ip}:{port}"
                return f"http://{ip}:{port}"
        return None


class ProxyManager:
    """Quản lý proxy xoay & tĩnh. Thread-safe, hỗ trợ round-robin nhiều key."""

    ROTATE_API = "https://proxyxoay.shop/api/get.php"
    GET_KEYS_API = "https://hanelproxy.vn/proxyxoay/apigetkeyxoay.php"

    def __init__(self, log_func: Optional[Callable] = None):
        self.proxies: List[ProxyConfig] = []
        self._round_robin_idx: int = 0      # Index hiện tại cho round-robin
        self._lock = threading.Lock()
        self._rotate_thread: Optional[threading.Thread] = None
        self._auto_rotate_running = False
        self._log_func = log_func
        self.load()

    def log(self, msg: str):
        if self._log_func:
            try:
                self._log_func(f"[Proxy] {msg}")
            except Exception:
                pass

    # ══════════════════════════════════════════════════════
    # CRUD
    # ══════════════════════════════════════════════════════

    def add_rotating(self, name: str, api_key: str, nhamang: str = "Random",
                     tinhthanh: str = "0", interval: int = 60) -> ProxyConfig:
        """Thêm proxy xoay mới."""
        pc = ProxyConfig(
            name=name or f"Key {len(self.proxies)+1}",
            type="rotating",
            api_key=api_key,
            nhamang=nhamang,
            tinhthanh=tinhthanh,
            rotate_interval=interval,
            enabled=True
        )
        self.proxies.append(pc)
        self.save()
        self.log(f"✅ Đã thêm proxy xoay: {pc.name} (key: {api_key[:8]}...)")
        return pc

    def add_static(self, name: str, host: str, port: int,
                   username: str = "", password: str = "",
                   protocol: str = "http") -> ProxyConfig:
        """Thêm proxy tĩnh."""
        pc = ProxyConfig(
            name=name or f"Static {len(self.proxies)+1}",
            type="static",
            host=host,
            port=port,
            username=username,
            password=password,
            protocol=protocol,
            enabled=True
        )
        # Proxy tĩnh: current_proxy_http = host:port
        pc.current_proxy_http = f"{host}:{port}:{username}:{password}"
        self.proxies.append(pc)
        self.save()
        self.log(f"✅ Đã thêm proxy tĩnh: {pc.name} ({host}:{port})")
        return pc

    def remove(self, proxy_id: str):
        """Xóa proxy theo ID."""
        self.proxies = [p for p in self.proxies if p.id != proxy_id]
        self.save()
        self.log(f"🗑 Đã xóa proxy {proxy_id}")

    def get_enabled_proxies(self) -> List[ProxyConfig]:
        """Trả về danh sách proxy đang bật."""
        return [p for p in self.proxies if p.enabled]

    # ══════════════════════════════════════════════════════
    # ROTATION
    # ══════════════════════════════════════════════════════

    def rotate_proxy(self, proxy: ProxyConfig, force: bool = False) -> bool:
        """Xoay 1 proxy xoay — gọi API proxyxoay.shop."""
        if proxy.type != "rotating" or not proxy.api_key:
            return False

        if not force and getattr(proxy, "rotation_lock_count", 0) > 0:
            self.log(f"⏳ Hoãn xoay proxy [{proxy.name}] vì đang trong tiến trình giải reCAPTCHA/Submit (lock count: {proxy.rotation_lock_count})...")
            # Cập nhật last_rotate_time để tránh thử xoay liên tục
            proxy.last_rotate_time = time.time() - (proxy.rotate_interval - 15)
            return False

        try:
            params = {
                "key": proxy.api_key,
                "nhamang": proxy.nhamang or "Random",
                "tinhthanh": proxy.tinhthanh or "0"
            }
            r = requests.get(self.ROTATE_API, params=params, timeout=15)
            data = r.json()

            if data.get("status") == 100:
                proxy.current_proxy_http = data.get("proxyhttp", "")
                proxy.current_proxy_socks5 = data.get("proxysocks5", "")
                proxy.current_isp = data.get("Nha Mang", "")
                proxy.current_location = data.get("Vi Tri", "")
                proxy.expires_at = data.get("Token expiration date", "")
                proxy.last_rotate_time = time.time()
                proxy.last_error = ""

                # Parse exit IP from proxy response
                msg = data.get("message", "")
                if "die sau" in msg:
                    try:
                        proxy.proxy_die_after = int(msg.split("die sau")[1].split("s")[0].strip())
                    except Exception:
                        proxy.proxy_die_after = 0

                # Exit IP = proxy IP (phần đầu)
                http_parts = proxy.current_proxy_http.split(":")
                if http_parts:
                    proxy.current_exit_ip = http_parts[0]

                self.log(
                    f"🔄 Xoay thành công [{proxy.name}]: "
                    f"IP={proxy.current_exit_ip} | "
                    f"ISP={proxy.current_isp} | "
                    f"Vị trí={proxy.current_location} | "
                    f"Die sau {proxy.proxy_die_after}s"
                )
                
                # Tự động kiểm tra hoạt động của proxy sau khi xoay
                test_res = self.test_proxy(proxy)
                if test_res["ok"]:
                    self.log(f"✅ Proxy [{proxy.name}] đang HOẠT ĐỘNG TỐT! IP thực tế: {test_res['ip']}")
                else:
                    self.log(f"⚠️ Cảnh báo: Proxy [{proxy.name}] kết nối lỗi hoặc chậm: {test_res['error']}")
                return True
            else:
                err = data.get("comen", data.get("message", f"status={data.get('status')}"))
                proxy.last_error = err
                self.log(f"❌ Xoay thất bại [{proxy.name}]: {err}")
                return False

        except Exception as e:
            proxy.last_error = str(e)
            self.log(f"❌ Lỗi kết nối API xoay [{proxy.name}]: {e}")
            return False

    def rotate_all(self, force: bool = True):
        """Xoay tất cả proxy xoay đang bật."""
        for p in self.get_enabled_proxies():
            if p.type == "rotating":
                self.rotate_proxy(p, force=force)

    # ══════════════════════════════════════════════════════
    # AUTO ROTATE (background thread)
    # ══════════════════════════════════════════════════════

    def start_auto_rotate(self):
        """Bắt đầu auto-rotate trong background thread."""
        if self._auto_rotate_running:
            return
        self._auto_rotate_running = True
        self._rotate_thread = threading.Thread(target=self._auto_rotate_loop, daemon=True)
        self._rotate_thread.start()
        self.log("▶ Đã bật auto-rotate proxy.")

    def stop_auto_rotate(self):
        """Dừng auto-rotate."""
        self._auto_rotate_running = False
        self.log("⏹ Đã tắt auto-rotate proxy.")

    @property
    def is_auto_rotating(self) -> bool:
        return self._auto_rotate_running

    def _auto_rotate_loop(self):
        """Loop chạy trong thread — xoay proxy khi hết interval."""
        while self._auto_rotate_running:
            now = time.time()
            for p in self.get_enabled_proxies():
                if p.type != "rotating":
                    continue
                elapsed = now - p.last_rotate_time
                if elapsed >= p.rotate_interval or p.last_rotate_time == 0:
                    self.rotate_proxy(p)
            # Sleep ngắn để check thường xuyên
            time.sleep(5)

    # ══════════════════════════════════════════════════════
    # ROUND-ROBIN PROVIDER
    # ══════════════════════════════════════════════════════

    def get_current_proxy(self) -> Optional[ProxyConfig]:
        """Trả về proxy active hiện tại (round-robin)."""
        with self._lock:
            enabled = self.get_enabled_proxies()
            if not enabled:
                return None
            # Filter out proxies that don't have a valid proxy URL yet
            ready = [p for p in enabled if p.get_httpx_proxy_url()]
            if not ready:
                return None
            self._round_robin_idx = self._round_robin_idx % len(ready)
            proxy = ready[self._round_robin_idx]
            self._round_robin_idx = (self._round_robin_idx + 1) % len(ready)
            return proxy

    def get_httpx_proxy_url(self) -> Optional[str]:
        """Trả về proxy URL cho httpx.Client(proxy=...). Round-robin nếu nhiều key."""
        proxy = self.get_current_proxy()
        return proxy.get_httpx_proxy_url() if proxy else None

    def get_chrome_proxy_arg(self) -> Optional[str]:
        """Trả về --proxy-server=ip:port cho Chrome. Dùng proxy đầu tiên có sẵn."""
        with self._lock:
            enabled = self.get_enabled_proxies()
            for p in enabled:
                if p.type == "rotating" and p.current_proxy_http:
                    parts = p.current_proxy_http.split(":")
                    if len(parts) >= 2:
                        return f"{parts[0]}:{parts[1]}"
                elif p.type == "static" and p.host and p.port:
                    return f"{p.host}:{p.port}"
        return None

    def should_proxy_url(self, url: str) -> bool:
        """Kiểm tra URL có nên dùng proxy hay không.
        Không proxy: 127.0.0.1, localhost, các dải IP nội bộ/mạng cục bộ, cổng CLIProxy 8317, v.v.
        """
        if not url:
            return True
        lower = url.lower()
        skip_hosts = [
            "127.0.0.1", "localhost", "::1", ":8317",
            "proxyxoay.shop", "hanelproxy.vn",
            "192.168.", "10.", 
            "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.",
            "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
            "172.28.", "172.29.", "172.30.", "172.31."
        ]
        for host in skip_hosts:
            if host in lower:
                return False
        return True

    # ══════════════════════════════════════════════════════
    # TEST PROXY
    # ══════════════════════════════════════════════════════

    def test_proxy(self, proxy: Optional[ProxyConfig] = None) -> dict:
        """Test proxy bằng cách check IP qua ip-api.com và lấy thông tin địa lý.
        Returns: {"ok": bool, "ip": str, "error": str}
        """
        pc = proxy or self.get_current_proxy()
        if not pc:
            return {"ok": False, "ip": "", "error": "Không có proxy nào active"}

        proxy_url = pc.get_httpx_proxy_url()
        if not proxy_url:
            return {"ok": False, "ip": "", "error": "Proxy chưa có URL (chưa xoay?)"}

        try:
            # 1. Thử lấy thông tin địa lý và múi giờ chi tiết từ ip-api
            r = requests.get(
                "http://ip-api.com/json",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=12
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    pc.current_exit_ip = data.get("query", "")
                    pc.current_timezone = data.get("timezone", "Asia/Ho_Chi_Minh")
                    pc.current_latitude = float(data.get("lat", 21.02))
                    pc.current_longitude = float(data.get("lon", 105.80))
                    pc.current_country_code = data.get("countryCode", "VN")
                    return {"ok": True, "ip": pc.current_exit_ip, "error": ""}

            # 2. Fallback sang api.ipify.org nếu ip-api bị rate limit hoặc lỗi
            r = requests.get(
                "https://api.ipify.org?format=json",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=12
            )
            if r.status_code == 200:
                ip = r.json().get("ip", "")
                pc.current_exit_ip = ip
                # Đảm bảo không để trống các thuộc tính múi giờ
                if not getattr(pc, "current_timezone", None):
                    pc.current_timezone = "Asia/Ho_Chi_Minh"
                    pc.current_latitude = 21.02
                    pc.current_longitude = 105.80
                    pc.current_country_code = "VN"
                return {"ok": True, "ip": ip, "error": ""}
            return {"ok": False, "ip": "", "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "ip": "", "error": str(e)}

    # ══════════════════════════════════════════════════════
    # CHECK KEY INFO
    # ══════════════════════════════════════════════════════

    def check_keys_info(self, master_key: str) -> list:
        """Lấy danh sách key xoay còn hạn từ API.
        GET https://hanelproxy.vn/proxyxoay/apigetkeyxoay.php?key=...
        """
        try:
            r = requests.get(self.GET_KEYS_API, params={"key": master_key}, timeout=15)
            # API trả về nhiều JSON objects
            text = r.text.strip()
            results = []
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        d = json.loads(line)
                        if d.get("status") == 100 and "keyxoay" in d:
                            results.append(d)
                    except json.JSONDecodeError:
                        pass
            # Try parsing as array too
            if not results:
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        results = [d for d in data if d.get("status") == 100]
                    elif isinstance(data, dict) and data.get("status") == 100:
                        results = [data]
                except Exception:
                    pass
            return results
        except Exception as e:
            self.log(f"❌ Lỗi kiểm tra key: {e}")
            return []

    # ══════════════════════════════════════════════════════
    # PERSISTENCE
    # ══════════════════════════════════════════════════════

    def save(self):
        """Lưu cấu hình proxy vào file JSON."""
        try:
            data = {
                "proxies": [p.to_dict() for p in self.proxies],
                "round_robin_idx": self._round_robin_idx
            }
            with open(PROXY_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ Lỗi lưu proxy config: {e}")

    def load(self):
        """Đọc cấu hình proxy từ file JSON."""
        if not PROXY_CONFIG_FILE.exists():
            return
        try:
            with open(PROXY_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.proxies = [ProxyConfig.from_dict(d) for d in data.get("proxies", [])]
            self._round_robin_idx = data.get("round_robin_idx", 0)
            self.log(f"📂 Đã tải {len(self.proxies)} proxy từ config.")
        except Exception as e:
            self.log(f"❌ Lỗi đọc proxy config: {e}")


# ══════════════════════════════════════════════════════════
# HTTPX HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════

# Global proxy manager instance — set bởi GrokVideoApp.__init__()
_global_proxy_manager: Optional[ProxyManager] = None


def set_global_proxy_manager(mgr: ProxyManager):
    """Set global ProxyManager instance."""
    global _global_proxy_manager
    _global_proxy_manager = mgr


def get_proxy_for_url(url: str = "") -> Optional[str]:
    """Lấy proxy URL cho 1 URL cụ thể. Trả về None nếu không cần proxy."""
    if not _global_proxy_manager:
        return None
    if not _global_proxy_manager.get_enabled_proxies():
        return None
    if url and not _global_proxy_manager.should_proxy_url(url):
        return None
    return _global_proxy_manager.get_httpx_proxy_url()


def make_httpx_client(timeout=120, target_url: str = "", use_proxy: bool = True, **kwargs):
    """Tạo httpx.Client có proxy (nếu ProxyManager active).
    
    Args:
        timeout: Timeout cho httpx client
        target_url: URL đích để kiểm tra có nên proxy hay không
        use_proxy: Cho phép sử dụng proxy hay không
        **kwargs: Các tham số khác cho httpx.Client
    """
    import httpx
    friendly_target = target_url
    if target_url and "://" in target_url:
        try:
            from urllib.parse import urlparse
            friendly_target = urlparse(target_url).netloc
        except Exception:
            pass

    # Tạo mounts để tự động bypass proxy cho localhost, 127.0.0.1 và ::1
    mounts = {
        "http://127.0.0.1": httpx.HTTPTransport(),
        "https://127.0.0.1": httpx.HTTPTransport(),
        "http://localhost": httpx.HTTPTransport(),
        "https://localhost": httpx.HTTPTransport(),
        "http://[::1]": httpx.HTTPTransport(),
        "https://[::1]": httpx.HTTPTransport(),
    }

    if use_proxy:
        proxy_url = get_proxy_for_url(target_url)
        if target_url and _global_proxy_manager and not _global_proxy_manager.should_proxy_url(target_url):
            proxy_url = None

        if proxy_url:
            if _global_proxy_manager:
                logged_url = proxy_url
                if "@" in proxy_url:
                    parts = proxy_url.split("@")
                    logged_url = "http://***:***@" + parts[-1]
                _global_proxy_manager.log(f"🔗 Request tới {friendly_target or 'API'} được GẮN PROXY: {logged_url}")
            return httpx.Client(timeout=timeout, proxy=proxy_url, mounts=mounts, **kwargs)
        else:
            if _global_proxy_manager:
                _global_proxy_manager.log(f"ℹ️ Request tới {friendly_target or 'API'} KHÔNG dùng proxy (không có proxy active/không hỗ trợ URL)")
    else:
        if _global_proxy_manager:
            _global_proxy_manager.log(f"ℹ️ Request tới {friendly_target or 'API'} KHÔNG dùng proxy (tắt proxy trong request)")
    return httpx.Client(timeout=timeout, mounts=mounts, **kwargs)


def make_httpx_async_client(timeout=120, target_url: str = "", use_proxy: bool = True, **kwargs):
    """Tạo httpx.AsyncClient có proxy (nếu ProxyManager active).
    
    Args:
        timeout: Timeout cho httpx client
        target_url: URL đích để kiểm tra có nên proxy hay không
        use_proxy: Cho phép sử dụng proxy hay không
        **kwargs: Các tham số khác cho httpx.AsyncClient
    """
    import httpx
    friendly_target = target_url
    if target_url and "://" in target_url:
        try:
            from urllib.parse import urlparse
            friendly_target = urlparse(target_url).netloc
        except Exception:
            pass

    # Tạo mounts để tự động bypass proxy cho localhost, 127.0.0.1 và ::1
    mounts = {
        "http://127.0.0.1": httpx.AsyncHTTPTransport(),
        "https://127.0.0.1": httpx.AsyncHTTPTransport(),
        "http://localhost": httpx.AsyncHTTPTransport(),
        "https://localhost": httpx.AsyncHTTPTransport(),
        "http://[::1]": httpx.AsyncHTTPTransport(),
        "https://[::1]": httpx.AsyncHTTPTransport(),
    }

    if use_proxy:
        proxy_url = get_proxy_for_url(target_url)
        if target_url and _global_proxy_manager and not _global_proxy_manager.should_proxy_url(target_url):
            proxy_url = None

        if proxy_url:
            if _global_proxy_manager:
                logged_url = proxy_url
                if "@" in proxy_url:
                    parts = proxy_url.split("@")
                    logged_url = "http://***:***@" + parts[-1]
                _global_proxy_manager.log(f"🔗 Request tới {friendly_target or 'API'} được GẮN PROXY: {logged_url}")
            return httpx.AsyncClient(timeout=timeout, proxy=proxy_url, mounts=mounts, **kwargs)
        else:
            if _global_proxy_manager:
                _global_proxy_manager.log(f"ℹ️ Request tới {friendly_target or 'API'} KHÔNG dùng proxy (không có proxy active/không hỗ trợ URL)")
    else:
        if _global_proxy_manager:
            _global_proxy_manager.log(f"ℹ️ Request tới {friendly_target or 'API'} KHÔNG dùng proxy (tắt proxy trong request)")
    return httpx.AsyncClient(timeout=timeout, mounts=mounts, **kwargs)
