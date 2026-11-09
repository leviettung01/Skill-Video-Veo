# -*- coding: utf-8 -*-
"""
Generator cho Template "Nhà Xưởng" (Template/Nhà Xưởng/generator.py)
Tự động phân tích thông tin sản phẩm (info.json + ảnh trong product_images/)
và sinh ra prompts.json + spec_v*.json chuẩn Hyper-Photorealistic 2K Ref Image & 1080p Video.
"""
import os
import re
import sys
import glob
import json
import math
from PIL import Image

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(TEMPLATE_DIR, "template_config.json")
WS_ROOT = os.path.abspath(os.path.join(TEMPLATE_DIR, "..", ".."))
SCRIPTS_DIR = os.path.join(WS_ROOT, "flow_final_pipeline", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    import engine_settings_manager as _esm
    from video_fx_and_broll_engine import (
        build_credible_environment_ref_prompt,
        build_scene_video_prompt_with_broll,
        DEFAULT_CAMERA_BROLL_SETTINGS,
        DEFAULT_VIDEO_EDIT_FX_SETTINGS,
    )
except Exception:
    _esm = None
    build_credible_environment_ref_prompt = None
    build_scene_video_prompt_with_broll = None
    DEFAULT_CAMERA_BROLL_SETTINGS = {}
    DEFAULT_VIDEO_EDIT_FX_SETTINGS = {}


def _load_cam_broll_settings() -> dict:
    if _esm is not None:
        try:
            cfg = _esm.load_engine_settings()
            if isinstance(cfg.get("camera_broll_settings"), dict):
                return cfg["camera_broll_settings"]
        except Exception:
            pass
    return dict(DEFAULT_CAMERA_BROLL_SETTINGS) if DEFAULT_CAMERA_BROLL_SETTINGS else {}


def _load_video_fx_settings() -> dict:
    if _esm is not None:
        try:
            cfg = _esm.load_engine_settings()
            if isinstance(cfg.get("video_edit_fx_settings"), dict):
                return cfg["video_edit_fx_settings"]
        except Exception:
            pass
    return dict(DEFAULT_VIDEO_EDIT_FX_SETTINGS) if DEFAULT_VIDEO_EDIT_FX_SETTINGS else {}


def load_template_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _parse_price_k(price_raw) -> tuple:
    """Trả về (price_k_str, ceil_anchor_k_str, high1_str, high2_str). VD: ('69K', '70K', '200', '150')."""
    s = str(price_raw or "").strip()
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return ("69K", "70K", "200", "150")
    val = int(digits)
    if val >= 1000:
        k = max(10, round(val / 1000))
    else:
        k = max(10, val)
    ceil_k = int(math.ceil((k + 1) / 10.0) * 10)
    high2 = max(ceil_k + 50, 150)
    high1 = max(high2 + 50, 200)
    return (f"{k}K", f"{ceil_k}K", str(high1), str(high2))


def _extract_short_vn_name(title: str) -> str:
    """Rút gọn tên sản phẩm tiếng Việt để đọc thoại tự nhiên (khoảng 5-8 từ, không cắt cụt từ ghép)."""
    t = (title or "").strip()
    t = re.sub(r"\[[^\]]*\]|\([^\)]*\)", " ", t)
    t = re.sub(r"-\s*[A-Za-z0-9_]+$", " ", t)
    # Bỏ các thông số kích thước dạng 20x20cm, 15x20cm để câu thoại mượt tự nhiên
    t = re.sub(r"\b\d+\s*[xX×]\s*\d+\s*(cm|mm|m)\b", " ", t)
    # Ưu tiên lấy cụm chính trước dấu phẩy hoặc gạch chéo nếu đủ độ dài
    first_clause = re.split(r"[,;/|]+", t)[0].strip()
    if len(first_clause.split()) >= 4:
        t = first_clause
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return "sản phẩm chính hãng tại xưởng"
    words = t.split()
    max_w = 7
    # Nếu từ thứ 7 là tiền tố của từ ghép 2 âm tiết phổ biến thì lấy thêm từ thứ 8 để không bị cụt chữ
    incomplete_prefixes = {
        "đa", "thông", "tự", "chính", "cao", "chống", "không", "siêu",
        "nhà", "điện", "kim", "rửa", "cổ", "dây", "khóa", "in", "ba",
    }
    if len(words) > max_w and words[max_w - 1].lower() in incomplete_prefixes:
        max_w = 8
    short = " ".join(words[:max_w])
    short_lower = short.lower()
    short_lower = re.sub(r"\b304\b", "ba lẻ tư", short_lower)
    short_lower = re.sub(r"\b5kg\b", "năm ký", short_lower)
    short_lower = re.sub(r"\b10kg\b", "mười ký", short_lower)
    return short_lower.strip(" ,.-")


def _infer_product_en_and_scale(title: str, desc: str) -> tuple:
    """Suy luận mô tả loại sản phẩm và kích thước cầm tay chuẩn xác bằng tiếng Anh cho Prompt Ảnh Ref 2K."""
    text = f"{title} {desc}".lower()
    mapping = [
        (
            ["khăn lưới", "khăn rửa chén", "khăn lau bếp", "miếng rửa chén", "miếng cọ", "bùi nhùi"],
            "20x20cm silver diamond-weave metal mesh dishwashing cloth",
            "true-to-life 20x20cm palm-sized flexible mesh dishcloth held naturally between both hands",
        ),
        (
            ["khăn tắm", "khăn mặt", "khăn lau"],
            "soft folded fabric towel",
            "true-to-life hand-held folded towel size relative to the hands and body",
        ),
        (
            ["cân tiểu ly", "cân điện tử", "cân nhà bếp"],
            "compact stainless-steel digital kitchen scale",
            "true-to-life compact 18x14cm hand-held digital scale relative to the hands and body",
        ),
        (
            ["thắt lưng", "dây nịt", "belt"],
            "men's belt with metal buckle",
            "true-to-life palm-sized coiled belt and gift box scale relative to the hands and body",
        ),
        (
            ["kính", "mắt kính", "gọng kính"],
            "eyeglasses frame",
            "true-to-life palm-sized eyewear frame relative to the hands and body",
        ),
        (
            ["ví", "bóp", "wallet"],
            "compact leather wallet",
            "true-to-life palm-sized wallet relative to the hands and body",
        ),
        (
            ["túi", "balo", "cặp"],
            "handbag / backpack",
            "true-to-life natural bag proportion relative to the hands and body",
        ),
        (
            ["đồng hồ", "watch"],
            "wristwatch",
            "true-to-life compact wristwatch scale relative to the hands and body",
        ),
        (
            ["tai nghe", "loa", "bluetooth"],
            "compact audio device",
            "true-to-life palm-sized gadget scale relative to the hands and body",
        ),
        (
            ["bình giữ nhiệt", "cốc", "ly"],
            "insulated tumbler cup",
            "true-to-life hand-held tumbler size relative to the hands and body",
        ),
        (
            ["máy cạo râu", "tông đơ", "máy sấy", "bàn chải"],
            "compact personal care appliance",
            "true-to-life compact hand-held device relative to the hands and body",
        ),
        (
            ["bộ vẽ", "dụng cụ vẽ", "bút màu", "màu vẽ"],
            "art & drawing supply kit box",
            "true-to-life hand-held stationery case proportion relative to the hands and body",
        ),
        (
            ["tinh dầu", "nước hoa", "kem", "serum", "sữa rửa mặt", "son", "mỹ phẩm"],
            "cosmetic / fragrance bottle set",
            "true-to-life palm-sized cosmetic bottle / gift box relative to the hands and body",
        ),
        (
            ["kho quẹt", "bánh pía", "bánh", "kẹo", "hạt sen", "hạt", "khô gà", "khô bò", "trà"],
            "packaged food specialty item",
            "true-to-life hand-held food jar / retail pack size relative to the hands and body",
        ),
        (
            ["áo", "quần", "váy", "đầm"],
            "neatly folded garment item",
            "true-to-life natural clothing item proportion relative to the hands and body",
        ),
        (
            ["giày", "dép", "sandal"],
            "single footwear item",
            "true-to-life natural shoe size relative to the hands and body",
        ),
        (
            ["nồi", "chảo", "bếp từ", "bếp điện", "bếp ga", "máy xay", "ấm siêu tốc"],
            "kitchen appliance / cookware item",
            "true-to-life realistic household cookware size relative to the hands and body",
        ),
    ]
    for keywords, prod_en, scale_en in mapping:
        if any(kw in text for kw in keywords):
            return prod_en, scale_en
    return "authentic product item", "true-to-life natural hand-held scale relative to the hands and body"


def build_hyper_realistic_ref_prompt(
    ck: str,
    appearance_en: str,
    outfit_en: str,
    setting_en: str,
    prod_type_en: str,
    prod_scale_en: str,
    gender: str = "female",
) -> str:
    """
    Xây dựng Prompt tạo Ảnh Reference 2K (1536x2752) theo cấu trúc Hyper-Photorealistic Portrait:
      1. Subject & Identity Lock (Close-medium upper-body 9:16 portrait at 1.2m distance)
      2. Skin Pores, Douyin Glass-Skin & Makeup
      3. Hair & Adult Physique (90-60-90 / Athletic)
      4. Expression, Relaxed Asymmetrical Pose & 100% Product Lock
      5. Camera, Lens & Lighting Physics (Sony A7R V 50mm f/1.4 GM + natural iPhone 16 Pro realism)
      6. Strict Anti-AI Negative Prompt
    """
    is_male = (gender or "").lower() == "male" or "nv3" in (ck or "").lower()
    app_low = (appearance_en or "").lower()
    has_glasses = (
        ("nv1" in (ck or "").lower())
        or ("framed glasses" in app_low and "no glasses" not in app_low and "without glasses" not in app_low)
    )

    if is_male:
        skin_and_details = (
            "Detailed visible natural skin pores and authentic masculine epidermal micro-texture (zero plastic or waxy smoothing), "
            "healthy warm-fair complexion with subtle natural light reflection on the bridge of the nose, cheekbones, and forehead; "
            "matching skin tone across face, neck, forearms, and hands. Sharp masculine jawline, naturally groomed eyebrows, "
            "and expressive dark eyes with crisp dual catchlights."
        )
        physique_block = (
            "PHYSIQUE: Athletic, mature adult masculine proportions with broad shoulders, toned chest, V-taper torso, and natural confident posture."
        )
        pose_block = (
            "Expression / Pose: Warm, charismatic, approachable smile toward the camera, lips gently parted as if speaking naturally, "
            "subtle head tilt, torso turned slightly (5-8 degrees) for relaxed masculine asymmetry rather than a stiff frontal pose."
        )
    else:
        glasses_clause = (
            " She wears thin, lightweight black-framed glasses with crystal-clear anti-reflective lenses — zero white glare or distortion over her eyes."
            if has_glasses
            else ""
        )
        skin_and_details = (
            "Detailed visible natural skin pores and lifelike epidermal micro-texture (absolutely zero plastic or airbrushed doll skin), "
            "radiant rosy dewy Douyin glass-skin finish with subtle specular light reflection on the bridge of her nose, cheeks, and forehead. "
            "Her face, neck, and hands match in the same fair, radiant skin tone without any unevenness. "
            "Makeup: Fresh Korean soft-glam luminous makeup, soft pink blush across the cheeks and a touch of blush on the nose tip for a youthful look, "
            "subtle aegyosal under bright expressive dark-brown eyes with crisp catchlights, wispy curled eyelashes, thin defined winged eyeliner, "
            "naturally brushed eyebrows, and glossy ombré lips with a nude-pink base blending into cherry-blossom red lip tint in the center."
            + glasses_clause
        )
        physique_block = (
            "PHYSIQUE: Full, mature adult feminine proportions with natural womanly curves, C-cup natural bust, using 90-60-90 proportions, "
            "natural upper-body volume, relatively slender waist, and graceful feminine posture."
        )
        pose_block = (
            "Expression / Pose: Warm, charming, friendly smile looking directly into the camera lens, lips gently parted, "
            "subtle head tilt, torso turned slightly (5-10 degrees three-quarter angle), gently relaxed neck and one shoulder slightly closer to the camera "
            "for relaxed feminine asymmetry (NOT a stiff frontal mannequin pose)."
        )

    if build_credible_environment_ref_prompt is not None:
        return build_credible_environment_ref_prompt(
            ck=ck,
            appearance_en=appearance_en,
            outfit_en=outfit_en,
            setting_en=setting_en,
            prod_type_en=prod_type_en,
            prod_scale_en=prod_scale_en,
            gender=gender,
            cam_settings=_load_cam_broll_settings(),
        )

    return (
        "Subject & Identity: A hyper-photorealistic vertical 9:16 MEDIUM-FULL ENVIRONMENTAL SHOT (framed from mid-thigh/hips up with natural headroom, "
        f"camera at 2.2 meters distance with 35mm wide-environmental perspective so the presenter occupies ~45% of the frame width and the credible background behind them is clearly visible) of the exact same person from the attached character reference image "
        f"({appearance_en}), preserving their original facial identity, bone structure, and features 100% without altering facial identity. "
        f"Outfit & Credible Background Setting: {outfit_en}, {setting_en}. "
        f"Skin & Makeup: {skin_and_details} "
        f"{physique_block} "
        f"{pose_block} "
        f"Product Action & Lock: Clean, natural hands holding and presenting the exact {prod_type_en} from the attached product reference image "
        f"at chest-to-waist level facing the camera ({prod_scale_en}, NOT oversized), with neat authentic retail packages on the foreground table. "
        "Keep the product 100% identical to the product reference image (preserve exact shape, material texture, weave, color, logo, and labels without redesigning). "
        "Camera & Lighting: Shot on Sony A7R V full-frame camera with 35mm f/1.4 GM prime lens stopped down to f/4.5 for deep environmental depth of field, "
        "soft diffused key lighting from the front-left combined with natural overhead facility lighting, keeping the background racks, production line, and facility architecture clearly recognizable behind the presenter. "
        "Ultra-high resolution 2K (1536x2752), indistinguishable from a genuine photograph, zero AI-generated appearance. "
        "Negative prompt: AI look, CGI, 3D render, plastic skin, waxy airbrushed face, doll face, stiff pose, frontal passport pose, unnatural symmetry, "
        "dead eyes, crossed eyes, blurry eyes, opaque glasses glare, altered facial identity, giant oversized product, redesigned product, "
        "extra fingers, deformed hands, extreme close-up cropping out background, random text, watermark."
    )


def _split_into_karaoke_phrases(text: str, max_chars: int = 28) -> list:
    """
    Tách câu thoại tiếng Việt thành danh sách các phrase [TEXT_IN_HOA <= 28 ký tự, số_từ_nói].
    """
    clean = re.sub(r"[\"“”]", "", text)
    clean = re.sub(r"[,.;:!?\-]+", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return [["ƯU ĐÃI TẬN XƯỞNG HÔM NAY", 6]]

    words = clean.split()
    phrases = []
    cur_words = []

    def _spoken_word_count(w_list):
        cnt = 0
        for w in w_list:
            wu = w.upper()
            if wu in ("200", "300", "400", "500"):
                cnt += 2
            elif wu in ("150", "250", "350"):
                cnt += 3
            elif re.match(r"^\d+K$", wu):
                cnt += 2
            else:
                cnt += 1
        return max(1, cnt)

    for w in words:
        wu = w.upper()
        candidate = " ".join(cur_words + [wu])
        if len(candidate) <= max_chars and len(cur_words) < 6:
            cur_words.append(wu)
        else:
            if cur_words:
                phrases.append([" ".join(cur_words), _spoken_word_count(cur_words)])
            cur_words = [wu[:max_chars]]
    if cur_words:
        phrases.append([" ".join(cur_words), _spoken_word_count(cur_words)])
    return phrases


def _extract_usp_lines(title: str, desc: str, short_name: str) -> list:
    """Trích xuất 3 cặp câu USP ngắn gọn, giàu thông tin thực tế và luôn nhắc đầy đủ tên sản phẩm cho Cảnh 3."""
    sn = (short_name or "sản phẩm chính hãng").strip()
    text_low = f"{title or ''} {desc or ''}".lower()

    if any(k in text_low for k in ("khăn lưới", "khăn rửa chén", "miếng cọ", "khăn lau bếp")):
        return [
            (
                f"Mẫu {sn} cọ sạch xoong nồi chén bát không làm trầy xước.",
                "Sợi lưới kim loại đan kim cương bền chắc, đánh bay vết bẩn cực nhanh.",
            ),
            (
                f"Dùng {sn} lau bếp thoát nước nhanh, không bám dầu mỡ.",
                "Hàng xuất trực tiếp từ nhà máy, kiểm tra kỹ từng đường viền trước khi giao.",
            ),
            (
                f"Combo {sn} dệt dày dặn, tái sử dụng bền gấp chục lần.",
                "Mua dùng cho bếp gia đình hay quán ăn đều cực kỳ sạch sẽ tiết kiệm.",
            ),
        ]

    raw_text = f"{desc or ''}. {title or ''}"
    sents = [s.strip() for s in re.split(r"[.\n•\-]+", raw_text) if len(s.strip()) > 15]
    usp_pairs = [
        (
            f"Mẫu {sn} chuẩn xưởng chất lượng cao, gia công tỉ mỉ từng chi tiết.",
            "Đóng gói kỹ lưỡng đầy đủ phụ kiện, các bác chốt ngay giúp em.",
        ),
        (
            f"Dòng {sn} thiết kế chắc chắn hiện đại, sử dụng tiện lợi bền bỉ.",
            "Hàng xuất trực tiếp từ nhà máy, kiểm tra kỹ từng sản phẩm trước khi giao.",
        ),
        (
            f"Siêu phẩm {sn} chất liệu cao cấp chọn lọc kỹ, hoàn thiện sắc nét.",
            "Mua dùng hay làm quà đều rất hợp lý, cam kết y hình từ nhà xưởng.",
        ),
    ]
    if sents:
        cleaned_s = []
        for s in sents[:6]:
            s_clean = re.sub(r"\s+", " ", s).strip()
            s_Words = s_clean.split()
            if 6 <= len(s_Words) <= 18:
                cleaned_s.append(" ".join(s_Words[:14]))
        if len(cleaned_s) >= 1:
            u0 = cleaned_s[0].rstrip(",.;") + "."
            u0 = re.sub(r"\b304\b", "ba lẻ tư", u0, flags=re.I)
            u0 = re.sub(r"\b10kg\b", "mười ký", u0, flags=re.I)
            u0 = re.sub(r"\b5kg\b", "năm ký", u0, flags=re.I)
            usp_pairs[0] = (u0, usp_pairs[0][1])
    return usp_pairs


def select_best_product_images(prod_img_dir: str) -> tuple:
    """Chọn primary_product_refs (1 ảnh đơn rõ nét) và slide_overlay_files (tối đa 5 ảnh)."""
    jpgs = sorted(
        glob.glob(os.path.join(prod_img_dir, "prod_*.jpg")),
        key=lambda p: int(re.findall(r"prod_(\d+)", os.path.basename(p))[0]) if re.findall(r"prod_(\d+)", os.path.basename(p)) else 999,
    )
    if not jpgs:
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            jpgs.extend(sorted(glob.glob(os.path.join(prod_img_dir, ext))))
    if not jpgs:
        return (["prod_1.jpg"], ["prod_1.jpg"])

    valid_rels = []
    for p in jpgs:
        try:
            if os.path.getsize(p) > 3000:
                valid_rels.append(os.path.basename(p))
        except OSError:
            pass
    if not valid_rels:
        valid_rels = [os.path.basename(jpgs[0])]

    primary_rel = valid_rels[0]
    slides = valid_rels[:5]
    return ([primary_rel], slides)


def _adapt_dialect_lines(timed_lines: list, region: str) -> list:
    if (region or "").lower() != "south":
        return timed_lines
    out = []
    for ln in timed_lines:
        s = ln
        s = re.sub(r"\bcác bác\b", "cả nhà", s, flags=re.I)
        s = re.sub(r"\bCác bác\b", "Cả nhà", s)
        s = re.sub(r"\bnhé\b", "nha", s, flags=re.I)
        s = re.sub(r"\bđó ạ\b", "luôn nghen", s, flags=re.I)
        s = re.sub(r"\bgiúp em ạ\b", "giúp em nha", s, flags=re.I)
        s = re.sub(r"\bthôi ạ\b", "thôi nghen", s, flags=re.I)
        out.append(s)
    return out


def make_video_prompt(
    scene_idx: int,
    timed_lines: list,
    scene_actions: dict,
    voice_prompt_en: str = "",
    prod_type_en: str = "authentic product",
    style_label: str = "Nhà Xưởng & Tổng Kho Xuất Hàng",
) -> str:
    if build_scene_video_prompt_with_broll is not None:
        return build_scene_video_prompt_with_broll(
            scene_idx=scene_idx,
            timed_lines=timed_lines,
            scene_actions=scene_actions or {},
            prod_type_en=prod_type_en,
            setting_en=style_label,
            voice_prompt_en=voice_prompt_en,
            cam_settings=_load_cam_broll_settings(),
            fx_settings=_load_video_fx_settings(),
        )
    action_str = scene_actions.get(str(scene_idx)) or scene_actions.get(1) or (
        "The presenter looks directly into the camera lens with a warm, charming, energetic smile and lifelike eye contact "
        "(natural eye blinking and crisp catchlights), speaking naturally with accurate Vietnamese lip-sync while holding the exact product "
        "from the reference image steady at chest-to-waist level, tilting it slightly toward the camera to showcase it, then keeping the presenting pose at the end."
    )
    voice_block = "\n".join(timed_lines)
    voice_dir = f" ({voice_prompt_en})" if voice_prompt_en else ""
    return (
        "A hyper-photorealistic 10-second vertical 9:16 video starting directly from the provided 2K reference image, "
        "shot on Sony A7R V 35mm f/1.4 GM lens at f/4.5, one continuous medium-full environmental shot, front-facing eye-level camera. "
        "Preserve 100% of the character's exact facial identity, visible natural skin pores, rosy dewy glass-skin texture, "
        "clear eyes with crisp catchlights (and clear anti-reflective glasses if worn), the exact product in hand, "
        "the items on the table, and the background warehouse/factory layout from the reference image — "
        "do not alter, smooth, or re-synthesize the face, and do not redesign or replace the product's shape, weave, color, or logo.\n\n"
        f"ACTION: {action_str}\n\n"
        f"VOICE{voice_dir} — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment "
        "fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — "
        "no repetition, no looping, no added words, then stay silent:\n"
        f"{voice_block}\n\n"
        "No background music, no watermark.\n"
        "Negative: AI plastic skin, waxy face, altered face, crossed or blurry eyes, glasses glare, warped mouth, changed product, altered product design, repeating voice, looping dialogue, second voice pass, rushed reading"
    )


def generate_project_from_template(
    pid: str,
    pdir: str,
    info_data: dict,
    characters_data: dict,
    videos_per_character: int = None,
    primary_product_refs: list = None,
    slide_overlay_files: list = None,
) -> dict:
    """
    Sinh prompts.json và spec_v*.json trong thư mục projects/<pid>/ theo Template Nhà Xưởng.
    Hỗ trợ tuỳ chỉnh số lượng video trên mỗi nhân vật (videos_per_character).
    """
    cfg = load_template_config()
    scene_actions = cfg.get("scene_actions", {})
    char_presets_map = cfg.get("character_presets", {})

    os.makedirs(pdir, exist_ok=True)
    prod_img_dir = os.path.join(pdir, "product_images")
    os.makedirs(prod_img_dir, exist_ok=True)

    auto_primary, auto_slides = select_best_product_images(prod_img_dir)
    primary_refs = primary_product_refs if primary_product_refs else auto_primary
    slide_overlays = slide_overlay_files if slide_overlay_files else auto_slides

    pname = (
        info_data.get("name")
        or info_data.get("title")
        or info_data.get("product_name")
        or f"Sản phẩm {pid}"
    )
    desc = info_data.get("description") or ""
    price_raw = info_data.get("price") or info_data.get("price_str") or "69.000₫"

    price_k, ceil_k, high1, high2 = _parse_price_k(price_raw)
    short_vn = _extract_short_vn_name(pname)
    prod_type_en, prod_scale_en = _infer_product_en_and_scale(pname, desc)
    usp_pairs = _extract_usp_lines(pname, desc, short_vn)

    chars_dict = characters_data.get("characters", {})
    voices_dict = characters_data.get("voices", {})
    default_vpc = int(
        videos_per_character
        or characters_data.get("default_videos_per_character")
        or cfg.get("default_videos_per_character", 3)
    )

    hook_templates = [
        (
            '[0.0-3.7s] "Cái này là cho các bác này. Sàn người ta cho chứ không phải bán nữa rồi."',
            f'[3.7-7.8s] "Siêu phẩm {short_vn} đang được trợ giá cực rẻ tại xưởng,"',
            '[7.8-10.0s] "các bác bấm giỏ hàng xem giá giúp em nhé."',
        ),
        (
            f'[0.0-4.0s] "{price_k} cho siêu phẩm {short_vn} này các bác ơi."',
            '[4.0-7.8s] "Ở đâu bán giá này em cũng bái phục, tận xưởng không thể rẻ vậy."',
            '[7.8-10.0s] "Hôm nay kênh em được trợ giá rất rẻ luôn."',
        ),
        (
            '[0.0-3.5s] "Các bác khoan hãy lướt qua video này kẻo tiếc hùi hụi luôn nha."',
            f'[3.5-7.4s] "Tại tổng kho hôm nay mẫu {short_vn} đang xả trợ giá cực sâu,"',
            '[7.4-10.0s] "bấm ngay vào giỏ hàng kiểm tra giá giúp em nhé."',
        ),
        (
            '[0.0-3.5s] "Đừng mua ở ngoài làm gì cho đắt đỏ tốn kém các bác ơi."',
            f'[3.5-7.4s] "Lấy trực tiếp tại xưởng mẫu {short_vn} hôm nay rẻ bất ngờ,"',
            '[7.4-10.0s] "các bác mở giỏ hàng góc trái xem thử ngay nhé."',
        ),
        (
            f'[0.0-3.6s] "Tin vui cho các bác đang tìm {short_vn} chuẩn xưởng giá bình dân."',
            '[3.6-7.4s] "Lô mới xuất xưởng hôm nay đang được sàn tài trợ giá cực tốt,"',
            '[7.4-10.0s] "các bác ấn ngay vào giỏ hàng xem ưu đãi nhé."',
        ),
        (
            '[0.0-3.5s] "Thật sự mức giá hôm nay làm em đứng tại xưởng cũng bất ngờ."',
            f'[3.5-7.4s] "Nguyên một siêu phẩm {short_vn} chuẩn xịn mà giá chỉ bằng bữa sáng,"',
            '[7.4-10.0s] "các bác bấm giỏ hàng bên dưới xem ngay nha."',
        ),
    ]

    scene2_templates = [
        (
            f'[0.0-3.6s] "Giá không phải {high1}, không phải {high2}, {ceil_k} cũng không luôn."',
            '[3.6-6.0s] "Mỗi tài khoản các bác sẽ thấy một giá khác nhau."',
            f'[6.0-10.0s] "Bấm giỏ hàng góc trái nha, nếu thấy giá dưới {ceil_k} thì săn liền giúp em ạ."',
        ),
        (
            f'[0.0-3.7s] "Giá không phải {high1}, không phải {high2}, {ceil_k} cũng không luôn."',
            '[3.7-5.7s] "Mà mỗi tài khoản một giá khác nhau nha."',
            f'[5.7-10.0s] "Các bác bấm giỏ hàng góc trái, thấy dưới {ceil_k} thì săn liền giúp em ạ."',
        ),
        (
            f'[0.0-3.6s] "Giá không phải {high1}, không phải {high2}, {ceil_k} cũng không luôn."',
            '[3.6-6.2s] "Tùy từng tài khoản mà sàn áp mức giảm khác nhau."',
            f'[6.2-10.0s] "Các bác mở giỏ hàng góc trái, thấy dưới {ceil_k} là chốt đơn liền tay nha."',
        ),
    ]

    scene3_closings = [
        '[7.0-10.0s] "ưu đãi chớp nhoáng hôm nay, hết là về giá gốc đó ạ."',
        '[7.0-10.0s] "số lượng ưu đãi có hạn nên các bác đặt sớm nhé."',
        '[7.0-10.0s] "chương trình chỉ mở trong hôm nay thôi ạ."',
    ]

    videos_json = {}
    enabled_chars = [
        (ck, cval)
        for ck, cval in chars_dict.items()
        if cval.get("enabled", True) is not False
    ]
    if not enabled_chars:
        enabled_chars = list(chars_dict.items())

    global_var_counter = 0
    for char_idx, (ck, cval) in enumerate(enabled_chars):
        char_vpc = int(
            videos_per_character
            if videos_per_character is not None
            else cval.get("videos_per_character", default_vpc)
        )
        char_vpc = max(1, min(5, char_vpc))
        voice_key = cval.get("default_voice", ck)
        v_obj = voices_dict.get(voice_key, {})
        voice_id = cval.get("voice_id") or v_obj.get("voice_id", "")
        voice_name = cval.get("voice_name") or v_obj.get("name", "")
        voice_region = cval.get("voice_region") or v_obj.get("region", "north")
        voice_gender = cval.get("voice_gender") or v_obj.get("gender", "female")
        voice_prompt_en = cval.get("voice_prompt_en") or v_obj.get("voice_prompt_en", "")
        char_id = cval.get("character_id", "")
        proj_id = cval.get("project_id", "")
        appearance_en = cval.get("appearance_en") or (
            "beautiful 23-year-old Vietnamese/East Asian woman with refined symmetrical facial features, fair rosy dewy Douyin glass-skin with visible natural pores, expressive dark-brown eyes, thin black-framed anti-reflective glasses, voluminous shoulder-length layered glossy black hair with airy see-through bangs"
            if "nv1" in ck.lower()
            else "gorgeous 23-year-old Vietnamese/East Asian woman with refined symmetrical V-line face, radiant fair rosy dewy Douyin glass-skin with visible natural pores, wavy dark-brown hair in a high ponytail with pastel hair clips, no glasses"
        )

        presets = char_presets_map.get(ck) or char_presets_map.get("nv1" if char_idx % 2 == 0 else "nv2", [])

        for v_idx in range(1, char_vpc + 1):
            global_var_counter += 1
            preset = presets[(v_idx - 1) % len(presets)] if presets else {}
            if ck == "nv1" and v_idx <= 5:
                vkey = f"v{(v_idx - 1) * 2 + 1}"
            elif ck == "nv2" and v_idx <= 5:
                vkey = f"v{v_idx * 2}"
            else:
                vkey = f"{ck}_v{v_idx}"

            char_v = f"{ck}_v{v_idx}"
            hook_title = preset.get("hook_title") or f"{ck.upper()} - Kịch bản {v_idx}"
            style_label = preset.get("style") or "Xưởng sản xuất & Kiểm định chất lượng"
            outfit_en = preset.get("outfit_en") or "wearing a chic open tailored blazer over a fitted soft ribbed knit top"
            setting_en = preset.get("setting_en") or "standing behind a clean display worktable in a bright modern manufacturing and inspection facility with creamy background bokeh"

            ref_img_prompt = build_hyper_realistic_ref_prompt(
                ck=ck,
                appearance_en=appearance_en,
                outfit_en=outfit_en,
                setting_en=setting_en,
                prod_type_en=prod_type_en,
                prod_scale_en=prod_scale_en,
                gender=voice_gender,
            )

            h_seg1, h_seg2, h_seg3 = hook_templates[(global_var_counter - 1) % len(hook_templates)]
            s2_seg1, s2_seg2, s2_seg3 = scene2_templates[(global_var_counter - 1) % len(scene2_templates)]
            u_line1, u_line2 = usp_pairs[(global_var_counter - 1) % len(usp_pairs)]
            s3_seg1 = f'[0.0-3.7s] "{u_line1}"'
            s3_seg2 = f'[3.7-7.0s] "{u_line2}"'
            s3_seg3 = scene3_closings[(global_var_counter - 1) % len(scene3_closings)]

            raw_scenes = [
                (1, f"{vkey}_s1", f"{vkey}_s1.mp4", _adapt_dialect_lines([h_seg1, h_seg2, h_seg3], voice_region)),
                (2, f"{vkey}_s2", f"{vkey}_s2.mp4", _adapt_dialect_lines([s2_seg1, s2_seg2, s2_seg3], voice_region)),
                (3, f"{vkey}_s3", f"{vkey}_s3.mp4", _adapt_dialect_lines([s3_seg1, s3_seg2, s3_seg3], voice_region)),
            ]

            scenes_list = []
            spec_scenes = []
            for sc_num, sc_id, sc_file, timed_lines in raw_scenes:
                joined_dialogue = " ".join(
                    re.sub(r"^\[[^\]]+\]\s*", "", ln).strip().strip('"')
                    for ln in timed_lines
                )
                phrases = _split_into_karaoke_phrases(joined_dialogue, max_chars=28)
                total_w = sum(w for _, w in phrases)
                v_prompt = make_video_prompt(
                    sc_num,
                    timed_lines,
                    scene_actions,
                    voice_prompt_en=voice_prompt_en,
                    prod_type_en=prod_type_en,
                    style_label=style_label,
                )
                scenes_list.append({
                    "id": sc_id,
                    "file": sc_file,
                    "words": total_w,
                    "prompt": v_prompt,
                    "include_prod_uuid_in_video": True,
                })
                spec_scenes.append({
                    "file": sc_file,
                    "words": total_w,
                    "phrases": phrases,
                })

            ref_img_name = f"{vkey}-refimg.jpg"
            videos_json[vkey] = {
                "char_v": char_v,
                "character": ck,
                "hook_title": hook_title,
                "style": style_label,
                "template_id": cfg.get("id", "nha_xuong"),
                "template_name": cfg.get("folder_name", "Nhà Xưởng"),
                "character_id": char_id,
                "project_id": proj_id,
                "voice_id": voice_id,
                "voice_name": voice_name,
                "ref_image": ref_img_name,
                "ref_image_prompt": ref_img_prompt,
                "primary_product_refs": primary_refs,
                "slide_overlay_files": slide_overlays,
                "scenes": scenes_list,
            }

            spec_obj = {
                "scenes": spec_scenes,
                "overlays": [os.path.join("product_images", f) for f in slide_overlays],
                "output": f"{pid}_{char_v}.mp4",
            }
            with open(os.path.join(pdir, f"spec_{vkey}.json"), "w", encoding="utf-8") as f:
                json.dump(spec_obj, f, ensure_ascii=False, indent=2)

    prompts_obj = {
        "product_id": pid,
        "product_name": pname,
        "template_id": cfg.get("id", "nha_xuong"),
        "template_name": cfg.get("folder_name", "Nhà Xưởng"),
        "videos_per_character": default_vpc,
        "primary_product_refs": primary_refs,
        "slide_overlay_files": slide_overlays,
        "ref_img_prompt_nv1": videos_json.get("v1", {}).get("ref_image_prompt", ""),
        "ref_img_prompt_nv2": videos_json.get("v2", {}).get("ref_image_prompt", ""),
        "videos": videos_json,
    }
    with open(os.path.join(pdir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_obj, f, ensure_ascii=False, indent=2)

    return prompts_obj
