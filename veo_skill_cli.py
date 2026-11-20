# -*- coding: utf-8 -*-
"""
Skill Video Veo — Core Multi-Threaded Engine & Agent CLI
========================================================
AI Agent (Antigravity / Codex) đóng vai trò là BỘ NÃO:
1. Đọc Role Skill (.MD) và danh sách sản phẩm (ảnh + thông tin sản phẩm).
2. Tự biên tập Kịch bản & Prompt chi tiết cho từng phân cảnh (image_prompt, video_prompt).
3. Truyền trực tiếp danh sách Prompt xuống Engine này qua CLI hoặc REST API.
4. Engine thực thi ĐA LUỒNG tốc độ cao:
   - Tạo ảnh các phân cảnh song song (Google Flow / Grok) có tham chiếu ảnh sản phẩm gốc.
   - Tạo video I2V song song từ ảnh từng phân cảnh (Veo 3.1 / Grok).
   - Tự động ghép nối (FFmpeg Concat) các phân cảnh thành Video Final hoàn chỉnh (.mp4).
"""

import argparse
import asyncio
import concurrent.futures
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_DIR = Path(__file__).resolve().parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

PROJECTS_DIR = SKILL_DIR / "projects"
ROLE_SKILLS_LOCAL_DIR = SKILL_DIR / "role_skills"
SKILLS_DOCS_DIR = SKILL_DIR / "skills"
PROJECTS_INDEX_FILE = PROJECTS_DIR / "projects_index.json"
VOICES_CATALOG_FILE = SKILL_DIR / "flow_final_pipeline" / "voices_and_characters.json"

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
ROLE_SKILLS_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DOCS_DIR.mkdir(parents=True, exist_ok=True)


def load_voices_and_characters() -> Dict[str, Any]:
    """Đọc danh sách Nhân vật cố định (Saved Characters) và Giọng nói (Custom + Built-in Voices) của Google Flow."""
    if VOICES_CATALOG_FILE.is_file():
        try:
            return json.loads(VOICES_CATALOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"saved_characters": [], "custom_voices": [], "builtin_voices": []}


def resolve_character_and_voice(
    character_key_or_id: str = "",
    voice_key_or_id: str = "",
) -> Dict[str, str]:
    """Ánh xạ tên/key/ID nhân vật ('nv1', 'nv2', UUID) và giọng nói sang (character_id, voice_id, project_id)."""
    cat = load_voices_and_characters()
    chars = cat.get("saved_characters", [])
    custom_voices = cat.get("custom_voices", [])
    builtin_voices = cat.get("builtin_voices", [])

    char_id = ""
    proj_id = ""
    default_voice_id = ""
    ck = (character_key_or_id or "").strip().lower()
    if ck:
        for c in chars:
            if ck in (
                str(c.get("key", "")).lower(),
                str(c.get("character_id", "")).lower(),
                str(c.get("name", "")).lower(),
            ):
                char_id = c.get("character_id", "")
                proj_id = c.get("project_id", "")
                default_voice_id = c.get("default_voice_id", "")
                break
        if not char_id and len(character_key_or_id.strip()) >= 32:
            char_id = character_key_or_id.strip()

    voice_id = ""
    vk = (voice_key_or_id or "").strip().lower()
    if vk:
        for v in custom_voices:
            if vk in (str(v.get("voice_id", "")).lower(), str(v.get("name", "")).lower()):
                voice_id = v.get("voice_id", "")
                if not proj_id and v.get("project_id"):
                    proj_id = v.get("project_id", "")
                break
        if not voice_id:
            for bv in builtin_voices:
                if vk in (str(bv.get("voice_id", "")).lower(), str(bv.get("name", "")).lower()):
                    voice_id = bv.get("voice_id", "")
                    break
        if not voice_id:
            voice_id = voice_key_or_id.strip()
    elif default_voice_id:
        voice_id = default_voice_id

    return {
        "character_id": char_id,
        "voice_id": voice_id,
        "project_id": proj_id,
    }


def sync_role_skills_dirs() -> List[Dict[str, Any]]:
    """Quét và đồng bộ các file Role Skill (.MD) bên trong thư mục ./role_skills của Skill Video Veo."""
    dirs = [
        ROLE_SKILLS_LOCAL_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    latest_files: Dict[str, Path] = {}
    for d in dirs:
        for ext in ("*.md", "*.MD"):
            for f in d.glob(ext):
                key = f.name.lower()
                if key not in latest_files or f.stat().st_mtime > latest_files[key].stat().st_mtime:
                    latest_files[key] = f

    results = []
    for key, src_path in sorted(latest_files.items()):
        results.append({
            "filename": src_path.name,
            "path": str((ROLE_SKILLS_LOCAL_DIR / src_path.name).resolve()),
            "size": src_path.stat().st_size,
            "updated_at": datetime.fromtimestamp(src_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return results


def read_role_skill(filename: str) -> str:
    sync_role_skills_dirs()
    candidates = [
        ROLE_SKILLS_LOCAL_DIR / filename,
        SKILLS_DOCS_DIR / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c.read_text(encoding="utf-8")
    target_lower = filename.lower()
    for f in ROLE_SKILLS_LOCAL_DIR.iterdir():
        if f.name.lower() == target_lower or f.stem.lower() == target_lower:
            return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Không tìm thấy Role Skill: {filename}")


def save_role_skill(filename: str, content: str) -> str:
    if not filename.lower().endswith(".md"):
        filename += ".MD"
    ROLE_SKILLS_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    p = ROLE_SKILLS_LOCAL_DIR / filename
    p.write_text(content, encoding="utf-8")
    return str(p.resolve())


def delete_role_skill(filename: str) -> bool:
    p = ROLE_SKILLS_LOCAL_DIR / filename
    if p.is_file():
        p.unlink()
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  QUẢN LÝ DỰ ÁN & SẢN PHẨM HÀNG LOẠT (PROJECT & BULK PRODUCT STORE)
# ═══════════════════════════════════════════════════════════════════════════

_STORE_LOCK = threading.RLock()
_STOPPED_PROJECTS_LOCK = threading.Lock()
_STOPPED_PROJECT_IDS: set[str] = set()
_ACTIVE_PROJECT_BATCHES: set[str] = set()


def request_stop_project(project_id: str) -> bool:
    pid = str(project_id or "").strip()
    if not pid:
        return False
    with _STOPPED_PROJECTS_LOCK:
        was_active = pid in _ACTIVE_PROJECT_BATCHES
        _STOPPED_PROJECT_IDS.add(pid)
    return was_active


def is_project_stopped(project_id: str) -> bool:
    with _STOPPED_PROJECTS_LOCK:
        return str(project_id or "").strip() in _STOPPED_PROJECT_IDS


def _atomic_write_store_json(target: Path, payload_obj: Any) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload_obj, indent=2, ensure_ascii=False)
    tmp = target.parent / f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        tmp.write_text(text, encoding="utf-8")
        for attempt in range(7):
            try:
                os.replace(str(tmp), str(target))
                return
            except OSError:
                time.sleep(0.02 * (attempt + 1))
        target.write_text(text, encoding="utf-8")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def _load_projects_index() -> List[Dict[str, Any]]:
    with _STORE_LOCK:
        if not PROJECTS_INDEX_FILE.is_file():
            return []
        for attempt in range(3):
            try:
                return json.loads(PROJECTS_INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:
                if attempt < 2:
                    time.sleep(0.03)
        return []


def _save_projects_index(projects: List[Dict[str, Any]]) -> None:
    with _STORE_LOCK:
        _atomic_write_store_json(PROJECTS_INDEX_FILE, projects)


def get_project_dir(project_id: str) -> Path:
    d = PROJECTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_project_file(project_id: str) -> Path:
    return get_project_dir(project_id) / "project.json"


def _safe_read_project_json(pfile: Path) -> Optional[Dict[str, Any]]:
    for attempt in range(3):
        try:
            raw = pfile.read_text(encoding="utf-8").strip()
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        if attempt < 2:
            time.sleep(0.05)
    return None


def load_project(project_id_or_name: str) -> Optional[Dict[str, Any]]:
    with _STORE_LOCK:
        direct_file = get_project_file(project_id_or_name)
        if direct_file.is_file():
            res = _safe_read_project_json(direct_file)
            if res is not None:
                return res
        # Tìm theo tên hoặc ID gần đúng
        idx = _load_projects_index()
        q = project_id_or_name.strip().lower()
        for item in idx:
            if item["id"].lower() == q or item["name"].lower() == q or item["id"].lower().startswith(q):
                f = get_project_file(item["id"])
                if f.is_file():
                    res = _safe_read_project_json(f)
                    if res is not None:
                        return res
        return None


def save_project(proj: Dict[str, Any]) -> Dict[str, Any]:
    with _STORE_LOCK:
        proj["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pfile = get_project_file(proj["id"])
        _atomic_write_store_json(pfile, proj)

        idx = _load_projects_index()
        products = proj.get("products", [])
        summary = {
            "id": proj["id"],
            "name": proj["name"],
            "role_skill_file": proj.get("role_skill_file", ""),
            "created_at": proj.get("created_at", ""),
            "updated_at": proj["updated_at"],
            "total_products": len(products),
            "done_products": sum(1 for p in products if p.get("status") == "done"),
            "running_products": sum(1 for p in products if p.get("status") in ("scripting", "img_gen", "vid_gen", "assembling")),
            "failed_products": sum(1 for p in products if p.get("status") == "failed"),
            "settings": proj.get("settings", {}),
        }
        replaced = False
        for i, existing in enumerate(idx):
            if existing["id"] == proj["id"]:
                idx[i] = summary
                replaced = True
                break
        if not replaced:
            idx.insert(0, summary)
        _save_projects_index(idx)
        return proj


def create_or_get_project(
    name: str,
    role_skill_file: str = "DoAnVat.MD",
    img_model: str = "Nano Banana 2",
    vid_model: str = "Veo 3.1 - Fast",
    aspect: str = "9:16",
    num_scenes: int = 4,
    seconds_per_scene: int = 8,
    video_resolution: str = "720p",
    max_workers: int = 3,
) -> Dict[str, Any]:
    existing = load_project(name)
    if existing:
        return existing

    proj_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    proj = {
        "id": proj_id,
        "name": name,
        "role_skill_file": role_skill_file,
        "created_at": now_str,
        "updated_at": now_str,
        "settings": {
            "role_skill_file": role_skill_file,
            "img_model": img_model,
            "vid_model": vid_model,
            "aspect": aspect,
            "num_scenes": int(num_scenes),
            "seconds_per_scene": int(seconds_per_scene),
            "video_resolution": video_resolution,
            "max_workers": int(max_workers),
        },
        "products": [],
        "logs": [f"[{now_str}] Đã khởi tạo dự án '{name}' với Role Skill '{role_skill_file}'."],
    }
    return save_project(proj)


def append_project_log(project_id: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, file=sys.stderr, flush=True)
    with _STORE_LOCK:
        proj = load_project(project_id)
        if not proj:
            return
        logs = proj.setdefault("logs", [])
        logs.append(line)
        if len(logs) > 500:
            proj["logs"] = logs[-500:]
        save_project(proj)


def import_products_to_project(
    project_id_or_name: str,
    items: List[Dict[str, Any]],
    default_role_skill: str = "",
) -> Dict[str, Any]:
    """
    Thêm danh sách sản phẩm vào dự án.
    Mỗi item có thể gồm:
      - product_name: Tên sản phẩm
      - product_info: Mô tả / USP / ghi chú sản phẩm
      - product_image_path: Đường dẫn file ảnh sản phẩm gốc
      - role_skill_file: (Tùy chọn) Ghi đè Role Skill riêng cho sản phẩm này
      - num_scenes: (Tùy chọn) Số cảnh
      - scenes: (Tùy chọn) Nếu AI Agent đã viết sẵn kịch bản phân cảnh thì truyền luôn!
    """
    proj = load_project(project_id_or_name)
    if not proj:
        proj = create_or_get_project(project_id_or_name, role_skill_file=default_role_skill or "DoAnVat.MD")

    settings = proj.get("settings", {})
    proj_dir = get_project_dir(proj["id"])
    added = 0

    for raw in items:
        prod_id = raw.get("id") or f"prod_{uuid.uuid4().hex[:8]}"
        img_path = str(raw.get("product_image_path") or raw.get("image_path") or "").strip()
        prod_name = str(raw.get("product_name") or raw.get("name") or "").strip()
        if not prod_name and img_path:
            prod_name = Path(img_path).stem.replace("_", " ").replace("-", " ")
        if not prod_name:
            prod_name = f"Sản phẩm #{len(proj['products']) + 1}"

        prod_info = str(raw.get("product_info") or raw.get("info") or prod_name).strip()
        # Nếu cùng thư mục ảnh có file .txt cùng tên thì tự động đọc làm thông tin sản phẩm
        if img_path and Path(img_path).is_file():
            txt_companion = Path(img_path).with_suffix(".txt")
            if txt_companion.is_file() and prod_info == prod_name:
                try:
                    prod_info = f"{prod_name} — {txt_companion.read_text(encoding='utf-8').strip()}"
                except Exception:
                    pass

        out_dir = proj_dir / prod_id
        out_dir.mkdir(parents=True, exist_ok=True)

        # Copy ảnh sản phẩm gốc vào thư mục dự án để hiển thị trên Web UI dễ dàng
        local_ref_img = img_path
        if img_path and Path(img_path).is_file():
            dst_img = out_dir / f"product_ref{Path(img_path).suffix.lower()}"
            try:
                if not dst_img.exists():
                    shutil.copy2(img_path, dst_img)
                local_ref_img = str(dst_img.resolve())
            except Exception:
                local_ref_img = str(Path(img_path).resolve())

        scenes_in = raw.get("scenes") or []
        formatted_scenes = []
        for idx, s in enumerate(scenes_in):
            formatted_scenes.append({
                "scene_number": int(s.get("scene_number", idx + 1)),
                "scene_title": str(s.get("scene_title") or s.get("title") or f"Cảnh {idx + 1}"),
                "scene_description": str(s.get("scene_description") or s.get("description") or ""),
                "image_prompt": str(s.get("image_prompt") or s.get("img_prompt") or ""),
                "video_prompt": str(s.get("video_prompt") or s.get("vid_prompt") or ""),
                "image_path": str(s.get("image_path") or ""),
                "video_path": str(s.get("video_path") or ""),
                "status": "pending",
                "error_msg": "",
            })

        status = "queued" if formatted_scenes else "waiting_agent"
        resolved_cv = resolve_character_and_voice(
            str(raw.get("character_id") or raw.get("character") or settings.get("character_id", "")),
            str(raw.get("voice_id") or raw.get("voice") or settings.get("voice_id", "")),
        )
        prod_entry = {
            "id": prod_id,
            "product_name": prod_name,
            "product_info": prod_info,
            "product_image_path": local_ref_img,
            "role_skill_file": raw.get("role_skill_file") or default_role_skill or settings.get("role_skill_file", "DoAnVat.MD"),
            "img_model": raw.get("img_model") or settings.get("img_model", "Nano Banana 2"),
            "vid_model": raw.get("vid_model") or settings.get("vid_model", "Veo 3.1 - Fast"),
            "aspect": raw.get("aspect") or settings.get("aspect", "9:16"),
            "num_scenes": int(raw.get("num_scenes") or settings.get("num_scenes", 4)),
            "seconds_per_scene": int(raw.get("seconds_per_scene") or settings.get("seconds_per_scene", 8)),
            "video_resolution": raw.get("video_resolution") or settings.get("video_resolution", "720p"),
            "character_id": resolved_cv["character_id"],
            "voice_id": resolved_cv["voice_id"],
            "flow_project_id": str(raw.get("flow_project_id") or resolved_cv["project_id"] or ""),
            "output_dir": str(out_dir.resolve()),
            "status": status,
            "error_msg": "",
            "final_video_path": "",
            "scenes": formatted_scenes,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        proj["products"].append(prod_entry)
        added += 1

    save_project(proj)
    append_project_log(proj["id"], f"➕ Đã thêm {added} sản phẩm vào dự án '{proj['name']}'.")
    return proj


def import_products_from_folder(
    project_id_or_name: str,
    folder_path: str,
    role_skill_file: str = "DoAnVat.MD",
    **project_kwargs,
) -> Dict[str, Any]:
    """Quét toàn bộ ảnh trong 1 thư mục (hoặc file manifest.json / products.csv) để tạo danh sách sản phẩm hàng loạt."""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Thư mục không tồn tại: {folder_path}")

    proj = load_project(project_id_or_name)
    if not proj:
        proj = create_or_get_project(project_id_or_name, role_skill_file=role_skill_file, **project_kwargs)

    exts = {".jpg", ".jpeg", ".png", ".webp"}
    img_files = sorted([f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in exts])
    items = []
    for img in img_files:
        items.append({
            "product_name": img.stem.replace("_", " ").replace("-", " "),
            "product_image_path": str(img.resolve()),
            "role_skill_file": role_skill_file,
        })
    return import_products_to_project(proj["id"], items, default_role_skill=role_skill_file)


def submit_agent_prompts(
    project_id_or_name: str,
    products_prompts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Nhận kịch bản & prompt phân cảnh do AI Agent (Antigravity/Codex) sinh ra và gắn vào từng sản phẩm.
    Mỗi phần tử trong `products_prompts` có thể khớp theo `product_id` hoặc `product_name` (hoặc tạo mới nếu chưa có).
    """
    proj = load_project(project_id_or_name)
    if not proj:
        proj = create_or_get_project(project_id_or_name)

    existing_by_id = {p["id"]: p for p in proj.get("products", [])}
    existing_by_name = {p["product_name"].lower(): p for p in proj.get("products", [])}

    updated_count = 0
    new_items = []

    for item in products_prompts:
        pid = item.get("product_id") or item.get("id") or ""
        pname = (item.get("product_name") or item.get("name") or "").strip()
        target = existing_by_id.get(pid) or (existing_by_name.get(pname.lower()) if pname else None)

        scenes_in = item.get("scenes") or []
        formatted_scenes = []
        for idx, s in enumerate(scenes_in):
            formatted_scenes.append({
                "scene_number": int(s.get("scene_number", idx + 1)),
                "scene_title": str(s.get("scene_title") or s.get("title") or f"Cảnh {idx + 1}"),
                "scene_description": str(s.get("scene_description") or s.get("description") or ""),
                "image_prompt": str(s.get("image_prompt") or s.get("img_prompt") or ""),
                "video_prompt": str(s.get("video_prompt") or s.get("vid_prompt") or ""),
                "image_path": "",
                "video_path": "",
                "status": "pending",
                "error_msg": "",
            })

        if target:
            target["scenes"] = formatted_scenes
            target["num_scenes"] = len(formatted_scenes) or target.get("num_scenes", 4)
            if item.get("product_info"):
                target["product_info"] = item["product_info"]
            if item.get("role_skill_file"):
                target["role_skill_file"] = item["role_skill_file"]
            if item.get("img_model"):
                target["img_model"] = item["img_model"]
            if item.get("vid_model"):
                target["vid_model"] = item["vid_model"]
            if item.get("aspect"):
                target["aspect"] = item["aspect"]
            if item.get("character_id") or item.get("character") or item.get("voice_id") or item.get("voice"):
                resolved_cv = resolve_character_and_voice(
                    str(item.get("character_id") or item.get("character") or target.get("character_id", "")),
                    str(item.get("voice_id") or item.get("voice") or target.get("voice_id", "")),
                )
                target["character_id"] = resolved_cv["character_id"]
                target["voice_id"] = resolved_cv["voice_id"]
                if resolved_cv["project_id"]:
                    target["flow_project_id"] = resolved_cv["project_id"]
            target["status"] = "queued"
            target["error_msg"] = ""
            # Lưu file prompts_summary.json vào output_dir của sản phẩm
            out_dir = Path(target["output_dir"])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "prompts_summary.json").write_text(
                json.dumps(target, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            updated_count += 1
        else:
            new_items.append(item)

    if new_items:
        proj = import_products_to_project(proj["id"], new_items)

    proj = save_project(proj)
    append_project_log(
        proj["id"],
        f"🧠 AI Agent đã truyền kịch bản & prompt cho {updated_count + len(new_items)} sản phẩm (Sẵn sàng chạy đa luồng).",
    )
    return proj


# ═══════════════════════════════════════════════════════════════════════════
#  MULTI-THREADED EXECUTION ENGINE (TẠO ẢNH -> TẠO VIDEO I2V -> GHÉP FINAL)
# ═══════════════════════════════════════════════════════════════════════════

class MultiThreadSkillRunner:
    """
    Thực thi đa luồng cho toàn bộ sản phẩm trong Dự án bằng cách tận dụng
    trực tiếp lõi Google Flow + CaptchaBridge + CLIProxy + FFmpeg của grok_video_tool.py.
    """

    FLOW_SUBMIT_DELAY_SEC = float(os.environ.get("FLOW_SUBMIT_DELAY_SEC", "4.5") or "4.5")
    FLOW_GLOBAL_STAGGER_SEC = float(os.environ.get("FLOW_GLOBAL_STAGGER_SEC", "0.7") or "0.7")

    def __init__(self, captcha_bridge=None):
        import grok_video_tool as gvt
        self.gvt = gvt
        self.captcha_bridge = captcha_bridge
        self._rr_lock = threading.Lock()
        self._rr_idx = 0
        self._flow_submit_lock = threading.Lock()
        self._last_flow_submit_ts = 0.0
        self._account_submit_ts: Dict[str, float] = {}
        self._account_cooldown_until: Dict[str, float] = {}
        self._bg_heal_inflight: set = set()

    def _get_flow_limits(self) -> Dict[str, Any]:
        """Lấy cấu hình luồng thực thi mới nhất (Auto/Custom) từ engine_settings_manager."""
        defaults = {
            "flow_api_workers": 6,
            "max_inflight_per_account": 5,
            "max_total_inflight": 10,
            "submit_delay_sec": float(self.FLOW_SUBMIT_DELAY_SEC),
            "global_submit_stagger_sec": float(self.FLOW_GLOBAL_STAGGER_SEC),
            "parallel_products": 4,
            "upscale_download_workers": 6,
            "extension_pool_tabs": 4,
        }
        try:
            scripts_dir = str(SKILL_DIR / "flow_final_pipeline" / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            import engine_settings_manager as _esm_lim
            eff = _esm_lim.get_effective_flow_concurrency()
            if isinstance(eff, dict):
                defaults.update(eff)
        except Exception:
            pass
        if "FLOW_SUBMIT_DELAY_SEC" in self.__dict__:
            defaults["submit_delay_sec"] = float(self.__dict__["FLOW_SUBMIT_DELAY_SEC"])
        elif os.environ.get("FLOW_SUBMIT_DELAY_SEC", "").strip():
            defaults["submit_delay_sec"] = float(os.environ["FLOW_SUBMIT_DELAY_SEC"])
        if "FLOW_GLOBAL_STAGGER_SEC" in self.__dict__:
            defaults["global_submit_stagger_sec"] = float(self.__dict__["FLOW_GLOBAL_STAGGER_SEC"])
        elif os.environ.get("FLOW_GLOBAL_STAGGER_SEC", "").strip():
            defaults["global_submit_stagger_sec"] = float(os.environ["FLOW_GLOBAL_STAGGER_SEC"])
        try:
            if hasattr(self.gvt, "get_flow_media_download_pool"):
                self.gvt.get_flow_media_download_pool(max_workers=int(defaults.get("upscale_download_workers") or 6))
        except Exception:
            pass
        return defaults

    def _throttle_flow_submit(self, log_fn=None, account_key: str = ""):
        """Giãn cách request theo từng tài khoản riêng biệt (đồng bộ Auto/Custom từ Engine Settings)."""
        limits = self._get_flow_limits()
        per_acc_delay = float(limits.get("submit_delay_sec") or self.FLOW_SUBMIT_DELAY_SEC)
        glob_stagger = float(limits.get("global_submit_stagger_sec") or self.FLOW_GLOBAL_STAGGER_SEC)
        key = str(account_key or "").strip().lower()
        with self._flow_submit_lock:
            now = time.time()
            acc_last = self._account_submit_ts.get(key, 0.0) if key else self._last_flow_submit_ts
            acc_target = (acc_last + per_acc_delay) if acc_last > 0 else now
            glob_target = (
                (self._last_flow_submit_ts + glob_stagger)
                if self._last_flow_submit_ts > 0
                else now
            )
            slot_ts = max(now, acc_target, glob_target)
            if key:
                self._account_submit_ts[key] = slot_ts
            self._last_flow_submit_ts = slot_ts
            wait_s = max(0.0, slot_ts - now)
        if wait_s > 0.05:
            if log_fn:
                tag = f" [{account_key}]" if account_key else ""
                log_fn(f"⏱️ Chờ {wait_s:.1f}s cooldown tài khoản{tag} trước khi gửi request lên Google Flow...")
            time.sleep(wait_s)

    def mark_account_cooldown(self, account_key: str, seconds: float = 90.0):
        key = str(account_key or "").strip().lower()
        if not key or seconds <= 0:
            return
        with self._rr_lock:
            self._account_cooldown_until[key] = max(
                self._account_cooldown_until.get(key, 0.0),
                time.time() + float(seconds),
            )

    def _schedule_profile_heal(self, profile_name: str):
        prof = str(profile_name or "").strip()
        if not prof:
            return
        with self._rr_lock:
            if prof in self._bg_heal_inflight:
                return
            self._bg_heal_inflight.add(prof)

        def _heal():
            try:
                ok_h, new_tok, new_pid, err_h = self.gvt._refresh_google_profile(prof, True)
                if ok_h and new_tok:
                    try:
                        from google_flow_auth import commit_login, identity_matches, expected_email
                        auth_root = self.gvt._auth_root_value(None)
                        email = str(err_h or "").removeprefix("session_verified:")
                        if identity_matches(expected_email(auth_root, prof), email):
                            commit_login(auth_root, prof, email, new_tok, new_pid or self.gvt.DEFAULT_PROJECT_ID, refresh=True)
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                with self._rr_lock:
                    self._bg_heal_inflight.discard(prof)

        threading.Thread(target=_heal, daemon=True).start()

    def ensure_captcha_bridge(self):
        need_rebind = self.captcha_bridge is None
        if not need_rebind and getattr(self.captcha_bridge, "_server", None) is None and getattr(self.captcha_bridge, "_remote_bridge", False):
            # If the companion GUI process holding :4000 closed, self-heal by binding :4000 locally!
            try:
                st = self.captcha_bridge._remote_call("GET", "/status", timeout=1.5)
                if not isinstance(st, dict) or st.get("bridge") != "CaptchaBridge":
                    need_rebind = True
            except Exception:
                need_rebind = True
        if need_rebind:
            bridge_port = getattr(self.gvt, "CAPTCHA_BRIDGE_PORT", 4000)
            bridge = self.gvt.CaptchaBridge(print, port=bridge_port)
            try:
                bridge.start(allow_remote=True)
            except TypeError:
                bridge.start()
            self.captcha_bridge = bridge
        try:
            if hasattr(self.captcha_bridge, "apply_concurrency_settings"):
                lim = self._get_flow_limits()
                self.captcha_bridge.apply_concurrency_settings(
                    per_account_delay_sec=lim.get("submit_delay_sec"),
                    global_stagger_sec=lim.get("global_submit_stagger_sec"),
                    pool_tabs=lim.get("extension_pool_tabs"),
                )
        except Exception:
            pass
        return self.captcha_bridge

    def get_accounts_info(self) -> Dict[str, Any]:
        acc_mgr = self.gvt.AccountManager()
        google_accs = []
        grok_accs = []
        cliproxy_models = []
        try:
            import engine_settings_manager as _esm_vsc
            ok_cm, cliproxy_models, _ = _esm_vsc._cliproxy_fetch_models(timeout=1.5)
            if not ok_cm:
                cliproxy_models = []
        except Exception:
            cliproxy_models = []

        for a in acc_mgr.accounts:
            is_google = self.gvt._is_google_flow_account(a)
            prof = (
                self.gvt._google_profile_name_for_account(a, allow_unresolved=True)
                if is_google
                else (getattr(a, "profile_name", "") or "")
            )
            raw_key = str(a.api_key or "").strip()
            has_cookie = bool(raw_key.startswith("flow_cookie:"))
            if is_google and prof and not has_cookie:
                try:
                    has_cookie = bool(self.gvt._load_flow_cookie_header(prof))
                except Exception:
                    has_cookie = False
            has_token = bool(raw_key and len(raw_key) > 10)
            g_email = getattr(a, "google_email", "") or (a.name[len("Google_"):] if a.name.startswith("Google_") else "")
            if is_google:
                avail_models = self.gvt.get_veo_ui_video_models(prof or a.name)
            else:
                low_name = str(a.name or "").lower()
                img_vid_models = [
                    m for m in cliproxy_models
                    if any(k in m.lower() for k in ("gpt-image", "gemini-3.1-flash-image", "grok-imagine"))
                ]
                if "codex" in low_name:
                    avail_models = [m for m in img_vid_models if "gpt-image" in m.lower()] or ["gpt-image-2 (chưa sẵn sàng)"]
                elif "grok" in low_name:
                    avail_models = [m for m in img_vid_models if "grok" in m.lower()] or ["grok-imagine-* (chưa login xAI trên :8317)"]
                else:
                    avail_models = img_vid_models or ["CLIProxy (:8317 offline hoặc chưa có model ảnh/video)"]
            live_cred = (
                self.gvt.get_live_flow_account_credits(prof or a.name)
                if hasattr(self.gvt, "get_live_flow_account_credits")
                else None
            )
            eff_cred = live_cred if live_cred is not None else getattr(a, "credits", None)
            own_pid = a.proxy_url if (is_google and a.proxy_url and not str(a.proxy_url).startswith("http")) else ""
            entry = {
                "name": a.name,
                "active": a.active,
                "profile_name": prof,
                "google_email": g_email,
                "credits": eff_cred,
                "tag": getattr(a, "tag", "Pro"),
                "auth_state": getattr(a, "auth_state", "") or ("ready" if (has_cookie or has_token) else "missing"),
                "proxy_url": a.proxy_url,
                "project_id": own_pid,
                "has_cookie": has_cookie,
                "has_token": has_token,
                "type": "google_flow" if is_google else "cliproxy",
                "available_video_models": avail_models,
                "cliproxy_models": [] if is_google else list(cliproxy_models),
                "has_low_priority_lite": self.gvt.is_veo_low_priority_available(prof or a.name) if is_google else False,
            }
            if is_google:
                google_accs.append(entry)
            else:
                grok_accs.append(entry)
        return {
            "total": len(acc_mgr.accounts),
            "active": len(acc_mgr.active),
            "google_accounts": google_accs,
            "grok_accounts": grok_accs,
        }

    def _resolve_flow_token_for_account(self, account) -> str:
        raw_tok = str(getattr(account, "api_key", "") or "").strip()
        if raw_tok.startswith("ya29."):
            return raw_tok
        prof = self.gvt._google_profile_name_for_account(account, allow_unresolved=True)
        if prof:
            try:
                disk_hdr = self.gvt._load_flow_cookie_header(prof)
                if disk_hdr:
                    return f"flow_cookie:{disk_hdr}"
            except Exception:
                pass
        return raw_tok

    def _is_usable_flow_account(self, account) -> bool:
        if not account.active or not self.gvt._is_google_flow_account(account):
            return False
        auth_st = str(getattr(account, "auth_state", "") or "").strip().lower()
        tok = self._resolve_flow_token_for_account(account)
        if not tok and auth_st in ("logging_in", "login_required", "missing", ""):
            return False
        prof = self.gvt._google_profile_name_for_account(account, allow_unresolved=True) or account.name
        if hasattr(self.gvt, "is_flow_account_credits_exhausted") and self.gvt.is_flow_account_credits_exhausted(prof):
            return False
        disk_cred = getattr(account, "credits", None)
        if isinstance(disk_cred, (int, float)) and 0 <= disk_cred < 10:
            return False
        return True

    def _own_flow_project_id(self, account, seen_pids: Optional[set] = None) -> str:
        raw_p = str(getattr(account, "proxy_url", "") or "").strip()
        if not raw_p or raw_p.startswith("http"):
            return ""
        if seen_pids is not None:
            if raw_p in seen_pids:
                return ""
            seen_pids.add(raw_p)
        return raw_p

    def flow_account_candidates(self):
        """Return enabled, authenticated, credit-available Flow accounts in rotating order."""
        all_google = [
            acc for acc in self.gvt.AccountManager().accounts
            if self.gvt._is_google_flow_account(acc)
        ]
        # Track project_ids already claimed by earlier accounts so a stamped DEFAULT_PROJECT_ID isn't reused across accounts
        pid_owner: Dict[str, str] = {}
        for acc in all_google:
            raw_p = str(getattr(acc, "proxy_url", "") or "").strip()
            if raw_p and not raw_p.startswith("http") and raw_p not in pid_owner:
                pid_owner[raw_p] = acc.name

        accounts = [acc for acc in all_google if self._is_usable_flow_account(acc)]
        if not accounts:
            return []
        now = time.time()
        with self._rr_lock:
            start = self._rr_idx % len(accounts)
            self._rr_idx += 1
            cooldowns = dict(self._account_cooldown_until)
        rotated = accounts[start:] + accounts[:start]
        healthy = []
        cooled = []
        for idx, acc in enumerate(rotated):
            prof = self.gvt._google_profile_name_for_account(acc, allow_unresolved=True) or acc.name
            rem_local = max(0.0, cooldowns.get(str(prof).strip().lower(), 0.0) - now)
            rem_global = 0.0
            if hasattr(self.gvt, "is_flow_account_in_cooldown"):
                for _k in {str(prof or "").strip(), str(getattr(acc, "name", "") or "").strip()}:
                    if _k:
                        in_cd, rem_g, _ = self.gvt.is_flow_account_in_cooldown(_k)
                        if in_cd:
                            rem_global = max(rem_global, float(rem_g))
            rem = max(rem_local, rem_global)
            if rem > 0.0:
                cooled.append((rem, idx, acc))
            else:
                healthy.append(acc)
        cooled.sort(key=lambda x: (x[0], x[1]))
        ordered = healthy + [x[2] for x in cooled]
        out = []
        for account in ordered:
            raw_p = str(getattr(account, "proxy_url", "") or "").strip()
            safe_pid = raw_p if (raw_p and not raw_p.startswith("http") and pid_owner.get(raw_p) == account.name) else ""
            out.append((account, self._resolve_flow_token_for_account(account), safe_pid))
        return out

    def _next_account(self, for_veo: bool = True):
        acc_mgr = self.gvt.AccountManager()
        active = [a for a in acc_mgr.accounts if a.active]
        if not active:
            active = acc_mgr.accounts
        if not active:
            return None, "", ""

        if for_veo:
            veo_candidates = [a for a in active if self._is_usable_flow_account(a)]
            if not veo_candidates:
                veo_candidates = [a for a in active if self.gvt._is_google_flow_account(a)]
            if veo_candidates:
                active = veo_candidates

        with self._rr_lock:
            acc = active[self._rr_idx % len(active)]
            self._rr_idx += 1

        bearer = self._resolve_flow_token_for_account(acc) if for_veo else str(acc.api_key or "").strip()
        proj_id = acc.proxy_url if (acc.proxy_url and not str(acc.proxy_url).startswith("http")) else ""
        return acc, bearer, proj_id

    def _run_veo_flow_with_failover(self, make_job_fn, flow_project_override: str, _log, defer_media: bool = False) -> str:
        candidates = self.flow_account_candidates()
        if not candidates:
            acc, bearer, veo_proj_id = self._next_account(for_veo=True)
            candidates = [(acc, bearer, veo_proj_id)] if acc or bearer else []
        if not candidates:
            raise RuntimeError("Chưa có tài khoản Google Flow nào đang bật.")

        def _clear_acct_cd(*keys):
            for _k in keys:
                if _k:
                    with self._rr_lock:
                        self._account_cooldown_until.pop(str(_k).strip().lower(), None)
                    if hasattr(self.gvt, "clear_flow_account_cooldown"):
                        self.gvt.clear_flow_account_cooldown(_k)

        def _mark_acct_cd(kind: str, reason: str, *keys):
            for _k in keys:
                if not _k:
                    continue
                if hasattr(self.gvt, "mark_flow_account_cooldown"):
                    dur = self.gvt.mark_flow_account_cooldown(_k, kind, reason)
                else:
                    dur = {"account_quota": 900.0, "account_auth": 180.0, "rate_limit": 120.0, "captcha_score": 45.0}.get(kind, 15.0)
                if dur > 0:
                    self.mark_account_cooldown(_k, dur)

        last_err = ""
        for idx, (acc, bearer, veo_proj_id) in enumerate(candidates):
            prof_name = self.gvt._google_profile_name_for_account(acc, allow_unresolved=True) if acc else ""
            acc_name = str(getattr(acc, "name", "") or "").strip() if acc else ""
            acct_key = prof_name or acc_name
            eff_proj_id = str(flow_project_override or veo_proj_id)
            job = make_job_fn(acc, prof_name)
            if len(candidates) > 1 and getattr(job, "max_retries", 3) > 1:
                job.max_retries = 1
            if defer_media and hasattr(job, "async_media_finalize"):
                job.async_media_finalize = True
            bridge = self.ensure_captcha_bridge()
            self._throttle_flow_submit(_log, account_key=acct_key)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                ok = loop.run_until_complete(
                    self.gvt.run_veo_flow(
                        job, bearer, eff_proj_id, bridge, log=_log, progress=None
                    )
                )
                if ok and defer_media and getattr(job, "media_finalize_future", None) is not None:
                    _clear_acct_cd(prof_name, acc_name)
                    return job
                if ok and job.local_path and Path(job.local_path).is_file():
                    _clear_acct_cd(prof_name, acc_name)
                    return str(Path(job.local_path).resolve())
                if ok and hasattr(self.gvt, "wait_for_job_media") and self.gvt.wait_for_job_media(job):
                    _clear_acct_cd(prof_name, acc_name)
                    return str(Path(job.local_path).resolve())
                last_err = str(job.error or "Google Flow thất bại")
                err_kind = (
                    self.gvt.classify_flow_error(last_err)
                    if hasattr(self.gvt, "classify_flow_error")
                    else "transient"
                )
                short_err = (
                    self.gvt.format_flow_error_short(last_err, 120)
                    if hasattr(self.gvt, "format_flow_error_short")
                    else last_err[:120]
                )
                if (
                    (hasattr(self.gvt, "should_stop_all_accounts") and self.gvt.should_stop_all_accounts(last_err))
                    or err_kind == "content_policy"
                ):
                    vi_err = (
                        self.gvt.describe_flow_error_vi(last_err)
                        if hasattr(self.gvt, "describe_flow_error_vi")
                        else last_err
                    )
                    _log(f"❌ {vi_err} — dừng ngay, không xoay sang tài khoản khác.")
                    raise RuntimeError(vi_err)

                if err_kind in ("account_quota", "rate_limit", "account_auth", "captcha_score", "transient"):
                    _mark_acct_cd(err_kind, last_err, prof_name, acc_name)
                if err_kind == "account_auth" or getattr(job, "_force_google_token_refresh", False):
                    if prof_name and not getattr(job, "_inline_cookie_refreshed", False):
                        self._schedule_profile_heal(prof_name)
                if idx + 1 < len(candidates):
                    _log(f"⚠️ {acct_key or 'Flow'} lỗi [{err_kind}] ({short_err}), tự động chuyển tài khoản tiếp theo...")
            finally:
                loop.close()
        final_vi = (
            self.gvt.describe_flow_error_vi(last_err)
            if last_err and hasattr(self.gvt, "describe_flow_error_vi")
            else (last_err or "Tạo nội dung Google Flow thất bại")
        )
        raise RuntimeError(final_vi)

    def _generate_single_scene_image(self, project_id: str, prod: Dict[str, Any], scene: Dict[str, Any]) -> str:
        s_num = scene["scene_number"]
        prompt = scene.get("image_prompt", "").strip()
        if not prompt:
            raise ValueError(f"Cảnh {s_num} thiếu image_prompt")

        model = prod.get("img_model", "Nano Banana 2")
        aspect = prod.get("aspect", "9:16")
        ref_img = prod.get("product_image_path", "")
        out_dir = Path(prod["output_dir"]) / f"scene_{s_num:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_base = str(out_dir / f"scene_{s_num:02d}")

        is_veo = self.gvt.is_veo_model(model)

        def _log(m: str):
            append_project_log(project_id, f"[{prod['product_name']} | Cảnh {s_num}] {m}")

        if is_veo:
            resolved_cv = resolve_character_and_voice(
                str(scene.get("character_id") or prod.get("character_id") or ""),
                str(scene.get("voice_id") or prod.get("voice_id") or ""),
            )
            override_pid = str(prod.get("flow_project_id") or resolved_cv["project_id"] or "")

            def _make_img_job(cand_acc, cand_prof):
                job = self.gvt.VideoJob(
                    id=f"skill_img_{prod['id']}_{s_num}_{int(time.time())}",
                    model=model,
                    prompt=prompt,
                    resolution="1K",
                    aspect_ratio=aspect,
                    local_path=out_base,
                    account_name=cand_acc.name if cand_acc else "",
                    google_profile_name=cand_prof,
                )
                if ref_img and Path(ref_img).is_file():
                    job.image_url = ref_img
                if resolved_cv["character_id"]:
                    job.character_id = resolved_cv["character_id"]
                return job

            return self._run_veo_flow_with_failover(_make_img_job, override_pid, _log)
        else:
            # ChatGPT (Codex) / Gemini / Grok image generation qua CLIProxy (:8317)
            acc, _, _ = self._next_account(for_veo=False)
            import base64
            proxy = acc.proxy_url if (acc and acc.proxy_url.startswith("http")) else self.gvt.DEFAULT_PROXY_URL
            api_key = (acc.api_key if acc else "") or "grok-video-key-001"
            size = "1024x1536" if "9:16" in aspect else ("1536x1024" if "16:9" in aspect else "1024x1024")
            refs = self.gvt._cliproxy_collect_unique_refs(
                ref_img,
                list(scene.get("reference_images") or []) + list(prod.get("reference_images") or []),
            )
            kind, val = self.gvt._cliproxy_run_image_sync(
                proxy,
                api_key,
                model,
                prompt,
                size,
                aspect=aspect,
                ref_paths=refs,
                log_fn=_log,
            )
            out_file = out_dir / f"scene_{s_num:02d}.png"
            if kind == "url":
                with self.gvt.make_httpx_client(timeout=60, target_url=val) as client:
                    r = client.get(val)
                    r.raise_for_status()
                    img_bytes = r.content
            elif kind == "base64":
                img_bytes = base64.b64decode(val)
            else:
                raise RuntimeError("Không nhận được URL hoặc b64_json từ API ảnh")
            self.gvt._save_image_payload_to_path(img_bytes, str(out_file))
            return str(out_file.resolve())

    def _generate_single_scene_video(
        self,
        project_id: str,
        prod: Dict[str, Any],
        scene: Dict[str, Any],
        defer_media: bool = False,
    ) -> Any:
        s_num = scene["scene_number"]
        source_img = scene.get("image_path", "")
        if not source_img or not Path(source_img).is_file():
            raise FileNotFoundError(f"Cảnh {s_num} chưa có ảnh đầu vào để tạo video I2V")

        raw_vid_prompt = scene.get("video_prompt", "").strip()
        if not raw_vid_prompt:
            raw_vid_prompt = f"Animate this product image naturally. Smooth {prod.get('seconds_per_scene', 8)}-second motion."

        vid_prompt = (
            "IMPORTANT: Use the provided input image as the STRICT visual reference. "
            "The video MUST show the EXACT same subject, product, and composition as the input image. "
            "Do NOT create a completely different scene or landscape. " + raw_vid_prompt
        )

        model = prod.get("vid_model", "Veo 3.1 - Fast")
        aspect = prod.get("aspect", "9:16")
        duration = int(prod.get("seconds_per_scene", 8))
        resolution = prod.get("video_resolution", "720p")
        out_dir = Path(prod["output_dir"]) / f"scene_{s_num:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_video = str(out_dir / f"video_scene_{s_num:02d}.mp4")

        is_veo = self.gvt.is_veo_model(model)

        def _log(m: str):
            append_project_log(project_id, f"[{prod['product_name']} | Video Cảnh {s_num}] {m}")

        if is_veo:
            resolved_cv = resolve_character_and_voice(
                str(scene.get("character_id") or prod.get("character_id") or ""),
                str(scene.get("voice_id") or prod.get("voice_id") or ""),
            )
            override_pid = str(prod.get("flow_project_id") or resolved_cv["project_id"] or "")
            vid_mode = "reference-to-video" if resolved_cv["voice_id"] else "image-to-video"

            def _make_vid_job(cand_acc, cand_prof):
                job = self.gvt.VideoJob(
                    id=f"skill_vid_{prod['id']}_{s_num}_{int(time.time())}",
                    model=model,
                    mode=vid_mode,
                    prompt=vid_prompt,
                    image_url=source_img,
                    aspect_ratio=aspect,
                    duration=duration,
                    resolution=resolution,
                    local_path=out_video,
                    account_name=cand_acc.name if cand_acc else "",
                    google_profile_name=cand_prof,
                )
                if resolved_cv["voice_id"]:
                    job.voice_id = resolved_cv["voice_id"]
                    job.reference_image_urls = [source_img]
                return job

            return self._run_veo_flow_with_failover(_make_vid_job, override_pid, _log, defer_media=defer_media)
        else:
            # Grok I2V qua CLIProxy (:8317)
            acc, _, _ = self._next_account(for_veo=False)
            import base64
            proxy = acc.proxy_url if (acc and acc.proxy_url.startswith("http")) else self.gvt.DEFAULT_PROXY_URL
            api_key = (acc.api_key if acc else "") or "grok-video-key-001"
            img_bytes = Path(source_img).read_bytes()
            ext = Path(source_img).suffix.lower().lstrip(".") or "jpg"
            mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            img_bytes_c, mime = self.gvt._compress_image_for_grok(img_bytes, mime, max_kb=700)
            pub_url = self.gvt._upload_image_for_grok(img_bytes_c, mime, _log)
            ref_url = pub_url or f"data:{mime};base64,{base64.b64encode(img_bytes_c).decode()}"

            submit_url = f"{proxy}/v1/videos/generations"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "prompt": vid_prompt,
                "input_reference": {"image_url": ref_url},
                "aspect_ratio": aspect,
                "duration": duration,
                "resolution": resolution,
            }
            with self.gvt.make_httpx_client(timeout=120, target_url=submit_url) as client:
                resp = client.post(submit_url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(self.gvt._cliproxy_format_api_error(resp.status_code, resp.text, model, proxy))
            req_id = resp.json().get("id") or resp.json().get("request_id", "")
            if not req_id:
                raise RuntimeError("Không nhận được request_id từ Grok Video API")

            poll_url = f"{proxy}/v1/videos/{req_id}"
            for _ in range(90):
                time.sleep(8)
                with self.gvt.make_httpx_client(timeout=30, target_url=poll_url) as client:
                    r = client.get(poll_url, headers={"Authorization": f"Bearer {api_key}"})
                    if r.status_code < 400:
                        st_data = r.json()
                        st = st_data.get("status", "")
                        if st in ("succeeded", "completed", "done"):
                            vurl = (
                                st_data.get("url")
                                or st_data.get("video_url")
                                or (st_data.get("video", {}) or {}).get("url")
                                or ((st_data.get("data") or [{}])[0]).get("url")
                            )
                            if vurl:
                                with self.gvt.make_httpx_client(timeout=120, target_url=vurl) as dl:
                                    vr = dl.get(vurl)
                                    vr.raise_for_status()
                                    Path(out_video).write_bytes(vr.content)
                                return str(Path(out_video).resolve())
                        elif st in ("failed", "error"):
                            raise RuntimeError(f"Grok video job failed: {st_data}")
            raise TimeoutError("Quá thời gian chờ tạo video Grok")

    def _concat_final_video(self, project_id: str, prod: Dict[str, Any]) -> str:
        out_dir = Path(prod["output_dir"])
        scenes_sorted = sorted(prod.get("scenes", []), key=lambda s: int(s.get("scene_number", 1)))
        video_paths = [
            s["video_path"]
            for s in scenes_sorted
            if s.get("video_path") and Path(s["video_path"]).is_file()
        ]
        if not video_paths:
            raise RuntimeError("Không có video phân cảnh nào để ghép Final")

        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in prod["product_name"])[:40]
        final_path = out_dir / f"FINAL_{safe_name}_{prod['id']}.mp4"

        if len(video_paths) == 1 or not shutil.which("ffmpeg"):
            shutil.copy2(video_paths[0], final_path)
            return str(final_path.resolve())

        append_project_log(project_id, f"🎞️ [{prod['product_name']}] Đang ghép {len(video_paths)} cảnh thành Video Final bằng FFmpeg...")
        concat_list = out_dir / "ffmpeg_concat_list.txt"
        lines = []
        for vp in video_paths:
            escaped = str(Path(vp).resolve()).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        concat_list.write_text("\n".join(lines), encoding="utf-8")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(final_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        if res.returncode != 0 or not final_path.is_file():
            # Fallback copy stream
            cmd_copy = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-c", "copy", str(final_path)
            ]
            subprocess.run(cmd_copy, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

        if not final_path.is_file():
            shutil.copy2(video_paths[0], final_path)
        return str(final_path.resolve())

    def run_single_product(self, project_id: str, product_id: str, max_scene_workers: Optional[int] = None) -> Dict[str, Any]:
        """Chạy trọn gói 1 sản phẩm (Pipeline gối đầu): Tạo Ảnh -> Gửi Video ngay khi từng cảnh có ảnh + tải nền."""
        limits = self._get_flow_limits()
        eff_scene_workers = (
            int(max_scene_workers)
            if (max_scene_workers is not None and int(max_scene_workers) > 0)
            else int(limits.get("flow_api_workers") or 6)
        )
        eff_scene_workers = max(1, min(32, eff_scene_workers))

        def _update_state(fn):
            with _STORE_LOCK:
                p_data = load_project(project_id)
                for item in p_data.get("products", []):
                    if item["id"] == product_id:
                        fn(item)
                        save_project(p_data)
                        return item
            return None

        prod = _update_state(lambda item: item.update({"status": "img_gen", "error_msg": ""}))
        if not prod:
            raise ValueError(f"Không tìm thấy sản phẩm {product_id} trong dự án {project_id}")

        scenes = prod.get("scenes", [])
        if not scenes:
            _update_state(lambda item: item.update({"status": "waiting_agent", "error_msg": "Chưa có kịch bản phân cảnh từ AI Agent"}))
            raise ValueError(f"Sản phẩm '{prod['product_name']}' chưa có kịch bản phân cảnh từ AI Agent.")

        append_project_log(
            project_id,
            f"🚀 [{prod['product_name']}] Khởi chạy Pipeline gối đầu {len(scenes)} phân cảnh ({eff_scene_workers} luồng tạo + tải nền {limits.get('upscale_download_workers', 6)} luồng)...",
        )

        # ── BƯỚC 1 + 2 PIPELINE GỐI ĐẦU: TẠO ẢNH XONG CẢNH NÀO GỬI VIDEO CẢNH ĐÓ NGAY, KHÔNG CHỜ ĐỒNG BỘ ──
        def _is_fatal_outer_err(err_msg: str) -> bool:
            kind = (
                self.gvt.classify_flow_error(err_msg)
                if hasattr(self.gvt, "classify_flow_error")
                else "transient"
            )
            return kind in ("content_policy", "account_quota", "account_auth")

        def _img_task(s_idx: int):
            s_obj = prod["scenes"][s_idx]
            if s_obj.get("image_path") and Path(s_obj["image_path"]).is_file():
                return s_idx, s_obj["image_path"], None
            for attempt in range(1, 3):
                try:
                    img_p = self._generate_single_scene_image(project_id, prod, s_obj)
                    return s_idx, img_p, None
                except Exception as e:
                    err_s = str(e)
                    if attempt == 2 or _is_fatal_outer_err(err_s):
                        return s_idx, "", err_s
                    time.sleep(random.uniform(2.0, 4.5))
            return s_idx, "", "Unknown error"

        def _vid_task(s_idx: int, cur_scene_obj: Dict[str, Any]):
            if cur_scene_obj.get("video_path") and Path(cur_scene_obj["video_path"]).is_file():
                return s_idx, cur_scene_obj["video_path"], None, None
            for attempt in range(1, 3):
                try:
                    try:
                        res_v = self._generate_single_scene_video(project_id, prod, cur_scene_obj, defer_media=True)
                    except TypeError:
                        res_v = self._generate_single_scene_video(project_id, prod, cur_scene_obj)
                    if isinstance(res_v, str):
                        return s_idx, res_v, None, None
                    return s_idx, "", res_v, None
                except Exception as e:
                    err_s = str(e)
                    if attempt == 2 or _is_fatal_outer_err(err_s):
                        return s_idx, "", None, err_s
                    time.sleep(random.uniform(3.0, 6.0))
            return s_idx, "", None, "Unknown video error"

        pool_size = max(1, min(max(eff_scene_workers, len(scenes) * 2), eff_scene_workers))
        pending_vid_futs = []
        deferred_vid_jobs = []
        img_done_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=pool_size) as pool:
            img_futs = {pool.submit(_img_task, i): i for i in range(len(scenes))}
            for fut in concurrent.futures.as_completed(img_futs):
                s_idx, img_path, err = fut.result()
                def _apply_img(item, idx=s_idx, p=img_path, e=err):
                    sc = item["scenes"][idx]
                    if p:
                        sc["image_path"] = p
                        sc["status"] = "img_done"
                        sc["error_msg"] = ""
                    else:
                        sc["status"] = "failed"
                        sc["error_msg"] = e or "Lỗi tạo ảnh"
                prod = _update_state(_apply_img)
                if img_path:
                    img_done_count += 1
                    sc_ready = dict(prod["scenes"][s_idx])
                    append_project_log(
                        project_id,
                        f"🎬 [{prod['product_name']}] Ảnh cảnh {sc_ready.get('scene_number', s_idx + 1)} xong -> Đẩy tạo Video I2V ngay lập tức!",
                    )
                    pending_vid_futs.append(pool.submit(_vid_task, s_idx, sc_ready))

            if img_done_count > 0:
                prod = _update_state(lambda item: item.update({"status": "vid_gen"}))

            for vfut in concurrent.futures.as_completed(pending_vid_futs):
                s_idx, vid_path, deferred_job, err = vfut.result()
                if deferred_job is not None:
                    deferred_vid_jobs.append((s_idx, deferred_job))
                else:
                    def _apply_vid(item, idx=s_idx, p=vid_path, e=err):
                        sc = item["scenes"][idx]
                        if p:
                            sc["video_path"] = p
                            sc["status"] = "done"
                            sc["error_msg"] = ""
                        else:
                            sc["status"] = "failed"
                            sc["error_msg"] = e or "Lỗi tạo video"
                    prod = _update_state(_apply_vid)

        if not img_done_count:
            _update_state(lambda item: item.update({"status": "failed", "error_msg": "Tất cả phân cảnh đều lỗi tạo ảnh"}))
            append_project_log(project_id, f"❌ [{prod['product_name']}] Thất bại: Không tạo được ảnh phân cảnh nào.")
            return load_project(project_id)

        # Hoàn tất các file video đang tải nền (nếu defer_media=True)
        for s_idx, d_job in deferred_vid_jobs:
            vid_ok = hasattr(self.gvt, "wait_for_job_media") and self.gvt.wait_for_job_media(d_job, timeout=300.0)
            vid_path = str(Path(d_job.local_path).resolve()) if (vid_ok and getattr(d_job, "local_path", None) and Path(d_job.local_path).is_file()) else ""
            err_msg = "" if vid_path else str(getattr(d_job, "error", None) or "Lỗi tải video nền")
            if not vid_path and not _is_fatal_outer_err(err_msg):
                # Fallback đồng bộ qua failover nếu tải CDN nền lỗi (không retry nếu vi phạm/hết quota)
                try:
                    sc_fb = dict(prod["scenes"][s_idx])
                    vid_path = self._generate_single_scene_video(project_id, prod, sc_fb, defer_media=False)
                    err_msg = ""
                except Exception as fb_exc:
                    err_msg = str(fb_exc)
            def _apply_dl(item, idx=s_idx, p=vid_path, e=err_msg):
                sc = item["scenes"][idx]
                if p:
                    sc["video_path"] = p
                    sc["status"] = "done"
                    sc["error_msg"] = ""
                else:
                    sc["status"] = "failed"
                    sc["error_msg"] = e or "Lỗi tải video"
            prod = _update_state(_apply_dl)

        vid_ready = [s for s in prod["scenes"] if s.get("video_path") and Path(s["video_path"]).is_file()]
        if not vid_ready:
            _update_state(lambda item: item.update({"status": "failed", "error_msg": "Không tạo được video cho phân cảnh nào"}))
            append_project_log(project_id, f"❌ [{prod['product_name']}] Thất bại ở bước tạo video.")
            return load_project(project_id)

        # ── BƯỚC 3: GHÉP VIDEO FINAL BẰNG FFMPEG ──
        prod = _update_state(lambda item: item.update({"status": "assembling"}))
        try:
            final_vid = self._concat_final_video(project_id, prod)
            thumb_cli = ""
            try:
                scripts_dir = str(SKILL_DIR / "flow_final_pipeline" / "scripts")
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                import engine_settings_manager as _esm_cli
                vkey_cli = str(prod.get("vkey") or prod.get("char_v_code") or prod.get("id") or "v1")
                th_res = _esm_cli.ensure_project_variant_thumbnail_and_inject(
                    project_id,
                    vkey=vkey_cli,
                    final_video_path=final_vid,
                    log_cb=lambda m: append_project_log(project_id, m),
                )
                thumb_cli = str(th_res.get("thumbnail_path") or th_res.get("project_thumbnail_path") or "").strip()
            except Exception as _th_err:
                append_project_log(project_id, f"⚠️ [{prod['product_name']}] Bỏ qua tự tạo thumbnail: {_th_err}")
            upd = {"status": "done", "final_video_path": final_vid, "error_msg": ""}
            if thumb_cli:
                upd["thumbnail_path"] = thumb_cli
            _update_state(lambda item: item.update(upd))
            append_project_log(project_id, f"✅ [{prod['product_name']}] HOÀN TẤT VIDEO FINAL: {final_vid}")
        except Exception as e:
            _update_state(lambda item: item.update({"status": "failed", "error_msg": f"Lỗi ghép video: {e}"}))
            append_project_log(project_id, f"❌ [{prod['product_name']}] Lỗi ghép video final: {e}")

        return load_project(project_id)

    def run_project_batch(
        self,
        project_id_or_name: str,
        max_product_workers: Optional[int] = None,
        max_scene_workers: Optional[int] = None,
        product_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Chạy hàng loạt sản phẩm song song trong dự án."""
        proj = load_project(project_id_or_name)
        if not proj:
            raise ValueError(f"Không tìm thấy dự án: {project_id_or_name}")

        limits = self._get_flow_limits()
        eff_prod_workers = (
            int(max_product_workers)
            if (max_product_workers is not None and int(max_product_workers) > 0)
            else int(limits.get("parallel_products") or 4)
        )
        eff_scene_workers = (
            int(max_scene_workers)
            if (max_scene_workers is not None and int(max_scene_workers) > 0)
            else int(limits.get("flow_api_workers") or 6)
        )
        eff_prod_workers = max(1, min(16, eff_prod_workers))
        eff_scene_workers = max(1, min(32, eff_scene_workers))

        pid = proj["id"]
        with _STOPPED_PROJECTS_LOCK:
            _STOPPED_PROJECT_IDS.discard(pid)
            _ACTIVE_PROJECT_BATCHES.add(pid)
        status_file = get_project_dir(pid) / "pipeline_status.json"
        _atomic_write_store_json(
            status_file,
            {
                "is_running": True,
                "pid_os": os.getpid(),
                "runner_mode": "in_process_batch",
                "message": f"🔥 Đang chạy đa luồng dự án '{proj['name']}'...",
                "updated_at": time.time(),
            },
        )
        try:
            targets = []
            for p in proj.get("products", []):
                if product_ids and p["id"] not in product_ids:
                    continue
                if p.get("scenes") and p.get("status") in ("queued", "failed", "img_gen", "vid_gen"):
                    targets.append(p["id"])

            if not targets:
                append_project_log(pid, "ℹ️ Không có sản phẩm nào ở trạng thái sẵn sàng chạy (queued/failed có kịch bản).")
                _atomic_write_store_json(
                    status_file,
                    {
                        "is_running": False,
                        "pid_os": None,
                        "message": "ℹ️ Không có sản phẩm nào ở trạng thái sẵn sàng chạy.",
                        "updated_at": time.time(),
                    },
                )
                return proj

            append_project_log(
                pid,
                f"🔥 BẮT ĐẦU CHẠY ĐA LUỒNG {len(targets)} SẢN PHẨM (Song song {eff_prod_workers} SP × {eff_scene_workers} luồng/cảnh | Delay/TK {limits.get('submit_delay_sec', 4.5)}s)...",
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=eff_prod_workers) as pool:
                futs = [
                    pool.submit(
                        lambda pr_id=prod_id: (
                            None if is_project_stopped(pid) else self.run_single_product(pid, pr_id, eff_scene_workers)
                        )
                    )
                    for prod_id in targets
                ]
                for fut in concurrent.futures.as_completed(futs):
                    try:
                        fut.result()
                    except Exception as e:
                        append_project_log(pid, f"⚠️ Lỗi xử lý sản phẩm: {e}")

            final_proj = load_project(pid)
            done_cnt = sum(1 for p in final_proj.get("products", []) if p.get("status") == "done")
            fail_cnt = sum(1 for p in final_proj.get("products", []) if p.get("status") == "failed")
            stopped_now = is_project_stopped(pid)
            end_msg = (
                f"⏹ Đã dừng dự án '{final_proj['name']}' theo yêu cầu ({done_cnt} xong, {fail_cnt} lỗi)."
                if stopped_now
                else f"🎉 HOÀN THÀNH BATCH DỰ ÁN '{final_proj['name']}': {done_cnt}/{len(final_proj.get('products', []))} sản phẩm có Video Final ({fail_cnt} lỗi)!"
            )
            append_project_log(pid, end_msg)
            _atomic_write_store_json(
                status_file,
                {
                    "is_running": False,
                    "pid_os": None,
                    "message": end_msg,
                    "updated_at": time.time(),
                },
            )
            return final_proj
        finally:
            with _STOPPED_PROJECTS_LOCK:
                _ACTIVE_PROJECT_BATCHES.discard(pid)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI ENTRYPOINT CHO AI AGENT (ANTIGRAVITY / CODEX)
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Skill Video Veo CLI — Công cụ điều khiển tạo Video hàng loạt cho AI Agent"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 1. status
    sub.add_parser("status", help="Xem trạng thái tài khoản, Role Skills và danh sách dự án")

    # 1b. list-voices
    sub.add_parser("list-voices", help="Liệt kê danh sách Nhân vật cố định (Saved Characters) và Giọng nói (Custom + Built-in Voices) của Google Flow")

    # 2. list-roles
    sub.add_parser("list-roles", help="Liệt kê các file Role Skill (.MD) hiện có")

    # 3. read-role
    p_read_role = sub.add_parser("read-role", help="Đọc nội dung 1 file Role Skill (.MD)")
    p_read_role.add_argument("--file", required=True, help="Tên file Role Skill (ví dụ: DoAnVat.MD)")

    # 4. import-folder
    p_imp = sub.add_parser("import-folder", help="Nhập hàng loạt ảnh sản phẩm từ 1 thư mục vào Dự án")
    p_imp.add_argument("--project", required=True, help="Tên hoặc ID dự án")
    p_imp.add_argument("--folder", required=True, help="Đường dẫn thư mục chứa ảnh sản phẩm")
    p_imp.add_argument("--role", default="DoAnVat.MD", help="Tên file Role Skill (.MD)")
    p_imp.add_argument("--img-model", default="Nano Banana 2", help="Model tạo ảnh")
    p_imp.add_argument("--vid-model", default="Veo 3.1 - Fast", help="Model tạo video")
    p_imp.add_argument("--aspect", default="9:16", help="Tỷ lệ khung hình (9:16 hoặc 16:9)")
    p_imp.add_argument("--scenes", type=int, default=4, help="Số phân cảnh mỗi sản phẩm")

    # 5. list-pending
    p_pend = sub.add_parser("list-pending", help="Lấy danh sách các sản phẩm đang chờ AI Agent viết kịch bản")
    p_pend.add_argument("--project", required=True, help="Tên hoặc ID dự án")

    # 6. submit-prompts
    p_sub = sub.add_parser("submit-prompts", help="AI Agent truyền JSON kịch bản & prompt phân cảnh xuống cho dự án")
    p_sub.add_argument("--project", required=True, help="Tên hoặc ID dự án")
    p_sub.add_argument("--payload-file", required=True, help="Đường dẫn file JSON chứa kịch bản các sản phẩm")
    p_sub.add_argument("--auto-run", action="store_true", help="Tự động chạy tạo Ảnh -> Video -> Final ngay sau khi nạp prompt")
    p_sub.add_argument("--product-workers", type=int, default=0, help="Số sản phẩm chạy song song (0 = Auto theo Engine Settings)")
    p_sub.add_argument("--scene-workers", type=int, default=0, help="Số phân cảnh chạy song song mỗi sản phẩm (0 = Auto theo Engine Settings)")

    # 7. run-batch
    p_run = sub.add_parser("run-batch", help="Chạy đa luồng tạo Ảnh -> Video -> Final cho dự án")
    p_run.add_argument("--project", required=True, help="Tên hoặc ID dự án")
    p_run.add_argument("--product-workers", type=int, default=0, help="Số sản phẩm chạy song song (0 = Auto theo Engine Settings)")
    p_run.add_argument("--scene-workers", type=int, default=0, help="Số phân cảnh chạy song song mỗi sản phẩm (0 = Auto theo Engine Settings)")

    # 8. crawl-product (Tự động tải ảnh & thông tin sản phẩm TikTokShop theo Cách 1 SPAI hoặc Cách 2 Browser)
    p_crawl = sub.add_parser("crawl-product", help="Crawl thông tin & ảnh sản phẩm TikTokShop theo Link hoặc ID")
    p_crawl.add_argument("--url", "--id", dest="raw_input", required=True, help="Link hoặc ID sản phẩm TikTokShop")
    p_crawl.add_argument("--method", choices=["auto", "api", "browser"], default="auto", help="Phương thức crawl (auto/api/browser)")
    p_crawl.add_argument("--force", action="store_true", help="Tải lại ngay cả khi đã có cache")

    # 9. set-videos-per-char (Cấu hình số lượng video tạo ra cho mỗi nhân vật)
    p_vpc = sub.add_parser("set-videos-per-char", help="Cập nhật số video mặc định cho mỗi nhân vật trong thư viện")
    p_vpc.add_argument("--count", type=int, required=True, help="Số lượng video mỗi nhân vật (1 - 5)")
    p_vpc.add_argument("--char", default="", help="Mã nhân vật cụ thể (VD: nv1, nv2) hoặc để trống áp dụng toàn bộ")

    # 10. gen-char-image (Tạo ảnh Character Sheet hoặc ảnh Nhân vật cầm sản phẩm 2K)
    p_gci = sub.add_parser("gen-char-image", help="Tạo ảnh Character Sheet hoặc ảnh Nhân vật cầm sản phẩm 2K")
    p_gci.add_argument("--mode", choices=["character_sheet", "product_ref"], default="character_sheet", help="Chế độ tạo ảnh")
    p_gci.add_argument("--char", default="nv1", help="Mã nhân vật (nv1..nv5)")
    p_gci.add_argument("--sheet-template", default="sheet_6panel_studio", help="Mã mẫu Character Sheet")
    p_gci.add_argument("--pid", default="", help="Mã sản phẩm (khi mode=product_ref)")
    p_gci.add_argument("--model", choices=["nano_banana", "chatgpt"], default="nano_banana", help="Model tạo ảnh")
    p_gci.add_argument("--prompt", default="", help="Prompt tùy chỉnh (nếu có)")

    # 11. create-video (Khởi tạo kịch bản theo Template #001..#003 và tùy chọn chạy pipeline ngay)
    p_cv = sub.add_parser("create-video", help="Tạo kịch bản theo Template (#001, #002, #003) từ Link/ID sản phẩm và tùy chọn chạy tạo video")
    p_cv.add_argument("--product", required=True, help="Link hoặc ID sản phẩm TikTokShop")
    p_cv.add_argument("--template", default="001", help="Mã hoặc tên Template (001, 002, 003)")
    p_cv.add_argument("--videos-per-char", type=int, default=None, help="Số video mỗi nhân vật")
    p_cv.add_argument("--crawl-method", choices=["auto", "api", "browser"], default="auto", help="Phương thức crawl")
    p_cv.add_argument("--run", action="store_true", help="Tự động kích hoạt pipeline tạo Ảnh 2K -> Video -> Final")

    args = parser.parse_args()

    if args.cmd == "status":
        runner = MultiThreadSkillRunner()
        roles = sync_role_skills_dirs()
        projects = _load_projects_index()
        acc_info = runner.get_accounts_info()
        print(json.dumps({
            "accounts": acc_info,
            "role_skills": [r["filename"] for r in roles],
            "projects": projects,
            "voices_and_characters": load_voices_and_characters(),
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "list-voices":
        print(json.dumps(load_voices_and_characters(), indent=2, ensure_ascii=False))

    elif args.cmd == "list-roles":
        roles = sync_role_skills_dirs()
        print(json.dumps(roles, indent=2, ensure_ascii=False))

    elif args.cmd == "read-role":
        print(read_role_skill(args.file))

    elif args.cmd == "import-folder":
        proj = import_products_from_folder(
            args.project,
            args.folder,
            role_skill_file=args.role,
            img_model=args.img_model,
            vid_model=args.vid_model,
            aspect=args.aspect,
            num_scenes=args.scenes,
        )
        print(json.dumps({
            "project_id": proj["id"],
            "project_name": proj["name"],
            "total_products": len(proj["products"]),
            "products": [
                {
                    "id": p["id"],
                    "product_name": p["product_name"],
                    "product_info": p["product_info"],
                    "product_image_path": p["product_image_path"],
                    "role_skill_file": p["role_skill_file"],
                    "num_scenes": p["num_scenes"],
                    "status": p["status"],
                }
                for p in proj["products"]
            ],
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "list-pending":
        proj = load_project(args.project)
        if not proj:
            print(json.dumps({"error": f"Project not found: {args.project}"}, ensure_ascii=False))
            sys.exit(1)
        pending = [
            {
                "id": p["id"],
                "product_name": p["product_name"],
                "product_info": p["product_info"],
                "product_image_path": p["product_image_path"],
                "role_skill_file": p["role_skill_file"],
                "num_scenes": p["num_scenes"],
                "aspect": p["aspect"],
                "status": p["status"],
            }
            for p in proj.get("products", [])
            if not p.get("scenes") or p.get("status") in ("waiting_agent", "failed")
        ]
        print(json.dumps({
            "project_id": proj["id"],
            "project_name": proj["name"],
            "pending_count": len(pending),
            "pending_products": pending,
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "submit-prompts":
        payload_path = Path(args.payload_file)
        data = json.loads(payload_path.read_text(encoding="utf-8"))
        items = data.get("products", data) if isinstance(data, dict) else data
        proj = submit_agent_prompts(args.project, items)
        if args.auto_run:
            runner = MultiThreadSkillRunner()
            proj = runner.run_project_batch(
                proj["id"],
                max_product_workers=args.product_workers,
                max_scene_workers=args.scene_workers,
            )
        print(json.dumps({
            "project_id": proj["id"],
            "project_name": proj["name"],
            "total_products": len(proj["products"]),
            "done_products": sum(1 for p in proj["products"] if p.get("status") == "done"),
            "final_videos": [
                {"product_name": p["product_name"], "final_video_path": p.get("final_video_path", ""), "status": p["status"]}
                for p in proj["products"]
            ],
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "run-batch":
        runner = MultiThreadSkillRunner()
        proj = runner.run_project_batch(
            args.project,
            max_product_workers=args.product_workers,
            max_scene_workers=args.scene_workers,
        )
        print(json.dumps({
            "project_id": proj["id"],
            "project_name": proj["name"],
            "done_products": sum(1 for p in proj["products"] if p.get("status") == "done"),
            "final_videos": [
                {"product_name": p["product_name"], "final_video_path": p.get("final_video_path", ""), "status": p["status"]}
                for p in proj["products"]
            ],
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "crawl-product":
        scripts_dir = str(SKILL_DIR / "flow_final_pipeline" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import io, contextlib
        import product_crawler_bridge as _pcb
        with contextlib.redirect_stdout(sys.stderr):
            res = _pcb.crawl_product_by_id_or_url(args.raw_input, method=args.method, force=args.force)
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.cmd == "set-videos-per-char":
        scripts_dir = str(SKILL_DIR / "flow_final_pipeline" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import character_library_manager as _clm
        st = _clm.get_character_library_state()
        cnt = max(1, min(5, int(args.count)))
        target_ck = args.char.strip().lower()
        chars_payload = {}
        for c in st.get("characters", []):
            ck = c["key"]
            c_copy = dict(c)
            if not target_ck or ck == target_ck:
                c_copy["videos_per_character"] = cnt
            chars_payload[ck] = c_copy
        payload = {"characters": chars_payload}
        if not target_ck:
            payload["default_videos_per_character"] = cnt
        updated = _clm.save_character_library_settings(payload)
        print(json.dumps({
            "ok": True,
            "default_videos_per_character": updated.get("default_videos_per_character"),
            "characters": [
                {"key": c["key"], "enabled": c.get("enabled", True), "videos_per_character": c.get("videos_per_character")}
                for c in updated.get("characters", [])
            ],
        }, indent=2, ensure_ascii=False))

    elif args.cmd == "gen-char-image":
        scripts_dir = str(SKILL_DIR / "flow_final_pipeline" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import io, contextlib
        import character_library_manager as _clm
        with contextlib.redirect_stdout(sys.stderr):
            res = _clm.generate_character_or_product_image({
                "mode": args.mode,
                "char_key": args.char,
                "sheet_template_id": args.sheet_template,
                "pid": args.pid,
                "model": args.model,
                "custom_prompt": args.prompt,
            })
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.cmd == "create-video":
        scripts_dir = str(SKILL_DIR / "flow_final_pipeline" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import contextlib
        import product_crawler_bridge as _pcb
        with contextlib.redirect_stdout(sys.stderr):
            res = _pcb.prepare_and_optionally_run_product(
                raw_id_or_url=args.product,
                template_name=args.template,
                crawl_method=args.crawl_method,
                videos_per_character=args.videos_per_char,
                force_regenerate_prompts=True,
                auto_run_pipeline=bool(args.run),
            )
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

