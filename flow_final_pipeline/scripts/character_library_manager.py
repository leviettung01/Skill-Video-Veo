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
                    "Hyper-photorealistic 6-panel character reference turnaround sheet arranged in a clean 2x3 grid with thin white borders on a neutral light-grey studio background. "
                    "Top row: full-body standing views (Front, Back, Side) of ({character_description}) with full mature adult proportions. "
                    "Bottom row: close-up portrait views (Front, 3/4 angle, Side profile) of the exact same person with detailed visible natural skin pores, rosy dewy Douyin glass-skin glow, and expressive eyes with crisp catchlights. "
                    "Shot on Sony A7R V 85mm f/1.4 GM lens, consistent soft studio lighting, identical face across all panels, 8k photorealistic, zero AI plastic look."
                ),
                "product_with_character_prompt": (
                    "Subject & Identity: A hyper-photorealistic vertical 9:16 close-medium upper-body portrait (framed from top of head with natural headroom to waist/hips, camera at 1.2 meters distance) "
                    "of the exact same person from the character reference ({character_description}), {outfit_en}, {setting_en}. "
                    "Skin & Makeup: Detailed visible natural skin pores, radiant rosy dewy Douyin glass-skin finish with subtle light reflection on the nose bridge, cheeks, and forehead, matching fair skin tone across face, neck, and hands, expressive eyes with crisp catchlights, wispy eyelashes, thin winged liner, soft pink blush, and glossy ombré cherry-pink lips. "
                    "PHYSIQUE: Full, mature adult proportions with natural curves (90-60-90 proportions, C-cup natural bust, slender waist). "
                    "Expression / Pose: Warm, charming smile toward the camera, subtle head tilt, torso turned slightly (5-10 degrees) for relaxed natural asymmetry, holding and presenting the exact product from the product reference image at chest-to-waist level facing the camera (true-to-life natural hand-held scale, NOT oversized). "
                    "Keep the product 100% identical to the product reference image. Shot on Sony A7R V 50mm f/1.4 GM at f/2.0, soft diffused key lighting, creamy background bokeh, 2K (1536x2752), zero AI look."
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
        owner_prof = str(v_item.get("owner_profile") or "leviettung04").strip() or "leviettung04"
        v_item["owner_profile"] = owner_prof
        acc_vids = dict(v_item.get("account_voice_ids") or {})
        vid_cur = str(v_item.get("voice_id") or "").strip()
        if len(vid_cur) == 36 and "-" in vid_cur and owner_prof not in acc_vids:
            acc_vids[owner_prof] = vid_cur
        v_item["account_voice_ids"] = acc_vids
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

        rel_bed = cval.get("bedroom_ref_file", "")
        abs_bed = os.path.join(PIPELINE_DIR, rel_bed.replace("/", os.sep)) if rel_bed else ""
        item["bedroom_ref_abs"] = abs_bed if (abs_bed and os.path.exists(abs_bed)) else abs_img

        rel_ward = cval.get("wardrobe_sheet_file", "")
        abs_ward = os.path.join(PIPELINE_DIR, rel_ward.replace("/", os.sep)) if rel_ward else ""
        item["wardrobe_sheet_abs"] = abs_ward if (abs_ward and os.path.exists(abs_ward)) else abs_img

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
    is_male = (gender or "").lower() == "male"
    if region == "south":
        r_en = "Southern Vietnamese (Saigon accent)"
        price_words = "“ba mươi cành”, “bốn trăm ka”, “năm triệu”, “hai triệu rưỡi”, “hai trăm”, “xịn xò”, “cực kỳ rẻ” and “miễn phí ship”"
    elif region == "central":
        r_en = "Central Vietnamese (Hue/Da Nang accent)"
        price_words = "“ba mươi ka”, “bốn trăm ka”, “năm triệu”, “hai triệu rưỡi”, “đậm đà chuẩn vị”, “cực kỳ rẻ” and “miễn phí ship”"
    else:
        r_en = "Northern Vietnamese (Hanoi accent)"
        price_words = "“ba mươi ka”, “bốn trăm ka”, “năm triệu”, “bốn triệu”, “ba triệu”, “hai triệu rưỡi”, “hai triệu”, “cực kỳ rẻ” and “miễn phí ship”"

    if tone_style == "energetic_sale":
        delivery_en = "energetic TikTok Shop sales delivery, persuasive but not aggressive, warm smile audible in the voice, confident and conversational, fast moderately paced speech with crisp consonants"
    elif tone_style == "sweet_foodie":
        delivery_en = "cheerful and appetizing TikTok Shop food and lifestyle reviewer delivery, warm mouth-watering inflection, friendly smile audible in the voice, confident and conversational, moderately fast speech with crisp consonants"
    elif tone_style == "chill_story":
        delivery_en = "warm, sincere and reassuring TikTok Shop storytelling and specialty consultant delivery, gentle smile audible in the voice, smooth and conversational articulation with crisp consonants"
    else:
        delivery_en = "energetic and authoritative TikTok Shop factory direct & QC expert sales delivery, persuasive and trustworthy, warm confident smile audible in the voice, fast moderately paced speech with crisp consonants"

    if is_male:
        return (
            f"Vietnamese male commercial presenter, young adult masculine voice, bright and energetic baritone-tenor pitch, "
            f"clear forward chest projection, natural {r_en} pronunciation, {delivery_en}. "
            f"Emphasize important words and prices such as {price_words}. "
            f"Use short natural pauses after each price, slight playful disbelief when saying “không phải”, and an excited reassuring lift at the end of promotional sentences. "
            f"Keep the same male voice, masculine pitch, accent, loudness, speaking speed and emotional style across every clip. "
            f"No announcer voice, no radio voice, no singing, no whispering, no shouting, no female resonance, no high-pitched female voice, no English accent, no robotic delivery."
        )
    return (
        f"Vietnamese female commercial presenter, young adult voice, bright and friendly, mid-to-high pitch, "
        f"clear forward projection, natural {r_en} pronunciation, {delivery_en}. "
        f"Emphasize important words and prices such as {price_words}. "
        f"Use short natural pauses after each price, slight playful disbelief when saying “không phải”, and an excited reassuring lift at the end of promotional sentences. "
        f"Keep the same female voice, pitch, accent, loudness, speaking speed and emotional style across every clip. "
        f"No announcer voice, no radio voice, no singing, no whispering, no shouting, no male resonance, no English accent, no robotic delivery."
    )


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

    owner_prof = str(payload.get("owner_profile") or existing_v.get("owner_profile") or "leviettung04").strip() or "leviettung04"
    acc_vids = dict(existing_v.get("account_voice_ids") or {})
    if isinstance(payload.get("account_voice_ids"), dict):
        acc_vids.update(payload["account_voice_ids"])
    eff_vid = (payload.get("voice_id") or existing_v.get("voice_id") or flow_slug or "27f51973-e290-4a38-bd7a-9d6fbe81b2f6").strip()
    if len(eff_vid) == 36 and "-" in eff_vid:
        acc_vids.setdefault(owner_prof, eff_vid)

    voice_entry = {
        "key": vkey,
        "name": (payload.get("name") or f"Giọng {region_labels.get(region, 'Việt Nam')} ({vkey})").strip(),
        "voice_id": eff_vid,
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
        "owner_profile": owner_prof,
        "account_voice_ids": acc_vids,
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

    # Đồng bộ danh sách custom_voices để các module CLI / Đa tài khoản đọc trực tiếp
    cfg["custom_voices"] = [
        {
            "key": k,
            "voice_id": v.get("voice_id", ""),
            "name": v.get("name", k),
            "gender": v.get("gender", "female"),
            "region": v.get("region", "north"),
            "flow_slug": v.get("flow_slug", ""),
            "owner_profile": v.get("owner_profile", "leviettung04"),
            "account_voice_ids": v.get("account_voice_ids", {}),
            "project_id": "932bc2a1-07ea-4199-b147-80ab0018d41c",
            "description": v.get("description", ""),
        }
        for k, v in cfg.get("voices", {}).items()
        if isinstance(v, dict)
    ]

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


def resolve_voice_id_for_account(voice_id_or_key: str, profile_name: str = "") -> str:
    """
    Khi chạy Đa Tài Khoản Google Flow (Round-Robin):
    Mỗi tài khoản có thể có mã UUID Custom Voice riêng trong `account_voice_ids[profile_name]`.
    - Nếu tài khoản `profile_name` đã có UUID riêng trong `account_voice_ids[profile_name]` -> trả về UUID đó.
    - Nếu `profile_name` là tài khoản gốc (`owner_profile`, mặc định `leviettung04`) -> trả về `voice_id` gốc.
    - Nếu `profile_name` là tài khoản phụ chưa đồng bộ/nhân bản UUID Custom Voice -> trả về `account_voice_ids.get(profile_name)` hoặc `voice_id` / `flow_slug`.
    """
    raw = str(voice_id_or_key or "").strip()
    if not raw:
        return ""
    prof = str(profile_name or "").strip()
    if not os.path.isfile(VOICES_CHARS_PATH):
        return raw
    try:
        with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for vk, v in (cfg.get("voices") or {}).items():
            if not isinstance(v, dict):
                continue
            vid = str(v.get("voice_id") or "").strip()
            if raw.lower() in (vk.lower(), vid.lower(), str(v.get("name") or "").strip().lower()):
                acc_map = v.get("account_voice_ids") or {}
                if prof and prof in acc_map and acc_map[prof]:
                    return str(acc_map[prof]).strip()
                owner = str(v.get("owner_profile") or "leviettung04").strip()
                if not prof or prof.lower() == owner.lower():
                    return vid or raw
                # Nếu tài khoản phụ chưa nhân bản UUID riêng, kiểm tra bất kỳ UUID nào đã map hoặc trả về vid
                return str(acc_map.get(prof) or vid or v.get("flow_slug") or raw).strip()
    except Exception:
        pass
    return raw


def _list_flow_accounts_with_cookies(target_profile: str = "") -> list:
    """Liệt kê tất cả các tài khoản Google Flow đang có file Cookie hợp lệ để đồng bộ hoặc nhân bản Voice đa tài khoản."""
    target_clean = str(target_profile or "").strip().lower()
    if target_clean == "all":
        target_clean = ""
    results = []
    seen = set()

    acc_grok_json = os.path.join(WORKSPACE_DIR, "data", "google_flow_grok", "accounts.json")
    default_proj = "932bc2a1-07ea-4199-b147-80ab0018d41c"
    if os.path.isfile(acc_grok_json):
        try:
            rows = json.loads(open(acc_grok_json, "r", encoding="utf-8").read())
            if isinstance(rows, list):
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    prof = str(r.get("profile_name") or "").strip()
                    if not prof or prof in seen:
                        continue
                    if target_clean and prof.lower() != target_clean:
                        continue
                    ck = _load_clean_flow_cookies(prof)
                    if ck:
                        proj = str(r.get("proxy_url") or default_proj).strip()
                        if proj.startswith("http") or len(proj) < 20:
                            proj = default_proj
                        seen.add(prof)
                        results.append({
                            "profile_name": prof,
                            "name": str(r.get("name") or f"Google_{prof}"),
                            "project_id": proj,
                            "cookies": ck,
                        })
        except Exception:
            pass

    if not results:
        fallback_prof = str(target_profile or "leviettung04").strip()
        if fallback_prof.lower() == "all":
            fallback_prof = "leviettung04"
        ck = _load_clean_flow_cookies(fallback_prof)
        if ck:
            results.append({
                "profile_name": fallback_prof,
                "name": f"Google_{fallback_prof}",
                "project_id": default_proj,
                "cookies": ck,
            })
    return results


def scan_and_sync_flow_voices(payload: dict = None) -> dict:
    """
    Đồng bộ 2 chiều Danh Sách Giọng Đọc Custom giữa Google Flow và Tool (Hỗ trợ Đa Tài Khoản):
      1. Quét trực tiếp trên tài khoản Google Flow (`live_flow_sync=True`) tất cả các Custom Voice người dùng đã tạo thủ công
         trong mục `Giọng nói` (`.asset-item` có icon `settings_2`), tự động lấy Tên Giọng, Hội Thoại Mẫu Tiếng Việt,
         Prompt Chỉ Dẫn (`voice_prompt_en`), Mã `voice_id` UUID và tải file âm thanh `.mp3` về kho `voice_samples/`.
      2. Nếu bật `clone_to_all_accounts=True`, tự động nhân bản (clone) các giọng Custom sang toàn bộ các tài khoản Google Flow
         khác đang có Cookie hợp lệ và lưu bảng ánh xạ `account_voice_ids: {profile_name: voice_uuid}` để khi chạy Đa Luồng
         xoay vòng nhiều tài khoản, tài khoản nào cũng dùng đúng mã Voice UUID của tài khoản đó!
    """
    payload = payload or {}
    live_flow_sync = bool(payload.get("live_flow_sync", True))
    clone_to_all = bool(payload.get("clone_to_all_accounts", False))
    target_profile = str(payload.get("profile_name") or "").strip()
    download_missing_audio = bool(payload.get("download_missing_audio", True))

    ensure_dirs_and_default_sheet()
    imported_names = []
    updated_names = []
    cloned_accounts_summary = []
    live_sync_errors = []

    if live_flow_sync:
        accounts_to_scan = _list_flow_accounts_with_cookies(target_profile if not clone_to_all else "")
        if accounts_to_scan:
            try:
                scripts_dir = os.path.join(PIPELINE_DIR, "scripts")
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                if WORKSPACE_DIR not in sys.path:
                    sys.path.insert(0, WORKSPACE_DIR)
                import re as _re
                import unicodedata as _ud
                import grok_video_tool as gvt
                from playwright.sync_api import sync_playwright

                def _slugify_vn(text_val: str) -> str:
                    s = _ud.normalize("NFKD", str(text_val or "")).encode("ascii", "ignore").decode("ascii").lower()
                    s = _re.sub(r"[^a-z0-9]+", "_", s).strip("_")
                    return s[:36] or "flow_custom"

                with open(VOICES_CHARS_PATH, "r", encoding="utf-8") as f:
                    cfg_live = json.load(f)
                voices_map = cfg_live.setdefault("voices", {})

                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        channel="chrome",
                        headless=False,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--window-position=-2000,-2000",
                            "--window-size=1280,800",
                        ],
                    )
                    try:
                        # Bước 1: Quét toàn bộ Custom Voice có trên tài khoản nguồn (hoặc các tài khoản đã chọn)
                        primary_accs = accounts_to_scan if not clone_to_all else accounts_to_scan[:1]
                        for acc_info in primary_accs:
                            prof_name = acc_info["profile_name"]
                            proj_id = acc_info["project_id"]
                            ctx = browser.new_context()
                            ctx.add_init_script(gvt._FLOW_HIJACK_BYPASS_JS)
                            ctx.add_cookies(acc_info["cookies"])
                            pg = ctx.new_page()
                            audio_captured = []

                            def _make_on_resp(bucket):
                                def _on_resp(r):
                                    if "flow-content.google/audio/" in r.url and r.status == 200:
                                        try:
                                            b = r.body()
                                            if len(b) > 1000:
                                                m = _re.search(r"flow-content\.google/audio/([0-9a-f\-]{36})", r.url)
                                                vid = m.group(1) if m else ""
                                                bucket.append((vid, r.url, b))
                                        except Exception:
                                            pass
                                return _on_resp

                            pg.on("response", _make_on_resp(audio_captured))
                            try:
                                pg.goto(f"https://flow.google.com/project/{proj_id}", wait_until="domcontentloaded", timeout=40000)
                                pg.evaluate(gvt._FLOW_HIJACK_BYPASS_JS)
                                pg.wait_for_function(
                                    "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e",
                                    timeout=25000,
                                )
                                pg.wait_for_timeout(1500)
                                pg.locator("button:has-text('Nhân vật'), [role='button']:has-text('Nhân vật')").first.click(force=True, timeout=6000)
                                pg.wait_for_timeout(1200)
                                pg.locator("text=MUSE").first.click(force=True, timeout=6000)
                                pg.wait_for_timeout(1200)
                                pg.locator(".voice-card-start-btn").first.click(force=True, timeout=6000)
                                pg.wait_for_timeout(1600)

                                # Thu thập danh sách tất cả Custom Voice (có icon settings_2) ở đầu danh sách Giọng nói
                                custom_titles_seen = []
                                for scroll_step in range(6):
                                    pg.evaluate(
                                        """(step) => {
                                            const v = document.querySelector('.cdk-overlay-container cdk-virtual-scroll-viewport.asset-list-viewport');
                                            if (v) v.scrollTop = step * 180;
                                        }""",
                                        scroll_step,
                                    )
                                    pg.wait_for_timeout(250)
                                    items_meta = pg.evaluate(
                                        """() => {
                                            const els = Array.from(document.querySelectorAll('.cdk-overlay-container .asset-item'));
                                            return els.map(e => {
                                                const txt = (e.innerText || '').trim();
                                                const lines = txt.split(/\\r?\\n/).map(s => s.trim()).filter(Boolean);
                                                const isCustom = lines.includes('settings_2');
                                                const cleanLines = lines.filter(l => l !== 'graphic_eq' && l !== 'settings_2');
                                                return {
                                                    isCustom,
                                                    titleLine: cleanLines[0] || '',
                                                    subLine: cleanLines[1] || ''
                                                };
                                            }).filter(x => x.isCustom && x.titleLine);
                                        }"""
                                    )
                                    for im in items_meta:
                                        if im["titleLine"] not in custom_titles_seen:
                                            custom_titles_seen.append(im["titleLine"])
                                    # Nếu đã cuộn tới giọng gốc Achernar thì dừng
                                    has_builtin = pg.locator(".cdk-overlay-container .asset-item:has-text('Achernar')").count() > 0
                                    if has_builtin and scroll_step >= 1:
                                        break

                                # Cuộn lại lên đầu và đọc chi tiết từng Custom Voice
                                pg.evaluate(
                                    """() => {
                                        const v = document.querySelector('.cdk-overlay-container cdk-virtual-scroll-viewport.asset-list-viewport');
                                        if (v) v.scrollTop = 0;
                                    }"""
                                )
                                pg.wait_for_timeout(300)

                                for short_title in custom_titles_seen:
                                    # Tìm và click vào item custom voice đó
                                    loc_item = pg.locator(".cdk-overlay-container .asset-item").filter(has_text=short_title[:18]).first
                                    if loc_item.count() == 0:
                                        continue
                                    loc_item.click(force=True, timeout=4000)
                                    pg.wait_for_timeout(550)

                                    full_name = ""
                                    if pg.locator(".cdk-overlay-container input.voice-name-input").count() > 0:
                                        full_name = pg.locator(".cdk-overlay-container input.voice-name-input").first.input_value().strip()
                                    if not full_name:
                                        full_name = short_title.strip()

                                    sample_dlg = ""
                                    if pg.locator(".cdk-overlay-container textarea.sample-dialogue-input").count() > 0:
                                        sample_dlg = pg.locator(".cdk-overlay-container textarea.sample-dialogue-input").first.input_value().strip()

                                    perf_prompt = ""
                                    if pg.locator(".cdk-overlay-container textarea.performance-input").count() > 0:
                                        perf_prompt = pg.locator(".cdk-overlay-container textarea.performance-input").first.input_value().strip()

                                    # Kiểm tra xem giọng này đã có trong voices_and_characters.json chưa
                                    matched_vk = None
                                    norm_full = full_name.lower().replace("(nv1)", "").replace("(nv2)", "").replace("(nv3)", "").strip()
                                    for vk_cand, v_cand in voices_map.items():
                                        if not isinstance(v_cand, dict):
                                            continue
                                        c_name = str(v_cand.get("name") or "").lower().replace("(nv1)", "").replace("(nv2)", "").replace("(nv3)", "").strip()
                                        if c_name == norm_full or norm_full in c_name or c_name in norm_full:
                                            matched_vk = vk_cand
                                            break

                                    is_new_manual_voice = False
                                    if not matched_vk:
                                        is_new_manual_voice = True
                                        matched_vk = f"v_flow_{_slugify_vn(full_name)}"
                                        idx_dup = 2
                                        base_vk = matched_vk
                                        while matched_vk in voices_map:
                                            matched_vk = f"{base_vk}_{idx_dup}"
                                            idx_dup += 1

                                    cur_entry = dict(voices_map.get(matched_vk) or {})
                                    comb_txt = f"{full_name} {perf_prompt}".lower()
                                    is_male_v = ("male" in comb_txt and "female" not in comb_txt) or ("nam " in full_name.lower() and "nữ" not in full_name.lower() and "miền nam" not in full_name.lower()) or ("giọng nam" in full_name.lower()) or ("nam miền" in full_name.lower()) or ("nam bắc" in full_name.lower())
                                    gender_v = cur_entry.get("gender") or ("male" if is_male_v else "female")
                                    region_v = cur_entry.get("region") or (
                                        "south" if any(k in comb_txt for k in ("miền nam", "southern", "saigon", "sài gòn"))
                                        else ("central" if any(k in comb_txt for k in ("miền trung", "central", "hue")) else "north")
                                    )
                                    tone_v = cur_entry.get("tone_style") or (
                                        "sweet_foodie" if any(k in comb_txt for k in ("ngọt ngào", "foodie", "ẩm thực", "ăn vặt"))
                                        else ("chill_story" if any(k in comb_txt for k in ("dịu dàng", "kể chuyện", "gentle")) else "energetic_sale")
                                    )
                                    slug_v = cur_entry.get("flow_slug") or _resolve_base_speaker_title(gender_v, "", tone_v, region_v).lower()

                                    out_rel = cur_entry.get("sample_vn_file") or f"voice_samples/{matched_vk}_flow.mp3"
                                    out_abs = os.path.join(PIPELINE_DIR, out_rel.replace("/", os.sep))
                                    cur_vid = str(cur_entry.get("voice_id") or "").strip()
                                    acc_vids = dict(cur_entry.get("account_voice_ids") or {})

                                    need_preview_capture = (
                                        is_new_manual_voice
                                        or (download_missing_audio and not os.path.isfile(out_abs))
                                        or (len(cur_vid) != 36 and prof_name not in acc_vids)
                                    )
                                    got_vid = acc_vids.get(prof_name) or (cur_vid if len(cur_vid) == 36 else "")

                                    if need_preview_capture:
                                        audio_captured.clear()
                                        prev_btn = pg.locator(".cdk-overlay-container button:has-text('Xem trước')").first
                                        if prev_btn.count() > 0:
                                            prev_btn.click(force=True, timeout=5000)
                                            for _ in range(18):
                                                pg.wait_for_timeout(700)
                                                if audio_captured:
                                                    cap_vid, _, cap_bytes = audio_captured[-1]
                                                    if cap_vid:
                                                        got_vid = cap_vid
                                                    with open(out_abs, "wb") as f_mp3:
                                                        f_mp3.write(cap_bytes)
                                                    break

                                    if got_vid:
                                        acc_vids[prof_name] = got_vid
                                    eff_vid = cur_vid if (matched_vk in ("nv1", "nv2") and len(cur_vid) == 36) else (got_vid or cur_vid or slug_v)

                                    cur_entry.update({
                                        "key": matched_vk,
                                        "name": cur_entry.get("name") or full_name,
                                        "voice_id": eff_vid,
                                        "flow_slug": slug_v,
                                        "gender": gender_v,
                                        "region": region_v,
                                        "region_label": "Miền Nam (Sài Gòn)" if region_v == "south" else ("Miền Trung (Huế / Đà Nẵng)" if region_v == "central" else "Miền Bắc (Hà Nội)"),
                                        "tone_style": tone_v,
                                        "tone_label": cur_entry.get("tone_label") or ("🔥 Năng lượng cao • Chốt Sale" if tone_v == "energetic_sale" else ("🍯 Ngọt ngào • Review Ẩm Thực" if tone_v == "sweet_foodie" else "🛡️ Uy tín • Tư vấn")),
                                        "speed_wpm": cur_entry.get("speed_wpm") or "44-48 từ / 10s (Tốc độ Nhanh)",
                                        "sample_url": cur_entry.get("sample_url") or f"https://www.gstatic.com/aitestkitchen/voices/samples/{slug_v.capitalize()}.wav",
                                        "sample_vn_file": out_rel,
                                        "sample_dialogue_vn": sample_dlg or cur_entry.get("sample_dialogue_vn") or COMMON_VN_DIALOGUE_PRESETS[0]["text"],
                                        "voice_prompt_en": perf_prompt or cur_entry.get("voice_prompt_en") or build_voice_prompt_en(gender_v, region_v, tone_v),
                                        "dialect_markers_vn": cur_entry.get("dialect_markers_vn") or "các bác ơi, nhé, miễn phí ship, cực kỳ rẻ",
                                        "recommended_templates": cur_entry.get("recommended_templates") or ["001", "002"],
                                        "recommended_categories": cur_entry.get("recommended_categories") or ["Đa ngành hàng", "TikTok Affiliate"],
                                        "description": cur_entry.get("description") or f"Giọng {'Nam' if gender_v == 'male' else 'Nữ'} đồng bộ trực tiếp từ Google Flow ({prof_name}).",
                                        "flow_synced": True,
                                        "owner_profile": cur_entry.get("owner_profile") or prof_name,
                                        "account_voice_ids": acc_vids,
                                    })
                                    voices_map[matched_vk] = cur_entry
                                    if is_new_manual_voice:
                                        imported_names.append(full_name)
                                    else:
                                        updated_names.append(cur_entry["name"])
                            except Exception as e_acc:
                                live_sync_errors.append(f"{prof_name}: {str(e_acc)[:120]}")
                            finally:
                                try:
                                    ctx.close()
                                except Exception:
                                    pass

                        # Bước 2: Nếu bật `clone_to_all_accounts=True`, nhân bản các giọng Custom sang các tài khoản Google Flow phụ
                        if clone_to_all and len(accounts_to_scan) > 1:
                            for sec_acc in accounts_to_scan[1:]:
                                sec_prof = sec_acc["profile_name"]
                                sec_proj = sec_acc["project_id"]
                                cloned_cnt = 0
                                ctx2 = browser.new_context()
                                ctx2.add_init_script(gvt._FLOW_HIJACK_BYPASS_JS)
                                ctx2.add_cookies(sec_acc["cookies"])
                                pg2 = ctx2.new_page()
                                sec_audio = []
                                pg2.on("response", _make_on_resp(sec_audio))
                                try:
                                    pg2.goto(f"https://flow.google.com/project/{sec_proj}", wait_until="domcontentloaded", timeout=40000)
                                    pg2.evaluate(gvt._FLOW_HIJACK_BYPASS_JS)
                                    pg2.wait_for_function("() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e", timeout=25000)
                                    pg2.wait_for_timeout(1500)
                                    pg2.locator("button:has-text('Nhân vật'), [role='button']:has-text('Nhân vật')").first.click(force=True, timeout=6000)
                                    pg2.wait_for_timeout(1200)
                                    pg2.locator("text=MUSE").first.click(force=True, timeout=6000)
                                    pg2.wait_for_timeout(1200)
                                    pg2.locator(".voice-card-start-btn").first.click(force=True, timeout=6000)
                                    pg2.wait_for_timeout(1600)

                                    for vk_c, v_c in voices_map.items():
                                        if not isinstance(v_c, dict):
                                            continue
                                        acc_vids = dict(v_c.get("account_voice_ids") or {})
                                        if sec_prof in acc_vids and len(str(acc_vids[sec_prof])) == 36:
                                            continue
                                        base_sp = _resolve_base_speaker_title(
                                            v_c.get("gender", "female"),
                                            v_c.get("flow_slug", ""),
                                            v_c.get("tone_style", ""),
                                            v_c.get("region", ""),
                                        )
                                        for step in range(16):
                                            pg2.evaluate(
                                                """(step) => {
                                                    const v = document.querySelector('.cdk-overlay-container cdk-virtual-scroll-viewport.asset-list-viewport');
                                                    if (v) v.scrollTop = step * 200;
                                                }""",
                                                step,
                                            )
                                            pg2.wait_for_timeout(200)
                                            sp_l = pg2.locator(f".cdk-overlay-container .asset-item:has-text('{base_sp}')")
                                            if sp_l.count() > 0:
                                                sp_l.first.click(force=True)
                                                pg2.wait_for_timeout(500)
                                                break
                                        sec_audio.clear()
                                        pg2.locator(".cdk-overlay-container textarea.sample-dialogue-input").first.fill(str(v_c.get("sample_dialogue_vn") or "")[:118], force=True)
                                        pg2.locator(".cdk-overlay-container textarea.performance-input").first.fill(str(v_c.get("voice_prompt_en") or ""), force=True)
                                        if pg2.locator(".cdk-overlay-container input.voice-name-input").count() > 0:
                                            pg2.locator(".cdk-overlay-container input.voice-name-input").first.fill(str(v_c.get("name") or vk_c), force=True)
                                        pg2.wait_for_timeout(400)
                                        pg2.locator(".cdk-overlay-container button:has-text('Xem trước')").first.click(force=True, timeout=5000)
                                        for _ in range(22):
                                            pg2.wait_for_timeout(800)
                                            if sec_audio:
                                                new_sec_vid, _, _ = sec_audio[-1]
                                                if new_sec_vid:
                                                    acc_vids[sec_prof] = new_sec_vid
                                                    v_c["account_voice_ids"] = acc_vids
                                                    cloned_cnt += 1
                                                break
                                        save_b = pg2.locator(".cdk-overlay-container button:has-text('Lưu giọng nói mới')").first
                                        if save_b.count() > 0 and not save_b.is_disabled():
                                            save_b.click(force=True, timeout=4000)
                                            pg2.wait_for_timeout(1600)
                                    cloned_accounts_summary.append(f"{sec_prof} ({cloned_cnt} voice)")
                                except Exception as e_sec:
                                    live_sync_errors.append(f"Clone {sec_prof}: {str(e_sec)[:100]}")
                                finally:
                                    try:
                                        ctx2.close()
                                    except Exception:
                                        pass
                    finally:
                        try:
                            browser.close()
                        except Exception:
                            pass

                cfg_live["custom_voices"] = [
                    {
                        "key": k,
                        "voice_id": v.get("voice_id", ""),
                        "name": v.get("name", k),
                        "gender": v.get("gender", "female"),
                        "region": v.get("region", "north"),
                        "flow_slug": v.get("flow_slug", ""),
                        "owner_profile": v.get("owner_profile", "leviettung04"),
                        "account_voice_ids": v.get("account_voice_ids", {}),
                        "project_id": "932bc2a1-07ea-4199-b147-80ab0018d41c",
                        "description": v.get("description", ""),
                    }
                    for k, v in voices_map.items()
                    if isinstance(v, dict)
                ]
                with open(VOICES_CHARS_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg_live, f, ensure_ascii=False, indent=2)
            except Exception as e_outer:
                live_sync_errors.append(str(e_outer)[:160])

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
                "account_voice_ids": v.get("account_voice_ids", {}),
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
    state["imported_new_voices"] = imported_names
    state["updated_voices"] = updated_names
    state["cloned_accounts_summary"] = cloned_accounts_summary
    state["live_sync_errors"] = live_sync_errors

    extra_parts = []
    if imported_names:
        extra_parts.append(f"vừa nhập mới {len(imported_names)} giọng tạo thủ công từ Google Flow ({', '.join(imported_names[:4])})")
    if updated_names:
        extra_parts.append(f"cập nhật/xác minh {len(updated_names)} giọng Custom trên Google Flow")
    if cloned_accounts_summary:
        extra_parts.append(f"nhân bản đa tài khoản: {', '.join(cloned_accounts_summary)}")

    state["scan_message"] = (
        f"🔄 Đã đồng bộ {len(state.get('voices_list', []))} giọng đọc Việt Nam trên Google Flow"
        + (f" — {'; '.join(extra_parts)}" if extra_parts else "")
        + f"! (Hỗ trợ ánh xạ UUID tự động theo từng tài khoản trong account_voice_ids)."
    )
    return state


def preview_vietnamese_voice(payload: dict) -> dict:
    """
    Nghe thử Giọng Đọc bằng Tiếng Việt với các lời thoại Affiliate hay dùng:
      1. Ưu tiên tuyệt đối phát file âm thanh thực tế từ Google Flow (`models/gemini-v4s-tts-flow`, `voice_samples/<key>_flow.mp3`)
         đúng giới tính Nam/Nữ và vùng miền của giọng đọc để tránh lỗi `gTTS` luôn đọc bằng giọng Nữ Google Translate.
      2. Nếu người dùng chọn lời thoại Tiếng Việt trùng với 1 trong các giọng Google Flow đã tải sẵn cùng giới tính -> phát ngay bản Google Flow đó.
      3. Nếu giọng đọc hiện tại đã có file Google Flow thực tế (`sample_vn_abs`) -> phát trực tiếp bản thu Google Flow chuẩn của giọng đó.
    """
    ensure_dirs_and_default_sheet()
    state = get_character_library_state()
    voices_list = state.get("voices_list", [])

    vkey = (payload.get("voice_key") or "").strip()
    flow_slug = (payload.get("flow_slug") or "").strip().lower()
    sample_text_vn = (payload.get("sample_text_vn") or payload.get("dialogue_vn") or "").strip()

    v_obj = next((x for x in voices_list if x["key"] == vkey), None)
    gender = (payload.get("gender") or (v_obj or {}).get("gender") or "female").lower()
    region = (payload.get("region") or (v_obj or {}).get("region") or "north").lower()
    tone_style = (payload.get("tone_style") or (v_obj or {}).get("tone_style") or "trustworthy_expert").lower()
    voice_label = (v_obj or {}).get("name") or flow_slug.upper() or vkey or "Giọng Tiếng Việt"

    if not sample_text_vn:
        sample_text_vn = (v_obj or {}).get("sample_dialogue_vn") or COMMON_VN_DIALOGUE_PRESETS[0]["text"]

    import urllib.parse as _urlparse

    # 1. Nếu câu thoại người dùng chọn trùng với 1 trong các file Google Flow `.mp3` đã tải sẵn và CÙNG GIỚI TÍNH -> phát ngay bản Google Flow đó
    if sample_text_vn:
        for cand_v in voices_list:
            c_abs = cand_v.get("sample_vn_abs")
            c_dlg = (cand_v.get("sample_dialogue_vn") or "").strip()
            if c_abs and os.path.isfile(c_abs) and cand_v.get("gender") == gender and c_dlg and sample_text_vn[:45] == c_dlg[:45]:
                return {
                    "ok": True,
                    "source": f"Google Flow ({cand_v.get('name')})",
                    "voice_key": vkey or cand_v["key"],
                    "voice_label": voice_label,
                    "sample_text_vn": c_dlg,
                    "dialogue_vn": c_dlg,
                    "audio_path": c_abs,
                    "audio_url": f"/api/media?path={_urlparse.quote(c_abs)}",
                }

    # 2. Nếu giọng đọc hiện tại (`v_obj`) có sẵn file âm thanh Google Flow thực tế (`sample_vn_abs`) và đúng giới tính -> phát luôn bản Google Flow chuẩn của giọng này
    if v_obj and v_obj.get("sample_vn_abs") and os.path.isfile(v_obj["sample_vn_abs"]) and v_obj.get("gender") == gender:
        abs_p = v_obj["sample_vn_abs"]
        saved_dlg = (v_obj.get("sample_dialogue_vn") or "").strip()
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

    # 3. Nếu đang tạo giọng mới trong Modal hoặc đổi giới tính Nam/Nữ sang giọng khác -> chọn file Google Flow `.mp3` chuẩn cùng giới tính + vùng miền / slug
    same_gender_voices = [
        x for x in voices_list
        if x.get("gender") == gender and x.get("sample_vn_abs") and os.path.isfile(x["sample_vn_abs"])
    ]
    if same_gender_voices:
        best_match = (
            next((x for x in same_gender_voices if x.get("flow_slug") == flow_slug), None)
            or next((x for x in same_gender_voices if x.get("region") == region and x.get("tone_style") == tone_style), None)
            or next((x for x in same_gender_voices if x.get("region") == region), None)
            or same_gender_voices[0]
        )
        fb_abs = best_match["sample_vn_abs"]
        fb_dlg = best_match.get("sample_dialogue_vn") or sample_text_vn
        return {
            "ok": True,
            "source": f"Google Flow ({best_match.get('name')})",
            "voice_key": vkey or best_match["key"],
            "voice_label": voice_label,
            "sample_text_vn": fb_dlg,
            "dialogue_vn": fb_dlg,
            "audio_path": fb_abs,
            "audio_url": f"/api/media?path={_urlparse.quote(fb_abs)}",
        }

    return {"ok": False, "error": "Chưa có file mẫu âm thanh Google Flow cho giới tính này. Hãy bấm 'Tự Custom Lên Google Flow & Lấy Về Kho' để tổng hợp giọng mới!"}


def _load_clean_flow_cookies(profile_name: str = "") -> list:
    """
    Đọc cookies phiên Google Flow từ `cookies/<profile_name>.json` hoặc tài khoản đang active
    mà KHÔNG mở `launch_persistent_context` trên thư mục profile đang mở (tránh lỗi Target page, context or browser has been closed).
    """
    scripts_dir = os.path.join(PIPELINE_DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    if WORKSPACE_DIR not in sys.path:
        sys.path.insert(0, WORKSPACE_DIR)

    prof_clean = str(profile_name or "").strip()
    cookie_candidates = []
    if prof_clean:
        for cand_p in (
            os.path.join(WORKSPACE_DIR, "data", "google_flow_grok", "cookies", f"{prof_clean}.json"),
            os.path.join(WORKSPACE_DIR, "cookies", f"{prof_clean}.json"),
        ):
            if os.path.isfile(cand_p) and cand_p not in cookie_candidates:
                cookie_candidates.append(cand_p)

    if not prof_clean:
        for def_p in (
            os.path.join(WORKSPACE_DIR, "data", "google_flow_grok", "cookies", "leviettung04.json"),
            os.path.join(WORKSPACE_DIR, "cookies", "leviettung04.json"),
        ):
            if os.path.isfile(def_p) and def_p not in cookie_candidates:
                cookie_candidates.append(def_p)
        try:
            import run_all_7_videos_mt as mt
            if getattr(mt, "cookie_file", None) and os.path.isfile(str(mt.cookie_file)):
                cookie_candidates.append(str(mt.cookie_file))
        except Exception:
            pass

        acc_json = os.path.join(WORKSPACE_DIR, "data", "google_flow_accounts.json")
        if os.path.isfile(acc_json):
            try:
                with open(acc_json, "r", encoding="utf-8") as f:
                    adata = json.load(f)
                for acc in adata.get("accounts", []):
                    if acc.get("enabled", True) and acc.get("cookie_file") and os.path.isfile(acc["cookie_file"]):
                        if acc["cookie_file"] not in cookie_candidates:
                            cookie_candidates.append(acc["cookie_file"])
            except Exception:
                pass

    for cpath in cookie_candidates:
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cookies = raw.get("cookies", raw) if isinstance(raw, dict) else raw
            if isinstance(cookies, list) and len(cookies) > 0:
                clean = [c for c in cookies if isinstance(c, dict) and "GRECAPTCHA" not in str(c.get("name", "")).upper()]
                if clean:
                    return clean
        except Exception:
            pass
    return []


def _resolve_base_speaker_title(gender: str, flow_slug: str, tone_style: str = "", region: str = "") -> str:
    """
    Chọn đúng tên Giọng Gốc (TitleCase) trên Google Flow (`Fenrir`, `Puck`, `Alnilam`, `Sadachbia`, `Orus`, `Achird`, `Zephyr`, `Erinome`, `Leda`...)
    để `no0P6` truyền đúng `[[BaseSpeakerName, CustomDisplayName]]` xuống `gemini_v4s_tts_flow`.
    Đảm bảo tuyệt đối giọng Nam không bao giờ bị gán nhầm vào giọng gốc Nữ (`Zephyr`...).
    """
    male_speakers = {
        "fenrir": "Fenrir",
        "puck": "Puck",
        "alnilam": "Alnilam",
        "sadachbia": "Sadachbia",
        "orus": "Orus",
        "achird": "Achird",
        "algenib": "Algenib",
        "algieba": "Algieba",
        "charon": "Charon",
        "enceladus": "Enceladus",
        "iapetus": "Iapetus",
        "rasalgethi": "Rasalgethi",
        "schedar": "Schedar",
        "umbriel": "Umbriel",
        "zubenelgenubi": "Zubenelgenubi",
    }
    female_speakers = {
        "zephyr": "Zephyr",
        "erinome": "Erinome",
        "leda": "Leda",
        "laomedeia": "Laomedeia",
        "aoede": "Aoede",
        "kore": "Kore",
        "callirrhoe": "Callirrhoe",
        "autonoe": "Autonoe",
        "despina": "Despina",
        "achernar": "Achernar",
        "gacrux": "Gacrux",
        "pulcherrima": "Pulcherrima",
        "sulafat": "Sulafat",
        "vindemiatrix": "Vindemiatrix",
    }
    slug_low = (flow_slug or "").strip().lower()
    if (gender or "").lower() == "male":
        if slug_low in male_speakers:
            return male_speakers[slug_low]
        if region == "south" or tone_style == "sweet_foodie":
            return "Puck"
        if tone_style == "trustworthy_expert":
            return "Alnilam"
        if tone_style == "chill_story":
            return "Orus"
        return "Fenrir"
    else:
        if slug_low in female_speakers:
            return female_speakers[slug_low]
        if tone_style == "sweet_foodie":
            return "Leda"
        if tone_style == "chill_story":
            return "Aoede"
        return "Zephyr"


def create_custom_voice_on_flow(payload: dict) -> dict:
    """
    Tự động mở Google Flow (`flow.google.com/project/<project_id>`) bằng phiên Cookie độc lập (không khóa Chrome profile đang mở),
    chọn đúng Giọng Gốc Nam/Nữ (`Fenrir`, `Puck`, `Alnilam`, `Sadachbia`, `Zephyr`...), điền:
      - Lời thoại mẫu Tiếng Việt (`textarea.sample-dialogue-input`, tối đa 120 ký tự)
      - Chỉ dẫn đặc điểm giọng đọc (`textarea.performance-input` — `voice_prompt_en`)
      - Tên hiển thị giọng đọc (`input.voice-name-input`)
    sau đó bấm `Xem trước` để Google Flow (`models/gemini-v4s-tts-flow`) tổng hợp giọng đọc Tiếng Việt mới,
    tự động bắt lấy mã `voice_id` UUID mới + tải file âm thanh `.mp3` về `flow_final_pipeline/voice_samples/<key>_flow.mp3`,
    bấm `Lưu giọng nói mới` trên Google Flow và cập nhật vào `voices_and_characters.json`.
    """
    ensure_dirs_and_default_sheet()
    save_voice_profile(payload)
    state = get_character_library_state()

    vkey = (payload.get("key") or "").strip().lower()
    vkey = __import__("re").sub(r"[^a-z0-9_]", "_", vkey).strip("_")
    v_obj = next((x for x in state.get("voices_list", []) if x["key"] == vkey), None)
    if not v_obj:
        return {"ok": False, "error": f"Không tìm thấy cấu hình giọng đọc #{vkey}"}

    gender = (payload.get("gender") or v_obj.get("gender") or "female").lower()
    region = (payload.get("region") or v_obj.get("region") or "north").lower()
    tone_style = (payload.get("tone_style") or v_obj.get("tone_style") or "energetic_sale").lower()
    flow_slug = (payload.get("flow_slug") or v_obj.get("flow_slug") or "").strip().lower()
    base_speaker = _resolve_base_speaker_title(gender, flow_slug, tone_style, region)

    v_name = v_obj.get("name") or f"Custom Voice {vkey}"
    v_prompt_en = (payload.get("voice_prompt_en") or v_obj.get("voice_prompt_en") or "").strip()
    if not v_prompt_en or len(v_prompt_en) < 120:
        v_prompt_en = build_voice_prompt_en(gender, region, tone_style, v_obj.get("speed_wpm", ""))
    elif gender == "male" and "no female resonance" not in v_prompt_en.lower():
        v_prompt_en = (
            f"Vietnamese male commercial presenter, young adult masculine baritone-tenor voice, {v_prompt_en}. "
            "Keep the same male voice, masculine pitch, accent, loudness, speaking speed and emotional style across every clip. "
            "No female resonance, no high-pitched female voice, no robotic delivery."
        )

    sample_vn = (payload.get("sample_dialogue_vn") or v_obj.get("sample_dialogue_vn") or COMMON_VN_DIALOGUE_PRESETS[0]["text"]).strip()
    sample_vn_118 = sample_vn[:118]
    project_id = payload.get("project_id") or "932bc2a1-07ea-4199-b147-80ab0018d41c"

    try:
        scripts_dir = os.path.join(PIPELINE_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        if WORKSPACE_DIR not in sys.path:
            sys.path.insert(0, WORKSPACE_DIR)
        import re as _re
        import grok_video_tool as gvt
        from playwright.sync_api import sync_playwright

        clean_cookies = _load_clean_flow_cookies()
        if not clean_cookies:
            return {"ok": False, "error": "Chưa tìm thấy Cookie phiên đăng nhập Google Flow. Hãy mở tab Tài Khoản & Flow để đăng nhập hoặc lấy Cookie!"}

        audio_captured = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-position=-2000,-2000", "--window-size=1280,800"],
            )
            ctx = browser.new_context()
            ctx.add_init_script(gvt._FLOW_HIJACK_BYPASS_JS)
            ctx.add_cookies(clean_cookies)
            pg = ctx.new_page()

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
            pg.evaluate(gvt._FLOW_HIJACK_BYPASS_JS)
            pg.wait_for_function(
                "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise",
                timeout=35000,
            )
            pg.wait_for_timeout(1800)

            pg.locator("button:has-text('Nhân vật'), [role='button']:has-text('Nhân vật')").first.click(force=True, timeout=6000)
            pg.wait_for_timeout(1400)
            pg.locator("text=MUSE Nhân vật 1").first.click(force=True, timeout=6000)
            pg.wait_for_timeout(1400)
            pg.locator(".voice-card-start-btn").first.click(force=True, timeout=6000)
            pg.wait_for_timeout(1800)

            # Cuộn danh sách giọng đọc trong `.cdk-overlay-container` để chọn đúng Giọng Gốc (`Fenrir`, `Puck`, `Alnilam`, `Zephyr`...)
            for step in range(16):
                pg.evaluate(
                    """(step) => {
                        const v = document.querySelector('.cdk-overlay-container cdk-virtual-scroll-viewport.asset-list-viewport');
                        if (v) v.scrollTop = step * 200;
                    }""",
                    step,
                )
                pg.wait_for_timeout(250)
                sp_loc = pg.locator(f".cdk-overlay-container .asset-item:has-text('{base_speaker}')")
                if sp_loc.count() > 0:
                    sp_loc.first.click(force=True)
                    pg.wait_for_timeout(700)
                    break

            audio_captured.clear()
            pg.locator(".cdk-overlay-container textarea.sample-dialogue-input").first.fill(sample_vn_118, force=True)
            pg.locator(".cdk-overlay-container textarea.performance-input").first.fill(v_prompt_en, force=True)
            if pg.locator(".cdk-overlay-container input.voice-name-input").count() > 0:
                pg.locator(".cdk-overlay-container input.voice-name-input").first.fill(v_name, force=True)
            pg.wait_for_timeout(600)

            pg.locator(".cdk-overlay-container button:has-text('Xem trước')").first.click(force=True, timeout=6000)
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
                if pg.locator(".cdk-overlay-container input.voice-name-input").count() > 0:
                    pg.locator(".cdk-overlay-container input.voice-name-input").first.fill(v_name, force=True)
                    pg.wait_for_timeout(300)
                save_btn = pg.locator(".cdk-overlay-container button:has-text('Lưu giọng nói mới')").first
                if save_btn.count() > 0 and not save_btn.is_disabled():
                    save_btn.click(force=True, timeout=5000)
                    pg.wait_for_timeout(2500)

            ctx.close()
            browser.close()

        if not got_vid or not os.path.isfile(out_abs):
            return {
                "ok": False,
                "error": "Google Flow chưa trả về file âm thanh sau 30 giây. Vui lòng kiểm tra phiên đăng nhập Google Flow.",
            }

        # Cập nhật voice_id mới & đường dẫn file âm thanh Tiếng Việt vào voices_and_characters.json
        updated_payload = dict(payload)
        updated_payload["key"] = vkey
        updated_payload["flow_slug"] = base_speaker.lower()
        updated_payload["voice_prompt_en"] = v_prompt_en
        if vkey not in ("nv1", "nv2") or payload.get("overwrite_default_uuid"):
            updated_payload["voice_id"] = got_vid
        updated_payload["sample_vn_file"] = out_rel
        updated_payload["sample_dialogue_vn"] = sample_vn_118
        updated_payload["flow_synced"] = True
        import urllib.parse as _urlparse
        new_state = save_voice_profile(updated_payload)
        new_state["created_voice_id"] = got_vid
        new_state["created_voice"] = {"key": vkey, "name": v_name, "voice_id": got_vid, "base_speaker": base_speaker}
        new_state["audio_path"] = out_abs
        new_state["audio_url"] = f"/api/media?path={_urlparse.quote(out_abs)}"
        new_state["sample_dialogue_vn"] = sample_vn_118
        msg = f"Đã tự động Custom giọng '{v_name}' (Giọng gốc: {base_speaker}, UUID: {got_vid}) trên Google Flow và tải mẫu âm thanh Tiếng Việt về máy!"
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

        clean_cookies = _load_clean_flow_cookies()
        if not clean_cookies:
            return {"ok": False, "error": "Chưa tìm thấy Cookie phiên đăng nhập Google Flow. Hãy mở tab Tài Khoản & Flow để đăng nhập hoặc lấy Cookie!", "prompt": final_prompt}
        cookie_map = {c["name"]: c["value"] for c in clean_cookies}
        cookie_hdr = "; ".join(f"{k}={v}" for k, v in cookie_map.items())

        with sync_playwright() as pw:
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

