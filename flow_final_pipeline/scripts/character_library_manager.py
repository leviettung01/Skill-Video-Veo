# -*- coding: utf-8 -*-
"""
Quản lý Thư Viện Nhân Vật & Character Sheet Templates (`character_library_manager.py`):
  - Đọc/Ghi cấu hình nhân vật, giọng đọc, và số lượng video trên mỗi nhân vật/sản phẩm (`voices_and_characters.json`).
  - Tự động quét thư mục `Template/Character_Sheet_Templates/` để nạp các mẫu Character Sheet (hiện tại có 1 mẫu mặc định `mau_1_turnaround_6_goc.png`, người dùng chỉ cần bỏ thêm ảnh mẫu vào thư mục này hoặc thêm trên UI là tự nhận).
  - Hỗ trợ tạo ảnh Character Sheet mới hoặc tạo ảnh Nhân vật cầm sản phẩm bằng:
      1. Model `nano_banana` (Google Flow Nano Banana 2.1 - BELUGA 2K `1536x2752`)
      2. Model `chatgpt` (ChatGPT Image `gpt-image-1` / `dall-e-3` qua CLIProxy `:8317` hoặc OpenAI API)
"""
import os
import sys
import json
import time
import uuid
import base64
import shutil
import random
import urllib.request

WS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PIPELINE_DIR = os.path.join(WS_DIR, "flow_final_pipeline")
CHARS_DIR = os.path.join(PIPELINE_DIR, "characters")
VOICE_SAMPLES_DIR = os.path.join(PIPELINE_DIR, "voice_samples")
VOICES_CHARS_PATH = os.path.join(PIPELINE_DIR, "voices_and_characters.json")
SHEET_TEMPLATES_DIR = os.path.join(WS_DIR, "Template", "Character_Sheet_Templates")
SHEET_TEMPLATES_JSON = os.path.join(SHEET_TEMPLATES_DIR, "templates.json")
PROJECTS_DIR = os.path.join(WS_DIR, "projects")

COMMON_VN_DIALOGUE_PRESETS = [
    {
        "id": "preset_1_bao_gia_xuong",
        "label": "🏭 [Báo Giá Xưởng - Miền Bắc] Thang giá 3 bậc & miễn phí ship",
        "region": "north",
        "gender": "female",
        "text": "30k miễn phí ship tới tận nhà cho nguyên một thắt lưng nam tặng thêm đồng hồ này. Ở đâu bán cái giá đó thì em cũng đến",
    },
    {
        "id": "preset_2_chot_sale_fomo",
        "label": "🔥 [Xả Kho Flash Sale - Năng Lượng] Dồn dập kích thích chốt đơn",
        "region": "north",
        "gender": "female",
        "text": "Mọi người ơi xả kho trực tiếp tại xưởng chỉ ba mươi cành miễn phí ship tới tận nhà! Săn ngay kẻo hết nhé!",
    },
    {
        "id": "preset_3_do_an_vat_nam",
        "label": "🍲 [Review Đồ Ăn Vặt - Miền Nam] Ngọt ngào kích thích vị giác",
        "region": "south",
        "gender": "female",
        "text": "Mấy bà ơi mở nắp hũ kho quẹt nồi đất ra là thơm nức mũi luôn nha, chấm rau củ hay ăn cơm nóng là cuốn xỉu!",
    },
    {
        "id": "preset_4_livestream_sai_gon",
        "label": "☀️ [Livestream Săn Deal - Sài Gòn] Hoạt ngôn rộn ràng chốt đơn",
        "region": "south",
        "gender": "female",
        "text": "Trời ơi cả nhà coi cái chất lượng của nó nè, xịn xò từng chi tiết mà hôm nay trợ giá sâu dữ lắm, hốt lẹ liền tay nghen!",
    },
    {
        "id": "preset_5_do_nam_ky_thuat",
        "label": "👔 [Chuyên Gia Đồ Nam & Kỹ Thuật] Trầm ấm đĩnh đạc uy tín",
        "region": "north",
        "gender": "male",
        "text": "Anh em nhìn kỹ bề mặt da bò nguyên tấm và khoá hợp kim chống gỉ này nhé, độ bền cực cao, bảo hành mười hai tháng!",
    },
    {
        "id": "preset_6_dac_san_mien_trung",
        "label": "🌿 [Kể Chuyện Đặc Sản & Quà Biếu] Dịu dàng truyền cảm sâu lắng",
        "region": "central",
        "gender": "female",
        "text": "Mọi người ơi, từng mẻ đặc sản quê hương đều được chế biến thủ công đậm đà hương vị truyền thống, làm quà biếu rất quý!",
    },
    {
        "id": "preset_7_genz_foodie_bac",
        "label": "🧋 [GenZ Hà Nội - Đồ Ăn Vặt] Trẻ trung cuốn miệng",
        "region": "north",
        "gender": "female",
        "text": "Mọi người nha, nhìn phần sốt sánh kẹo mê chữ ê kéo dài luôn, ăn kèm cơm nóng thì đúng là hết nước chấm nhé!",
    },
]

BUILTIN_FLOW_VOICES = [
    {"slug": "erinome", "display_name": "Erinome (Nữ • Rõ ràng, Uy tín)", "gender": "female", "pitch_tier": "mid", "description": "Female, clear, mid pitch — Hợp tư vấn xưởng & kiểm định QC", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Erinome.wav"},
    {"slug": "zephyr", "display_name": "Zephyr (Nữ • Tươi sáng, Năng lượng cao)", "gender": "female", "pitch_tier": "mid-high", "description": "Female, bright, mid-high pitch — Hợp Flash Sale & Chốt đơn", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Zephyr.wav"},
    {"slug": "leda", "display_name": "Leda (Nữ • Trẻ trung, Ngọt ngào)", "gender": "female", "pitch_tier": "mid-high", "description": "Female, youthful, mid-high pitch — Hợp Review Đồ Ăn Vặt & Mỹ Phẩm", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Leda.wav"},
    {"slug": "laomedeia", "display_name": "Laomedeia (Nữ • Sôi nổi, Hào hứng)", "gender": "female", "pitch_tier": "mid-high", "description": "Female, upbeat, mid-high pitch — Hợp Livestream săn deal", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Laomedeia.wav"},
    {"slug": "autonoe", "display_name": "Autonoe (Nữ • Tươi tắn GenZ)", "gender": "female", "pitch_tier": "mid", "description": "Female, bright, mid pitch — Hợp Review Ẩm thực & Đời sống", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Autonoe.wav"},
    {"slug": "kore", "display_name": "Kore (Nữ • Chững chạc, Chuyên nghiệp)", "gender": "female", "pitch_tier": "mid", "description": "Female, firm, mid pitch — Hợp Giới thiệu sản phẩm cao cấp", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Kore.wav"},
    {"slug": "sulafat", "display_name": "Sulafat (Nữ • Ấm áp, Truyền cảm)", "gender": "female", "pitch_tier": "mid", "description": "Female, warm, mid pitch — Hợp Đặc sản truyền thống & Quà biếu", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Sulafat.wav"},
    {"slug": "aoede", "display_name": "Aoede (Nữ • Tự nhiên, Thoải mái)", "gender": "female", "pitch_tier": "mid", "description": "Female, breezy, mid pitch — Hợp Vlog & Lifestyle", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Aoede.wav"},
    {"slug": "achernar", "display_name": "Achernar (Nữ • Dịu dàng, Giọng cao)", "gender": "female", "pitch_tier": "high", "description": "Female, soft, high pitch — Hợp Mỹ phẩm & Chăm sóc da", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Achernar.wav"},
    {"slug": "despina", "display_name": "Despina (Nữ • Mượt mà, Dễ nghe)", "gender": "female", "pitch_tier": "mid", "description": "Female, smooth, mid pitch — Hợp Kể chuyện & Decor", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Despina.wav"},
    {"slug": "callirrhoe", "display_name": "Callirrhoe (Nữ • Thân thiện, Dễ tính)", "gender": "female", "pitch_tier": "mid", "description": "Female, easy-going, mid pitch — Hợp Chia sẻ mẹo vặt gia đình", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Callirrhoe.wav"},
    {"slug": "gacrux", "display_name": "Gacrux (Nữ • Đằm thắm, Trưởng thành)", "gender": "female", "pitch_tier": "mid", "description": "Female, mature, mid pitch — Hợp Sức khoẻ, Đông y & Gia đình", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Gacrux.wav"},
    {"slug": "pulcherrima", "display_name": "Pulcherrima (Nữ • Sắc nét, Hiện đại)", "gender": "female", "pitch_tier": "mid-high", "description": "Female, forward, mid-high pitch — Hợp Thời trang & Lookbook", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Pulcherrima.wav"},
    {"slug": "vindemiatrix", "display_name": "Vindemiatrix (Nữ • Hiền hoà, Nhẹ nhàng)", "gender": "female", "pitch_tier": "mid-low", "description": "Female, gentle, mid-low pitch — Hợp Sách, Trà & Phong thuỷ", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Vindemiatrix.wav"},
    {"slug": "orus", "display_name": "Orus (Nam • Đĩnh đạc, Chuyên gia)", "gender": "male", "pitch_tier": "mid-low", "description": "Male, firm, mid-low pitch — Hợp Đồ Nam, Thắt lưng, Đồng hồ, Kỹ thuật", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Orus.wav"},
    {"slug": "puck", "display_name": "Puck (Nam • Năng lượng, Vui vẻ)", "gender": "male", "pitch_tier": "mid", "description": "Male, upbeat, mid pitch — Hợp Review Đồ Ăn & Công nghệ", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Puck.wav"},
    {"slug": "fenrir", "display_name": "Fenrir (Nam • Trẻ trung, Hào hứng)", "gender": "male", "pitch_tier": "mid-high", "description": "Male, excitable, younger pitch — Hợp Chốt sale & Đồ chơi công nghệ", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Fenrir.wav"},
    {"slug": "achird", "display_name": "Achird (Nam • Thân thiện, Gần gũi)", "gender": "male", "pitch_tier": "mid", "description": "Male, friendly, mid pitch — Hợp Tư vấn gia dụng & Đời sống", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Achird.wav"},
    {"slug": "charon", "display_name": "Charon (Nam • Trầm ấm, Thuyết minh)", "gender": "male", "pitch_tier": "low", "description": "Male, informative, lower pitch — Hợp Review chi tiết & Phân tích", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Charon.wav"},
    {"slug": "alnilam", "display_name": "Alnilam (Nam • Quyết đoán, Mạnh mẽ)", "gender": "male", "pitch_tier": "mid-low", "description": "Male, firm, mid-low pitch — Hợp Dụng cụ cơ khí & Thể thao", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Alnilam.wav"},
    {"slug": "algenib", "display_name": "Algenib (Nam • Trầm khàn, Cá tính)", "gender": "male", "pitch_tier": "low", "description": "Male, gravelly, low pitch — Hợp Đồ da, Phượt & Xe cộ", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Algenib.wav"},
    {"slug": "algieba", "display_name": "Algieba (Nam • Điềm đạm, Dễ mến)", "gender": "male", "pitch_tier": "mid-low", "description": "Male, easy-going, mid-low pitch — Hợp Vlog Đời sống & Cafe", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Algieba.wav"},
    {"slug": "enceladus", "display_name": "Enceladus (Nam • Trầm sâu, Điện ảnh)", "gender": "male", "pitch_tier": "low", "description": "Male, breathy, lower pitch — Hợp Kể chuyện & Phim hoạt hình 3D", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Enceladus.wav"},
    {"slug": "iapetus", "display_name": "Iapetus (Nam • Rõ ràng, Chuẩn mực)", "gender": "male", "pitch_tier": "mid", "description": "Male, clear, mid pitch — Hợp Giới thiệu sản phẩm & Hướng dẫn", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Iapetus.wav"},
    {"slug": "rasalgethi", "display_name": "Rasalgethi (Nam • Chuyên gia Tư vấn)", "gender": "male", "pitch_tier": "mid", "description": "Male, informative, mid pitch — Hợp Đánh giá công nghệ & Điện máy", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Rasalgethi.wav"},
    {"slug": "sadachbia", "display_name": "Sadachbia (Nam • Sôi động, Hoạt ngôn)", "gender": "male", "pitch_tier": "mid-high", "description": "Male, lively, mid-high pitch — Hợp Livestream Xả kho", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Sadachbia.wav"},
    {"slug": "sadaltager", "display_name": "Sadaltager (Nam • Uyên bác, Điềm tĩnh)", "gender": "male", "pitch_tier": "mid-low", "description": "Male, knowledgeable, mid-low pitch — Hợp Sức khoẻ & Thực phẩm chức năng", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Sadaltager.wav"},
    {"slug": "schedar", "display_name": "Schedar (Nam • Vững chãi, Đáng tin)", "gender": "male", "pitch_tier": "mid", "description": "Male, even, mid pitch — Hợp Nội thất & Xây dựng", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Schedar.wav"},
    {"slug": "umbriel", "display_name": "Umbriel (Nam • Thư thái, Tự nhiên)", "gender": "male", "pitch_tier": "mid-low", "description": "Male, easy-going, mid-low pitch — Hợp Du lịch & Ẩm thực", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Umbriel.wav"},
    {"slug": "zubenelgenubi", "display_name": "Zubenelgenubi (Nam • Đời thường, Thân근)", "gender": "male", "pitch_tier": "low", "description": "Male, casual, low pitch — Hợp Review chân thật", "sample_url": "https://www.gstatic.com/aitestkitchen/voices/samples/Zubenelgenubi.wav"},
]



def ensure_dirs_and_default_sheet():
    os.makedirs(CHARS_DIR, exist_ok=True)
    os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)
    os.makedirs(SHEET_TEMPLATES_DIR, exist_ok=True)
    default_sample = os.path.join(SHEET_TEMPLATES_DIR, "mau_1_turnaround_6_goc.png")
    nv2_src = os.path.join(CHARS_DIR, "nv2_ref.png")
    if not os.path.exists(default_sample) and os.path.exists(nv2_src):
        try:
            shutil.copy2(nv2_src, default_sample)
        except Exception:
            pass


def load_sheet_templates() -> list:
    ensure_dirs_and_default_sheet()
    data = {"templates": []}
    if os.path.exists(SHEET_TEMPLATES_JSON):
        try:
            with open(SHEET_TEMPLATES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    templates = data.get("templates", [])
    known_files = set()
    for t in templates:
        if t.get("sample_image"):
            known_files.add(t.get("sample_image"))
        if t.get("reference_image"):
            known_files.add(t.get("reference_image"))

    # Tự động phát hiện các file ảnh mới được người dùng thêm vào Template/Character_Sheet_Templates/
    dirty = False
    for fn in sorted(os.listdir(SHEET_TEMPLATES_DIR)):
        fl = fn.lower()
        if "_ref." in fl:
            continue
        if fl.endswith((".png", ".jpg", ".jpeg", ".webp")) and fn not in known_files:
            tid = os.path.splitext(fn)[0].lower().replace(" ", "_")
            templates.append({
                "id": tid,
                "name": f"Mẫu Character Sheet: {os.path.splitext(fn)[0]}",
                "badge": "MẪU TUỲ CHỌN",
                "sample_image": fn,
                "aspect_ratio": "3:2",
                "description": f"Mẫu Character Sheet tự động nạp từ file {fn}",
                "character_sheet_prompt": (
                    "Photorealistic 6-panel character reference turnaround sheet arranged in a clean 2x3 grid with thin white borders on a neutral light-grey studio background. "
                    "Top row: full-body standing views (Front, Back, Side) of ({character_description}). "
                    "Bottom row: close-up portrait views (Front, 3/4 angle, Side profile) of the exact same person. "
                    "Consistent studio lighting, identical face across all panels, 8k photorealistic."
                ),
                "product_with_character_prompt": (
                    "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
                    "the exact same person from the character reference ({character_description}), {outfit_en}, {setting_en}, "
                    "holding and presenting the exact product from the product reference image at waist level facing the camera "
                    "(true-to-life natural hand-held scale, NOT oversized). Keep the product 100% identical and keep the face identical."
                ),
            })
            known_files.add(fn)
            dirty = True

    if dirty:
        try:
            with open(SHEET_TEMPLATES_JSON, "w", encoding="utf-8") as f:
                json.dump({"templates": templates}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    for t in templates:
        s_img = t.get("sample_image", "")
        s_abs = os.path.join(SHEET_TEMPLATES_DIR, s_img) if s_img else ""
        t["sample_image_path"] = s_abs if (s_abs and os.path.exists(s_abs)) else ""
        r_img = t.get("reference_image", "")
        r_abs = os.path.join(SHEET_TEMPLATES_DIR, r_img) if r_img else ""
        t["reference_image_path"] = r_abs if (r_abs and os.path.exists(r_abs)) else ""
    return templates


def get_character_library_state() -> dict:
    ensure_dirs_and_default_sheet()
    cfg = {
        "default_videos_per_character": 3,
        "default_image_model": "nano_banana",
        "default_sheet_template_id": "sheet_6panel_studio",
        "voices": {},
        "characters": {},
    }
    if os.path.exists(VOICES_CHARS_PATH):
        try:
            with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                cfg.update(loaded)
        except Exception:
            pass

    voices_dict = cfg.get("voices", {})
    voices_list = []
    for vk, vval in voices_dict.items():
        v_item = dict(vval) if isinstance(vval, dict) else {"name": str(vval)}
        v_item["key"] = vk
        v_item.setdefault("name", f"Voice {vk.upper()}")
        v_item.setdefault("voice_id", "27f51973-e290-4a38-bd7a-9d6fbe81b2f6")
        v_item.setdefault("gender", "female")
        v_item.setdefault("region", "north")
        v_item.setdefault("region_label", "Miền Bắc (Hà Nội)" if v_item["region"] == "north" else ("Miền Nam (Sài Gòn)" if v_item["region"] == "south" else "Miền Trung"))
        v_item.setdefault("tone_style", "trustworthy_expert")
        v_item.setdefault("tone_label", "🛡️ Uy tín • Tư vấn")
        v_item.setdefault("speed_wpm", "42-46 từ / 10s")
        v_item.setdefault("voice_prompt_en", "clear, natural Vietnamese voice, steady confident delivery")
        v_item.setdefault("dialect_markers_vn", "nhé, đấy ạ, mọi người ơi")
        v_item.setdefault("recommended_templates", ["001", "002"])
        v_item.setdefault("recommended_categories", ["Đa ngành hàng"])
        v_item.setdefault("sample_url", "")

        # Resolve local Google Flow Vietnamese audio sample (`voice_samples/<vk>_flow.mp3`)
        rel_vn = v_item.get("sample_vn_file") or f"voice_samples/{vk}_flow.mp3"
        abs_vn = os.path.join(PIPELINE_DIR, rel_vn.replace("/", os.sep))
        if not os.path.isfile(abs_vn):
            cand_vn = os.path.join(VOICE_SAMPLES_DIR, f"{vk}_flow.mp3")
            abs_vn = cand_vn if os.path.isfile(cand_vn) else ""
        v_item["sample_vn_abs"] = abs_vn
        v_item["has_flow_vn_audio"] = bool(abs_vn)
        v_item["flow_synced"] = bool(v_item.get("flow_synced") or abs_vn)
        if not v_item.get("sample_dialogue_vn"):
            if v_item["region"] == "south":
                v_item["sample_dialogue_vn"] = COMMON_VN_DIALOGUE_PRESETS[2]["text"]
            elif v_item["region"] == "central":
                v_item["sample_dialogue_vn"] = COMMON_VN_DIALOGUE_PRESETS[5]["text"]
            elif v_item["gender"] == "male":
                v_item["sample_dialogue_vn"] = COMMON_VN_DIALOGUE_PRESETS[4]["text"]
            elif v_item["tone_style"] == "energetic_sale":
                v_item["sample_dialogue_vn"] = COMMON_VN_DIALOGUE_PRESETS[1]["text"]
            else:
                v_item["sample_dialogue_vn"] = COMMON_VN_DIALOGUE_PRESETS[0]["text"]
        voices_list.append(v_item)

    chars_list = []
    for ck, cval in cfg.get("characters", {}).items():
        rel_img = cval.get("ref_image_file", "")
        abs_img = os.path.join(PIPELINE_DIR, rel_img.replace("/", os.sep)) if rel_img else ""
        if not abs_img or not os.path.exists(abs_img):
            cand = os.path.join(CHARS_DIR, os.path.basename(rel_img)) if rel_img else ""
            abs_img = cand if (cand and os.path.exists(cand)) else ""

        item = dict(cval)
        item["key"] = ck
        item["ref_image_abs"] = abs_img
        item["videos_per_character"] = int(cval.get("videos_per_character", cfg.get("default_videos_per_character", 3)))
        item["enabled"] = bool(cval.get("enabled", True))
        item["preferred_image_model"] = cval.get("preferred_image_model", cfg.get("default_image_model", "nano_banana"))
        item["sheet_template_id"] = cval.get("sheet_template_id", cfg.get("default_sheet_template_id", "sheet_6panel_studio"))
        item["lock_voice_to_character"] = bool(cval.get("lock_voice_to_character", True))
        def_vk = cval.get("default_voice") or ck
        item["default_voice"] = def_vk
        linked_v = voices_dict.get(def_vk, {})
        if isinstance(linked_v, dict) and linked_v:
            item.setdefault("voice_id", linked_v.get("voice_id", ""))
            item.setdefault("voice_name", linked_v.get("name", ""))
            item["voice_region"] = cval.get("voice_region") or linked_v.get("region", "north")
            item["voice_gender"] = cval.get("voice_gender") or linked_v.get("gender", "female")
            item["voice_tone"] = cval.get("voice_tone") or linked_v.get("tone_style", "trustworthy_expert")
            item["voice_prompt_en"] = cval.get("voice_prompt_en") or linked_v.get("voice_prompt_en", "")
        chars_list.append(item)

    return {
        "ok": True,
        "default_videos_per_character": int(cfg.get("default_videos_per_character", 3)),
        "default_image_model": cfg.get("default_image_model", "nano_banana"),
        "default_sheet_template_id": cfg.get("default_sheet_template_id", "sheet_6panel_studio"),
        "characters": chars_list,
        "voices": voices_dict,
        "voices_list": voices_list,
        "builtin_flow_voices": BUILTIN_FLOW_VOICES,
        "common_vn_dialogues": COMMON_VN_DIALOGUE_PRESETS,
        "sheet_templates": load_sheet_templates(),
        "characters_dir": CHARS_DIR,
        "voice_samples_dir": VOICE_SAMPLES_DIR,
        "sheet_templates_dir": SHEET_TEMPLATES_DIR,
    }


def build_voice_prompt_en(gender: str, region: str, tone_style: str, speed_wpm: str = "") -> str:
    g_en = "male" if gender == "male" else "female"
    if region == "south":
        r_en = "Southern Vietnamese (Saigon accent)"
    elif region == "central":
        r_en = "Central Vietnamese (Hue/Da Nang accent)"
    else:
        r_en = "Northern Vietnamese (Hanoi accent)"

    if tone_style == "energetic_sale":
        t_en = "high-energy, enthusiastic livestream flash-sale host tone, persuasive, bright and fast-paced delivery (4.6 words/sec)"
    elif tone_style == "sweet_foodie":
        t_en = "cheerful, appetizing food-reviewer and lifestyle vlogger tone, warm mouth-watering inflection, friendly cadence (4.1 words/sec)"
    elif tone_style == "chill_story":
        t_en = "warm, gentle, sincere storytelling tone for traditional specialties and gifts, smooth and calm articulation (3.8 words/sec)"
    else:
        t_en = "clear, trustworthy professional factory & QC consultant tone, steady confident articulation (4.4 words/sec)"

    return f"{t_en}, young {r_en} {g_en} voice"


def save_character_library_settings(payload: dict) -> dict:
    """
    Cập nhật cấu hình chung (`default_videos_per_character`, `default_image_model`)
    hoặc thêm/sửa thông tin 1 nhân vật (kèm gắn cố định giọng đọc) trong `voices_and_characters.json`.
    """
    ensure_dirs_and_default_sheet()
    cfg = {
        "default_videos_per_character": 3,
        "default_image_model": "nano_banana",
        "default_sheet_template_id": "sheet_6panel_studio",
        "voices": {},
        "characters": {},
    }
    if os.path.exists(VOICES_CHARS_PATH):
        try:
            with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    if "default_videos_per_character" in payload:
        vpc = max(1, min(5, int(payload["default_videos_per_character"])))
        cfg["default_videos_per_character"] = vpc
        if payload.get("apply_to_all_characters"):
            for ck, cv in cfg.get("characters", {}).items():
                cv["videos_per_character"] = vpc

    if "default_image_model" in payload:
        cfg["default_image_model"] = str(payload["default_image_model"])

    if "default_sheet_template_id" in payload:
        cfg["default_sheet_template_id"] = str(payload["default_sheet_template_id"])

    char_obj = payload.get("character")
    if isinstance(char_obj, dict):
        ck = (char_obj.get("key") or "").strip().lower()
        if not ck:
            existing_nums = [
                int(m.group(1))
                for k in cfg.get("characters", {}).keys()
                for m in [__import__("re").match(r"^nv(\d+)$", k)]
                if m
            ]
            next_num = (max(existing_nums) + 1) if existing_nums else (len(cfg.get("characters", {})) + 1)
            ck = f"nv{next_num}"

        cur = cfg.setdefault("characters", {}).get(ck, {})
        cur["key"] = ck
        if "name" in char_obj:
            cur["name"] = char_obj["name"]
        if "enabled" in char_obj:
            cur["enabled"] = bool(char_obj["enabled"])
        if "videos_per_character" in char_obj:
            cur["videos_per_character"] = max(1, min(5, int(char_obj["videos_per_character"])))
        if "character_id" in char_obj:
            cur["character_id"] = str(char_obj["character_id"]).strip()
        if "project_id" in char_obj:
            cur["project_id"] = str(char_obj["project_id"]).strip()
        if "lock_voice_to_character" in char_obj:
            cur["lock_voice_to_character"] = bool(char_obj["lock_voice_to_character"])
        if "default_voice" in char_obj and char_obj["default_voice"]:
            vkey = str(char_obj["default_voice"]).strip()
            cur["default_voice"] = vkey
            v_entry = cfg.get("voices", {}).get(vkey)
            if isinstance(v_entry, dict):
                cur["voice_id"] = v_entry.get("voice_id") or cur.get("voice_id", "")
                cur["voice_name"] = v_entry.get("name") or cur.get("voice_name", "")
                cur["voice_region"] = v_entry.get("region", "north")
                cur["voice_gender"] = v_entry.get("gender", "female")
                cur["voice_tone"] = v_entry.get("tone_style", "trustworthy_expert")
                cur["voice_prompt_en"] = v_entry.get("voice_prompt_en", "")
        if "voice_id" in char_obj and char_obj["voice_id"]:
            cur["voice_id"] = str(char_obj["voice_id"]).strip()
        if "voice_name" in char_obj and char_obj["voice_name"]:
            cur["voice_name"] = str(char_obj["voice_name"]).strip()
        if "voice_region" in char_obj and char_obj["voice_region"]:
            cur["voice_region"] = str(char_obj["voice_region"]).strip()
        if "voice_gender" in char_obj and char_obj["voice_gender"]:
            cur["voice_gender"] = str(char_obj["voice_gender"]).strip()
        if "voice_tone" in char_obj and char_obj["voice_tone"]:
            cur["voice_tone"] = str(char_obj["voice_tone"]).strip()
        if "voice_prompt_en" in char_obj and char_obj["voice_prompt_en"]:
            cur["voice_prompt_en"] = str(char_obj["voice_prompt_en"]).strip()
        if "appearance_en" in char_obj:
            cur["appearance_en"] = str(char_obj["appearance_en"]).strip()
        if "preferred_image_model" in char_obj:
            cur["preferred_image_model"] = str(char_obj["preferred_image_model"]).strip()
        if "sheet_template_id" in char_obj:
            cur["sheet_template_id"] = str(char_obj["sheet_template_id"]).strip()
        if "ref_image_file" in char_obj and char_obj["ref_image_file"]:
            cur["ref_image_file"] = str(char_obj["ref_image_file"]).strip()

        b64_img = char_obj.get("uploaded_image_base64")
        if b64_img:
            if "," in b64_img:
                b64_img = b64_img.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_img)
            out_fn = f"{ck}_ref.jpg"
            out_abs = os.path.join(CHARS_DIR, out_fn)
            with open(out_abs, "wb") as f:
                f.write(raw_bytes)
            cur["ref_image_file"] = f"characters/{out_fn}"

        cfg["characters"][ck] = cur

    with open(VOICES_CHARS_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    return get_character_library_state()


def save_voice_profile(payload: dict) -> dict:
    """Thêm mới hoặc cập nhật 1 Giọng Đọc (Custom Bắc/Nam, Nam/Nữ, Năng lượng, Voice ID, Prompt) vào `voices_and_characters.json`."""
    ensure_dirs_and_default_sheet()
    cfg = {"voices": {}, "characters": {}}
    if os.path.exists(VOICES_CHARS_PATH):
        try:
            with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    vkey = (payload.get("key") or "").strip().lower()
    vkey = __import__("re").sub(r"[^a-z0-9_]", "_", vkey).strip("_")
    if not vkey:
        vkey = f"voice_{len(cfg.get('voices', {})) + 1}_{int(time.time()) % 1000}"

    gender = (payload.get("gender") or "female").strip().lower()
    region = (payload.get("region") or "north").strip().lower()
    tone_style = (payload.get("tone_style") or "trustworthy_expert").strip()
    speed_wpm = (payload.get("speed_wpm") or "42-46 từ / 10s").strip()

    region_labels = {
        "north": "Miền Bắc (Hà Nội)",
        "south": "Miền Nam (Sài Gòn)",
        "central": "Miền Trung (Huế / Đà Nẵng)",
    }
    tone_labels = {
        "energetic_sale": "🔥 Năng lượng cao • Chốt Sale",
        "trustworthy_expert": "🛡️ Uy tín • Tư vấn Xưởng & QC",
        "sweet_foodie": "🍲 Ngọt ngào • Review Ẩm thực / Mỹ phẩm",
        "chill_story": "🌿 Dịu dàng • Kể chuyện & Đặc sản",
    }

    voice_prompt_en = (payload.get("voice_prompt_en") or "").strip()
    if not voice_prompt_en:
        voice_prompt_en = build_voice_prompt_en(gender, region, tone_style, speed_wpm)

    default_dialects = {
        "north": "các bác ơi, mọi người nhé, đấy ạ, chuẩn chỉnh tận xưởng, rinh ngay",
        "south": "mấy bà ơi, cả nhà nha, nghen, thiệt sự cuốn xỉu, hốt lẹ liền tay",
        "central": "mọi người ơi, hương vị đậm đà khó quên, thương mời cả nhà thưởng thức",
    }
    dialect_markers = (payload.get("dialect_markers_vn") or "").strip() or default_dialects.get(region, default_dialects["north"])

    flow_slug = (payload.get("flow_slug") or "").strip().lower()
    sample_url = (payload.get("sample_url") or "").strip()
    if not sample_url and flow_slug:
        matched_b = next((b for b in BUILTIN_FLOW_VOICES if b["slug"] == flow_slug), None)
        if matched_b:
            sample_url = matched_b.get("sample_url", "")

    rec_cats = payload.get("recommended_categories")
    if isinstance(rec_cats, str):
        rec_cats = [x.strip() for x in rec_cats.split(",") if x.strip()]
    elif not isinstance(rec_cats, list) or not rec_cats:
        rec_cats = ["Đa ngành hàng", "TikTok Affiliate"]

    rec_tpls = payload.get("recommended_templates")
    if isinstance(rec_tpls, str):
        rec_tpls = [x.strip() for x in rec_tpls.split(",") if x.strip()]
    elif not isinstance(rec_tpls, list) or not rec_tpls:
        rec_tpls = ["001", "002"]

    existing_v = cfg.get("voices", {}).get(vkey, {})
    sample_dialogue_vn = (payload.get("sample_dialogue_vn") or existing_v.get("sample_dialogue_vn") or "").strip()
    if not sample_dialogue_vn:
        if region == "south":
            sample_dialogue_vn = COMMON_VN_DIALOGUE_PRESETS[2]["text"]
        elif region == "central":
            sample_dialogue_vn = COMMON_VN_DIALOGUE_PRESETS[5]["text"]
        elif gender == "male":
            sample_dialogue_vn = COMMON_VN_DIALOGUE_PRESETS[4]["text"]
        else:
            sample_dialogue_vn = COMMON_VN_DIALOGUE_PRESETS[0]["text"]

    voice_entry = {
        "key": vkey,
        "name": (payload.get("name") or f"Giọng {region_labels.get(region, 'Việt Nam')} ({vkey})").strip(),
        "voice_id": (payload.get("voice_id") or existing_v.get("voice_id") or flow_slug or "27f51973-e290-4a38-bd7a-9d6fbe81b2f6").strip(),
        "flow_slug": flow_slug,
        "gender": gender,
        "region": region,
        "region_label": region_labels.get(region, "Miền Bắc (Hà Nội)"),
        "tone_style": tone_style,
        "tone_label": tone_labels.get(tone_style, "🛡️ Uy tín • Tư vấn"),
        "speed_wpm": speed_wpm,
        "sample_url": sample_url,
        "sample_vn_file": payload.get("sample_vn_file") or existing_v.get("sample_vn_file") or f"voice_samples/{vkey}_flow.mp3",
        "sample_dialogue_vn": sample_dialogue_vn,
        "flow_synced": bool(payload.get("flow_synced", existing_v.get("flow_synced", False))),
        "voice_prompt_en": voice_prompt_en,
        "dialect_markers_vn": dialect_markers,
        "recommended_templates": rec_tpls,
        "recommended_categories": rec_cats,
        "description": (payload.get("description") or f"Giọng {'Nam' if gender == 'male' else 'Nữ'} {region_labels.get(region, '')} — {tone_labels.get(tone_style, '')}").strip(),
    }

    cfg.setdefault("voices", {})[vkey] = voice_entry

    # Đồng bộ tự động sang các nhân vật đang khóa cố định vào vkey này
    for ck, cval in cfg.get("characters", {}).items():
        if cval.get("default_voice") == vkey:
            cval["voice_id"] = voice_entry["voice_id"]
            cval["voice_name"] = voice_entry["name"]
            cval["voice_region"] = voice_entry["region"]
            cval["voice_gender"] = voice_entry["gender"]
            cval["voice_tone"] = voice_entry["tone_style"]
            cval["voice_prompt_en"] = voice_entry["voice_prompt_en"]

    with open(VOICES_CHARS_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    return get_character_library_state()


def delete_voice_profile(voice_key: str) -> dict:
    vk = (voice_key or "").strip()
    if not vk or not os.path.exists(VOICES_CHARS_PATH):
        return {"ok": False, "error": "Không tìm thấy mã giọng đọc"}
    with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if vk in ("nv1", "nv2"):
        return {"ok": False, "error": "Không thể xoá 2 giọng gốc mặc định (nv1, nv2). Bạn có thể bấm Sửa để thay đổi thông tin."}
    cfg.get("voices", {}).pop(vk, None)
    with open(VOICES_CHARS_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return get_character_library_state()


def scan_and_sync_flow_voices(payload: dict = None) -> dict:
    """
    Quét toàn bộ các `voice_id` và `character_id` từ:
      1. Các dự án đã tạo trong `projects/*/prompts.json`
      2. File cấu hình `voices_and_characters.json`
      3. Danh sách 30 Giọng Built-in chất lượng cao của Google Flow (`BUILTIN_FLOW_VOICES`)
    và trả về báo cáo chi tiết để người dùng sử dụng ngay.
    """
    payload = payload or {}
    state = get_character_library_state()
    cfg_voices = state.get("voices", {})
    discovered_uuids = {}

    for vk, v in cfg_voices.items():
        vid = (v.get("voice_id") or "").strip()
        if vid:
            discovered_uuids[vid] = {
                "voice_id": vid,
                "name": v.get("name", vk),
                "source": "voices_and_characters.json",
                "key": vk,
            }

    if os.path.isdir(PROJECTS_DIR):
        for pid in os.listdir(PROJECTS_DIR):
            pjson = os.path.join(PROJECTS_DIR, pid, "prompts.json")
            if os.path.isfile(pjson):
                try:
                    pdata = json.loads(open(pjson, "r", encoding="utf-8").read())
                    for v_k, v_obj in (pdata.get("videos") or {}).items():
                        vid = (v_obj.get("voice_id") or "").strip()
                        vname = (v_obj.get("voice_name") or "").strip()
                        if vid and vid not in discovered_uuids:
                            discovered_uuids[vid] = {
                                "voice_id": vid,
                                "name": vname or f"Flow Voice ({vid[:8]})",
                                "source": f"projects/{pid}/prompts.json",
                                "key": f"flow_{vid[:8]}",
                            }
                except Exception:
                    pass

    state["discovered_flow_voices"] = list(discovered_uuids.values())
    state["scan_message"] = (
        f"Đã đồng bộ {len(state.get('voices_list', []))} giọng đọc Việt Nam đã Custom trên Google Flow, "
        f"{len(discovered_uuids)} mã Voice UUID thực tế và "
        f"{len(BUILTIN_FLOW_VOICES)} giọng gốc Google Flow."
    )
    return state


def preview_vietnamese_voice(payload: dict) -> dict:
    """
    Nghe thử Giọng Đọc bằng Tiếng Việt với các lời thoại Affiliate hay dùng:
      1. Nếu là giọng đã Custom trên Google Flow và chưa đổi lời thoại khác mặc định -> phát ngay file `.mp3` thực tế từ Google Flow (`voice_samples/<key>_flow.mp3`).
      2. Nếu người dùng chọn lời thoại Tiếng Việt bất kỳ trong 7 lời thoại mẫu hoặc tự gõ lời thoại mới:
         - Kiểm tra xem đã có lời thoại trùng với 1 trong 8 file Google Flow `.mp3` có sẵn chưa (ưu tiên chất lượng Gemini TTS của Google Flow).
         - Hoặc tổng hợp nhanh file `.mp3` Tiếng Việt qua `gTTS` + `ffmpeg` tinh chỉnh tốc độ/cao độ theo Nam/Nữ/Vùng miền để nghe thử tức thì.
    """
    ensure_dirs_and_default_sheet()
    state = get_character_library_state()
    voices_list = state.get("voices_list", [])

    vkey = (payload.get("voice_key") or "").strip()
    flow_slug = (payload.get("flow_slug") or "").strip().lower()
    sample_text_vn = (payload.get("sample_text_vn") or payload.get("dialogue_vn") or "").strip()
    prefer_flow_file = bool(payload.get("prefer_flow_file", False)) and not bool(payload.get("force_regenerate", False))

    v_obj = next((x for x in voices_list if x["key"] == vkey), None)
    gender = (payload.get("gender") or (v_obj or {}).get("gender") or "female").lower()
    region = (payload.get("region") or (v_obj or {}).get("region") or "north").lower()
    tone_style = (payload.get("tone_style") or (v_obj or {}).get("tone_style") or "trustworthy_expert").lower()
    voice_label = (v_obj or {}).get("name") or flow_slug.upper() or vkey or "Giọng Tiếng Việt"

    if not sample_text_vn:
        sample_text_vn = (v_obj or {}).get("sample_dialogue_vn") or COMMON_VN_DIALOGUE_PRESETS[0]["text"]

    import urllib.parse as _urlparse

    # 1. Nếu bấm nghe thử trực tiếp giọng Custom đã có sẵn file từ Google Flow (hoặc câu thoại trùng khớp)
    if v_obj and v_obj.get("sample_vn_abs") and os.path.isfile(v_obj["sample_vn_abs"]):
        saved_dlg = (v_obj.get("sample_dialogue_vn") or "").strip()
        if prefer_flow_file or not sample_text_vn or sample_text_vn[:60] == saved_dlg[:60]:
            abs_p = v_obj["sample_vn_abs"]
            return {
                "ok": True,
                "source": "Google Flow (gemini-v4s-tts-flow)",
                "voice_key": vkey,
                "voice_label": voice_label,
                "sample_text_vn": saved_dlg or sample_text_vn,
                "dialogue_vn": saved_dlg or sample_text_vn,
                "audio_path": abs_p,
                "audio_url": f"/api/media?path={_urlparse.quote(abs_p)}",
            }

    # 2. Nếu câu thoại người dùng chọn trùng với 1 trong 8 file Google Flow `.mp3` đã tải sẵn và cùng giới tính -> ưu tiên dùng bản Google Flow chuẩn
    for cand_v in voices_list:
        c_abs = cand_v.get("sample_vn_abs")
        c_dlg = (cand_v.get("sample_dialogue_vn") or "").strip()
        if c_abs and os.path.isfile(c_abs) and cand_v.get("gender") == gender and sample_text_vn[:55] == c_dlg[:55]:
            return {
                "ok": True,
                "source": f"Google Flow ({cand_v.get('name')})",
                "voice_key": vkey or cand_v["key"],
                "voice_label": voice_label,
                "sample_text_vn": sample_text_vn,
                "dialogue_vn": sample_text_vn,
                "audio_path": c_abs,
                "audio_url": f"/api/media?path={_urlparse.quote(c_abs)}",
            }

    # 3. Sinh nhanh file preview Tiếng Việt cho câu thoại tuỳ ý bằng gTTS + ffmpeg chỉnh tốc độ/pitch theo Nam/Nữ/Năng lượng
    import hashlib
    import subprocess
    h = hashlib.md5(f"{gender}|{region}|{tone_style}|{sample_text_vn}".encode("utf-8")).hexdigest()[:12]
    out_mp3 = os.path.join(VOICE_SAMPLES_DIR, f"preview_{h}.mp3")
    if not os.path.isfile(out_mp3):
        raw_mp3 = os.path.join(VOICE_SAMPLES_DIR, f"_raw_{h}.mp3")
        try:
            from gtts import gTTS
            tts = gTTS(text=sample_text_vn, lang="vi", slow=False)
            tts.save(raw_mp3)
            # Tinh chỉnh pitch & tốc độ bằng ffmpeg để phân biệt Nam/Nữ và Năng lượng
            if gender == "male":
                af_filter = "asetrate=24000*0.84,aresample=24000,atempo=1.28"
            elif tone_style == "energetic_sale":
                af_filter = "asetrate=24000*1.05,aresample=24000,atempo=1.22"
            elif tone_style == "chill_story":
                af_filter = "asetrate=24000*0.98,aresample=24000,atempo=1.10"
            else:
                af_filter = "asetrate=24000*1.02,aresample=24000,atempo=1.16"
            subprocess.run(
                ["ffmpeg", "-y", "-i", raw_mp3, "-af", af_filter, out_mp3],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            if not os.path.isfile(out_mp3) and os.path.isfile(raw_mp3):
                shutil.copy2(raw_mp3, out_mp3)
        except Exception as e:
            # Fallback về file âm thanh Tiếng Việt Google Flow có sẵn cùng giới tính/vùng miền
            fallback_v = v_obj or next((x for x in voices_list if x.get("gender") == gender and x.get("sample_vn_abs")), None)
            if fallback_v and fallback_v.get("sample_vn_abs") and os.path.isfile(fallback_v["sample_vn_abs"]):
                fb_abs = fallback_v["sample_vn_abs"]
                return {
                    "ok": True,
                    "source": f"Google Flow ({fallback_v.get('name')})",
                    "voice_key": vkey,
                    "voice_label": voice_label,
                    "sample_text_vn": fallback_v.get("sample_dialogue_vn") or sample_text_vn,
                    "dialogue_vn": fallback_v.get("sample_dialogue_vn") or sample_text_vn,
                    "audio_path": fb_abs,
                    "audio_url": f"/api/media?path={_urlparse.quote(fb_abs)}",
                }
            return {"ok": False, "error": f"Không tạo được bản nghe thử Tiếng Việt: {e}"}
        finally:
            if os.path.isfile(raw_mp3):
                try:
                    os.remove(raw_mp3)
                except Exception:
                    pass

    return {
        "ok": True,
        "source": "Tự động tổng hợp Tiếng Việt (Instant Preview)",
        "voice_key": vkey,
        "voice_label": voice_label,
        "sample_text_vn": sample_text_vn,
        "dialogue_vn": sample_text_vn,
        "audio_path": out_mp3,
        "audio_url": f"/api/media?path={_urlparse.quote(out_mp3)}",
    }


def create_custom_voice_on_flow(payload: dict) -> dict:
    """
    Tự động mở Google Flow (`flow.google.com/project/<project_id>`), điền:
      - Lời thoại mẫu Tiếng Việt (`textarea.sample-dialogue-input`, tối đa 120 ký tự)
      - Chỉ dẫn đặc điểm giọng đọc (`textarea.performance-input` — `voice_prompt_en`)
      - Tên hiển thị giọng đọc (`input.voice-name-input`)
    sau đó bấm `Xem trước` để Google Flow (`models/gemini-v4s-tts-flow`) tổng hợp giọng đọc Tiếng Việt mới,
    tự động bắt lấy mã `voice_id` UUID mới + tải file âm thanh `.mp3` về `flow_final_pipeline/voice_samples/<key>_flow.mp3`,
    bấm `Lưu giọng nói mới` trên Google Flow và cập nhật vào `voices_and_characters.json`.
    """
    ensure_dirs_and_default_sheet()
    # Lưu cấu hình cơ bản trước
    save_voice_profile(payload)
    state = get_character_library_state()

    vkey = (payload.get("key") or "").strip().lower()
    vkey = __import__("re").sub(r"[^a-z0-9_]", "_", vkey).strip("_")
    v_obj = next((x for x in state.get("voices_list", []) if x["key"] == vkey), None)
    if not v_obj:
        return {"ok": False, "error": f"Không tìm thấy cấu hình giọng đọc #{vkey}"}

    v_name = v_obj.get("name") or f"Custom Voice {vkey}"
    v_prompt_en = (payload.get("voice_prompt_en") or v_obj.get("voice_prompt_en") or "").strip()
    if v_obj.get("gender") == "male" and "male" not in v_prompt_en.lower():
        v_prompt_en = f"Adult male baritone voice, {v_prompt_en}. Strictly male resonance."

    sample_vn = (payload.get("sample_dialogue_vn") or v_obj.get("sample_dialogue_vn") or COMMON_VN_DIALOGUE_PRESETS[0]["text"]).strip()
    sample_vn_118 = sample_vn[:118]
    project_id = payload.get("project_id") or "932bc2a1-07ea-4199-b147-80ab0018d41c"

    try:
        scripts_dir = os.path.join(PIPELINE_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import re as _re
        import run_all_7_videos_mt as mt
        from playwright.sync_api import sync_playwright

        audio_captured = []
        with sync_playwright() as pw:
            p_ctx = pw.chromium.launch_persistent_context(
                str(mt.profile_dir),
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-position=-2000,-2000", "--window-size=1280,800"],
            )
            pg = p_ctx.pages[0] if p_ctx.pages else p_ctx.new_page()

            def on_resp(r):
                if "flow-content.google/audio/" in r.url and r.status == 200:
                    try:
                        b = r.body()
                        if len(b) > 1000:
                            m = _re.search(r"flow-content\.google/audio/([0-9a-f\-]{36})", r.url)
                            vid = m.group(1) if m else ""
                            audio_captured.append((vid, r.url, b))
                    except Exception:
                        pass

            pg.on("response", on_resp)
            pg.goto(f"https://flow.google.com/project/{project_id}", wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(4200)

            pg.locator("button:has-text('Nhân vật'), [role='button']:has-text('Nhân vật')").first.click(timeout=6000)
            pg.wait_for_timeout(1400)
            pg.locator("text=MUSE Nhân vật 1").first.click(timeout=6000)
            pg.wait_for_timeout(1400)
            pg.locator(".voice-card-start-btn").first.click(timeout=6000)
            pg.wait_for_timeout(1800)

            audio_captured.clear()
            pg.locator("textarea.sample-dialogue-input").first.fill(sample_vn_118)
            pg.locator("textarea.performance-input").first.fill(v_prompt_en)
            if pg.locator("input.voice-name-input").count() > 0:
                pg.locator("input.voice-name-input").first.fill(v_name)
            pg.wait_for_timeout(600)

            pg.locator(".cdk-overlay-container button:has-text('Xem trước')").first.click(timeout=6000)
            got_vid = ""
            out_rel = f"voice_samples/{vkey}_flow.mp3"
            out_abs = os.path.join(PIPELINE_DIR, out_rel.replace("/", os.sep))

            for _ in range(30):
                pg.wait_for_timeout(1000)
                if audio_captured:
                    got_vid, _, got_bytes = audio_captured[-1]
                    with open(out_abs, "wb") as f_aud:
                        f_aud.write(got_bytes)
                    break

            if got_vid:
                if pg.locator("input.voice-name-input").count() > 0:
                    pg.locator("input.voice-name-input").first.fill(v_name)
                save_btn = pg.locator(".cdk-overlay-container button:has-text('Lưu giọng nói mới')").first
                if save_btn.count() > 0 and not save_btn.is_disabled():
                    save_btn.click(timeout=5000)
                    pg.wait_for_timeout(2500)

            p_ctx.close()

        if not got_vid or not os.path.isfile(out_abs):
            return {
                "ok": False,
                "error": "Google Flow chưa trả về file âm thanh sau 30 giây. Vui lòng kiểm tra phiên đăng nhập Google Flow.",
            }

        # Cập nhật voice_id mới & đường dẫn file âm thanh Tiếng Việt vào voices_and_characters.json
        updated_payload = dict(payload)
        updated_payload["key"] = vkey
        if vkey not in ("nv1", "nv2") or payload.get("overwrite_default_uuid"):
            updated_payload["voice_id"] = got_vid
        updated_payload["sample_vn_file"] = out_rel
        updated_payload["sample_dialogue_vn"] = sample_vn_118
        updated_payload["flow_synced"] = True
        import urllib.parse as _urlparse
        new_state = save_voice_profile(updated_payload)
        new_state["created_voice_id"] = got_vid
        new_state["created_voice"] = {"key": vkey, "name": v_name, "voice_id": got_vid}
        new_state["audio_path"] = out_abs
        new_state["audio_url"] = f"/api/media?path={_urlparse.quote(out_abs)}"
        new_state["sample_dialogue_vn"] = sample_vn_118
        msg = f"Đã tự động Custom giọng '{v_name}' trên Google Flow (UUID: {got_vid}) và tải mẫu âm thanh Tiếng Việt về máy!"
        new_state["message"] = msg
        new_state["flow_sync_message"] = msg
        return new_state
    except Exception as e:
        return {"ok": False, "error": f"Lỗi khi tự động Custom giọng trên Google Flow: {e}"}


def recommend_voice_for_product(payload: dict) -> dict:
    """
    Bộ Não Tư Vấn Giọng Đọc & Prompt Cho AI Agent (`AI Agent Voice Recommendation Engine`):
    Dựa trên 4 yếu tố:
      1. Ngành hàng & Đặc tính sản phẩm (tên, mô tả, giá bán)
      2. Mã Template Video đang chọn (#001 Nhà Xưởng, #002 Đồ Ăn Vặt POV Có Voice, #003 Đồ Ăn Vặt UGC)
      3. Vùng miền mục tiêu (Tự động / Miền Bắc / Miền Nam / Miền Trung)
      4. Giới tính giọng đọc ưu tiên (Tự động / Nữ / Nam)
    Trả về Top 3 Giọng đọc phù hợp nhất kèm Điểm số, Lý do chi tiết, Câu lệnh Voice Prompt và Câu Hook mẫu theo vùng miền.
    """
    state = get_character_library_state()
    voices_list = state.get("voices_list", [])
    chars_list = state.get("characters", [])

    pid = str(payload.get("product_id") or "").strip()
    title = str(payload.get("title") or "").strip()
    desc = str(payload.get("description") or "").strip()
    price = str(payload.get("price") or "").strip()
    template_code = str(payload.get("template_code") or "001").strip()
    pref_region = str(payload.get("preferred_region") or "auto").strip().lower()
    pref_gender = str(payload.get("preferred_gender") or "auto").strip().lower()

    # Nếu truyền product_id mà chưa có title, tự đọc từ store/info.json
    if pid and not title:
        for cand_info in (
            os.path.join(WS_DIR, "data", "tiktok_crawler", "data", "product_images", pid, "info.json"),
            os.path.join(PROJECTS_DIR, pid, "info.json"),
        ):
            if os.path.isfile(cand_info):
                try:
                    info_obj = json.loads(open(cand_info, "r", encoding="utf-8").read())
                    title = info_obj.get("name") or info_obj.get("title") or ""
                    desc = info_obj.get("description") or ""
                    price = str(info_obj.get("price") or "")
                    break
                except Exception:
                    pass

    text = f"{title} {desc}".lower()

    # Phân loại ngành hàng sản phẩm
    is_food_snack = any(k in text for k in [
        "ăn vặt", "kho quẹt", "cơm cháy", "bánh", "kẹo", "trà", "kombucha", "xoài", "mứt",
        "ô mai", "khô gà", "khô bò", "mực", "hạt", "sốt", "muối chấm", "mắm", "đặc sản", "sữa", "cà phê"
    ])
    is_southern_specialty = any(k in text for k in [
        "làng chài xưa", "tây ninh", "sài gòn", "miền tây", "bến tre", "cần thơ", "kho quẹt", "bánh tráng", "muối tôm"
    ])
    is_mens_or_tech = any(k in text for k in [
        "nam", "thắt lưng", "dây nịt", "ví da", "đồng hồ", "cạo râu", "tông đơ", "cơ khí",
        "ốc vít", "cờ lê", "máy khoan", "bluetooth", "tai nghe", "loa", "ô tô", "xe máy"
    ])
    is_beauty_decor = any(k in text for k in [
        "kem", "serum", "son", "nước hoa", "mỹ phẩm", "dưỡng da", "sữa rửa mặt", "xịt thơm", "decor", "trang điểm"
    ])
    is_spiritual_traditional = any(k in text for k in [
        "trầm hương", "nhang", "quế", "phong thủy", "tài lộc", "khai thái", "thảo dược", "đông y", "quà biếu"
    ])

    scored = []
    for v in voices_list:
        score = 65
        reasons = []
        vk = v["key"]
        v_reg = v.get("region", "north")
        v_gen = v.get("gender", "female")
        v_tone = v.get("tone_style", "trustworthy_expert")

        # 1. Chấm theo Ngành hàng
        if is_food_snack:
            if v_tone == "sweet_foodie":
                score += 22
                reasons.append("Chất giọng Review Ẩm thực kích thích vị giác, nhấn nhá độ ngon & topping cực cuốn")
            if is_southern_specialty and v_reg == "south":
                score += 12
                reasons.append("Món ăn/đặc sản mang phong vị Miền Nam nên giọng Sài Gòn tạo cảm giác đúng chuẩn bản địa")
        elif is_mens_or_tech:
            if v_gen == "male" and v_tone == "trustworthy_expert":
                score += 24
                reasons.append("Giọng Nam trầm ấm chuyên gia tạo độ tin cậy cao cho sản phẩm Đồ Nam / Kỹ thuật / Công nghệ")
            elif vk == "nv1":
                score += 18
                reasons.append("Giọng Nữ Tư vấn Xưởng (NV1) rõ ràng, lịch sự, hợp giới thiệu hộp quà tặng & kiểm định QC")
        elif is_beauty_decor:
            if v_gen == "female" and v_tone in ("sweet_foodie", "energetic_sale"):
                score += 20
                reasons.append("Giọng Nữ trẻ trung, sáng rõ rất hợp tâm lý tệp khách hàng nữ mua Mỹ phẩm / Chăm sóc nhà cửa")
        elif is_spiritual_traditional:
            if v_tone in ("chill_story", "trustworthy_expert"):
                score += 20
                reasons.append("Giọng đọc truyền cảm, điềm đạm phù hợp sản phẩm Phong thuỷ / Thảo mộc / Quà tặng")
        else:
            # Hàng gia dụng / tiêu dùng phổ thông
            if v_tone in ("energetic_sale", "trustworthy_expert"):
                score += 18
                reasons.append("Hàng gia dụng & tiêu dùng cần giọng Báo giá tận xưởng hoặc Chốt sale năng lượng cao")

        # 2. Chấm theo Mã Template Video
        if "002" in template_code or "pov" in template_code.lower():
            if v_tone == "sweet_foodie":
                score += 10
                reasons.append("Khớp hoàn hảo với nhịp độ 3 mốc Timeline [0-3.5s], [3.5-7s], [7-10s] của Template #002 (POV Có Voice)")
        elif "001" in template_code:
            if v_tone in ("trustworthy_expert", "energetic_sale"):
                score += 10
                reasons.append("Chuẩn nhịp đọc 44-48 từ/10s cho công thức Thang giá 3 bậc của Template #001 (Nhà Xưởng)")

        # 3. Ưu tiên Vùng miền & Giới tính do người dùng chọn
        if pref_region in ("north", "south", "central"):
            if v_reg == pref_region:
                score += 15
                reasons.append(f"Đúng vùng miền ưu tiên đã chọn ({v.get('region_label')})")
            else:
                score -= 15
        if pref_gender in ("female", "male"):
            if v_gen == pref_gender:
                score += 15
                reasons.append(f"Đúng giới tính giọng đọc đã chọn ({'Nam' if v_gen == 'male' else 'Nữ'})")
            else:
                score -= 15

        score = max(40, min(99, score))
        if not reasons:
            reasons.append("Giọng đọc đa năng, phát âm rõ ràng, phù hợp làm video Affiliate TikTok Shop")

        # Sinh câu Hook mẫu theo đúng phương ngữ (Bắc / Nam / Trung) của giọng đọc
        short_t = (title or "sản phẩm chính hãng").split("-")[0].strip()[:45]
        if v_reg == "south":
            sample_hook = f"Mấy bà ơi, ai đang tìm {short_t} vừa ngon vừa hời thì coi hết clip này nha, thiệt sự cuốn xỉu luôn nè!"
        elif v_reg == "central":
            sample_hook = f"Mọi người ơi, hôm nay mình giới thiệu {short_t} đậm đà hương vị truyền thống, dùng trong nhà hay làm quà đều quý!"
        else:
            if v_tone == "energetic_sale":
                sample_hook = f"Mọi người ơi, xả kho trực tiếp tại xưởng {short_t} nhé, giá không phải hai trăm đâu mà mỗi tài khoản một giá cực hời!"
            else:
                sample_hook = f"Các bác ơi, trên tay em đang là {short_t} vừa xuất xưởng kiểm định kỹ càng, chất lượng chuẩn chỉnh từng chi tiết đấy ạ!"

        # Tìm nhân vật gợi ý đi kèm
        matched_char = next((c for c in chars_list if c.get("default_voice") == vk), chars_list[0] if chars_list else {})

        scored.append({
            "voice": v,
            "score": score,
            "reasons": reasons,
            "sample_hook_vn": sample_hook,
            "recommended_character_key": matched_char.get("key", "nv1"),
            "recommended_character_name": matched_char.get("name", "Nhân Vật 1"),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    detected_cat = (
        "🍲 Đồ Ăn Vặt & Ẩm Thực" if is_food_snack
        else ("👔 Đồ Nam / Kỹ Thuật / Công Nghệ" if is_mens_or_tech
              else ("💄 Mỹ Phẩm / Làm Đẹp / Decor" if is_beauty_decor
                    else ("🌿 Truyền Thống / Thảo Mộc / Phong Thuỷ" if is_spiritual_traditional
                          else "🏠 Gia Dụng & Tiêu Dùng Nhanh")))
    )

    return {
        "ok": True,
        "product_id": pid,
        "product_title": title or "(Sản phẩm tuỳ chọn)",
        "detected_category": detected_cat,
        "template_code": template_code,
        "top_recommendations": scored[:4],
        "ai_criteria_explanation": [
            "1️⃣ Phân tích Ngành hàng & Đặc tính sản phẩm (Đồ ăn vặt cần giọng kích thích vị giác; Đồ nam/kỹ thuật cần giọng trầm uy tín; Hàng gia dụng xả kho cần giọng năng lượng FOMO).",
            "2️⃣ Đồng bộ với Cấu trúc Template Video (#001 Nhà Xưởng cần tốc độ 44-48 từ/10s đọc thang giá 3 bậc; #002 Đồ Ăn Vặt POV cần nhịp 38-42 từ/10s khớp 3 mốc gắp/múc đồ ăn).",
            "3️⃣ Tự động chuyển hoá Từ vựng Phương ngữ (Miền Bắc dùng 'các bác ơi, nhé, đấy ạ, chuẩn chỉnh'; Miền Nam dùng 'mấy bà ơi, nha, nghen, cuốn xỉu, hốt lẹ').",
            "4️⃣ Kết hợp kép: Gắn mã Voice ID trên Google Flow + Chèn câu lệnh Âm học tiếng Anh (voice_prompt_en) vào mục VOICE của từng phân cảnh để Veo 3.1 thể hiện đúng cảm xúc & vùng miền."
        ],
    }



def delete_character(char_key: str) -> dict:
    ck = (char_key or "").strip().lower()
    if not ck or not os.path.exists(VOICES_CHARS_PATH):
        return {"ok": False, "error": "Không tìm thấy nhân vật"}
    with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if ck not in cfg.get("characters", {}):
        return {"ok": False, "error": f"Nhân vật {ck} không tồn tại"}
    cfg["characters"].pop(ck, None)
    with open(VOICES_CHARS_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return get_character_library_state()


def save_character_sheet_template(payload: dict) -> dict:
    """Thêm hoặc chỉnh sửa 1 mẫu Character Sheet Template trong `Template/Character_Sheet_Templates/`."""
    templates = load_sheet_templates()
    tid = (payload.get("id") or "").strip().lower()
    if not tid:
        tid = f"sheet_mau_{len(templates) + 1}_{int(time.time()) % 10000}"

    sample_fn = payload.get("sample_image") or ""
    b64_img = payload.get("uploaded_sample_base64")
    if b64_img:
        if "," in b64_img:
            b64_img = b64_img.split(",", 1)[1]
        raw_bytes = base64.b64decode(b64_img)
        sample_fn = f"{tid}.jpg"
        with open(os.path.join(SHEET_TEMPLATES_DIR, sample_fn), "wb") as f:
            f.write(raw_bytes)

    found = None
    for t in templates:
        if t.get("id") == tid:
            found = t
            break
    if not found:
        found = {"id": tid}
        templates.append(found)

    found["name"] = payload.get("name") or found.get("name") or f"Mẫu Character Sheet ({tid})"
    found["badge"] = payload.get("badge") or found.get("badge") or "MẪU TUỲ CHỌN"
    found["aspect_ratio"] = payload.get("aspect_ratio") or found.get("aspect_ratio") or "3:2"
    found["description"] = payload.get("description") or found.get("description") or ""
    if sample_fn:
        found["sample_image"] = sample_fn
    if "character_sheet_prompt" in payload:
        found["character_sheet_prompt"] = payload["character_sheet_prompt"]
    if "product_with_character_prompt" in payload:
        found["product_with_character_prompt"] = payload["product_with_character_prompt"]

    clean_templates = []
    for t in templates:
        c = dict(t)
        c.pop("sample_image_path", None)
        clean_templates.append(c)

    with open(SHEET_TEMPLATES_JSON, "w", encoding="utf-8") as f:
        json.dump({"templates": clean_templates}, f, ensure_ascii=False, indent=2)

    return get_character_library_state()


def generate_character_or_product_image(payload: dict) -> dict:
    """
    Tạo ảnh Character Sheet hoặc ảnh Nhân vật cầm sản phẩm bằng:
      - `model = "nano_banana"` (Google Flow Nano Banana 2.1 - BELUGA 2K)
      - `model = "chatgpt"` (ChatGPT Image API `gpt-image-1` / `dall-e-3` qua CLIProxy `:8317` hoặc OpenAI API)
    """
    mode = payload.get("mode", "character_sheet")  # "character_sheet" | "product_ref"
    model_choice = (payload.get("model") or "nano_banana").lower()
    sheet_template_id = payload.get("sheet_template_id") or "sheet_6panel_studio"
    char_key = (payload.get("char_key") or "nv1").lower()
    char_desc = (payload.get("appearance_en") or "young Vietnamese woman, shoulder-length black hair, friendly smile").strip()
    custom_prompt = (payload.get("custom_prompt") or "").strip()
    pid = (payload.get("pid") or "").strip()

    templates = load_sheet_templates()
    tpl = next((t for t in templates if t.get("id") == sheet_template_id), templates[0] if templates else {})

    if custom_prompt:
        final_prompt = custom_prompt
    elif mode == "product_ref":
        base_p = tpl.get("product_with_character_prompt") or (
            "Photorealistic vertical 9:16 medium-wide standing photo: the exact same woman ({character_description}), "
            "{outfit_en}, {setting_en}, holding and presenting the exact product from the product reference image at waist level."
        )
        final_prompt = base_p.format(
            character_description=char_desc,
            outfit_en=payload.get("outfit_en") or "wearing a polite professional blazer over a collared shirt",
            setting_en=payload.get("setting_en") or "standing behind a worktable in a modern factory inspection room",
        )
    else:
        base_p = tpl.get("character_sheet_prompt") or (
            "Photorealistic 6-panel character reference turnaround sheet arranged in a 2x3 grid on a neutral light-grey studio background of ({character_description})."
        )
        final_prompt = base_p.format(character_description=char_desc)

    out_dir = CHARS_DIR if mode == "character_sheet" else os.path.join(PROJECTS_DIR, pid or "_preview_gen")
    os.makedirs(out_dir, exist_ok=True)
    out_filename = (
        f"{char_key}_sheet_{int(time.time())}.jpg"
        if mode == "character_sheet"
        else f"{char_key}_prodref_{int(time.time())}.jpg"
    )
    out_abs = os.path.join(out_dir, out_filename)

    # 1. Nếu chọn model ChatGPT (`chatgpt`), thử gọi CLIProxy (:8317) hoặc OpenAI Images API trước
    if model_choice == "chatgpt":
        api_url = os.environ.get("OPENAI_IMAGE_API_URL", "http://127.0.0.1:8317/v1/images/generations")
        api_key = os.environ.get("OPENAI_API_KEY", "sk-cliproxy-local")
        req_body = json.dumps({
            "model": "gpt-image-1",
            "prompt": final_prompt,
            "n": 1,
            "size": "1024x1536" if mode == "product_ref" else "1536x1024",
            "response_format": "b64_json",
        }).encode("utf-8")
        try:
            req = urllib.request.Request(
                api_url,
                data=req_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                img_item = (resp_data.get("data") or [{}])[0]
                if img_item.get("b64_json"):
                    raw_bytes = base64.b64decode(img_item["b64_json"])
                    with open(out_abs, "wb") as f:
                        f.write(raw_bytes)
                    return {
                        "ok": True,
                        "model_used": "ChatGPT Image (gpt-image-1)",
                        "image_path": out_abs,
                        "prompt": final_prompt,
                    }
        except Exception as e_gpt:
            print(f"[CHAR-GEN] ChatGPT endpoint returned {e_gpt}, falling back to Google Flow Nano Banana 2.1...", flush=True)

    # 2. Tạo ảnh qua Google Flow Nano Banana 2.1 (`BELUGA` / `ogiZ0b` + Upsample 2K `SPrCad`)
    try:
        scripts_dir = os.path.join(PIPELINE_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import run_all_7_videos_mt as mt
        from playwright.sync_api import sync_playwright

        state_cfg = get_character_library_state()
        char_entry = next((c for c in state_cfg["characters"] if c["key"] == char_key), None)
        project_id = (char_entry or {}).get("project_id") or "932bc2a1-07ea-4199-b147-80ab0018d41c"
        char_uuid = (char_entry or {}).get("character_id") or "208606a7-a345-48b2-af32-9fd3c37d0c9a"

        with sync_playwright() as pw:
            p_ctx = pw.chromium.launch_persistent_context(
                str(mt.profile_dir),
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-position=-2000,-2000", "--window-size=1280,800"],
            )
            raw_cookies = p_ctx.cookies(["https://flow.google.com", "https://google.com", "https://www.google.com", "https://accounts.google.com"])
            p_ctx.close()
            clean_cookies = [c for c in raw_cookies if "GRECAPTCHA" not in c.get("name", "").upper()]
            cookie_map = {c["name"]: c["value"] for c in clean_cookies}
            cookie_hdr = "; ".join(f"{k}={v}" for k, v in cookie_map.items())

            browser = pw.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-position=-2000,-2000", "--window-size=1280,800"],
            )
            ctx = browser.new_context()
            ctx.add_init_script(mt.gvt._FLOW_HIJACK_BYPASS_JS)
            ctx.add_cookies(clean_cookies)
            pg = ctx.new_page()
            pg.goto(f"https://flow.google.com/project/{project_id}", wait_until="domcontentloaded", timeout=45000)
            pg.evaluate(mt.gvt._FLOW_HIJACK_BYPASS_JS)
            pg.wait_for_function(
                "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise",
                timeout=35000,
            )
            pg.wait_for_timeout(1200)
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
            prod_uuids = []
            if mode == "product_ref" and pid:
                prod_img_dir = os.path.join(PROJECTS_DIR, pid, "product_images")
                cand_jpg = os.path.join(prod_img_dir, "prod_1.jpg")
                if os.path.exists(cand_jpg):
                    ok_u, u_id, _ = mt.upload_single_product_ref_in_page(pg, wz, project_id, cand_jpg)
                    if ok_u and u_id:
                        prod_uuids = [u_id]

            task = {
                "pid": pid or char_key,
                "v_key": char_key,
                "project_id": project_id,
                "char_id": char_uuid if mode == "product_ref" else char_uuid,
                "prod_uuids": prod_uuids,
                "prompt_str": final_prompt,
                "out_file": out_abs,
            }
            ok, gen_uuid, err = mt.generate_variant_ref_image_in_page(pg, wz, cookie_hdr, dl_headers, task)
            ctx.close()
            browser.close()

        if ok and os.path.exists(out_abs):
            return {
                "ok": True,
                "model_used": "Nano Banana 2.1 (BELUGA 2K)",
                "image_path": out_abs,
                "media_uuid": gen_uuid,
                "prompt": final_prompt,
            }
        return {"ok": False, "error": err or "Không tạo được ảnh qua Nano Banana 2.1", "prompt": final_prompt}
    except Exception as e:
        return {"ok": False, "error": str(e), "prompt": final_prompt}

