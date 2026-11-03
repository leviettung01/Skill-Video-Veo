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


def _load_projects_index() -> List[Dict[str, Any]]:
    with _STORE_LOCK:
        if not PROJECTS_INDEX_FILE.is_file():
            return []
        try:
            return json.loads(PROJECTS_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []


def _save_projects_index(projects: List[Dict[str, Any]]) -> None:
    with _STORE_LOCK:
        PROJECTS_INDEX_FILE.write_text(
            json.dumps(projects, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def get_project_dir(project_id: str) -> Path:
    d = PROJECTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_project_file(project_id: str) -> Path:
    return get_project_dir(project_id) / "project.json"


def load_project(project_id_or_name: str) -> Optional[Dict[str, Any]]:
    with _STORE_LOCK:
        direct_file = get_project_file(project_id_or_name)
        if direct_file.is_file():
            return json.loads(direct_file.read_text(encoding="utf-8"))
        # Tìm theo tên hoặc ID gần đúng
        idx = _load_projects_index()
        q = project_id_or_name.strip().lower()
        for item in idx:
            if item["id"].lower() == q or item["name"].lower() == q or item["id"].lower().startswith(q):
                f = get_project_file(item["id"])
                if f.is_file():
                    return json.loads(f.read_text(encoding="utf-8"))
        return None


def save_project(proj: Dict[str, Any]) -> Dict[str, Any]:
    with _STORE_LOCK:
        proj["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pfile = get_project_file(proj["id"])
        pfile.write_text(json.dumps(proj, indent=2, ensure_ascii=False), encoding="utf-8")

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
    print(line, flush=True)
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

    FLOW_SUBMIT_DELAY_SEC = 15.0

    def __init__(self, captcha_bridge=None):
        import grok_video_tool as gvt
        self.gvt = gvt
        self.captcha_bridge = captcha_bridge
        self._rr_lock = threading.Lock()
        self._rr_idx = 0
        self._flow_submit_lock = threading.Lock()
        self._last_flow_submit_ts = 0.0

    def _throttle_flow_submit(self, log_fn=None):
        """Giãn cách các request gửi lên Google Flow ~15s giữa các luồng để tránh rate-limit / reCAPTCHA score tụt."""
        with self._flow_submit_lock:
            now = time.time()
            elapsed = now - self._last_flow_submit_ts
            if self._last_flow_submit_ts > 0 and elapsed < self.FLOW_SUBMIT_DELAY_SEC:
                wait_s = self.FLOW_SUBMIT_DELAY_SEC - elapsed
                if log_fn:
                    log_fn(f"⏱️ Chờ {wait_s:.1f}s trước khi gửi request tiếp theo lên Google Flow (delay 15s)...")
                time.sleep(wait_s)
            self._last_flow_submit_ts = time.time()

    def ensure_captcha_bridge(self):
        if self.captcha_bridge is not None:
            return self.captcha_bridge
        # Kiểm tra xem cổng 4000 đã có CaptchaBridge của server hay tool chạy chưa
        import socket
        bridge_port = getattr(self.gvt, "CAPTCHA_BRIDGE_PORT", 4000)
        port_open = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", bridge_port))
                port_open = True
        except Exception:
            pass

        bridge = self.gvt.CaptchaBridge(print, port=bridge_port)
        if not port_open:
            bridge.start()
        self.captcha_bridge = bridge
        return self.captcha_bridge

    def get_accounts_info(self) -> Dict[str, Any]:
        acc_mgr = self.gvt.AccountManager()
        google_accs = []
        grok_accs = []
        for a in acc_mgr.accounts:
            is_google = a.name.startswith("Google_") or (a.api_key and a.api_key.startswith("ya29."))
            entry = {
                "name": a.name,
                "active": a.active,
                "profile_name": getattr(a, "profile_name", ""),
                "proxy_url": a.proxy_url,
                "type": "google_flow" if is_google else "cliproxy",
                "available_video_models": self.gvt.get_veo_ui_video_models(getattr(a, "profile_name", "") or a.name) if is_google else ["grok-imagine-video"],
                "has_low_priority_lite": self.gvt.is_veo_low_priority_available(getattr(a, "profile_name", "") or a.name) if is_google else False,
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

    def _next_account(self, for_veo: bool = True):
        acc_mgr = self.gvt.AccountManager()
        active = [a for a in acc_mgr.accounts if a.active]
        if not active:
            active = acc_mgr.accounts
        if not active:
            return None, "", ""

        if for_veo:
            veo_candidates = [
                a for a in active
                if a.name.startswith("Google_") or (a.api_key and a.api_key.startswith("ya29.")) or getattr(a, "profile_name", "")
            ]
            if veo_candidates:
                active = veo_candidates

        with self._rr_lock:
            acc = active[self._rr_idx % len(active)]
            self._rr_idx += 1

        bearer = acc.api_key if (acc.api_key and acc.api_key.startswith("ya29.")) else ""
        proj_id = acc.proxy_url if (acc.proxy_url and not acc.proxy_url.startswith("http")) else self.gvt.DEFAULT_PROJECT_ID
        return acc, bearer, proj_id

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
        acc, bearer, veo_proj_id = self._next_account(for_veo=is_veo)

        def _log(m: str):
            append_project_log(project_id, f"[{prod['product_name']} | Cảnh {s_num}] {m}")

        if is_veo:
            resolved_cv = resolve_character_and_voice(
                str(scene.get("character_id") or prod.get("character_id") or ""),
                str(scene.get("voice_id") or prod.get("voice_id") or ""),
            )
            eff_proj_id = str(prod.get("flow_project_id") or resolved_cv["project_id"] or veo_proj_id)
            job = self.gvt.VideoJob(
                id=f"skill_img_{prod['id']}_{s_num}_{int(time.time())}",
                model=model,
                prompt=prompt,
                resolution="1K",
                aspect_ratio=aspect,
                local_path=out_base,
            )
            if ref_img and Path(ref_img).is_file():
                job.image_url = ref_img
            if resolved_cv["character_id"]:
                job.character_id = resolved_cv["character_id"]

            self._throttle_flow_submit(_log)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                ok = loop.run_until_complete(
                    self.gvt.run_veo_flow(
                        job, bearer, eff_proj_id, self.captcha_bridge, log=_log, progress=None
                    )
                )
                if ok and job.local_path and Path(job.local_path).is_file():
                    return str(Path(job.local_path).resolve())
                raise RuntimeError(job.error or "Tạo ảnh Google Flow thất bại")
            finally:
                loop.close()
        else:
            # Grok / OpenAI image generation qua CLIProxy (:8317)
            import httpx
            import base64
            proxy = acc.proxy_url if (acc and acc.proxy_url.startswith("http")) else self.gvt.DEFAULT_PROXY_URL
            api_key = acc.api_key if acc else "grok-video-key-001"
            size = "1024x1792" if "9:16" in aspect else ("1792x1024" if "16:9" in aspect else "1024x1024")
            url = f"{proxy}/v1/images/generations"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model, "prompt": prompt, "n": 1, "size": size}
            with self.gvt.make_httpx_client(timeout=300, target_url=url) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Image API error {resp.status_code}: {resp.text[:300]}")
            item = resp.json()["data"][0]
            out_file = out_dir / f"scene_{s_num:02d}.png"
            if item.get("url"):
                with self.gvt.make_httpx_client(timeout=60) as client:
                    r = client.get(item["url"])
                    r.raise_for_status()
                    out_file.write_bytes(r.content)
            elif item.get("b64_json"):
                out_file.write_bytes(base64.b64decode(item["b64_json"]))
            else:
                raise RuntimeError("Không nhận được URL hoặc b64_json từ API ảnh")
            return str(out_file.resolve())

    def _generate_single_scene_video(self, project_id: str, prod: Dict[str, Any], scene: Dict[str, Any]) -> str:
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
        acc, bearer, veo_proj_id = self._next_account(for_veo=is_veo)

        def _log(m: str):
            append_project_log(project_id, f"[{prod['product_name']} | Video Cảnh {s_num}] {m}")

        if is_veo:
            resolved_cv = resolve_character_and_voice(
                str(scene.get("character_id") or prod.get("character_id") or ""),
                str(scene.get("voice_id") or prod.get("voice_id") or ""),
            )
            eff_proj_id = str(prod.get("flow_project_id") or resolved_cv["project_id"] or veo_proj_id)
            vid_mode = "reference-to-video" if resolved_cv["voice_id"] else "image-to-video"
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
            )
            if resolved_cv["voice_id"]:
                job.voice_id = resolved_cv["voice_id"]
                job.reference_image_urls = [source_img]
            self._throttle_flow_submit(_log)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                ok = loop.run_until_complete(
                    self.gvt.run_veo_flow(
                        job, bearer, eff_proj_id, self.captcha_bridge, log=_log, progress=None
                    )
                )
                if ok and job.local_path and Path(job.local_path).is_file():
                    return str(Path(job.local_path).resolve())
                raise RuntimeError(job.error or "Tạo video Veo thất bại")
            finally:
                loop.close()
        else:
            # Grok I2V qua CLIProxy (:8317)
            import base64
            proxy = acc.proxy_url if (acc and acc.proxy_url.startswith("http")) else self.gvt.DEFAULT_PROXY_URL
            api_key = acc.api_key if acc else "grok-video-key-001"
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
            with self.gvt.make_httpx_client(timeout=120) as client:
                resp = client.post(submit_url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Grok Video API error {resp.status_code}: {resp.text[:300]}")
            req_id = resp.json().get("id") or resp.json().get("request_id", "")
            if not req_id:
                raise RuntimeError("Không nhận được request_id từ Grok Video API")

            poll_url = f"{proxy}/v1/videos/{req_id}"
            for _ in range(90):
                time.sleep(8)
                with self.gvt.make_httpx_client(timeout=30) as client:
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
                                with self.gvt.make_httpx_client(timeout=120) as dl:
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

    def run_single_product(self, project_id: str, product_id: str, max_scene_workers: int = 3) -> Dict[str, Any]:
        """Chạy trọn gói 1 sản phẩm: Đa luồng Tạo Ảnh -> Đa luồng Tạo Video -> FFmpeg Ghép Video Final."""
        self.ensure_captcha_bridge()

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

        append_project_log(project_id, f"🚀 [{prod['product_name']}] Bắt đầu tạo ảnh {len(scenes)} phân cảnh (Đa luồng: {max_scene_workers})...")

        # ── BƯỚC 1: ĐA LUỒNG TẠO ẢNH CÁC PHÂN CẢNH ──
        def _img_task(s_idx: int):
            s_obj = prod["scenes"][s_idx]
            if s_obj.get("image_path") and Path(s_obj["image_path"]).is_file():
                return s_idx, s_obj["image_path"], None
            for attempt in range(1, 3):
                try:
                    img_p = self._generate_single_scene_image(project_id, prod, s_obj)
                    return s_idx, img_p, None
                except Exception as e:
                    if attempt == 2:
                        return s_idx, "", str(e)
                    time.sleep(3)
            return s_idx, "", "Unknown error"

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_scene_workers) as pool:
            futs = [pool.submit(_img_task, i) for i in range(len(scenes))]
            for fut in concurrent.futures.as_completed(futs):
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

        img_ready_indices = [
            i for i, s in enumerate(prod["scenes"])
            if s.get("image_path") and Path(s["image_path"]).is_file()
        ]
        if not img_ready_indices:
            _update_state(lambda item: item.update({"status": "failed", "error_msg": "Tất cả phân cảnh đều lỗi tạo ảnh"}))
            append_project_log(project_id, f"❌ [{prod['product_name']}] Thất bại: Không tạo được ảnh phân cảnh nào.")
            return load_project(project_id)

        # ── BƯỚC 2: ĐA LUỒNG TẠO VIDEO I2V TỪ ẢNH PHÂN CẢNH ──
        prod = _update_state(lambda item: item.update({"status": "vid_gen"}))
        append_project_log(project_id, f"🎬 [{prod['product_name']}] Đã xong {len(img_ready_indices)}/{len(scenes)} ảnh. Bắt đầu dựng Video I2V đa luồng...")

        def _vid_task(s_idx: int):
            s_obj = prod["scenes"][s_idx]
            if s_obj.get("video_path") and Path(s_obj["video_path"]).is_file():
                return s_idx, s_obj["video_path"], None
            for attempt in range(1, 3):
                try:
                    vid_p = self._generate_single_scene_video(project_id, prod, s_obj)
                    return s_idx, vid_p, None
                except Exception as e:
                    if attempt == 2:
                        return s_idx, "", str(e)
                    time.sleep(5)
            return s_idx, "", "Unknown video error"

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_scene_workers) as pool:
            futs = [pool.submit(_vid_task, i) for i in img_ready_indices]
            for fut in concurrent.futures.as_completed(futs):
                s_idx, vid_path, err = fut.result()
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

        vid_ready = [s for s in prod["scenes"] if s.get("video_path") and Path(s["video_path"]).is_file()]
        if not vid_ready:
            _update_state(lambda item: item.update({"status": "failed", "error_msg": "Không tạo được video cho phân cảnh nào"}))
            append_project_log(project_id, f"❌ [{prod['product_name']}] Thất bại ở bước tạo video.")
            return load_project(project_id)

        # ── BƯỚC 3: GHÉP VIDEO FINAL BẰNG FFMPEG ──
        prod = _update_state(lambda item: item.update({"status": "assembling"}))
        try:
            final_vid = self._concat_final_video(project_id, prod)
            _update_state(lambda item: item.update({"status": "done", "final_video_path": final_vid, "error_msg": ""}))
            append_project_log(project_id, f"✅ [{prod['product_name']}] HOÀN TẤT VIDEO FINAL: {final_vid}")
        except Exception as e:
            _update_state(lambda item: item.update({"status": "failed", "error_msg": f"Lỗi ghép video: {e}"}))
            append_project_log(project_id, f"❌ [{prod['product_name']}] Lỗi ghép video final: {e}")

        return load_project(project_id)

    def run_project_batch(
        self,
        project_id_or_name: str,
        max_product_workers: int = 2,
        max_scene_workers: int = 3,
        product_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Chạy hàng loạt sản phẩm song song trong dự án."""
        proj = load_project(project_id_or_name)
        if not proj:
            raise ValueError(f"Không tìm thấy dự án: {project_id_or_name}")

        self.ensure_captcha_bridge()
        pid = proj["id"]
        targets = []
        for p in proj.get("products", []):
            if product_ids and p["id"] not in product_ids:
                continue
            if p.get("scenes") and p.get("status") in ("queued", "failed", "img_gen", "vid_gen"):
                targets.append(p["id"])

        if not targets:
            append_project_log(pid, "ℹ️ Không có sản phẩm nào ở trạng thái sẵn sàng chạy (queued/failed có kịch bản).")
            return proj

        append_project_log(
            pid,
            f"🔥 BẮT ĐẦU CHẠY ĐA LUỒNG {len(targets)} SẢN PHẨM (Song song {max_product_workers} sản phẩm x {max_scene_workers} cảnh)...",
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_product_workers) as pool:
            futs = [
                pool.submit(self.run_single_product, pid, prod_id, max_scene_workers)
                for prod_id in targets
            ]
            for fut in concurrent.futures.as_completed(futs):
                try:
                    fut.result()
                except Exception as e:
                    append_project_log(pid, f"⚠️ Lỗi xử lý sản phẩm: {e}")

        final_proj = load_project(pid)
        done_cnt = sum(1 for p in final_proj.get("products", []) if p.get("status") == "done")
        append_project_log(pid, f"🎉 HOÀN THÀNH BATCH DỰ ÁN '{final_proj['name']}': {done_cnt}/{len(final_proj.get('products', []))} sản phẩm có Video Final!")
        return final_proj


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
    p_sub.add_argument("--product-workers", type=int, default=2, help="Số sản phẩm chạy song song")
    p_sub.add_argument("--scene-workers", type=int, default=3, help="Số phân cảnh chạy song song mỗi sản phẩm")

    # 7. run-batch
    p_run = sub.add_parser("run-batch", help="Chạy đa luồng tạo Ảnh -> Video -> Final cho dự án")
    p_run.add_argument("--project", required=True, help="Tên hoặc ID dự án")
    p_run.add_argument("--product-workers", type=int, default=2, help="Số sản phẩm chạy song song")
    p_run.add_argument("--scene-workers", type=int, default=3, help="Số phân cảnh chạy song song mỗi sản phẩm")

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


if __name__ == "__main__":
    main()

