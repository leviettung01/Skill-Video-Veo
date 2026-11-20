# -*- coding: utf-8 -*-
"""
⚡ Lê Việt Tùng - SkillAutoVeo
Quản lý:
  1. Tự động nhận diện thông số phần cứng máy tính (CPU, RAM, GPU NVIDIA NVENC) & đề xuất số luồng tối ưu.
  2. Cấu hình Đa luồng & Đa tài khoản Google Flow / CLIProxy (`engine_settings.json`).
  3. Theo dõi Tiến trình đang chạy trực tiếp (Live Process & Pipeline Monitor).
  4. Tạo Ảnh Thumbnail Chuyên Nghiệp (Google Flow Nano Banana 2K / ChatGPT Image) theo Nhân vật + Sản phẩm
     và ghép vào 0.1s đầu Video Final (hoặc tải ảnh Thumbnail riêng).
"""
import os
import sys
import re
import glob
import json
import time
import shutil
import ctypes
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
WS_DIR = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
FINAL_VIDEOS_DIR = os.path.join(WS_DIR, "final_videos")
THUMBS_ROOT_DIR = os.path.join(WS_DIR, "thumbnails")
CHARS_DIR = os.path.join(PIPELINE_DIR, "characters")
ENGINE_SETTINGS_JSON = os.path.join(PIPELINE_DIR, "engine_settings.json")

os.makedirs(THUMBS_ROOT_DIR, exist_ok=True)
os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from thumbnail_template_engine import (
    THUMBNAIL_TEMPLATES,
    THUMBNAIL_CATEGORIES,
    DEFAULT_CATEGORY_THUMBNAIL_MAP,
    detect_product_thumbnail_category,
    resolve_thumbnail_template,
    composite_template_product_insets,
    get_template_by_id,
)
from video_fx_and_broll_engine import (
    BACKGROUND_CREDIBILITY_STYLES,
    DEFAULT_CAMERA_BROLL_SETTINGS,
    DEFAULT_VIDEO_EDIT_FX_SETTINGS,
    upgrade_project_prompts_with_camera_broll,
)
from subtitle_template_engine import (
    SUBTITLE_TEMPLATES,
    SUBTITLE_CATEGORIES,
    AVAILABLE_SUBTITLE_FONTS,
    SUBTITLE_ANIMATION_STYLES,
    DEFAULT_SUBTITLE_SETTINGS,
    resolve_subtitle_settings,
    ensure_all_subtitle_demo_images,
)

THUMBNAIL_PRESETS = THUMBNAIL_TEMPLATES

DEFAULT_ENGINE_SETTINGS = {
    # 1. Đa luồng & Đa tài khoản Google Flow / Google Vids Web
    "video_provider": "google_flow",  # 'google_flow' (aisandbox-pa + Voice UUID) | 'google_vids' (docs.google.com/videos Omni 1080p • Zero reCAPTCHA)
    "google_vids_model": "omni",  # 'omni' (Model 12 • Lên tới 15s 1080p) | 'veo_3_1' (Model 9)
    "flow_video_model": "",
    "multi_account_enabled": True,
    "selected_flow_profile": "",
    "auto_flow_concurrency": True,
    "flow_concurrency_mode": "optimal",
    "flow_api_workers": 6,
    "max_inflight_per_account": 5,
    "max_total_inflight": 10,
    "submit_delay_sec": 4.5,
    "global_submit_stagger_sec": 0.7,
    "parallel_products": 4,
    "upscale_download_workers": 6,
    "extension_pool_tabs": 4,
    # 2. Đa luồng Render Video FFmpeg (Tự động theo phần cứng máy tính)
    "auto_hardware_tuning": True,
    "ffmpeg_render_workers": 3,
    "ffmpeg_threads_per_job": 4,
    "video_encoder": "auto",  # 'auto' | 'h264_nvenc' | 'libx264'
    "ffmpeg_preset": "fast",
    # 3. Cài đặt Tạo Ảnh Thumbnail AI, Kho Template Đa Ngành Hàng & Ghép 0.1s đầu Video
    "auto_generate_thumbnail": True,
    "auto_inject_thumbnail_01s": True,
    "thumbnail_duration_sec": 0.1,
    "thumbnail_provider": "google_flow",  # 'google_flow' (Nano Banana 2K) | 'chatgpt' (ChatGPT Image / CLIProxy)
    "thumbnail_selection_mode": "auto_category",  # 'fixed' | 'auto_category' | 'custom_category'
    "rotate_templates_per_variant": True,
    "category_thumbnail_map": dict(DEFAULT_CATEGORY_THUMBNAIL_MAP),
    "thumbnail_preset_id": "gia_dung_3grid_pro",
    "thumbnail_master_prompt": THUMBNAIL_PRESETS[0]["master_prompt"],
    "thumbnail_embed_product_insets": True,
    "thumbnail_add_text_badge": False,
    # 4. Hệ thống 1 (Độc lập): Góc Máy Uy Tín (Nhà Xưởng / Kho Hàng / Luxury) & Đạo Diễn B-Roll Cận Sản Phẩm (SHOT 1 -> SHOT 2 -> SHOT 3)
    "camera_broll_settings": dict(DEFAULT_CAMERA_BROLL_SETTINGS),
    # 5. Hệ thống 2 (Độc lập): Hiệu Ứng Visual FX Trực Tiếp Trong Prompt Render AI Video (Không chèn chữ/subtitle)
    "video_edit_fx_settings": dict(DEFAULT_VIDEO_EDIT_FX_SETTINGS),
    # 6. Hệ thống 3 (Độc lập): Kho Template Subtitle & Studio Tùy Chỉnh Phụ Đề Chuyên Nghiệp
    "subtitle_settings": dict(DEFAULT_SUBTITLE_SETTINGS),
}

_HW_CACHE = None


def detect_hardware_specs(force_refresh: bool = False) -> dict:
    """Phát hiện thông số CPU, RAM, GPU NVIDIA & FFmpeg Encoder của máy tính để tự động tính số luồng tối ưu."""
    global _HW_CACHE
    if _HW_CACHE is not None and not force_refresh:
        return _HW_CACHE

    cpu_threads = os.cpu_count() or 4
    cpu_name = os.environ.get("PROCESSOR_IDENTIFIER", "x86_64 Processor")
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if val:
                cpu_name = str(val).strip()
        except Exception:
            pass

    total_ram_gb = 8.0
    avail_ram_gb = 4.0
    if sys.platform == "win32":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_ram_gb = round(stat.ullTotalPhys / (1024 ** 3), 1)
                avail_ram_gb = round(stat.ullAvailPhys / (1024 ** 3), 1)
        except Exception:
            pass

    gpu_name = ""
    gpu_vram_mb = 0
    has_nvenc = False
    try:
        r_smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if r_smi.returncode == 0 and r_smi.stdout.strip():
            first_line = r_smi.stdout.strip().splitlines()[0]
            parts = [x.strip() for x in first_line.split(",")]
            gpu_name = parts[0]
            if len(parts) > 1 and parts[1].isdigit():
                gpu_vram_mb = int(parts[1])
    except Exception:
        pass

    try:
        r_enc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "h264_nvenc" in (r_enc.stdout or "") and gpu_name:
            # Kiểm tra nhanh h264_nvenc có hoạt động thực tế không
            r_test = subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1",
                    "-c:v", "h264_nvenc", "-f", "null", "-",
                ],
                capture_output=True,
                timeout=5,
            )
            has_nvenc = (r_test.returncode == 0)
    except Exception:
        pass

    # Tính toán số luồng FFmpeg & CPU threads khuyến nghị theo cấu hình thực tế của máy
    if has_nvenc:
        rec_ffmpeg_workers = min(6, max(2, int(total_ram_gb // 6)))
        rec_threads_per_job = max(2, min(4, cpu_threads // max(1, rec_ffmpeg_workers)))
        rec_encoder = "h264_nvenc"
    else:
        rec_ffmpeg_workers = max(1, min(6, cpu_threads // 4, int(max(1, total_ram_gb // 4))))
        rec_threads_per_job = max(2, min(8, cpu_threads // max(1, rec_ffmpeg_workers)))
        rec_encoder = "libx264"

    _HW_CACHE = {
        "cpu_name": cpu_name,
        "cpu_threads": cpu_threads,
        "total_ram_gb": total_ram_gb,
        "avail_ram_gb": avail_ram_gb,
        "gpu_name": gpu_name or "Card tích hợp / CPU Rendering",
        "gpu_vram_mb": gpu_vram_mb,
        "has_nvenc": has_nvenc,
        "recommended": {
            "ffmpeg_render_workers": rec_ffmpeg_workers,
            "ffmpeg_threads_per_job": rec_threads_per_job,
            "video_encoder": rec_encoder,
            "ffmpeg_preset": "fast" if rec_encoder == "libx264" else "p4",
        },
    }
    return _HW_CACHE


def _has_saved_cookie_file(prof: str) -> bool:
    p = (prof or "").split("@")[0].strip()
    if not p:
        return False
    for cpath in (
        os.path.join(WS_DIR, "cookies", f"{p}.json"),
        os.path.join(WS_DIR, "data", "google_flow_grok", "cookies", f"{p}.json"),
    ):
        if os.path.isfile(cpath) and os.path.getsize(cpath) > 100:
            return True
    return False


_CLIPROXY_MODELS_CACHE = {"ts": 0.0, "models": []}
_DEFAULT_CLIPROXY_CHAT_PRIORITY = (
    "gemini-3.5-flash-lite",
    "gemini-3-flash",
    "gemini-3.8-flash-high",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash-tiered",
    "gpt-5.6-luna",
    "gpt-6-luna",
    "gpt-5.6-terra",
    "claude-sonnet-4-6",
    "gemini-2.5-flash",
    "gpt-4o-mini",
    "gpt-4o",
)
_CLIPROXY_NON_CHAT_HINTS = ("image", "codex-auto-review", "-sol", "-astra", "chat-thinking", "tts", "whisper")


def get_cliproxy_config() -> dict:
    """Trả về cấu hình CLIProxy cục bộ (`url`, `api_key`) từ accounts.json hoặc env."""
    base_url = os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317").strip().rstrip("/")
    api_key = os.environ.get("CLIPROXY_API_KEY", "").strip()
    if not api_key:
        for acc_path in (
            os.path.join(WS_DIR, "data", "google_flow_grok", "accounts.json"),
            os.path.join(WS_DIR, "accounts.json"),
        ):
            if not os.path.isfile(acc_path):
                continue
            try:
                with open(acc_path, "r", encoding="utf-8") as _f_acc0:
                    rows = json.load(_f_acc0)
                if isinstance(rows, list):
                    for r in rows:
                        if isinstance(r, dict) and "8317" in str(r.get("proxy_url") or "") and r.get("api_key"):
                            api_key = str(r["api_key"]).strip()
                            break
                if api_key:
                    break
            except Exception:
                pass
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip() or "grok-video-key-001"
    return {"url": base_url, "api_key": api_key}


def resolve_cliproxy_chat_models(preferred=(), timeout: float = 1.5, force_refresh: bool = False) -> list:
    """Lấy danh sách model chat/vision hợp lệ trên CLIProxy (:8317/v1/models), ưu tiên model chạy ổn định."""
    cfg = get_cliproxy_config()
    now = time.time()
    cached = _CLIPROXY_MODELS_CACHE.get("models") or []
    if cached and not force_refresh and (now - float(_CLIPROXY_MODELS_CACHE.get("ts") or 0)) < 120.0:
        avail = list(cached)
    else:
        avail = []
        try:
            import urllib.request as _ur
            req = _ur.Request(
                f"{cfg['url']}/v1/models",
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
            )
            with _ur.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            avail = [str(m.get("id") or "").strip() for m in (data.get("data") or []) if isinstance(m, dict) and m.get("id")]
            if avail:
                _CLIPROXY_MODELS_CACHE["ts"] = now
                _CLIPROXY_MODELS_CACHE["models"] = list(avail)
        except Exception:
            avail = list(cached)

    pref_list = [str(m).strip() for m in (preferred or ()) if str(m or "").strip() and str(m).strip().lower() != "auto"]
    ordered = []
    seen = set()

    def _add(m_id: str):
        if m_id and m_id not in seen:
            seen.add(m_id)
            ordered.append(m_id)

    if avail:
        avail_set = set(avail)
        for m in pref_list:
            if m in avail_set:
                _add(m)
        for m in _DEFAULT_CLIPROXY_CHAT_PRIORITY:
            if m in avail_set:
                _add(m)
        for m in avail:
            ml = m.lower()
            if not any(h in ml for h in _CLIPROXY_NON_CHAT_HINTS):
                _add(m)
    for m in pref_list or ("gemini-3.5-flash-lite", "gemini-2.5-flash", "gpt-4o-mini"):
        _add(m)
    return ordered


def get_default_flow_project_id(profile_name: str = "") -> str:
    """Tìm Google Flow Project UUID đang cấu hình cho profile hoặc từ account sẵn có (không hardcode tài khoản dev)."""
    prof_target = str(profile_name or "").split("@")[0].strip().lower()
    for acc_path in (
        os.path.join(WS_DIR, "data", "google_flow_grok", "accounts.json"),
        os.path.join(WS_DIR, "accounts.json"),
        os.path.join(WS_DIR, "data", "google_flow_grok", "Flow_nhieu_worker_accounts.json"),
    ):
        if not os.path.isfile(acc_path):
            continue
        try:
            with open(acc_path, "r", encoding="utf-8") as _f_acc1:
                items = json.load(_f_acc1)
            if not isinstance(items, list):
                continue
            fallback_pid = ""
            for it in items:
                if not isinstance(it, dict):
                    continue
                pid = str(it.get("project_id") or "").strip()
                if not pid:
                    purl = str(it.get("proxy_url") or "").strip()
                    if re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,}$", purl):
                        pid = purl
                if not pid:
                    continue
                p_name = str(it.get("profile_name") or os.path.basename(str(it.get("profile_dir") or "").rstrip("\\/")) or "").split("@")[0].strip().lower()
                if prof_target and p_name == prof_target:
                    return pid
                if not fallback_pid:
                    fallback_pid = pid
            if not prof_target and fallback_pid:
                return fallback_pid
        except Exception:
            pass
    try:
        raw_env = os.environ.get("FLOW_DEFAULT_PROJECT_ID", "").strip()
        if raw_env:
            return raw_env
    except Exception:
        pass
    return ""


def list_available_flow_accounts() -> list:
    """Liệt kê toàn bộ tài khoản / profile Google Flow sẵn sàng để chạy đa tài khoản (chỉ bật xoay vòng cho profile đã có Cookie hợp lệ)."""
    accounts = []
    seen_profiles = set()

    # 1. Đọc từ data/google_flow_grok/accounts.json & accounts.json
    for acc_path in (
        os.path.join(WS_DIR, "data", "google_flow_grok", "accounts.json"),
        os.path.join(WS_DIR, "accounts.json"),
    ):
        if os.path.isfile(acc_path):
            try:
                with open(acc_path, "r", encoding="utf-8") as _f_acc2:
                    items = json.load(_f_acc2)
                if isinstance(items, list):
                    for it in items:
                        raw_prof = str(it.get("profile_name") or "").strip()
                        prof = raw_prof.split("@")[0].strip()
                        name = str(it.get("name") or prof or "").strip()
                        if not prof or "grok" in name.lower() or "codex" in name.lower() or "cliproxy" in name.lower():
                            continue
                        if prof in seen_profiles:
                            continue
                        has_ck = _has_saved_cookie_file(prof) or ("flow_cookie:" in str(it.get("api_key") or ""))
                        auth_st = str(it.get("auth_state") or "").strip().lower()
                        if not has_ck and auth_st == "logging_in":
                            continue
                        seen_profiles.add(prof)
                        accounts.append({
                            "name": name or f"Google_{prof}",
                            "profile_name": prof,
                            "project_id": str(it.get("proxy_url") or it.get("project_id") or get_default_flow_project_id(prof)),
                            "active": bool(it.get("active", True)) and has_ck,
                            "has_cookies": has_ck,
                        })
            except Exception:
                pass

    # 2. Quét thêm thư mục cookies/*.json nếu có profile chưa nằm trong accounts.json
    for c_dir in (
        os.path.join(WS_DIR, "cookies"),
        os.path.join(WS_DIR, "data", "google_flow_grok", "cookies"),
    ):
        if os.path.isdir(c_dir):
            for fp in sorted(glob.glob(os.path.join(c_dir, "*.json"))):
                prof = os.path.splitext(os.path.basename(fp))[0].split("@")[0].strip()
                if prof and prof not in seen_profiles and os.path.getsize(fp) > 100:
                    seen_profiles.add(prof)
                    accounts.append({
                        "name": f"Google_{prof}",
                        "profile_name": prof,
                        "project_id": get_default_flow_project_id(prof),
                        "active": True,
                        "has_cookies": True,
                    })

    return accounts


_EXT_TABS_CACHE = {"ts": 0.0, "ready_tabs": 4}


def get_live_extension_ready_tabs(default: int = 4, probe_timeout: float = 0.35) -> int:
    """Lấy số tab Extension Google Flow đang mở từ local CaptchaBridge (:4000) nếu sẵn sàng (cache 10s)."""
    now = time.time()
    if (now - float(_EXT_TABS_CACHE.get("ts") or 0.0)) < 10.0 and int(_EXT_TABS_CACHE.get("ready_tabs") or 0) > 0:
        return int(_EXT_TABS_CACHE["ready_tabs"])
    val = int(default or 4)
    sec_path = os.path.join(WS_DIR, "data", "captcha-bridge.secret")
    if os.path.isfile(sec_path):
        try:
            import urllib.request as _ur
            with open(sec_path, "r", encoding="utf-8") as _f_sec:
                secret = _f_sec.read().strip()
            if secret:
                req = _ur.Request(
                    "http://127.0.0.1:4000/api/internal/captcha/stats",
                    headers={"x-local-auth": secret},
                )
                opener = _ur.build_opener(_ur.ProxyHandler({}))
                with opener.open(req, timeout=probe_timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                if isinstance(data, dict) and data.get("extensionOnline"):
                    rt = int(data.get("readyTabs") or data.get("effectiveConcurrency") or val)
                    if rt >= 1:
                        val = max(1, min(16, rt))
        except Exception:
            pass
    _EXT_TABS_CACHE["ts"] = now
    _EXT_TABS_CACHE["ready_tabs"] = val
    return val


def compute_flow_concurrency_profile(
    num_accounts: int,
    ready_tabs: int = 4,
    multi_account_enabled: bool = True,
) -> dict:
    """
    Tính toán thông số đa luồng tối ưu ("nhanh vừa đủ, an toàn chống 429") và trần tối đa an toàn
    dựa trên số tài khoản Google Flow hợp lệ (A) và số tab Extension giải reCAPTCHA song song (T).
    """
    raw_accs = max(1, int(num_accounts or 1))
    acc = raw_accs if multi_account_enabled else 1
    tabs = max(1, min(12, int(ready_tabs or 4)))

    # 1. Mặc định Tối ưu ("Nhanh vừa đủ": hạn chế 429 & bảo vệ reCAPTCHA v3 score)
    opt_delay = 5.0 if acc == 1 else (4.5 if acc <= 3 else 4.0)
    opt_pool_tabs = min(6, max(3, acc + 2))
    opt_stagger = 0.8 if acc == 1 else (0.7 if acc <= 3 else 0.6)
    opt_per_acc = 4 if acc == 1 else 5
    opt_total_inflight = min(80, acc * opt_per_acc)
    opt_workers = min(24, max(4, acc * 3))
    opt_dl_workers = min(24, max(4, acc * 3))
    opt_products = min(12, max(2, acc * 2))
    opt_eff_tabs = max(tabs, opt_pool_tabs)
    opt_interval = round(max(opt_stagger, opt_delay / acc), 2)
    opt_ext_rpm = round(opt_eff_tabs * (60.0 / 2.5) * 0.85, 1)
    opt_rpm = round(min(60.0 / opt_interval, opt_ext_rpm), 1)

    # 2. Trần Tối Đa An Toàn ("Max Speed": chạm ngưỡng an toàn trước khi tụt reCAPTCHA / [8] TOO_MUCH_TRAFFIC)
    max_delay = 3.6 if acc <= 2 else (3.0 if acc <= 4 else 2.4)
    max_pool_tabs = 3 if acc >= 2 else 2
    max_stagger = 0.55 if acc <= 3 else 0.4
    max_per_acc = 16 if acc <= 2 else 12
    max_total_inflight = min(120, acc * max_per_acc)
    max_workers = min(48, max(12, acc * 12, tabs * 3))
    max_dl_workers = min(32, max(16, acc * 12, tabs * 2))
    max_products = min(16, max(3, acc * 3))
    max_eff_tabs = max(tabs, max_pool_tabs)
    max_interval = round(max(max_stagger, max_delay / acc), 2)
    max_ext_rpm = round(max_eff_tabs * (60.0 / 2.5) * 0.85, 1)
    max_rpm = round(min(60.0 / max_interval, max_ext_rpm), 1)

    return {
        "accounts_count": raw_accs,
        "effective_accounts": acc,
        "ready_tabs": tabs,
        "extension_live_rpm": round(tabs * (60.0 / 2.5) * 0.85, 1),
        "optimal": {
            "flow_api_workers": opt_workers,
            "max_inflight_per_account": opt_per_acc,
            "max_total_inflight": opt_total_inflight,
            "submit_delay_sec": opt_delay,
            "global_submit_stagger_sec": opt_stagger,
            "parallel_products": opt_products,
            "upscale_download_workers": opt_dl_workers,
            "extension_pool_tabs": opt_pool_tabs,
            "effective_global_interval_sec": opt_interval,
            "est_requests_per_min": opt_rpm,
        },
        "max": {
            "flow_api_workers": max_workers,
            "max_inflight_per_account": max_per_acc,
            "max_total_inflight": max_total_inflight,
            "submit_delay_sec": max_delay,
            "global_submit_stagger_sec": max_stagger,
            "parallel_products": max_products,
            "upscale_download_workers": max_dl_workers,
            "extension_pool_tabs": max_pool_tabs,
            "effective_global_interval_sec": max_interval,
            "est_requests_per_min": max_rpm,
        },
    }


def _resolve_flow_mode(cfg: dict) -> str:
    mode = str((cfg or {}).get("flow_concurrency_mode") or "").strip().lower()
    if mode in ("optimal", "max", "custom"):
        return mode
    return "optimal" if bool((cfg or {}).get("auto_flow_concurrency", True)) else "custom"


def get_effective_flow_concurrency(ready_tabs: int = None, cfg: dict = None) -> dict:
    """Trả về cấu hình luồng thực thi hiệu lực (tự động hoặc custom) cho tất cả engine."""
    cur_cfg = dict(cfg) if isinstance(cfg, dict) else load_engine_settings()
    flow_accs = cur_cfg.get("detected_flow_accounts")
    if not isinstance(flow_accs, list):
        flow_accs = [a for a in list_available_flow_accounts() if a.get("active", True)]
    multi_acc = bool(cur_cfg.get("multi_account_enabled", True))
    sel_profs = [str(p).strip() for p in (cur_cfg.get("selected_flow_profiles") or []) if str(p).strip()]
    if multi_acc and sel_profs:
        filtered = [a for a in flow_accs if str(a.get("profile_name") or "").strip() in sel_profs]
        if filtered:
            flow_accs = filtered
    tabs = int(ready_tabs) if ready_tabs is not None else int(cur_cfg.get("extension_ready_tabs") or 4)
    profile = compute_flow_concurrency_profile(max(1, len(flow_accs)), ready_tabs=tabs, multi_account_enabled=multi_acc)
    mode = _resolve_flow_mode(cur_cfg)
    if mode in ("optimal", "max"):
        picked = dict(profile[mode])
    else:
        acc_eff = profile["effective_accounts"]
        delay_val = max(1.0, min(60.0, float(cur_cfg.get("submit_delay_sec") or profile["optimal"]["submit_delay_sec"])))
        stagger_val = max(0.25, min(10.0, float(cur_cfg.get("global_submit_stagger_sec") or profile["optimal"]["global_submit_stagger_sec"])))
        pool_tabs = max(1, min(8, int(cur_cfg.get("extension_pool_tabs") or profile["optimal"]["extension_pool_tabs"])))
        eff_int = round(max(stagger_val, delay_val / max(1, acc_eff)), 2)
        eff_ext_rpm = round(max(tabs, pool_tabs) * (60.0 / 2.5) * 0.85, 1)
        picked = {
            "flow_api_workers": max(1, min(40, int(cur_cfg.get("flow_api_workers") or profile["optimal"]["flow_api_workers"]))),
            "max_inflight_per_account": max(1, min(20, int(cur_cfg.get("max_inflight_per_account") or profile["optimal"]["max_inflight_per_account"]))),
            "max_total_inflight": max(1, min(120, int(cur_cfg.get("max_total_inflight") or profile["optimal"]["max_total_inflight"]))),
            "submit_delay_sec": delay_val,
            "global_submit_stagger_sec": stagger_val,
            "parallel_products": max(1, min(16, int(cur_cfg.get("parallel_products") or profile["optimal"]["parallel_products"]))),
            "upscale_download_workers": max(1, min(32, int(cur_cfg.get("upscale_download_workers") or profile["optimal"]["upscale_download_workers"]))),
            "extension_pool_tabs": pool_tabs,
            "effective_global_interval_sec": eff_int,
            "est_requests_per_min": round(min(60.0 / eff_int, eff_ext_rpm), 1),
        }
    picked["mode"] = mode
    picked["auto_flow_concurrency"] = (mode != "custom")
    picked["multi_account_enabled"] = multi_acc
    picked["accounts_count"] = profile["accounts_count"]
    picked["effective_accounts"] = profile["effective_accounts"]
    picked["ready_tabs"] = profile["ready_tabs"]
    return picked


def load_engine_settings() -> dict:
    hw = detect_hardware_specs()
    cfg = dict(DEFAULT_ENGINE_SETTINGS)
    cfg["ffmpeg_render_workers"] = hw["recommended"]["ffmpeg_render_workers"]
    cfg["ffmpeg_threads_per_job"] = hw["recommended"]["ffmpeg_threads_per_job"]

    saved = {}
    if os.path.isfile(ENGINE_SETTINGS_JSON):
        try:
            with open(ENGINE_SETTINGS_JSON, "r", encoding="utf-8") as _f_es:
                raw_saved = json.load(_f_es)
            if isinstance(raw_saved, dict):
                saved = raw_saved
                cfg.update(raw_saved)
        except Exception:
            pass

    if cfg.get("auto_hardware_tuning", True):
        cfg["ffmpeg_render_workers"] = hw["recommended"]["ffmpeg_render_workers"]
        cfg["ffmpeg_threads_per_job"] = hw["recommended"]["ffmpeg_threads_per_job"]

    flow_accs = [a for a in list_available_flow_accounts() if a.get("active", True)]
    sel_multi = [str(p).strip() for p in (cfg.get("selected_flow_profiles") or []) if str(p).strip()]
    conc_accs = flow_accs
    if bool(cfg.get("multi_account_enabled", True)) and sel_multi:
        filt_conc = [a for a in flow_accs if str(a.get("profile_name") or "").strip() in sel_multi]
        if filt_conc:
            conc_accs = filt_conc
    ready_tabs = get_live_extension_ready_tabs(default=int(cfg.get("extension_pool_tabs") or 4))
    flow_profile = compute_flow_concurrency_profile(
        max(1, len(conc_accs)),
        ready_tabs=ready_tabs,
        multi_account_enabled=bool(cfg.get("multi_account_enabled", True)),
    )
    flow_mode = _resolve_flow_mode(cfg)
    cfg["flow_concurrency_mode"] = flow_mode
    cfg["auto_flow_concurrency"] = (flow_mode != "custom")
    cfg["extension_ready_tabs"] = ready_tabs
    cfg["flow_recommended"] = flow_profile
    if flow_mode in ("optimal", "max"):
        rec_flow = flow_profile[flow_mode]
        for k in (
            "flow_api_workers",
            "max_inflight_per_account",
            "max_total_inflight",
            "submit_delay_sec",
            "global_submit_stagger_sec",
            "parallel_products",
            "upscale_download_workers",
            "extension_pool_tabs",
        ):
            cfg[k] = rec_flow[k]
    else:
        eff_custom = get_effective_flow_concurrency(ready_tabs=ready_tabs, cfg={**cfg, "detected_flow_accounts": flow_accs})
        for k in (
            "flow_api_workers",
            "max_inflight_per_account",
            "max_total_inflight",
            "submit_delay_sec",
            "global_submit_stagger_sec",
            "parallel_products",
            "upscale_download_workers",
            "extension_pool_tabs",
        ):
            cfg[k] = eff_custom[k]
    try:
        import google_vids_client as _gvc
        vids_map = {x["profile_name"]: x for x in _gvc.list_available_vids_accounts()}
        for a in flow_accs:
            vi = vids_map.get(a.get("profile_name") or "")
            a["ready_for_vids"] = bool(vi and vi.get("ready_for_vids"))
    except Exception:
        pass
    cfg["detected_flow_accounts_count"] = len(flow_accs)
    cfg["detected_flow_accounts"] = flow_accs
    cfg["hardware"] = hw
    # Migrate only obsolete thumbnail settings, preserving unrelated settings.
    cfg['thumbnail_catalog_version'] = 'ai-complete-v3'
    cfg['thumbnail_embed_product_insets'] = False
    cfg['composite_product_insets'] = False
    cfg['thumbnail_add_text_badge'] = False
    cfg['thumbnail_preset_id'] = get_template_by_id(cfg.get('thumbnail_preset_id',''))['id']
    cfg['category_thumbnail_map'] = {k:get_template_by_id(v)['id'] for k,v in (cfg.get('category_thumbnail_map') or {}).items()}
    cfg['thumbnail_master_prompt'] = get_template_by_id(cfg['thumbnail_preset_id'])['master_prompt']
    cfg["thumbnail_presets"] = [
        {k: v for k, v in tpl.items() if k != "palette"}
        for tpl in THUMBNAIL_PRESETS
    ]
    cfg["thumbnail_categories"] = THUMBNAIL_CATEGORIES
    cfg["background_credibility_styles"] = BACKGROUND_CREDIBILITY_STYLES
    if not isinstance(cfg.get("category_thumbnail_map"), dict):
        cfg["category_thumbnail_map"] = dict(DEFAULT_CATEGORY_THUMBNAIL_MAP)
    else:
        merged_map = dict(DEFAULT_CATEGORY_THUMBNAIL_MAP)
        merged_map.update(cfg["category_thumbnail_map"])
        cfg["category_thumbnail_map"] = merged_map

    merged_cam = dict(DEFAULT_CAMERA_BROLL_SETTINGS)
    if isinstance(cfg.get("camera_broll_settings"), dict):
        merged_cam.update(cfg["camera_broll_settings"])
    cfg["camera_broll_settings"] = merged_cam

    merged_fx = dict(DEFAULT_VIDEO_EDIT_FX_SETTINGS)
    if isinstance(cfg.get("video_edit_fx_settings"), dict):
        merged_fx.update(cfg["video_edit_fx_settings"])
    cfg["video_edit_fx_settings"] = merged_fx

    cfg["subtitle_settings"] = resolve_subtitle_settings(cfg.get("subtitle_settings"))
    cfg["subtitle_presets"] = ensure_all_subtitle_demo_images(force=False)
    cfg["subtitle_categories"] = SUBTITLE_CATEGORIES
    cfg["subtitle_fonts"] = AVAILABLE_SUBTITLE_FONTS
    cfg["subtitle_animations"] = SUBTITLE_ANIMATION_STYLES
    return cfg


def save_engine_settings(new_settings: dict) -> dict:
    cur = load_engine_settings()
    allowed_keys = set(DEFAULT_ENGINE_SETTINGS.keys())
    to_save = {k: cur.get(k, DEFAULT_ENGINE_SETTINGS[k]) for k in allowed_keys}
    for k, v in (new_settings or {}).items():
        if k in allowed_keys:
            to_save[k] = v

    # Ép kiểu chuẩn xác
    vid_prov = str(to_save.get("video_provider") or "google_flow").strip().lower()
    if vid_prov not in ("google_flow", "google_vids"):
        vid_prov = "google_flow"
    to_save["video_provider"] = vid_prov
    vids_m = str(to_save.get("google_vids_model") or "omni").strip().lower()
    if vids_m not in ("omni", "veo_3_1"):
        vids_m = "omni"
    to_save["google_vids_model"] = vids_m
    to_save["multi_account_enabled"] = bool(to_save.get("multi_account_enabled", True))
    _explicit_ns = new_settings or {}
    _flow_num_keys = (
        "flow_api_workers",
        "max_inflight_per_account",
        "max_total_inflight",
        "submit_delay_sec",
        "global_submit_stagger_sec",
        "parallel_products",
        "upscale_download_workers",
        "extension_pool_tabs",
    )
    if (
        "flow_concurrency_mode" not in _explicit_ns
        and "auto_flow_concurrency" not in _explicit_ns
        and any(k in _explicit_ns for k in _flow_num_keys)
    ):
        mode_raw = "custom"
    else:
        mode_raw = str(_explicit_ns.get("flow_concurrency_mode") or "").strip().lower()
        if mode_raw not in ("optimal", "max", "custom"):
            if "auto_flow_concurrency" in _explicit_ns:
                mode_raw = "optimal" if bool(_explicit_ns.get("auto_flow_concurrency")) else "custom"
            else:
                mode_raw = _resolve_flow_mode(to_save)
    to_save["flow_concurrency_mode"] = mode_raw
    to_save["auto_flow_concurrency"] = (mode_raw != "custom")
    if mode_raw in ("optimal", "max"):
        flow_accs = [a for a in list_available_flow_accounts() if a.get("active", True)]
        prof_auto = compute_flow_concurrency_profile(
            max(1, len(flow_accs)),
            ready_tabs=get_live_extension_ready_tabs(default=int(to_save.get("extension_pool_tabs") or 4)),
            multi_account_enabled=to_save["multi_account_enabled"],
        )[mode_raw]
        for k_auto, v_auto in prof_auto.items():
            if k_auto in allowed_keys:
                to_save[k_auto] = v_auto
    to_save["flow_api_workers"] = max(1, min(40, int(to_save.get("flow_api_workers") or 6)))
    to_save["max_inflight_per_account"] = max(1, min(20, int(to_save.get("max_inflight_per_account") or 5)))
    to_save["max_total_inflight"] = max(1, min(120, int(to_save.get("max_total_inflight") or 10)))
    to_save["submit_delay_sec"] = round(max(1.0, min(60.0, float(to_save.get("submit_delay_sec") or 4.5))), 2)
    to_save["global_submit_stagger_sec"] = round(max(0.25, min(10.0, float(to_save.get("global_submit_stagger_sec") or 0.7))), 2)
    to_save["parallel_products"] = max(1, min(16, int(to_save.get("parallel_products") or 4)))
    to_save["upscale_download_workers"] = max(1, min(32, int(to_save.get("upscale_download_workers") or 6)))
    to_save["extension_pool_tabs"] = max(1, min(8, int(to_save.get("extension_pool_tabs") or 4)))
    to_save["auto_hardware_tuning"] = bool(to_save.get("auto_hardware_tuning", False))
    to_save["ffmpeg_render_workers"] = max(1, min(12, int(to_save.get("ffmpeg_render_workers") or 3)))
    to_save["ffmpeg_threads_per_job"] = max(1, min(16, int(to_save.get("ffmpeg_threads_per_job") or 4)))
    to_save["auto_generate_thumbnail"] = bool(to_save.get("auto_generate_thumbnail", True))
    to_save["auto_inject_thumbnail_01s"] = bool(to_save.get("auto_inject_thumbnail_01s", True))
    to_save["thumbnail_duration_sec"] = max(0.05, min(1.0, float(to_save.get("thumbnail_duration_sec") or 0.1)))
    to_save["thumbnail_embed_product_insets"] = bool(to_save.get("thumbnail_embed_product_insets", True))
    to_save["thumbnail_add_text_badge"] = bool(to_save.get("thumbnail_add_text_badge", False))
    to_save["rotate_templates_per_variant"] = bool(to_save.get("rotate_templates_per_variant", True))
    sel_mode = str(to_save.get("thumbnail_selection_mode") or "auto_category").strip().lower()
    if sel_mode not in ("fixed", "auto_category", "custom_category"):
        sel_mode = "auto_category"
    to_save["thumbnail_selection_mode"] = sel_mode
    cat_map = dict(DEFAULT_CATEGORY_THUMBNAIL_MAP)
    if isinstance(to_save.get("category_thumbnail_map"), dict):
        cat_map.update(to_save["category_thumbnail_map"])
    to_save["category_thumbnail_map"] = cat_map

    cam_cfg = dict(DEFAULT_CAMERA_BROLL_SETTINGS)
    if isinstance(to_save.get("camera_broll_settings"), dict):
        for ck, cv in to_save["camera_broll_settings"].items():
            if ck in cam_cfg:
                cam_cfg[ck] = str(cv) if isinstance(cam_cfg[ck], str) else bool(cv)
    to_save["camera_broll_settings"] = cam_cfg

    fx_cfg = dict(DEFAULT_VIDEO_EDIT_FX_SETTINGS)
    if isinstance(to_save.get("video_edit_fx_settings"), dict):
        for fk, fv in to_save["video_edit_fx_settings"].items():
            if fk in fx_cfg:
                fx_cfg[fk] = str(fv) if isinstance(fx_cfg[fk], str) else bool(fv)
    to_save["video_edit_fx_settings"] = fx_cfg

    to_save["subtitle_settings"] = resolve_subtitle_settings(to_save.get("subtitle_settings"))

    _esm_atomic_write_json(ENGINE_SETTINGS_JSON, to_save)

    return {"ok": True, "settings": load_engine_settings()}


_ESM_JSON_LOCK = __import__("threading").RLock()
_THUMB_REG_LOCK = __import__("threading").RLock()


def _esm_atomic_write_json(path: str, payload: object, retries: int = 7) -> bool:
    with _ESM_JSON_LOCK:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        except Exception:
            pass
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp = f"{path}.{os.getpid()}.{__import__('threading').get_ident()}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fw:
                fw.write(text)
            for attempt in range(max(1, int(retries))):
                try:
                    os.replace(tmp, path)
                    return True
                except OSError:
                    time.sleep(0.02 * (attempt + 1))
            with open(path, "w", encoding="utf-8") as fw2:
                fw2.write(text)
            return True
        except Exception:
            return False
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass


def apply_camera_broll_to_project(
    pid: str = "",
    override_settings: dict = None,
    override_fx: dict = None,
) -> dict:
    """Áp dụng cấu hình Góc Máy Uy Tín (Medium-Full 35mm), B-Roll 3 Nhịp & Hiệu ứng Visual FX trong Prompt AI vào 1 hoặc toàn bộ dự án."""
    cfg = load_engine_settings()
    cam_cfg = dict(cfg.get("camera_broll_settings") or DEFAULT_CAMERA_BROLL_SETTINGS)
    fx_cfg = dict(cfg.get("video_edit_fx_settings") or DEFAULT_VIDEO_EDIT_FX_SETTINGS)
    to_update = {}
    if isinstance(override_settings, dict):
        cam_cfg.update(override_settings)
        to_update["camera_broll_settings"] = cam_cfg
    if isinstance(override_fx, dict):
        fx_cfg.update(override_fx)
        to_update["video_edit_fx_settings"] = fx_cfg
    if to_update:
        save_engine_settings(to_update)

    target_pids = [pid] if pid else [
        d for d in sorted(os.listdir(PROJECTS_DIR))
        if os.path.isdir(os.path.join(PROJECTS_DIR, d)) and os.path.isfile(os.path.join(PROJECTS_DIR, d, "prompts.json"))
    ]
    results = []
    total_refs = 0
    total_scenes = 0
    for p in target_pids:
        res = upgrade_project_prompts_with_camera_broll(p, PROJECTS_DIR, cam_cfg, fx_cfg)
        if res.get("ok"):
            results.append(res)
            total_refs += int(res.get("updated_variants") or res.get("updated_refs") or 0)
            total_scenes += int(res.get("updated_scenes") or 0)
    return {
        "ok": True,
        "updated_projects_count": len(results),
        "updated_refs": total_refs,
        "updated_scenes": total_scenes,
        "camera_broll_settings": cam_cfg,
        "video_edit_fx_settings": fx_cfg,
        "details": results,
    }


def rebuild_project_final_videos_with_fx(
    pid: str,
    vkey: str = "",
    override_fx: dict = None,
    override_subtitle: dict = None,
) -> dict:
    """Render lại Video Final (`build_final.py`) với Kho Template Subtitle / Custom Subtitle mới cho dự án `pid`."""
    to_update = {}
    if isinstance(override_fx, dict):
        cur = load_engine_settings()
        fx_cfg = dict(cur.get("video_edit_fx_settings") or DEFAULT_VIDEO_EDIT_FX_SETTINGS)
        fx_cfg.update(override_fx)
        to_update["video_edit_fx_settings"] = fx_cfg
    if isinstance(override_subtitle, dict):
        to_update["subtitle_settings"] = resolve_subtitle_settings(override_subtitle)
    if to_update:
        save_engine_settings(to_update)

    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return {"ok": False, "error": f"Không tìm thấy thư mục dự án: {pid}"}

    build_script = os.path.join(SCRIPTS_DIR, "build_final.py")
    spec_files = (
        [os.path.join(pdir, f"spec_{vkey}.json")]
        if vkey
        else sorted(
            glob.glob(os.path.join(pdir, "spec_*.json")),
            key=lambda x: (0 if os.path.basename(x).startswith("spec_v") else 1, int(re.sub(r"\D", "", os.path.basename(x)) or "0")),
        )
    )
    rebuilt = []
    errors = []
    for sp in spec_files:
        if not os.path.isfile(sp):
            continue
        try:
            sp_data = json.load(open(sp, "r", encoding="utf-8"))
            scenes = sp_data.get("scenes") or []
            if not scenes or not all(os.path.isfile(os.path.join(pdir, s.get("file", ""))) for s in scenes):
                continue
            r = subprocess.run(
                [sys.executable, build_script, sp],
                cwd=pdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            if r.returncode == 0:
                rebuilt.append(os.path.basename(sp))
            else:
                errors.append(f"{os.path.basename(sp)}: {(r.stderr or r.stdout or '')[-200:]}")
        except Exception as e:
            errors.append(f"{os.path.basename(sp)}: {e}")

    return {
        "ok": len(rebuilt) > 0,
        "pid": pid,
        "rebuilt_specs": rebuilt,
        "rebuilt_count": len(rebuilt),
        "errors": errors,
    }


def is_os_pid_running(pid_os: int) -> bool:
    if not pid_os or pid_os <= 0:
        return False
    if sys.platform == "win32":
        try:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid_os))
            if not h:
                return False
            exit_code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(h)
            return bool(ok and exit_code.value == STILL_ACTIVE)
        except Exception:
            return False
    else:
        try:
            os.kill(int(pid_os), 0)
            return True
        except OSError:
            return False


FASHION_STUDIO_PROJECTS_DIR = os.path.join(PIPELINE_DIR, "fashion_motion_projects")


def _get_fashion_project_live_progress(pid: str, fjson_path: str) -> dict:
    try:
        with open(fjson_path, "r", encoding="utf-8") as f:
            fproj = json.load(f)
    except Exception:
        return {"pid": pid, "is_running": False, "logs": []}
    fdir = os.path.dirname(fjson_path)
    f_status = str(fproj.get("status") or "")
    f_scenes = fproj.get("scenes") or []
    active_sc_states = ("preparing", "submitting", "submitted_720p", "upsampling_1080p", "rendering_720p", "rendering_1080p", "retrying_auto", "running")
    is_running = (f_status in ("running_flow", "preparing", "retrying_auto")) or any(
        str(sc.get("status") or "") in active_sc_states for sc in f_scenes
    )
    final_vid_path = fproj.get("final_video_path") or os.path.join(FINAL_VIDEOS_DIR, f"{pid}_final.mp4")
    if not os.path.exists(final_vid_path):
        alt_final = os.path.join(FINAL_VIDEOS_DIR, f"{pid}_final_1080p_60fps.mp4")
        if os.path.exists(alt_final):
            final_vid_path = alt_final
    final_done = os.path.isfile(final_vid_path) and os.path.getsize(final_vid_path) > 50000

    room_char_abs = (fproj.get("char_sheet_2k") or {}).get("path") or (fproj.get("base_char_2k") or {}).get("path") or ""
    done_refs = int(bool(room_char_abs and os.path.isfile(room_char_abs)))
    total_scenes = len(f_scenes)
    done_scenes = 0
    sc_720_cnt = 0
    sc_weight_sum = 0.0
    logs = []
    if fproj.get("status_message"):
        logs.append(f"[{fproj.get('updated_at') or ''}] {fproj.get('status_message')}")
    for idx, sc in enumerate(f_scenes, start=1):
        sc_vid = sc.get("output_video_path") or os.path.join(fdir, sc.get("output_video_file") or f"fashion_scene_s{idx}_1080p.mp4")
        sc_ok = os.path.isfile(sc_vid) and os.path.getsize(sc_vid) > 50000
        sc_st = str(sc.get("status") or "")
        if sc_ok or sc_st == "completed_1080p":
            done_scenes += 1
            sc_weight_sum += 1.0
        elif sc_st in ("submitted_720p", "upsampling_1080p", "rendering_1080p"):
            sc_720_cnt += 1
            sc_weight_sum += 0.72
        elif sc_st in ("submitting", "rendering_720p", "retrying_auto"):
            sc_weight_sum += 0.45
        elif sc_st in ("preparing", "running"):
            sc_weight_sum += 0.22
        det = sc.get("status_detail") or sc.get("last_error") or ""
        if det:
            logs.append(f"• Cảnh {idx} ({sc_st or 'pending'}): {det}")

    total_steps = max(1, 1 + total_scenes + 1)
    if final_done:
        pct = 100
    elif done_scenes > 0 or sc_weight_sum > 0 or done_refs > 0:
        pct = max(12 if is_running else 0, min(96, int(round(((done_refs + max(float(done_scenes), sc_weight_sum)) / total_steps) * 100))))
    else:
        pct = 15 if is_running else 0

    thumb_p = get_variant_thumbnail_path(pid, "nv1_v1") or os.path.join(fdir, "final_video_thumb.jpg")
    has_thumb = bool(thumb_p and os.path.isfile(thumb_p) and os.path.getsize(thumb_p) > 3000)
    step_text = fproj.get("status_message") or (logs[-1] if logs else f"Thời trang #004: {done_scenes}/{total_scenes} cảnh 1080p")
    title = str(fproj.get("title") or pid).strip()
    return {
        "pid": pid,
        "product_name": f"👗 {title}" if not title.startswith("👗") else title,
        "pipeline_kind": "fashion_motion",
        "is_running": is_running,
        "pid_os": 0,
        "recent_activity": is_running,
        "progress_pct": pct,
        "total_variants": 1,
        "done_refs": done_refs,
        "total_scenes": total_scenes,
        "done_scenes": done_scenes,
        "done_thumbs": int(has_thumb),
        "done_finals": int(final_done),
        "inflight_count": 1 if is_running else 0,
        "queued_count": max(0, total_scenes - done_scenes) if is_running else 0,
        "active_tasks": [step_text] if is_running else [],
        "accounts_active": [fproj.get("preferred_profile_name")] if fproj.get("preferred_profile_name") else [],
        "current_step_text": step_text,
        "last_log_line": logs[-1] if logs else step_text,
        "logs": logs,
        "variant_progress": {
            "v1": {
                "char_v": "nv1_v1",
                "ref_done": bool(done_refs),
                "scenes_done": done_scenes,
                "scenes_720p": sc_720_cnt,
                "scenes_total": total_scenes,
                "has_thumbnail": has_thumb,
                "thumbnail_path": thumb_p if has_thumb else "",
                "final_done": final_done,
                "stage": "done" if final_done else ("vid_gen" if is_running else "queued"),
                "label": step_text,
            }
        },
        "updated_at": fproj.get("updated_at") or "",
    }


def _get_cooking_project_live_progress(pid: str, pdir: str) -> dict:
    try:
        from cooking_studio_projection import build_project
        proj = build_project(pdir)
        if not proj:
            return {"pid": pid, "is_running": False, "logs": []}
        live = proj.get("live_status") or {}
        is_running = bool(proj.get("is_running"))
        step_text = live.get("current_step_text") or live.get("current_step") or ""
        logs = proj.get("logs") or ([step_text] if step_text else [])
        return {
            "pid": pid,
            "product_name": proj.get("name") or proj.get("dish") or pid,
            "pipeline_kind": "cooking_storyboard",
            "is_running": is_running,
            "pid_os": 0,
            "recent_activity": is_running,
            "progress_pct": int(proj.get("progress_pct") or 0),
            "total_variants": 1,
            "done_refs": int(live.get("done_refs") or 0),
            "total_scenes": int(live.get("total_scenes") or 3),
            "done_scenes": int(live.get("done_scenes") or 0),
            "done_thumbs": int(live.get("done_thumbnails") or 0),
            "done_finals": int(proj.get("done_products") or 0),
            "inflight_count": 1 if is_running else 0,
            "queued_count": 0,
            "active_tasks": [step_text] if is_running else [],
            "accounts_active": [proj.get("profile")] if proj.get("profile") else [],
            "current_step_text": step_text,
            "last_log_line": step_text,
            "logs": logs,
            "variant_progress": {},
            "updated_at": time.strftime("%H:%M:%S"),
        }
    except Exception:
        return {"pid": pid, "is_running": False, "logs": []}


def _get_transform_project_live_progress(pid: str, pdir: str) -> dict:
    try:
        from pathlib import Path as _Path
        import transform_engine as te
        proj = te.project_view(_Path(pdir))
        if not proj:
            return {"pid": pid, "is_running": False, "logs": []}
        live = proj.get("live_status") or {}
        is_running = bool(proj.get("is_running"))
        raw_status = str(proj.get("status") or "")
        is_queued = bool(is_running and raw_status == "queued")
        step_text = live.get("current_step_text") or proj.get("current_step_text") or ""
        logs = proj.get("logs") or ([step_text] if step_text else [])
        prod0 = (proj.get("products") or [{}])[0]
        return {
            "pid": pid,
            "product_name": proj.get("name") or pid,
            "pipeline_kind": "fashion_transformation",
            "is_running": is_running,
            "pid_os": 0,
            "recent_activity": is_running,
            "progress_pct": int(proj.get("progress_pct") or 0),
            "total_variants": 1,
            "done_refs": int(live.get("done_refs") or 0),
            "total_scenes": int(live.get("total_scenes") or 2),
            "done_scenes": int(live.get("done_scenes") or 0),
            "done_thumbs": int(proj.get("thumbnails_count") or 0),
            "done_finals": int(proj.get("done_products") or 0),
            "inflight_count": 1 if (is_running and not is_queued) else 0,
            "queued_count": 1 if is_queued else 0,
            "active_tasks": [step_text] if is_running else [],
            "accounts_active": [],
            "current_step_text": step_text,
            "last_log_line": step_text,
            "logs": logs,
            "variant_progress": {
                "nv1_v1": {
                    "ref_done": bool(prod0.get("thumbnail_path") or live.get("done_refs")),
                    "scenes_done": int(live.get("done_scenes") or 0),
                    "scenes_total": int(live.get("total_scenes") or 2),
                    "has_thumbnail": bool(prod0.get("has_thumbnail")),
                    "thumbnail_path": str(prod0.get("thumbnail_path") or ""),
                    "final_done": bool(proj.get("done_products")),
                    "stage": prod0.get("status") or ("vid_gen" if is_running else "queued"),
                    "label": step_text,
                }
            },
            "updated_at": time.strftime("%H:%M:%S"),
        }
    except Exception:
        return {"pid": pid, "is_running": False, "logs": []}


def get_project_live_progress(pid: str) -> dict:
    """Đọc trạng thái tiến trình đang chạy thực tế + nhật ký trực tiếp của 1 sản phẩm (hỗ trợ Basic #001-#003, Fashion #004, Cooking #005, Biến hình #006+)."""
    fjson_cand = os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid, "fashion_project.json")
    if os.path.isfile(fjson_cand):
        return _get_fashion_project_live_progress(pid, fjson_cand)

    pdir = os.path.join(PROJECTS_DIR, pid)
    if os.path.isfile(os.path.join(pdir, "transform.json")):
        return _get_transform_project_live_progress(pid, pdir)
    if os.path.isfile(os.path.join(pdir, "cooking_manifest.json")):
        return _get_cooking_project_live_progress(pid, pdir)

    if not os.path.isdir(pdir):
        return {"is_running": False, "logs": []}

    log_path = os.path.join(pdir, "pipeline_run.log")
    mt_log_path = os.path.join(pdir, "pipeline_mt.log")
    status_path = os.path.join(pdir, "pipeline_status.json")
    prompts_path = os.path.join(pdir, "prompts.json")
    flow_state_path = os.path.join(pdir, "flow_state.json")

    logs = []
    log_mtime = 0.0
    chosen_log = log_path
    if os.path.isfile(mt_log_path):
        if not os.path.isfile(log_path) or os.path.getmtime(mt_log_path) > os.path.getmtime(log_path):
            chosen_log = mt_log_path
    if os.path.isfile(chosen_log):
        try:
            log_mtime = os.path.getmtime(chosen_log)
            with open(chosen_log, "r", encoding="utf-8", errors="replace") as _f_lg:
                raw_lines = _f_lg.read().splitlines()
            logs = [ln for ln in raw_lines if ln.strip()][-80:]
        except Exception:
            pass

    scene_errors = {}
    if os.path.isfile(flow_state_path):
        try:
            with open(flow_state_path, "r", encoding="utf-8") as _f_fs:
                fs_data = json.load(_f_fs)
            if isinstance(fs_data.get("scene_errors"), dict):
                scene_errors = fs_data["scene_errors"]
        except Exception:
            pass

    status_data = {}
    if os.path.isfile(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as _f_st:
                status_data = json.load(_f_st)
        except Exception:
            pass

    # Đếm tiến độ thực tế trên ổ đĩa
    total_variants = 0
    done_refs = 0
    total_scenes = 0
    done_scenes = 0
    done_thumbs = 0
    done_finals = 0
    variant_progress = {}

    if os.path.isfile(prompts_path):
        try:
            with open(prompts_path, "r", encoding="utf-8") as _f_pr:
                pdata = json.load(_f_pr)
            videos = pdata.get("videos", {})
            total_variants = len(videos)
            for vk, vcfg in videos.items():
                ck = vcfg.get("character", "nv1")
                ref_rel = vcfg.get("ref_image", f"{vk}-refimg.jpg")
                ref_ok = os.path.isfile(os.path.join(pdir, ref_rel)) and os.path.getsize(os.path.join(pdir, ref_rel)) > 10000
                if ref_ok:
                    done_refs += 1

                scs = vcfg.get("scenes", [])
                sc_done_cnt = 0
                sc_720_cnt = 0
                for sc in scs:
                    total_scenes += 1
                    s_abs = os.path.join(pdir, sc["file"])
                    if os.path.isfile(s_abs) and os.path.getsize(s_abs) > 50000:
                        done_scenes += 1
                        sc_done_cnt += 1
                    elif os.path.isfile(s_abs + ".720p.tmp"):
                        sc_720_cnt += 1

                # Check thumbnail
                char_v = vk if re.match(r"^nv\d+_v\d+$", vk.lower()) else (
                    {"v1": "nv1_v1", "v3": "nv1_v2", "v5": "nv1_v3", "v2": "nv2_v1", "v4": "nv2_v2", "v6": "nv2_v3"}.get(vk.lower(), f"{ck}_{vk}")
                )
                thumb_p = get_variant_thumbnail_path(pid, char_v)
                has_thumb = bool(thumb_p and os.path.isfile(thumb_p))
                if has_thumb:
                    done_thumbs += 1

                final_fname = f"{pid}_{char_v}.mp4"
                final_ok = os.path.isfile(os.path.join(FINAL_VIDEOS_DIR, final_fname)) and os.path.getsize(os.path.join(FINAL_VIDEOS_DIR, final_fname)) > 50000
                if final_ok:
                    done_finals += 1

                if final_ok:
                    v_stage = "done"
                    v_label = "✓ Hoàn tất Video Final"
                elif sc_done_cnt == len(scs) and len(scs) > 0:
                    v_stage = "assembling"
                    v_label = "🎞️ Đang ghép FFmpeg 60FPS..."
                elif sc_done_cnt > 0 or sc_720_cnt > 0:
                    v_stage = "vid_gen"
                    v_label = f"🎬 Xong {sc_done_cnt}/{len(scs)} cảnh 1080p" + (f" ({sc_720_cnt} đang upsample)" if sc_720_cnt else "")
                elif ref_ok:
                    v_stage = "vid_gen"
                    v_label = f"🎬 Đã có Ảnh Ref 2K • Đang dựng {len(scs)} cảnh..."
                else:
                    v_stage = "img_gen"
                    v_label = "🎨 Chờ / Đang tạo Ảnh Ref 2K..."

                variant_progress[vk] = {
                    "char_v": char_v,
                    "ref_done": ref_ok,
                    "scenes_done": sc_done_cnt,
                    "scenes_720p": sc_720_cnt,
                    "scenes_total": len(scs),
                    "has_thumbnail": has_thumb,
                    "thumbnail_path": thumb_p or "",
                    "final_done": final_ok,
                    "stage": v_stage,
                    "label": v_label,
                }
        except Exception:
            pass

    pid_os = int(status_data.get("pid_os") or 0)
    alive = is_os_pid_running(pid_os)
    recent_log = (time.time() - log_mtime) < 35.0 if log_mtime > 0 else False
    is_running = bool((status_data.get("is_running") and alive) or (alive and done_finals < total_variants))
    if not alive and status_data.get("is_running"):
        is_running = False

    # Tính % tiến độ tổng thể (Ref 20% + Scenes 65% + Final 15%)
    pct = 0
    if total_variants > 0:
        r_ratio = done_refs / float(total_variants)
        s_ratio = done_scenes / float(max(1, total_scenes))
        f_ratio = done_finals / float(total_variants)
        pct = int(round((r_ratio * 20.0) + (s_ratio * 65.0) + (f_ratio * 15.0)))
        if done_finals >= total_variants:
            pct = 100

    last_log_line = logs[-1] if logs else ""
    step_text = status_data.get("current_step_text") or last_log_line or (
        f"Đã hoàn tất {done_finals}/{total_variants} Video Final • {done_scenes}/{total_scenes} cảnh 1080p • {done_refs}/{total_variants} Ảnh Ref 2K"
    )

    return {
        "pid": pid,
        "is_running": is_running,
        "pid_os": pid_os if alive else 0,
        "recent_activity": recent_log,
        "progress_pct": pct,
        "total_variants": total_variants,
        "done_refs": done_refs,
        "total_scenes": total_scenes,
        "done_scenes": done_scenes,
        "done_thumbs": done_thumbs,
        "done_finals": done_finals,
        "inflight_count": int(status_data.get("inflight_count") or 0) if is_running else 0,
        "queued_count": int(status_data.get("queued_count") or 0) if is_running else 0,
        "active_tasks": (status_data.get("active_tasks") or []) if is_running else [],
        "accounts_active": status_data.get("accounts_active") or [],
        "current_step_text": step_text,
        "last_log_line": last_log_line,
        "logs": logs,
        "scene_errors": scene_errors,
        "failed_scenes_count": len(scene_errors),
        "variant_progress": variant_progress,
        "updated_at": status_data.get("updated_at") or (time.strftime("%H:%M:%S", time.localtime(log_mtime)) if log_mtime else ""),
    }


def list_all_running_pipelines() -> list:
    """Trả về danh sách tất cả các dự án đang chạy ngầm hoặc đang dở dang tiến trình (Basic, Thời trang #004, Nấu ăn #005)."""
    running = []
    seen_pids = set()

    if os.path.isdir(FASHION_STUDIO_PROJECTS_DIR):
        for entry in os.listdir(FASHION_STUDIO_PROJECTS_DIR):
            fjson_p = os.path.join(FASHION_STUDIO_PROJECTS_DIR, entry, "fashion_project.json")
            if not os.path.isfile(fjson_p):
                continue
            st_f = _get_fashion_project_live_progress(entry, fjson_p)
            if st_f.get("is_running"):
                running.append(st_f)
                seen_pids.add(entry)

    if os.path.isdir(PROJECTS_DIR):
        for entry in os.listdir(PROJECTS_DIR):
            if entry in seen_pids:
                continue
            pdir = os.path.join(PROJECTS_DIR, entry)
            if not os.path.isdir(pdir):
                continue
            if os.path.isfile(os.path.join(pdir, "transform.json")):
                st_t = _get_transform_project_live_progress(entry, pdir)
                if st_t.get("is_running"):
                    running.append(st_t)
                    seen_pids.add(entry)
                continue
            if os.path.isfile(os.path.join(pdir, "cooking_manifest.json")):
                st_c = _get_cooking_project_live_progress(entry, pdir)
                if st_c.get("is_running"):
                    running.append(st_c)
                    seen_pids.add(entry)
                continue
            has_log = os.path.isfile(os.path.join(pdir, "pipeline_run.log"))
            has_status = os.path.isfile(os.path.join(pdir, "pipeline_status.json"))
            if not has_status and not has_log:
                continue
            st = get_project_live_progress(entry)
            is_incomplete_with_log = (
                has_log
                and st.get("total_variants", 0) > 0
                and st.get("done_finals", 0) < st.get("total_variants", 0)
                and (st.get("done_refs", 0) > 0 or st.get("done_scenes", 0) > 0)
            )
            if st.get("is_running") or st.get("recent_activity") or is_incomplete_with_log:
                p_json = os.path.join(pdir, "prompts.json")
                pname = entry
                if os.path.isfile(p_json):
                    try:
                        with open(p_json, "r", encoding="utf-8") as _f_pj:
                            pname = json.load(_f_pj).get("product_name") or entry
                    except Exception:
                        pass
                st["product_name"] = pname
                running.append(st)
                seen_pids.add(entry)

    running.sort(key=lambda x: (0 if x.get("is_running") else 1, -x.get("progress_pct", 0)))
    return running


def _mark_cancelled_batch_pid(pid: str) -> None:
    cancel_file = os.path.join(WS_DIR, "flow_final_pipeline", "cancelled_batch_pids.json")
    os.makedirs(os.path.dirname(cancel_file), exist_ok=True)
    with _ESM_JSON_LOCK:
        cur = []
        if os.path.isfile(cancel_file):
            try:
                with open(cancel_file, "r", encoding="utf-8") as _f_cf:
                    cur = json.load(_f_cf)
                if not isinstance(cur, list):
                    cur = []
            except Exception:
                cur = []
        if pid not in cur:
            cur.append(pid)
        _esm_atomic_write_json(cancel_file, cur[-200:])


def stop_running_pipeline(pid: str) -> dict:
    """Dừng tiến trình đang chạy của 1 sản phẩm (hỗ trợ Basic, Bulk chia sẻ PID, Custom proj_*, Thời trang #004, Nấu ăn #005, Biến hình #006)."""
    fjson_cand = os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid, "fashion_project.json")
    if os.path.isfile(fjson_cand):
        try:
            try:
                import fashion_motion_control_engine as _fmce_stop
                if hasattr(_fmce_stop, "request_stop_fashion_project"):
                    _fmce_stop.request_stop_fashion_project(pid)
            except Exception:
                pass
            with open(fjson_cand, "r", encoding="utf-8") as f:
                fproj = json.load(f)
            fproj["status"] = "stopped"
            fproj["status_message"] = "⏹️ Đã tạm dừng tiến trình tạo video thời trang theo yêu cầu người dùng."
            fproj["updated_at"] = time.strftime("%H:%M:%S")
            for sc in fproj.get("scenes") or []:
                if sc.get("status") not in ("completed_1080p", "done"):
                    sc["status"] = "stopped"
                    sc["status_detail"] = "⏹️ Đã tạm dừng"
            _esm_atomic_write_json(fjson_cand, fproj)
            return {"ok": True, "pid": pid, "pid_os": 0, "stopped": True}
        except Exception as exc:
            return {"ok": False, "pid": pid, "error": str(exc)}

    pdir = os.path.join(PROJECTS_DIR, pid)
    if os.path.isfile(os.path.join(pdir, "transform.json")):
        try:
            import transform_engine as te
            res_t = te.stop_job(pid)
            return {"ok": bool(res_t.get("ok")), "pid": pid, "pid_os": 0, "stopped": True, **res_t}
        except Exception as exc:
            return {"ok": False, "pid": pid, "error": str(exc)}

    if os.path.isfile(os.path.join(pdir, "cooking_manifest.json")):
        try:
            import cooking_storyboard_engine as cooking
            cooking.stop_stage(pid)
            return {"ok": True, "pid": pid, "pid_os": 0, "stopped": True}
        except Exception as exc:
            return {"ok": False, "pid": pid, "error": str(exc)}

    # Nếu là dự án Custom in-process (veo_skill_cli.run_project_batch)
    in_proc_stopped = False
    try:
        import veo_skill_cli as _vsc_stop
        if hasattr(_vsc_stop, "request_stop_project") and _vsc_stop.request_stop_project(pid):
            in_proc_stopped = True
    except Exception:
        pass

    _mark_cancelled_batch_pid(pid)

    status_path = os.path.join(pdir, "pipeline_status.json")
    killed = in_proc_stopped
    pid_os = 0
    if os.path.isfile(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as _f_stp:
                st = json.load(_f_stp)
            pid_os = int(st.get("pid_os") or 0)
            runner_mode = str(st.get("runner_mode") or "")
            if pid_os > 0 and pid_os != os.getpid() and runner_mode != "in_process_batch" and is_os_pid_running(pid_os):
                # Kiểm tra xem có sản phẩm anh em nào khác đang chạy chung tiến trình batch `pid_os` không
                sibling_running = False
                if os.path.isdir(PROJECTS_DIR):
                    for other_entry in os.listdir(PROJECTS_DIR):
                        if other_entry == pid:
                            continue
                        other_st_p = os.path.join(PROJECTS_DIR, other_entry, "pipeline_status.json")
                        if not os.path.isfile(other_st_p):
                            continue
                        try:
                            with open(other_st_p, "r", encoding="utf-8") as _f_ost:
                                ost = json.load(_f_ost)
                            if int(ost.get("pid_os") or 0) == pid_os and bool(ost.get("is_running")):
                                sibling_running = True
                                break
                        except Exception:
                            pass
                if not sibling_running:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid_os)], capture_output=True)
                killed = True
            st["is_running"] = False
            st["current_step_text"] = "⏹️ Đã tạm dừng theo yêu cầu người dùng."
            _esm_atomic_write_json(status_path, st)
        except Exception:
            pass
    return {"ok": True, "pid": pid, "pid_os": pid_os, "stopped": killed}


# ═══════════════════════════════════════════════════════════════════════════════
# HỆ THỐNG TẠO ẢNH THUMBNAIL CHUYÊN NGHIỆP & GHÉP 0.1 GIÂY ĐẦU VIDEO FINAL
# ═══════════════════════════════════════════════════════════════════════════════

def get_variant_thumbnail_path(pid: str, char_v: str) -> str:
    """Tìm đường dẫn file ảnh Thumbnail của 1 video ({pid}_{char_v}_thumb.jpg)."""
    pdir_thumbs = os.path.join(PROJECTS_DIR, pid, "thumbnails")
    for cand in (
        os.path.join(THUMBS_ROOT_DIR, f"{pid}_{char_v}_thumb.jpg"),
        os.path.join(pdir_thumbs, f"{pid}_{char_v}_thumb.jpg"),
    ):
        if os.path.isfile(cand) and os.path.getsize(cand) > 5000:
            return cand
    return ""


def build_thumbnail_prompt_for_variant(
    pid: str,
    vkey: str = "v1",
    custom_master_prompt: str = "",
    preset_id: str = "",
    custom_product_info: str = "",
    subject_mode: str = "auto",
    headline: str = "",
) -> dict:
    """
    Sinh Prompt & gom đủ 3 nguồn dữ liệu Reference để AI Render Ảnh Thumbnail chuyên nghiệp:
      1. Ref Image 1 (`char_holding_prod_img`): Ảnh 2K nhân vật cầm sản phẩm của đúng kịch bản (`{vkey}-refimg.jpg`).
      2. Ref Image 2 (`prod_img_path` / `prod_img_paths`): Bộ ảnh sản phẩm gốc (`product_images/prod_1.jpg`, `prod_2.jpg`).
      3. Ref 3 (`product_info`): Thông tin chi tiết sản phẩm (Tên, Giá, Điểm nổi bật USP, Mô tả & Hook kịch bản).
    """
    cfg = load_engine_settings()
    pdir = os.path.join(PROJECTS_DIR, pid)
    fashion_dir = os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid)
    if not os.path.isfile(os.path.join(fashion_dir, "fashion_project.json")):
        alt_fdir = os.path.join(WS_DIR, "fashion_motion_projects", pid)
        if os.path.isfile(os.path.join(alt_fdir, "fashion_project.json")):
            fashion_dir = alt_fdir
        elif os.path.isfile(os.path.join(pdir, "fashion_project.json")):
            fashion_dir = pdir
    prompts_path = os.path.join(pdir, "prompts.json")
    proj_json_path = os.path.join(pdir, "project.json")
    transform_json_path = os.path.join(pdir, "transform.json")
    cooking_json_path = os.path.join(pdir, "cooking_manifest.json")
    fashion_json_path = os.path.join(fashion_dir, "fashion_project.json")
    info_path = os.path.join(pdir, "product_images", "info.json")
    if not os.path.isfile(info_path):
        alt_info = os.path.join(pdir, "info.json")
        if os.path.isfile(alt_info):
            info_path = alt_info
    def _read_json_dict(path: str) -> dict:
        if not path or not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    pdata = _read_json_dict(prompts_path)
    idata = _read_json_dict(info_path)
    proj_data = _read_json_dict(proj_json_path)
    tdata = _read_json_dict(transform_json_path)
    cdata = _read_json_dict(cooking_json_path)
    fdata = _read_json_dict(fashion_json_path)

    def _resolve_ws_file(raw_p: str) -> str:
        s = str(raw_p or "").strip()
        if not s:
            return ""
        if os.path.isfile(s):
            return s
        for base in (pdir, fashion_dir, WS_DIR):
            cand = os.path.join(base, s)
            if os.path.isfile(cand):
                return cand
        return ""

    proj_prods = proj_data.get("products") or []
    prod_obj = next(
        (
            p for p in proj_prods
            if str(p.get("vkey") or "").lower() == vkey.lower()
            or str(p.get("char_v_code") or "").lower() == vkey.lower()
        ),
        proj_prods[0] if proj_prods else {},
    )
    is_transform = bool(tdata) or proj_data.get("pipeline_kind") == "fashion_transformation"
    is_cooking = bool(cdata) or (proj_data.get("pipeline_kind") == "cooking_storyboard") or (prod_obj.get("pipeline_kind") == "cooking_storyboard")
    is_fashion = bool(fdata) or is_transform or bool(proj_data.get("is_fashion_motion_project"))

    t_preset_meta = {}
    if tdata:
        try:
            from transform_engine import PRESETS as _TRANSFORM_PRESETS
            t_preset_meta = _TRANSFORM_PRESETS.get(tdata.get("preset") or "", {}) or {}
        except Exception:
            t_preset_meta = {}

    prod_name = (
        pdata.get("product_name")
        or idata.get("name")
        or idata.get("title")
        or cdata.get("dish")
        or proj_data.get("dish")
        or fdata.get("title")
        or (f"Biến hình · {t_preset_meta['title']}" if t_preset_meta.get("title") else "")
        or proj_data.get("full_product_name")
        or proj_data.get("name")
        or f"Sản phẩm {pid}"
    )
    price_str = str(idata.get("price") or pdata.get("price") or (proj_data.get("price") if not is_fashion else "") or "").strip()
    cat_str = str(
        idata.get("category")
        or pdata.get("category")
        or ("food" if is_cooking else ("quan_ao_nu" if is_fashion else ""))
        or ""
    ).strip()
    vcfg = (pdata.get("videos") or {}).get(vkey) or {}
    char_key = vcfg.get("character") or ("nv2" if vkey in ("v2", "v4", "v6") else "nv1")
    hook_title = (
        headline.strip()
        or vcfg.get("hook_title")
        or prod_obj.get("hook_label")
        or t_preset_meta.get("title")
        or prod_name
    )
    if "—" in hook_title:
        hook_title = hook_title.split("—")[-1].strip()
    elif ":" in hook_title:
        hook_title = hook_title.split(":")[-1].strip()
    style_desc = vcfg.get("style") or (
        "Warm cozy overhead kitchen counter lighting, rich food photography"
        if is_cooking
        else ("Fashion lookbook lighting, natural flattering editorial portrait" if is_fashion else "Modern commercial studio with soft warm rim lighting")
    )

    if is_cooking or vkey.lower() in ("pov", "pov_v1"):
        char_v = "pov"
    elif is_transform or (is_fashion and not pdata):
        char_v = str(prod_obj.get("char_v_code") or "nv1_v1").lower()
    elif not pdata and prod_obj.get("char_v_code"):
        char_v = str(prod_obj["char_v_code"]).lower()
    else:
        char_v = vkey if re.match(r"^nv\d+_v\d+$", vkey.lower()) else (
            {"v1": "nv1_v1", "v3": "nv1_v2", "v5": "nv1_v3", "v2": "nv2_v1", "v4": "nv2_v2", "v6": "nv2_v3"}.get(vkey.lower(), f"{char_key}_{vkey}")
        )

    # 1. Tổng hợp Thông tin Sản phẩm & USP (`product_info`) từ info.json + prompts.json + project.json
    prod_info_str = (custom_product_info or "").strip()
    if not prod_info_str:
        info_parts = [f"Sản phẩm: {prod_name}"]
        if price_str:
            info_parts.append(f"Giá bán: {price_str}")
        if cat_str:
            info_parts.append(f"Ngành hàng: {cat_str}")
        if t_preset_meta.get("summary"):
            info_parts.append(f"Kịch bản: {t_preset_meta['summary']}")
        highlights = idata.get("highlights") or idata.get("features") or idata.get("usp") or []
        if isinstance(highlights, list) and highlights:
            info_parts.append("Đặc điểm nổi bật: " + "; ".join(str(x).strip() for x in highlights[:4] if str(x).strip()))
        elif isinstance(highlights, str) and highlights.strip():
            info_parts.append(f"Đặc điểm nổi bật: {highlights.strip()[:220]}")
        raw_desc = str(idata.get("short_description") or idata.get("description") or pdata.get("product_description") or prod_obj.get("product_info") or "").strip()
        if raw_desc:
            clean_desc = re.sub(r"\s+", " ", raw_desc)[:240]
            info_parts.append(f"Mô tả: {clean_desc}")
        # Lấy câu mở đầu Cảnh 1 để nắm bắt USP cốt lõi của kịch bản
        scenes_list = vcfg.get("scenes") or prod_obj.get("scenes") or tdata.get("scenes") or fdata.get("scenes") or []
        if scenes_list and isinstance(scenes_list[0], dict):
            sc1_d = str(scenes_list[0].get("dialogue_vn") or "")
            sc1_p = str(scenes_list[0].get("prompt") or scenes_list[0].get("video_prompt") or "")
            if sc1_d:
                info_parts.append(f"Thông điệp kịch bản: \"{sc1_d[:160]}\"")
            else:
                m_q = re.findall(r'"([^"]{15,160})"', sc1_p)
                if m_q:
                    info_parts.append(f"Thông điệp Hook kịch bản: \"{m_q[0]}\"")
        prod_info_str = " | ".join(info_parts)

    # Giải quyết Template Thumbnail theo cấu hình (fixed / auto_category / custom_category)
    resolved_tpl = resolve_thumbnail_template(
        vkey=vkey,
        preset_id=preset_id,
        settings=cfg,
        product_name=prod_name,
        product_info=prod_info_str,
        category_hint=cat_str,
    )
    detected_cat = detect_product_thumbnail_category(prod_name, prod_info_str, cat_str)

    master_tpl = (custom_master_prompt or "").strip()
    if not master_tpl:
        master_tpl = resolved_tpl.get("master_prompt") or cfg.get("thumbnail_master_prompt") or THUMBNAIL_PRESETS[0]["master_prompt"]

    # 2. Đọc mô tả ngoại hình nhân vật & ảnh Ref nhân vật gốc
    char_desc = "Use only the supplied character identity; do not invent a person."
    vc_json = os.path.join(PIPELINE_DIR, "voices_and_characters.json")
    char_ref_path = os.path.join(CHARS_DIR, f"{char_key}_ref.jpg")

    char_uuid = vcfg.get("character_id") or prod_obj.get("character_id") or ""
    if os.path.isfile(vc_json):
        try:
            with open(vc_json, "r", encoding="utf-8") as vcf:
                vc_data = json.load(vcf)
            c_obj = (vc_data.get("characters") or {}).get(char_key) or {}
            if c_obj.get("appearance_en"):
                char_desc = c_obj["appearance_en"]
            ref_rel_c = c_obj.get("ref_image_file") or c_obj.get("ref_image_path") or ""
            for ref_cand in (
                os.path.join(PIPELINE_DIR, ref_rel_c) if ref_rel_c else "",
                os.path.join(WS_DIR, ref_rel_c) if ref_rel_c else "",
                os.path.join(CHARS_DIR, f"{char_key}_ref.png"),
                os.path.join(CHARS_DIR, f"{char_key}_ref.jpg"),
            ):
                if ref_cand and os.path.isfile(ref_cand):
                    char_ref_path = ref_cand
                    break
            if not char_uuid and c_obj.get("id"):
                char_uuid = c_obj["id"]
        except Exception:
            pass

    # 3. Tìm Ảnh Ref 1: Ảnh nhân vật cầm/mặc sản phẩm (`char_holding_prod_img`) của kịch bản này
    ref_rel = vcfg.get("ref_image") or f"{vkey}-refimg.jpg"
    holding_candidates = [
        os.path.join(pdir, ref_rel),
        os.path.join(pdir, f"{vkey}-refimg.jpg"),
        os.path.join(pdir, f"{char_v}-refimg.jpg"),
        os.path.join(pdir, "refs", f"{vkey}-refimg.jpg"),
        os.path.join(pdir, "refs", f"{char_v}-refimg.jpg"),
    ]
    if is_transform or tdata:
        for tname in ("reveal_2k.jpg", "before_2k.jpg", "character_input.jpg"):
            holding_candidates.append(os.path.join(pdir, tname))
    if is_fashion:
        for fc in (
            prod_obj.get("character_sheet_path"),
            (fdata.get("char_sheet_2k") or {}).get("path"),
            (fdata.get("base_char_2k") or {}).get("path"),
            fdata.get("character_sheet_path"),
            fdata.get("character_image_path"),
            prod_obj.get("product_image_path"),
            fdata.get("product_image_path"),
        ):
            rp = _resolve_ws_file(fc or "")
            if rp:
                holding_candidates.append(rp)
        for fsc in (fdata.get("scenes") or []):
            rp = _resolve_ws_file((fsc or {}).get("start_frame_path") or "")
            if rp:
                holding_candidates.append(rp)
    # Nếu biến thể hiện tại chưa có refimg thì tìm refimg của cùng nhân vật trong dự án
    for vk_other, vcfg_other in (pdata.get("videos") or {}).items():
        if vcfg.get("character") and vcfg_other.get("character") == char_key:
            holding_candidates.append(os.path.join(pdir, f"{vk_other}-refimg.jpg"))
    if vcfg.get("character"):
        holding_candidates.append(char_ref_path)
    char_holding_prod_img = next(
        (p for p in holding_candidates if p and os.path.isfile(p) and os.path.getsize(p) > 5000),
        "",
    )

    if is_cooking and subject_mode != "character":
        effective_mode = "pov"
    elif is_fashion and subject_mode == "auto":
        effective_mode = "character" if char_holding_prod_img else "pov"
    else:
        effective_mode = subject_mode if subject_mode in ("pov", "character") else resolved_tpl.get("subject_mode", "auto")
        if effective_mode == "auto":
            effective_mode = "character" if (vcfg.get("character") or char_holding_prod_img) else "pov"

    # 4. Tìm Ảnh Ref 2: Bộ ảnh sản phẩm gốc / Storyboard / Outfit (`prod_img_path` & `prod_img_paths`)
    primary_refs = vcfg.get("primary_product_refs") or pdata.get("primary_product_refs") or ["prod_1.jpg", "prod_2.jpg", "prod_3.jpg"]
    prod_img_paths = []
    for pr_name in primary_refs:
        cand_p = os.path.join(pdir, "product_images", pr_name)
        if os.path.isfile(cand_p) and os.path.getsize(cand_p) > 3000 and cand_p not in prod_img_paths:
            prod_img_paths.append(cand_p)
    for jp in sorted(glob.glob(os.path.join(pdir, "product_images", "prod_*.jpg")))[:6]:
        if os.path.isfile(jp) and os.path.getsize(jp) > 3000 and jp not in prod_img_paths:
            prod_img_paths.append(jp)
    extra_proj_imgs = (
        ([os.path.join(pdir, "product_2k.jpg"), os.path.join(pdir, "product_input.jpg")] if (is_transform or tdata) else [])
        + [o.get("path") for o in (fdata.get("outfits") or []) if isinstance(o, dict)]
        + ([fdata.get("product_image_path")] if fdata.get("product_image_path") else [])
        + ([fdata.get("outfit_image_path")] if fdata.get("outfit_image_path") else [])
        + ([cdata.get("dish_photo_path")] if cdata.get("dish_photo_path") else [])
        + [(sc or {}).get("first_frame_path") for sc in (cdata.get("scenes") or []) if isinstance(sc, dict) and sc.get("first_frame_path")]
        + [os.path.join(pdir, c.get("storyboard_file")) for c in (cdata.get("clips") or []) if isinstance(c, dict) and c.get("storyboard_file")]
        + sorted(glob.glob(os.path.join(pdir, "storyboard_*.jpg")))
        + sorted(glob.glob(os.path.join(pdir, "storyboard_*.png")))
        + sorted(glob.glob(os.path.join(pdir, "qa_s*.jpg")))
        + list(prod_obj.get("slide_overlay_image_paths") or [])
        + list(prod_obj.get("all_product_image_paths") or [])
        + list(proj_data.get("all_product_image_paths") or [])
        + ([proj_data.get("primary_product_image_path")] if proj_data.get("primary_product_image_path") else [])
    )
    for ep in extra_proj_imgs:
        rep = _resolve_ws_file(ep or "")
        if rep and os.path.getsize(rep) > 3000 and rep not in prod_img_paths:
            prod_img_paths.append(rep)
            if len(prod_img_paths) >= 6:
                break
    prod_img_path = prod_img_paths[0] if prod_img_paths else ""

    # Danh sách tổng hợp các ảnh Reference truyền vào AI Renderer (Ảnh NV cầm SP + Ảnh SP gốc)
    reference_images = []
    if effective_mode == "pov":
        char_holding_prod_img = ""
    if char_holding_prod_img and os.path.isfile(char_holding_prod_img):
        reference_images.append(char_holding_prod_img)
    for pp in prod_img_paths[:2]:
        if pp and os.path.isfile(pp) and pp not in reference_images:
            reference_images.append(pp)

    # 5. Kết xuất Master Prompt hoàn chỉnh cho AI Image Generator
    final_prompt = (
        master_tpl
        .replace("{product_name}", prod_name)
        .replace("{product_info}", prod_info_str)
        .replace("{character_desc}", char_desc)
        .replace("{hook_text}", hook_title)
        .replace("{price}", price_str)
        .replace("{style}", style_desc)
    )
    # Frame provides scene identity, not a finished thumbnail to overlay.
    scene_ref = ''
    vid_candidates = [
        os.path.join(FINAL_VIDEOS_DIR, f'{pid}_{char_v}.mp4'),
        str(prod_obj.get("final_video_path") or ""),
        _resolve_ws_file(str(cdata.get("final_video_path") or "")),
        _resolve_ws_file(str(fdata.get("final_video_path") or "")),
        os.path.join(FINAL_VIDEOS_DIR, f'{pid}_final.mp4'),
        os.path.join(pdir, "video_final.mp4"),
    ]
    video_path = next((vp for vp in vid_candidates if vp and os.path.isfile(vp) and os.path.getsize(vp) > 10000), "")
    if video_path:
        scene_ref = os.path.join(pdir, 'thumbnails', f'{char_v}_scene_ref.jpg')
        os.makedirs(os.path.dirname(scene_ref), exist_ok=True)
        frame = subprocess.run(['ffmpeg','-y','-ss','0.5','-i',video_path,'-frames:v','1',scene_ref],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if frame.returncode != 0:
            scene_ref = ''
        elif scene_ref not in reference_images:
            reference_images.append(scene_ref)
    final_prompt += '\nREFERENCE ROLES: ' + json.dumps({
        'character_and_scene': char_holding_prod_img, 'exact_products': prod_img_paths[:2],
        'video_environment': scene_ref}, ensure_ascii=False)
    if not reference_images:
        raise ValueError('Chưa có ảnh tham chiếu nhân vật, sản phẩm hoặc video. Thêm ảnh trước khi tạo thumbnail AI.')
    if subject_mode == 'character' and not char_holding_prod_img:
        raise ValueError('Style có nhân vật cần ảnh nhân vật thật của dự án. Chọn POV hoặc thêm ảnh nhân vật.')
    if effective_mode == 'pov':
        final_prompt += '\nNo presenter or human face. Focus on the supplied product or dish and video setting.'

    return {
        "pid": pid,
        "vkey": vkey,
        "char_key": char_key,
        "char_v": char_v,
        "char_uuid": char_uuid,
        "char_ref_path": char_ref_path,
        "char_holding_prod_img": char_holding_prod_img,
        "prod_img_path": prod_img_path,
        "prod_img_paths": prod_img_paths,
        "reference_images": reference_images,
        "scene_ref_path": scene_ref,
        "final_video_path": video_path,
        "subject_mode": effective_mode,
        "product_name": prod_name,
        "product_info": prod_info_str,
        "price": price_str,
        "hook_title": hook_title,
        "character_desc": char_desc,
        "style": style_desc,
        "template_id": resolved_tpl["id"],
        "template_name": resolved_tpl["name"],
        "layout_type": resolved_tpl.get("layout_type", "grid_3_bottom"),
        "detected_category": detected_cat,
        "prompt": final_prompt,
        "flow_project_id": vcfg.get("project_id") or prod_obj.get("flow_project_id") or cdata.get("flow_project_id") or fdata.get("flow_project_id") or get_default_flow_project_id(),
    }


def _apply_pro_thumbnail_badge_overlay(
    img_path: str,
    hook_title: str,
    product_name: str,
    price_str: str = "",
    prod_img_path: str = "",
):
    """Tạo bố cục Poster Thumbnail 1080x1920 sắc nét chuẩn TikTok Shop (viền sáng + Hook Badge + Giá)."""
    with Image.open(img_path) as im:
        im_rgb = im.convert("RGB")
        # Resize/crop chuẩn 1080x1920
        target_w, target_h = 1080, 1920
        src_w, src_h = im_rgb.size
        scale = max(target_w / float(src_w), target_h / float(src_h))
        nw, nh = int(round(src_w * scale)), int(round(src_h * scale))
        im_resized = im_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - target_w) // 2
        top = (nh - target_h) // 2
        canvas = im_resized.crop((left, top, left + target_w, top + target_h)).convert("RGBA")

    # Tăng nhẹ độ tương phản & độ nét cho ảnh bìa bắt mắt
    canvas_rgb = canvas.convert("RGB")
    canvas_rgb = ImageEnhance.Contrast(canvas_rgb).enhance(1.06)
    canvas_rgb = ImageEnhance.Color(canvas_rgb).enhance(1.08)
    canvas = canvas_rgb.convert("RGBA")

    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Đổ bóng gradient nhẹ phía trên và phía dưới để nổi bật chữ
    for y in range(280):
        alpha = int(175 * (1.0 - (y / 280.0)) ** 1.5)
        draw.line([(0, y), (1080, y)], fill=(8, 12, 24, alpha))
    for y in range(1580, 1920):
        ratio = (y - 1580) / 340.0
        alpha = int(190 * (ratio ** 1.4))
        draw.line([(0, y), (1080, y)], fill=(8, 12, 24, alpha))

    font_paths = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
    ]
    font_file = next((fp for fp in font_paths if os.path.isfile(fp)), None)
    try:
        f_hook = ImageFont.truetype(font_file, 58) if font_file else ImageFont.load_default()
        f_sub = ImageFont.truetype(font_file, 36) if font_file else ImageFont.load_default()
        f_badge = ImageFont.truetype(font_file, 34) if font_file else ImageFont.load_default()
    except Exception:
        f_hook = ImageFont.load_default()
        f_sub = ImageFont.load_default()
        f_badge = ImageFont.load_default()

    # Khung pill Hook nổi bật ở trên cùng
    hook_clean = (hook_title or "CHÍNH HÃNG GIÁ XƯỞNG").upper().strip()
    if len(hook_clean) > 28:
        hook_clean = hook_clean[:26].rstrip() + "..."
    draw.rounded_rectangle([54, 58, 1026, 178], radius=26, fill=(220, 38, 38, 235), outline=(253, 224, 71, 255), width=5)
    # Canh giữa chữ Hook
    bbox = draw.textbbox((0, 0), hook_clean, font=f_hook)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = max(70, (1080 - tw) // 2)
    ty = 58 + (120 - th) // 2 - 6
    draw.text((tx + 3, ty + 3), hook_clean, font=f_hook, fill=(0, 0, 0, 220))
    draw.text((tx, ty), hook_clean, font=f_hook, fill=(255, 255, 255, 255))

    # Tên sản phẩm rút gọn ở dưới
    short_prod = (product_name or "").strip()
    if len(short_prod) > 42:
        short_prod = short_prod[:40].rstrip() + "..."
    if short_prod:
        draw.rounded_rectangle([54, 1710, 1026, 1805], radius=18, fill=(15, 23, 42, 225), outline=(245, 158, 11, 220), width=3)
        pb = draw.textbbox((0, 0), short_prod, font=f_sub)
        px = max(72, (1080 - (pb[2] - pb[0])) // 2)
        draw.text((px, 1735), short_prod, font=f_sub, fill=(254, 240, 138, 255))

    # Badge giá nếu có
    if price_str:
        num = re.sub(r"[^\d]", "", str(price_str))
        if num:
            p_fmt = f"🔥 CHỈ {int(num):,}Đ".replace(",", ".")
            draw.rounded_rectangle([64, 195, 420, 265], radius=16, fill=(245, 158, 11, 245), outline=(255, 255, 255, 240), width=3)
            draw.text((88, 210), p_fmt, font=f_badge, fill=(15, 23, 42, 255))

    out_im = Image.alpha_composite(canvas, overlay).convert("RGB")
    out_im.save(img_path, format="JPEG", quality=95)


def _load_thumb_intro_registry() -> dict:
    with _THUMB_REG_LOCK:
        reg_path = os.path.join(THUMBS_ROOT_DIR, ".thumb_injected_registry.json")
        if os.path.isfile(reg_path):
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {}


def _save_thumb_intro_registry(reg: dict) -> None:
    with _THUMB_REG_LOCK:
        try:
            os.makedirs(THUMBS_ROOT_DIR, exist_ok=True)
            reg_path = os.path.join(THUMBS_ROOT_DIR, ".thumb_injected_registry.json")
            current = _load_thumb_intro_registry()
            current.update(reg or {})
            _esm_atomic_write_json(reg_path, current)
        except Exception:
            pass


def inject_thumbnail_01s_into_video(video_path: str, thumb_path: str, duration_sec: float = 0.1) -> dict:
    """
    Ghép ảnh Thumbnail (1080x1920) vào 0.1 giây đầu tiên của Video Final (giữ nguyên FPS gốc của video: 24/30/60 FPS).
    Tự động nhận diện chính xác nếu video đã từng ghép intro trước đó qua metadata tag `skillautoveo_thumb_intro=<sec>`
    và registry để cắt bỏ đúng phần intro cũ khi đổi Thumbnail nhiều lần, tuyệt đối không làm tăng thời lượng clip ngắn.
    """
    if not os.path.isfile(video_path):
        return {"ok": False, "error": f"Không tìm thấy file video: {video_path}"}
    if not os.path.isfile(thumb_path):
        return {"ok": False, "error": f"Không tìm thấy file ảnh Thumbnail: {thumb_path}"}

    dur = max(0.05, min(1.0, float(duration_sec or 0.1)))
    hw = detect_hardware_specs()
    cfg = load_engine_settings()
    enc_pref = cfg.get("video_encoder", "auto")
    use_nvenc = (enc_pref == "h264_nvenc") or (enc_pref == "auto" and hw.get("has_nvenc"))
    threads_cnt = int(cfg.get("ffmpeg_threads_per_job") or 4)

    # Đọc thời lượng, FPS gốc, có kênh âm thanh không và metadata comment xem đã có intro 0.1s chưa
    already_has_intro = False
    prev_intro_dur = dur
    v_dur = 0.0
    target_fps = 60
    has_audio = True

    norm_vpath = os.path.normcase(os.path.abspath(video_path))
    reg = _load_thumb_intro_registry()

    try:
        r_pr = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration:format_tags=comment:stream=codec_type,r_frame_rate",
                "-of", "json",
                video_path,
            ],
            capture_output=True, text=True, timeout=12,
        )
        pr_data = json.loads(r_pr.stdout or "{}")
        fmt_info = pr_data.get("format") or {}
        v_dur = float(fmt_info.get("duration") or 0.0)
        tags = fmt_info.get("tags") or {}
        comment_val = str(tags.get("comment") or tags.get("COMMENT") or "")
        m_tag = re.search(r"skillautoveo_thumb_intro=([0-9.]+)", comment_val)
        if m_tag:
            already_has_intro = True
            prev_intro_dur = float(m_tag.group(1))

        streams = pr_data.get("streams") or []
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        for s in streams:
            if s.get("codec_type") == "video" and s.get("r_frame_rate"):
                fr_str = str(s["r_frame_rate"])
                if "/" in fr_str:
                    num, den = fr_str.split("/", 1)
                    if float(den) > 0:
                        fps_calc = int(round(float(num) / float(den)))
                        if 15 <= fps_calc <= 120:
                            target_fps = fps_calc
                break
    except Exception:
        pass

    if not already_has_intro and norm_vpath in reg:
        entry_reg = reg[norm_vpath]
        expected_total = float(entry_reg.get("expected_total_dur") or 0.0)
        if v_dur > 0 and expected_total > 0 and abs(v_dur - expected_total) < 0.08:
            already_has_intro = True
            prev_intro_dur = float(entry_reg.get("intro_dur") or dur)
    elif not already_has_intro and v_dur >= 29.98 and abs(v_dur - 30.0) < 0.18:
        already_has_intro = True
        prev_intro_dur = dur

    base_dur_est = max(0.1, (v_dur - prev_intro_dur) if already_has_intro else v_dur)
    v_trim_expr = f"trim=start={prev_intro_dur:.4f}," if already_has_intro else ""
    a_trim_expr = f"atrim=start={prev_intro_dur:.4f}," if already_has_intro else ""

    tmp_out = video_path + ".thumb_tmp.mp4"
    if has_audio:
        fc = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps},trim=duration={dur:.4f},setpts=PTS-STARTPTS,format=yuv420p[vt];"
            f"aevalsrc=0:d={dur:.4f}:s=44100:c=stereo,aformat=sample_fmts=fltp:channel_layouts=stereo[at];"
            f"[1:v]{v_trim_expr}scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps},setpts=PTS-STARTPTS,format=yuv420p[vm];"
            f"[1:a]{a_trim_expr}aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[am];"
            f"[vt][at][vm][am]concat=n=2:v=1:a=1[vout][aout]"
        )
        map_args = ["-map", "[vout]", "-map", "[aout]"]
        audio_enc_args = ["-c:a", "aac", "-b:a", "128k"]
    else:
        fc = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps},trim=duration={dur:.4f},setpts=PTS-STARTPTS,format=yuv420p[vt];"
            f"[1:v]{v_trim_expr}scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps},setpts=PTS-STARTPTS,format=yuv420p[vm];"
            f"[vt][vm]concat=n=2:v=1:a=0[vout]"
        )
        map_args = ["-map", "[vout]"]
        audio_enc_args = []

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-loop", "1", "-t", f"{dur:.4f}", "-i", thumb_path,
        "-i", video_path,
        "-filter_complex", fc,
        *map_args,
        "-r", str(target_fps),
        "-threads", str(threads_cnt),
        "-metadata", f"comment=skillautoveo_thumb_intro={dur:.4f}",
    ]
    def _build_encode_cmd(nvenc: bool) -> list:
        encode_cmd = list(cmd)
        if nvenc:
            encode_cmd += ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20"]
        else:
            encode_cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "19"]
        encode_cmd += [*audio_enc_args, "-movflags", "+faststart", tmp_out]
        return encode_cmd

    try:
        res = subprocess.run(_build_encode_cmd(use_nvenc), capture_output=True, text=True, timeout=180)
        if (res.returncode != 0 or not os.path.isfile(tmp_out) or os.path.getsize(tmp_out) < 20000) and use_nvenc:
            if os.path.isfile(tmp_out):
                try:
                    os.remove(tmp_out)
                except OSError:
                    pass
            res = subprocess.run(_build_encode_cmd(False), capture_output=True, text=True, timeout=180)
        if res.returncode != 0 or not os.path.isfile(tmp_out) or os.path.getsize(tmp_out) < 20000:
            if os.path.isfile(tmp_out):
                os.remove(tmp_out)
            return {"ok": False, "error": f"FFmpeg lỗi: {(res.stderr or '')[:250]}"}
        replaced_ok = False
        last_rep_err = None
        for rep_i in range(8):
            try:
                os.replace(tmp_out, video_path)
                replaced_ok = True
                break
            except OSError as rep_exc:
                last_rep_err = rep_exc
                time.sleep(0.06 * (rep_i + 1))
        if not replaced_ok:
            try:
                shutil.copy2(tmp_out, video_path)
                os.remove(tmp_out)
            except Exception:
                if os.path.isfile(tmp_out):
                    try:
                        os.remove(tmp_out)
                    except OSError:
                        pass
                return {"ok": False, "error": f"File MP4 đang được mở/phát nên chưa ghi đè intro được ({last_rep_err})"}
        new_dur = base_dur_est + dur
        try:
            r_new = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=8,
            )
            new_dur = float((r_new.stdout or "").strip() or new_dur)
        except Exception:
            pass
        reg[norm_vpath] = {
            "intro_dur": round(dur, 4),
            "orig_dur": round(base_dur_est, 4),
            "expected_total_dur": round(new_dur, 4),
            "fps": target_fps,
            "updated_at": time.time(),
        }
        _save_thumb_intro_registry(reg)
        return {
            "ok": True,
            "video_path": video_path,
            "thumb_path": thumb_path,
            "duration_sec": dur,
            "replaced_existing_intro": already_has_intro,
            "fps": target_fps,
            "total_duration_sec": round(new_dur, 4),
        }
    except Exception as e:
        if os.path.isfile(tmp_out):
            try:
                os.remove(tmp_out)
            except OSError:
                pass
        return {"ok": False, "error": str(e)}


import threading

_THUMB_PREFERRED_LOCK = threading.Lock()
_THUMB_PREFERRED_PROFILES = []


def _cliproxy_no_proxy_opener():
    import urllib.request
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _cliproxy_fetch_models(opener=None, base_url: str = "", api_key: str = "", timeout: float = 4.0) -> tuple:
    """Query `/v1/models` on local CLIProxy without system proxy. Returns `(ok: bool, models: list[str], err: str)`."""
    import urllib.request
    cfg = get_cliproxy_config()
    b_url = (base_url or cfg.get("url") or "http://127.0.0.1:8317").strip().rstrip("/")
    a_key = (api_key or cfg.get("api_key") or "grok-video-key-001").strip()
    op = opener or _cliproxy_no_proxy_opener()
    try:
        req = urllib.request.Request(
            f"{b_url}/v1/models",
            headers={"Authorization": f"Bearer {a_key}"},
            method="GET",
        )
        with op.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        models = [str(m.get("id") or "") for m in (data.get("data") or []) if m.get("id")]
        return True, models, ""
    except Exception as e:
        return False, [], str(e)


def _cliproxy_image_candidates(requested_model: str, available: list = None) -> list:
    """Resolve ordered candidate model IDs for CLIProxy `/v1/images/*` endpoints (excluding chat-only image models)."""
    req_name = str(requested_model or "").strip() or "gpt-image-2"
    low_req = req_name.lower()
    avail = list(available or [])
    avail_set = set(avail)

    if "gemini" in low_req:
        return []

    if "grok" in low_req:
        grok_cands = []
        norm_req = "grok-imagine-image" if low_req in ("grok", "grok-2-image") else req_name
        if norm_req in avail_set:
            grok_cands.append(norm_req)
        for m in avail:
            ml = m.lower()
            if "grok" in ml and "video" not in ml and m not in grok_cands:
                grok_cands.append(m)
        if not avail:
            grok_cands.append(norm_req)
        return grok_cands

    # ChatGPT / OpenAI Codex image endpoint (`/v1/images/generations` and `/v1/images/edits`)
    mapped_req = req_name
    if low_req in ("gpt-image-1", "dall-e-3", "chatgpt"):
        mapped_req = "gpt-image-2"
    elif low_req == "dall-e-2":
        mapped_req = "gpt-image-1.5"

    ordered = []
    preferred = [
        mapped_req,
        "gpt-image-2",
        "gpt-image-2.5",
        "gpt-image-1.5",
        "gpt-image-2.5-flare",
        "gpt-image-2.5-sunburst",
    ]
    if avail:
        for cand in preferred:
            if cand in avail_set and cand not in ordered:
                ordered.append(cand)
        return ordered

    for cand in (mapped_req, "gpt-image-2", "gpt-image-2.5", "gpt-image-1.5"):
        if cand not in ordered:
            ordered.append(cand)
    return ordered


def _resolve_cliproxy_image_model(requested_model: str, opener=None, allow_cross_fallback: bool = True) -> str:
    """Resolve best `/v1/images/*` model supported by CLIProxy `:8317/v1/models`."""
    req_name = str(requested_model or "").strip() or "gpt-image-2"
    if "gemini" in req_name.lower():
        return req_name
    ok_m, avail, _ = _cliproxy_fetch_models(opener=opener, timeout=5.0)
    if not ok_m:
        if "grok" in req_name.lower() and not allow_cross_fallback:
            return "grok-imagine-image"
        fb_offline = _cliproxy_image_candidates("gpt-image-2" if "grok" in req_name.lower() else req_name, None)
        return fb_offline[0] if fb_offline else "gpt-image-2"
    cands = _cliproxy_image_candidates(req_name, avail)
    if cands:
        return cands[0]
    if allow_cross_fallback:
        fb = _cliproxy_image_candidates("gpt-image-2", avail)
        if fb:
            return fb[0]
    if "grok" in req_name.lower():
        return ""
    return "gpt-image-2"


def _normalize_cliproxy_image_size(size_str: str, ratio: str = "") -> str:
    """Map requested dimensions/aspect ratio to reliable CLIProxy `/v1/images/*` sizes."""
    s = str(size_str or "").strip().lower()
    if s in ("1024x1536", "1536x1024", "1024x1024", "1024x1792", "1792x1024"):
        return s
    if "x" in s:
        try:
            w, h = [int(p) for p in s.split("x", 1)]
            if w == h:
                return "1024x1024"
            return "1024x1536" if h > w else "1536x1024"
        except Exception:
            pass
    r = str(ratio or "").strip()
    if r in ("16:9", "4:3", "3:2", "21:9"):
        return "1536x1024"
    if r == "1:1":
        return "1024x1024"
    return "1024x1536"


def _prepare_cliproxy_ref_image(rpath: str, max_side: int = 1536, max_bytes: int = 1_100_000) -> tuple:
    """Read & resize/convert reference image to crisp RGB JPEG for fast reliable CLIProxy multi-ref uploads."""
    import mimetypes
    with open(rpath, "rb") as rf:
        raw_img = rf.read()
    ext = os.path.splitext(rpath)[1].lower()
    fname = os.path.basename(rpath)
    mime = mimetypes.guess_type(rpath)[0] or ("image/png" if ext == ".png" else "image/jpeg")

    try:
        from PIL import Image
        import io as _io
        with Image.open(_io.BytesIO(raw_img)) as im:
            w, h = im.size
            needs_convert = (
                ext not in (".jpg", ".jpeg", ".png")
                or max(w, h) > max_side
                or len(raw_img) > max_bytes
                or im.mode not in ("RGB", "L")
            )
            if needs_convert:
                if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                    rgba = im.convert("RGBA")
                    bg = Image.new("RGB", rgba.size, (255, 255, 255))
                    bg.paste(rgba, mask=rgba.split()[-1])
                    rgb = bg
                else:
                    rgb = im.convert("RGB")
                if max(w, h) > max_side:
                    scale = max_side / float(max(w, h))
                    rgb = rgb.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
                q = 90
                buf = _io.BytesIO()
                rgb.save(buf, format="JPEG", quality=q, optimize=True)
                while buf.tell() > max_bytes and q > 60:
                    q -= 8
                    buf = _io.BytesIO()
                    rgb.save(buf, format="JPEG", quality=q, optimize=True)
                stem = os.path.splitext(fname)[0] or "ref"
                return buf.getvalue(), f"{stem}.jpg", "image/jpeg"
    except Exception:
        pass
    return raw_img, fname, mime


def _normalize_saved_image_to_jpg(path: str) -> None:
    """Normalize saved image bytes to match target extension (`.jpg`/`.jpeg` -> JPEG, `.png` -> PNG)."""
    if not path or not os.path.isfile(path):
        return
    try:
        low = path.lower()
        with open(path, "rb") as f:
            head = f.read(8)
        from PIL import Image
        if low.endswith(".png"):
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                return
            with Image.open(path) as im:
                im.save(path, format="PNG")
            return
        if head[:2] == b"\xff\xd8":
            return
        with Image.open(path) as im:
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                rgba = im.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[-1])
                bg.save(path, format="JPEG", quality=95)
            else:
                im.convert("RGB").save(path, format="JPEG", quality=95)
    except Exception:
        pass


def _extract_image_bytes_from_chat_completion(rj: dict, opener) -> bytes:
    """Extract image bytes from CLIProxy `/v1/chat/completions` Gemini image response."""
    import base64
    choices = rj.get("choices") or []
    if not choices:
        return b""
    msg = choices[0].get("message") or {}

    candidates = []
    for item in (msg.get("images") or []):
        if isinstance(item, dict):
            if item.get("b64_json"):
                candidates.append(f"data:image/png;base64,{item['b64_json']}")
            u = ((item.get("image_url") or {}).get("url") if isinstance(item.get("image_url"), dict) else item.get("url")) or ""
            if u:
                candidates.append(str(u))

    content = msg.get("content")
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                u = ((part.get("image_url") or {}).get("url") if isinstance(part.get("image_url"), dict) else part.get("url")) or ""
                if u:
                    candidates.append(str(u))
    elif isinstance(content, str) and "data:image/" in content:
        m = re.search(r"data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+", content)
        if m:
            candidates.append(m.group(0))

    for u in candidates:
        if u.startswith("data:image/") and ";base64," in u:
            b64_part = u.split(";base64,", 1)[1].strip()
            return base64.b64decode(b64_part)
        if u.startswith("http://") or u.startswith("https://"):
            with opener.open(u, timeout=60) as r_dl:
                return r_dl.read()
    return b""


def _render_image_via_cliproxy_chat(
    meta: dict,
    out_path: str,
    model_name: str = "gemini-3.1-flash-image",
    opener=None,
    cp_cfg: dict = None,
) -> tuple:
    """Render image (text-to-image or multi-reference editing) via CLIProxy `/v1/chat/completions`."""
    import base64
    import urllib.error
    import urllib.request

    cfg = cp_cfg or get_cliproxy_config()
    b_url = (cfg.get("url") or "http://127.0.0.1:8317").strip().rstrip("/")
    a_key = (cfg.get("api_key") or "grok-video-key-001").strip()
    op = opener or _cliproxy_no_proxy_opener()

    ref_imgs = [p for p in (meta.get("reference_images") or []) if p and os.path.isfile(p)]
    ratio = str(meta.get("aspect_ratio") or meta.get("ratio") or "").strip()
    if not ratio:
        sz = str(meta.get("image_size") or "")
        if sz == "1536x1024" or sz == "1792x1024":
            ratio = "16:9"
        elif sz == "1024x1024":
            ratio = "1:1"
        else:
            ratio = "9:16"

    prompt_txt = str(meta.get("prompt") or "").strip()
    if f"{ratio}" not in prompt_txt:
        prompt_txt = f"Aspect ratio {ratio}. {prompt_txt}"
    if ref_imgs:
        prompt_txt = f"{prompt_txt}\nUse ALL attached reference images accurately. Output ONLY the finished generated image."

    parts = [{"type": "text", "text": prompt_txt}]
    for rpath in ref_imgs[:4]:
        raw_b, _, mime = _prepare_cliproxy_ref_image(rpath)
        b64 = base64.b64encode(raw_b).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": parts if len(parts) > 1 else prompt_txt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{b_url}/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {a_key}",
        },
        method="POST",
    )
    try:
        with op.open(req, timeout=180) as resp:
            rj = json.loads(resp.read().decode("utf-8", errors="replace"))
        img_bytes = _extract_image_bytes_from_chat_completion(rj, op)
        if not img_bytes:
            return False, "", f"CLIProxy Gemini ({model_name}) không trả về dữ liệu ảnh"
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "wb") as wf:
            wf.write(img_bytes)
        _normalize_saved_image_to_jpg(out_path)
        label = f"cliproxy_gemini ({model_name}{' Ref Image Edit' if ref_imgs else ''})"
        return True, label, ""
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:350]
        return False, "", f"CLIProxy Gemini ({model_name}) HTTP {e.code}: {err_body}"
    except Exception as e:
        return False, "", f"CLIProxy Gemini (:8317, {model_name}): {e}"


def _render_thumbnail_via_chatgpt(meta: dict, out_thumb_proj: str) -> tuple:
    """
    Render ảnh AI qua CLIProxy `:8317` hỗ trợ cả:
      - ChatGPT/Codex (`gpt-image-2`, `gpt-image-2.5`, `gpt-image-1.5`) qua `/v1/images/edits` (đa ảnh ref) & `/v1/images/generations`
      - xAI Grok (`grok-imagine-image*`) qua `/v1/images/edits` & `/v1/images/generations` (nếu đã login Grok trong CLIProxy)
      - Google Gemini CLIProxy (`gemini-3.1-flash-image`) qua `/v1/chat/completions` (kèm đa ảnh ref)
    """
    import base64
    import urllib.error
    import urllib.request

    cfg = get_cliproxy_config()
    b_url = (cfg.get("url") or "http://127.0.0.1:8317").strip().rstrip("/")
    a_key = (cfg.get("api_key") or "grok-video-key-001").strip()
    opener = _cliproxy_no_proxy_opener()

    ref_imgs = [p for p in (meta.get("reference_images") or []) if p and os.path.isfile(p)]
    prompt_str = str(meta.get("prompt") or "").strip()
    req_model = str(
        meta.get("image_model") or meta.get("model_name") or meta.get("model") or "gpt-image-2"
    ).strip()
    req_low = req_model.lower()
    norm_size = _normalize_cliproxy_image_size(
        meta.get("image_size", "1024x1536"),
        meta.get("aspect_ratio") or meta.get("ratio") or "",
    )

    ok_models, available, err_models = _cliproxy_fetch_models(opener=opener, base_url=b_url, api_key=a_key, timeout=4.0)
    if not ok_models and not available:
        # Proceed directly using mapped fallback only if local port fails cleanly with error detail
        pass

    # A. Route Gemini CLIProxy explicitly via `/v1/chat/completions`
    if "gemini" in req_low:
        gem_model = req_model if (not available or req_model in available) else (
            next((m for m in available if "gemini" in m.lower() and "image" in m.lower()), "")
        )
        if available and not gem_model:
            return False, "", "CLIProxy (:8317) chưa có model gemini-3.1-flash-image. Hãy đăng nhập Antigravity/Gemini trên Web Admin :8317."
        return _render_image_via_cliproxy_chat(
            meta, out_thumb_proj, model_name=gem_model or "gemini-3.1-flash-image", opener=opener, cp_cfg=cfg
        )

    # B. Explicit xAI Grok check (do NOT silently claim Grok ran when no xai-*.json account is loaded)
    is_grok_req = "grok" in req_low
    candidates = _cliproxy_image_candidates(req_model, available if ok_models else None)
    if is_grok_req and ok_models and not candidates:
        return (
            False,
            "",
            "CLIProxy (:8317) chưa có tài khoản xAI Grok (thiếu model grok-imagine-image trên /v1/models). "
            "Hãy vào Tab Tài Khoản → Login Grok (xAI) hoặc Web Admin :8317 để đăng nhập, hoặc chọn ChatGPT Image / Gemini CLIProxy.",
        )

    if not candidates and not is_grok_req and ok_models:
        # Codex image models absent; check if Gemini image model is logged into CLIProxy
        gem_avail = next((m for m in available if "gemini" in m.lower() and "image" in m.lower()), "")
        if gem_avail and bool(meta.get("allow_gemini_fallback", False)):
            return _render_image_via_cliproxy_chat(meta, out_thumb_proj, model_name=gem_avail, opener=opener, cp_cfg=cfg)
        return (
            False,
            "",
            "CLIProxy (:8317) chưa có tài khoản OpenAI Codex hỗ trợ tạo ảnh (gpt-image-2). "
            "Hãy vào Tab Tài Khoản → Login Codex (ChatGPT Plus) hoặc chuyển sang Gemini CLIProxy / Google Flow."
            + (f" (Models hiện có: {', '.join(available[:6])})" if available else ""),
        )

    if not candidates:
        return False, "", f"Không kết nối được CLIProxy ({b_url}): {err_models or 'service offline'}"

    os.makedirs(os.path.dirname(os.path.abspath(out_thumb_proj)), exist_ok=True)
    last_err = ""

    # Prepare compressed reference payloads once across retries
    prepared_refs = []
    if ref_imgs:
        for rpath in ref_imgs[:4]:
            prepared_refs.append(_prepare_cliproxy_ref_image(rpath))

    for resolved_model in candidates[:3]:
        # 1. Multi-reference edit (`/v1/images/edits`)
        if prepared_refs:
            try:
                boundary = f"----SkillAutoVeoThumbBoundary{int(time.time() * 1000)}"
                body_parts = []

                def _add_field(name: str, val: str):
                    body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
                    body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
                    body_parts.append(f"{val}\r\n".encode("utf-8"))

                _add_field("model", resolved_model)
                _add_field("prompt", prompt_str)
                _add_field("size", norm_size)
                _add_field("n", "1")

                field_name = "image[]" if len(prepared_refs) > 1 else "image"
                for raw_img, fname, mime in prepared_refs:
                    body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
                    body_parts.append(
                        f'Content-Disposition: form-data; name="{field_name}"; filename="{fname}"\r\n'
                        f"Content-Type: {mime}\r\n\r\n".encode("utf-8")
                    )
                    body_parts.append(raw_img)
                    body_parts.append(b"\r\n")

                body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
                body_bytes = b"".join(body_parts)

                req_edit = urllib.request.Request(
                    f"{b_url}/v1/images/edits",
                    data=body_bytes,
                    headers={
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                        "Authorization": f"Bearer {a_key}",
                    },
                    method="POST",
                )
                with opener.open(req_edit, timeout=180) as resp:
                    rj = json.loads(resp.read().decode("utf-8", errors="replace"))
                item0 = (rj.get("data") or [{}])[0]
                if item0.get("b64_json"):
                    with open(out_thumb_proj, "wb") as wf:
                        wf.write(base64.b64decode(item0["b64_json"]))
                    _normalize_saved_image_to_jpg(out_thumb_proj)
                    eng_prefix = "grok" if "grok" in resolved_model.lower() else "chatgpt"
                    return True, f"{eng_prefix} ({resolved_model} Ref Image Edit)", ""
                if item0.get("url"):
                    with opener.open(item0["url"], timeout=60) as r_dl:
                        with open(out_thumb_proj, "wb") as wf:
                            wf.write(r_dl.read())
                    _normalize_saved_image_to_jpg(out_thumb_proj)
                    eng_prefix = "grok" if "grok" in resolved_model.lower() else "chatgpt"
                    return True, f"{eng_prefix} ({resolved_model} Ref Image Edit)", ""
                last_err = f"Image edit ({resolved_model}) returned no image"
            except urllib.error.HTTPError as e:
                err_txt = e.read().decode("utf-8", errors="replace")[:350]
                last_err = f"Image edit ({resolved_model}) HTTP {e.code}: {err_txt}"
            except Exception as e:
                last_err = f"Image edit ({resolved_model}) failed; references preserved, no text-only fallback: {e}"
            continue

        # 2. Text-only generation (`/v1/images/generations`) when no reference images supplied
        try:
            payload = json.dumps({
                "model": resolved_model,
                "prompt": prompt_str,
                "size": norm_size,
                "n": 1,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{b_url}/v1/images/generations",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {a_key}",
                },
                method="POST",
            )
            with opener.open(req, timeout=120) as resp:
                rj = json.loads(resp.read().decode("utf-8", errors="replace"))
            item0 = (rj.get("data") or [{}])[0]
            if item0.get("b64_json"):
                with open(out_thumb_proj, "wb") as wf:
                    wf.write(base64.b64decode(item0["b64_json"]))
                _normalize_saved_image_to_jpg(out_thumb_proj)
                eng_prefix = "grok" if "grok" in resolved_model.lower() else "chatgpt"
                return True, f"{eng_prefix} ({resolved_model})", ""
            if item0.get("url"):
                with opener.open(item0["url"], timeout=60) as r_dl:
                    with open(out_thumb_proj, "wb") as wf:
                        wf.write(r_dl.read())
                _normalize_saved_image_to_jpg(out_thumb_proj)
                eng_prefix = "grok" if "grok" in resolved_model.lower() else "chatgpt"
                return True, f"{eng_prefix} ({resolved_model})", ""
            last_err = f"CLIProxy Image API ({resolved_model}) không trả về dữ liệu ảnh"
        except urllib.error.HTTPError as e:
            err_txt = e.read().decode("utf-8", errors="replace")[:350]
            last_err = f"CLIProxy Image API (:8317, {resolved_model}) HTTP {e.code}: {err_txt}"
        except Exception as e:
            last_err = f"CLIProxy Image API (:8317, {resolved_model}): {e}"

    return False, "", last_err or "CLIProxy Image API không tạo được ảnh"


generate_image_via_cliproxy = _render_thumbnail_via_chatgpt


def _run_async_sync(coro):
    """Run an async coroutine safely whether or not the caller thread already has an event loop."""
    import asyncio
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    holder = {}
    def _runner():
        try:
            holder["result"] = asyncio.run(coro)
        except BaseException as exc:
            holder["error"] = exc

    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    th.join()
    if "error" in holder:
        raise holder["error"]
    return holder.get("result")


def _render_thumbnails_via_google_flow_batch(items: list) -> dict:
    """
    Render Ảnh Thumbnail AI 2K qua engine Google Flow thống nhất (`grok_video_tool.run_veo_flow` / `_FlowBrowserActor`)
    với đa tài khoản failover, tự refresh cookie/token theo `profile_name`, dùng đúng `project_id` riêng từng tài khoản
    và tái sử dụng tài khoản vừa thắng cho các biến thể tiếp theo.
    """
    outcomes = {}
    if not items:
        return outcomes

    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    if WS_DIR not in sys.path:
        sys.path.insert(0, WS_DIR)

    try:
        import grok_video_tool as gvt
    except Exception as e:
        for it in items:
            outcomes[it["meta"]["vkey"]] = (False, "", f"Lỗi nạp grok_video_tool: {e}")
        return outcomes

    flow_accs = [a for a in (list_available_flow_accounts() or []) if a.get("active", True)]
    if not flow_accs:
        for it in items:
            outcomes[it["meta"]["vkey"]] = (
                False,
                "",
                "Chưa có tài khoản Google Flow nào đang hoạt động. Vui lòng đăng nhập tài khoản trong tab Tài Khoản!",
            )
        return outcomes

    bridge = None
    try:
        bridge = gvt.CaptchaBridge(print, port=getattr(gvt, "CAPTCHA_BRIDGE_PORT", 4000))
        try:
            bridge.start(allow_remote=True)
        except TypeError:
            bridge.start()
    except Exception:
        bridge = None

    def _ordered_accounts(meta: dict) -> list:
        want_acc = str(meta.get("account_name") or "").strip()
        want_prof = str(meta.get("google_profile_name") or "").strip()
        strict_only = bool(meta.get("strict_profile_only", False))
        with _THUMB_PREFERRED_LOCK:
            pref_order = list(_THUMB_PREFERRED_PROFILES)

        def _prof_of(acc: dict) -> str:
            acc_n = str(acc.get("name") or "").strip()
            return str(acc.get("profile_name") or "").strip() or (
                gvt._google_profile_name_for_account(acc, allow_unresolved=True)
                if hasattr(gvt, "_google_profile_name_for_account") else ""
            ) or acc_n

        pool_accs = list(flow_accs)
        allowed_profs = [str(p).strip() for p in (meta.get("allowed_profile_names") or []) if str(p).strip()]
        if allowed_profs:
            only_allowed = [acc for acc in pool_accs if _prof_of(acc) in allowed_profs]
            if only_allowed:
                pool_accs = only_allowed

        if strict_only and want_prof:
            exact = [acc for acc in pool_accs if _prof_of(acc) == want_prof]
            if exact:
                return exact
            return []

        def _acc_key(acc: dict) -> tuple:
            acc_n = str(acc.get("name") or "").strip()
            prof_n = _prof_of(acc)
            if want_acc and acc_n == want_acc:
                return (0, 0)
            if want_prof and prof_n == want_prof:
                return (0, 1)
            if prof_n in pref_order:
                return (1, pref_order.index(prof_n))
            return (2, 0)

        return [acc for _, acc in sorted(enumerate(pool_accs), key=lambda pair: (_acc_key(pair[1]), pair[0]))]

    for it in items:
        meta = it["meta"]
        vk = meta["vkey"]
        char_v = meta.get("char_v") or vk
        out_thumb_proj = it["out_thumb_proj"]
        os.makedirs(os.path.dirname(os.path.abspath(out_thumb_proj)), exist_ok=True)
        ref_imgs = [p for p in (meta.get("reference_images") or [])[:4] if p and os.path.isfile(p)]

        candidates = _ordered_accounts(meta)
        errors_tried = []
        rendered_ok = False

        for acc_idx, acc in enumerate(candidates):
            acc_name = str(acc.get("name") or "").strip()
            prof_name = str(acc.get("profile_name") or "").strip()
            if not prof_name and hasattr(gvt, "_google_profile_name_for_account"):
                try:
                    prof_name = gvt._google_profile_name_for_account(acc, allow_unresolved=True) or ""
                except Exception:
                    prof_name = ""
            if not prof_name:
                prof_name = acc_name

            # Always resolve THIS account's own Flow project_id (never reuse another account's ID on failover)
            acc_project_id = str(
                acc.get("project_id") or acc.get("proxy_url") or acc.get("flow_project_id") or ""
            ).strip()
            if not acc_project_id and prof_name:
                try:
                    acc_project_id = str(get_default_flow_project_id(prof_name) or "").strip()
                except Exception:
                    acc_project_id = ""
            if not acc_project_id and acc_idx == 0:
                acc_project_id = str(meta.get("flow_project_id") or "").strip()

            tok = str(acc.get("api_key") or "").strip()
            disk_cookie = ""
            if prof_name and hasattr(gvt, "_load_flow_cookie_header"):
                try:
                    disk_cookie = gvt._load_flow_cookie_header(prof_name) or ""
                except Exception:
                    disk_cookie = ""
            if not tok and disk_cookie:
                tok = f"flow_cookie:{disk_cookie}"

            if not tok and prof_name and hasattr(gvt, "_refresh_google_profile"):
                try:
                    ok_ref, new_tok, new_pid, err_ref = gvt._refresh_google_profile(prof_name, prefer_profile=True)
                    if ok_ref and new_tok:
                        tok = new_tok
                        if new_pid and len(str(new_pid)) > 10 and not acc_project_id:
                            acc_project_id = str(new_pid).strip()
                    elif err_ref:
                        errors_tried.append(f"{prof_name}: {err_ref}")
                except Exception as ex_ref:
                    errors_tried.append(f"{prof_name}: {ex_ref}")

            if not acc_project_id:
                errors_tried.append(f"{prof_name or acc_name}: Thiếu Google Flow Project ID")
                continue

            if os.path.isfile(out_thumb_proj):
                try:
                    os.remove(out_thumb_proj)
                except OSError:
                    pass

            job = gvt.VideoJob(
                id=f"thumb_{meta['pid']}_{vk}",
                mode="text-to-video",
                prompt=meta["prompt"],
                output_name=f"{meta['pid']}_{char_v}_thumb",
                model="Nano Banana 2",
                resolution="2K",
                aspect_ratio="9:16",
                reference_image_urls=ref_imgs,
                account_name=acc_name,
                google_profile_name=prof_name,
                local_path=out_thumb_proj,
                max_retries=2,
                prefer_bearer_request=False,
                flow_request_only=True,
                require_all_reference_uploads=bool(ref_imgs),
            )
            if meta.get("char_uuid"):
                job.character_id = str(meta.get("char_uuid") or "").strip()

            try:
                ok_flow = bool(_run_async_sync(gvt.run_veo_flow(job, tok, acc_project_id, bridge, None, None)))
            except Exception as ex_flow:
                ok_flow = False
                job.error = f"Exception: {ex_flow}"

            if ok_flow and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
                _normalize_saved_image_to_jpg(out_thumb_proj)
                with _THUMB_PREFERRED_LOCK:
                    if prof_name in _THUMB_PREFERRED_PROFILES:
                        _THUMB_PREFERRED_PROFILES.remove(prof_name)
                    if prof_name:
                        _THUMB_PREFERRED_PROFILES.insert(0, prof_name)
                outcomes[vk] = (
                    True,
                    f"google_flow (Nano Banana 2 2K • {len(ref_imgs)} Ref Images • {prof_name or acc_name})",
                    "",
                )
                rendered_ok = True
                break

            err_msg = str(getattr(job, "error", "") or "Google Flow không trả về ảnh Thumbnail")
            errors_tried.append(f"{prof_name or acc_name}: {err_msg}")
            if prof_name and hasattr(gvt, "invalidate_flow_chrome_session"):
                try:
                    gvt.invalidate_flow_chrome_session(prof_name)
                except Exception:
                    pass

        if not rendered_ok:
            outcomes[vk] = (
                False,
                "",
                " | ".join(errors_tried) or "Tất cả tài khoản Google Flow đều thất bại khi tạo Thumbnail",
            )

    return outcomes


def _resolve_final_video_candidate(pid: str, char_v: str, pdir: str, meta_final: str = "") -> str:
    """Locate the rendered final MP4 for a project variant across standard and specialized project folders."""
    for cand in (
        meta_final,
        os.path.join(pdir, "video_final.mp4"),
        os.path.join(FINAL_VIDEOS_DIR, f"{pid}_{char_v}.mp4"),
        os.path.join(FINAL_VIDEOS_DIR, f"{pid}_final.mp4"),
        os.path.join(FINAL_VIDEOS_DIR, f"{pid}.mp4"),
    ):
        if cand and os.path.isfile(cand) and os.path.getsize(cand) > 10000:
            return cand
    return str(meta_final or "")


def _persist_thumbnail_to_project_manifests(
    pid: str,
    pdir: str,
    out_thumb_central: str,
    dur_01s: float,
    injected: bool,
) -> None:
    """Sync thumbnail metadata into cooking_manifest.json, transform.json, and fashion_project.json."""
    rel_media = ""
    try:
        rel_sub = os.path.relpath(out_thumb_central, WS_DIR).replace("\\", "/")
        if not rel_sub.startswith(".."):
            rel_media = f"/media/{rel_sub}"
    except Exception:
        rel_media = ""

    manifest_candidates = [
        os.path.join(pdir, "cooking_manifest.json"),
        os.path.join(pdir, "transform.json"),
        os.path.join(pdir, "fashion_project.json"),
        os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid, "fashion_project.json"),
        os.path.join(WS_DIR, "fashion_motion_projects", pid, "fashion_project.json"),
    ]
    for mf_path in manifest_candidates:
        if not os.path.isfile(mf_path):
            continue
        try:
            with open(mf_path, "r", encoding="utf-8") as rf:
                mdata = json.load(rf)
            if not isinstance(mdata, dict):
                continue
            mdata["thumbnail_path"] = out_thumb_central
            if rel_media and "transform.json" in mf_path:
                mdata["thumbnail"] = rel_media
            if injected:
                mdata["thumbnail_injected_01s"] = True
                mdata["thumbnail_intro_duration_sec"] = round(float(dur_01s or 0.1), 3)
            with open(mf_path, "w", encoding="utf-8") as wf:
                json.dump(mdata, wf, ensure_ascii=False, indent=2)
        except Exception:
            pass


def generate_thumbnail_for_variant(
    pid: str,
    vkey: str = "v1",
    provider: str = "",
    custom_master_prompt: str = "",
    preset_id: str = "",
    custom_product_info: str = "",
    add_text_badge: bool = None,
    inject_01s: bool = None,
    prefer_existing_ref: bool = False,
    apply_template_only: bool = False,
    subject_mode: str = "auto",
    headline: str = "",
    preferred_profile: str = "",
) -> dict:
    """
    Render Ảnh Thumbnail AI chuyên nghiệp & ghép cụm Ảnh Sản Phẩm Thực Tế cho 1 video ({pid}_{char_v}):
      - Dùng kết hợp 3 nguồn Reference:
          1. Ảnh nhân vật cầm sản phẩm (`char_holding_prod_img`)
          2. Bộ ảnh sản phẩm gốc (`prod_img_paths` — `prod_1.jpg .. prod_6.jpg`)
          3. Thông tin chi tiết sản phẩm & Hook (`product_info`)
      - Nếu `apply_template_only=True` (hoặc `prefer_existing_ref=True` và đã có ảnh 2K trên đĩa):
          Áp dụng ngay bố cục Template Thumbnail (`composite_template_product_insets`) lên ảnh 2K gốc (`_raw2k.jpg`) siêu tốc!
      - Sau khi render & ghép cụm Ảnh Sản Phẩm Thực Tế xong, lưu vào `projects/<pid>/thumbnails/{pid}_{char_v}_thumb.jpg`
        & `thumbnails/{pid}_{char_v}_thumb.jpg`, đồng thời ghép 0.1s vào đầu Video Final nếu `inject_01s=True`.
    """
    cfg = load_engine_settings()
    prov = (provider or cfg.get("thumbnail_provider") or "google_flow").strip().lower()
    if add_text_badge is None:
        add_text_badge = bool(cfg.get("thumbnail_add_text_badge", False))
    if inject_01s is None:
        inject_01s = bool(cfg.get("auto_inject_thumbnail_01s", True))
    embed_insets = False  # AI composes the entire thumbnail; no automatic PIL insets.
    dur_01s = float(cfg.get("thumbnail_duration_sec") or 0.1)

    meta = build_thumbnail_prompt_for_variant(
        pid=pid,
        vkey=vkey,
        custom_master_prompt=custom_master_prompt,
        preset_id=preset_id,
        custom_product_info=custom_product_info,
        subject_mode=subject_mode, headline=headline,
    )
    sel_prof = str(preferred_profile or cfg.get("selected_flow_profile") or "").strip()
    is_single_prof = (not bool(cfg.get("multi_account_enabled", True))) and bool(sel_prof)
    sel_multi = [str(p).strip() for p in (cfg.get("selected_flow_profiles") or []) if str(p).strip()]
    if sel_multi and not is_single_prof:
        meta["allowed_profile_names"] = sel_multi
    if sel_prof:
        meta["google_profile_name"] = sel_prof
        if preferred_profile or is_single_prof:
            meta["strict_profile_only"] = True
    char_v = meta["char_v"]
    tpl_obj = get_template_by_id(meta.get("template_id") or preset_id)
    pdir = os.path.join(PROJECTS_DIR, pid)
    pdir_thumbs = os.path.join(pdir, "thumbnails")
    os.makedirs(pdir_thumbs, exist_ok=True)
    os.makedirs(THUMBS_ROOT_DIR, exist_ok=True)

    out_thumb_proj = os.path.join(pdir_thumbs, f"{pid}_{char_v}_thumb.jpg")
    raw2k_proj = os.path.join(pdir_thumbs, f"{pid}_{char_v}_thumb_raw2k.jpg")
    out_thumb_central = os.path.join(THUMBS_ROOT_DIR, f"{pid}_{char_v}_thumb.jpg")

    generated_ok = False
    used_engine = prov
    err_detail = ""
    fresh_ai_rendered = False

    # 0. Nếu `prefer_existing_ref=True` hoặc `apply_template_only=True`: ưu tiên dùng ảnh 2K đã có sẵn
    if (prefer_existing_ref or apply_template_only):
        if os.path.isfile(raw2k_proj) and os.path.getsize(raw2k_proj) > 5000:
            shutil.copy2(raw2k_proj, out_thumb_proj)
            generated_ok = True
            used_engine = f"Template Compositor ({tpl_obj['short_name']})"
        elif os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
            generated_ok = True
            used_engine = f"google_flow 2K + {tpl_obj['short_name']}"
        elif os.path.isfile(out_thumb_central) and os.path.getsize(out_thumb_central) > 5000:
            shutil.copy2(out_thumb_central, out_thumb_proj)
            generated_ok = True
            used_engine = f"google_flow 2K + {tpl_obj['short_name']}"
        elif apply_template_only and meta.get("char_holding_prod_img") and os.path.isfile(meta["char_holding_prod_img"]):
            shutil.copy2(meta["char_holding_prod_img"], out_thumb_proj)
            generated_ok = True
            used_engine = f"Ref 2K + {tpl_obj['short_name']}"

    # 1. Nếu chưa có sẵn (hoặc người dùng yêu cầu Render AI 2K mới hoàn toàn)
    if not generated_ok:
        if prov in ("grok", "xai"):
            meta["image_model"] = "grok-imagine-image"
            ok_grk, eng_grk, err_grk = _render_thumbnail_via_chatgpt(meta, out_thumb_proj)
            if ok_grk and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
                generated_ok = True
                fresh_ai_rendered = True
                used_engine = f"{eng_grk} + {tpl_obj['short_name']}"
            else:
                return {"ok": False, "pid": pid, "vkey": vkey, "char_v": char_v, "error": err_grk, "provider": "grok"}
        elif prov in ("cliproxy_gemini", "gemini", "gemini_cliproxy"):
            meta["image_model"] = "gemini-3.1-flash-image"
            ok_gem, eng_gem, err_gem = _render_thumbnail_via_chatgpt(meta, out_thumb_proj)
            if ok_gem and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
                generated_ok = True
                fresh_ai_rendered = True
                used_engine = f"{eng_gem} + {tpl_obj['short_name']}"
            else:
                err_detail = err_gem
        elif prov in ("chatgpt", "openai", "gpt", "cliproxy_gpt"):
            if not meta.get("image_model") or "gpt" not in str(meta.get("image_model")).lower():
                meta["image_model"] = "gpt-image-2"
            ok_gpt, eng_gpt, err_gpt = _render_thumbnail_via_chatgpt(meta, out_thumb_proj)
            if ok_gpt and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
                generated_ok = True
                fresh_ai_rendered = True
                used_engine = f"{eng_gpt} + {tpl_obj['short_name']}"
            else:
                err_detail = err_gpt
        else:
            batch_res = _render_thumbnails_via_google_flow_batch([{"meta": meta, "out_thumb_proj": out_thumb_proj}])
            ok_fl, eng_fl, err_fl = batch_res.get(vkey, (False, "", ""))
            if (not ok_fl or not os.path.isfile(out_thumb_proj) or os.path.getsize(out_thumb_proj) <= 5000) and not is_single_prof:
                # Rotate to a healthy alternate account when rate-limited / captcha-throttled on preferred account
                try:
                    import grok_video_tool as _gvt_th
                    _th_kind = _gvt_th.classify_flow_error(str(err_fl or ""))
                    if sel_prof and _th_kind in ("rate_limit", "captcha_score", "account_quota", "account_auth"):
                        _gvt_th.mark_flow_account_cooldown(sel_prof, _th_kind, str(err_fl or ""))
                        _cand_accs = sel_multi or [a.get("profile_name") for a in list_available_flow_accounts() if a.get("active", True)]
                        _alt_accs = [
                            str(p).strip() for p in _cand_accs
                            if str(p).strip() and str(p).strip() != sel_prof and not _gvt_th.is_flow_account_in_cooldown(str(p).strip())[0]
                        ]
                        if _alt_accs:
                            _retry_meta = dict(meta)
                            _retry_meta["google_profile_name"] = _alt_accs[0]
                            _retry_meta["strict_profile_only"] = True
                            _retry_res = _render_thumbnails_via_google_flow_batch([{"meta": _retry_meta, "out_thumb_proj": out_thumb_proj}])
                            ok_fl, eng_fl, err_fl = _retry_res.get(vkey, (ok_fl, eng_fl, err_fl))
                except Exception:
                    pass
            if ok_fl and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
                generated_ok = True
                fresh_ai_rendered = True
                used_engine = f"{eng_fl} + {tpl_obj['short_name']}"
            else:
                err_detail = err_fl

    if not generated_ok or not os.path.isfile(out_thumb_proj):
        return {
            "ok": False,
            "pid": pid,
            "vkey": vkey,
            "char_v": char_v,
            "error": err_detail or "Không thể render Ảnh Thumbnail AI. Hãy kiểm tra tài khoản Google Flow hoặc CLIProxy!",
        }

    # Nếu vừa render AI 2K mới, cập nhật luôn bản backup `_raw2k.jpg`
    if fresh_ai_rendered:
        try:
            shutil.copy2(out_thumb_proj, raw2k_proj)
        except Exception:
            pass

    # Luôn ghép cụm Ảnh Sản Phẩm Thực Tế (`prod_1.jpg..prod_6.jpg`) theo đúng bố cục của Template Thumbnail!
    if embed_insets:
        try:
            composite_template_product_insets(
                img_path=out_thumb_proj,
                pdir=pdir,
                prod_img_paths=meta.get("prod_img_paths") or [],
                template_obj=tpl_obj,
                meta=meta,
            )
        except Exception as comp_err:
            print("WARN composite_template_product_insets:", comp_err)

    # Đóng khung PIL cổ điển nếu người dùng bật thêm tuỳ chọn add_text_badge
    if add_text_badge:
        try:
            _apply_pro_thumbnail_badge_overlay(
                img_path=out_thumb_proj,
                hook_title=meta["hook_title"],
                product_name=meta["product_name"],
                price_str=meta["price"],
                prod_img_path=meta["prod_img_path"],
            )
        except Exception:
            pass

    with open(out_thumb_proj + '.json', 'w', encoding='utf-8') as receipt:
        json.dump({'provider': used_engine, 'style': meta['template_id'], 'prompt': meta['prompt'],
                   'references': meta['reference_images']}, receipt, ensure_ascii=False, indent=2)
    shutil.copy2(out_thumb_proj, out_thumb_central)

    # Nếu Video Final đã có sẵn và bật inject_01s -> ghép ngay 0.1s vào đầu Video Final!
    final_mp4 = _resolve_final_video_candidate(pid, char_v, pdir, meta.get("final_video_path") or "")
    injected_info = None
    if inject_01s and final_mp4 and os.path.isfile(final_mp4) and os.path.getsize(final_mp4) > 10000:
        injected_info = inject_thumbnail_01s_into_video(final_mp4, out_thumb_central, duration_sec=dur_01s)
    injected_ok = bool(injected_info and injected_info.get("ok"))
    _persist_thumbnail_to_project_manifests(pid, pdir, out_thumb_central, dur_01s, injected_ok)

    return {
        "ok": True,
        "pid": pid,
        "vkey": vkey,
        "char_v": char_v,
        "template_id": tpl_obj["id"],
        "template_name": tpl_obj["name"],
        "layout_type": tpl_obj.get("layout_type", "grid_3_bottom"),
        "detected_category": meta.get("detected_category", "gia_dung"),
        "engine": used_engine,
        "prompt": meta["prompt"],
        "product_info": meta["product_info"],
        "char_holding_prod_img": meta["char_holding_prod_img"],
        "prod_img_path": meta["prod_img_path"],
        "reference_images": meta["reference_images"],
        "thumbnail_path": out_thumb_central,
        "project_thumbnail_path": out_thumb_proj,
        "final_video_path": final_mp4,
        "injected_01s": injected_ok,
        "inject_detail": injected_info,
    }


def generate_thumbnails_for_all_variants(
    pid: str,
    provider: str = "",
    custom_master_prompt: str = "",
    preset_id: str = "",
    custom_product_info: str = "",
    add_text_badge: bool = None,
    inject_01s: bool = None,
    apply_template_only: bool = False,
    subject_mode: str = "auto",
    headline: str = "",
) -> dict:
    """
    Render Ảnh Thumbnail AI + ghép 0.1s đầu video cho toàn bộ biến thể của 1 project
    (hỗ trợ cả project chuẩn `prompts.json`/`project.json`, Template #006 `transform.json`,
    Template #005 `cooking_manifest.json`, và Template #004 `fashion_project.json`).
    """
    pdir = os.path.join(PROJECTS_DIR, pid)
    prompts_path = os.path.join(pdir, "prompts.json")
    proj_json_path = os.path.join(pdir, "project.json")
    transform_path = os.path.join(pdir, "transform.json")
    cooking_path = os.path.join(pdir, "cooking_manifest.json")
    fashion_paths = (
        os.path.join(pdir, "fashion_project.json"),
        os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid, "fashion_project.json"),
        os.path.join(WS_DIR, "fashion_motion_projects", pid, "fashion_project.json"),
    )

    vkeys = []
    if os.path.isfile(prompts_path):
        pdata = json.load(open(prompts_path, "r", encoding="utf-8"))
        vkeys = list((pdata.get("videos") or {}).keys())
    elif os.path.isfile(proj_json_path):
        proj_data = json.load(open(proj_json_path, "r", encoding="utf-8"))
        vkeys = [str(p.get("vkey") or p.get("char_v_code") or "v1") for p in (proj_data.get("products") or [])]
    elif os.path.isfile(transform_path):
        vkeys = ["nv1_v1"]
    elif os.path.isfile(cooking_path):
        vkeys = ["pov"]
    elif any(os.path.isfile(fp) for fp in fashion_paths):
        vkeys = ["nv1_v1"]
    if not vkeys:
        return {"ok": False, "error": f"Sản phẩm {pid} chưa có kịch bản (prompts.json / project.json). Hãy bấm Tạo Kịch Bản trước!"}

    cfg = load_engine_settings()
    prov = (provider or cfg.get("thumbnail_provider") or "google_flow").strip().lower()
    if add_text_badge is None:
        add_text_badge = bool(cfg.get("thumbnail_add_text_badge", False))
    if inject_01s is None:
        inject_01s = bool(cfg.get("auto_inject_thumbnail_01s", True))
    embed_insets = False  # AI composes the entire thumbnail; no automatic PIL insets.
    dur_01s = float(cfg.get("thumbnail_duration_sec") or 0.1)

    pdir_thumbs = os.path.join(pdir, "thumbnails")
    os.makedirs(pdir_thumbs, exist_ok=True)
    os.makedirs(THUMBS_ROOT_DIR, exist_ok=True)

    # Nếu chỉ áp dụng nhanh Template (ghép cụm Ảnh Sản Phẩm Thực Tế lên các ảnh 2K đã có)
    if False:  # Legacy compositor is no longer a generation mode.
        results = []
        for vk in vkeys:
            r = generate_thumbnail_for_variant(
                pid=pid,
                vkey=vk,
                provider=provider,
                custom_master_prompt=custom_master_prompt,
                preset_id=preset_id,
                custom_product_info=custom_product_info,
                subject_mode=subject_mode, headline=headline,
                add_text_badge=add_text_badge,
                inject_01s=inject_01s,
                prefer_existing_ref=True,
                apply_template_only=True,
            )
            results.append(r)
        ok_cnt = sum(1 for r in results if r.get("ok"))
        return {
            "ok": ok_cnt > 0,
            "pid": pid,
            "total": len(vkeys),
            "success_count": ok_cnt,
            "results": results,
        }

    if prov in ("google_flow", "nano_banana", "flow"):
        batch_items = []
        for vk in vkeys:
            meta = build_thumbnail_prompt_for_variant(
                pid=pid,
                vkey=vk,
                custom_master_prompt=custom_master_prompt,
                preset_id=preset_id,
                custom_product_info=custom_product_info,
                subject_mode=subject_mode, headline=headline,
            )
            out_proj = os.path.join(pdir_thumbs, f"{pid}_{meta['char_v']}_thumb.jpg")
            batch_items.append({"meta": meta, "out_thumb_proj": out_proj})

        outcomes = _render_thumbnails_via_google_flow_batch(batch_items)
        results = []
        for it in batch_items:
            meta = it["meta"]
            vk = meta["vkey"]
            char_v = meta["char_v"]
            tpl_obj = get_template_by_id(meta.get("template_id") or preset_id)
            out_thumb_proj = it["out_thumb_proj"]
            raw2k_proj = os.path.join(pdir_thumbs, f"{pid}_{char_v}_thumb_raw2k.jpg")
            out_thumb_central = os.path.join(THUMBS_ROOT_DIR, f"{pid}_{char_v}_thumb.jpg")
            ok_fl, eng_fl, err_fl = outcomes.get(vk, (False, "", "Lỗi không xác định"))
            if ok_fl and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 5000:
                try:
                    shutil.copy2(out_thumb_proj, raw2k_proj)
                except Exception:
                    pass
                if embed_insets:
                    try:
                        composite_template_product_insets(
                            img_path=out_thumb_proj,
                            pdir=pdir,
                            prod_img_paths=meta.get("prod_img_paths") or [],
                            template_obj=tpl_obj,
                            meta=meta,
                        )
                    except Exception:
                        pass
                if add_text_badge:
                    try:
                        _apply_pro_thumbnail_badge_overlay(
                            img_path=out_thumb_proj,
                            hook_title=meta["hook_title"],
                            product_name=meta["product_name"],
                            price_str=meta["price"],
                            prod_img_path=meta["prod_img_path"],
                        )
                    except Exception:
                        pass
                with open(out_thumb_proj + '.json', 'w', encoding='utf-8') as receipt:
                    json.dump({'provider': eng_fl, 'style': meta['template_id'], 'prompt': meta['prompt'],
                        'references': meta['reference_images']}, receipt, ensure_ascii=False, indent=2)
                shutil.copy2(out_thumb_proj, out_thumb_central)
                final_mp4 = _resolve_final_video_candidate(pid, char_v, pdir, meta.get("final_video_path") or "")
                injected_info = None
                if inject_01s and final_mp4 and os.path.isfile(final_mp4) and os.path.getsize(final_mp4) > 10000:
                    injected_info = inject_thumbnail_01s_into_video(final_mp4, out_thumb_central, duration_sec=dur_01s)
                injected_ok = bool(injected_info and injected_info.get("ok"))
                _persist_thumbnail_to_project_manifests(pid, pdir, out_thumb_central, dur_01s, injected_ok)
                results.append({
                    "ok": True,
                    "pid": pid,
                    "vkey": vk,
                    "char_v": char_v,
                    "template_id": tpl_obj["id"],
                    "template_name": tpl_obj["name"],
                    "layout_type": tpl_obj.get("layout_type", "grid_3_bottom"),
                    "engine": f"{eng_fl} + {tpl_obj['short_name']}",
                    "prompt": meta["prompt"],
                    "thumbnail_path": out_thumb_central,
                    "project_thumbnail_path": out_thumb_proj,
                    "final_video_path": final_mp4,
                    "injected_01s": injected_ok,
                })
            else:
                results.append({
                    "ok": False,
                    "pid": pid,
                    "vkey": vk,
                    "char_v": char_v,
                    "error": err_fl,
                })
        ok_cnt = sum(1 for r in results if r.get("ok"))
        return {
            "ok": ok_cnt > 0,
            "pid": pid,
            "total": len(vkeys),
            "success_count": ok_cnt,
            "results": results,
        }

    # Chế độ ChatGPT Image / Grok (:8317)
    results = []
    for vk in vkeys:
        r = generate_thumbnail_for_variant(
            pid=pid,
            vkey=vk,
            provider=provider,
            custom_master_prompt=custom_master_prompt,
            preset_id=preset_id,
            custom_product_info=custom_product_info,
            subject_mode=subject_mode, headline=headline,
            add_text_badge=add_text_badge,
            inject_01s=inject_01s,
        )
        results.append(r)
    ok_cnt = sum(1 for r in results if r.get("ok"))
    return {
        "ok": ok_cnt > 0,
        "pid": pid,
        "total": len(vkeys),
        "success_count": ok_cnt,
        "results": results,
    }


def ensure_project_variant_thumbnail_and_inject(
    pid: str,
    vkey: str = "v1",
    final_video_path: str = "",
    log_cb=None,
    inject_01s: bool = None,
    prefer_existing_ref: bool = True,
    provider: str = "",
) -> dict:
    """
    Generate project AI thumbnail (when `auto_generate_thumbnail=True` in engine settings)
    and inject 0.1s thumbnail intro into `final_video_path` (when `auto_inject_thumbnail_01s=True`).
    Safe for pipeline orchestrators: logs warnings instead of raising on thumbnail failure.
    """
    def _log(msg: str):
        if log_cb:
            try:
                log_cb(msg)
            except Exception:
                pass

    try:
        cfg = load_engine_settings()
    except Exception:
        cfg = {}

    auto_gen = bool(cfg.get("auto_generate_thumbnail", True))
    want_inject = bool(cfg.get("auto_inject_thumbnail_01s", True)) if inject_01s is None else bool(inject_01s)
    dur_01s = float(cfg.get("thumbnail_duration_sec") or 0.1)

    if not auto_gen and not want_inject:
        return {"ok": True, "skipped": True, "reason": "auto_generate_thumbnail=False", "injected_01s": False}

    res = {"ok": False, "pid": pid, "vkey": vkey, "injected_01s": False}
    if auto_gen:
        try:
            _log(f"🖼️ Đang tự động tạo Ảnh Thumbnail AI cho project {pid} ({vkey})...")
            res = generate_thumbnail_for_variant(
                pid=pid,
                vkey=vkey,
                provider=provider or cfg.get("thumbnail_provider", "google_flow"),
                add_text_badge=bool(cfg.get("thumbnail_add_text_badge", False)),
                inject_01s=False,
                prefer_existing_ref=prefer_existing_ref,
            )
            if not res.get("ok"):
                _log(f"⚠️ Tạo Thumbnail AI chưa thành công ({res.get('error', '')}); giữ nguyên video gốc.")
        except Exception as exc:
            _log(f"⚠️ Lỗi tạo Thumbnail AI ({pid}): {exc}")
            res = {"ok": False, "pid": pid, "vkey": vkey, "error": str(exc)}

    pdir = os.path.join(PROJECTS_DIR, pid)
    thumb_path = str(res.get("thumbnail_path") or res.get("project_thumbnail_path") or "").strip()
    if not thumb_path or not os.path.isfile(thumb_path):
        for cand in (
            os.path.join(pdir, "thumbnails", f"{pid}_{vkey}_thumb.jpg"),
            os.path.join(THUMBS_ROOT_DIR, f"{pid}_{vkey}_thumb.jpg"),
        ):
            if os.path.isfile(cand) and os.path.getsize(cand) > 5000:
                thumb_path = cand
                res["thumbnail_path"] = cand
                res["ok"] = True
                break

    target_video = _resolve_final_video_candidate(pid, vkey, pdir, final_video_path or res.get("final_video_path") or "")
    if want_inject and thumb_path and os.path.isfile(thumb_path) and target_video and os.path.isfile(target_video):
        try:
            inj = inject_thumbnail_01s_into_video(target_video, thumb_path, duration_sec=dur_01s)
            res["inject_detail"] = inj
            res["injected_01s"] = bool(inj and inj.get("ok"))
            res["final_video_path"] = target_video
            if res["injected_01s"]:
                _log(f"🎬 Đã tự động ghép Thumbnail {dur_01s:.1f}s vào đầu video: {os.path.basename(target_video)}")
                _persist_thumbnail_to_project_manifests(pid, pdir, thumb_path, dur_01s, True)
            else:
                _log(f"⚠️ Chưa ghép được Thumbnail 0.1s vào video: {(inj or {}).get('error', '')}")
        except Exception as exc:
            _log(f"⚠️ Lỗi ghép Thumbnail 0.1s vào video: {exc}")

    return res
