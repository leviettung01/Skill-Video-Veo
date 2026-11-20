# -*- coding: utf-8 -*-
"""
Quản lý danh sách các Template Video trong thư mục gốc `Template/`.
Mỗi thư mục con trong `Template/<Tên Template>` (ví dụ: `Template/Nhà Xưởng`, `Template/Đồ Ăn Vặt`)
chứa:
  - template_config.json
  - SKILL.md
  - KICH_BAN.md
  - PROMPT_TEMPLATES.md
  - RENDER.md
  - generator.py
  - demo_videos/ (các video demo thực tế 9:16 của template)
  - demo_images/ (các ảnh demo thực tế: ảnh gốc sản phẩm, ảnh ref 2K / storyboard từng cảnh)
"""
import io
import os
import re
import sys
import glob
import json
import shutil
import subprocess
import urllib.parse
import zipfile
import importlib.util
from pathlib import Path

WS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMPLATE_ROOT_DIR = os.path.join(WS_DIR, "Template")
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
VOICES_CHARS_PATH = os.path.join(WS_DIR, "flow_final_pipeline", "voices_and_characters.json")

RESERVED_SUBFOLDERS = {
    "Character_Sheet_Templates",
    "Thumbnail_Templates",
    "Subtitle_Templates",
    "__pycache__",
    "Biến hình Làm nông, Bán cá",
}


def ensure_template_root():
    os.makedirs(TEMPLATE_ROOT_DIR, exist_ok=True)


def _prettify_media_label(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    stem = re.sub(r"^\d+[a-z]?_", "", stem)
    stem = stem.replace("_", " ").replace("-", " ").strip()
    label_map = {
        "demo nha xuong that lung nv1": "🎬 Video Final: Thắt Lưng Nam (NV1 - Xưởng Lắp Ráp)",
        "demo nha xuong can tieu ly nv1": "🎬 Video Final: Cân Tiểu Ly Inox 304 (NV1 - Xưởng SX)",
        "demo nha xuong can tieu ly nv2": "🎬 Video Final: Cân Tiểu Ly Inox 304 (NV2 - Phòng QC)",
        "FINAL Banh Pia Mini Mix Vi": "🎬 Video Final: Bánh Pía Mini Mix 10 Vị Cô An (Full 8 Cảnh)",
        "FINAL Hat Dac Rim Chanh Day": "🎬 Video Final: Hạt Đác Rim Chanh Dây BaoQuang Food",
        "FINAL Hoanh Thanh Haidilao": "🎬 Video Final: Hoành Thánh Haidilao 3 Vị Nóng Hổi",
        "Banh Pia Canh1 Pack Hero": "Cảnh 1: Pack Hero Giỏ Bánh Pía Trên Quầy Tiệm",
        "Banh Pia Canh2 Mo Goi": "Cảnh 2: Bóc Gói Lộ Bánh Pía Vàng Mềm",
        "Banh Pia Canh4 Be Doi Trung Chay": "Cảnh 4: Bẻ Đôi Lộ Nhân Kim Sa Trứng Chảy",
        "Hat Dac Canh1 Hook Ly Da": "Cảnh 1: Hook Ly Chanh Dây Đá Lạnh Cạnh Hũ Hạt Đác",
        "Hat Dac Canh3 Muc Sot Sanh": "Cảnh 3: Macro Muỗng Múc Hạt Đác Sốt Chanh Dây Sánh",
        "Hat Dac Canh5 Rot Nuoc Chanh Day": "Cảnh 5: Rót Nước Chanh Dây Vào Ly Đá Topping",
        "Hoanh Thanh Haidilao Cham Nuoc Soi": "Cảnh 3: Châm Nước Sôi Bốc Khói Vào Cốc Haidilao",
        "anh goc that lung": "Ảnh Gốc SP: Thắt Lưng Nam",
        "anh ref 2k nv1 xuong lap rap": "Ảnh Ref 2K: NV1 Cầm Thắt Lưng Tại Xưởng",
        "anh ref 2k nv2 phong qc": "Ảnh Ref 2K: NV2 Cầm Thắt Lưng Phòng QC",
        "anh goc can tieu ly": "Ảnh Gốc SP: Cân Tiểu Ly Inox 304",
        "anh ref 2k nv1 can tieu ly": "Ảnh Ref 2K: NV1 Cầm Cân Tiểu Ly",
        "anh ref 2k nv2 can tieu ly": "Ảnh Ref 2K: NV2 Cầm Cân Tiểu Ly",
        "banh pia s1 pack hero": "Storyboard Cảnh 1: Giỏ Bánh Pía Trên Quầy Hà Nội",
        "banh pia s2 mo goi": "Storyboard Cảnh 2: Bóc Gói Bánh Pía Mini",
        "banh pia s4 be doi trung chay": "Storyboard Cảnh 4: Bẻ Đôi Nhân Trứng Chảy",
        "banh pia s5 khay 10 vi": "Storyboard Cảnh 5: Khay 10 Vị Cắt Đôi",
        "hat dac s1 ly chanh day": "Storyboard Cảnh 1: Ly Chanh Dây Bàn Học Gen Z",
        "hat dac s3 muc sot": "Storyboard Cảnh 3: Muỗng Múc Hạt Đác Sốt Vàng",
        "haidilao s1 pack hero": "Storyboard Cảnh 1: Bộ 3 Cốc Hoành Thánh Haidilao",
        "haidilao s5 muc hoanh thanh": "Storyboard Cảnh 5: Muỗng Múc Hoành Thánh Nhân Thịt",
        "character sheet 4 outfits 2k": "Bảng Nhân Vật 2K: 4 Góc Mặt + 4 Bộ Đồ Lookbook",
        "character sheet basic poses 2k": "Bảng Nhân Vật 2K: Xoay 360° + 5 Tư Thế Tạo Dáng",
        "product sheet quan xanh 2k": "Bộ Đồ 1 (2K): Áo Yếm Vàng Hoa Đỏ + Quần Suông Xanh Coban",
        "product sheet vay vang 2k": "Bộ Đồ 2 (2K): Váy Ngắn Xếp Tầng Vàng Bơ + Túi Nhún Bèo",
        "product sheet quan sooc trang 2k": "Bộ Đồ 3 Alt (2K): Áo Yếm Vàng + Quần Soóc Trắng Xếp Ly",
        "product sheet quan be 2k": "Bộ Đồ 3 (2K): Áo Yếm Vàng + Quần Ống Rộng Màu Be + Kính Hồng",
        "nhan vat basic phong ngu 2k": "Ảnh Ref Nhân Vật Gốc 2K: Đứng Trong Phòng Ngủ (Ảnh 1)",
        "demo google flow phan canh 1 8s": "Thực Tế Google Flow Cảnh 1 (0s-8s): Thay Bộ Đồ 1 Tại 4:04",
        "demo google flow phan canh 2 8s": "Thực Tế Google Flow Cảnh 2 (8s-16s): Thay Bộ 2 (3:04) & Bộ 3 (6:12)",
        "final motion control video ref 16s": "🎬 Video Gốc Tham Chiếu (16.28s) -> Chia 2 Cảnh × 8s",
        "phan canh 1 clip ref 0s 8s": "✂️ Phân Cảnh 1 Đã Cắt (0.00s - 8.00s | Đổi Đồ Tại 4:04)",
        "phan canh 2 clip ref 8s 16s": "✂️ Phân Cảnh 2 Đã Cắt (8.00s - 16.00s | Đổi Đồ Tại 3:04 & 6:12)",
    }
    for k, v in label_map.items():
        if k.lower() in stem.lower():
            return v
    return stem.title()


def _scan_template_demo_media(tdir: str) -> tuple:
    dv_dir = os.path.join(tdir, "demo_videos")
    di_dir = os.path.join(tdir, "demo_images")
    demo_videos = []
    demo_images = []

    if os.path.isdir(dv_dir):
        for vp in sorted(glob.glob(os.path.join(dv_dir, "*.mp4"))):
            fn = os.path.basename(vp)
            demo_videos.append({
                "filename": fn,
                "label": _prettify_media_label(fn),
                "is_final": "final" in fn.lower() or "demo_nha_xuong" in fn.lower(),
                "path": vp,
                "url": "/api/media?path=" + urllib.parse.quote(vp),
            })

    if os.path.isdir(di_dir):
        imgs = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            imgs.extend(glob.glob(os.path.join(di_dir, ext)))
        for ip in sorted(imgs):
            fn = os.path.basename(ip)
            demo_images.append({
                "filename": fn,
                "label": _prettify_media_label(fn),
                "path": ip,
                "url": "/api/media?path=" + urllib.parse.quote(ip),
            })

    return demo_videos, demo_images


def list_video_templates() -> list:
    """Liệt kê tất cả các Template Video trong thư mục `Template/` kèm mã số độc nhất (001, 002...), 1 video demo hoàn thiện và Role Skill."""
    ensure_template_root()
    templates = []
    used_codes = set()
    raw_entries = []

    for entry in sorted(os.listdir(TEMPLATE_ROOT_DIR)):
        if entry in RESERVED_SUBFOLDERS or entry.startswith("."):
            continue
        tdir = os.path.join(TEMPLATE_ROOT_DIR, entry)
        if not os.path.isdir(tdir):
            continue
        cfg_path = os.path.join(tdir, "template_config.json")
        cfg = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                pass
        code = str(cfg.get("code") or cfg.get("template_code") or "").strip()
        if code:
            used_codes.add(code)
        raw_entries.append((entry, tdir, cfg_path, cfg))

    next_code_int = 1
    for entry, tdir, cfg_path, cfg in raw_entries:
        code = str(cfg.get("code") or cfg.get("template_code") or "").strip()
        if not code:
            while f"{next_code_int:03d}" in used_codes:
                next_code_int += 1
            code = f"{next_code_int:03d}"
            used_codes.add(code)
            cfg["code"] = code
            try:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        md_files = [
            fn for fn in ("ROLE_SKILL.md", "SKILL.md", "KICH_BAN.md", "PROMPT_TEMPLATES.md", "RENDER.md", "WORKFLOW_GUIDE.md", "template_config.json", "generator.py")
            if os.path.exists(os.path.join(tdir, fn))
        ]
        demo_videos, demo_images = _scan_template_demo_media(tdir)
        # Chỉ giữ 1 video demo hoàn thiện chất lượng tốt nhất để hiển thị trên Chợ Template
        primary_demo_video = demo_videos[0] if demo_videos else None
        demo_caption = cfg.get("demo_video_caption") or (primary_demo_video["label"] if primary_demo_video else "Video Demo 1080p 60 FPS")
        if primary_demo_video:
            primary_demo_video["label"] = demo_caption

        pipeline_kind = str(cfg.get("pipeline_kind") or "product")
        raw_ui_studio = str(cfg.get("ui_studio") or "").strip().lower()
        raw_presets = cfg.get("presets") or cfg.get("transform_presets")
        preset_titles: list[str] = []
        if isinstance(raw_presets, dict):
            preset_titles = [str((v or {}).get("title") or k) for k, v in raw_presets.items()]
        elif isinstance(raw_presets, list):
            preset_titles = [str((v or {}).get("title") or (v or {}).get("id") or f"Kịch bản {i}") for i, v in enumerate(raw_presets, 1) if isinstance(v, dict)]
        if (
            raw_ui_studio in {"transform", "transform_studio", "character_product"}
            or pipeline_kind.lower() in {"fashion_transformation", "transform_studio", "character_product_studio"}
            or bool(preset_titles)
            or code == "006"
        ):
            ui_studio = "transform"
            if not preset_titles and code == "006":
                preset_titles = ["Làm nông", "Bán cá"]
        elif pipeline_kind.lower() == "cooking":
            ui_studio = "cooking"
        elif pipeline_kind.lower() == "fashion_motion":
            ui_studio = "fashion_motion"
        else:
            ui_studio = "standard"

        templates.append({
            "code": code,
            "id": cfg.get("id") or entry.lower().replace(" ", "_"),
            "folder_name": entry,
            "name": cfg.get("name") or cfg.get("template_name") or entry,
            "subtitle": cfg.get("subtitle") or "",
            "badge": cfg.get("badge") or "TEMPLATE VIDEO",
            "category": cfg.get("category") or "Thương Mại Điện Tử / TikTok Affiliate",
            "pipeline_kind": pipeline_kind,
            "ui_studio": ui_studio,
            "supports_character": cfg.get("supports_character", True) is not False if ui_studio == "transform" else bool(cfg.get("supports_character", False)),
            "supports_product": cfg.get("supports_product", True) is not False,
            "presets_count": len(preset_titles),
            "preset_titles": preset_titles,
            "input_kind": cfg.get("input_kind", "product"),
            "has_subtitles": cfg.get("has_subtitles", True),
            "price_label": cfg.get("price_label") or "Miễn Phí • Sẵn Sàng",
            "tier_badge": cfg.get("tier_badge") or "🔥 CHỢ TEMPLATE",
            "author": cfg.get("author") or "Lê Việt Tùng - SkillAutoVeo",
            "zalo": cfg.get("zalo") or "0915967790",
            "facebook": cfg.get("facebook") or "https://www.facebook.com/tungbinh.38/",
            "description": cfg.get("description") or f"Template tạo video tự động từ thư mục Template/{entry}",
            "default_videos_per_character": int(cfg.get("default_videos_per_character", 3)),
            "scenes_per_video": int(cfg.get("scenes_per_video", 3)),
            "scene_duration_sec": int(cfg.get("scene_duration_sec", 10)),
            "video_aspect": cfg.get("video_aspect", "9:16"),
            "image_resolution": cfg.get("image_resolution", "2K (1536x2752)"),
            "video_resolution": cfg.get("video_resolution", "1080p • 60 FPS"),
            "image_model": cfg.get("image_model", "Nano Banana 2.1 / GPT-Image-2"),
            "video_model": cfg.get("video_model", "Veo 3.1 / Grok Video 1.5"),
            "tags": cfg.get("tags", []),
            "highlights": cfg.get("highlights", []),
            "workflow_steps": cfg.get("workflow_steps", []),
            "scene_breakdown": cfg.get("scene_breakdown", []),
            "sample_products": cfg.get("sample_products", []),
            "primary_demo_video": primary_demo_video,
            "demo_video_caption": demo_caption,
            "demo_videos": [primary_demo_video] if primary_demo_video else [],
            "demo_images": demo_images,
            "role_skill_file": cfg.get("role_skill_file") or ("ROLE_SKILL.md" if "ROLE_SKILL.md" in md_files else "SKILL.md"),
            "ai_agent_command_example": cfg.get("ai_agent_command_example") or f"Tạo video cho sản phẩm <Link_hoặc_ID> theo template {code}",
            "folder_path": tdir,
            "files": md_files,
        })

    templates.sort(key=lambda x: (str(x.get("code") or "999"), x["folder_name"]))
    return templates


def resolve_template_dir(template_name_or_id: str = "") -> str:
    """
    Tìm đường dẫn thư mục Template theo:
      - Mã số độc nhất: '001', '1', '#001', 'template 001', 'tpl 001', 'mã 001'
      - ID hoặc Tên thư mục: 'nha_xuong', 'Nhà Xưởng', 'do_an_vat_pov_voice', v.v.
    Mặc định: `Template/Nhà Xưởng` (Mã 001).
    """
    ensure_template_root()
    q = (template_name_or_id or "").strip().lower()
    templates = list_video_templates()
    if q:
        # 1. Kiểm tra nếu chuỗi truyền vào là mã số (001, 1, #001, template 001, tpl-002...)
        m_code = re.match(r"^(?:template|tpl|ma|mã|#|\s|-|_)*0*(\d{1,4})$", q)
        if m_code:
            target_num = int(m_code.group(1))
            target_code = f"{target_num:03d}"
            for t in templates:
                if t.get("code") == target_code or str(t.get("code")).lstrip("0") == str(target_num):
                    return t["folder_path"]

        # 2. Kiểm tra khớp chính xác code, folder_name hoặc id
        for t in templates:
            if (
                str(t.get("code") or "").lower() == q
                or t["folder_name"].lower() == q
                or t["id"].lower() == q
            ):
                return t["folder_path"]

        # 3. Kiểm tra khớp một phần tên hoặc "[001]" trong chuỗi dropdown
        m_bracket = re.search(r"#?0*(\d{1,3})\b", q)
        if m_bracket:
            target_code = f"{int(m_bracket.group(1)):03d}"
            for t in templates:
                if t.get("code") == target_code:
                    return t["folder_path"]

        for t in templates:
            if q in t["folder_name"].lower() or q in t["name"].lower() or q in t["id"].lower():
                return t["folder_path"]

    default_dir = os.path.join(TEMPLATE_ROOT_DIR, "Nhà Xưởng")
    if os.path.isdir(default_dir):
        return default_dir
    if templates:
        return templates[0]["folder_path"]
    os.makedirs(default_dir, exist_ok=True)
    return default_dir


def _template_scene_examples(cfg):
    """Use real saved projects, with provenance; never invent media for a scene."""
    ids = list(cfg.get('demo_project_ids') or [])
    ids += [p['product_id'] for p in cfg.get('sample_products', []) if p.get('product_id')]
    try:
        with open(os.path.join(PROJECTS_DIR, 'projects_index.json'), encoding='utf-8') as f:
            ids += [p['id'] for p in json.load(f) if str(p.get('template_code', '')).zfill(3) == str(cfg.get('code', '')).zfill(3) and p.get('done_products')]
    except (OSError, ValueError):
        pass
    result = []
    for pid in dict.fromkeys(ids):
        if os.path.basename(pid) != pid:
            continue
        try:
            with open(os.path.join(PROJECTS_DIR, pid, 'project.json'), encoding='utf-8') as f:
                project = json.load(f)
            product = next((p for p in project.get('products', []) if p.get('final_video_path') and os.path.isfile(p['final_video_path'])), None)
            if not product:
                continue
            result.append({'id': pid, 'name': project.get('name', pid), 'final_video_path': product['final_video_path'],
                           'scenes': [dict({k: s.get(k) for k in ('scene_number','scene_title','scene_description','image_prompt','video_prompt','image_path','video_path','actions')},
                                           duration_sec=s.get('duration_sec') or product.get('seconds_per_scene') or cfg.get('scene_duration_sec')) for s in product.get('scenes', [])]})
            if len(result) >= 3:
                break
        except (OSError, ValueError):
            continue
    return result


def get_template_detail(template_name_or_id: str) -> dict:
    tdir = resolve_template_dir(template_name_or_id)
    folder_name = os.path.basename(tdir)
    docs = {}
    doc_order = ("ROLE_SKILL.md", "MASTER_PROMPT.md", "GENERATED_PROMPTS_V2.md", "SKILL.md", "KICH_BAN.md", "PROMPT_TEMPLATES.md", "RENDER.md", "WORKFLOW_GUIDE.md", "template_config.json", "generator.py")
    for fn in doc_order:
        fp = os.path.join(tdir, fn)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    docs[fn] = f.read()
            except Exception:
                docs[fn] = ""
    cfg = {}
    try:
        if docs.get("template_config.json"):
            cfg = json.loads(docs["template_config.json"])
    except Exception:
        pass
    demo_videos, demo_images = _scan_template_demo_media(tdir)
    primary_demo_video = demo_videos[0] if demo_videos else None
    return {
        "ok": True,
        "code": cfg.get("code") or "001",
        "folder_name": folder_name,
        "folder_path": tdir,
        "config": cfg,
        "primary_demo_video": primary_demo_video,
        "demo_videos": demo_videos,
        "demo_images": demo_images,
        "demo_projects": _template_scene_examples(cfg),
        "docs": docs,
    }


def save_template_doc(template_name_or_id: str, doc_name: str, content: str) -> dict:
    """Lưu chỉnh sửa Role Skill / Kịch bản / Cấu hình trực tiếp vào thư mục Template/<Folder>."""
    tdir = resolve_template_dir(template_name_or_id)
    allowed_docs = {"ROLE_SKILL.md", "SKILL.md", "KICH_BAN.md", "PROMPT_TEMPLATES.md", "RENDER.md", "WORKFLOW_GUIDE.md", "template_config.json"}
    clean_name = os.path.basename((doc_name or "ROLE_SKILL.md").strip())
    if clean_name not in allowed_docs and not clean_name.lower().endswith(".md"):
        return {"ok": False, "error": f"Không hỗ trợ sửa file {clean_name}"}

    if clean_name == "template_config.json":
        try:
            json.loads(content)
        except Exception as e:
            return {"ok": False, "error": f"JSON không hợp lệ: {e}"}

    fp = os.path.join(tdir, clean_name)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)

    # Nếu sửa ROLE_SKILL.md thì đồng bộ sang SKILL.md trong cùng Template để đồng nhất
    if clean_name == "ROLE_SKILL.md":
        skill_fp = os.path.join(tdir, "SKILL.md")
        try:
            with open(skill_fp, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    return {
        "ok": True,
        "folder_name": os.path.basename(tdir),
        "doc_name": clean_name,
        "path": fp,
    }


def load_characters_config() -> dict:
    if os.path.exists(VOICES_CHARS_PATH):
        try:
            with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"default_videos_per_character": 3, "voices": {}, "characters": {}}


def generate_prompts_for_product(
    pid: str,
    template_name: str = "Nhà Xưởng",
    videos_per_character: int = None,
    primary_product_refs: list = None,
    slide_overlay_files: list = None,
    force_regenerate: bool = False,
) -> dict:
    """
    Sinh `prompts.json` và `spec_*.json` cho sản phẩm `pid` sử dụng Template được chọn.
    """
    pdir = os.path.join(PROJECTS_DIR, pid)
    os.makedirs(pdir, exist_ok=True)
    prod_img_dir = os.path.join(pdir, "product_images")
    os.makedirs(prod_img_dir, exist_ok=True)

    prompts_path = os.path.join(pdir, "prompts.json")
    info_data = {}
    for cand_info in (os.path.join(pdir, "info.json"), os.path.join(prod_img_dir, "info.json")):
        if os.path.exists(cand_info):
            try:
                with open(cand_info, "r", encoding="utf-8") as f:
                    info_data = json.load(f)
                if info_data:
                    break
            except Exception:
                pass

    chars_cfg = load_characters_config()
    target_vpc = int(videos_per_character or chars_cfg.get("default_videos_per_character", 3))
    tdir = resolve_template_dir(template_name)
    if os.path.isfile(os.path.join(tdir, "template_config.json")):
        with open(os.path.join(tdir, "template_config.json"), encoding="utf-8") as cooking_cfg_file:
            pipeline_kind = json.load(cooking_cfg_file).get("pipeline_kind")
            if pipeline_kind == "fashion_transformation":
                raise ValueError("Mở Template 006 trong Chợ Template để chọn ảnh quần áo và kịch bản.")
            if pipeline_kind == "cooking_storyboard":
                raise ValueError("Template 005 dùng công thức nấu ăn. Mở Nấu Ăn POV trong Chợ Template hoặc dùng cooking_storyboard_engine.py.")
    target_tpl_folder = os.path.basename(tdir)

    # Nếu prompts.json đã tồn tại và không bắt buộc tạo lại, kiểm tra xem đã khớp CHÍNH XÁC template_id / template_code chưa
    custom_cfg_path = os.path.join(tdir, "template_config.json")
    tpl_cfg_obj = {}
    if os.path.exists(custom_cfg_path):
        try:
            with open(custom_cfg_path, "r", encoding="utf-8") as f_cfg:
                tpl_cfg_obj = json.load(f_cfg)
        except Exception:
            tpl_cfg_obj = {}
    target_tpl_id = str(tpl_cfg_obj.get("id") or "").strip().lower()
    target_tpl_code = str(tpl_cfg_obj.get("code") or "001").strip()

    if os.path.exists(prompts_path) and not force_regenerate:
        try:
            with open(prompts_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_vids = existing.get("videos", {})
            existing_id = str(existing.get("template_id") or "").strip().lower()
            existing_name = str(existing.get("template_name") or "").strip().lower()
            is_exact_match = (
                (target_tpl_id and existing_id == target_tpl_id)
                or (existing_name == target_tpl_folder.lower())
            )
            if existing_vids and (not template_name or is_exact_match):
                updated = False
                if primary_product_refs:
                    existing["primary_product_refs"] = primary_product_refs
                    for vk, vv in existing_vids.items():
                        vv["primary_product_refs"] = primary_product_refs
                    updated = True
                if slide_overlay_files:
                    existing["slide_overlay_files"] = slide_overlay_files
                    for vk, vv in existing_vids.items():
                        vv["slide_overlay_files"] = slide_overlay_files
                    updated = True
                if updated:
                    with open(prompts_path, "w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
                return existing
        except Exception:
            pass

    gen_path = os.path.join(tdir, "generator.py")
    if not os.path.exists(gen_path):
        gen_path = os.path.join(TEMPLATE_ROOT_DIR, "Nhà Xưởng", "generator.py")

    spec = importlib.util.spec_from_file_location("template_generator_mod", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if os.path.exists(custom_cfg_path):
        mod.CONFIG_PATH = custom_cfg_path
        if hasattr(mod, "_mod"):
            mod._mod.CONFIG_PATH = custom_cfg_path

    prompts_obj = mod.generate_project_from_template(
        pid=pid,
        pdir=pdir,
        info_data=info_data,
        characters_data=chars_cfg,
        videos_per_character=videos_per_character,
        primary_product_refs=primary_product_refs,
        slide_overlay_files=slide_overlay_files,
    )
    if isinstance(prompts_obj, dict):
        prompts_obj["template_code"] = target_tpl_code
        if target_tpl_id:
            prompts_obj["template_id"] = target_tpl_id
        prompts_obj["template_name"] = target_tpl_folder
        for _, vv in (prompts_obj.get("videos") or {}).items():
            if isinstance(vv, dict):
                vv["template_code"] = target_tpl_code
                if target_tpl_id:
                    vv["template_id"] = target_tpl_id
                vv["template_name"] = target_tpl_folder
        try:
            with open(prompts_path, "w", encoding="utf-8") as f:
                json.dump(prompts_obj, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return prompts_obj


# ==============================================================================
# CẬP NHẬT CODE / TEMPLATE MỚI (GIT FAST-FORWARD & GÓI .ZIP AN TOÀN)
# ==============================================================================

_DANGEROUS_ZIP_EXTS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".dll", ".msi", ".scr", ".com"}


def _run_git(args: list[str], timeout: int = 35) -> tuple[int, str, str]:
    git_bin = shutil.which("git")
    if not git_bin:
        return (127, "", "Máy chưa cài Git CLI.")
    try:
        r = subprocess.run(
            [git_bin, "-C", WS_DIR, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return (r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip())
    except Exception as exc:
        return (1, "", str(exc))


def _extract_template_folders_from_paths(paths: list[str]) -> list[str]:
    folders: list[str] = []
    for p in paths:
        norm = str(p or "").replace("\\", "/").lstrip("./")
        if norm.startswith("Template/"):
            parts = norm.split("/")
            if len(parts) >= 2 and parts[1] and parts[1] not in RESERVED_SUBFOLDERS:
                if parts[1] not in folders:
                    folders.append(parts[1])
    return folders


def check_code_updates() -> dict:
    """Kiểm tra phiên bản Git cục bộ so với remote origin mà không ghi đè dữ liệu người dùng."""
    git_dir = os.path.join(WS_DIR, ".git")
    if not os.path.isdir(git_dir) or not shutil.which("git"):
        return {
            "ok": True,
            "git_available": False,
            "can_import_zip": True,
            "has_updates": False,
            "behind_count": 0,
            "message": "Bản cài đặt không gắn Git — hãy dùng nút Cài Gói Template (.ZIP) để nạp template mới ngay.",
        }

    rc_b, branch, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    rc_h, head_short, _ = _run_git(["rev-parse", "--short", "HEAD"])
    _, remote_url, _ = _run_git(["remote", "get-url", "origin"])
    rc_f, _, err_f = _run_git(["fetch", "origin", "--prune"], timeout=45)
    if rc_f != 0:
        return {
            "ok": True,
            "git_available": True,
            "can_import_zip": True,
            "has_updates": False,
            "behind_count": 0,
            "branch": branch or "main",
            "head": head_short or "",
            "remote_url": remote_url,
            "network_error": err_f or "Không kết nối được tới máy chủ Git.",
            "message": f"Không kiểm tra được bản cập nhật ({err_f or 'offline'}). Bạn vẫn có thể cài gói .ZIP trực tiếp.",
        }

    rc_up, upstream, _ = _run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if rc_up != 0 or not upstream:
        upstream = f"origin/{branch}" if branch and branch != "HEAD" else "origin/main"

    _, behind_raw, _ = _run_git(["rev-list", "--count", f"HEAD..{upstream}"])
    _, ahead_raw, _ = _run_git(["rev-list", "--count", f"{upstream}..HEAD"])
    behind = int(behind_raw) if str(behind_raw).isdigit() else 0
    ahead = int(ahead_raw) if str(ahead_raw).isdigit() else 0

    incoming_files: list[str] = []
    commit_notes: list[str] = []
    if behind > 0:
        _, diff_out, _ = _run_git(["diff", "--name-only", f"HEAD..{upstream}"])
        incoming_files = [ln.strip() for ln in diff_out.splitlines() if ln.strip()]
        _, log_out, _ = _run_git(["log", "--oneline", "-n", "6", f"HEAD..{upstream}"])
        commit_notes = [ln.strip() for ln in log_out.splitlines() if ln.strip()]

    _, mod_unstaged, _ = _run_git(["diff", "--name-only"])
    _, mod_staged, _ = _run_git(["diff", "--cached", "--name-only"])
    local_modified = sorted({ln.strip() for ln in (mod_unstaged + "\n" + mod_staged).splitlines() if ln.strip()})
    conflicts = sorted(set(local_modified) & set(incoming_files))
    new_templates = _extract_template_folders_from_paths(incoming_files)

    return {
        "ok": True,
        "git_available": True,
        "can_import_zip": True,
        "branch": branch or "main",
        "upstream": upstream,
        "head": head_short or "",
        "remote_url": remote_url,
        "has_updates": behind > 0,
        "behind_count": behind,
        "ahead_count": ahead,
        "incoming_files": incoming_files[:60],
        "incoming_templates": new_templates,
        "commit_notes": commit_notes,
        "conflicts": conflicts,
        "message": (
            f"Có {behind} bản cập nhật mới ({len(new_templates)} thư mục template thay đổi)."
            if behind > 0 else "Hệ thống và Chợ Template đang ở phiên bản mới nhất."
        ),
    }


def sync_updates_from_git() -> dict:
    """Kéo bản cập nhật code & template mới nhất qua `git pull --ff-only`, bảo vệ tuyệt đối dữ liệu dự án."""
    status = check_code_updates()
    if not status.get("git_available"):
        return {
            "ok": False,
            "error": status.get("message") or "Thư mục cài đặt không dùng Git. Hãy dùng chức năng Cài Gói Template (.ZIP).",
        }
    if status.get("network_error"):
        return {"ok": False, "error": f"Không thể kết nối Git remote: {status['network_error']}"}
    if not status.get("has_updates"):
        return {
            "ok": True,
            "up_to_date": True,
            "head": status.get("head", ""),
            "updated_files": [],
            "updated_templates": [],
            "message": "Bạn đang dùng phiên bản mới nhất rồi.",
            "templates": list_video_templates(),
        }
    if status.get("conflicts"):
        c_list = ", ".join(status["conflicts"][:5])
        return {
            "ok": False,
            "conflicts": status["conflicts"],
            "error": f"Có thay đổi cục bộ trùng với bản cập nhật ({c_list}). Hãy commit/sao lưu trước khi cập nhật.",
        }

    rc_p, out_p, err_p = _run_git(["pull", "--ff-only"], timeout=60)
    if rc_p != 0:
        return {
            "ok": False,
            "error": f"Không thể tự đồng bộ (pull --ff-only): {err_p or out_p or 'Lịch sử commit bị rẽ nhánh'}",
        }

    _, new_head, _ = _run_git(["rev-parse", "--short", "HEAD"])
    templates = list_video_templates()
    return {
        "ok": True,
        "up_to_date": False,
        "head": new_head or "",
        "updated_files": status.get("incoming_files", []),
        "updated_templates": status.get("incoming_templates", []),
        "message": f"Đã cập nhật thành công lên bản {new_head or 'mới'} ({len(templates)} template sẵn sàng)!",
        "templates": templates,
    }


def _safe_zip_rel_parts(member_name: str) -> list[str] | None:
    raw = str(member_name or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        return None
    parts = [p for p in raw.split("/") if p and p != "."]
    if not parts or any(p == ".." for p in parts):
        return None
    return parts


def _sanitize_template_folder_name(raw_name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(raw_name or "").strip()).strip(". ")
    if not clean or clean in {".", ".."} or clean in RESERVED_SUBFOLDERS:
        return ""
    return clean[:80]


def import_template_zip(zip_bytes: bytes, overwrite: bool = True) -> dict:
    """
    Cài đặt / cập nhật một gói Template (.zip) vào `Template/<Folder>/`.
    Hỗ trợ cả zip có `template_config.json` ở root, `<Folder>/template_config.json`, hoặc `Template/<Folder>/template_config.json`.
    Bảo vệ Zip-Slip, symlink và giới hạn kích thước giải nén.
    """
    if not zip_bytes or len(zip_bytes) > 160 * 1024 * 1024:
        raise ValueError("File ZIP trống hoặc vượt quá 160 MB.")

    ensure_template_root()
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("File tải lên không phải gói .ZIP hợp lệ.") from exc

    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if not infos:
            raise ValueError("Gói ZIP rỗng.")
        if len(infos) > 500:
            raise ValueError("Gói ZIP chứa quá nhiều tệp (tối đa 500 tệp).")

        total_size = 0
        parsed_entries: list[tuple[zipfile.ZipInfo, list[str]]] = []
        config_candidates: list[tuple[int, zipfile.ZipInfo, list[str]]] = []

        for info in infos:
            is_symlink = ((info.external_attr >> 16) & 0o170000) == 0o120000
            if is_symlink:
                raise ValueError(f"Gói ZIP chứa liên kết (symlink) không an toàn: {info.filename}")
            parts = _safe_zip_rel_parts(info.filename)
            if not parts:
                raise ValueError(f"Đường dẫn tệp không hợp lệ trong ZIP: {info.filename}")
            if parts[0] in {"__MACOSX", ".git"}:
                continue
            ext = Path(parts[-1]).suffix.lower()
            if ext in _DANGEROUS_ZIP_EXTS:
                raise ValueError(f"Không cho phép tệp thực thi ({ext}) trong gói template: {parts[-1]}")
            total_size += int(info.file_size or 0)
            if total_size > 400 * 1024 * 1024:
                raise ValueError("Tổng dung lượng giải nén vượt quá 400 MB.")
            parsed_entries.append((info, parts))
            if parts[-1] == "template_config.json":
                config_candidates.append((len(parts), info, parts))

        if not config_candidates:
            raise ValueError("Gói ZIP thiếu tệp `template_config.json`.")

        config_candidates.sort(key=lambda t: t[0])
        _, cfg_info, cfg_parts = config_candidates[0]
        try:
            cfg_obj = json.loads(zf.read(cfg_info).decode("utf-8-sig"))
            if not isinstance(cfg_obj, dict):
                raise ValueError("template_config.json phải là JSON object.")
        except Exception as exc:
            raise ValueError(f"Không đọc được template_config.json: {exc}") from exc

        prefix_parts = cfg_parts[:-1]
        if not prefix_parts:
            raw_folder = str(cfg_obj.get("folder_name") or cfg_obj.get("name") or cfg_obj.get("template_name") or cfg_obj.get("id") or "Template_Moi")
        elif len(prefix_parts) >= 2 and prefix_parts[0].lower() == "template":
            raw_folder = prefix_parts[1]
            prefix_parts = prefix_parts[:2]
        else:
            raw_folder = prefix_parts[0]
            prefix_parts = prefix_parts[:1]

        folder_name = _sanitize_template_folder_name(raw_folder)
        if not folder_name:
            raise ValueError(f"Tên thư mục template không hợp lệ hoặc bị trùng vùng hệ thống: {raw_folder}")

        target_root = Path(TEMPLATE_ROOT_DIR).resolve()
        dest_dir = (target_root / folder_name).resolve()
        if not dest_dir.is_relative_to(target_root) or dest_dir == target_root:
            raise ValueError("Đường dẫn đích nằm ngoài thư mục Template.")

        if dest_dir.exists() and not overwrite:
            raise ValueError(f"Template `{folder_name}` đã tồn tại.")

        dest_dir.mkdir(parents=True, exist_ok=True)
        written_files = 0
        for info, parts in parsed_entries:
            if prefix_parts and parts[: len(prefix_parts)] != prefix_parts:
                continue
            rel_parts = parts[len(prefix_parts):]
            if not rel_parts:
                continue
            out_path = (dest_dir / Path(*rel_parts)).resolve()
            if not out_path.is_relative_to(dest_dir):
                raise ValueError(f"Phát hiện Zip-Slip path traversal: {info.filename}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src_f, open(out_path, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f, length=1024 * 256)
            written_files += 1

    all_templates = list_video_templates()
    installed = next((t for t in all_templates if t.get("folder_name") == folder_name), None)
    label_code = (installed or {}).get("code") or cfg_obj.get("code") or cfg_obj.get("template_code") or "NEW"
    label_name = (installed or {}).get("name") or cfg_obj.get("name") or folder_name
    return {
        "ok": True,
        "folder_name": folder_name,
        "files_written": written_files,
        "installed": installed,
        "templates": all_templates,
        "message": f"Đã cài đặt thành công Template #{label_code} — {label_name} ({written_files} tệp)!",
    }
