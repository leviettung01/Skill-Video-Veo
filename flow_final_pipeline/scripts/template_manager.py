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
import os
import re
import sys
import glob
import json
import urllib.parse
import importlib.util

WS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMPLATE_ROOT_DIR = os.path.join(WS_DIR, "Template")
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
VOICES_CHARS_PATH = os.path.join(WS_DIR, "flow_final_pipeline", "voices_and_characters.json")

RESERVED_SUBFOLDERS = {
    "Character_Sheet_Templates",
    "Thumbnail_Templates",
    "Subtitle_Templates",
    "__pycache__",
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
        code = str(cfg.get("code") or "").strip()
        if code:
            used_codes.add(code)
        raw_entries.append((entry, tdir, cfg_path, cfg))

    next_code_int = 1
    for entry, tdir, cfg_path, cfg in raw_entries:
        code = str(cfg.get("code") or "").strip()
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

        templates.append({
            "code": code,
            "id": cfg.get("id") or entry.lower().replace(" ", "_"),
            "folder_name": entry,
            "name": cfg.get("name") or entry,
            "badge": cfg.get("badge") or "TEMPLATE VIDEO",
            "category": cfg.get("category") or "Thương Mại Điện Tử / TikTok Affiliate",
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


def get_template_detail(template_name_or_id: str) -> dict:
    tdir = resolve_template_dir(template_name_or_id)
    folder_name = os.path.basename(tdir)
    docs = {}
    doc_order = ("ROLE_SKILL.md", "SKILL.md", "KICH_BAN.md", "PROMPT_TEMPLATES.md", "RENDER.md", "WORKFLOW_GUIDE.md", "template_config.json", "generator.py")
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
        "demo_videos": [primary_demo_video] if primary_demo_video else [],
        "demo_images": demo_images,
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
