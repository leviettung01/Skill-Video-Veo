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
    "multi_account_enabled": True,
    "flow_api_workers": 2,
    "max_inflight_per_account": 5,
    "max_total_inflight": 12,
    "submit_delay_sec": 12.0,
    "parallel_products": 2,
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
                rows = json.load(open(acc_path, "r", encoding="utf-8"))
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
            items = json.load(open(acc_path, "r", encoding="utf-8"))
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
                items = json.load(open(acc_path, "r", encoding="utf-8"))
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


def load_engine_settings() -> dict:
    hw = detect_hardware_specs()
    cfg = dict(DEFAULT_ENGINE_SETTINGS)
    cfg["ffmpeg_render_workers"] = hw["recommended"]["ffmpeg_render_workers"]
    cfg["ffmpeg_threads_per_job"] = hw["recommended"]["ffmpeg_threads_per_job"]

    if os.path.isfile(ENGINE_SETTINGS_JSON):
        try:
            saved = json.load(open(ENGINE_SETTINGS_JSON, "r", encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception:
            pass

    if cfg.get("auto_hardware_tuning", True):
        cfg["ffmpeg_render_workers"] = hw["recommended"]["ffmpeg_render_workers"]
        cfg["ffmpeg_threads_per_job"] = hw["recommended"]["ffmpeg_threads_per_job"]

    flow_accs = [a for a in list_available_flow_accounts() if a.get("active", True)]
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
    to_save["flow_api_workers"] = max(1, min(10, int(to_save.get("flow_api_workers") or 2)))
    to_save["max_inflight_per_account"] = max(1, min(15, int(to_save.get("max_inflight_per_account") or 5)))
    to_save["max_total_inflight"] = max(1, min(40, int(to_save.get("max_total_inflight") or 12)))
    to_save["submit_delay_sec"] = max(2.0, min(60.0, float(to_save.get("submit_delay_sec") or 12.0)))
    to_save["parallel_products"] = max(1, min(6, int(to_save.get("parallel_products") or 2)))
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

    with open(ENGINE_SETTINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)

    return {"ok": True, "settings": load_engine_settings()}


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


def get_project_live_progress(pid: str) -> dict:
    """Đọc trạng thái tiến trình đang chạy thực tế + nhật ký trực tiếp của 1 sản phẩm (hỗ trợ Basic #001-#003, Fashion #004, Cooking #005)."""
    fjson_cand = os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid, "fashion_project.json")
    if os.path.isfile(fjson_cand):
        return _get_fashion_project_live_progress(pid, fjson_cand)

    pdir = os.path.join(PROJECTS_DIR, pid)
    if os.path.isfile(os.path.join(pdir, "cooking_manifest.json")):
        return _get_cooking_project_live_progress(pid, pdir)

    if not os.path.isdir(pdir):
        return {"is_running": False, "logs": []}

    log_path = os.path.join(pdir, "pipeline_run.log")
    status_path = os.path.join(pdir, "pipeline_status.json")
    prompts_path = os.path.join(pdir, "prompts.json")

    logs = []
    log_mtime = 0.0
    if os.path.isfile(log_path):
        try:
            log_mtime = os.path.getmtime(log_path)
            raw_lines = open(log_path, "r", encoding="utf-8", errors="replace").read().splitlines()
            logs = [ln for ln in raw_lines if ln.strip()][-80:]
        except Exception:
            pass

    status_data = {}
    if os.path.isfile(status_path):
        try:
            status_data = json.load(open(status_path, "r", encoding="utf-8"))
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
            pdata = json.load(open(prompts_path, "r", encoding="utf-8"))
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
                        pname = json.load(open(p_json, "r", encoding="utf-8")).get("product_name") or entry
                    except Exception:
                        pass
                st["product_name"] = pname
                running.append(st)
                seen_pids.add(entry)

    running.sort(key=lambda x: (0 if x.get("is_running") else 1, -x.get("progress_pct", 0)))
    return running


def stop_running_pipeline(pid: str) -> dict:
    """Dừng tiến trình đang chạy của 1 sản phẩm (hỗ trợ Basic, Thời trang #004, Nấu ăn #005)."""
    fjson_cand = os.path.join(FASHION_STUDIO_PROJECTS_DIR, pid, "fashion_project.json")
    if os.path.isfile(fjson_cand):
        try:
            with open(fjson_cand, "r", encoding="utf-8") as f:
                fproj = json.load(f)
            fproj["status"] = "stopped"
            fproj["status_message"] = "⏹️ Đã tạm dừng tiến trình tạo video thời trang theo yêu cầu người dùng."
            fproj["updated_at"] = time.strftime("%H:%M:%S")
            for sc in fproj.get("scenes") or []:
                if sc.get("status") not in ("completed_1080p", "done"):
                    sc["status"] = "stopped"
                    sc["status_detail"] = "⏹️ Đã tạm dừng"
            with open(fjson_cand, "w", encoding="utf-8") as f:
                json.dump(fproj, f, ensure_ascii=False, indent=2)
            return {"ok": True, "pid": pid, "pid_os": 0, "stopped": True}
        except Exception as exc:
            return {"ok": False, "pid": pid, "error": str(exc)}

    pdir = os.path.join(PROJECTS_DIR, pid)
    if os.path.isfile(os.path.join(pdir, "cooking_manifest.json")):
        try:
            import cooking_storyboard_engine as cooking
            cooking.stop_stage(pid)
            return {"ok": True, "pid": pid, "pid_os": 0, "stopped": True}
        except Exception as exc:
            return {"ok": False, "pid": pid, "error": str(exc)}

    status_path = os.path.join(pdir, "pipeline_status.json")
    killed = False
    pid_os = 0
    if os.path.isfile(status_path):
        try:
            st = json.load(open(status_path, "r", encoding="utf-8"))
            pid_os = int(st.get("pid_os") or 0)
            if pid_os > 0 and is_os_pid_running(pid_os):
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid_os)], capture_output=True)
                killed = True
            st["is_running"] = False
            st["current_step_text"] = "⏹️ Đã tạm dừng theo yêu cầu người dùng."
            json.dump(st, open(status_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
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
    prompts_path = os.path.join(pdir, "prompts.json")
    proj_json_path = os.path.join(pdir, "project.json")
    info_path = os.path.join(pdir, "product_images", "info.json")
    if not os.path.isfile(info_path):
        alt_info = os.path.join(pdir, "info.json")
        if os.path.isfile(alt_info):
            info_path = alt_info
    pdata = json.load(open(prompts_path, "r", encoding="utf-8")) if os.path.isfile(prompts_path) else {}
    idata = json.load(open(info_path, "r", encoding="utf-8")) if os.path.isfile(info_path) else {}
    proj_data = json.load(open(proj_json_path, "r", encoding="utf-8")) if os.path.isfile(proj_json_path) else {}

    proj_prods = proj_data.get("products") or []
    prod_obj = next(
        (
            p for p in proj_prods
            if str(p.get("vkey") or "").lower() == vkey.lower()
            or str(p.get("char_v_code") or "").lower() == vkey.lower()
        ),
        proj_prods[0] if proj_prods else {},
    )
    is_cooking = (proj_data.get("pipeline_kind") == "cooking_storyboard") or (prod_obj.get("pipeline_kind") == "cooking_storyboard")
    is_fashion = bool(proj_data.get("is_fashion_motion_project"))

    prod_name = (
        pdata.get("product_name")
        or idata.get("name")
        or idata.get("title")
        or proj_data.get("dish")
        or proj_data.get("full_product_name")
        or proj_data.get("name")
        or f"Sản phẩm {pid}"
    )
    price_str = str(idata.get("price") or pdata.get("price") or (proj_data.get("price") if not is_fashion else "") or "").strip()
    cat_str = str(
        idata.get("category")
        or pdata.get("category")
        or ("am_thuc" if is_cooking else ("thoi_trang" if is_fashion else ""))
        or ""
    ).strip()
    vcfg = (pdata.get("videos") or {}).get(vkey) or {}
    char_key = vcfg.get("character") or ("nv2" if vkey in ("v2", "v4", "v6") else "nv1")
    hook_title = headline.strip() or vcfg.get("hook_title") or prod_obj.get("hook_label") or prod_name
    if "—" in hook_title:
        hook_title = hook_title.split("—")[-1].strip()
    elif ":" in hook_title:
        hook_title = hook_title.split(":")[-1].strip()
    style_desc = vcfg.get("style") or (
        "Warm cozy overhead kitchen counter lighting, rich food photography"
        if is_cooking
        else "Modern commercial studio with soft warm rim lighting"
    )

    if vkey.lower() in ("pov", "pov_v1"):
        char_v = "pov"
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
        scenes_list = vcfg.get("scenes") or prod_obj.get("scenes") or []
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
    if is_cooking and subject_mode != 'character':
        effective_mode = 'pov'
    elif is_fashion and subject_mode == 'auto':
        effective_mode = 'character'
    else:
        effective_mode = subject_mode if subject_mode in ('pov','character') else resolved_tpl.get('subject_mode','auto')
        if effective_mode == 'auto':
            effective_mode = 'character' if vcfg.get('character') else 'pov'

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
            vc_data = json.load(open(vc_json, "r", encoding="utf-8"))
            c_obj = (vc_data.get("characters") or {}).get(char_key) or {}
            if c_obj.get("appearance_en"):
                char_desc = c_obj["appearance_en"]
            if c_obj.get("ref_image_path") and os.path.isfile(os.path.join(WS_DIR, c_obj["ref_image_path"])):
                char_ref_path = os.path.join(WS_DIR, c_obj["ref_image_path"])
            if not char_uuid and c_obj.get("id"):
                char_uuid = c_obj["id"]
        except Exception:
            pass

    # 3. Tìm Ảnh Ref 1: Ảnh nhân vật cầm sản phẩm (`char_holding_prod_img`) của kịch bản này
    ref_rel = vcfg.get("ref_image") or f"{vkey}-refimg.jpg"
    holding_candidates = [
        os.path.join(pdir, ref_rel),
        os.path.join(pdir, f"{vkey}-refimg.jpg"),
        os.path.join(pdir, f"{char_v}-refimg.jpg"),
        os.path.join(pdir, "refs", f"{vkey}-refimg.jpg"),
        os.path.join(pdir, "refs", f"{char_v}-refimg.jpg"),
    ]
    if is_fashion:
        if prod_obj.get("product_image_path"):
            holding_candidates.append(prod_obj["product_image_path"])
        if prod_obj.get("character_sheet_path"):
            holding_candidates.append(prod_obj["character_sheet_path"])
    # Nếu biến thể hiện tại chưa có refimg thì tìm refimg của cùng nhân vật trong dự án
    for vk_other, vcfg_other in (pdata.get("videos") or {}).items():
        if vcfg.get("character") and vcfg_other.get("character") == char_key:
            holding_candidates.append(os.path.join(pdir, f"{vk_other}-refimg.jpg"))
    if effective_mode == "character" and vcfg.get("character"):
        holding_candidates.append(char_ref_path)
    char_holding_prod_img = next(
        (p for p in holding_candidates if p and os.path.isfile(p) and os.path.getsize(p) > 5000),
        "",
    )

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
        list(prod_obj.get("slide_overlay_image_paths") or [])
        + list(prod_obj.get("all_product_image_paths") or [])
        + list(proj_data.get("all_product_image_paths") or [])
        + ([proj_data.get("primary_product_image_path")] if proj_data.get("primary_product_image_path") else [])
    )
    for ep in extra_proj_imgs:
        if ep and os.path.isfile(ep) and os.path.getsize(ep) > 3000 and ep not in prod_img_paths:
            prod_img_paths.append(ep)
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
        os.path.join(FINAL_VIDEOS_DIR, f'{pid}_final.mp4'),
    ]
    video_path = next((vp for vp in vid_candidates if vp and os.path.isfile(vp) and os.path.getsize(vp) > 50000), "")
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
    if effective_mode == 'character' and not char_holding_prod_img:
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
        "flow_project_id": vcfg.get("project_id") or prod_obj.get("flow_project_id") or get_default_flow_project_id(),
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
    try:
        os.makedirs(THUMBS_ROOT_DIR, exist_ok=True)
        reg_path = os.path.join(THUMBS_ROOT_DIR, ".thumb_injected_registry.json")
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False, indent=2)
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
    if use_nvenc:
        cmd += ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "19"]
    cmd += [*audio_enc_args, "-movflags", "+faststart", tmp_out]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode != 0 or not os.path.isfile(tmp_out) or os.path.getsize(tmp_out) < 20000:
            if os.path.isfile(tmp_out):
                os.remove(tmp_out)
            return {"ok": False, "error": f"FFmpeg lỗi: {(res.stderr or '')[:250]}"}
        os.replace(tmp_out, video_path)
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


def _render_thumbnail_via_chatgpt(meta: dict, out_thumb_proj: str) -> tuple:
    """
    Render ảnh Thumbnail AI bằng ChatGPT Image (`gpt-image-1` qua CLIProxy `:8317`)
    sử dụng bộ Ảnh Ref (Ảnh nhân vật cầm sản phẩm + Ảnh sản phẩm gốc) + Thông tin sản phẩm + Master Prompt.
    """
    import base64
    import urllib.request

    ref_imgs = [p for p in (meta.get("reference_images") or []) if p and os.path.isfile(p)]
    prompt_str = meta["prompt"]

    # 1. Ưu tiên gọi multipart `/v1/images/edits` truyền trực tiếp Ảnh Nhân vật cầm SP + Ảnh SP gốc
    if ref_imgs:
        try:
            boundary = f"----SkillAutoVeoThumbBoundary{int(time.time() * 1000)}"
            body_parts = []

            def _add_field(name: str, val: str):
                body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
                body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
                body_parts.append(f"{val}\r\n".encode("utf-8"))

            _add_field("model", meta.get("image_model", "gpt-image-1"))
            _add_field("prompt", prompt_str)
            _add_field("size", "1024x1536")
            _add_field("n", "1")

            import mimetypes
            for idx, rpath in enumerate(ref_imgs[:4]):
                fname = os.path.basename(rpath)
                raw_img = open(rpath, "rb").read()
                field_name = "image[]" if len(ref_imgs[:4]) > 1 else "image"
                body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
                body_parts.append(
                    f'Content-Disposition: form-data; name="{field_name}"; filename="{fname}"\r\n'
                    f"Content-Type: {mimetypes.guess_type(rpath)[0] or 'image/jpeg'}\r\n\r\n".encode("utf-8")
                )
                body_parts.append(raw_img)
                body_parts.append(b"\r\n")

            body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            body_bytes = b"".join(body_parts)

            req_edit = urllib.request.Request(
                "http://127.0.0.1:8317/v1/images/edits",
                data=body_bytes,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Authorization": "Bearer grok-video-key-001",
                },
                method="POST",
            )
            with urllib.request.urlopen(req_edit, timeout=120) as resp:
                rj = json.loads(resp.read().decode("utf-8"))
                item0 = (rj.get("data") or [{}])[0]
                if item0.get("b64_json"):
                    open(out_thumb_proj, "wb").write(base64.b64decode(item0["b64_json"]))
                    return True, "chatgpt (gpt-image-1 Ref Image Edit)", ""
                if item0.get("url"):
                    with urllib.request.urlopen(item0["url"], timeout=60) as r_dl:
                        open(out_thumb_proj, "wb").write(r_dl.read())
                        return True, "chatgpt (gpt-image-1 Ref Image Edit)", ""
        except Exception as e:
            return False, "", f"Image edit failed; references preserved, no text-only fallback: {e}"
        return False, "", "Image edit returned no image; no text-only fallback"

    # 2. Gọi `/v1/images/generations` với `gpt-image-1` kèm Master Prompt + Thông tin SP
    try:
        payload = json.dumps({
            "model": "gpt-image-1",
            "prompt": prompt_str,
            "size": "1024x1536",
            "n": 1,
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8317/v1/images/generations",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer grok-video-key-001",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            rj = json.loads(resp.read().decode("utf-8"))
            item0 = (rj.get("data") or [{}])[0]
            if item0.get("b64_json"):
                open(out_thumb_proj, "wb").write(base64.b64decode(item0["b64_json"]))
                return True, "chatgpt (gpt-image-1)", ""
            if item0.get("url"):
                with urllib.request.urlopen(item0["url"], timeout=60) as r_dl:
                    open(out_thumb_proj, "wb").write(r_dl.read())
                    return True, "chatgpt (gpt-image-1)", ""
    except Exception as e:
        return False, "", f"ChatGPT Image API (:8317): {e}"
    return False, "", "ChatGPT Image API không trả về dữ liệu ảnh"


def _render_thumbnails_via_google_flow_batch(items: list) -> dict:
    """
    Render hàng loạt hoặc đơn lẻ Ảnh Thumbnail AI 2K (1536x2752) qua Google Flow Nano Banana 2.1 (`BELUGA` / `ogiZ0b` + `SPrCad` 2K).
    Mỗi item trong `items` gồm: `{"meta": meta, "out_thumb_proj": out_thumb_proj}`.
    Sử dụng kết hợp:
      - Ref Image 1 (`char_holding_prod_img` — Ảnh nhân vật cầm sản phẩm)
      - Ref Image 2 (`prod_img_path` — Ảnh sản phẩm gốc)
      - Character UUID (`char_uuid`)
      - Master Prompt (`meta["prompt"]` đã nhúng `product_info`, `hook_title`, `price`)
    """
    outcomes = {}
    if not items:
        return outcomes

    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    if WS_DIR not in sys.path:
        sys.path.insert(0, WS_DIR)

    try:
        import run_all_7_videos_mt as mt
        import google_flow_auth as gfa
        from playwright.sync_api import sync_playwright
    except Exception as e:
        for it in items:
            outcomes[it["meta"]["vkey"]] = (False, "", f"Lỗi nạp module Google Flow: {e}")
        return outcomes

    # Lấy tài khoản Google Flow đang hoạt động và đọc Cookie từ file đã đồng bộ (không khoá Chrome đang mở)
    flow_accs = [a for a in list_available_flow_accounts() if a.get("active", True)]
    if not flow_accs:
        for it in items:
            outcomes[it["meta"]["vkey"]] = (False, "", "Chưa có tài khoản Google Flow nào đang hoạt động. Vui lòng đăng nhập tài khoản trong tab Tài Khoản!")
        return outcomes
    prof_name = flow_accs[0]["profile_name"]
    shared_dir = mt.gvt._resolve_flow_shared_dir(prof_name)
    raw_cookies = []
    try:
        _, snap_path = gfa.profile_paths(shared_dir, prof_name)
        snap_obj = gfa.read_json(snap_path, default=None)
        if isinstance(snap_obj, dict):
            raw_cookies = snap_obj.get("cookies") or []
        elif isinstance(snap_obj, list):
            raw_cookies = snap_obj
    except Exception:
        raw_cookies = []
    if not raw_cookies:
        for alt_dir in (
            os.path.join(WS_DIR, "cookies", f"{prof_name}.json"),
            os.path.join(WS_DIR, "data", "google_flow_grok", "cookies", f"{prof_name}.json"),
        ):
            if os.path.isfile(alt_dir):
                try:
                    c_obj = json.load(open(alt_dir, "r", encoding="utf-8"))
                    raw_cookies = c_obj.get("cookies", []) if isinstance(c_obj, dict) else c_obj
                    if raw_cookies:
                        break
                except Exception:
                    pass
    if not raw_cookies:
        try:
            import character_library_manager as _clm_th
            raw_cookies = _clm_th._load_clean_flow_cookies(prof_name) or _clm_th._load_clean_flow_cookies("")
        except Exception:
            pass

    try:
        _headless_thumb = os.environ.get("FLOW_SHOW_BROWSER", "").strip() != "1"
        _launch_args = ["--disable-blink-features=AutomationControlled", "--window-size=1280,800", "--mute-audio"]
        with sync_playwright() as pw:
            if not raw_cookies:
                pdir_prof, _ = gfa.profile_paths(shared_dir, prof_name)
                p_ctx = pw.chromium.launch_persistent_context(
                    str(pdir_prof),
                    channel="chrome",
                    headless=_headless_thumb,
                    args=_launch_args,
                )
                raw_cookies = p_ctx.cookies(["https://flow.google.com", "https://google.com", "https://www.google.com", "https://accounts.google.com"])
                p_ctx.close()

            clean_cookies = [c for c in (raw_cookies or []) if "GRECAPTCHA" not in str(c.get("name", "")).upper()]
            if not clean_cookies:
                for it in items:
                    outcomes[it["meta"]["vkey"]] = (False, "", f"Tài khoản Google Flow '{prof_name}' chưa có Cookie. Hãy đăng nhập 1 lần ở mục Tài Khoản & Flow!")
                return outcomes

            cookie_map = {c["name"]: c["value"] for c in clean_cookies if c.get("name") and c.get("value")}
            cookie_hdr = "; ".join(f"{k}={v}" for k, v in cookie_map.items())

            browser = pw.chromium.launch(
                channel="chrome",
                headless=_headless_thumb,
                args=_launch_args,
            )
            ctx = browser.new_context()
            ctx.add_init_script(mt.gvt._FLOW_HIJACK_BYPASS_JS)
            ctx.add_cookies(clean_cookies)
            pg = ctx.new_page()

            cur_proj_id = None
            wz = None
            dl_headers = None
            uploaded_img_cache = {}  # (project_id, abs_img_path) -> media_uuid

            for it in items:
                meta = it["meta"]
                vk = meta["vkey"]
                out_thumb_proj = it["out_thumb_proj"]
                project_id = meta.get("flow_project_id") or get_default_flow_project_id(prof_name)
                if not project_id:
                    outcomes[vk] = (False, "", f"Tài khoản '{prof_name}' chưa có Google Flow Project ID. Vui lòng thiết lập Project ID trong tab Tài Khoản!")
                    continue

                try:
                    if cur_proj_id != project_id or wz is None:
                        pg.goto(f"https://flow.google.com/project/{project_id}", wait_until="domcontentloaded", timeout=45000)
                        pg.evaluate(mt.gvt._FLOW_HIJACK_BYPASS_JS)
                        pg.wait_for_function(
                            "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise",
                            timeout=35000,
                        )
                        pg.wait_for_timeout(1000)
                        wz = pg.evaluate(
                            """() => {
                                const w = window.WIZ_global_data || {};
                                return {
                                    at: w.SNlM0e || '',
                                    bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261030.00_p2',
                                    fsid: w.FdrFJe || '',
                                    ua: navigator.userAgent,
                                };
                            }"""
                        )
                        dl_headers = {"Cookie": cookie_hdr, "Referer": "https://flow.google.com/", "User-Agent": wz["ua"]}
                        cur_proj_id = project_id

                    # Upload cả 2 Ảnh Reference: (1) Ảnh nhân vật cầm sản phẩm + (2) Ảnh sản phẩm gốc
                    ref_uuids = []
                    for ref_path in (meta.get("reference_images") or [])[:4]:
                        if not ref_path or not os.path.isfile(ref_path):
                            continue
                        cache_key = (project_id, os.path.abspath(ref_path))
                        u_id = uploaded_img_cache.get(cache_key)
                        if not u_id:
                            ok_u, u_id, err_u = mt.upload_single_product_ref_in_page(pg, wz, project_id, ref_path)
                            if ok_u and u_id:
                                uploaded_img_cache[cache_key] = u_id
                        if not u_id:
                            raise RuntimeError('Không upload được ảnh tham chiếu: ' + os.path.basename(ref_path))
                        if u_id and u_id not in ref_uuids:
                            ref_uuids.append(u_id)

                    task = {
                        "pid": meta["pid"],
                        "v_key": f"{vk}_thumb",
                        "project_id": project_id,
                        "char_id": meta.get("char_uuid") or "",
                        "prod_uuids": ref_uuids,
                        "allow_multi_refs": True,
                        "prompt_str": meta["prompt"],
                        "out_file": out_thumb_proj,
                    }
                    ok_gen, gen_uuid, err_gen = mt.generate_variant_ref_image_in_page(pg, wz, cookie_hdr, dl_headers, task)
                    if ok_gen and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000:
                        outcomes[vk] = (True, f"google_flow (Nano Banana 2.1 2K • {len(ref_uuids)} Ref Images)", "")
                    else:
                        outcomes[vk] = (False, "", err_gen or "Nano Banana 2.1 không trả về ảnh Thumbnail")
                except Exception as ex_item:
                    outcomes[vk] = (False, "", f"Google Flow Render ({vk}): {ex_item}")

            try:
                ctx.close()
                browser.close()
            except Exception:
                pass
    except Exception as e_outer:
        for it in items:
            vk = it["meta"]["vkey"]
            if vk not in outcomes:
                outcomes[vk] = (False, "", f"Google Flow Browser Error: {e_outer}")

    return outcomes


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
    apply_template_only = False
    prefer_existing_ref = False
    cfg = load_engine_settings()
    prov = (provider or cfg.get("thumbnail_provider") or "google_flow").strip().lower()
    if add_text_badge is None:
        add_text_badge = bool(cfg.get("thumbnail_add_text_badge", False))
    if inject_01s is None:
        inject_01s = False
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
        if os.path.isfile(raw2k_proj) and os.path.getsize(raw2k_proj) > 10000:
            shutil.copy2(raw2k_proj, out_thumb_proj)
            generated_ok = True
            used_engine = f"Template Compositor ({tpl_obj['short_name']})"
        elif os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000:
            generated_ok = True
            used_engine = f"google_flow 2K + {tpl_obj['short_name']}"
        elif os.path.isfile(out_thumb_central) and os.path.getsize(out_thumb_central) > 10000:
            shutil.copy2(out_thumb_central, out_thumb_proj)
            generated_ok = True
            used_engine = f"google_flow 2K + {tpl_obj['short_name']}"
        elif apply_template_only and meta.get("char_holding_prod_img") and os.path.isfile(meta["char_holding_prod_img"]):
            shutil.copy2(meta["char_holding_prod_img"], out_thumb_proj)
            generated_ok = True
            used_engine = f"Ref 2K + {tpl_obj['short_name']}"

    # 1. Nếu chưa có sẵn (hoặc người dùng yêu cầu Render AI 2K mới hoàn toàn)
    if not generated_ok:
        if prov == 'grok':
            meta['image_model'] = 'grok-imagine-image'
            ok, engine, error = _render_thumbnail_via_chatgpt(meta, out_thumb_proj)
            if not ok:
                return {'ok': False, 'error': error, 'provider': 'grok'}
            generated_ok = fresh_ai_rendered = True
            used_engine = 'grok-imagine-image'
        elif prov in ("chatgpt", "openai", "gpt"):
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
            if ok_fl and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000:
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
    cooking_mf = os.path.join(pdir, "cooking_manifest.json")
    if os.path.isfile(cooking_mf):
        try:
            mdata = json.load(open(cooking_mf, "r", encoding="utf-8"))
            mdata["thumbnail_path"] = out_thumb_central
            with open(cooking_mf, "w", encoding="utf-8") as mf_out:
                json.dump(mdata, mf_out, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # Nếu Video Final đã có sẵn và bật inject_01s -> ghép ngay 0.1s vào đầu Video Final!
    final_mp4 = meta.get("final_video_path") or os.path.join(FINAL_VIDEOS_DIR, f"{pid}_{char_v}.mp4")
    if not os.path.isfile(final_mp4):
        alt_final = os.path.join(FINAL_VIDEOS_DIR, f"{pid}_final.mp4")
        if os.path.isfile(alt_final):
            final_mp4 = alt_final
    injected_info = None
    if inject_01s and os.path.isfile(final_mp4) and os.path.getsize(final_mp4) > 50000:
        injected_info = inject_thumbnail_01s_into_video(final_mp4, out_thumb_central, duration_sec=dur_01s)

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
        "injected_01s": bool(injected_info and injected_info.get("ok")),
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
    Render Ảnh Thumbnail AI + Ghép cụm Ảnh Sản Phẩm Thực Tế & ghép 0.1s đầu video cho toàn bộ các video của 1 sản phẩm.
    - Nếu `apply_template_only=True`: Áp dụng ngay Template Thumbnail (ghép 3 ảnh SP thực tế & cập nhật 0.1s) lên toàn bộ ảnh 2K hiện có siêu tốc!
    - Khi dùng Google Flow Nano Banana 2.1 2K, tái sử dụng 1 phiên trình duyệt duy nhất để upload Ảnh Ref & render toàn bộ các biến thể!
    """
    pdir = os.path.join(PROJECTS_DIR, pid)
    prompts_path = os.path.join(pdir, "prompts.json")
    proj_json_path = os.path.join(pdir, "project.json")
    vkeys = []
    if os.path.isfile(prompts_path):
        pdata = json.load(open(prompts_path, "r", encoding="utf-8"))
        vkeys = list((pdata.get("videos") or {}).keys())
    elif os.path.isfile(proj_json_path):
        proj_data = json.load(open(proj_json_path, "r", encoding="utf-8"))
        vkeys = [str(p.get("vkey") or p.get("char_v_code") or "v1") for p in (proj_data.get("products") or [])]
    if not vkeys:
        return {"ok": False, "error": f"Sản phẩm {pid} chưa có kịch bản (prompts.json / project.json). Hãy bấm Tạo Kịch Bản trước!"}

    cfg = load_engine_settings()
    prov = (provider or cfg.get("thumbnail_provider") or "google_flow").strip().lower()
    if add_text_badge is None:
        add_text_badge = bool(cfg.get("thumbnail_add_text_badge", False))
    if inject_01s is None:
        inject_01s = False
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
            if ok_fl and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000:
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
                cooking_mf = os.path.join(pdir, "cooking_manifest.json")
                if os.path.isfile(cooking_mf):
                    try:
                        mdata = json.load(open(cooking_mf, "r", encoding="utf-8"))
                        mdata["thumbnail_path"] = out_thumb_central
                        with open(cooking_mf, "w", encoding="utf-8") as mf_out:
                            json.dump(mdata, mf_out, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                final_mp4 = meta.get("final_video_path") or os.path.join(FINAL_VIDEOS_DIR, f"{pid}_{char_v}.mp4")
                if not os.path.isfile(final_mp4):
                    alt_final = os.path.join(FINAL_VIDEOS_DIR, f"{pid}_final.mp4")
                    if os.path.isfile(alt_final):
                        final_mp4 = alt_final
                injected_info = None
                if inject_01s and os.path.isfile(final_mp4) and os.path.getsize(final_mp4) > 50000:
                    injected_info = inject_thumbnail_01s_into_video(final_mp4, out_thumb_central, duration_sec=dur_01s)
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
                    "injected_01s": bool(injected_info and injected_info.get("ok")),
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

    # Chế độ ChatGPT Image
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
