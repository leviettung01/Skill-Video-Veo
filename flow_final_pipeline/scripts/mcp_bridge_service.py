# -*- coding: utf-8 -*-
"""
SkillAutoVeo Secure MCP Server (JSON-RPC 2.0 / MCP 2025-03-26)
- Chỉ mở cho tài khoản được cấp quyền MCP (Cloud Lease entitlement hoặc Signed MCP Grant Key).
- Bảo mật tuyệt đối mã nguồn (src code): chỉ cung cấp các công cụ nghiệp vụ theo ID,
  lọc sạch mọi đường dẫn file hệ thống / traceback / cookie / token / API key.
- Hỗ trợ mọi AI Agent: Claude Desktop/Code, ChatGPT/Codex, Gemini CLI/Antigravity qua
  Streamable HTTP (`POST /mcp`) và thin stdio proxy (`mcp_stdio_proxy.py` / `--mcp-stdio`).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
WS_DIR = SCRIPTS_DIR.parent.parent
for _p in (str(WS_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DATA_DIR = WS_DIR / "data"
MCP_STATE_PATH = DATA_DIR / "mcp_state.json"
MCP_LICENSE_PATH = DATA_DIR / "mcp_license.json"
MCP_AUDIT_PATH = DATA_DIR / "mcp_audit.jsonl"

_MCP_LOCK = threading.RLock()
MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_SUPPORTED_VERSIONS = {"2025-03-26", "2024-11-05"}

# Public verification key / commercial signing secret (can be overridden in build/env)
_DEFAULT_GRANT_SECRET = "SkillAutoVeo-MCP-Grant-v1-Protected-Key-2026"

_SENSITIVE_KEY_RE = re.compile(
    r"(?:api[_-]?key|cookie|token|secret|password|authorization|bearer|proxy[_-]?auth|private[_-]?key|sig(?:nature)?)",
    re.IGNORECASE,
)
_CODE_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\[^\s\"'<>|]+|/(?:Users|home|var|etc|opt|tmp)/[^\s\"'<>|]+)",
    re.IGNORECASE,
)
_SRC_FILE_RE = re.compile(r"\b[\w\-]+\.(?:py|pyc|js|ts|html|bat|sh|env)\b", re.IGNORECASE)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def get_machine_hwid() -> str:
    """Stable machine fingerprint for binding MCP grants (matches cloud client format)."""
    machine_guid = ""
    vol_serial = ""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                val, _ = winreg.QueryValueEx(key, "MachineGuid")
                machine_guid = str(val or "").strip()
        except Exception:
            pass
        try:
            import ctypes
            import ctypes.wintypes
            serial = ctypes.wintypes.DWORD(0)
            if ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p("C:\\"), None, 0, ctypes.byref(serial), None, None, None, 0
            ):
                vol_serial = f"{serial.value:08x}"
        except Exception:
            pass
    parts = [
        platform.system(),
        platform.machine(),
        socket.gethostname(),
        machine_guid,
        vol_serial,
        "SkillAutoVeo-HWID-v1",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8", errors="ignore")).hexdigest()


def _grant_signing_secret() -> bytes:
    env_sec = os.environ.get("SKILL_MCP_SIGNING_SECRET", "").strip()
    return (env_sec or _DEFAULT_GRANT_SECRET).encode("utf-8")


def issue_signed_mcp_grant(
    account: str,
    hwid: str = "*",
    days: int = 365,
    tier: str = "pro_mcp",
    signing_secret: str = "",
) -> str:
    """
    Tạo chuỗi MCP Grant Key đã ký HMAC-SHA256 (`MCP1.<payload_b64>.<sig_b64>`) để cấp cho tài khoản được phép.
    """
    now_ts = int(time.time())
    payload = {
        "v": 1,
        "account": str(account or "").strip(),
        "hwid": str(hwid or "*").strip(),
        "tier": str(tier or "pro_mcp").strip(),
        "features": ["mcp", "mcp_access"],
        "iat": now_ts,
        "exp": now_ts + max(1, int(days)) * 86400,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    p_b64 = _b64url_encode(payload_bytes)
    sec = signing_secret.encode("utf-8") if signing_secret else _grant_signing_secret()
    sig = hmac.new(sec, p_b64.encode("ascii"), hashlib.sha256).digest()
    return f"MCP1.{p_b64}.{_b64url_encode(sig)}"


def verify_signed_mcp_grant(grant_key: str, signing_secret: str = "", expected_hwid: str = "") -> dict:
    """Xác thực chữ ký, hạn sử dụng và HWID của chuỗi `MCP1.<payload>.<sig>`."""
    raw = str(grant_key or "").strip()
    if not raw:
        return {"ok": False, "error": "Chưa có mã cấp quyền MCP."}
    parts = raw.split(".")
    if len(parts) != 3 or parts[0] != "MCP1":
        return {"ok": False, "error": "Định dạng mã cấp quyền MCP không hợp lệ (phải bắt đầu bằng MCP1.)."}
    _, p_b64, sig_b64 = parts
    sec = signing_secret.encode("utf-8") if signing_secret else _grant_signing_secret()
    expected_sig = _b64url_encode(hmac.new(sec, p_b64.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig_b64, expected_sig):
        return {"ok": False, "error": "Chữ ký mã cấp quyền MCP không hợp lệ hoặc đã bị chỉnh sửa."}
    try:
        payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
    except Exception:
        return {"ok": False, "error": "Không giải mã được nội dung giấy phép MCP."}
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Dữ liệu giấy phép MCP không hợp lệ."}
    exp = int(payload.get("exp") or 0)
    if exp > 0 and time.time() > exp:
        return {"ok": False, "error": "Quyền truy cập MCP của tài khoản này đã hết hạn."}
    feats = payload.get("features") or []
    if "mcp" not in feats and "mcp_access" not in feats:
        return {"ok": False, "error": "Gói cấp phép không bao gồm quyền MCP."}
    bound_hwid = str(payload.get("hwid") or "*").strip()
    cur_hwid = expected_hwid or get_machine_hwid()
    if bound_hwid not in ("", "*") and bound_hwid.lower() != cur_hwid.lower():
        return {"ok": False, "error": "Mã cấp quyền MCP này đã gắn cố định cho thiết bị khác."}
    return {
        "ok": True,
        "account": str(payload.get("account") or "licensed_user"),
        "tier": str(payload.get("tier") or "pro_mcp"),
        "expires_at": exp,
        "expires_at_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exp)) if exp else "Vĩnh viễn",
        "hwid_bound": bound_hwid not in ("", "*"),
    }


def _check_cloud_session_mcp_claim() -> dict | None:
    """
    Tự động kiểm tra quyền `mcp` / `mcp_access` từ Cloud Account Session nếu gói thương mại đã tích hợp `cloud_account_client`.
    """
    try:
        import cloud_account_client as cac  # type: ignore
        if hasattr(cac, "get_verified_session_claims"):
            claims = cac.get_verified_session_claims() or {}
            if isinstance(claims, dict):
                feats = claims.get("features") or claims.get("entitlements") or claims.get("addons") or []
                if claims.get("mcp_enabled") is True or "mcp" in feats or "mcp_access" in feats:
                    return {
                        "entitled": True,
                        "source": "cloud_license",
                        "account": str(claims.get("email") or claims.get("account") or claims.get("sub") or "cloud_user"),
                        "tier": str(claims.get("plan") or "cloud_pro_mcp"),
                        "expires_at": int(claims.get("exp") or 0),
                        "reason": "Đã kích hoạt tự động qua tài khoản Cloud được cấp quyền MCP.",
                    }
    except Exception:
        pass
    return None


def check_mcp_entitlement() -> dict:
    """
    Kiểm tra quyền mở tính năng kết nối AI Agent (MCP).
    Mặc định KHOÁ đối với tài khoản thường; chỉ mở khi:
      1. Tài khoản Cloud đã xác thực có claim `mcp` / `mcp_access` / `mcp_enabled=True`, HOẶC
      2. Có giấy phép `MCP1.<payload>.<sig>` hợp lệ tại `data/mcp_license.json`, HOẶC
      3. Biến môi trường quản trị nội bộ `SKILL_MCP_ADMIN_UNLOCK=1`.
    """
    if os.environ.get("SKILL_MCP_ADMIN_UNLOCK", "").strip().lower() in ("1", "true", "yes"):
        return {
            "entitled": True,
            "source": "admin_env",
            "account": "admin_dev",
            "tier": "enterprise_mcp",
            "expires_at": 0,
            "expires_at_str": "Không giới hạn (Admin Mode)",
            "reason": "Đang bật qua chế độ quản trị viên nội bộ.",
        }

    cloud_claim = _check_cloud_session_mcp_claim()
    if cloud_claim and cloud_claim.get("entitled"):
        return cloud_claim

    if MCP_LICENSE_PATH.is_file():
        try:
            lic = json.loads(MCP_LICENSE_PATH.read_text(encoding="utf-8"))
            grant_key = str((lic or {}).get("grant_key") or "").strip()
            ver = verify_signed_mcp_grant(grant_key)
            if ver.get("ok"):
                return {
                    "entitled": True,
                    "source": "signed_grant",
                    "account": ver["account"],
                    "tier": ver["tier"],
                    "expires_at": ver["expires_at"],
                    "expires_at_str": ver["expires_at_str"],
                    "reason": f"Đã kích hoạt cho tài khoản {ver['account']} (hạn: {ver['expires_at_str']}).",
                }
            return {
                "entitled": False,
                "source": "invalid_grant",
                "account": "",
                "tier": "",
                "expires_at": 0,
                "reason": ver.get("error") or "Giấy phép MCP không hợp lệ.",
            }
        except Exception:
            return {
                "entitled": False,
                "source": "corrupt_grant",
                "account": "",
                "tier": "",
                "expires_at": 0,
                "reason": "Không đọc được tệp giấy phép MCP.",
            }

    return {
        "entitled": False,
        "source": "locked",
        "account": "",
        "tier": "",
        "expires_at": 0,
        "reason": "Tính năng kết nối MCP với AI Agent chỉ mở cho các tài khoản được cấp quyền riêng. Vui lòng nhập Mã Cấp Quyền MCP (MCP1...) hoặc liên hệ quản trị viên.",
    }


def _load_mcp_state() -> dict:
    with _MCP_LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        state = {"enabled": False, "token": "", "updated_at": ""}
        if MCP_STATE_PATH.is_file():
            try:
                raw = json.loads(MCP_STATE_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    state.update(raw)
            except Exception:
                pass
        if not state.get("token") or len(str(state["token"])) < 24:
            state["token"] = "skv_mcp_" + secrets.token_urlsafe(32)
            state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_mcp_state(state)
        return state


def _save_mcp_state(state: dict) -> None:
    with _MCP_LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = MCP_STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, MCP_STATE_PATH)


def install_mcp_grant_key(grant_key: str) -> dict:
    ver = verify_signed_mcp_grant(grant_key)
    if not ver.get("ok"):
        return {"ok": False, "error": ver.get("error") or "Mã cấp quyền MCP không hợp lệ."}
    with _MCP_LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MCP_LICENSE_PATH.write_text(
            json.dumps(
                {
                    "grant_key": str(grant_key).strip(),
                    "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "account": ver["account"],
                    "tier": ver["tier"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        st = _load_mcp_state()
        st["enabled"] = True
        st["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save_mcp_state(st)
    return {"ok": True, "message": f"✅ Đã mở khóa quyền MCP AI Agent cho tài khoản {ver['account']}!", **get_mcp_ui_status()}


def set_mcp_enabled(enabled: bool) -> dict:
    ent = check_mcp_entitlement()
    if enabled and not ent.get("entitled"):
        return {"ok": False, "error": ent.get("reason") or "Tài khoản chưa được cấp quyền MCP."}
    st = _load_mcp_state()
    st["enabled"] = bool(enabled)
    st["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_mcp_state(st)
    return {"ok": True, **get_mcp_ui_status()}


def rotate_mcp_token() -> dict:
    ent = check_mcp_entitlement()
    if not ent.get("entitled"):
        return {"ok": False, "error": ent.get("reason") or "Tài khoản chưa được cấp quyền MCP."}
    st = _load_mcp_state()
    st["token"] = "skv_mcp_" + secrets.token_urlsafe(32)
    st["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_mcp_state(st)
    return {"ok": True, "message": "✅ Đã tạo Bearer Token MCP mới. Hãy cập nhật lại cấu hình trên AI Agent!", **get_mcp_ui_status()}


def _append_audit_log(entry: dict) -> None:
    try:
        with _MCP_LOCK:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(MCP_AUDIT_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def get_recent_audit_logs(limit: int = 20) -> list:
    if not MCP_AUDIT_PATH.is_file():
        return []
    try:
        lines = MCP_AUDIT_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for ln in lines[-max(1, min(100, limit)):]:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return list(reversed(out))
    except Exception:
        return []


def sanitize_error_message(msg: Any) -> str:
    """Loại bỏ hoàn toàn đường dẫn mã nguồn, traceback và thông tin nhạy cảm trước khi trả về cho AI Agent."""
    text = str(msg or "Thao tác không thành công.").strip()
    if "Traceback (most recent call last)" in text:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        text = lines[-1] if lines else "Lỗi xử lý nội bộ."
    text = _CODE_PATH_RE.sub("[internal-path]", text)
    text = _SRC_FILE_RE.sub("[module]", text)
    text = re.sub(r"ya29\.[A-Za-z0-9_-]{12,}", "[redacted-token]", text)
    text = re.sub(r"sk-[A-Za-z0-9_-]{16,}", "[redacted-key]", text)
    text = re.sub(r"__Secure-1PSID=[^\s;\"']+", "[redacted-cookie]", text)
    return text[:500]


def sanitize_for_mcp(obj: Any, _depth: int = 0) -> Any:
    """Đệ quy làm sạch mọi dữ liệu trước khi gửi qua MCP (bảo vệ tuyệt đối src code, cookie, token, đường dẫn máy)."""
    if _depth > 8:
        return "..."
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            ks = str(k)
            if _SENSITIVE_KEY_RE.search(ks):
                continue
            # Ẩn đường dẫn nội bộ hệ thống (trừ URL /api/media?path= đã được kiểm soát)
            if ks.lower() in ("project_dir", "output_dir", "final_videos_dir", "local_path", "script_path", "source_path"):
                continue
            clean[ks] = sanitize_for_mcp(v, _depth + 1)
        return clean
    if isinstance(obj, list):
        return [sanitize_for_mcp(x, _depth + 1) for x in obj[:150]]
    if isinstance(obj, str):
        if len(obj) > 3000:
            obj = obj[:3000] + "…"
        if re.search(r"\.(?:py|pyc|js|html|bat|env)$", obj.strip(), re.IGNORECASE):
            return "[protected]"
        if _CODE_PATH_RE.search(obj) and not obj.startswith("/api/media"):
            # Chỉ giữ tên file ngắn gọn cho media (mp4/jpg/png/webp/mp3), ẩn đường dẫn ổ đĩa thật
            if re.search(r"\.(?:mp4|jpg|jpeg|png|webp|mp3|wav)$", obj.strip(), re.IGNORECASE):
                return os.path.basename(obj.strip())
            return _CODE_PATH_RE.sub("[internal]", obj)
        return obj
    return obj


def build_client_configs(port: int = 8456, token: str = "") -> dict:
    """Sinh mẫu cấu hình kết nối sẵn cho Claude, ChatGPT/Codex, Gemini/Antigravity (HTTP & Stdio)."""
    url = f"http://127.0.0.1:{port}/mcp"
    tok = token or "<YOUR_MCP_TOKEN>"
    is_frozen = bool(getattr(sys, "frozen", False))
    stdio_cmd = sys.executable if is_frozen else "python"
    stdio_args = ["--mcp-stdio"] if is_frozen else ["mcp_stdio_proxy.py"]
    return {
        "endpoint_url": url,
        "antigravity_gemini": json.dumps(
            {
                "mcpServers": {
                    "skillautoveo": {
                        "serverUrl": url,
                        "headers": {"Authorization": f"Bearer {tok}"},
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        "claude_code_cli": f'claude mcp add --transport http skillautoveo {url} --header "Authorization: Bearer {tok}"',
        "claude_desktop_stdio": json.dumps(
            {
                "mcpServers": {
                    "skillautoveo": {
                        "command": stdio_cmd,
                        "args": stdio_args,
                        "env": {
                            "SKILL_MCP_URL": url,
                            "SKILL_MCP_TOKEN": tok,
                        },
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        "codex_chatgpt_toml": (
            "[mcp_servers.skillautoveo]\n"
            f'url = "{url}"\n'
            f'http_headers = {{ Authorization = "Bearer {tok}" }}\n'
        ),
    }


def get_mcp_ui_status(port: int = 8456) -> dict:
    ent = check_mcp_entitlement()
    st = _load_mcp_state()
    entitled = bool(ent.get("entitled"))
    enabled = bool(entitled and st.get("enabled"))
    tok = st.get("token") if entitled else ""
    masked = (tok[:12] + "••••••••" + tok[-6:]) if len(tok) > 20 else ""
    return {
        "ok": True,
        "entitled": entitled,
        "entitlement": ent,
        "enabled": enabled,
        "hwid_short": get_machine_hwid()[:16],
        "hwid_full": get_machine_hwid(),
        "endpoint_url": f"http://127.0.0.1:{port}/mcp",
        "token": tok,
        "token_masked": masked,
        "protocol_version": MCP_PROTOCOL_VERSION,
        "tools_count": len(get_mcp_tools_schema()),
        "tools_summary": [{"name": t["name"], "description": t["description"]} for t in get_mcp_tools_schema()],
        "client_configs": build_client_configs(port=port, token=tok) if entitled else {},
        "recent_audit": get_recent_audit_logs(20) if entitled else [],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ĐỊNH NGHĨA ĐẦY ĐỦ 28+ CÔNG CỤ MCP (AI AGENT ĐIỀU KHIỂN TOÀN BỘ TOOL)
# ═══════════════════════════════════════════════════════════════════════════════

def _schema(props: dict, required: list | None = None) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": required or [],
        "additionalProperties": False,
    }


def get_mcp_tools_schema() -> list[dict]:
    return [
        {
            "name": "studio_get_overview",
            "description": "Xem tổng quan toàn bộ hệ thống SkillAutoVeo: số dự án đang chạy/hoàn tất/lỗi, danh sách template, số sản phẩm kho, số nhân vật/giọng đọc, trạng thái tài khoản Google Flow & CLIProxy (đã ẩn toàn bộ thông tin nhạy cảm).",
            "inputSchema": _schema({}),
        },
        {
            "name": "studio_get_settings",
            "description": "Xem toàn bộ cấu hình hiện tại của tool: chế độ đa luồng (optimal/max/custom), số luồng Flow/FFmpeg, model video mặc định, tự động tạo & ghép Thumbnail 0.1s, phụ đề và B-Roll/FX.",
            "inputSchema": _schema({}),
        },
        {
            "name": "studio_update_settings",
            "description": "Cập nhật cấu hình vận hành của tool (VD: đổi chế độ đa luồng optimal/max/custom, đổi model video, bật/tắt tự tạo Thumbnail 0.1s, bật/tắt phụ đề, chỉnh độ trễ submit_delay_sec).",
            "inputSchema": _schema({
                "flow_concurrency_mode": {"type": "string", "enum": ["optimal", "max", "custom"]},
                "flow_video_model": {"type": "string", "description": "VD: Omni 1.2 Flash, Omni 1.1 Flash, Veo 3.1 - Fast"},
                "video_provider": {"type": "string", "enum": ["google_flow", "google_vids"]},
                "multi_account_enabled": {"type": "boolean"},
                "auto_generate_thumbnail": {"type": "boolean"},
                "auto_inject_thumbnail_01s": {"type": "boolean"},
                "thumbnail_provider": {"type": "string", "enum": ["google_flow", "chatgpt", "cliproxy_gemini"]},
                "flow_api_workers": {"type": "integer"},
                "parallel_products": {"type": "integer"},
                "submit_delay_sec": {"type": "number"},
                "enable_subtitles": {"type": "boolean"},
            }),
        },
        {
            "name": "accounts_list_status",
            "description": "Kiểm tra danh sách các tài khoản Google Flow và CLIProxy đã kết nối, số credits và trạng thái sẵn sàng (không bao giờ trả về cookie hay token).",
            "inputSchema": _schema({}),
        },
        {
            "name": "products_list",
            "description": "Liệt kê hoặc tìm kiếm sản phẩm trong Kho Sản Phẩm theo từ khoá hoặc lọc sản phẩm Hot để lấy product_id dùng tạo video.",
            "inputSchema": _schema({
                "query": {"type": "string", "description": "Từ khoá tìm theo tên hoặc ID sản phẩm"},
                "only_hot": {"type": "boolean"},
                "limit": {"type": "integer", "default": 30},
            }),
        },
        {
            "name": "products_add",
            "description": "Thêm 1 hoặc nhiều sản phẩm TikTok Shop vào Kho Sản Phẩm từ URL hoặc Product ID.",
            "inputSchema": _schema({
                "inputs": {"type": "array", "items": {"type": "string"}, "description": "Danh sách ID hoặc link sản phẩm TikTok Shop"},
            }, required=["inputs"]),
        },
        {
            "name": "products_delete",
            "description": "Xoá 1 sản phẩm khỏi Kho Sản Phẩm theo product_id.",
            "inputSchema": _schema({
                "product_id": {"type": "string"},
            }, required=["product_id"]),
        },
        {
            "name": "templates_list",
            "description": "Liệt kê toàn bộ kho Template video của tool (#001 Nhà Xưởng, #002 Đồ Ăn Vặt Voice, #003 Đồ Ăn Vặt ASMR, #004 Thời Trang Biến Hình, #005 Nấu Ăn POV, #006 Biến Hình Thời Trang, #007+...).",
            "inputSchema": _schema({}),
        },
        {
            "name": "templates_get_detail",
            "description": "Xem mô tả chi tiết, kịch bản và yêu cầu đầu vào của 1 Template theo mã (VD: '001', '004', '005', '006').",
            "inputSchema": _schema({
                "template_code": {"type": "string", "description": "Mã template: 001, 002, 003, 004, 005, 006..."},
            }, required=["template_code"]),
        },
        {
            "name": "characters_list",
            "description": "Liệt kê toàn bộ thư viện nhân vật (nv1..nv5 và nhân vật tự tạo), kèm mô tả ngoại hình, giọng đọc gắn cố định và trạng thái ảnh Character Sheet.",
            "inputSchema": _schema({}),
        },
        {
            "name": "voices_list",
            "description": "Liệt kê danh sách giọng đọc Tiếng Việt (Bắc/Nam/Trung, Nam/Nữ) và giọng gốc Google Flow kèm khuyến nghị ngành hàng.",
            "inputSchema": _schema({}),
        },
        {
            "name": "character_save",
            "description": "Tạo nhân vật mới hoặc cập nhật nhân vật sẵn có: đặt tên, mã nhân vật, mô tả ngoại hình tiếng Anh, gắn cố định giọng đọc (default_voice), số video/sản phẩm, và tuỳ chọn đính kèm ảnh base64.",
            "inputSchema": _schema({
                "key": {"type": "string", "description": "Mã nhân vật (VD: nv6; để trống tool tự đánh số)"},
                "name": {"type": "string", "description": "Tên hiển thị nhân vật"},
                "default_voice": {"type": "string", "description": "Mã giọng đọc trong voices_list (VD: nv1, nv2, v5_nam_bac_chuyen_gia...)"},
                "lock_voice_to_character": {"type": "boolean", "default": True},
                "videos_per_character": {"type": "integer", "default": 3},
                "appearance_en": {"type": "string", "description": "Mô tả ngoại hình tiếng Anh cho AI giữ khuôn mặt"},
                "enabled": {"type": "boolean", "default": True},
                "uploaded_image_base64": {"type": "string", "description": "Tuỳ chọn: ảnh Character Sheet dạng data:image/...;base64,..."},
                "uploaded_source_image_base64": {"type": "string", "description": "Tuỳ chọn: ảnh chân dung nhân vật gốc base64"},
            }, required=["name"]),
        },
        {
            "name": "character_generate_image",
            "description": "Tạo ảnh Character Sheet 6 góc bằng AI (Nano Banana 2.1 / ChatGPT Image / Gemini) cho 1 nhân vật, hỗ trợ truyền ảnh nhân vật gốc (source_image_base64) để giữ đúng khuôn mặt và tự động gắn vào nhân vật.",
            "inputSchema": _schema({
                "char_key": {"type": "string", "description": "Mã nhân vật (VD: nv1, nv6)"},
                "char_name": {"type": "string", "description": "Tên nhân vật nếu tạo mã mới"},
                "mode": {"type": "string", "enum": ["character_sheet", "product_ref"], "default": "character_sheet"},
                "model": {"type": "string", "enum": ["nano_banana", "chatgpt", "cliproxy_gemini"], "default": "nano_banana"},
                "appearance_en": {"type": "string", "description": "Mô tả ngoại hình tiếng Anh"},
                "pid": {"type": "string", "description": "Mã sản phẩm (chỉ dùng khi mode='product_ref')"},
                "source_image_base64": {"type": "string", "description": "Tuỳ chọn: ảnh chân dung gốc base64 để AI vẽ Character Sheet đúng mặt gốc"},
                "auto_apply_to_char": {"type": "boolean", "default": True},
            }, required=["char_key"]),
        },
        {
            "name": "character_sync_flow",
            "description": "Tự động upload ảnh Character Sheet của nhân vật lên tất cả tài khoản Google Flow sẵn sàng để lấy Character/Media UUID (người dùng không cần tạo tay trên Flow).",
            "inputSchema": _schema({
                "char_key": {"type": "string"},
                "target_profile": {"type": "string", "description": "Để trống hoặc 'all' để đồng bộ tất cả tài khoản sẵn sàng"},
            }, required=["char_key"]),
        },
        {
            "name": "character_delete",
            "description": "Xoá 1 nhân vật khỏi thư viện theo mã char_key.",
            "inputSchema": _schema({
                "char_key": {"type": "string"},
            }, required=["char_key"]),
        },
        {
            "name": "projects_list",
            "description": "Liệt kê các dự án trong Studio Dự Án, hỗ trợ lọc theo trạng thái/loại template (all, running, done, error, transform, fashion, cooking) và tìm theo tên/ID.",
            "inputSchema": _schema({
                "filter": {"type": "string", "enum": ["all", "running", "done", "error", "transform", "fashion", "cooking"], "default": "all"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 30},
            }),
        },
        {
            "name": "project_get_detail",
            "description": "Xem chi tiết toàn bộ biến thể video, từng phân cảnh (trạng thái, lời thoại, lỗi nếu có), thumbnail và tiến độ trực tiếp của 1 project_id.",
            "inputSchema": _schema({
                "project_id": {"type": "string"},
            }, required=["project_id"]),
        },
        {
            "name": "project_create_and_run",
            "description": "Tạo kịch bản & chạy đa luồng tạo video Affiliate cho 1 Product ID (hoặc URL TikTok Shop) theo Template #001, #002 hoặc #003. Có thể chỉ sinh kịch bản trước (auto_run=false) hoặc chạy thẳng tới Video Final + Thumbnail 0.1s (auto_run=true).",
            "inputSchema": _schema({
                "product_id_or_url": {"type": "string", "description": "ID sản phẩm trong kho (VD: 1738086213622335480) hoặc link TikTok Shop"},
                "template_code": {"type": "string", "default": "001", "description": "001 (Nhà Xưởng), 002 (Đồ Ăn Vặt Voice), 003 (Đồ Ăn Vặt ASMR)"},
                "videos_per_character": {"type": "integer", "default": 3, "description": "Số video/nhân vật (1-5)"},
                "auto_run": {"type": "boolean", "default": True},
                "force_regenerate_prompts": {"type": "boolean", "default": False},
            }, required=["product_id_or_url"]),
        },
        {
            "name": "project_stop",
            "description": "Huỷ / dừng ngay tiến trình đang chạy ngầm của bất kỳ dự án nào (#001-#006+).",
            "inputSchema": _schema({
                "project_id": {"type": "string"},
            }, required=["project_id"]),
        },
        {
            "name": "project_retry_scene",
            "description": "Chạy lại (Retry) 1 phân cảnh bị lỗi, 1 biến thể bị lỗi hoặc toàn bộ các cảnh lỗi của 1 dự án (#001-#006+) mà vẫn giữ nguyên các cảnh đã render thành công.",
            "inputSchema": _schema({
                "project_id": {"type": "string"},
                "vkey": {"type": "string", "description": "Mã biến thể (VD: v1, nv1_v1); để trống nếu retry cả dự án"},
                "scene_number": {"type": "integer", "description": "Số thứ tự phân cảnh cần chạy lại (1, 2, 3...); 0 để retry tất cả cảnh lỗi"},
                "retry_all_failed": {"type": "boolean", "default": False},
            }, required=["project_id"]),
        },
        {
            "name": "project_delete_unfinished",
            "description": "Xoá video/biến thể đang làm dở hoặc bị lỗi (hoặc dọn sạch file render dở của dự án để tạo lại từ đầu).",
            "inputSchema": _schema({
                "project_id": {"type": "string"},
                "vkey": {"type": "string", "description": "Mã biến thể cần xoá (VD: v1, nv1_v1)"},
                "remove_variant": {"type": "boolean", "default": False},
                "delete_project_if_single": {"type": "boolean", "default": False, "description": "Với dự án 1 video (#004/#005/#006+), true sẽ xoá hẳn dự án dở dang"},
            }, required=["project_id"]),
        },
        {
            "name": "project_delete",
            "description": "Xoá hẳn 1 dự án khỏi Studio Dự Án theo project_id.",
            "inputSchema": _schema({
                "project_id": {"type": "string"},
            }, required=["project_id"]),
        },
        {
            "name": "fashion_list_templates",
            "description": "Liệt kê kho template Video Thời Trang Biến Hình (#004, FVT_001..252) hỗ trợ lọc theo từ khoá.",
            "inputSchema": _schema({
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            }),
        },
        {
            "name": "cooking_quick_run",
            "description": "Tạo và chạy thẳng 1 video Nấu Ăn POV (Template #005) từ tên món ăn, giọng đọc (hoặc chế độ ASMR), số phân cảnh và phụ đề.",
            "inputSchema": _schema({
                "dish": {"type": "string", "description": "Tên món ăn (VD: Bún chả Hà Nội, Lẩu Thái hải sản)"},
                "audio_mode": {"type": "string", "enum": ["voice", "asmr"], "default": "voice"},
                "voice_id": {"type": "string", "description": "Mã giọng đọc trong voices_list (bỏ qua nếu asmr)"},
                "num_clips": {"type": "integer", "default": 3},
                "has_subtitles": {"type": "boolean", "default": True},
                "custom_notes": {"type": "string"},
            }, required=["dish"]),
        },
        {
            "name": "transform_list_presets",
            "description": "Xem danh sách kịch bản Biến Hình Thời Trang (#006 Làm nông / Bán cá và #007+) cùng hàng đợi đa luồng đang chạy.",
            "inputSchema": _schema({
                "template_code": {"type": "string", "default": "006"},
            }),
        },
        {
            "name": "transform_start",
            "description": "Khởi tạo & xếp hàng chạy đa luồng ngay 1 video Biến Hình 16s (Template #006 hoặc #007+) bằng sản phẩm trong kho (product_id) hoặc ảnh base64, chọn nhân vật (character_key) và model AI.",
            "inputSchema": _schema({
                "template_code": {"type": "string", "default": "006"},
                "preset": {"type": "string", "description": "Mã kịch bản: 'farm' (Làm nông) hoặc 'fish' (Bán cá)"},
                "product_id": {"type": "string", "description": "ID sản phẩm trong Kho Sản Phẩm"},
                "image_index": {"type": "integer", "default": 0},
                "product_upload": {"type": "string", "description": "Hoặc ảnh sản phẩm data:image/...;base64,..."},
                "product_label": {"type": "string"},
                "character_key": {"type": "string", "description": "Mã nhân vật thư viện (VD: nv1, nv5); để trống nếu để AI tự tạo"},
                "image_provider": {"type": "string", "enum": ["banana", "chatgpt", "cliproxy_gemini"], "default": "banana"},
                "video_model": {"type": "string", "enum": ["Omni 1.1 Flash", "Omni 1.2 Flash", "Veo 3.1 - Fast", "Veo 3.1 - Quality"], "default": "Omni 1.1 Flash"},
                "music": {"type": "boolean", "default": True},
            }, required=["preset"]),
        },
        {
            "name": "thumbnail_generate",
            "description": "Tạo ảnh Thumbnail AI 2K và tự động ghép 0.1s vào đầu Video Final cho 1 dự án (1 biến thể hoặc ALL).",
            "inputSchema": _schema({
                "project_id": {"type": "string"},
                "vkey": {"type": "string", "default": "ALL", "description": "VD: 'v1', 'nv1_v1' hoặc 'ALL'"},
                "provider": {"type": "string", "enum": ["google_flow", "chatgpt", "cliproxy_gemini"], "default": "google_flow"},
                "preset_id": {"type": "string"},
                "headline": {"type": "string"},
                "inject_01s": {"type": "boolean", "default": True},
            }, required=["project_id"]),
        },
        {
            "name": "workflows_list",
            "description": "Liệt kê danh sách các sơ đồ Workflow Flow đã lưu trong mục Workflow Flow.",
            "inputSchema": _schema({}),
        },
        {
            "name": "workflow_run",
            "description": "Chạy 1 sơ đồ Workflow Flow đã lưu theo workflow_id.",
            "inputSchema": _schema({
                "workflow_id": {"type": "string"},
            }, required=["workflow_id"]),
        },
    ]


MCP_AGENT_GUIDE_MD = """# SkillAutoVeo MCP Agent Operating Guide

Bạn đang điều khiển **SkillAutoVeo AI Video Studio** thông qua giao thức MCP bảo mật.

## Quy trình tiêu chuẩn nên dùng
1. **Kiểm tra trạng thái & tài nguyên trước khi chạy**:
   - Gọi `studio_get_overview` hoặc `accounts_list_status` để biết tài khoản Google Flow / CLIProxy nào đang `ready`.
   - Gọi `templates_list` để biết các mã Template hiện có (`001` Nhà Xưởng, `002` Đồ Ăn Vặt Voice, `003` Đồ Ăn Vặt ASMR, `004` Thời Trang Biến Hình, `005` Nấu Ăn POV, `006` Biến Hình Thời Trang).
   - Gọi `products_list` để tra cứu `product_id` trong kho (hoặc `products_add` để thêm link TikTok Shop mới).
2. **Tạo video theo đúng loại Template**:
   - Template `#001`, `#002`, `#003`: gọi `project_create_and_run(product_id_or_url, template_code, videos_per_character, auto_run=true)`.
   - Template `#005` (Nấu ăn POV): gọi `cooking_quick_run(dish, audio_mode, voice_id, num_clips)`.
   - Template `#006+` (Biến hình thời trang): gọi `transform_list_presets` rồi gọi `transform_start(preset="farm"|"fish", product_id=..., character_key=...)` — có thể gọi nhiều lần liên tiếp để xếp hàng đa luồng.
3. **Tạo nhân vật mới & giọng đọc**:
   - Gọi `voices_list` chọn giọng phù hợp -> gọi `character_save(name, default_voice, appearance_en)` -> gọi `character_generate_image(char_key, model="nano_banana"|"chatgpt", source_image_base64=...)` -> tuỳ chọn `character_sync_flow(char_key)`.
4. **Giám sát, xử lý lỗi & tối ưu**:
   - Theo dõi tiến độ bằng `projects_list(filter="running")` và `project_get_detail(project_id)`.
   - Dừng dự án bằng `project_stop(project_id)`.
   - Khi có phân cảnh lỗi, gọi `project_retry_scene(project_id, vkey, scene_number)` (hoặc `retry_all_failed=true`).
   - Khi làm sai/dở dang, gọi `project_delete_unfinished(project_id, vkey)` hoặc `project_delete(project_id)`.
"""


def get_mcp_resources_schema() -> list[dict]:
    return [
        {
            "uri": "skillautoveo://guide",
            "name": "SkillAutoVeo Agent Guide",
            "description": "Hướng dẫn đầy đủ cách kết hợp các công cụ MCP để tạo video, quản lý nhân vật, giọng đọc và xử lý lỗi.",
            "mimeType": "text/markdown",
        },
        {
            "uri": "skillautoveo://overview",
            "name": "Studio Live Overview",
            "description": "Ảnh chụp JSON trực tiếp trạng thái hệ thống (dự án, tài khoản sẵn sàng, template, cài đặt).",
            "mimeType": "application/json",
        },
    ]


def get_mcp_prompts_schema() -> list[dict]:
    return [
        {
            "name": "create_product_video",
            "description": "Hướng dẫn tạo video bán hàng từ mã sản phẩm và mã template",
            "arguments": [
                {"name": "product_id", "description": "ID sản phẩm trong kho hoặc URL TikTok Shop", "required": True},
                {"name": "template_code", "description": "Mã template (001, 002, 003, 006...)", "required": False},
            ],
        },
        {
            "name": "create_character_and_voice",
            "description": "Hướng dẫn tạo nhân vật mới, gắn giọng đọc cố định và tạo ảnh Character Sheet",
            "arguments": [
                {"name": "character_name", "description": "Tên nhân vật mới", "required": True},
                {"name": "voice_style", "description": "Phong cách giọng (VD: nữ miền Bắc, nam miền Nam)", "required": False},
            ],
        },
        {
            "name": "recover_failed_projects",
            "description": "Kiểm tra tất cả dự án đang lỗi trong Studio và tự động retry phân cảnh lỗi",
            "arguments": [],
        },
    ]


def _dispatch_tool(name: str, args: dict, ctx: dict) -> dict:
    """Thực thi an toàn 1 tool MCP bằng cách gọi trực tiếp các service nội bộ đã được kiểm soát."""
    import character_library_manager as clm
    import engine_settings_manager as esm
    import product_crawler_bridge as pcb
    import sync_web_ui_state as sws
    import template_manager as tm
    import veo_skill_cli as core

    runner = ctx.get("runner")
    retry_fn: Callable | None = ctx.get("retry_scene_fn")
    delete_proj_fn: Callable | None = ctx.get("delete_project_fn")
    get_transform_fn: Callable | None = ctx.get("get_transform_fn")

    if name == "studio_get_overview":
        sws.sync_web_ui(force=False)
        projs = core._load_projects_index()
        accs = [a for a in (esm.list_available_flow_accounts() or []) if a.get("active", True)]
        tpls = tm.list_video_templates()
        chars = clm.get_character_library_state()
        store = pcb.list_all_products_store()
        running = esm.list_all_running_pipelines()
        return {
            "ok": True,
            "total_projects": len(projs),
            "running_pipelines": len(running),
            "done_projects": sum(1 for p in projs if (p.get("done_products") or 0) > 0),
            "failed_projects": sum(1 for p in projs if (p.get("failed_products") or 0) > 0),
            "ready_flow_accounts": len(accs),
            "templates_count": len(tpls),
            "template_codes": [f"#{t.get('code')} {t.get('name')}" for t in tpls],
            "products_store_count": len(store.get("products") or []),
            "characters_count": len(chars.get("characters") or []),
            "voices_count": len(chars.get("voices") or []),
            "running_items": [
                {"project_id": r.get("pid"), "name": r.get("product_name"), "progress_pct": r.get("progress_pct"), "step": r.get("current_step_text")}
                for r in running[:10]
            ],
        }

    if name == "studio_get_settings":
        cfg = esm.load_engine_settings()
        keep_keys = (
            "video_provider", "google_vids_model", "flow_video_model", "multi_account_enabled",
            "flow_concurrency_mode", "auto_flow_concurrency", "flow_api_workers",
            "max_inflight_per_account", "max_total_inflight", "submit_delay_sec",
            "parallel_products", "upscale_download_workers", "auto_generate_thumbnail",
            "auto_inject_thumbnail_01s", "thumbnail_duration_sec", "thumbnail_provider",
            "thumbnail_selection_mode", "thumbnail_preset_id", "subtitle_settings",
            "camera_broll_settings", "video_edit_fx_settings", "detected_flow_accounts_count",
        )
        return {"ok": True, "settings": {k: cfg.get(k) for k in keep_keys}}

    if name == "studio_update_settings":
        upd = dict(args or {})
        if "enable_subtitles" in upd:
            en_sub = bool(upd.pop("enable_subtitles"))
            cur_sub = dict((esm.load_engine_settings() or {}).get("subtitle_settings") or {})
            cur_sub["enable_subtitles"] = en_sub
            upd["subtitle_settings"] = cur_sub
        res = esm.save_engine_settings(upd)
        return {"ok": bool(res.get("ok", True)), "message": "Đã cập nhật cấu hình hệ thống.", "flow_concurrency_mode": (res.get("settings") or {}).get("flow_concurrency_mode")}

    if name == "accounts_list_status":
        accs = esm.list_available_flow_accounts() or []
        return {
            "ok": True,
            "total": len(accs),
            "accounts": [
                {
                    "name": a.get("name"),
                    "profile_name": a.get("profile_name"),
                    "active": bool(a.get("active", True)),
                    "tag": a.get("tag") or "",
                    "credits": a.get("credits"),
                    "ready_for_vids": bool(a.get("ready_for_vids")),
                }
                for a in accs
            ],
        }

    if name == "products_list":
        store = pcb.list_all_products_store()
        items = list(store.get("products") or [])
        q = str(args.get("query") or "").strip().lower()
        if q:
            items = [x for x in items if q in (str(x.get("title") or "") + " " + str(x.get("product_id") or "") + " " + str(x.get("category") or "")).lower()]
        if args.get("only_hot"):
            items = [x for x in items if x.get("is_hot")]
        lim = max(1, min(100, int(args.get("limit") or 30)))
        return {
            "ok": True,
            "total_matched": len(items),
            "products": [
                {
                    "product_id": str(x.get("product_id") or ""),
                    "title": str(x.get("title") or ""),
                    "category": str(x.get("category") or ""),
                    "price": x.get("price") or x.get("price_label") or "",
                    "is_hot": bool(x.get("is_hot")),
                    "images_count": len(x.get("local_images") or []),
                }
                for x in items[:lim]
            ],
        }

    if name == "products_add":
        inputs = args.get("inputs") or []
        if not isinstance(inputs, list) or not inputs:
            return {"ok": False, "error": "Cần cung cấp ít nhất 1 Product ID hoặc link TikTok Shop."}
        results = []
        for raw_in in inputs[:20]:
            try:
                r = pcb.add_product_to_store(str(raw_in).strip())
                results.append({"input": str(raw_in), "ok": bool(r.get("ok")), "product_id": r.get("product_id"), "title": r.get("title"), "error": r.get("error")})
            except Exception as exc:
                results.append({"input": str(raw_in), "ok": False, "error": sanitize_error_message(exc)})
        return {"ok": any(r.get("ok") for r in results), "results": results}

    if name == "products_delete":
        pid = str(args.get("product_id") or "").strip()
        if not pid:
            return {"ok": False, "error": "Thiếu product_id."}
        return pcb.delete_product_from_store(pid)

    if name == "templates_list":
        tpls = tm.list_video_templates()
        return {
            "ok": True,
            "templates": [
                {
                    "code": str(t.get("code") or "").lstrip("#"),
                    "name": t.get("name") or t.get("folder_name"),
                    "folder_name": t.get("folder_name"),
                    "description": str(t.get("description") or "")[:240],
                    "pipeline_kind": t.get("pipeline_kind") or "",
                }
                for t in tpls
            ],
        }

    if name == "templates_get_detail":
        code = str(args.get("template_code") or "").strip().lstrip("#")
        tpls = tm.list_video_templates()
        found = next((t for t in tpls if str(t.get("code") or "").lstrip("#") == code), None)
        if not found:
            return {"ok": False, "error": f"Không tìm thấy template mã #{code}."}
        return {
            "ok": True,
            "code": str(found.get("code") or "").lstrip("#"),
            "name": found.get("name"),
            "description": found.get("description"),
            "pipeline_kind": found.get("pipeline_kind"),
            "num_scenes": found.get("num_scenes"),
            "seconds_per_scene": found.get("seconds_per_scene"),
            "presets": found.get("presets") if isinstance(found.get("presets"), (dict, list)) else None,
        }

    if name == "characters_list":
        st = clm.get_character_library_state()
        return {
            "ok": True,
            "characters": [
                {
                    "key": c.get("key"),
                    "name": c.get("name"),
                    "enabled": bool(c.get("enabled", True)),
                    "default_voice": c.get("default_voice"),
                    "voice_name": c.get("voice_name"),
                    "videos_per_character": c.get("videos_per_character"),
                    "appearance_en": c.get("appearance_en"),
                    "has_sheet_image": bool(c.get("ref_image_path")),
                    "synced_flow_accounts": list((c.get("account_character_ids") or {}).keys()),
                }
                for c in (st.get("characters") or [])
            ],
        }

    if name == "voices_list":
        st = clm.get_character_library_state()
        v_list = st.get("voices_list") if isinstance(st.get("voices_list"), list) else list((st.get("voices") or {}).values())
        return {
            "ok": True,
            "voices": [
                {
                    "key": v.get("key"),
                    "name": v.get("name"),
                    "gender": v.get("gender"),
                    "region": v.get("region"),
                    "tone_style": v.get("tone_style"),
                    "description": str(v.get("description") or "")[:180],
                }
                for v in v_list
                if isinstance(v, dict)
            ],
            "builtin_flow_voices": [
                {"slug": b.get("slug"), "display_name": b.get("display_name")}
                for b in (st.get("builtin_flow_voices") or [])
                if isinstance(b, dict)
            ],
        }

    if name == "character_save":
        res = clm.save_character_library_settings({"character": dict(args or {})})
        return {"ok": True, "characters_count": len(res.get("characters") or []), "message": "Đã lưu nhân vật thành công."}

    if name == "character_generate_image":
        res = clm.generate_character_or_product_image(dict(args or {}))
        return {
            "ok": bool(res.get("ok")),
            "model_used": res.get("model_used"),
            "applied_to_char": bool(res.get("applied_to_char")),
            "error": res.get("error"),
        }

    if name == "character_sync_flow":
        res = clm.sync_character_to_google_flow(str(args.get("char_key") or ""), str(args.get("target_profile") or ""))
        return {
            "ok": bool(res.get("ok")),
            "char_key": res.get("char_key"),
            "synced_count": res.get("synced_count", 0),
            "synced_accounts": list((res.get("synced_accounts") or {}).keys()),
            "message": res.get("message") or res.get("error"),
        }

    if name == "character_delete":
        res = clm.delete_character(str(args.get("char_key") or ""))
        return {"ok": bool(res.get("ok", True)), "error": res.get("error")}

    if name == "projects_list":
        sws.sync_web_ui(force=False)
        projs = core._load_projects_index()
        f = str(args.get("filter") or "all").strip().lower()
        q = str(args.get("query") or "").strip().lower()
        if f == "running":
            projs = [p for p in projs if p.get("is_running")]
        elif f == "done":
            projs = [p for p in projs if (p.get("done_products") or 0) > 0]
        elif f == "error":
            projs = [p for p in projs if (p.get("failed_products") or 0) > 0]
        elif f == "transform":
            projs = [p for p in projs if p.get("pipeline_kind") == "fashion_transformation" or str(p.get("template_code") or "").lstrip("#") == "006"]
        elif f == "fashion":
            projs = [p for p in projs if p.get("is_fashion_motion_project") or str(p.get("template_code") or "").lstrip("#") == "004"]
        elif f == "cooking":
            projs = [p for p in projs if p.get("pipeline_kind") == "cooking_storyboard" or str(p.get("template_code") or "").lstrip("#") == "005"]
        if q:
            projs = [p for p in projs if q in (str(p.get("name") or "") + " " + str(p.get("id") or "")).lower()]
        lim = max(1, min(100, int(args.get("limit") or 30)))
        return {
            "ok": True,
            "total": len(projs),
            "projects": [
                {
                    "project_id": p.get("id"),
                    "name": p.get("name"),
                    "template_code": str(p.get("template_code") or "").lstrip("#"),
                    "pipeline_kind": p.get("pipeline_kind") or ("fashion_motion" if p.get("is_fashion_motion_project") else "basic"),
                    "is_running": bool(p.get("is_running")),
                    "progress_pct": int(p.get("progress_pct") or 0),
                    "done_videos": int(p.get("done_products") or 0),
                    "total_videos": int(p.get("total_products") or 0),
                    "failed_videos": int(p.get("failed_products") or 0),
                    "thumbnails_count": int(p.get("thumbnails_count") or 0),
                    "current_step": str(p.get("current_step_text") or "")[:180],
                    "updated_at": p.get("updated_at") or "",
                }
                for p in projs[:lim]
            ],
        }

    if name == "project_get_detail":
        pid = str(args.get("project_id") or "").strip()
        if not pid:
            return {"ok": False, "error": "Thiếu project_id."}
        proj = core.load_project(pid)
        if not proj:
            return {"ok": False, "error": f"Không tìm thấy dự án '{pid}'."}
        live = esm.get_project_live_progress(pid)
        return {
            "ok": True,
            "project_id": proj.get("id"),
            "name": proj.get("name"),
            "template_code": str(proj.get("template_code") or "").lstrip("#"),
            "is_running": bool(live.get("is_running") or proj.get("is_running")),
            "progress_pct": int(live.get("progress_pct") or proj.get("progress_pct") or 0),
            "current_step": live.get("current_step_text") or proj.get("current_step_text") or "",
            "variants": [
                {
                    "vkey": pr.get("vkey") or pr.get("char_v_code") or pr.get("id"),
                    "title": pr.get("product_name"),
                    "status": pr.get("status"),
                    "error_msg": pr.get("error_msg") or "",
                    "has_final_video": bool(pr.get("final_video_path")),
                    "has_thumbnail": bool(pr.get("has_thumbnail") or pr.get("thumbnail_path")),
                    "scenes": [
                        {
                            "scene_number": sc.get("scene_number"),
                            "status": sc.get("status"),
                            "has_video": bool(sc.get("video_path")),
                            "error_msg": sc.get("error_msg") or sc.get("error") or "",
                        }
                        for sc in (pr.get("scenes") or [])
                    ],
                }
                for pr in (proj.get("products") or [])
            ],
        }

    if name == "project_create_and_run":
        raw_in = str(args.get("product_id_or_url") or "").strip()
        if not raw_in:
            return {"ok": False, "error": "Thiếu product_id_or_url."}
        res = pcb.prepare_and_optionally_run_product(
            raw_id_or_url=raw_in,
            template_name=str(args.get("template_code") or "001").strip().lstrip("#"),
            crawl_method="auto",
            videos_per_character=int(args.get("videos_per_character") or 3),
            force_regenerate_prompts=bool(args.get("force_regenerate_prompts", False)),
            auto_run_pipeline=bool(args.get("auto_run", True)),
        )
        sws.sync_web_ui(force=True)
        return {
            "ok": bool(res.get("ok")),
            "project_id": res.get("project_id") or res.get("pid"),
            "template_name": res.get("template_name"),
            "videos_count": res.get("videos_count"),
            "auto_run": bool(args.get("auto_run", True)),
            "error": res.get("error"),
        }

    if name == "project_stop":
        pid = str(args.get("project_id") or "").strip()
        if not pid:
            return {"ok": False, "error": "Thiếu project_id."}
        res = esm.stop_running_pipeline(pid)
        sws.sync_web_ui(force=True)
        return {"ok": bool(res.get("ok")), "project_id": pid, "stopped": bool(res.get("stopped", res.get("ok"))), "error": res.get("error")}

    if name == "project_retry_scene":
        if callable(retry_fn):
            return retry_fn(dict(args or {}))
        return {"ok": False, "error": "Chức năng retry chưa sẵn sàng."}

    if name == "project_delete_unfinished":
        return sws.delete_unfinished_variant(
            pid=str(args.get("project_id") or "").strip(),
            vkey=str(args.get("vkey") or "").strip(),
            remove_variant=bool(args.get("remove_variant", False)),
            delete_project_if_single=bool(args.get("delete_project_if_single", False)),
        )

    if name == "project_delete":
        pid = str(args.get("project_id") or "").strip()
        if not pid:
            return {"ok": False, "error": "Thiếu project_id."}
        if callable(delete_proj_fn):
            return delete_proj_fn(pid)
        return sws.delete_unfinished_variant(pid=pid, delete_project_if_single=True)

    if name == "fashion_list_templates":
        import fashion_motion_control_engine as fmce
        cat = fmce.get_fashion_video_templates_catalog()
        items = list(cat.get("templates") or [])
        q = str(args.get("query") or "").strip().lower()
        if q:
            items = [t for t in items if q in (str(t.get("title") or "") + " " + str(t.get("template_id") or "") + " " + str(t.get("category") or "")).lower()]
        lim = max(1, min(100, int(args.get("limit") or 25)))
        return {
            "ok": True,
            "total": len(items),
            "templates": [
                {"template_id": t.get("template_id") or t.get("id"), "title": t.get("title"), "category": t.get("category")}
                for t in items[:lim]
            ],
        }

    if name == "cooking_quick_run":
        import cooking_storyboard_engine as cooking
        dish = str(args.get("dish") or "").strip()
        if not dish:
            return {"ok": False, "error": "Thiếu tên món ăn (dish)."}
        accounts = cooking.list_cooking_flow_accounts()
        prof = next((a["profile_name"] for a in accounts if a.get("has_cookies")), (accounts[0]["profile_name"] if accounts else ""))
        if not prof:
            return {"ok": False, "error": "Chưa có tài khoản Google Flow sẵn sàng để chạy Nấu Ăn POV."}
        voices = cooking.list_cooking_voices()
        v_id = str(args.get("voice_id") or "").strip() or next((v["key"] for v in voices if v.get("recommended_for_cooking")), (voices[0]["key"] if voices else ""))
        from cooking_recipe_ai import generate_cooking_recipe_and_script
        recipe = generate_cooking_recipe_and_script(
            dish=dish,
            num_clips=int(args.get("num_clips") or 3),
            audio_mode=str(args.get("audio_mode") or "voice"),
            voice_id=v_id,
            custom_notes=str(args.get("custom_notes") or ""),
        )
        prepared = cooking.prepare_project(
            dish=dish,
            recipe=recipe,
            voice_id=v_id,
            audio_mode=str(args.get("audio_mode") or "voice"),
            profile_name=prof,
            has_subtitles=bool(args.get("has_subtitles", True)),
        )
        proj_id = prepared.get("project_id")
        cooking.launch_stage(proj_id, "auto", profile_name=prof)
        sws.sync_web_ui(force=True)
        return {"ok": True, "project_id": proj_id, "dish": dish, "message": f"Đã tạo và chạy ngầm video Nấu Ăn POV cho món '{dish}'."}

    if name == "transform_list_presets":
        te = get_transform_fn() if callable(get_transform_fn) else __import__("transform_engine")
        code = str(args.get("template_code") or "006").strip().lstrip("#")
        d = te.default(template_code=code)
        j = te.list_jobs(template_code=code, limit=12)
        return {
            "ok": True,
            "template_code": code,
            "presets": {k: {"title": v.get("title"), "summary": v.get("summary")} for k, v in (d.get("presets") or {}).items()},
            "active_count": j.get("active_count", 0),
            "queued_count": j.get("queued_count", 0),
            "max_slots": j.get("max_slots", 2),
            "recent_jobs": [{"project_id": x.get("id"), "name": x.get("name"), "status": x.get("status"), "progress_pct": x.get("progress_pct")} for x in (j.get("jobs") or [])[:8]],
        }

    if name == "transform_start":
        te = get_transform_fn() if callable(get_transform_fn) else __import__("transform_engine")
        res = te.start(dict(args or {}), runner)
        sws.sync_web_ui(force=True)
        return {"ok": True, "project_id": res.get("id"), "max_slots": res.get("max_slots"), "message": f"Đã đưa dự án {res.get('id')} vào hàng đợi chạy đa luồng tại Studio."}

    if name == "thumbnail_generate":
        pid = str(args.get("project_id") or "").strip()
        vk = str(args.get("vkey") or "ALL").strip()
        if not pid:
            return {"ok": False, "error": "Thiếu project_id."}
        if vk.upper() == "ALL":
            res = esm.generate_thumbnails_for_project(
                pid=pid,
                provider=str(args.get("provider") or "google_flow"),
                preset_id=str(args.get("preset_id") or ""),
                headline=str(args.get("headline") or ""),
                inject_01s=bool(args.get("inject_01s", True)),
            )
        else:
            res = esm.generate_thumbnail_for_variant(
                pid=pid,
                vkey=vk,
                provider=str(args.get("provider") or "google_flow"),
                preset_id=str(args.get("preset_id") or ""),
                headline=str(args.get("headline") or ""),
                inject_01s=bool(args.get("inject_01s", True)),
            )
        sws.sync_web_ui(force=True)
        return {"ok": bool(res.get("ok")), "project_id": pid, "vkey": vk, "injected_01s": res.get("injected_01s"), "error": res.get("error")}

    if name == "workflows_list":
        import flow_workflow_engine as fwe
        wfs = fwe.list_workflows()
        return {
            "ok": True,
            "workflows": [{"id": w.get("id"), "name": w.get("name"), "nodes_count": len(w.get("nodes") or [])} for w in (wfs or [])],
        }

    if name == "workflow_run":
        import flow_workflow_engine as fwe
        wf_id = str(args.get("workflow_id") or "").strip()
        if not wf_id:
            return {"ok": False, "error": "Thiếu workflow_id."}
        res = fwe.run_workflow_async(wf_id)
        return {"ok": bool(res.get("ok")), "workflow_id": wf_id, "message": res.get("message") or res.get("error")}

    return {"ok": False, "error": f"Không hỗ trợ công cụ MCP '{name}'."}


def handle_mcp_http_request(
    raw_body: bytes,
    headers: dict,
    client_host: str = "127.0.0.1",
    ctx: dict | None = None,
) -> tuple[int, dict]:
    """
    Xử lý 1 request JSON-RPC 2.0 MCP trên `POST /mcp`.
    Trả về `(http_status_code, json_response_dict)`.
    """
    # 1. Bảo mật chống truy cập ngoài localhost / DNS rebinding
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        return 403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32003, "message": "MCP chỉ cho phép kết nối cục bộ (localhost)."}}

    host_hdr = str(headers.get("Host") or headers.get("host") or "").strip().lower()
    if host_hdr and not (host_hdr.startswith("127.0.0.1") or host_hdr.startswith("localhost") or host_hdr.startswith("[::1]")):
        return 403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32003, "message": "Host header không hợp lệ."}}

    # 2. Kiểm tra quyền cấp phép tài khoản (Entitlement Gate)
    ent = check_mcp_entitlement()
    st = _load_mcp_state()
    if not ent.get("entitled"):
        return 403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": ent.get("reason") or "Tài khoản chưa được cấp quyền MCP."}}
    if not st.get("enabled"):
        return 403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32002, "message": "Cổng MCP đang tắt. Hãy bật 'Kết nối AI Agent (MCP)' trong mục Cài Đặt."}}

    # 3. Xác thực Bearer Token
    auth_hdr = str(headers.get("Authorization") or headers.get("authorization") or "").strip()
    supplied_tok = auth_hdr[7:].strip() if auth_hdr.lower().startswith("bearer ") else ""
    if not supplied_tok or not hmac.compare_digest(supplied_tok, str(st.get("token") or "")):
        return 401, {"jsonrpc": "2.0", "id": None, "error": {"code": -32004, "message": "Thiếu hoặc sai Bearer Token MCP."}}

    # 4. Parse JSON-RPC 2.0
    try:
        req = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON-RPC parse error"}}

    if not isinstance(req, dict):
        return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid JSON-RPC request"}}

    req_id = req.get("id")
    method = str(req.get("method") or "").strip()
    params = req.get("params") if isinstance(req.get("params"), dict) else {}

    def _ok(result: Any) -> tuple[int, dict]:
        return 200, {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _err(code: int, message: str) -> tuple[int, dict]:
        return 200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": sanitize_error_message(message)}}

    if method == "initialize":
        req_ver = str(params.get("protocolVersion") or MCP_PROTOCOL_VERSION)
        neg_ver = req_ver if req_ver in MCP_SUPPORTED_VERSIONS else MCP_PROTOCOL_VERSION
        return _ok({
            "protocolVersion": neg_ver,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {
                "name": "SkillAutoVeo-MCP",
                "version": "1.0.0",
            },
            "instructions": MCP_AGENT_GUIDE_MD,
        })

    if method in ("notifications/initialized", "notifications/cancelled"):
        return 202, {}

    if method == "ping":
        return _ok({"pong": True, "ts": int(time.time())})

    if method == "tools/list":
        return _ok({"tools": get_mcp_tools_schema()})

    if method == "resources/list":
        return _ok({"resources": get_mcp_resources_schema()})

    if method == "resources/read":
        uri = str(params.get("uri") or "").strip()
        if uri == "skillautoveo://guide":
            return _ok({"contents": [{"uri": uri, "mimeType": "text/markdown", "text": MCP_AGENT_GUIDE_MD}]})
        if uri == "skillautoveo://overview":
            ov = sanitize_for_mcp(_dispatch_tool("studio_get_overview", {}, ctx or {}))
            return _ok({"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(ov, ensure_ascii=False, indent=2)}]})
        return _err(-32602, f"Resource không tồn tại: {uri}")

    if method == "prompts/list":
        return _ok({"prompts": get_mcp_prompts_schema()})

    if method == "prompts/get":
        pname = str(params.get("name") or "").strip()
        pargs = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if pname == "create_product_video":
            pid = pargs.get("product_id") or "<product_id>"
            tpl = pargs.get("template_code") or "001"
            msg = f"Hãy kiểm tra sản phẩm `{pid}` trong kho (products_list) và tạo video theo Template #{tpl} bằng `project_create_and_run` (hoặc `transform_start` nếu là Template #006), sau đó báo lại `project_id` và trạng thái chạy."
            return _ok({"description": "Tạo video cho sản phẩm", "messages": [{"role": "user", "content": {"type": "text", "text": msg}}]})
        if pname == "create_character_and_voice":
            cname = pargs.get("character_name") or "Nhân vật mới"
            vstyle = pargs.get("voice_style") or "nữ miền Bắc năng lượng"
            msg = f"Hãy xem `voices_list` để chọn giọng phù hợp '{vstyle}', sau đó gọi `character_save` tạo nhân vật '{cname}' gắn cố định giọng đó, rồi gọi `character_generate_image` tạo Character Sheet 6 góc bằng AI và gọi `character_sync_flow` đồng bộ lên Google Flow."
            return _ok({"description": "Tạo nhân vật mới & giọng đọc", "messages": [{"role": "user", "content": {"type": "text", "text": msg}}]})
        if pname == "recover_failed_projects":
            msg = "Hãy gọi `projects_list(filter='error')`, kiểm tra chi tiết từng dự án lỗi bằng `project_get_detail`, sau đó gọi `project_retry_scene(..., retry_all_failed=true)` để tự động khôi phục các phân cảnh lỗi."
            return _ok({"description": "Khôi phục các dự án lỗi", "messages": [{"role": "user", "content": {"type": "text", "text": msg}}]})
        return _err(-32602, f"Prompt không tồn tại: {pname}")

    if method == "tools/call":
        t_name = str(params.get("name") or "").strip()
        t_args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        valid_names = {t["name"] for t in get_mcp_tools_schema()}
        if t_name not in valid_names:
            return _err(-32602, f"Công cụ MCP không tồn tại: {t_name}")

        t0 = time.time()
        try:
            raw_res = _dispatch_tool(t_name, t_args, ctx or {})
            clean_res = sanitize_for_mcp(raw_res)
            is_err = isinstance(clean_res, dict) and clean_res.get("ok") is False
            _append_audit_log({
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "account": ent.get("account") or "",
                "tool": t_name,
                "args": sanitize_for_mcp(t_args),
                "ok": not is_err,
                "ms": round((time.time() - t0) * 1000),
            })
            return _ok({
                "content": [{"type": "text", "text": json.dumps(clean_res, ensure_ascii=False, indent=2)}],
                "isError": bool(is_err),
            })
        except Exception as exc:
            safe_err = sanitize_error_message(exc)
            _append_audit_log({
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "account": ent.get("account") or "",
                "tool": t_name,
                "args": sanitize_for_mcp(t_args),
                "ok": False,
                "error": safe_err,
                "ms": round((time.time() - t0) * 1000),
            })
            return _ok({
                "content": [{"type": "text", "text": json.dumps({"ok": False, "error": safe_err}, ensure_ascii=False)}],
                "isError": True,
            })

    return _err(-32601, f"Method không hỗ trợ: {method}")
