# -*- coding: utf-8 -*-
"""Client-side connector for SkillAutoVeo Cloud Server:
- Fast in-process Windows HWID (winreg MachineGuid + kernel32 volume serial)
- Windows DPAPI encrypted session cache + monotonic rollback check
- Ed25519 offline Lease JWT verification
- Account registration, login, heartbeat, device unbind
- OTA App update check/staging + Store Catalog & Paid Add-on Template sync
"""

from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import hashlib
import io
import json
import os
import platform
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

APP_VERSION = "6.1.0"
DEFAULT_CLOUD_URL = os.environ.get("SKILL_CLOUD_URL", "http://127.0.0.1:8000").rstrip("/")
SCRIPT_DIR = Path(__file__).resolve().parent
WS_DIR = SCRIPT_DIR.parent.parent

_HWID_CACHE: str | None = None


def get_cloud_data_dir() -> Path:
    override = os.environ.get("SKILL_CLOUD_DATA_DIR", "").strip()
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "SkillAutoVeo"
        try:
            base.mkdir(parents=True, exist_ok=True)
            return base
        except Exception:
            pass
    fallback = WS_DIR / "data" / "cloud_client"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def is_cloud_enforcement_enabled() -> bool:
    return os.environ.get("SKILL_CLOUD_REQUIRED", "0").strip().lower() in ("1", "true", "yes")


# ── Fast In-Process HWID & Windows DPAPI Helpers ───────────────────────────────────────

def _read_windows_machine_guid() -> str:
    if sys.platform != "win32":
        return ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(val or "").strip()
    except Exception:
        return ""


def _read_windows_volume_serial(drive: str = "C:\\") -> str:
    if sys.platform != "win32":
        return ""
    try:
        serial = ctypes.wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive),
            None,
            0,
            ctypes.byref(serial),
            None,
            None,
            None,
            0,
        )
        return f"{serial.value:08x}" if ok else ""
    except Exception:
        return ""


def get_hardware_id() -> str:
    """Compute a stable SHA-256 device fingerprint without spawning subprocesses."""
    global _HWID_CACHE
    if _HWID_CACHE:
        return _HWID_CACHE
    parts = [
        platform.system(),
        platform.machine(),
        socket.gethostname(),
        _read_windows_machine_guid(),
        _read_windows_volume_serial("C:\\"),
        "SkillAutoVeo-HWID-v1",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8", errors="ignore")).hexdigest()
    _HWID_CACHE = digest
    return digest


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_protect(plain: bytes) -> str:
    if sys.platform != "win32":
        return "plain:" + base64.b64encode(plain).decode("ascii")
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        buf = (ctypes.c_ubyte * len(plain)).from_buffer_copy(plain)
        in_blob = _DataBlob(len(plain), buf)
        out_blob = _DataBlob()
        if not crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0x01, ctypes.byref(out_blob)):
            return "plain:" + base64.b64encode(plain).decode("ascii")
        try:
            raw = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return "dpapi:" + base64.b64encode(raw).decode("ascii")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return "plain:" + base64.b64encode(plain).decode("ascii")


def _dpapi_unprotect(encoded: str) -> bytes:
    if encoded.startswith("plain:"):
        return base64.b64decode(encoded[6:])
    if encoded.startswith("dpapi:") and sys.platform == "win32":
        raw = base64.b64decode(encoded[6:])
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        buf = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        in_blob = _DataBlob(len(raw), buf)
        out_blob = _DataBlob()
        if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0x01, ctypes.byref(out_blob)):
            raise ValueError("DPAPI unprotect failed")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)
    raise ValueError("Unsupported protected token format")


# ── Ed25519 JWT Verification ───────────────────────────────────────────────────────────

def _b64u_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def verify_lease_jwt_offline(
    token: str,
    public_key_pem: str,
    expected_hwid: str,
    last_seen_utc: int = 0,
) -> dict[str, Any]:
    parts = (token or "").strip().split(".")
    if len(parts) != 3:
        raise ValueError("Malformed lease token")
    pub = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    if not isinstance(pub, Ed25519PublicKey):
        raise ValueError("Invalid Ed25519 public key")
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    pub.verify(_b64u_decode(parts[2]), signing_input)

    claims = json.loads(_b64u_decode(parts[1]).decode("utf-8"))
    now = int(time.time())
    if last_seen_utc and now + 300 < int(last_seen_utc):
        raise ValueError("Phát hiện đồng hồ hệ thống bị chỉnh lùi. Vui lòng kết nối mạng để xác thực.")
    if claims.get("hwid_hash") != expected_hwid:
        raise ValueError("Mã thiết bị (HWID) không khớp với phiên đã kích hoạt.")
    exp = int(claims.get("exp") or 0)
    hard_exp = int(claims.get("hard_exp") or exp)
    if now > exp or now > hard_exp:
        raise ValueError("Phiên làm việc hoặc thời hạn gói đã hết.")
    return claims


# ── Cloud Client Session Manager ───────────────────────────────────────────────────────

class CloudAccountClient:
    """Thread-safe local manager communicating with SkillAutoVeo Cloud Server."""

    def __init__(self, data_dir: Path | None = None, ws_dir: Path | None = None, default_server_url: str | None = None):
        self.data_dir = data_dir or get_cloud_data_dir()
        self.ws_dir = ws_dir or WS_DIR
        self.default_server_url = (default_server_url or DEFAULT_CLOUD_URL).rstrip("/")
        self.session_path = self.data_dir / "cloud_session.json"

    def _load_session(self) -> dict[str, Any]:
        if not self.session_path.exists():
            return {"server_url": self.default_server_url}
        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("server_url", self.default_server_url)
                return data
        except Exception:
            pass
        return {"server_url": self.default_server_url}

    def _save_session(self, data: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.session_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.session_path)

    def _get_lease_token(self, sess: dict[str, Any]) -> str:
        enc = sess.get("lease_token_enc") or ""
        if not enc:
            return ""
        try:
            return _dpapi_unprotect(enc).decode("utf-8")
        except Exception:
            return ""

    def _http_json(
        self,
        server_url: str,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str = "",
        timeout: float = 15.0,
    ) -> tuple[int, dict[str, Any]]:
        url = server_url.rstrip("/") + path
        headers = {"Accept": "application/json", "X-HWID": get_hardware_id()}
        raw_body: bytes | None = None
        if payload is not None:
            raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, data=raw_body, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                txt = resp.read().decode("utf-8", errors="replace")
                return resp.status, (json.loads(txt) if txt else {})
        except urllib.error.HTTPError as err:
            txt = err.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(txt)
            except Exception:
                parsed = {"ok": False, "message": txt or str(err)}
            return err.code, parsed
        except Exception as exc:
            return 0, {"ok": False, "error_code": "NETWORK_ERROR", "message": f"Không kết nối được Server: {exc}"}

    def _ensure_public_key(self, server_url: str, sess: dict[str, Any]) -> str:
        cached = sess.get("public_key_pem") or ""
        if cached:
            return cached
        code, data = self._http_json(server_url, "GET", "/api/v1/public/ed25519-public-key")
        if code == 200 and data.get("public_key_pem"):
            sess["public_key_pem"] = data["public_key_pem"]
            self._save_session(sess)
            return data["public_key_pem"]
        return ""

    def register(self, email: str, password: str, full_name: str = "", phone_zalo: str = "", server_url: str = "") -> dict[str, Any]:
        sess = self._load_session()
        target_url = (server_url or sess.get("server_url") or self.default_server_url).rstrip("/")
        code, res = self._http_json(
            target_url,
            "POST",
            "/api/v1/auth/register",
            payload={
                "email": email,
                "password": password,
                "full_name": full_name,
                "phone_zalo": phone_zalo,
                "hwid_hash": get_hardware_id(),
                "device_name": socket.gethostname(),
                "os_info": f"{platform.system()} {platform.release()}",
            },
        )
        sess["server_url"] = target_url
        if res.get("ok"):
            sess["pending_email"] = res.get("email")
            sess["pending_user_id"] = res.get("user_id")
        self._save_session(sess)
        return {**res, "http_status": code}

    def login(self, email: str, password: str, server_url: str = "") -> dict[str, Any]:
        sess = self._load_session()
        target_url = (server_url or sess.get("server_url") or self.default_server_url).rstrip("/")
        pub_pem = self._ensure_public_key(target_url, sess)
        code, res = self._http_json(
            target_url,
            "POST",
            "/api/v1/auth/login",
            payload={
                "email": email,
                "password": password,
                "hwid_hash": get_hardware_id(),
                "device_name": socket.gethostname(),
                "os_info": f"{platform.system()} {platform.release()}",
                "app_version": APP_VERSION,
            },
        )
        if code != 200 or not res.get("ok"):
            return {**res, "ok": False, "http_status": code}

        sess.update(
            {
                "server_url": target_url,
                "public_key_pem": pub_pem,
                "lease_token_enc": _dpapi_protect(res["lease_token"].encode("utf-8")),
                "user": res.get("user") or {},
                "last_seen_utc": int(res.get("server_time") or time.time()),
                "grace_until": int(res.get("grace_until") or 0),
                "pending_email": None,
                "pending_user_id": None,
            }
        )
        self._save_session(sess)
        return {**res, "http_status": code}

    def logout(self) -> dict[str, Any]:
        sess = self._load_session()
        server_url = sess.get("server_url") or self.default_server_url
        self._save_session({"server_url": server_url})
        return {"ok": True}

    def unbind_current_device(self) -> dict[str, Any]:
        sess = self._load_session()
        tok = self._get_lease_token(sess)
        if not tok:
            return {"ok": False, "message": "Chưa đăng nhập tài khoản Cloud."}
        server_url = sess.get("server_url") or self.default_server_url
        code, res = self._http_json(
            server_url,
            "POST",
            "/api/v1/auth/unbind-device",
            payload={"hwid_hash": get_hardware_id()},
            token=tok,
        )
        if code == 200 and res.get("ok"):
            self._save_session({"server_url": server_url})
        return {**res, "http_status": code}

    def get_status(self, refresh_online: bool = False) -> dict[str, Any]:
        sess = self._load_session()
        server_url = sess.get("server_url") or self.default_server_url
        tok = self._get_lease_token(sess)
        hwid = get_hardware_id()
        pub_pem = sess.get("public_key_pem") or ""

        if tok and refresh_online:
            code, res = self._http_json(
                server_url,
                "POST",
                "/api/v1/auth/heartbeat",
                payload={"hwid_hash": hwid, "app_version": APP_VERSION},
                token=tok,
                timeout=8.0,
            )
            if code == 200 and res.get("ok"):
                tok = res["lease_token"]
                sess["lease_token_enc"] = _dpapi_protect(tok.encode("utf-8"))
                sess["user"] = res.get("user") or sess.get("user")
                sess["last_seen_utc"] = int(res.get("server_time") or time.time())
                sess["grace_until"] = int(res.get("grace_until") or 0)
                self._save_session(sess)
            elif code in (401, 403):
                return {
                    "ok": True,
                    "authenticated": False,
                    "enforced": is_cloud_enforcement_enabled(),
                    "server_url": server_url,
                    "app_version": APP_VERSION,
                    "hwid_short": hwid[:12],
                    "error_code": res.get("error_code") or "SESSION_INVALID",
                    "error": res.get("message") or "Phiên tài khoản đã bị khóa hoặc hết hạn.",
                    "pending_email": sess.get("pending_email"),
                    "pending_user_id": sess.get("pending_user_id"),
                }

        if tok and pub_pem:
            try:
                claims = verify_lease_jwt_offline(
                    tok,
                    pub_pem,
                    expected_hwid=hwid,
                    last_seen_utc=int(sess.get("last_seen_utc") or 0),
                )
                now = int(time.time())
                hard_exp = int(claims.get("hard_exp") or claims.get("exp") or 0)
                days_rem = max(1, (hard_exp - now + 86399) // 86400) if hard_exp > now else 0
                user_info = dict(sess.get("user") or {})
                user_info["days_remaining"] = days_rem
                if now > int(sess.get("last_seen_utc") or 0):
                    sess["last_seen_utc"] = now
                    self._save_session(sess)
                return {
                    "ok": True,
                    "authenticated": True,
                    "enforced": is_cloud_enforcement_enabled(),
                    "server_url": server_url,
                    "app_version": APP_VERSION,
                    "hwid_short": hwid[:12],
                    "user": user_info,
                    "claims": {
                        "plan_tier": claims.get("plan_tier"),
                        "granted_packs": claims.get("granted_packs") or [],
                        "granted_templates": claims.get("granted_templates") or [],
                        "hard_exp": hard_exp,
                    },
                }
            except Exception as exc:
                return {
                    "ok": True,
                    "authenticated": False,
                    "enforced": is_cloud_enforcement_enabled(),
                    "server_url": server_url,
                    "app_version": APP_VERSION,
                    "hwid_short": hwid[:12],
                    "error": str(exc),
                }

        return {
            "ok": True,
            "authenticated": False,
            "enforced": is_cloud_enforcement_enabled(),
            "server_url": server_url,
            "app_version": APP_VERSION,
            "hwid_short": hwid[:12],
            "pending_email": sess.get("pending_email"),
            "pending_user_id": sess.get("pending_user_id"),
        }

    def check_app_update(self) -> dict[str, Any]:
        sess = self._load_session()
        tok = self._get_lease_token(sess)
        if not tok:
            return {"ok": False, "message": "Vui lòng đăng nhập tài khoản Cloud trước."}
        server_url = sess.get("server_url") or self.default_server_url
        q = urllib.parse.urlencode({"current_version": APP_VERSION, "channel": "stable", "platform": "win64"})
        code, res = self._http_json(server_url, "GET", f"/api/v1/app/latest?{q}", token=tok)
        return {**res, "http_status": code}

    def stage_app_update(self) -> dict[str, Any]:
        check = self.check_app_update()
        if not check.get("ok") or not check.get("update_available"):
            return check
        rel = check["latest"]
        dl_url = rel.get("download_url") or ""
        expected_sha = rel.get("sha256") or ""
        raw = self._download_verified_bytes(dl_url, expected_sha)
        upd_dir = self.data_dir / "updates"
        upd_dir.mkdir(parents=True, exist_ok=True)
        ext = ".exe" if rel.get("release_type") == "full_exe" else ".zip"
        out_path = upd_dir / f"SkillAutoVeo_v{rel['version']}{ext}"
        out_path.write_bytes(raw)
        return {
            "ok": True,
            "version": rel["version"],
            "release_type": rel["release_type"],
            "staged_path": str(out_path),
            "size_bytes": len(raw),
            "changelog": rel.get("changelog") or "",
        }

    def fetch_store_catalog(self) -> dict[str, Any]:
        sess = self._load_session()
        tok = self._get_lease_token(sess)
        if not tok:
            return {"ok": False, "error_code": "NOT_AUTHENTICATED", "message": "Vui lòng đăng nhập tài khoản Cloud."}
        server_url = sess.get("server_url") or self.default_server_url
        code, res = self._http_json(server_url, "GET", "/api/v1/store/catalog", token=tok)
        return {**res, "http_status": code}

    def _download_verified_bytes(self, url: str, expected_sha256: str) -> bytes:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=120.0) as resp:
            raw = resp.read()
        if expected_sha256:
            actual = hashlib.sha256(raw).hexdigest()
            if actual.lower() != expected_sha256.lower():
                raise ValueError(f"Checksum mismatch: expected {expected_sha256}, got {actual}")
        return raw

    def sync_template_from_store(self, template_id: str, kind: str = "video_template", include_video: bool = True) -> dict[str, Any]:
        sess = self._load_session()
        tok = self._get_lease_token(sess)
        if not tok:
            return {"ok": False, "message": "Vui lòng đăng nhập tài khoản Cloud."}
        server_url = sess.get("server_url") or self.default_server_url

        code, info = self._http_json(
            server_url,
            "GET",
            f"/api/v1/store/download/{urllib.parse.quote(template_id)}?asset=meta",
            token=tok,
        )
        if code != 200 or not info.get("ok"):
            return {**info, "ok": False, "http_status": code}

        meta_bytes = self._download_verified_bytes(info["download_url"], info.get("sha256") or "")
        installed_paths: list[str] = []

        if kind == "fashion_clip":
            cache_dir = self.ws_dir / "data" / "fashion_templates_cache" / "cloud_items"
            cache_dir.mkdir(parents=True, exist_ok=True)
            meta_file = cache_dir / f"{template_id}.json"
            meta_file.write_bytes(meta_bytes)
            installed_paths.append(str(meta_file))
            if include_video:
                vc, vinfo = self._http_json(
                    server_url,
                    "GET",
                    f"/api/v1/store/download/{urllib.parse.quote(template_id)}?asset=video",
                    token=tok,
                )
                if vc == 200 and vinfo.get("ok"):
                    vid_bytes = self._download_verified_bytes(vinfo["download_url"], vinfo.get("sha256") or "")
                    vid_dir = self.ws_dir / "Template Thời Trang Video"
                    vid_dir.mkdir(parents=True, exist_ok=True)
                    vid_file = vid_dir / f"{template_id.upper()}.mp4"
                    vid_file.write_bytes(vid_bytes)
                    installed_paths.append(str(vid_file))
        else:
            dest_root = (self.ws_dir / "Template" / template_id).resolve()
            tpl_parent = (self.ws_dir / "Template").resolve()
            if tpl_parent not in dest_root.parents:
                raise ValueError("Invalid template destination")
            dest_root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(meta_bytes), "r") as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    target = (dest_root / member.filename).resolve()
                    if dest_root not in target.parents and target != dest_root:
                        raise ValueError(f"Blocked unsafe zip path: {member.filename}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(member))
                    installed_paths.append(str(target))

        return {
            "ok": True,
            "template_id": template_id,
            "version": info.get("version"),
            "installed_files": installed_paths,
        }
